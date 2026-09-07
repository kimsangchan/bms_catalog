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
import schema as SC  # noqa: E402  — 빈 값 어휘의 정본
import verify_ui as UI  # noqa: E402

# 이 대조대가 기본으로 담는 것 = 지금 손으로 몰아 가는 **국내 벤더 취입분**.
# 157모델을 전부 담으면 쪽 그림이 수백 MB 가 된다 — 필요하면 --only · --all.
DOMESTIC = ("ingest_lg", "ingest_lg_ahu", "ingest_ls", "ingest_samsung")
# extractor 로만 고르면 **정격은 손으로, 오브젝트는 취입기로** 채운 모델이 빠진다.
# Danfoss FC 101 이 그랬다 — extractor 는 'manual'(정격 이야기)인데 판은 취입기가 세웠다.
# 그래서 모델 id 로도 지목한다. 여기 적힌 것은 지금 현장 때문에 들여다보는 것들이다.
FOCUS_MODELS = ("danfoss-fc-101",)


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
        elif not take_all and (m.get("extractor") not in DOMESTIC
                               and m["id"] not in FOCUS_MODELS):
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
    # Modbus 판은 인스턴스가 없다 — 원문이 인쇄한 **주소**가 그 자리다
    # ('0h0009' · '00001'). 비워 두면 번호 칸이 통째로 빈다(실측: RS-485 157점).
    mb = (p.get("blocks") or {}).get("modbus") or {}
    n = (src.get("Instance ID") or src.get("Point No.") or src.get("Comm. Address")
         or src.get("Register")
         or (str(inst) if inst is not None else "")
         or (str(mb.get("address")) if mb.get("address") is not None else ""))
    st = ", ".join("%s=%s" % (s.get("code"), s.get("label"))
                   for s in (c.get("states") or []))
    r = {"n": n, "t": bac.get("objectType") or "", "nm": c.get("name") or ""}
    if inst is not None:
        r["i"] = inst
    rg = (c.get("range") or {}).get("raw")
    # 배율은 **방향까지 보여 준다** — 숫자만 '10' 이라고 두면 곱인지 나눗셈인지 모른다
    sc = ("×%s  (%s)" % (c["scale"], c.get("scaleRaw") or "")).strip()         if c.get("scale") is not None else None
    for k, v in (("u", c.get("unitSIRaw") or c.get("unitIPRaw")), ("rg", rg),
                 ("sc", sc), ("sr", c.get("statesRef")),
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
    #    ⚠ **문장 칸은 통째로 다 읽었으면 다시 보여 주지 않는다.** CO2 의 Unit 칸은
    #       '0~255 (Real Value = Value*10, … 200ppm)' 하나에 단위·범위·배율이 다
    #       들어 있어, 이미 세 열로 갈라 놓고 그 문장을 또 한 열로 보이면 같은 값이
    #       네 번 나온다. 조각들이 그 칸 **안에** 들어 있으면 읽은 것으로 본다.
    flat = lambda s: re.sub(r"\s+", "", str(s))
    mbb = (p.get("blocks") or {}).get("modbus") or {}
    solo = {flat(x) for x in (r.get("n"), r.get("t"), r.get("nm"), r.get("d"),
                              r.get("u"), r.get("rg"), r.get("rw"), r.get("sr"),
                              c.get("unitSI"), c.get("scaleRaw"),
                              # 구역 머리글과 배율 열에 이미 있는 것을 또 세우지 않는다
                              c.get("group"), mbb.get("scaleRaw"),
                              mbb.get("scale")) if x}
    solo |= {flat(s.get("label")) for s in (c.get("states") or [])}
    pieces = [flat(x) for x in (c.get("unitSIRaw") or c.get("unitIPRaw"),
                                (c.get("range") or {}).get("raw"),
                                c.get("scaleRaw"), c.get("statesRef")) if x]

    labels = [flat(s.get("label")) for s in (c.get("states") or [])]

    def read(v):
        f = flat(v)
        if f in solo:
            return True
        # 상태를 뽑아낸 칸도 다 읽은 것이다 — '0: None 1: FreeRun …' 은 상태 열과 같다
        if labels and all(x in f for x in labels):
            return True
        inside = [x for x in pieces if x and x in f]
        return len(inside) >= 2 or (len(inside) == 1 and inside[0] == f)

    # '-' · 'N/A' 는 값이 아니다(point-schema emptyMeansAbsent) — 열로 세우지 않는다
    extra = {k: v for k, v in src.items()
             if v and str(v).strip() not in SC.NO_UNIT and not read(v)}
    if extra:
        r["x"] = extra
    return r


# 화면 열 — 값이 하나라도 있는 것만 세운다(빈 열은 눈만 어지럽힌다)
# ⚠ 단위와 범위를 **다른 열**로 세운다. 원문은 한 칸에 섞어 넣지만
#    '-127~127' 은 단위가 아니다 — 같은 열에 두면 BMS 가 그것을 단위로 읽는다.
DERIVED = [("n", "번호"), ("t", "타입"), ("nm", "이름"), ("u", "단위"), ("rg", "범위"),
           ("sc", "배율"), ("rw", "R/W"), ("s", "상태 TEXT"), ("sr", "코드표"),
           ("d", "설명")]


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


def spec_sections(m, pages, no_pages):
    """모델의 **정격**을 대조 구역으로 만든다 — 포인트와 같은 화면에서 본다.

    오브젝트만 맞추고 정격은 딴 데서 보면 두 벌을 오가게 된다. 원문 쪽도 같은 방식으로
    띄운다. 다만 쪽 찾는 법이 다르다 — 포인트는 **인쇄 쪽번호**를 받아 PDF 쪽을 찾아야
    하지만(문서마다 오프셋이 다르다), 정격표는 `specTables[].page` 가 이미 **PDF 쪽**이다
    (실측: AJ2756…pdf 19쪽에 'Table 6', 24쪽에 'Table 9' — 그대로 맞는다).
    그래서 여기서는 찾지 않고 그대로 쓴다.

    담는 것: spec(항목형) · specTables(표) · elec(전기데이터) · comm · io · variants.
    문서가 준 열 이름을 그대로 세운다 — 우리 어휘로 바꾸지 않는다.
    """
    out = []
    mid = m["id"]

    # ── 쪽이 안 적힌 정격 줄에 원문 쪽을 붙인다 — **글자로 찾는다** ──────────────
    # 손으로 넣은 정격은 출처가 'Fact Sheet' 처럼 이름뿐이라 쪽이 없다. FC 101 은
    # 그런 줄이 맨 위 44행(항목·통신·입출력·전기데이터)이라 화면을 열면 **첫 장면이
    # 통째로 링크 없음**이 된다(사용자가 네 번 짚었다). 값이 원문에 그대로 있으니
    # 셈하지 말고 찾는다 — 저장소가 이미 쓰는 방식이다.
    doc_cache = {}

    def docs_of_model():
        got = []
        for t in (m.get("specTables") or []):
            f2 = (t.get("source") or "").split("#")[0]
            if f2 and f2 not in got and os.path.exists(os.path.join(DATA, "raw", f2)):
                got.append(f2)
        sd = (m.get("sourceDoc") or "").split("#")[0]
        if sd and sd not in got and os.path.exists(os.path.join(DATA, "raw", sd)):
            got.append(sd)
        return got

    def doc_text(f2):
        if f2 not in doc_cache:
            import fitz
            d2 = fitz.open(os.path.join(DATA, "raw", f2))
            doc_cache[f2] = [re.sub(r"\s+", " ", pg.get_text()).lower() for pg in d2]
            d2.close()
        return doc_cache[f2]

    def find_page(tokens):
        """(파일, 쪽, 쓴 낱말) 또는 None. 먼저 걸리는 낱말·첫 쪽을 쓴다."""
        for t in tokens:
            t2 = re.sub(r"\s+", " ", str(t or "")).strip()
            if len(t2) < 4 or not re.search(r"[A-Za-z0-9]", t2):
                continue
            low = t2.lower()
            for f2 in docs_of_model():
                for i, txt in enumerate(doc_text(f2), 1):
                    if low in txt:
                        return f2, i, t2
        return None

    def sec(kind, title, cols, rows, src="", pdf=None):
        if not rows:
            return
        # ⚠ 정격표의 source 는 **'파일.pdf#앵커'** 인 것이 있다
        #   ('LG_AHU_CommKit_…_PDB.pdf#eevkits' — 한 문서에서 표를 가르려고 붙인 표식).
        #   통째로 파일 이름으로 보면 없는 파일이 되어 원문 링크가 통째로 죽는다.
        src = (src or "").split("#")[0]
        key = None
        if pdf and src:
            path = os.path.join(DATA, "raw", src)
            if os.path.exists(path):
                # 열쇠는 --no-pages 에서도 만든다 — 쪽 그림은 안 담아도
                # '원문 PDF 전체' 링크는 이 열쇠에서 파일 이름을 얻는다.
                key = "%s|%s#%s" % (mid, src, pdf)
                if not no_pages:
                    pages.setdefault(key, (mid, pdf, path))
        for r in rows:
            # 줄이 제 출처를 갖고 있으면 그것을 쓴다(항목형). 없으면 구역 것을 따른다.
            rs, rp, by = r.pop("_src", None), r.pop("_pdf", None), r.pop("_by", None)
            if by:
                r["출처찾기"] = "'%s' 로 찾은 쪽" % by[:40]
            if rs and rp:
                rkey = "%s|%s#%s" % (mid, rs, rp)
                if not no_pages:
                    pages.setdefault(rkey, (mid, rp, os.path.join(DATA, "raw", rs)))
                r["pk"], r["pg"], r["pdf"] = rkey, rp, rp
            else:
                r["pk"] = key or ""
                r["pg"] = pdf or ""
                r["pdf"] = pdf or "?"
        # ⚠ '기타'로 판정된 표를 정격 칸에 같이 두면 정격을 못 믿는다 —
        #   LG AC Smart 는 정격 15행이 전부 오류 코드표·고장 증상표였다.
        #   지우지는 않고 **딴 칸으로 내린다**(원문에 있는 표이므로).
        misc = kind == "table" and (title or "").startswith("[기타]")
        out.append({"cols": cols, "id": "%s/spec/%s" % (mid, title[:40]),
                    "node": "%s|%s" % (mid, "misc" if misc else "spec"),
                    "path": [m.get("model") or mid,
                             "기타 표" if misc else "정격", title],
                    "doc": src, "span": str(pdf) if pdf else "—", "points": rows})

    FLAT = [("항목", 0), ("값", 1), ("단위", 2), ("조건", 3), ("출처", 4)]
    # 항목형 정격은 표가 아니라 줄마다 출처가 다르다 — '파일.pdf p12' 로 적혀 있다
    # (실측 1,568행 중 1,530행). 줄마다 제 원문 쪽을 갖게 해야 링크가 산다.
    SRC = re.compile(r"([A-Za-z0-9_\-.%]+\.pdf)(?:\s*[pP]\.?\s*(\d+))?")

    def flat_rows(items):
        rows = []
        for it in items:
            r = {"n": str(it[0])[:120]}
            for h, i in FLAT:
                r[h] = str(it[i]) if len(it) > i and it[i] is not None else ""
            g = SRC.search(r.get("출처") or "")
            if g and g.group(2):
                f2, pg2 = g.group(1), int(g.group(2))
                if os.path.exists(os.path.join(DATA, "raw", f2)):
                    r["_src"], r["_pdf"] = f2, pg2
            else:
                got = find_page([r.get("출처"), r.get("값"), r.get("항목")])
                if got:
                    r["_src"], r["_pdf"], r["_by"] = got
            rows.append(r)
        return rows

    flat_cols = [{"k": h, "h": h} for h, _ in FLAT]
    sec("spec", "항목", flat_cols, flat_rows(m.get("spec") or []))
    for label, key in (("통신", "comm"), ("입출력", "io")):
        items = m.get(key) or []
        if items:
            cols = [{"k": "c%d" % i, "h": h} for i, h in
                    enumerate(["항목", "값", "비고", "출처"][:max(len(x) for x in items)])]
            rows = []
            for it in items:
                r = dict({"c%d" % i: str(v) for i, v in enumerate(it)},
                         n=str(it[0])[:120])
                got = find_page([it[-1] if len(it) > 1 else None, it[0],
                                 it[1] if len(it) > 1 else None])
                if got:
                    r["_src"], r["_pdf"], r["_by"] = got
                rows.append(r)
            sec(key, label, cols, rows)

    el = m.get("elec") or {}
    if el.get("rows"):
        cols = [{"k": "c%d" % i, "h": h} for i, h in enumerate(el.get("header") or [])]
        rows = []
        for r in el["rows"]:
            rr = dict({"c%d" % i: str(v) for i, v in enumerate(r)}, n=str(r[0])[:120])
            if not el.get("page"):
                got = find_page([r[0]])       # 형식 코드('PK37')가 원문에 그대로 있다
                if got:
                    rr["_src"], rr["_pdf"], rr["_by"] = got
            rows.append(rr)
        sec("elec", "전기 데이터", cols, rows, el.get("source") or "", el.get("page"))

    # ── 쪽을 넘겨 이어지는 사양표는 **한 구역으로 붙인다** ────────────────────
    # 원문 한 표가 두 쪽에 걸치면 추출은 두 조각으로 남는다. 화면에서 그대로 두면
    # 아래쪽이 통째로 안 보여 "잘렸다" 로 읽힌다(사용자 지적. 실측 39모델 182건).
    # 붙이는 조건을 좁게 둔다 — 같은 문서 · 같은 제목 · **열이 같고**(머리글 첫 칸은
    # 이어지는 쪽에서 자료 행을 빨아들여 더러워지므로 둘째 칸부터 본다) · 쪽이 달라야
    # 한다(같은 쪽의 여러 블록은 서로 다른 표다 — AAON 치수표가 그렇다).
    # 이어지는 쪽의 캡션은 '… - (continued)' 로 끝난다. 캡션이 잘려 '- (' · '- (co'
    # 로만 남기도 한다. 그 꼬리를 떼지 않으면 제목이 달라 안 붙는다 —
    # Trane Precedent 정격이 같은 이유로 두 레코드가 됐다(NEXT [C]).
    CONT = re.compile(r"\s*[-–—]?\s*\(\s*(?:continued|contin\w*|cont|co|c)?\s*\)?\s*$",
                      re.I)

    def base_title(x):
        x = re.sub(r"\s+", " ", (x or "")).strip()
        y = CONT.sub("", x).strip()
        return y or x

    # ⚠ 열쇠로 덮어쓰면 안 된다. 같은 제목·같은 열이 **떨어진 쪽**에 또 나오면
    #   (이어진 것이 아니라 다른 표다) 앞 표를 잃는다 — 실제로 그렇게 짜서
    #   정격 행이 1,118 → 1,040 으로 78행이 조용히 사라졌다. 구역은 목록으로 쌓고,
    #   붙일 대상은 '그 열쇠로 **마지막에** 만든 구역' 하나만 본다.
    last, order = {}, []
    for t in (m.get("specTables") or []):
        header = list(t.get("header") or [])
        key = ((t.get("source") or "").split("#")[0],
               base_title(t.get("title")),
               tuple(header[1:]))
        prev = last.get(key)
        if prev is not None and (t.get("page") or 0) > (prev["page"] or 0)                 and (t.get("page") or 0) - (prev["page"] or 0) <= 2:
            # 첫 칸이 더러워졌으면 그 여분은 원문에 있던 **구역 제목 행**이다
            extra = (header[0] or "").strip()
            base = (prev["header"][0] or "").strip()
            if extra and base and extra.startswith(base) and len(extra) > len(base):
                prev["rows"].append([extra[len(base):].strip()] +
                                    [""] * (len(header) - 1))
                prev["rowPages"].append(t.get("page"))
                prev["contPages"].append(t.get("page"))
            add = list(t.get("rows") or [])
            prev["rows"].extend(add)
            # 이어 붙인 줄은 **제 쪽**을 단다 — 안 그러면 원문 그림이 첫 쪽만 뜬다
            prev["rowPages"].extend([t.get("page")] * len(add))
            prev["contPages"].append(t.get("page"))
            prev["page"] = t.get("page")   # 세 쪽 넘는 표도 이어진다
            continue
        cur = {"title": t.get("title") or "표", "kind": t.get("kind"), "header": header,
               "rows": list(t.get("rows") or []), "page": t.get("page"),
               "rowPages": [t.get("page")] * len(t.get("rows") or []),
               "source": t.get("source") or "", "contPages": []}
        last[key] = cur
        order.append(cur)

    for t in order:
        header = t["header"]
        cols = [{"k": "c%d" % i, "h": (h or "—")} for i, h in enumerate(header)]
        rows = []
        srcfile = (t["source"] or "").split("#")[0]
        for ri, r in enumerate(t["rows"]):
            rr = dict({"c%d" % i: ("" if v is None else str(v))
                       for i, v in enumerate(r)}, n=str(r[0] if r else "")[:120])
            pg2 = t["rowPages"][ri] if ri < len(t["rowPages"]) else t["page"]
            if pg2 and pg2 != t["page"] and srcfile:
                rr["_src"], rr["_pdf"] = srcfile, pg2
            rows.append(rr)
        # 표 성격을 제목에 단다 — 정격과 치수·성능표를 눈으로 갈라야 한다
        # (specs.py 의 판정. 전수 2,164표 중 정격은 929표뿐이다).
        KIND = {"rating": "[정격]", "perf": "[성능]", "dim": "[치수]", "etc": "[기타]"}
        title = ("%s %s" % (KIND.get(t.get("kind"), ""), base_title(t["title"]))).strip()
        if t["contPages"]:
            title += " (원문 %s쪽에서 이어짐)" % "·".join(
                str(x) for x in sorted(set(t["contPages"])))
        sec("table", title, cols, rows, t["source"], t["page"])

    for v in (m.get("variants") or []):
        sec("variant", "형번 %s" % v.get("code", "?"), flat_cols,
            flat_rows(v.get("spec") or []), v.get("source") or "")
    return out


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
             "국내 벤더 취입분 + %s" % " · ".join(FOCUS_MODELS))

    enames = equip_names()
    ptypes = addr_rules()
    tree, sections, pages, warns = collections.OrderedDict(), [], {}, []
    total = 0

    for m in models:
        eq = m.get("equipId") or "?"
        vendor = m.get("vendor") or "?"
        eid, vid = eq, "%s|%s" % (eq, vendor)
        mid = "%s|%s" % (vid, m["id"])
        # ⚠ 원문을 **판마다** 찾는다. 한 모델의 판들이 서로 다른 문서에서 올 수 있다 —
        #    LS H100 은 BACnet 판이 옵션 카드 매뉴얼, RS-485 판이 본체 매뉴얼이다.
        #    모델의 sourceDoc 하나만 보면 뒤엣것의 쪽을 못 찾아 **원문이 안 뜬다**
        #    (실측: 판 하나 157점이 통째로 그림 없이 떴다).
        pdfmap, docof = {}, {}
        for iface in m["interfaces"]:
            src = iface.get("sourceFile") or m.get("sourceDoc") or ""
            docof[iface["id"]] = src
            if src in pdfmap:
                continue
            path = os.path.join(DATA, "raw", src)
            if not os.path.exists(path):
                warns.append("%s / %s: 원문이 없다(%s) — 쪽 그림 없이 담는다"
                             % (m["id"], iface["id"], src))
                pdfmap[src] = {}
                continue
            want, names = set(), {}
            for i2 in m["interfaces"]:
                if (i2.get("sourceFile") or m.get("sourceDoc")) != src:
                    continue
                for p in i2.get("points") or []:
                    pr = (p.get("provenance") or {}).get("sourcePage")
                    if pr is None:
                        continue
                    want.add(pr)
                    names.setdefault(pr, []).append(
                        (p.get("common") or {}).get("name") or "")
            # 판이 "이 쪽번호는 PDF 순번이다"(pageBase='pdf')라고 밝히면 찾지 않는다.
            # 찾으면 오히려 틀린다 — 인쇄 쪽번호가 없는 문서에서 본문 숫자를 쪽번호로
            # 착각해 엉뚱한 쪽을 띄웠다(Danfoss FC 101: 77쪽→34쪽, 108쪽→33쪽).
            if any((i2.get("sourceFile") or m.get("sourceDoc")) == src
                   and i2.get("pageBase") == "pdf" for i2 in m["interfaces"]):
                pdfmap[src] = {x: x for x in want}
            else:
                dd = fitz.open(path)
                pdfmap[src], w = resolve_pages(dd, want, names)
                dd.close()
                warns += ["%s / %s: %s" % (m["id"], src, x) for x in w]

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
                src = docof[iface["id"]]
                for p in pts:
                    printed = (p.get("provenance") or {}).get("sourcePage")
                    pdf = (pdfmap.get(src) or {}).get(printed)
                    key = "%s|%s#%s" % (m["id"], src, pdf)
                    r = row_of(p)
                    r["pg"] = printed
                    r["pdf"] = pdf or "?"
                    r["pk"] = key
                    rows.append(r)
                    if printed not in span:
                        span.append(printed)
                    if pdf and not no_pages and key not in pages:
                        pages[key] = (m["id"], pdf,
                                      os.path.join(DATA, "raw", src))
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

        specs = spec_sections(m, pages, no_pages)
        if specs:
            sections.extend(specs)
            for node, label in (("spec", "정격"), ("misc", "기타 표")):
                nid = "%s|%s" % (m["id"], node)
                n2 = sum(len(sc["points"]) for sc in specs if sc["node"] == nid)
                if not n2:
                    continue
                mnode["children"].append({"id": nid, "label": label,
                                          "count": n2, "children": []})
                mnode["count"] += n2
                total += n2

        shorten(mnode["children"])
        e = tree.setdefault(eid, {"id": eid, "count": 0,
                                  "label": ("%s %s" % (eid, enames.get(eid, ""))).strip(),
                                  "children": collections.OrderedDict()})
        v = e["children"].setdefault(vid, {"id": vid, "label": vendor, "count": 0,
                                           "children": []})
        v["children"].append(mnode)
        v["count"] += mnode["count"]
        e["count"] += mnode["count"]

    # 쪽 그림은 문서별로 한 번만 연다.
    # ⚠ 열쇠를 **한 쪽에 하나만** 매달면 안 된다. 같은 문서 같은 쪽을 두 모델이
    #   쓰는 일이 흔하다 — LG AHU 킷 PAHCMR000·PAHCMS000 이 같은 PDB 5쪽을 본다.
    #   dict 로 덮어쓰다가 **정격 206행이 그림 없이 떴다**(사용자가 "정격 원문
    #   페이지가 안 열린다" 고 세 번 짚은 것이 이것이다). 쪽 하나에 열쇠 여럿을 단다.
    imgs = {}
    if not no_pages:
        bydoc = collections.defaultdict(lambda: collections.defaultdict(list))
        for key, (mid_, pdf, path) in pages.items():
            bydoc[path][pdf].append(key)
        for path, want in bydoc.items():
            doc = fitz.open(path)
            got = UI.page_images(doc, want.keys())
            for pdf, keys in want.items():
                for key in keys:
                    imgs[key] = got[pdf]
            doc.close()

    import pathlib
    payload = {
        "title": "취입 대조대",
        # 원문 PDF 를 여는 절대 주소. 이 산출물은 로컬에서 file:// 로 여는 물건이라
        # (쪽 그림을 담아 gitignore 된다) 상대경로보다 절대경로가 확실하다 —
        # 사용자가 "링크가 안 열린다" 고 두 번 짚었다. 상대경로는 JS 가 대비로 갖는다.
        "rawBase": pathlib.Path(os.path.join(DATA, "raw")).resolve().as_uri() + "/",
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
