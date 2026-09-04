# -*- coding: utf-8 -*-
"""취입 대조대 — review/point-verify.html

  PYTHONIOENCODING=utf-8 python verify_points.py
  PYTHONIOENCODING=utf-8 python verify_points.py --only ls-electric-h100-vfd
  PYTHONIOENCODING=utf-8 python verify_points.py --all        (쪽 그림이 커진다)
  PYTHONIOENCODING=utf-8 python verify_points.py --no-pages   (그림 없이 빠르게)

무엇을 대조하나
  **모델에 실제로 들어간 값**을 원문 쪽과 맞춘다. 원문에서 다시 뽑지 않는다 —
  뽑기와 취입 사이에서 잃은 것은 이 화면에서만 보인다.
  (원문에서 뽑은 것을 원문과 맞추는 쪽은 verify_lg.py 다. 목적이 다르다.)

왜 트리인가
  벤더가 늘면 판이 수십 개가 된다. 설비 → 벤더 → 모델 → 판으로 갈라 두면
  "지금 이 설비에서 뭘 봐야 하나"가 화면에 남는다.

⚠ 인쇄 쪽번호 ↔ PDF 쪽은 **셈하지 않고 찾는다.**
  모델에 남은 것은 원문이 인쇄한 쪽번호다. 'PDF 쪽 = 인쇄 쪽 + 8' 같은 오프셋은
  문서마다 다르고 개정판에서 조용히 어긋난다(사용자가 실제로 이 어긋남을 먼저 봤다).
  여기서는 ① 머리글의 인쇄 쪽번호로 후보를 잡고 ② 그 쪽 글자 안에 포인트 이름이
  실제로 있는지 확인한다. 안 맞으면 문서 전체에서 이름으로 찾고 어긋남을 보고한다.

⚠ 산출물은 원문 쪽 그림을 담아 gitignore 된다. 이 스크립트가 정본이다.
"""
import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CATALOG = os.path.join(HERE, "..", "08-equip-spec-tag-catalog.md")
OUT = os.path.join(HERE, "..", "review", "point-verify.html")
sys.path.insert(0, HERE)
import verify_ui as UI  # noqa: E402

# 이 대조대가 기본으로 담는 것 = 지금 손으로 몰아 가는 **국내 벤더 취입분**.
# 157모델을 전부 담으면 쪽 그림이 수백 MB 가 된다 — 필요하면 --only · --all.
DOMESTIC = ("ingest_lg", "ingest_ls")


def equip_names():
    """설비계열 한글 이름을 **기준 문서에서 읽는다** — 두 벌을 만들지 않는다.

    08-equip-spec-tag-catalog.md 의 절 번호가 곧 계열 번호다: '# 15. 인버터 (VFD)' → e15.
    """
    out = {}
    if os.path.exists(CATALOG):
        for line in io.open(CATALOG, encoding="utf-8"):
            m = re.match(r"^#\s+(\d+)\.\s+(.+?)\s*$", line)
            if m:
                out["e" + m.group(1)] = m.group(2)
    return out


def addr_rules():
    """주소를 넣어야 인스턴스가 정해지는 판(LG) 의 제품유형 표.

    ⚠ 여기서 숫자를 다시 적지 않는다 — ingest_lg.IFACE 와 verify_lg.KO 가 정본이다.
       두 벌이 되면 한쪽만 고쳐졌을 때 조용히 어긋난다.
    """
    try:
        import ingest_lg
        import verify_lg
    except Exception:
        return {}
    out = {}
    for _en, (ko, ptype) in verify_lg.KO.items():
        if ko in ingest_lg.IFACE:
            out[ingest_lg.IFACE[ko][0]] = ptype
    return out


LG_HELP = ('이름 끝 <b>_XXX</b> 는 원문이 <b>(XXX : Unit address)</b> 라고 밝힌 유닛 '
           '주소다. 주소를 넣으면 실제 이름과 BACnet 인스턴스 번호가 나온다.')
LG_RULE = ('instance = 제품유형×0x10000 + Device×0x1000 + Product×0x100 + Point')


def shorten(nodes):
    """형제들이 똑같이 되풀이하는 앞머리를 트리에서 뗀다.

    LG 판 여섯이 전부 'BACnet Point List : …' 로 시작해 트리에서 정작 다른 부분
    (실내기·ODU·AWHP)이 잘려 나갔다. 뗀 앞머리는 구역 머리글에 그대로 남고,
    노드에는 full 로 실어 마우스를 올리면 원래 이름이 보인다.
    """
    labs = [n["label"] for n in nodes]
    if len(labs) < 2:
        return
    pre = os.path.commonprefix(labs)
    cut = max([pre.rfind(c) + 1 for c in (":", "-", "·", " ")] or [0])
    if cut < 4 or any(len(l) - cut < 2 for l in labs):
        return
    for n in nodes:
        n["full"] = n["label"]
        n["label"] = n["label"][cut:].strip()


