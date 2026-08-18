# -*- coding: utf-8 -*-
"""JCI/York BAS 포인트 리스트 56건 취입 — 문서 → 모델의 interfaces[].

왜 register.py 가 아니라 따로인가
  register.py 는 '문서 1건 → 모델 1건'을 일반 추출기(extract.py)로 만든다. JCI 는
  계통마다 표 구조가 달라 전용 파서 넷(vendor_jci_sceq·_elink·_native·_yzd)이 있고,
  **문서와 모델이 1:1 이 아니다.** YK 하나가 SC-EQ·OptiView E-Link(EM/SSS·VSD)·
  Micropanel II 로 문서 4건이다. 그래서 취입 규칙이 다르다.

무엇을 모델로 삼나 (D-016)
  모델 = **제품**(JCI 카탈로그의 prodname), 인터페이스 = **그 제품이 내보내는 목록의 판**.
  한 문서가 여러 제품을 덮으면(YCAJ, YCAZ, YCWZ …) 주 제품에만 붙이고 나머지는
  interfaces[].appliesTo 로 밝힌다 — 같은 1,000점을 제품 수만큼 복제하지 않는다.

계통 판정은 머리글 표식으로 한다
  파일 이름·제목으로 가르면 깨진다. 실제로 'YPAL (ECO2) LON and N2 **E-Link** Point
  Maps' 는 제목에 E-Link 가 있지만 표 구조는 Native/Panel 계통이다. 표식은 그 계통의
  표에만 나오는 열 이름이고, 표식이 둘 이상 걸리면 **둘 다 파싱해 많이 나온 쪽**을
  쓴다(문서 안에 남의 계통 표가 섞여 있는 경우가 실제로 있다).

실행
  PYTHONIOENCODING=utf-8 python ingest_jci.py --route     계통 판정만 (빠름)
  PYTHONIOENCODING=utf-8 python ingest_jci.py --apply     모델 레코드 생성 (오래 걸림)
  PYTHONIOENCODING=utf-8 python ingest_jci.py --refresh    규칙만 다시 적용 (몇 초)
  PYTHONIOENCODING=utf-8 python ingest_jci.py --export     검토 화면 (review/jci-ingest.html)
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import collect as CO  # noqa: E402
import schema as S  # noqa: E402
import sources as SRC  # noqa: E402

SOURCE = "jci-york-bas-points"
VENDOR = "Johnson Controls / YORK"
SNAPSHOT = os.path.join(DATA, "haystack", "_jci_docs.json")

# 계통 → (파서 모듈, 머리글 표식). 표식은 그 계통의 표에만 나오는 열 이름이다.
#
# ⚠ E-Link 표식은 파서의 ANCHOR 가 아니라 **소유 조건**을 쓴다. ANCHOR 는 표를
#   찾는 그물이라 'BACnet Object &' 까지 포함해 SC-EQ 머리글에도 걸린다(실측 18건).
#   elink.parse_doc 이 실제로 자기 것이라고 인정하는 조건은 ENG/ASCII PAGE REF
#   열의 존재다 — 없으면 skipped['foreign'] 로 뺀다. 라우팅은 그쪽을 따른다.
ROUTES = [
    ("YZD-Logix", "vendor_jci_yzd", r"Logix\s*Tag"),
    ("Native", "vendor_jci_native", r"Item\s*Ref\s*Num|PANEL\s*DISPLAYED\s*NAME"),
    ("SC-EQ", "vendor_jci_sceq", r"Long\s*Name"),
    ("E-Link", "vendor_jci_elink",
     r"ENG\s*B?PAGE\s*REF|ASCII\s*PAGE\s*REF|York\s*Talk\s*Point\s*Type"),
]

# JCI 카탈로그가 제품명을 안 준 문서. 제목에 적힌 것만 옮겨 적는다 — 지어내지 않는다.
BLANK_PROD = {
    "38yjzoNRyJnOMntX63dCBA": "Sunline 3000 Rooftop",
    "47mW1GA_AXbFLIz2QICYeQ": "YCAL Style E",          # Scroll BAS SC-EQ — 아래 MERGE 로 합류
    "BIOPM0nRZnUk75tsUSvUTA": "CR (OptiView)",
    "5wtWGe_rjmetBNFyP2PvFQ": "Frick LS Screw (RWB Microboard)",
    "OQCjzS3A0ZVQ9QBqSlanSQ": "Basildon Reciprocating (Micro Panel II)",
    "TWAOtmjMD~xxMBlTMLA2QQ": "YVWH·YVWE·YGWH Chillers",
    "ZVOgU4MVClTr1wstBh3m2A": "AWHP Air Water Heat Pump",
}

# 같은 제품인데 카탈로그가 세대별로 다른 이름을 붙인 것 → 한 모델로 합치고
# 세대는 인터페이스의 revision.block 으로 남긴다. 합치지 않으면 'YCAL' 을 고른
# 사람이 자기 세대 목록을 못 찾는다.
MERGE = {
    "YCAL Style A-C": "York Scroll Chillers (YCAL·YCUL·YCWL·YLAA·YLPA·YLUA·YCRL)",
    "YCAL Style E": "York Scroll Chillers (YCAL·YCUL·YCWL·YLAA·YLPA·YLUA·YCRL)",
}
BLOCK_OF = {                       # 합쳐진 모델에서 그 문서가 어느 세대인지
    "YCAL Style A-C": "Style A–C",
    "YCAL Style E": "Style E",
}

# 제목 첫머리의 제품 코드 나열. JCI 는 세 가지로 쓴다 — 쉼표('YVAA, YVFA, YAGK'),
# and('YS and YN'·'YCWS and YCRS'), 섞어 쓰기('YCRL, YCUL and YCAL').
# 쉼표만 잡던 때 10건이 통째로 안 읽혔다.
CODE = r"[A-Z]{2,6}\d?"
CODES = re.compile(r"^((?:%s)(?:\s*(?:,|and|&|/)\s*(?:%s))+)\b" % (CODE, CODE), re.I)
CODE_ONE = re.compile(r"^%s$" % CODE)
CODE_WORD = re.compile(r"\b(%s)\b" % CODE)
# 제품 코드가 아니라 낱말인 것 — 'and' 로 이어 붙은 조각에 섞여 들어온다
NOT_CODE = {"AND", "OR", "THE", "AND/OR", "BAS", "SC", "EQ", "LON", "N2", "IPU",
            "ISN", "VSD", "EM", "SSS", "HMI", "PDF", "REV", "OPTIVIEW", "ELINK"}
REV = re.compile(r"\bRev[\s_]*([A-Za-z]?[\s_]?[\d.]+[a-z]?)", re.I)

# 설비 분류 — **제품명에 적힌 낱말**로만 정한다(JCI 카탈로그 prodname 이 근거다).
# 태그 어휘는 Haystack 4 를 그대로 쓴다: chillerMechanism 은 choice 라 하나만 붙는다.
# ⚠ 스크롤은 Haystack 4 에 chiller-scroll 이 **없다** — 지어내지 않고 gap 에 적는다.
MECHANISM = [
    ("Centrifugal", "CENTRIFUGAL", "chiller-centrifugal"),
    ("Screw", "SCREW", "chiller-rotaryScrew"),
    ("Reciprocating", "RECIP", "chiller-reciprocal"),
    ("Recip", "RECIP", "chiller-reciprocal"),
    ("Absorption", "ABSORPTION", "chiller-absorption"),
    ("Scroll", "SCROLL", None),
]
COOLING = [("Air Cooled", "airCooling"), ("Air-Cooled", "airCooling"),
           ("Water Cooled", "waterCooling"), ("Water-Cooled", "waterCooling")]


def catalog():
    """문서ID → 카탈로그 메타(파일·제목·제품). 스냅샷이 정본이다."""
    with open(SNAPSHOT, encoding="utf-8") as f:
        snap = json.load(f)
    out = {}
    for site, lst in snap.items():
        for x in lst:
            meta = {m.get("key"): (m.get("values") or [""])[0]
                    for m in (x.get("metadata") or [])}
            out[x["id"]] = {"site": site, "title": (x.get("title") or "").strip(),
                            "prod": (meta.get("prodname") or "").strip(),
                            "category": meta.get("category") or ""}
    return out


def registered():
    """대장에 등록된 JCI 포인트 문서 → [(문서ID, 경로, 저장이름)]"""
    paths = {os.path.basename(p): p for p in CO.files_of(SOURCE)}
    out = []
    for doc_id, _site, name in SRC.JCI_BAS_POINTS:
        p = paths.get(name)
        if p:
            out.append((doc_id, p, name))
    return out


def marks_of(path, pages=6):
    """표 **머리글**에서 계통 표식을 찾는다.

    ⚠ 페이지 글자 흐름(get_text)으로 찾으면 안 된다. 머리글 칸이 여러 줄이면
    글자 흐름에서는 열끼리 뒤섞여 나온다 — 'ENG PAGE REF' 가 실제로
    'ENG | PAGE Object Object & | Object' 로 온다. 표식 없음 21건이 전부 그것이었다.
    표 인식으로 읽으면 셀 그대로 'ENG\\nPAGE\\nREF' 라 파서와 같은 근거가 된다.
    """
    import fitz
    doc = fitz.open(path)
    pats = [(fam, pat) for fam, _mod, pat in ROUTES]
    found, limit = [], min(pages, doc.page_count)
    while True:
        heads = []
        for i in range(limit):
            try:
                tabs = doc[i].find_tables().tables
            except Exception:
                continue
            for t in tabs:
                data = t.extract()
                if data:
                    heads.append(" | ".join(c or "" for c in data[0]))
        text = "\n".join(heads)
        found = [fam for fam, p in pats if re.search(p, text, re.I)]
        # 앞쪽이 개정이력·표지뿐인 문서가 있다 — 못 찾으면 한 번 더 깊이 본다
        if found or limit >= min(30, doc.page_count):
            break
        limit = min(30, doc.page_count)
    doc.close()
    return found


def route(only=None, verbose=True):
    """문서별 계통 후보 판정. 표식이 0개면 사람이 봐야 한다 — 조용히 넘기지 않는다."""
    cat = catalog()
    rows = []
    for doc_id, path, name in registered():
        if only and only.lower() not in name.lower():
            continue
        m = cat.get(doc_id, {})
        marks = marks_of(path)
        rows.append({"id": doc_id, "path": path, "file": name, "marks": marks,
                     "title": m.get("title", ""), "prod": m.get("prod", ""),
                     "site": m.get("site", "")})
        if verbose:
            print("%-46s %-24s %s" % (name[:46], ", ".join(marks) or "표식 없음 ⚠",
                                      (m.get("prod") or m.get("title", ""))[:40]))
    if verbose:
        tally = collections.Counter(tuple(r["marks"]) for r in rows)
        print("\n문서 %d건" % len(rows))
        for k, v in tally.most_common():
            print("   %-40s %d건" % (", ".join(k) or "표식 없음", v))
    return rows


def parse_best(row):
    """표식이 걸린 파서를 모두 돌려 **가장 많이 뽑힌 것**을 쓴다.

    표식이 둘 이상 걸리는 이유는 문서 안에 남의 계통 표가 섞여 있어서다.
    우선순위로 정하면 그 문서에서 어느 쪽이 본문인지 알 수 없다 — 실측으로 고른다.
    """
    best = None
    tried = {}
    for fam, mod, _pat in ROUTES:
        if fam not in row["marks"]:
            continue
        parser = __import__(mod)
        rows, unk, head, skipped = parser.parse_doc(row["path"])
        tried[fam] = len(rows)
        if best is None or len(rows) > len(best[1]):
            best = (fam, rows, unk, skipped, mod)
    return best, tried


def model_of(row):
    """문서 → 모델 키(제품). 카탈로그 제품명이 정본, 없으면 제목에서 옮겨 적은 것."""
    prod = row["prod"] or BLANK_PROD.get(row["id"]) or row["title"][:40]
    return MERGE.get(prod, prod), prod


def equip_of(name):
    """제품명·제목의 낱말로 계열·분류·태그를 정한다.

    설비별로 갈라 보려면 계열(e9) 하나로는 부족하다 — 냉동기 31건이 한 덩어리가 된다.
    JCI 카탈로그 제품명이 압축 방식과 응축 방식을 이미 밝히므로(‘YCAS Air Cooled
    Screw Chiller’) 그걸 읽어 cat 4단계와 Haystack 태그로 옮긴다. **문서에 없는
    것은 만들지 않는다** — 이름에 안 적힌 제품은 그냥 CHILLER 로 남는다.
    """
    t = name.lower()
    if "rooftop" in t or "ypal" in t:
        return "e5", "HVAC.AIR.RTU", "rooftop", ["rooftop"], []
    tags, gaps = ["chiller"], []
    cat = "HVAC.PLANT.CHILLER"
    for word, suffix, tag in MECHANISM:
        if word.lower() in t:
            cat = "HVAC.PLANT.CHILLER." + suffix
            if tag:
                tags.append(tag)
            else:
                gaps.append("압축 방식 '%s' 는 Haystack 4 chillerMechanism 에 값이 없다"
                            "(chiller-scroll 미정의) — 태그를 지어내지 않는다" % word)
            break
    for word, tag in COOLING:
        if word.lower() in t:
            tags.append(tag)
            break
    if "heat pump" in t:
        tags.append("heatPump")
    return "e9", cat, "chiller", tags, gaps


def iface_id(name):
    """저장 이름 → 인터페이스 ID. 문서마다 유일하고 사람이 읽을 수 있다."""
    s = re.sub(r"^JCI_|\.pdf$", "", name)
    s = re.sub(r"[^\w]+", "-", s).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)


def applies_to(title):
    """제목 첫머리에 나열된 제품 코드. 없으면 빈 목록 — 짐작하지 않는다."""
    m = CODES.match(title or "")
    if not m:
        return []
    out = []
    for c in re.split(r"\s*(?:,|and|&|/)\s*", m.group(1), flags=re.I):
        c = c.strip().upper()
        if c and c not in NOT_CODE and CODE_ONE.match(c) and c not in out:
            out.append(c)
    return out if len(out) > 1 else []


def _axis(point):
    """이 포인트의 주 주소 축과 값. 계통마다 축이 다르다(BACnet·Modbus·N2·LON)."""
    b = point.get("blocks") or {}
    for blk, field in (("bacnet", "instance"), ("modbus", "address"),
                       ("n2", "address"), ("lon", "nvIndex")):
        v = (b.get(blk) or {}).get(field)
        if isinstance(v, int):
            return blk, v
    return None, None


def split_blocks(rows):
    """문서 안 표 블록 → 판(인터페이스) 단위로 묶는다.

    판정 근거는 **주소 대역**이다. 제목이 없는 블록이 대부분이라 제목으로는 못 가른다.
      · 다음 블록이 앞 블록의 최대 주소 **위**에서 시작하면 → 같은 판의 이어지는 구간.
        E-Link 는 한 판을 Section 1(1~43) · Section 2(101~135) · Section 3(205~243)
        으로 나눠 싣는다. 쪽이 넘어갈 뿐 같은 장치의 한 목록이다.
      · 주소가 **겹치면**(1~43 다음에 다시 1~43) → 별개 판. 한 장치의 목록이 같은
        주소를 두 번 쓸 수는 없다. 실측: 보드·스타터·스타일이 다른 판이 이렇게 온다
        (YK Micropanel II 3판 · YS/YN OptiView 4판 · YCAS 스타일 6판).

    돌려주는 것: [(구간 목록, 근거 문자열)] — 구간 = [(블록번호, 제목, 포인트들)]
    """
    blocks = collections.OrderedDict()
    for r in rows:
        bi = ((r.get("provenance") or {}).get("block") or {})
        blocks.setdefault((bi.get("index", 1), bi.get("title", "")), []).append(r)
    groups, spans = [], []
    for (idx, title), pts in blocks.items():
        vals = [v for _a, v in (_axis(p) for p in pts) if isinstance(v, int)]
        span = (min(vals), max(vals)) if vals else None
        if groups and span and spans[-1] and span[0] > spans[-1][1]:
            groups[-1].append((idx, title, pts))          # 이어지는 구간
            spans[-1] = (spans[-1][0], max(spans[-1][1], span[1]))
        else:
            groups.append([(idx, title, pts)])
            spans.append(span)
    out = []
    for g, span in zip(groups, spans):
        if len(g) > 1:
            why = "블록 %s 를 한 판으로 묶었다 — 주소 대역이 이어진다(%s~%s)" % (
                "·".join(str(b[0]) for b in g), span[0], span[1])
        elif len(groups) > 1:
            why = "주소 대역이 앞 판과 겹쳐 별개 판으로 갈랐다(%s~%s)" % (
                span[0], span[1]) if span else "주소가 없어 블록 단위로 두었다"
        else:
            why = ""
        out.append((g, why))
    return out


def build_interfaces(row, fam, rows, skipped, block=None):
    """문서 하나 → 판(인터페이스) 목록. 한 문서가 판을 여럿 담을 수 있다."""
    base = iface_id(row["file"])
    codes = applies_to(row["title"])
    rev0 = {}
    m = REV.search(row["title"]) or REV.search(row["file"])
    if m:
        rev0["doc"] = "Rev " + re.sub(r"[\s_]+", " ", m.group(1)).strip()
    if block:
        rev0["block"] = block
    ex = {k: v for k, v in (skipped or {}).items() if v}

    parts = split_blocks(rows)
    out = []
    for n, (group, why) in enumerate(parts, 1):
        pts = [p for _i, _t, ps in group for p in ps]
        titles = [t for _i, t, _ps in group if t]
        iid = base if len(parts) == 1 else "%s-p%d" % (base, n)
        for p in pts:                            # 포인트마다 소속을 남긴다
            p.setdefault("provenance", {})["interfaceId"] = iid
        pages = [p for p in ((r.get("provenance") or {}).get("sourcePage") for r in pts)
                 if isinstance(p, int)]
        blocks = collections.Counter()
        for r in pts:
            blocks.update((r.get("blocks") or {}).keys())
        fams = collections.Counter((r.get("provenance") or {}).get("family") for r in pts)
        # 레코드가 밝힌 계통이 정본이다(어댑터가 하위형까지 갈라 적는다). 표식은 후보였을 뿐.
        family = fams.most_common(1)[0][0] if fams else fam
        rev = dict(rev0)
        if len(parts) > 1:
            rev["block"] = titles[0] if titles else "구간 %d" % n
        label = row["title"] or row["file"]
        if len(parts) > 1:
            label = "%s — %s" % (label, rev["block"])
        it = {"id": iid, "label": label, "family": family,
              "protocols": sorted(blocks), "sourceFile": row["file"],
              "pointCount": len(pts), "status": "extracted", "points": pts}
        if rev:
            it["revision"] = rev
        if pages:
            it["sourcePages"] = [min(pages), max(pages)]
        if ex and n == 1:
            # 제외 행 통계는 파서가 문서 단위로 센 것이라 판별로 못 가른다 — 첫 판에 둔다
            it["excluded"] = ex
        if codes:
            it["appliesTo"] = codes
        gaps = []
        if len(fams) > 1:
            gaps.append("한 문서에 계통이 섞였다: %s"
                        % ", ".join("%s %d점" % kv for kv in fams.most_common()))
        if why:
            it["note"] = why
        out.append(it)
    # 판 수와 덮는 제품 수가 같으면 짝을 짓고 싶어지지만, 문서가 그 짝을 밝히지 않는다
    if codes and len(out) == len(codes):
        for it in out:
            it.setdefault("gaps", []).append(
                "판 %d개와 덮는 제품 %d개 수가 같다 — 어느 판이 어느 제품인지 문서가 "
                "밝히지 않아 짝짓지 않았다" % (len(out), len(codes)))
    return out


def crosscheck_of(path, ifaces):
    """줄 읽기 경로로 한 번 더 읽어 대조한다 (규칙 ④).

    BACnet 타입·인스턴스가 있는 계통에서만 성립한다 — 줄 경로가 짝을 만들 열쇠가
    그것뿐이다. 안 되는 계통은 '못 했다'를 사유와 함께 남긴다(추정으로 채우지 않는다).
    """
    import crosscheck as C
    flat = []
    for it in ifaces:
        for r in it["points"]:
            b = (r.get("blocks") or {}).get("bacnet") or {}
            nm = (r.get("common") or {}).get("name")
            if b.get("objectType") and isinstance(b.get("instance"), int) and nm:
                flat.append({"type": b["objectType"], "inst": b["instance"], "name": nm})
    total = sum(it["pointCount"] for it in ifaces)
    if len(flat) < max(20, total * 0.3):
        have = sorted({p for it in ifaces for p in it["protocols"]})
        return {"unverifiable": "BACnet 타입·인스턴스를 가진 포인트가 %d/%d 뿐이라 "
                                "줄 읽기 경로가 짝을 만들 수 없다 (이 문서의 주소 축: %s)"
                                % (len(flat), total, ", ".join(have) or "없음")}
    try:
        return C.compare(path, table_rows=flat)
    except Exception as e:
        return {"unverifiable": "교차 대조 실패: %s" % str(e)[:70]}


PROTO_KO = {"bacnet": "BACnet", "modbus": "Modbus", "n2": "N2", "lon": "LON",
            "yorktalk": "York Talk", "logix": "Logix", "elink": "E-Link"}


def comm_rows(ifaces):
    """프로토콜당 한 줄 — [프로토콜, 어느 판이 주나, 물리계층, 근거]."""
    by = collections.OrderedDict()
    for it in ifaces:
        for p in it.get("protocols") or []:
            by.setdefault(p, []).append(it)
    out = []
    for p, its in by.items():
        fams = sorted({x["family"] for x in its})
        out.append([PROTO_KO.get(p, p), " · ".join(fams), "—",
                    "포인트 리스트 %d판" % len(its)])
    return out


def apply(only=None, dry=False, crosscheck=True):
    rows = route(only=only, verbose=False)
    groups = collections.OrderedDict()
    for row in rows:
        key, prod = model_of(row)
        groups.setdefault(key, []).append((row, prod))

    made, pts_total = 0, 0
    for key, items in groups.items():
        ifaces, sources_seen, notes = [], [], []
        for row, prod in items:
            best, tried = parse_best(row)
            if not best or not best[1]:
                notes.append("%s: 포인트 0점 (표식 %s)" % (row["file"], ", ".join(row["marks"])))
                print("  ⚠ %-44s 0점 — %s" % (row["file"][:44], tried or "표식 없음"))
                continue
            fam, prows, _unk, skipped, mod = best
            made_ifs = build_interfaces(row, fam, prows, skipped, block=BLOCK_OF.get(prod))
            for it in made_ifs:
                if len(tried) > 1:
                    it.setdefault("gaps", []).append(
                        "표식이 여러 계통에 걸렸다: %s — 많이 뽑힌 쪽을 썼다"
                        % ", ".join("%s %d점" % kv for kv in tried.items()))
            ifaces.extend(made_ifs)
            sources_seen.append(row)
            print("  · %-44s %-22s %5d점%s" % (row["file"][:44], made_ifs[0]["family"],
                  len(prows), (" · %d판" % len(made_ifs)) if len(made_ifs) > 1 else ""))
        if not ifaces:
            continue
        equip, cat, tag, tags, cgaps = equip_of(key + " " + items[0][0]["title"])
        mid = S.model_id(VENDOR, key)
        n = sum(i["pointCount"] for i in ifaces)
        rec = {
            "id": mid, "equipId": equip, "vendor": VENDOR, "model": key, "name": key,
            "cat": cat, "tag": tag, "tags": tags, "status": "active",
            "classifiedBy": "JCI 카탈로그 제품명 %r 의 낱말 (압축 방식·응축 방식)" % key,
            "summary": "BAS 포인트 리스트 %d건에서 취입 — 오브젝트 %d점" % (len(ifaces), n),
            "has": {"spec": False, "points": True}, "ede": False,
            "spec": [], "io": [], "elec": None,
            # 통신표는 **프로토콜당 한 줄**이다. 판마다 한 줄씩 내면 같은 프로토콜이
            # 판 수만큼 되풀이돼(YT 12줄) 모델 단추의 프로토콜 배지까지 중복된다.
            "comm": comm_rows(ifaces),
            "points": [],
            "gap": "정격·형번이 없다 — BAS 포인트 문서만 있고 제품 카탈로그는 따로 수집해야 한다."
                   + (" " + " / ".join(cgaps) if cgaps else "")
                   + (" " + " / ".join(notes) if notes else ""),
            "extractor": "vendor_jci",
            "sourceDoc": ifaces[0]["sourceFile"],
            "interfaces": ifaces,
        }
        if crosscheck:
            rec["crosscheck"] = crosscheck_of(sources_seen[0]["path"], ifaces)
        pts_total += n
        made += 1
        if dry:
            print("  (dry) %s — 인터페이스 %d · %d점" % (mid, len(ifaces), n))
            continue
        with open(os.path.join(DATA, "models", mid + ".json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        print("  ✓ %s — 인터페이스 %d · %d점" % (mid, len(ifaces), n))
    print("\n모델 %d건 · 오브젝트 %d점" % (made, pts_total))
    return 0


def _doc_meta():
    """저장 이름 → (문서ID, 제목, 제품명). 취입 뒤에도 원 제목을 되찾을 수 있어야 한다."""
    cat = catalog()
    out = {}
    for doc_id, _site, name in SRC.JCI_BAS_POINTS:
        m = cat.get(doc_id) or {}
        out[name] = (doc_id, m.get("title", ""), m.get("prod", "") or BLANK_PROD.get(doc_id, ""))
    return out


def refresh():
    """저장된 취입 결과를 **새 규칙으로 다시 짠다** (PDF 재파싱 없음).

    포인트는 그대로 두고, 포인트에서 유도되는 것만 다시 만든다 — 판 분리(주소 대역),
    덮는 제품(appliesTo), 설비 분류(cat·tags), 통신표. 규칙을 고칠 때마다 문서
    56건을 다시 읽으면 30분이 걸리는데, 그 30분이 주는 것이 없다.
    """
    meta = _doc_meta()
    models, n = [], 0
    for path in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        if m.get("extractor") != "vendor_jci" or not m.get("interfaces"):
            continue
        by_file = collections.OrderedDict()
        for it in m["interfaces"]:
            f0 = it["sourceFile"]
            e = by_file.setdefault(f0, {"points": [], "excluded": {}, "note": it.get("note")})
            e["points"].extend(it.get("points") or [])
            for k, v in (it.get("excluded") or {}).items():
                e["excluded"][k] = e["excluded"].get(k, 0) + v
        ifaces = []
        for f0, e in by_file.items():
            doc_id, title, prod = meta.get(f0, ("", m["model"], ""))
            row = {"file": f0, "title": title or m["model"], "id": doc_id}
            ifaces.extend(build_interfaces(row, "", e["points"], e["excluded"],
                                           block=BLOCK_OF.get(prod)))
        equip, cat, tag, tags, cgaps = equip_of(m["model"] + " " + m.get("summary", ""))
        m["equipId"], m["cat"], m["tag"], m["tags"] = equip, cat, tag, tags
        m["classifiedBy"] = "JCI 카탈로그 제품명 %r 의 낱말 (압축 방식·응축 방식)" % m["model"]
        m["interfaces"] = ifaces
        m["comm"] = comm_rows(ifaces)
        m["summary"] = ("BAS 포인트 리스트 %d건 · 판 %d개에서 취입 — 오브젝트 %d점"
                        % (len(by_file), len(ifaces),
                           sum(i["pointCount"] for i in ifaces)))
        if cgaps and cgaps[0] not in m["gap"]:
            m["gap"] = m["gap"] + " " + " / ".join(cgaps)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
        models.append(m)
        n += 1
    made = write_aliases(models)
    print("갱신 %d모델 · 판 %d개 · 별칭 모델 %d건"
          % (n, sum(len(x["interfaces"]) for x in models), made))
    return 0


def write_aliases(models):
    """문서가 덮는데 모델이 없는 제품 → **별칭 모델**을 세운다.

    한 문서가 제품을 여럿 덮을 때 목록은 주 제품에만 붙인다(복제 금지). 그러면
    나머지 제품 코드로 찾을 길이 없어진다 — 실측 8개(YCWJ·YCWZ…)가 그랬다.
    별칭은 목록을 복제하지 않고 **어느 모델의 어느 판이 덮는지만** 가리킨다.
    """
    have = set()
    for m in models:
        for c in re.findall(CODE_WORD, m["model"]):
            have.add(c)
    want = collections.OrderedDict()
    for m in models:
        for it in m["interfaces"]:
            for c in it.get("appliesTo") or []:
                if c not in have:
                    want.setdefault(c, (m, it))
    made = 0
    for code, (m, it) in want.items():
        mid = S.model_id(VENDOR, code)
        rec = {
            "id": mid, "equipId": m["equipId"], "vendor": VENDOR,
            "model": code, "name": code, "cat": m["cat"], "tag": m["tag"],
            "tags": m.get("tags", []), "status": "active",
            "aliasOf": m["id"],
            "summary": "%s 문서가 함께 덮는 제품 — 오브젝트 목록은 %s 의 '%s' 판에 있다"
                       % (VENDOR, m["model"], it["id"]),
            "has": {"spec": False, "points": False}, "ede": False,
            "spec": [], "io": [], "elec": None, "comm": [], "points": [],
            "classifiedBy": "문서 제목의 제품 나열 — %s" % it["label"][:70],
            "gap": "제품 정식명·정격·형번 미상 — JCI 카탈로그가 이 코드에 제품명을 주지 "
                   "않는다. 문서 제목에 코드로만 나온다.",
            "extractor": "vendor_jci",
            "sourceDoc": it["sourceFile"],
        }
        with open(os.path.join(DATA, "models", mid + ".json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        made += 1
    # 규칙이 바뀌면 전에 만든 별칭이 남는다. 별칭은 생성물이므로 지운다 —
    # 사람이 손댄 파일이 아니라서 지워도 잃는 것이 없다(정본은 주 모델의 판이다).
    dropped = 0
    keep = {S.model_id(VENDOR, c) for c in want}
    for path in glob.glob(os.path.join(DATA, "models", "*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("aliasOf") and d["id"] not in keep:
            os.remove(path)
            dropped += 1
    if dropped:
        print("  · 더 이상 필요 없는 별칭 %d건 삭제" % dropped)
    return made


# ── 검토 화면 ────────────────────────────────────────────────────────────────
# 취입 결과를 사람이 볼 수 있는 표로 낸다. 정격 쪽 build.py 와 같은 자리다 —
# **명령으로 다시 만들어지는 오프라인 단일 HTML** 이어야 한다(폐쇄망에서 더블클릭).
VIEW = r"""<title>York 포인트 취입 검사대</title>
<style>
:root{
  --bg:#F5F8F9; --panel:#FFFFFF; --rail:#EDF2F4; --ink:#0F1A1F; --dim:#4A6068;
  --faint:#7C949C; --line:#DAE3E7; --accent:#0E7A88; --accent-soft:#DCEEF0;
  --warn:#9A6608; --warn-soft:#F6EBD3; --hole:#98304A; --hole-soft:#F7E2E7;
  --ok:#1F6B4B;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0C1417; --panel:#111C20; --rail:#0E181C; --ink:#DCE7EA; --dim:#93A8AF;
    --faint:#6B838B; --line:#1E2C32; --accent:#3FB4C2; --accent-soft:#10333A;
    --warn:#D9A441; --warn-soft:#2D2413; --hole:#E0788F; --hole-soft:#2E161C;
    --ok:#5FBF95;
  }
}
:root[data-theme="dark"]{
  --bg:#0C1417; --panel:#111C20; --rail:#0E181C; --ink:#DCE7EA; --dim:#93A8AF;
  --faint:#6B838B; --line:#1E2C32; --accent:#3FB4C2; --accent-soft:#10333A;
  --warn:#D9A441; --warn-soft:#2D2413; --hole:#E0788F; --hole-soft:#2E161C;
  --ok:#5FBF95;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif;
 font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
.mono{font-family:ui-monospace,"Cascadia Mono",Consolas,"SF Mono",monospace;
 font-variant-numeric:tabular-nums}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
code{font-family:ui-monospace,Consolas,monospace;font-size:.92em}

header{position:sticky;top:0;z-index:5;background:var(--panel);
 border-bottom:1px solid var(--line);padding:14px 20px;
 display:flex;align-items:baseline;gap:22px;flex-wrap:wrap}
h1{margin:0;font-size:15px;font-weight:650;letter-spacing:-.01em}
h1 span{color:var(--faint);font-weight:450;margin-left:8px;font-size:12.5px}
.stats{display:flex;gap:20px;flex-wrap:wrap;margin-left:auto;align-items:baseline}
.stat{display:flex;align-items:baseline;gap:6px;font-size:12px;color:var(--dim)}
.stat b{font-size:16px;font-weight:650;color:var(--ink);
 font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums}
.stat.good b{color:var(--ok)}
.stat.hole b{color:var(--hole)}
.flow{font-size:12px;color:var(--dim);display:flex;align-items:baseline;gap:7px}
.flow b{font-family:ui-monospace,Consolas,monospace;font-size:16px;color:var(--ink)}
.arrow{color:var(--accent)}

.app{display:grid;grid-template-columns:290px minmax(0,1fr);height:calc(100vh - 59px)}
aside{background:var(--rail);border-right:1px solid var(--line);overflow-y:auto}
.rh{padding:12px 16px 6px;font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;
 color:var(--faint);font-weight:700}
aside button.item{display:grid;grid-template-columns:1fr auto;gap:8px;width:100%;
 text-align:left;padding:7px 16px;border-left:2px solid transparent;align-items:center}
aside button.item:hover{background:var(--accent-soft)}
aside button.item[aria-current="true"]{background:var(--panel);border-left-color:var(--accent)}
.iname{font-size:12.5px;line-height:1.3}
.icount{font-size:10.5px;color:var(--faint);white-space:nowrap;
 font-family:ui-monospace,Consolas,monospace}
.icount em{font-style:normal;color:var(--accent);font-weight:700}
.cool{font-style:normal;font-size:10px;margin-left:6px;padding:0 5px;border-radius:3px;
 background:var(--accent-soft);color:var(--dim);font-family:ui-monospace,Consolas,monospace}

main{overflow-y:auto;padding:0 0 60px}
.pad{padding:20px 26px}
h2{margin:0 0 2px;font-size:20px;font-weight:650;letter-spacing:-.015em;text-wrap:balance}
.sub{color:var(--dim);font-size:12.5px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 0}
.chip{border:1px solid var(--line);background:var(--panel);border-radius:7px;
 padding:8px 12px;display:grid;gap:2px;text-align:left;min-width:184px}
.chip[aria-pressed="true"]{border-color:var(--accent);background:var(--accent-soft)}
.chip .fam{font-size:12.5px;font-weight:600}
.chip .meta{font-size:10.5px;color:var(--faint);font-family:ui-monospace,Consolas,monospace}
.chip .np{font-size:10.5px;color:var(--accent);font-weight:700;
 font-family:ui-monospace,Consolas,monospace}

.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
 padding:12px 14px;margin-top:14px;font-size:12.5px}
