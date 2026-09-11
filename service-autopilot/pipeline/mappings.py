# -*- coding: utf-8 -*-
"""검수 기록 — 사람이 원문과 눈으로 대조한 것을 저장소에 남긴다.

  PYTHONIOENCODING=utf-8 python mappings.py                    지금 상태
  PYTHONIOENCODING=utf-8 python mappings.py --import <파일>     화면에서 내려받은 것을 넣는다
  PYTHONIOENCODING=utf-8 python mappings.py --report           모델별 검수율

왜 있나
  `point-verify.html` 의 ✓ 표시는 여태 **그 브라우저 안에만** 남았다(localStorage).
  다른 PC 에서도, 다른 도구(Codex·Antigravity)에서도, 커밋에서도 안 보였다.
  그래서 "대조가 된 설비" 가 무엇인지 저장소가 알 길이 없었고, 템플릿 매칭과 등급이
  **검수 여부와 무관하게 158모델 전체**로 매겨졌다. 검수 안 된 152모델의 엉터리 매칭이
  등급의 '노출률' 을 끌어내리고, 그 낮은 숫자로 등급을 내리면 매칭을 고칠 이유가
  사라진다 — 순환이다. 그 고리를 끊으려면 **검수된 것이 무엇인지** 먼저 알아야 한다.

  정격 쪽은 이미 같은 문제를 겪고 골든 레코드로 풀었다(units.py 의 verified —
  "사람 확인, 동기화가 절대 덮지 않는다"). 이 파일은 그 방식을 **포인트 대조**에 옮기는
  첫 조각이다.

무엇을 기록하나
  "이 모델의 이 판에서 이 원문 점을 사람이 원문 쪽과 대조했다" — 그 사실뿐이다.
  ⚠ "이 점이 어느 템플릿 행이다" 는 **아직 아니다.** 그건 다음 조각이다
    (화면이 템플릿 행을 안 보여 주므로 화면부터 손봐야 한다).

규칙
  · **누적이다. 지우지 않는다.** 한 번 대조한 사실은 사라지지 않는다. 여러 사람이
    여러 번 내려받아 넣어도 합쳐진다.
  · 첫 확인일과 최근 확인일을 같이 남긴다 — 원문이 개정되면 다시 봐야 하므로
    "언제 본 것인가" 가 값이다.
  · 이름이 바뀐 점은 **지우지 않고 그대로 둔다.** 추출이 달라진 것인지 원문이 바뀐
    것인지 사람이 봐야 한다. --report 가 '지금 원문에 없는 점' 으로 보고한다.
"""
import argparse
import collections
import datetime
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
STORE = os.path.join(DATA, "point-verified.json")

HEAD = ("사람이 point-verify.html 에서 원문 쪽과 눈으로 대조한 포인트. "
        "누적이며 지우지 않는다. 넣기: python mappings.py --import <내려받은파일>")


def load():
    if not os.path.exists(STORE):
        return collections.OrderedDict([("_설명", HEAD), ("검수", collections.OrderedDict())])
    return json.load(io.open(STORE, encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)


def save(doc):
    doc["_설명"] = HEAD
    io.open(STORE, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


def models():
    out = {}
    for f in glob.glob(os.path.join(DATA, "models", "*.json")):
        m = json.load(io.open(f, encoding="utf-8"))
        out[m["id"]] = m
    return out


def point_names(m):
    """모델의 원문 점 이름 — 판별로."""
    out = collections.defaultdict(set)
    for i in m.get("interfaces") or []:
        for p in i.get("points") or []:
            out[i["id"]].add((p.get("common") or {}).get("name") or "")
    for p in m.get("points") or []:
        out["legacy"].add(p.get("name") or "")
    return out


def do_import(path):
    src = json.load(io.open(path, encoding="utf-8"))
    got = src.get("검수") or {}
    if not got:
        raise SystemExit("검수 기록이 없는 파일이다 — 화면의 '검수 내려받기' 로 받은 것인가?")
    today = datetime.date.today().isoformat()
    doc = load()
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
                    irec[key]["최근확인"] = today          # 다시 본 것은 날짜만 새로
                else:
                    irec[key] = collections.OrderedDict([
                        ("번호", p.get("번호") or ""),
                        ("쪽", p.get("쪽") or ""),
                        ("PDF쪽", p.get("PDF쪽") or ""),
                        ("첫확인", today), ("최근확인", today)])
                    added += 1
    save(doc)
    print("넣었다 — 새로 %d점 · 다시 본 것 %d점 (파일 안 %d점)"
          % (added, seen - added, seen))
    print("  → %s" % os.path.relpath(STORE, HERE))


def report():
    doc = load()
    store = doc.get("검수") or {}
    if not store:
        print("아직 검수 기록이 없다.")
        print("  point-verify.html 에서 행 왼쪽 동그라미를 눌러 대조를 표시하고,")
        print("  '검수 내려받기' 로 받은 파일을 --import 로 넣는다.")
        return
    M = models()
    rows, orphan = [], []
    for mid, ifaces in store.items():
        m = M.get(mid)
        have = point_names(m) if m else {}
        n = tot = 0
        for iface, pts in ifaces.items():
            n += len(pts)
            cur = have.get(iface) or set()
            tot += len(cur)
            for nm in pts:
                if cur and nm not in cur:
                    orphan.append((mid, iface, nm))
        rows.append((n, tot, mid, "없는 모델" if not m else ""))
    rows.sort(reverse=True)
    print("■ 검수된 모델 %d건 · 검수된 점 %d개"
          % (len(rows), sum(r[0] for r in rows)))
    for n, tot, mid, note in rows:
        pct = (" (%.0f%%)" % (100.0 * n / tot)) if tot else ""
        print("   %5d / %-5s %s  %-46s %s"
              % (n, tot or "?", pct.ljust(7), mid[:46], note))
    if orphan:
        print()
        print("⚠ 지금 원문에 없는 점 %d개 — 추출이 달라졌거나 원문이 개정된 것이다."
              % len(orphan))
        print("  지우지 않았다. 사람이 봐야 한다.")
        for mid, iface, nm in orphan[:10]:
            print("   %-40s %-14s %s" % (mid[:40], iface[:14], nm[:40]))
    print()
    print("전체 모델 %d건 중 검수된 것 %d건" % (len(M), len(rows)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="imp", metavar="파일",
                    help="화면에서 내려받은 검수 파일을 넣는다")
    ap.add_argument("--report", action="store_true", help="모델별 검수율")
    a = ap.parse_args(argv)
    if a.imp:
        do_import(a.imp)
        print()
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