def load_models(only, take_all):
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = json.load(io.open(f, encoding="utf-8"))
        if not (m.get("interfaces") or []):
            continue
        if only:
            if m["id"] not in only:
                continue
        elif not take_all and m.get("extractor") not in DOMESTIC:
            continue
        out.append(m)
    return out


def row_of(p):
    """모델 포인트 → 화면 행. 없는 값은 빼면 그 열이 접힌다."""
    c = p.get("common") or {}
    bac = (p.get("blocks") or {}).get("bacnet") or {}
    src = (p.get("provenance") or {}).get("sourceColumns") or {}
    inst = bac.get("instance")
    # ⚠ 번호 칸은 **원문이 인쇄한 그대로** 쓴다. LS H100 은 계열마다 1부터 다시
    #    세는데(BACnet 인스턴스는 타입별로 매겨진다) 숫자만 '9' 로 보이면
    #    같은 쪽의 AI9 인지 AV9 인지 알 수 없다. 더구나 AI9 의 **이름이 'AI1'**
    #    (드라이브 아날로그 입력 단자 1번)이라 숫자만 보여 주면 반드시 헷갈린다.
    n = src.get("Instance ID") or src.get("Point No.") or (
        str(inst) if inst is not None else "")
    st = ", ".join("%s=%s" % (s.get("code"), s.get("label"))
                   for s in (c.get("states") or []))
    r = {"n": n, "t": bac.get("objectType") or "", "nm": c.get("name") or ""}
    if inst is not None:
        r["i"] = inst
    for k, v in (("u", c.get("unitSIRaw") or c.get("unitIPRaw")),
                 ("rw", c.get("readWrite")), ("d", c.get("note")), ("s", st)):
        if v:
            r[k] = v
    # ⚠ 화면이 원문 칸을 **하나도 숨기지 않는다.** 스키마 필드로 못 올린 것
    #    (H100 의 'Range (REAL)'·'Active / Inactive Text', LG 의 범위형 'Unit')이
    #    화면에서 사라지면 대조가 안 된다 — 대조대의 존재 이유가 그것이다.
    #    어떤 칸이 이미 쓰였는지는 **값으로** 가른다(벤더마다 열 이름이 다르다).
    #    ⚠ 빈칸만 다른 값은 같은 값으로 본다. 안 그러면 조판 아티팩트를 지우기 전
    #       원문 이름('StartStopCommand_ XXX')이 91행에 덧붙어 화면이 시끄러워진다 —
    #       그건 빠진 값이 아니라 지운 자국이고, 그 기록은 모델에 이미 남아 있다.
    flat = lambda s: re.sub(r"\s+", "", str(s))
    used = {flat(x) for x in (r.get("n"), r.get("t"), r.get("nm"), r.get("d"),
                              r.get("u"), r.get("rw")) if x}
    used |= {flat(s.get("label")) for s in (c.get("states") or [])}
    extra = {k: v for k, v in src.items() if v and flat(v) not in used}
    if extra:
        r["x"] = extra
    return r


# 화면 열 — 값이 하나라도 있는 것만 세운다(빈 열은 눈만 어지럽힌다)
DERIVED = [("n", "번호"), ("t", "타입"), ("nm", "이름"), ("u", "단위"),
           ("rw", "R/W"), ("s", "상태 TEXT"), ("d", "설명")]


def columns(rows, addr, manypages):
    """구역의 열 목록. 원문 칸은 **원문 열 이름 그대로** 제 열을 갖는다.

    ⚠ 설명 칸 밑에 덧붙이지 않는다 — 원문 표와 눈으로 맞추려면 칸이 칸끼리
       세로로 서 있어야 한다.
    """
    cols = [{"k": k, "h": h} for k, h in DERIVED if any(r.get(k) for r in rows)]
    if addr:
        cols.append({"k": "inst", "h": "인스턴스"})
    seen = []
    for r in rows:
        for k in (r.get("x") or {}):
            if k not in seen:
                seen.append(k)
    cols += [{"k": "x:" + k, "h": k} for k in seen]
    if manypages:
        cols.append({"k": "pg", "h": "쪽"})
    return cols