.card b.lbl{display:block;font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
 color:var(--faint);margin-bottom:4px}
.card.warn{border-left:3px solid var(--warn);background:var(--warn-soft)}
.card.hole{border-left:3px solid var(--hole);background:var(--hole-soft)}
.kv{display:flex;gap:18px;flex-wrap:wrap;color:var(--dim)}
.kv span b{color:var(--ink);font-weight:600}

.tools{display:flex;gap:10px;align-items:center;margin:18px 0 8px}
input[type=search]{flex:0 1 320px;padding:6px 10px;border:1px solid var(--line);
 border-radius:6px;background:var(--panel);color:var(--ink);font:inherit;font-size:12.5px}
.rowcount{font-size:11.5px;color:var(--faint);font-family:ui-monospace,Consolas,monospace}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:12px}
th{position:sticky;top:0;background:var(--panel);text-align:left;font-size:10.5px;
 letter-spacing:.05em;text-transform:uppercase;color:var(--faint);font-weight:700;
 padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:5px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:hover{background:var(--accent-soft)}
td.num{font-family:ui-monospace,Consolas,monospace;font-variant-numeric:tabular-nums;
 white-space:nowrap;color:var(--dim)}
td.nm{min-width:210px}
.empty{padding:30px;color:var(--faint);text-align:center}
h3.ph{margin:22px 0 2px;font-size:13px;font-weight:650;letter-spacing:-.01em}
@media (max-width:820px){
  .app{grid-template-columns:1fr;height:auto}
  aside{border-right:0;border-bottom:1px solid var(--line);max-height:220px}
}
</style>
<header>
  <h1>York 포인트 취입 검사대 <span>2026-08-14 · JCI/York BAS 포인트 리스트</span></h1>
  <div class="stats">
    <div class="flow"><b id="sDocs">0</b> 문서 <span class="arrow">&#8594;</span> <b id="sModels">0</b> 제품</div>
    <div class="stat"><b id="sIfs">0</b> 판</div>
    <div class="stat"><b id="sPts">0</b> 오브젝트</div>
    <div class="stat good"><b>0</b> 검증 오류</div>
    <div class="stat"><b id="sHole">0</b> 별칭 제품</div>
  </div>
</header>
<div class="app">
  <aside>
    <div class="rh">남은 일</div>
    <button class="item" data-id="__progress__">
      <span class="iname">진행 현황 — 설비 타입별</span>
      <span class="icount"><em id="pn">0</em>제품</span>
    </button>
    <button class="item" data-id="__holes__">
      <span class="iname">판정·별칭·남은 일</span>
      <span class="icount"><em id="hn">0</em></span>
    </button>
    <div id="rail"></div>
  </aside>
  <main id="main"></main>
</div>
<script id="d" type="application/json">__DATA__</script>
<script>
"use strict";
var D = JSON.parse(document.getElementById('d').textContent);
var rail = document.getElementById('rail'), main = document.getElementById('main');
var cur = '__progress__', ifi = 0, term = '';

function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function pts(m){ return m.ifs.reduce(function(a, x){ return a + x.n; }, 0); }

D.models.sort(function(a, b){ return b.ifs.length - a.ifs.length || pts(b) - pts(a); });
var totDocs = D.docs;
document.getElementById('sDocs').textContent = D.docs;
document.getElementById('sModels').textContent = D.models.length;
document.getElementById('sIfs').textContent = D.totalIfs;
document.getElementById('sPts').textContent = D.totalPoints.toLocaleString();
var holeN = D.alias.length;
document.getElementById('sHole').textContent = holeN;
document.getElementById('hn').textContent = holeN;
document.getElementById('pn').textContent = D.models.length;

// 설비 분류로 묶는다 — 냉동기 31건을 한 줄로 늘어놓으면 압축 방식이 안 보인다.
// 분류 근거는 JCI 카탈로그 제품명의 낱말이고, cat 4단계에 그대로 실려 있다.
var KIND = [['HVAC.PLANT.CHILLER.CENTRIFUGAL','원심식 냉동기'],
            ['HVAC.PLANT.CHILLER.SCREW','스크류식 냉동기'],
            ['HVAC.PLANT.CHILLER.SCROLL','스크롤식 냉동기'],
            ['HVAC.PLANT.CHILLER.RECIP','왕복동식 냉동기'],
            ['HVAC.PLANT.CHILLER.ABSORPTION','흡수식 냉동기'],
            ['HVAC.PLANT.CHILLER','압축 방식 미상'],
            ['HVAC.AIR.RTU','옥상형 공조기']];
var COOL = {airCooling:'공랭', waterCooling:'수냉'};
rail.innerHTML = KIND.map(function(k){
  var list = D.models.map(function(m, i){ return {m:m, i:i}; })
    .filter(function(x){ return x.m.cat === k[0]; });
  if(!list.length) return '';
  return '<div class="rh">' + k[1] + ' <b>' + list.length + '</b></div>'
    + list.map(function(x){
        var cool = (x.m.tags || []).map(function(t){ return COOL[t]; }).filter(Boolean)[0];
        return '<button class="item" data-id="' + x.i + '"><span class="iname">'
          + esc(x.m.model) + (cool ? '<i class="cool">' + cool + '</i>' : '') + '</span>'
          + '<span class="icount"><em>' + x.m.ifs.length + '</em>판 &middot; ' + pts(x.m)
          + '</span></button>';
      }).join('');
}).join('');

var PROTO = {bacnet:'BACnet', modbus:'Modbus', n2:'N2', lon:'LON',
             yorktalk:'York Talk', logix:'Logix', elink:'E-Link'};
function protoName(p){ return PROTO[p] || p; }
// 판 이름은 계통+개정만으로는 안 갈린다 — YK 는 EM/SSS 와 VSD 가 같은 'Rev K 04d' 다.
// 문서 이름이 유일한 구분자라 칩에 함께 보인다.
function chipTail(x){ return x.id.replace(/^[a-z0-9]+-/, ''); }

var COLS = [['n','오브젝트명'],['s','짧은 이름'],['b','BACnet'],['m','Modbus'],['d','N2'],
            ['l','LON'],['y','York Talk'],['k','YT 종별'],['g','Logix'],['u','단위'],
            ['w','R/W'],['a','적용 조건'],['t','상태·열거'],['o','비고'],['p','쪽']];

// ── 진행 현황 ────────────────────────────────────────────────────────────────
// "어디까지 됐나"에 답하는 화면. 두 축으로 본다 — 설비 타입별로 무엇이 쌓였나,
// 그리고 **문서 포털에 있는 것 대비** 얼마나 가져왔나. 뒤쪽이 없으면 "다 했다"를
// 확인할 방법이 없다.
var SITE_KO = {chillers:'냉동기 포털', ductedsystems:'덕트·옥상형 포털', bas:'제어·계측 포털(Metasys)'};
function renderProgress(){
  var byKind = KIND.map(function(k){
    var ms = D.models.filter(function(m){ return m.cat === k[0]; });
    var al = D.alias.filter(function(a){
      return D.models.some(function(m){ return m.id === a.of && m.cat === k[0]; }); });
    return {ko:k[1], n:ms.length,
            ifs:ms.reduce(function(a,m){ return a + m.ifs.length; }, 0),
            pts:ms.reduce(function(a,m){ return a + pts(m); }, 0),
            alias:al.length,
            top:ms.slice().sort(function(a,b){ return pts(b)-pts(a); }).slice(0,3)};
  }).filter(function(x){ return x.n; });

  var h = '<div class="pad"><h2>진행 현황</h2>'
    + '<div class="sub">설비 타입별로 무엇이 쌓였는지, 그리고 <b>문서 포털에 있는 것 대비</b> '
    + '얼마나 가져왔는지. 뒤쪽이 없으면 "다 했다"를 확인할 방법이 없다.</div>'
    + '<div class="tw" style="margin-top:14px"><table><thead><tr>'
    + '<th>설비 타입</th><th>제품</th><th>판</th><th>오브젝트</th><th>별칭</th>'
    + '<th>정격</th><th>큰 것부터</th></tr></thead><tbody>'
    + byKind.map(function(x){
        return '<tr><td class="nm"><b>' + esc(x.ko) + '</b></td>'
          + '<td class="num">' + x.n + '</td><td class="num">' + x.ifs + '</td>'
          + '<td class="num">' + x.pts.toLocaleString() + '</td>'
          + '<td class="num">' + (x.alias || '') + '</td>'
          + '<td class="num" style="color:var(--hole)">0/' + x.n + '</td>'
          + '<td class="nm">' + x.top.map(function(m){
              return esc(m.model.split(' ')[0]) + ' ' + pts(m); }).join(' · ') + '</td></tr>';
      }).join('')
    + '<tr><td class="nm"><b>합계</b></td><td class="num"><b>' + D.models.length + '</b></td>'
    + '<td class="num"><b>' + D.totalIfs + '</b></td>'
    + '<td class="num"><b>' + D.totalPoints.toLocaleString() + '</b></td>'
    + '<td class="num"><b>' + D.alias.length + '</b></td>'
    + '<td class="num" style="color:var(--hole)"><b>0/' + D.models.length + '</b></td>'
    + '<td></td></tr></tbody></table></div>'
    + '<div class="card"><b class="lbl">정격이 왜 0 인가</b>'
    + '이 소스는 <b>BAS 포인트 리스트</b>다. 오브젝트 매핑 자동화는 33제품 전부 되지만, '
    + '시뮬레이터가 쓸 용량·COP·전류는 한 제품도 없다 — 제품 카탈로그가 별도 수집 대상이다.</div>';

  if(D.coverage && D.coverage.length){
    h += '<h3 class="ph">문서 포털 대비 취입률</h3>'
      + '<div class="sub" style="padding:0 0 8px">JCI 문서 카탈로그 스냅샷과 대조했다. '
      + '"후보"는 제목에 포인트 리스트 낌새가 있는 문서다 — 실제 포인트 표가 있는지는 열어 봐야 안다.</div>'
      + '<div class="tw"><table><thead><tr><th>포털</th><th>전체 문서</th><th>후보</th>'
      + '<th>취입</th><th>안 가져온 것의 분류</th></tr></thead><tbody>'
      + D.coverage.map(function(c){
          var pct = c.cand ? Math.round(c.taken * 100 / c.cand) : 0;
          return '<tr><td class="nm"><b>' + esc(SITE_KO[c.site] || c.site) + '</b></td>'
            + '<td class="num">' + c.docs.toLocaleString() + '</td>'
            + '<td class="num">' + c.cand + '</td>'
            + '<td class="num"><b>' + c.taken + '</b> <span style="color:var(--faint)">('
            + pct + '%)</span></td>'
            + '<td class="nm">' + (c.miss.length
                ? c.miss.map(function(m){ return esc(m[0]) + ' ' + m[1]; }).join(' · ')
                : '<span style="color:var(--ok)">없음</span>') + '</td></tr>';
        }).join('')
      + '</tbody></table></div>'
      + '<div class="card"><b class="lbl">냉동기 포털의 안 가져온 31건은 무엇인가</b>'
      + '열어 보니 대부분 <b>SC-EQ 펌웨어 공지 · 배선도 · 번역본 · 제품 카탈로그</b>였다 — '
      + '포인트 표가 아니다. 실제 포인트 표가 있는 문서는 아래 하나뿐이다.</div>';
  }
  if(D.knownGaps && D.knownGaps.length){
    h += '<h3 class="ph">확인된 구멍</h3>'
      + D.knownGaps.map(function(g){
          return '<div class="card hole"><b class="lbl">' + esc(g.what) + '</b>'
            + '<div class="kv"><span>문서 <b>' + esc(g.docs) + '</b></span>'
            + '<span>실측 <b>' + esc(g.found) + '</b></span></div>'
            + '<div style="margin-top:6px">' + esc(g.why) + '</div></div>';
        }).join('');
  }
  return h + '</div>';
}

function renderHoles(){
  var judged = [], merged = 0, split = 0;
  D.models.forEach(function(m){ m.ifs.forEach(function(x){
    if(/한 판으로 묶었다/.test(x.note || '')) merged++;
    if(/별개 판으로 갈랐다/.test(x.note || '')) split++;
    (x.gaps || []).forEach(function(g){ judged.push([m.model, x.id, g]); }); }); });
  var h = '<div class="pad"><h2>판정 · 별칭 · 남은 일</h2>'
    + '<div class="sub">문서 ' + D.docs + '건이 제품 ' + D.models.length + '건 · 판 '
    + D.totalIfs + '개로 정리됐다. 기계가 판단한 것과, 아직 사람이 채워야 하는 것을 나눠 적는다.</div>'
    + '<div class="card"><b class="lbl">판 분리 — 자동 판정</b>'
    + '한 문서 안에 표 블록이 여럿일 때 <b>주소 대역</b>으로 갈랐다. '
    + '다음 블록이 앞 블록의 최대 주소 위에서 시작하면(1~43 → 101~135) 쪽만 넘어간 <b>같은 판</b>이고, '
    + '주소가 다시 처음부터 시작하면(1~43 → 1~43) 한 장치가 같은 주소를 두 번 쓸 수 없으므로 <b>별개 판</b>이다.'
    + '<div class="kv" style="margin-top:8px">'
    + '<span>이어져서 합친 판 <b>' + merged + '</b></span>'
    + '<span>겹쳐서 가른 판 <b>' + split + '</b></span>'
    + '<span>문서 ' + D.docs + ' → 판 <b>' + D.totalIfs + '</b></span></div></div>'
    + '<div class="card"><b class="lbl">별칭 제품 ' + D.alias.length + '건 — 이제 찾아진다</b>'
    + '한 문서가 제품을 여럿 덮을 때 목록은 주 제품에만 두고(복제 금지), 나머지 코드는 '
    + '<b>어느 모델의 어느 판이 덮는지만</b> 가리키는 별칭 모델로 세웠다.'
    + '<div class="tw" style="margin-top:10px"><table><thead><tr><th>제품 코드</th><th>목록이 있는 곳</th><th>근거</th></tr></thead><tbody>'
    + D.alias.map(function(a){ return '<tr><td class="mono">' + esc(a.code) + '</td><td class="nm">'
        + esc(a.summary.replace(/^.*?— /, '')) + '</td><td class="mono">'
        + esc((a.why || '').replace('문서 제목의 제품 나열 — ', '')) + '</td></tr>'; }).join('')
    + '</tbody></table></div></div>'
    + '<div class="card hole"><b class="lbl">정격이 없다 — 제품 ' + D.models.length + '건 전부</b>'
    + '이 소스는 <b>BAS 포인트 리스트</b>뿐이다. 시뮬레이터가 소비전력·능력을 계산하려면 '
    + '용량·COP·전류가 있는 <b>제품 카탈로그</b>를 따로 수집해야 한다(짝 규칙). '
    + '지금 상태로는 매핑 자동화까지만 쓸 수 있다.</div>';
  if(judged.length) h += '<div class="card warn"><b class="lbl">아직 사람이 볼 것 ' + judged.length + '건</b>'
    + '<div class="tw" style="margin-top:10px"><table><thead><tr><th>제품</th><th>판</th><th>내용</th></tr></thead><tbody>'
    + judged.map(function(r){ return '<tr><td class="nm">' + esc(r[0]) + '</td><td class="mono">' + esc(r[1])
        + '</td><td>' + esc(r[2]) + '</td></tr>'; }).join('')
    + '</tbody></table></div></div>';
  return h + '</div>';
}

function render(){
  document.querySelectorAll('aside .item').forEach(function(b){
    b.setAttribute('aria-current', String(b.dataset.id) === String(cur)); });
  if(cur === '__progress__'){ main.innerHTML = renderProgress(); return; }
  if(cur === '__holes__'){ main.innerHTML = renderHoles(); return; }
  var m = D.models[cur | 0];
  var it = m.ifs[Math.min(ifi, m.ifs.length - 1)];
  var use = COLS.filter(function(c){
    return it.points.some(function(p){ return p[c[0]] !== undefined; }); });
  var rows = it.points.filter(function(p){
    return !term || JSON.stringify(p).toLowerCase().indexOf(term) >= 0; });
  var h = '<div class="pad"><h2>' + esc(m.model) + '</h2>'
    + '<div class="sub">' + esc(m.cat) + ' &middot; 계열 ' + esc(m.equipId)
    + ' &middot; 포인트 리스트 <b>' + m.ifs.length + '판</b> &middot; 오브젝트 <b>' + pts(m) + '</b></div>'
    + '<div class="chips">' + m.ifs.map(function(x, i){
        var rv = [x.rev.doc, x.rev.block, x.rev.firmware].filter(Boolean).join(' · ');
        return '<button class="chip" data-if="' + i + '" aria-pressed="' + (i === ifi) + '">'
          + '<span class="fam">' + esc(x.family) + '</span>'
          + '<span class="meta">' + esc([rv, chipTail(x)].filter(Boolean).join(' · ')) + '</span>'
          + '<span class="meta">' + esc(x.protocols.map(protoName).join(' · ')) + '</span>'
          + '<span class="np">' + x.n + '점</span></button>';
      }).join('') + '</div>'
    + '<div class="card"><b class="lbl">이 판의 출처</b><div class="kv">'
    + '<span class="mono">' + esc(it.src) + (it.pages ? ' p' + it.pages.join('~') : '') + '</span>'
    + (it.appliesTo ? '<span>덮는 제품 <b class="mono">' + esc(it.appliesTo.join(' · ')) + '</b></span>' : '')
    + '</div><div style="margin-top:6px;color:var(--dim)">' + esc(it.label) + '</div></div>';
  if(it.excluded) h += '<div class="card"><b class="lbl">포인트로 세지 않은 행</b>'
    + Object.keys(it.excluded).map(function(k){ return esc(k) + ' <b>' + it.excluded[k] + '</b>행'; }).join(' · ')
    + ' — 예약 슬롯·개정이력·NOTES 같은 것. 조용히 빼지 않고 여기 적는다.</div>';
  if(it.gaps) h += '<div class="card warn"><b class="lbl">남은 판단</b>' + esc(it.gaps.join(' / ')) + '</div>';
  if(m.crosscheck) h += '<div class="card"><b class="lbl">교차 대조</b>' + esc(m.crosscheck) + '</div>';
  h += '<div class="tools"><input type="search" id="q" placeholder="이 판에서 찾기 — 이름 · 주소 · 단위" value="'
    + esc(term) + '"><span class="rowcount">' + rows.length + ' / ' + it.points.length + '행</span></div>'
    + '<div class="tw"><table><thead><tr>'
    + use.map(function(c){ return '<th>' + c[1] + '</th>'; }).join('') + '</tr></thead><tbody>'
    + rows.map(function(p){ return '<tr>' + use.map(function(c){
        var v = p[c[0]];
        var cls = (c[0] === 'n' || c[0] === 'o' || c[0] === 't') ? 'nm' : 'num mono';
        return '<td class="' + cls + '">' + esc(v === undefined ? '' : v) + '</td>'; }).join('') + '</tr>';
      }).join('')
    + '</tbody></table>' + (rows.length ? '' : '<div class="empty">찾은 게 없어요</div>') + '</div></div>';
  main.innerHTML = h;
  main.querySelectorAll('.chip').forEach(function(b){
    b.addEventListener('click', function(){ ifi = +b.dataset.if; term = ''; render(); }); });
  var q = document.getElementById('q');
  if(q) q.addEventListener('input', function(){
    term = q.value.trim().toLowerCase();
    var at = q.selectionStart;
    render();
    var q2 = document.getElementById('q');
    if(q2){ q2.focus(); q2.setSelectionRange(at, at); } });
}
document.querySelectorAll('aside .item').forEach(function(b){
  b.addEventListener('click', function(){ cur = b.dataset.id; ifi = 0; term = ''; render();
    main.scrollTop = 0; }); });
render();
</script>
"""


# 포털 스냅샷에서 '포인트 표가 있을 법한 문서'를 고르는 힌트. 취입률을 재는 데만 쓴다 —
# 이걸로 파싱하지 않는다(파싱 판정은 표 머리글로 한다).
PT_HINT = re.compile(r"points?\s*list|data\s*map|point\s*map|BAS\b|E-?Link|SC-?EQ|"
                     r"BACnet|Modbus|N2\b|LON\b|protocol", re.I)

# 눈으로 확인한 구멍. **원문을 열어 센 것만 적는다** — 짐작은 적지 않는다.
KNOWN_GAPS = [
    {"what": "YKN2Open BMS 게이트웨이",
     "docs": "영문 1건 + 번역 7건 (chillers 포털)",
     "found": "Modbus 38행 · BACnet 51행 · 노드 설정 17행 = 106행 (2026-08-18 원문 실측)",
     "why": "표가 FieldServer 계열이라(Map Descriptor Name · Data Array Name) 지금 파서 "
            "넷 중 어느 것도 안 잡는다. 9번째 계통이다."},
    {"what": "정격 (용량·COP·전류)",
     "docs": "이 소스에 없음",
     "found": "제품 33건 전부 0",
     "why": "BAS 포인트 리스트 포털이라 정격이 실리지 않는다. York 제품 카탈로그를 "
            "따로 수집해야 시뮬레이터가 쓸 수 있다(짝 규칙)."},
]


def coverage():
    """포털 스냅샷 대비 취입률. 스냅샷이 없으면 빈 값 — 화면이 그 절을 생략한다."""
    if not os.path.exists(SNAPSHOT):
        return []
    with open(SNAPSHOT, encoding="utf-8") as f:
        snap = json.load(f)
    taken = {i for i, _s, _n in SRC.JCI_BAS_POINTS}
    out = []
    for site, lst in snap.items():
        cand = [x for x in lst if PT_HINT.search(x.get("title") or "")]
        got = [x for x in cand if x["id"] in taken]
        miss = collections.Counter()
        for x in cand:
            if x["id"] in taken:
                continue
            meta = {m.get("key"): (m.get("values") or [""])[0]
                    for m in (x.get("metadata") or [])}
            miss[meta.get("category") or "(분류 없음)"] += 1
        out.append({"site": site, "docs": len(lst), "cand": len(cand), "taken": len(got),
                    "miss": miss.most_common(6)})
    return out


def _cell(v):
    """중첩 값을 한 칸에 넣을 수 있는 글자로. 원문 표기(raw)가 있으면 그걸 쓴다."""
    if v is None:
        return None
    if isinstance(v, dict):
        if v.get("raw") not in (None, ""):
            return str(v["raw"])
        return " · ".join("%s=%s" % (k, _cell(x)) for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(str(_cell(x)) for x in v)
    return v


def view_point(p):
    """포인트 레코드 → 화면용 짧은 열쇠. 값이 있는 것만 담는다."""
    c = p.get("common") or {}
    b = p.get("blocks") or {}
    pv = p.get("provenance") or {}
    bac, mb, n2 = (b.get("bacnet") or {}, b.get("modbus") or {}, b.get("n2") or {})
    lon, yt, lg = (b.get("lon") or {}, b.get("yorktalk") or {}, b.get("logix") or {})
    obj = ""
    if bac.get("objectType"):
        obj = bac["objectType"] + ("" if bac.get("instance") is None else str(bac["instance"]))
        if bac.get("alternates"):
            obj += " /" + ",".join(bac["alternates"])
    row = {
        "n": c.get("name") or lon.get("nvName") or "", "s": c.get("shortName"),
        "b": obj or None, "m": mb.get("address"),
        "d": ("%s %s" % (n2.get("pointType") or "", n2.get("address"))).strip() if n2 else None,
        "l": lon.get("snvtType"),
        "y": yt.get("coord") or yt.get("pageRef") or yt.get("asciiPageRef"),
        "k": yt.get("pointType"), "g": lg.get("tag"),
        "u": (c.get("unitIP") or c.get("unitSI") or c.get("unitIPRaw") or c.get("unitSIRaw")),
        "w": c.get("readWrite"), "a": _cell(c.get("availability")),
        "t": _cell(c.get("states") or c.get("statesRef")),
        "o": c.get("note"), "p": pv.get("sourcePage"),
    }
    return {k: v for k, v in row.items() if v not in (None, "", [], {})}


def view_data():
    """저장된 모델에서 화면 데이터를 만든다 — 정본은 data/models 다."""
    out = {"models": [], "alias": []}
    for path in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("extractor") != "vendor_jci":
            continue
        if d.get("aliasOf"):
            out["alias"].append({"code": d["model"], "of": d["aliasOf"],
                                 "why": d.get("classifiedBy", ""), "summary": d["summary"]})
            continue
        m = {"id": d["id"], "model": d["model"], "equipId": d["equipId"], "cat": d["cat"],
             "tags": d.get("tags", []), "ifs": [],
             "crosscheck": (d.get("crosscheck") or {}).get("unverifiable") or ""}
        for it in d.get("interfaces") or []:
            m["ifs"].append({
                "id": it["id"], "label": it["label"], "family": it["family"],
                "protocols": it["protocols"], "rev": it.get("revision") or {},
                "src": it["sourceFile"], "pages": it.get("sourcePages"),
                "n": it["pointCount"], "excluded": it.get("excluded"),
                "appliesTo": it.get("appliesTo"), "gaps": it.get("gaps"),
                "note": it.get("note"),
                "points": [view_point(p) for p in it.get("points") or []]})
        out["models"].append(m)
    out["docs"] = len({i["src"] for m in out["models"] for i in m["ifs"]})
    out["totalIfs"] = sum(len(m["ifs"]) for m in out["models"])
    out["totalPoints"] = sum(i["n"] for m in out["models"] for i in m["ifs"])
    out["coverage"] = coverage()
    out["knownGaps"] = KNOWN_GAPS
    return out


def export(out_path=None):
    out_path = out_path or os.path.join(HERE, "..", "review", "jci-ingest.html")
    data = view_data()
    html = VIEW.replace("__DATA__", json.dumps(data, ensure_ascii=False,
                                               separators=(",", ":")))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("  %s" % os.path.normpath(out_path))
    print("  제품 %d · 문서 %d · 판 %d · 오브젝트 %d · 별칭 %d · %.1f MB"
          % (len(data["models"]), data["docs"], data["totalIfs"], data["totalPoints"],
             len(data["alias"]), os.path.getsize(out_path) / 1024.0 / 1024.0))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="JCI 포인트 리스트 취입")
    ap.add_argument("--route", action="store_true", help="계통 판정만 (빠름)")
    ap.add_argument("--apply", action="store_true", help="모델 레코드 생성")
    ap.add_argument("--dry", action="store_true", help="파싱은 하되 쓰지 않는다")
    ap.add_argument("--no-crosscheck", action="store_true", help="교차 대조 건너뛰기")
    ap.add_argument("--export", action="store_true",
                    help="검토 화면 review/jci-ingest.html 을 낸다")
    ap.add_argument("--refresh", action="store_true",
                    help="취입한 모델의 메타만 다시 계산 (PDF 재파싱 없음)")
    ap.add_argument("--only", help="저장 이름에 이 글자가 든 문서만")
    a = ap.parse_args(argv)
    if a.export:
        return export()
    if a.refresh:
        return refresh()
    if a.route:
        route(only=a.only)
        return 0
    if a.apply or a.dry:
        return apply(only=a.only, dry=a.dry, crosscheck=not a.no_crosscheck)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
