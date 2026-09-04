# -*- coding: utf-8 -*-
"""LG BACnet 오브젝트 목록 대조 화면 — review/lg-bacnet-verify.html

  PYTHONIOENCODING=utf-8 python verify_lg.py

**팝업을 쓰지 않는다.** 기존 검사대(ingest_jci.py)는 원문 쪽을 dialog 로 94vw x 92vh
띄워서, 뜨는 순간 뽑은 표가 가려졌다 — 값 대조는 둘을 **동시에** 봐야 되는 일이라
그 구조로는 눈이 왔다 갔다 한다. 여기서는 좌우 2단으로 나눠 둘 다 늘 보이게 하고,
행을 고르면 오른쪽이 그 쪽으로 따라간다.

⚠ 원문 표가 **전치돼 있다** — 행이 속성(Object Type·Object Name·Point No.)이고
   열이 포인트다. 세로로 세면 15점짜리 표가 10행으로 읽힌다.
⚠ 기기군은 **쪽 제목**('BACnet Point List : ODU')으로 정한다. 열 라벨보다 정확하고,
   제목이 없는 이어지는 쪽은 앞 제목을 승계한다.
⚠ 산출물은 쪽 그림을 담아 gitignore 된다. 이 스크립트가 정본이다 —
   원문은 대장에 있으므로 collect.py --run lg-bacnet-gateway 로 어디서든 다시 받는다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SRC_ID = "lg-bacnet-gateway"
OUT = os.path.join(HERE, "..", "review", "lg-bacnet-verify.html")
sys.path.insert(0, HERE)
import verify_ui as UI  # noqa: E402  — 화면 틀은 한 벌만 둔다

# 표가 실린 쪽. 쪽 제목이 기기군을 정하고, 제목 없는 쪽은 앞 제목을 승계한다.
PAGES = [34, 35, 36, 38, 39, 41, 42, 43, 44, 46, 47, 48, 49]
# 기기군 → (한글 이름, 제품유형). 제품유형은 원문 50쪽이 못 박았다:
#   "Product Type(Indoor:0, Vent:1, AHU:2, ODU:3, AWHP:4, GENERAL:5)"
#   "Device : Group of Product units(16EA)"
# 그래서 instance = 제품유형*0x10000 + Device*0x1000 + Product*0x100 + Point 이고
# 이름 끝 _XXX(= Unit address) = Device*16 + Product 다.
# 원문 50~52쪽 예시 42행에 맞춰 봤다 — 42/42 일치.
# ⚠ 이름은 원문 낱말만 쓴다. 원문은 HRV 가 아니라 **ERV** 라고 쓴다(5쪽 장치 목록).
KO = {"Indoor Unit": ("실내기", 0), "Ventilation": ("환기(ERV)", 1),
      "AHU": ("공조기(AHU)", 2), "ODU": ("실외기(ODU)", 3),
      "AWHP": ("AWHP", 4), "GENERAL": ("게이트웨이 공통", 5)}


def ledger_entry():
    """대장에서 원문을 찾는다 — 폴더를 훑으면 그 PC 에만 묶인다."""
    led = json.load(io.open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    for url, v in led.items():
        if v.get("source") == SRC_ID and v.get("file"):
            return url, v
    raise SystemExit("대장에 %s 가 없다 — 먼저 collect.py --run %s" % (SRC_ID, SRC_ID))


def printed_no(page, fallback):
    """머리글의 인쇄 쪽번호. 이 문서는 PDF 쪽 - 8 이지만 **가정하지 않고 읽는다** —
    개정판에서 앞표지 장수가 바뀌면 오프셋이 조용히 틀린다."""
    for line in page.get_text().splitlines()[:4]:
        s = line.strip()
        if s.isdigit() and 1 <= int(s) <= 999:
            return int(s)
    return fallback


def ident(s, txt):
    """오브젝트 이름의 조판 아티팩트를 지운다 — 빈칸 하나하나를 **원문에 물어본다.**

    ⚠ re.sub(r"\\s+", " ") 로 뭉개면 안 된다. 그렇게 했다가 165점 중 43점의 이름이
      'StartStopCommand_ XXX' 가 됐다 — 원문에 없는 빈칸이다.
    ⚠ 그렇다고 빈칸을 전부 지워도 안 된다. 원문이 정말 띄어 쓰는 이름이 있다.
      쪽 글자흐름을 세어 갈랐다(표 인식이 아닌 경로):
        '_XXX'                   붙음 236회 · **빈칸 0회** · 줄바꿈 34회 → 조판이다
        'Filter Sign'            빈칸 14회 · 줄바꿈 0회                 → 원문의 빈칸이다
        'InverterDischarge Temp' 빈칸  0회 · 줄바꿈 2회                 → 조판이다
    ⚠ 표 인식(find_tables)은 줄바꿈을 이미 빈칸으로 바꿔 놓아 셀만 봐서는 못 가른다.
      그래서 같은 쪽의 **글자흐름**에서 이름을 다시 찾아 빈칸 자리의 진짜 구분자를 본다.
      한 쪽에 여러 번 나오면 많이 나온 쪽을 따른다.
      원문 그대로는 provenance.sourceColumns['Object Name'] 에 남는다(artifactCleanupFirst).
    """
    toks = [t for t in s.split() if t]
    if len(toks) < 2:
        return "".join(toks)
    hits = list(re.finditer("(\\s*)".join(map(re.escape, toks)), txt))
    if not hits:
        return s.strip()
    out = toks[0]
    for i, t in enumerate(toks[1:]):
        joined = sum(1 for h in hits if "\n" in h.group(i + 1) or not h.group(i + 1))
        out += ("" if joined * 2 > len(hits) else " ") + t
    return out


def prose(s):
    """설명문은 반대다 — 줄바꿈이 낱말 사이를 자른 것이라 빈칸으로 바꾼다."""
    return re.sub(r"\s+", " ", s).strip()


def row_of(rows, key):
    for r in rows:
        if r and str(r[0] or "").strip().startswith(key):
            return r
    return None


def extract(doc):
    """전치된 표에서 포인트를 뽑는다 — 열 하나가 포인트 하나다."""
    group_of, cur = {}, None
    for p in PAGES:
        m = re.search(r"BACnet Point List\s*:?\s*([^\n]*)", doc[p - 1].get_text())
        if m and m.group(1).strip():
            cur = m.group(1).strip()
        group_of[p] = cur

    tables = []
    for p in PAGES:
        flow = doc[p - 1].get_text()         # 빈칸/줄바꿈을 가를 근거는 여기 있다
        for t in doc[p - 1].find_tables().tables:
            rows = t.extract()
            ot, on = row_of(rows, "Object Type"), row_of(rows, "Object Name")
            cm, pn = row_of(rows, "Control/monitoring"), row_of(rows, "Point No.")
            txt = [row_of(rows, "Text-%d" % i) for i in range(6)]
            if not (ot and on and pn):
                continue
            pts = []
            for c in range(len(pn)):
                num = str(pn[c] or "").strip()
                name = (str(on[c]) if c < len(on) else "").strip()
                if not num.isdigit() or not name or name in ("-", "None"):
                    continue
                states = []
                for i, tr in enumerate(txt):
                    v = (str(tr[c]).strip() if tr and c < len(tr) else "")
                    if v and v not in ("None", "-", ""):
                        states.append("%d=%s" % (i, v))
                pts.append({"no": int(num), "name": ident(name, flow), "nameRaw": name,
                            "type": (str(ot[c]).strip() if c < len(ot) else ""),
                            "desc": prose(str(cm[c]).strip()) if cm and c < len(cm) else "",
                            "states": ", ".join(states)})
            if pts:
                ko, ptype = KO.get(group_of[p], (group_of[p] or "?", None))
                tables.append({"page": p, "printed": printed_no(doc[p - 1], p),
                               "group": ko, "ptype": ptype, "points": pts})
    return tables


def main():
    import fitz
    url, meta = ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, SRC_ID))
    doc = fitz.open(path)

    tables = extract(doc)
    total = sum(len(t["points"]) for t in tables)
    imgs = UI.page_images(doc, {t["page"] for t in tables})
    pages = {str(p): v for p, v in imgs.items()}

    # 기기군 하나가 한 구역이다 — 쪽으로 자르면 같은 표가 토막난다. 쪽은 행마다 붙는다.
    order, byg = [], {}
    for t in tables:
        if t["group"] not in byg:
            order.append(t["group"])
            byg[t["group"]] = []
        byg[t["group"]].append(t)

    tree, sections = [], []
    for g in order:
        ts = byg[g]
        rows, span = [], []
        for t in ts:
            for p in t["points"]:
                rows.append({"n": str(p["no"]), "t": p["type"], "nm": p["name"],
                             "d": p["desc"], "s": p["states"],
                             "pg": t["printed"], "pdf": t["page"], "pk": str(t["page"])})
            if t["printed"] not in span:
                span.append(t["printed"])
        span = sorted(span)
        tree.append({"id": g, "label": g, "count": len(rows), "children": []})
        sections.append({
            "id": g, "node": g, "path": [g], "doc": meta["file"],
            "span": ("%d–%d" % (span[0], span[-1])) if len(span) > 1 else str(span[0]),
            "addr": {"label": "유닛 주소 XXX", "ptype": ts[0]["ptype"],
                     "rule": "instance = 제품유형×0x10000 + Device×0x1000 + "
                             "Product×0x100 + Point",
                     "help": "이름 끝 <b>_XXX</b> 는 원문이 <b>(XXX : Unit address)</b> 라고 "
                             "밝힌 유닛 주소다. 주소를 넣으면 실제 이름과 BACnet 인스턴스 "
                             "번호가 나온다."},
            "points": rows,
        })

    mb = UI.write({
        "title": "LG BACnet 추출 대조대",
        "scope": "원문에서 뽑은 것을 원문과 맞춘다",
        "subtitle": "%s · sha %s… · %d점" % (meta["file"], meta.get("sha256", "")[:10], total),
        "storeKey": "lg-bacnet-verify/v1",
        "total": total, "tree": tree, "sections": sections, "pages": pages,
        "hint": "왼쪽은 <b>원문에서 방금 뽑은 것</b>이다(모델에 들어간 값이 아니다 — "
                "그쪽은 verify_points.py). 원문 표가 눕혀 인쇄돼 있어 가로로 돌려 보여 준다. "
                "<kbd>↑</kbd><kbd>↓</kbd> 행 이동 · <kbd>Space</kbd> 확인 · "
                "휠/<kbd>+</kbd><kbd>−</kbd> 확대 · <kbd>0</kbd> 맞춤",
    }, OUT)

    print("표 %d개 · 포인트 %d점 · 쪽 그림 %d장" % (len(tables), total, len(imgs)))
    for s in sections:
        print("   %-14s %3d점  원문 %s쪽" % (s["path"][0], len(s["points"]), s["span"]))
    print("→ %s  (%.2f MB)" % (os.path.relpath(OUT, HERE), mb))


if __name__ == "__main__":
    main()