def resolve_pages(doc, wanted, names_by_printed):
    """인쇄 쪽번호 → PDF 쪽. 머리글로 후보를 잡고 **글자로 확인한다.**

    돌려주는 것: (map, 어긋남 보고)
    """
    flat, head = {}, {}
    for i in range(doc.page_count):
        page = doc[i]
        flat[i + 1] = re.sub(r"\s+", "", page.get_text())
        head[i + 1] = UI.printed_no(page, None)

    def hits(pdf, printed):
        f = flat[pdf]
        names = names_by_printed.get(printed) or []
        if not names:
            return 0
        return sum(1 for nm in names if re.sub(r"\s+", "", nm) in f)

    out, warn = {}, []
    for printed in sorted(wanted):
        cand = [p for p in flat if head[p] == printed]
        best = max(cand, key=lambda p: hits(p, printed)) if cand else None
        need = max(1, len(names_by_printed.get(printed) or []) // 2)
        if best is None or hits(best, printed) < need:
            # 머리글이 못 맞혔다 — 문서 전체에서 이름으로 찾는다(다른 경로).
            alt = max(flat, key=lambda p: hits(p, printed))
            if hits(alt, printed) >= need:
                warn.append("인쇄 %s쪽: 머리글 후보 %s → 글자로 찾은 PDF %d쪽"
                            % (printed, cand or "없음", alt))
                best = alt
        if best:
            out[printed] = best
        else:
            warn.append("인쇄 %s쪽: PDF 쪽을 못 찾았다" % printed)
    return out, warn


def main(argv):
    import fitz
    take_all = "--all" in argv
    no_pages = "--no-pages" in argv
    only = set()
    if "--only" in argv:
        only = {a for a in argv[argv.index("--only") + 1:] if not a.startswith("-")}

    models = load_models(only, take_all)
    if not models:
        raise SystemExit("담을 모델이 없다 — --only 이름을 확인하거나 --all")
    scope = ("고른 모델만" if only else
             "카탈로그 전체" if take_all else
             "국내 벤더 취입분만 (%s)" % " · ".join(DOMESTIC))

    enames = equip_names()
    ptypes = addr_rules()
    tree, sections, pages, warns = collections.OrderedDict(), [], {}, []
    total = 0

    for m in models:
        eq = m.get("equipId") or "?"
        vendor = m.get("vendor") or "?"
        eid, vid = eq, "%s|%s" % (eq, vendor)
        mid = "%s|%s" % (vid, m["id"])
        path = os.path.join(DATA, "raw", m.get("sourceDoc") or "")
        doc = fitz.open(path) if os.path.exists(path) else None
        if doc is None:
            warns.append("%s: 원문이 없다(%s) — 쪽 그림 없이 담는다"
                         % (m["id"], m.get("sourceDoc")))

        # 판별로 인쇄 쪽 → 포인트
        want, names = set(), {}
        for iface in m["interfaces"]:
            for p in iface.get("points") or []:
                pr = (p.get("provenance") or {}).get("sourcePage")
                if pr is None:
                    continue
                want.add(pr)
                names.setdefault(pr, []).append((p.get("common") or {}).get("name") or "")
        pdfmap, w = ({}, []) if doc is None else resolve_pages(doc, want, names)
        warns += ["%s: %s" % (m["id"], x) for x in w]

        # 분류(cat)를 모델 줄에 늘 붙인다 — 계열(eN) 이름만으로는 어긋남이 안 보인다.
        # 실제로 LG 게이트웨이는 계열 e5(공조기)인데 분류가 HVAC.AIR.VRF 다.
        label = "%s · %s" % ((m.get("model") or m.get("name") or m["id"]), m.get("cat") or "?")
        mnode = {"id": mid, "label": label, "count": 0, "children": []}
        for iface in m["interfaces"]:
            iid = "%s|%s" % (mid, iface["id"])
            # ⚠ 쪽으로 가르지 않는다. 원문의 한 표가 쪽을 넘어 이어질 뿐인데 쪽으로
            #    자르면 같은 표가 여러 토막이 된다(LS H100 은 AI 27점이 세 쪽에 걸친다).
            #    문서가 스스로 절을 나눠 뒀으면(common.group) 그것을 따르고,
            #    안 나눠 뒀으면 판 하나를 한 구역으로 둔다. 쪽은 **행마다** 붙는다.
            by = collections.OrderedDict()
            for p in iface.get("points") or []:
                by.setdefault((p.get("common") or {}).get("group") or "", []).append(p)
            n = 0
            for gi, (group, pts) in enumerate(by.items()):
                rows, span = [], []
                for p in pts:
                    printed = (p.get("provenance") or {}).get("sourcePage")
                    pdf = pdfmap.get(printed)
                    key = "%s#%s" % (m["id"], pdf)
                    r = row_of(p)
                    r["pg"] = printed
                    r["pdf"] = pdf or "?"
                    r["pk"] = key
                    rows.append(r)
                    if printed not in span:
                        span.append(printed)
                    if doc is not None and pdf and not no_pages and key not in pages:
                        pages[key] = (m["id"], pdf, path)
                span = sorted(x for x in span if x is not None)
                sec = {
                    "cols": columns(rows, iface["id"] in ptypes
                                    and m.get("extractor") == "ingest_lg",
                                    len(span) > 1),
                    "id": "%s/%s/%s" % (m["id"], iface["id"], group or gi),
                    "node": iid,
                    "path": [m.get("model") or m["id"], iface.get("label") or iface["id"]]
                            + ([group] if group else []),
                    "doc": m.get("sourceDoc") or "",
                    "span": ("%d–%d" % (span[0], span[-1])) if len(span) > 1
                            else (str(span[0]) if span else "?"),
                    "points": rows,
                }
                if iface["id"] in ptypes and m.get("extractor") == "ingest_lg":
                    sec["addr"] = {"label": "유닛 주소 XXX", "ptype": ptypes[iface["id"]],
                                   "rule": LG_RULE, "help": LG_HELP}
                sections.append(sec)
                n += len(rows)
            mnode["children"].append({"id": iid, "label": iface.get("label") or iface["id"],
                                      "count": n, "children": []})
            mnode["count"] += n
            total += n

        shorten(mnode["children"])
        e = tree.setdefault(eid, {"id": eid, "count": 0,
                                  "label": ("%s %s" % (eid, enames.get(eid, ""))).strip(),
                                  "children": collections.OrderedDict()})
        v = e["children"].setdefault(vid, {"id": vid, "label": vendor, "count": 0,
                                           "children": []})
        v["children"].append(mnode)
        v["count"] += mnode["count"]
        e["count"] += mnode["count"]
        if doc is not None:
            doc.close()

    # 쪽 그림은 문서별로 한 번만 연다
    imgs = {}
    if not no_pages:
        bydoc = collections.defaultdict(dict)
        for key, (mid_, pdf, path) in pages.items():
            bydoc[path][pdf] = key
        for path, want in bydoc.items():
            doc = fitz.open(path)
            got = UI.page_images(doc, want.keys())
            for pdf, key in want.items():
                imgs[key] = got[pdf]
            doc.close()

    payload = {
        "title": "취입 대조대",
        # ⚠ 범위를 제목 옆에 박는다. 범위 없는 숫자는 전체로 읽힌다 —
        #    이 화면은 카탈로그 157모델이 아니라 **여기 적힌 것만** 담는다.
        "scope": scope,
        "subtitle": "%s — 모델 %d · 판 %d · 오브젝트 %d점"
                    % (scope, len(models), sum(len(m["interfaces"]) for m in models), total),
        "storeKey": "point-verify/v1",
        "total": total,
        "tree": [dict(e, children=list(e["children"].values())) for e in tree.values()],
        "sections": sections,
        "pages": imgs,
        "hint": ('왼쪽은 <b>모델에 실제로 들어간 값</b>이다(원문에서 다시 뽑은 것이 아니다). '
                 '<kbd>↑</kbd><kbd>↓</kbd> 행 이동 · <kbd>Space</kbd> 확인 · '
                 '휠/<kbd>+</kbd><kbd>−</kbd> 확대 · <kbd>0</kbd> 맞춤 · 더블클릭 확대'),
    }
    mb = UI.write(payload, OUT)

    for e in payload["tree"]:
        print("■ %s  %d점" % (e["label"], e["count"]))
        for v in e["children"]:
            for mo in v["children"]:
                print("   %-14s %-34s %4d점" % (v["label"], mo["label"][:34], mo["count"]))
                for i in mo["children"]:
                    print("      · %-28s %4d점" % (i["label"][:28], i["count"]))
    if warns:
        print("\n⚠ 쪽 맞추기:")
        for w in warns:
            print("   " + w)
    print("\n→ %s  (%.2f MB · 쪽 그림 %d장)"
          % (os.path.relpath(OUT, HERE), mb, len(imgs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
