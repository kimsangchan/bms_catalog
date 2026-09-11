# -*- coding: utf-8 -*-
"""검수 현황 — 무엇이 얼마나 확인됐나. 그리고 사람이 확인한 것을 저장소에 남긴다.

  PYTHONIOENCODING=utf-8 python mappings.py                    현황
  PYTHONIOENCODING=utf-8 python mappings.py --import <파일>     화면에서 내려받은 것을 넣는다
  PYTHONIOENCODING=utf-8 python mappings.py --models           모델별로 자세히

왜 있나
  `point-verify.html` 의 ✓ 표시는 여태 **그 브라우저 안에만** 남았다(localStorage).
  다른 PC 에서도, 다른 도구에서도, 커밋에서도 안 보였다. 그래서 "대조가 된 설비" 가
  무엇인지 저장소가 알 길이 없었고, 템플릿 매칭과 등급이 **검수 여부와 무관하게**
  158모델 전체로 매겨졌다.

⚠ 처음엔 사람 ✓ 만 셌다. 그건 두 가지가 틀렸다.
  ① **이미 있는 검증을 안 셌다.** 교차 대조(crosscheck)가 130모델에 있고 그중 73모델은
     일치율 99% 이상이다 — 기계가 표 인식과 **다른 경로로** 원문을 한 번 더 읽어 같은
     결과를 낸 것이다. 사람 손이 닿지 않았을 뿐 확인이 안 된 게 아니다.
  ② **사람 ✓ 의 단위가 틀렸다.** 6,777행을 하나씩 찍으라는 건 말이 안 된다. 사람은
     "이 쪽 표를 통째로 맞춰 본다" — 그래서 화면의 ✓ 도 구역 단위로 찍게 고쳤다.

등급 (믿음의 세기 순)
  human      사람이 화면에서 직접 대조 (point-verified.json) — 가장 세다
  sample     사람이 원문 보고 4~6쌍 표본 확인 (known-good.json)
  machine    교차 대조 99%+ — 다른 경로로 읽어 같은 결과
  weak       교차 대조 90% 미만 — **다시 봐야 한다**
  blind      대조 자체가 불가(문서가 개요/상세 열이 달라 두 번 못 읽는다) 또는 없음
"""
import argparse
import collections
import datetime
import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
STORE = os.path.join(DATA, "point-verified.json")

HEAD = ("사람이 point-verify.html 에서 원문 쪽과 눈으로 대조한 포인트. "
        "누적이며 지우지 않는다. 넣기: python mappings.py --import <내려받은파일>")


def load_store():
    if not os.path.exists(STORE):
        return collections.OrderedDict([("_설명", HEAD),
                                        ("검수", collections.OrderedDict())])
    return json.load(io.open(STORE, encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)


def save_store(doc):
    doc["_설명"] = HEAD
    io.open(STORE, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


def models():
    out = collections.OrderedDict()
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = json.load(io.open(f, encoding="utf-8"))
        out[m["id"]] = m
    return out


def n_points(m):
    n = sum(len(i.get("points") or []) for i in (m.get("interfaces") or []))
    return n + len(m.get("points") or [])


def grade(mid, m, human, sample):
    """이 모델이 어느 세기로 확인됐나 → (등급, 한 줄 사유)."""
    if mid in human:
        k = sum(len(v) for v in human[mid].values())
        return "human", "사람이 화면에서 %d점 대조" % k
    if mid in sample:
        return "sample", "사람이 원문 보고 %d쌍 표본 확인" % len(sample[mid])
    c = m.get("crosscheck") or {}
    if isinstance(c, dict) and c.get("rate") is not None:
        r = c["rate"]
        if r >= 0.99:
            return "machine", "교차 대조 %.1f%% (%d점)" % (r * 100, c.get("both") or 0)
        if r >= 0.90:
            return "weak", "교차 대조 %.1f%% — 차이 %d건" % (r * 100, len(c.get("diff") or []))
        return "weak", "교차 대조 %.1f%% — 다시 봐야 한다" % (r * 100)
    if isinstance(c, dict) and c.get("unverifiable"):
        return "blind", str(c["unverifiable"])[:60]
    return "blind", "교차 대조도 사람 확인도 없다"


ORDER = [("human", "사람이 직접 대조"), ("sample", "사람이 표본 확인"),
         ("machine", "기계 교차 대조 99%+"), ("weak", "교차 대조 약함 — 다시 봐야"),
         ("blind", "확인 없음")]


def status():
    M = models()
    human = (load_store().get("검수") or {})
    kg = json.load(io.open(os.path.join(DATA, "known-good.json"), encoding="utf-8"))
    sample = {k: v for k, v in kg.items() if not k.startswith("_")}
    out = collections.OrderedDict()
    for mid, m in M.items():
        g, why = grade(mid, m, human, sample)
        out[mid] = (g, why, n_points(m))
    return out


def report(detail=False):
    st = status()
    by = collections.defaultdict(list)
    for mid, (g, why, n) in st.items():
        by[g].append((n, mid, why))
    tot = len(st)
    totpts = sum(v[2] for v in st.values())
    print("■ 확인 세기 — 모델 %d건 · 포인트 %d점" % (tot, totpts))
    for g, label in ORDER:
        rows = sorted(by.get(g) or [], reverse=True)
        pts = sum(r[0] for r in rows)
        print("   %-22s 모델 %3d (%2.0f%%) · 포인트 %6d"
              % (label, len(rows), 100.0 * len(rows) / tot, pts))
        if detail:
            for n, mid, why in rows[:40]:
                print("        %6d점  %-46s %s" % (n, mid[:46], why[:44]))
    print()
    weak = len(by.get("weak") or []) + len(by.get("blind") or [])
    print("사람 손이 필요한 것 %d건 — 교차 대조가 약하거나 없는 모델이다." % weak)
    print("  point-verify.html 에서 구역 머리의 '이 구역 다 봤다' 로 찍고")
    print("  '검수 내려받기' → python mappings.py --import <파일>")


def do_import(path):
    src = json.load(io.open(path, encoding="utf-8"))
    got = src.get("검수") or {}
    if not got:
        raise SystemExit("검수 기록이 없는 파일이다 — 화면의 '검수 내려받기' 로 받은 것인가?")
    today = datetime.date.today().isoformat()
    doc = load_store()
    store = doc.setdefault("검수", collections.OrderedDict())
    added = seen = 0
    for mid, ifaces in got.items():
        mrec = store.setdefault(mid, collections.OrderedDict())
        for iface, pts in ifaces.items():
            irec = mrec.setdefault(iface, collections.OrderedDict())
            for p in pts:
                key = p.get("이름") or p.get("번호") or ""
                if not key:
                    continue
                seen += 1
                if key in irec:
                    irec[key]["최근확인"] = today
                else:
                    irec[key] = collections.OrderedDict([
                        ("번호", p.get("번호") or ""), ("쪽", p.get("쪽") or ""),
                        ("PDF쪽", p.get("PDF쪽") or ""),
                        ("첫확인", today), ("최근확인", today)])
                    added += 1
    save_store(doc)
    print("넣었다 — 새로 %d점 · 다시 본 것 %d점" % (added, seen - added))
    print("  → %s" % os.path.relpath(STORE, HERE))
    print()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="imp", metavar="파일")
    ap.add_argument("--models", action="store_true", help="모델별로 자세히")
    a = ap.parse_args(argv)
    if a.imp:
        do_import(a.imp)
    report(a.models)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
