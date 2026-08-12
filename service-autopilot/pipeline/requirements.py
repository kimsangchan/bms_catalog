# -*- coding: utf-8 -*-
"""요구 항목 — 문서를 열기 전에 '무엇을 뽑을지' 먼저 정하고, 그 기준으로만 채점한다.

왜 만들었나
  지금까지는 순서가 거꾸로였다. PDF 에서 표를 읽고 → 나온 걸 모아 → 나중에 시뮬레이터
  요구와 맞춰 봤다. 그 결과 두 가지가 동시에 일어났다.

    · 안 쓰는 값을 잔뜩 모았다 (치수·부속·배선)
    · 정작 필요한 값이 비었다 (기외정압 0% · 난방 2% · 최소외기량 0%)

  게다가 채점표 자체가 틀렸다. e5 요구 항목이 **한국식 맞춤 AHU** 기준(냉수코일 능력·
  코일 열수·가습 방식)이라, 냉수코일이 없는 RTU 8모델을 없는 부품으로 채점하고 있었다.
  matched 59 / missing 1,162 (4.6%) 라는 숫자는 그렇게 나왔다.

규칙 (data/equip-requirements.json 의 rules 와 같다)
  ① 요구 먼저 — 프로파일 없으면 수집·추출을 시작하지 않는다
  ② 쓰임 없으면 항목이 아니다 — usedBy·why 를 못 적으면 넣지 않는다
  ③ 하위형식이 다르면 다른 설비다 — RTU 와 AHU 는 계산식이 달라 프로파일을 나눈다
  ④ features 는 unit-schema.json 에 있는 id 만 — 빈 배열 = 사전 신설 과제
  ⑤ 채점은 이 파일 기준 — 여기 없는 값을 많이 뽑았다고 잘한 게 아니다

실행
  PYTHONIOENCODING=utf-8 python requirements.py --check           # 정의 자체 검사
  PYTHONIOENCODING=utf-8 python requirements.py --report          # 항목별 채움률
  PYTHONIOENCODING=utf-8 python requirements.py --report --profile e5.rtu
  PYTHONIOENCODING=utf-8 python requirements.py --gaps            # 비어 있는 필수 항목만
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REQ = os.path.join(DATA, "equip-requirements.json")
SCHEMA = os.path.join(DATA, "unit-schema.json")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def profiles():
    return load(REQ).get("profiles") or {}


def profile_for(model):
    """모델 → 프로파일 id. 하위형식(cat)이 먼저, 없으면 계열 기본.

    **결합 규칙은 이 함수 하나뿐이다.** data/equip-templates.json 등 다른 파일에
    catPrefix 를 다시 적지 않는다. 규칙이 두 벌이 되는 순간이 'RTU 를 냉수코일 AHU
    체크리스트로 채점'한 사고의 재현 조건이다 — datasets.py 가 이 함수를 부른다.

    catPrefix 는 문자열 하나 또는 문자열 목록이다. 목록을 허용한 이유:
    HVAC.AIR.SPLIT(직팽 스플릿)은 HVAC.AIR.RTU 접두에 안 걸리는데 계산식은 RTU 와
    같다. 프로파일을 하나 더 만들면 정격·템플릿이 또 한 벌 늘어난다.
    """
    cat = model.get("cat") or ""
    equip = model.get("equipId")
    best, best_len = None, -1
    for pid, p in profiles().items():
        m = p.get("match") or {}
        pre = m.get("catPrefix")
        pres = [pre] if isinstance(pre, str) else list(pre or [])
        hit = max((len(x) for x in pres if cat.startswith(x)), default=None)
        if hit is not None and hit > best_len:
            best, best_len = pid, hit
        elif not pres and p.get("equipId") == equip and best_len < 0:
            best, best_len = pid, 0
    return best


def models():
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        yield load(f)


def curated(model_id):
    p = os.path.join(DATA, "units", "%s.json" % model_id)
    if not os.path.exists(p):
        return []
    return load(p).get("units") or []


def field_values(unit):
    fl = unit.get("fields") or {}
    out = {}
    if isinstance(fl, dict):
        for k, v in fl.items():
            if isinstance(v, dict):
                v = v.get("value")
            if v not in (None, "", [], {}):
                out[k] = v
    return out


def check():
    """정의 자체가 성립하나 — 게이트용."""
    req = load(REQ)
    feats = set((load(SCHEMA).get("features") or {}).keys())
    errs, warns = [], []
    for pid, p in (req.get("profiles") or {}).items():
        seen = set()
        # 항목이 비면 조용히 통과한다 — 그러면 '요구가 없다'는 사실이 사라진다.
        # 프로파일을 결합 앵커로만 먼저 만든 경우(e5.ahu)를 경고로 계속 세워 둔다.
        if not (p.get("items") or []):
            warns.append("%s: 정격 요구 항목이 아직 없다 (규칙 ①) — %s"
                         % (pid, p.get("pending") or "사유 미기재"))
        for it in p.get("items") or []:
            if it["id"] in seen:
                errs.append("%s: 항목 id 중복 %s" % (pid, it["id"]))
            seen.add(it["id"])
            if not it.get("why"):
                errs.append("%s/%s: why 없음 (규칙 ②)" % (pid, it["id"]))
            if it.get("grade") != "참고" and not it.get("usedBy"):
                errs.append("%s/%s: usedBy 없음 (규칙 ②)" % (pid, it["id"]))
            bad = [f for f in (it.get("features") or []) if f not in feats]
            if bad:
                errs.append("%s/%s: 사전에 없는 feature %s (규칙 ④)"
                            % (pid, it["id"], ", ".join(bad)))
            # 격자·메타 항목은 형번당 스칼라가 아니다 — 사전에 넣을 것이 아니라
            # storage 에 보관 방식을 적는다. 그걸 '사전 신설 과제'로 세면 신호가 흐려진다.
            if not it.get("features") and not it.get("storage"):
                warns.append("%s/%s: 연결된 feature 없음 — 사전 신설 과제"
                             % (pid, it["id"]))
            if it.get("storage") and it.get("features"):
                errs.append("%s/%s: storage(격자·메타)와 features(스칼라)를 같이 쓸 수 없다"
                            % (pid, it["id"]))
    # 프로파일이 없는 설비
    have = set()
    for m in models():
        pid = profile_for(m)
        if pid:
            have.add(pid)
        else:
            warns.append("%s: 요구 프로파일 없음 (규칙 ①) — cat=%s"
                         % (m.get("id"), m.get("cat")))
    for e in errs:
        print("  오류 %s" % e)
    for w in warns[:20]:
        print("  경고 %s" % w)
    if len(warns) > 20:
        print("  … 경고 %d건 더" % (len(warns) - 20))
    print("오류 %d · 경고 %d" % (len(errs), len(warns)))
    return 1 if errs else 0


def report(only=None, gaps_only=False):
    ps = profiles()
    targets = {k: v for k, v in ps.items() if not only or k == only}
    if not targets:
        print("그런 프로파일이 없다: %s" % only)
        return 1
    for pid, p in targets.items():
        ms = [m for m in models() if profile_for(m) == pid]
        units = []
        for m in ms:
            units.extend(field_values(u) for u in curated(m["id"]))
        n = len(units)
        print("\n■ %s — %s" % (pid, p.get("title")))
        print("  모델 %d개 · 형번 확정본 %d건" % (len(ms), n))
        if p.get("energyModel"):
            print("  계산식:")
            for k, v in p["energyModel"].items():
                print("    %-9s %s" % (k, v))
        avail = ((availability().get("profiles") or {}).get(pid)
                 or {}).get("items") or {}
        print("  %-34s %-5s %-12s %-6s %s"
              % ("항목", "등급", "쓰임", "채움", "정량 가능성"))
        for it in p.get("items") or []:
            feats = it.get("features") or []
            if not feats:
                fill = -1
            elif n:
                fill = 100.0 * sum(
                    1 for u in units if any(f in u for f in feats)) / n
            else:
                fill = 0.0
            if gaps_only and it.get("grade") != "필수":
                continue
            if gaps_only and fill > 50:
                continue
            curve = bool(it.get("storage"))
            mark = ("격자·메타" if curve else
                    ("사전없음" if fill < 0 else ("%3.0f%%" % fill)))
            flag = ""
            if curve:
                flag = "  ← 스칼라 아님: %s" % it["storage"][:46]
            elif fill < 0:
                flag = "  ← 사전 신설 필요"
            elif it.get("grade") == "필수" and fill < 50:
                flag = "  ← 필수인데 비었다"
            av = avail.get(it["id"])
            note = ""
            if av:
                s = av["summary"]
                note = ("표 %d · 애매 %d · 불가 %d"
                        % (s["table"], s.get("weak", 0), s["notInTable"]))
                if not s["table"]:
                    note += "  ▣ 항목만 표시 (문서에 정량표 없음)"
            print("  %-34s %-5s %-12s %6s  %s%s"
                  % (it["name"][:34], it.get("grade"),
                     ",".join(it.get("usedBy") or []) or "—", mark, note, flag))
            if av and av["summary"]["table"]:
                for mid, v in av["models"].items():
                    if v["status"] == "table" and v.get("evidence"):
                        e = v["evidence"][0]
                        print("      뽑을 표: %s p%s — %s"
                              % (e["file"][:32], e["page"],
                                 (e["title"] or "(제목없음)")[:44]))
                for mid, v in av["models"].items():
                    if v["status"] == "not-in-table":
                        print("      ▣ %s — 정량표 없음, 값 비우고 항목만 남긴다"
                              % mid[:44])
            elif flag and it.get("sourceHint"):
                print("      찾을 곳: %s" % it["sourceHint"])
    return 0


# ── 정량 가능성 프로브 ────────────────────────────────────────────────
# 규칙: **표에서 정량값을 얻을 수 있는 것만 넣는다.** 필요하지만 못 구하는 항목은
# 값을 비워 두고 항목만 남긴다(사유와 함께). 본문 설명이나 팬 곡선 그래프에만 있는
# 값을 억지로 뽑으면 시뮬레이터가 그 숫자를 그대로 믿는다.
MIN_DIGITS = 40
MAX_PAGES_PER_DOC = 8
NUMCELL = None


def _term_re(t):
    import re
    return re.compile(r"(?<![a-z0-9])" + re.escape(t.lower()) + r"(?![a-z0-9])")


def _numericish(s):
    import re
    return bool(re.search(r"\d", s or ""))


def probe_item(models, item, source_pdfs):
    """이 항목이 '표에서 정량으로' 얻어지는가 — 모델별로 판정한다."""
    import fitz
    sys.path.insert(0, HERE)
    import specs as SP
    pats = [(t, _term_re(t)) for t in (item.get("searchTerms") or [])]
    if not pats:
        return {}
    out = {}
    for m in models:
        ev, seen_terms = [], set()
        for fname in source_pdfs(m):
            path = os.path.join(DATA, "raw", fname)
            try:
                doc = fitz.open(path)
            except Exception:
                continue
            pages = []
            for pi in range(doc.page_count):
                try:
                    txt = doc[pi].get_text().lower()
                except Exception:
                    continue
                hits = [t for t, p in pats if p.search(txt)]
                digits = sum(1 for c in txt if c.isdigit())
                if hits and digits >= MIN_DIGITS:
                    pages.append((len(hits), digits, pi, hits))
            pages.sort(reverse=True)
            for _h, _d, pi, hits in pages[:MAX_PAGES_PER_DOC]:
                page = doc[pi]
                try:
                    tabs = page.find_tables().tables
                except Exception:
                    continue
                for t in tabs:
                    try:
                        data = t.extract()
                    except Exception:
                        continue
                    cells = [SP._c(c) for r in data for c in r]
                    nums = sum(1 for c in cells if _numericish(c))
                    if nums < 6:
                        continue
                    cap = SP.caption(page, t.bbox) or ""
                    # 표가 '무엇에 대한 표인가'는 제목·머리글·첫 열이 정한다.
                    # 본문 칸에 낱말이 스쳐 지나간 것으로 정량 가능이라 하면
                    # 선적중량표가 '이코노마이저 표'가 되어 버린다(실측 오탐).
                    head = " ".join(
                        [cap] + [SP._c(c) for c in (data[0] if data else [])]
                        + [SP._c(r[0]) for r in data if r]).lower()
                    body = " ".join(cells).lower()
                    strong = [x for x, p in pats if p.search(head)]
                    weak = [x for x, p in pats if p.search(body)]
                    if strong or weak:
                        seen_terms.update(strong or weak)
                        if len(ev) < 4:
                            ev.append({
                                "file": fname, "page": pi + 1,
                                "title": cap[:70],
                                "terms": (strong or weak)[:4], "numCells": nums,
                                "where": "제목·머리글" if strong else "본문 칸만",
                                "strong": bool(strong),
                            })
                if len(ev) >= 4:
                    break
            doc.close()
            if len(ev) >= 4:
                break
        strong_ev = [e for e in ev if e["strong"]]
        if strong_ev:
            out[m["id"]] = {"status": "table", "evidence": strong_ev[:4],
                            "terms": sorted(seen_terms)}
        elif ev:
            out[m["id"]] = {
                "status": "weak", "evidence": ev[:4], "terms": sorted(seen_terms),
                "reason": "낱말이 표 본문 칸에만 있다 — 그 표의 주제가 아닐 수 있다. "
                          "사람이 원문을 봐야 한다",
            }
        else:
            out[m["id"]] = {
                "status": "not-in-table", "evidence": [],
                "reason": "낱말은 원문에 있으나 숫자 칸이 있는 표의 제목·머리글에서 "
                          "찾지 못했다 — 본문 서술이나 곡선 그래프일 수 있다",
            }
    return out


def probe(profile_id=None, out_path=None):
    import verify_req as VR          # source_pdfs 재사용
    ps = profiles()
    targets = {k: v for k, v in ps.items() if not profile_id or k == profile_id}
    if not targets:
        print("그런 프로파일이 없다: %s" % profile_id)
        return 1
    result = {"version": 1,
              "description": "요구 항목이 '표에서 정량으로' 얻어지는지 원문에서 확인한 결과. "
                             "not-in-table 은 값을 채우지 않고 항목만 남긴다.",
              "profiles": {}}
    for pid, p in targets.items():
        ms = [m for m in models() if profile_for(m) == pid]
        items = {}
        for it in p.get("items") or []:
            _rows, fill, _hit, _tot = _fill_of(ms, it)
            if fill >= 60 or it.get("grade") == "참고":
                continue
            print("  프로브: %s (채움 %.0f%%)" % (it["name"], fill))
            per = probe_item(ms, it, VR.source_pdfs)
            n_tab = sum(1 for v in per.values() if v["status"] == "table")
            n_weak = sum(1 for v in per.values() if v["status"] == "weak")
            items[it["id"]] = {
                "name": it["name"], "grade": it.get("grade"), "fill": round(fill, 1),
                "models": per,
                "summary": {"table": n_tab, "weak": n_weak,
                            "notInTable": len(per) - n_tab - n_weak},
                "verdict": ("정량 가능 — 추출 대상" if n_tab
                            else "정량 불가 — 항목만 표시"),
            }
            print("      정량 %d · 애매 %d · 불가 %d / %d 모델 → %s"
                  % (n_tab, n_weak, len(per) - n_tab - n_weak, len(per),
                     items[it["id"]]["verdict"]))
        result["profiles"][pid] = {"title": p.get("title"), "items": items}
    path = out_path or os.path.join(DATA, "requirement-availability.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("  %s" % os.path.normpath(path))
    return 0


def _fill_of(ms, item):
    feats = item.get("features") or []
    hit = tot = 0
    for m in ms:
        for u in curated(m["id"]):
            tot += 1
            if any(f in field_values(u) for f in feats):
                hit += 1
    return [], (100.0 * hit / tot if tot else 0.0), hit, tot


def availability():
    p = os.path.join(DATA, "requirement-availability.json")
    return load(p) if os.path.exists(p) else {"profiles": {}}


def main(argv):
    ap = argparse.ArgumentParser(description="설비 요구 항목")
    ap.add_argument("--check", action="store_true", help="정의 검사 (게이트)")
    ap.add_argument("--report", action="store_true", help="항목별 채움률")
    ap.add_argument("--gaps", action="store_true", help="비어 있는 필수 항목만")
    ap.add_argument("--probe", action="store_true",
                    help="빈 항목이 '표에서 정량으로' 얻어지는지 원문 확인")
    ap.add_argument("--profile", help="프로파일 하나만")
    a = ap.parse_args(argv)
    if a.probe:
        return probe(a.profile)
    if a.check:
        return check()
    if a.report or a.gaps:
        return report(a.profile, gaps_only=a.gaps)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
