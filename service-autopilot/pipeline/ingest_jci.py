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
# IOM 본문형 판을 가리키는 표식. `--refresh` 가 이 판을 건너뛰는 근거다
# (파서·문서 성격이 달라 E-Link 규칙으로 다시 짜면 안 된다).
IOM_NOTE = "파서 vendor_jci_ipu · 원문 IOM 본문"
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
    # 9번째 계통 — 게이트웨이(FieldServer QuickServer). 앞 넷과 달리 장비가 아니라
    # **변환기**가 내는 표라 열 어휘가 통째로 다르다. marks_of 는 표의 0행만 보는데
    # 이 계통은 0행이 표 제목('Modbus variables')이고 진짜 머리글은 그 아래다.
    ("YKN2Open", "vendor_jci_ykn2open",
     r"Bacnet\s*variables|Modbus\s*variables|Map\s*Descriptor\s*Name"),
    # 10번째 계통 — 통신 카드 **자신의** 설정 포인트. 위 'SC-EQ' 계통이 냉동기가 카드를
    # 통해 내보내는 목록인 데 반해, 이 표 6점은 카드의 BACnet 장치 이름·인스턴스 ID·
    # 인코딩·단위계·붙어 있는 냉동기 기종이다.
    # ⚠ 표식을 'Point name' 하나로 잡으면 안 된다 — 흔한 낱말이라 남의 계통 표가 걸린다.
    #   다섯 낱말이 **이 순서로 붙은 표 머리글**만 이 계통이다(marks_of 는 표 0행을 본다).
    ("SC-EQ/Config", "vendor_jci_sceq_config",
     r"Point\s*name\s*\|\s*BACnet\s*\|\s*Modbus\s*\|\s*N2\b"),
]

# 같은 문서의 번역본. 내용이 같아 등록하지 않는다 — 다만 포털 취입률을 셀 때
# '안 가져온 것'으로 남으므로 어느 것이 무엇의 번역인지 근거를 남긴다.
TRANSLATIONS = {
    "bdk7s53yQ5tftUD6MrJq9g": ["7uJN9xsUvPTIs732TjFlWQ",   # pt
                               "0DZBTy5Dzl4w1f3LcczfdQ",   # es
                               "7GjH3ZdAZVCKh4ryibKb9A",   # de
                               "DR7Cfv2Z_oXplT3b_6ioCg",   # nl
                               "e_e_RWK3yhqgoEujgdbfJQ",   # it
                               "F8c~Vlv0OwMaJ7YndUL4cg"],  # fr
}

# 같은 표를 싣는 다른 문서. 판은 하나만 세우고 나머지는 **근거**로 남긴다 —
# 대조한 사실이 사라지면 다음 사람이 '안 가져온 문서'로 보고 또 연다.
CORROBORATED = {
    "9cg6yK~zvn2rx75l2aehJA": [
        ("2P~o78Hw6Zd~F~_z12AEMg",
         "SC-EQ Communication Card Installation Instructions (450.50-N1) 46쪽 "
         "'Table 8 - Manual Modbus addresses' 에 같은 6점이 있다. 글자 흐름(get_text)으로 "
         "따로 읽어 대조했다 — 이름·BACnet·Modbus·N2 네 칸이 여섯 행 모두 같고, 다른 것은 "
         "'N/A'/'n/a' 대소문자와 설명문 어투뿐이다. 값 표(Table 1, 44종)를 가진 SI0371 을 "
         "판으로 삼았다 — 450.50-N1 은 그 자리에 \"Refer to SI0371.\" 이라 적어 값 표를 "
         "이쪽에 넘긴다."),
    ],
}

# 덮는 제품을 **제목만으로는 정할 수 없는** 문서. 짐작이 아니라 원문 문장을 옮겨
# 적고 쪽수를 남긴다. 두 가지가 있다.
#   ⑴ 제목엔 없고 본문이 밝힌다 → 본문이 말한 코드를 적는다(YKN2Open).
#   ⑵ 제목이 코드를 나열하지만 그게 '이 목록이 덮는 제품'이 아니다 → **빈 목록**을 적고
#      왜 아닌지를 남긴다. 빈 목록도 판단이다 — applies_to() 로 흘려보내면 안 된다.
BODY_APPLIES = {
    "bdk7s53yQ5tftUD6MrJq9g": {
        "codes": ["RTC", "RTH", "VAC", "VAH", "VCH", "VIR"],
        "why": "덮는 제품은 제목이 아니라 본문이 밝힌다 — 원문 4쪽 \"cold units and "
               "heat pumps from Roomtop (RTC-RTH-L), ACTIVA Rooftop, Large ACTIVA "
               "Rooftop, VITALITY VAC/VAH/VCH-VIR of R410A equipped with the YKN2Open "
               "control\". 게이트웨이 한 대가 장비 최대 5대를 덮는다(원문 7쪽).",
    },
    "9cg6yK~zvn2rx75l2aehJA": {
        "codes": [],
        "why": "제목이 냉동기 11종(YVAA·YVFA·YVWA·YCAV·YCIV·YCAL·YCUL·YCRL·YLAA·YLAE·"
               "YLUA)을 나열하지만 **이 목록이 덮는 제품이 아니다** — 그 냉동기들은 이 "
               "펌웨어 릴리스가 걸리는 장비이고, 표 6점은 냉동기의 값이 아니라 SC-EQ 카드 "
               "자신의 설정값이다(BACnet 장치 이름·인스턴스 ID·인코딩·단위계·기종 선택). "
               "appliesTo 로 적으면 별칭 생성기가 냉동기 코드의 목록 소재지를 통신 카드로 "
               "돌려 YVFA·YCIV 별칭이 냉동기에서 카드로 옮겨 붙는다(설비 분류까지 따라간다). "
               "카드가 말을 걸 수 있는 기종은 'Manual Select Chiller Model' 포인트의 "
               "states 44종에 그대로 실려 있다 — 그쪽이 문서가 실제로 밝힌 자리다.",
    },
}

# JCI 카탈로그의 prodname 이 **문서가 말하는 제품**이 아닌 것.
# khub 의 prodname 은 '이 문서가 걸리는 제품 목록'이라 SI0371 에는 냉동기 11종이 붙어
# 있고 catalog() 가 쓰는 첫 값이 'YCAL Scroll Chiller' 다. 그대로 두면 SC-EQ 통신 카드의
# 설정 포인트 6점이 YCAL 냉동기의 목록으로 들어간다 — 냉동기가 자기 것이 아닌 오브젝트를
# 갖게 되는 셈이다. 제품명은 **문서 자신이 밝힌 것**만 적는다(지어내지 않는다):
# 짝 문서 450.50-N1 의 제목이 'SC-EQ Communication Card Installation Instructions' 이고,
# 그 13쪽 표가 'Microboard number | SC-EQ/install kit | Equipment model',
# 18쪽 부품표가 'P/N 031-03610-000 · Gateway SC-EQ B' 로 카드를 하나의 부품으로 센다.
PROD_OF = {
    "9cg6yK~zvn2rx75l2aehJA": "SC-EQ Communication Card",
}

# 모델 단위의 **판단** 근거. 문서에서 자동으로 나오지 않는 결정을 적는 자리다 —
# 재취입(--apply)이 gap 을 다시 짜므로 모델 파일을 손으로 고치면 다음 실행에 사라진다.
MODEL_GAP = {
    "SC-EQ Communication Card":
        "결정(2026-08-31) — 이 6점을 어느 냉동기가 아니라 **카드 자신을 제품으로 세워** "
        "붙였다. ⑴ 표의 여섯 점은 냉동기의 값이 아니라 카드의 값이다(카드의 BACnet 장치 "
        "이름·인스턴스 ID·문자 인코딩·단위계·붙어 있는 기종 선택). 냉동기 하나를 골라 "
        "붙이면 임의 선택이고, 이 카드를 쓰는 SC-EQ 문서 20건의 제품 전부에 복제하면 "
        "'같은 목록을 제품 수만큼 복제하지 않는다'(interfaces.appliesTo)를 어긴다. "
        "⑵ 선례가 있다 — YKN2Open 게이트웨이도 게이트웨이 자체를 제품으로 세웠다"
        "(johnson-controls-york-ykn2open-control-board). ⑶ 제품이 실재한다는 근거는 짝 "
        "문서 450.50-N1 이다: 제목이 'SC-EQ Communication Card Installation Instructions' "
        "이고 13쪽 표가 'Microboard number | SC-EQ/install kit | Equipment model', 18쪽 "
        "부품표가 'P/N 031-03610-000 · Gateway SC-EQ B' 로 카드를 하나의 부품으로 센다. "
        "⑷ 계열을 e16 으로 둔 근거: data/equips/e16.json 이 '제어기·판넬은 장비 대장이 "
        "아니라 통신 토폴로지로 관리한다'고 못박는데, 이 모델은 정격 없이 포인트만 갖는 "
        "통신 토폴로지 노드라 그 규정과 어긋나지 않는다. YKN2Open 이 e5(옥상형)로 간 것과 "
        "갈린 이유는 근거의 유무다 — 그쪽은 제품명이 설비 종류를 안 밝혀 JCI 문서 분류"
        "('Rooftop Packaged Unit' = 덮는 장비)를 빌렸지만, 이쪽은 문서 두 건의 분류가 냉동기 "
        "다섯 종류로 흩어져 덮는 장비 하나를 못 가리키고 제품명이 스스로 '통신 카드'라고 "
        "밝힌다. ⑸ Haystack 4 에 `gateway` 정의는 없어 지어내지 않고 `controller`"
        "(lib:phIct, 'Microprocessor based device used in a control system … or via "
        "network protocols')를 붙였다.",
}

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
# 제목이 밝힌 펌웨어 판 — 'SC-EQ Firmware 3.0.0.1114'. 등록 문서 58건 중 이 한 건만
# 걸린다(실측). 목록이 펌웨어에 매인 계통이 있어 판 구분으로 남긴다.
FW = re.compile(r"\bFirmware\s+([\d][\d.]*)", re.I)

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

# JCI 카탈로그의 문서 분류(category) — **제조사 자신의 분류**라 두 번째 근거로 쓴다.
# 제품명에 방식이 안 적힌 제품이 4건 있었는데 그중 3건을 이걸로 채웠다
# (CR→원심 · YVWH/YVWE/YGWH→스크류 수냉 · YMAE→스크롤 공랭).
# ⚠ 방식을 안 밝히는 분류가 있다('Heat Pump'·'Condensing Unit') — 그때는 미상으로 남긴다.
CATEGORY = {
    "Centrifugal": ("CENTRIFUGAL", None),
    "Screw Air-Cooled": ("SCREW", "airCooling"),
    "Screw Water-Cooled": ("SCREW", "waterCooling"),
    "Scroll Air-Cooled": ("SCROLL", "airCooling"),
    "Scroll Water-Cooled": ("SCROLL", "waterCooling"),
    "Reciprocating": ("RECIP", None),
    "Absorption": ("ABSORPTION", None),
}
MECH_TAG = {"CENTRIFUGAL": "chiller-centrifugal", "SCREW": "chiller-rotaryScrew",
            "RECIP": "chiller-reciprocal", "ABSORPTION": "chiller-absorption",
            "SCROLL": None}


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
                     "category": m.get("category", ""), "site": m.get("site", "")})
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
    prod = (PROD_OF.get(row["id"]) or row["prod"]
            or BLANK_PROD.get(row["id"]) or row["title"][:40])
    return MERGE.get(prod, prod), prod


def equip_of(name, category=""):
    """제품명과 문서 분류로 계열·분류·태그를 정한다.

    설비별로 갈라 보려면 계열(e9) 하나로는 부족하다 — 냉동기 31건이 한 덩어리가 된다.
    근거는 둘이고 순서가 있다.
      ① 제품명 — JCI 가 대개 방식을 이름에 적는다('YCAS Air Cooled Screw Chiller')
      ② 문서 분류(category) — 제조사 자신의 분류. 이름에 방식이 없을 때 채운다
    **문서에 없는 것은 만들지 않는다** — 둘 다 안 밝히면 미상으로 남긴다(AWHP).

    ⚠ 둘이 어긋나면 **이름을 따르되 gap 에 적는다.** 실측 1건 — YIA ParaFlow
    Absorption 은 이름이 흡수식이라고 밝히는데 카탈로그는 Centrifugal 분류에 넣어
    두었다. 더 구체적인 근거는 이름이지만, 어긋났다는 사실 자체가 사라지면 안 된다.
    """
    t = name.lower()
    # 통신 카드는 **장비가 아니다** — 장비의 프로토콜을 BAS 로 바꿔 주는 부품이고,
    # 제품명이 그렇게 밝힌다. 이 가드가 없으면 아래에서 JCI 문서 분류(category)가
    # 그대로 굳는다: SC-EQ 카드 문서의 분류는 'Screw Air-Cooled'·'Absorption' 인데
    # 그건 **이 문서가 걸리는 냉동기**의 분류이지 카드의 분류가 아니다 — 카드가
    # 스크류 공랭 냉동기가 되어 냉동기 목록 사이에 서게 된다.
    # 계열은 e16(계량·계측·제어기) — 그 사전이 "제어기·판넬은 장비 대장이 아니라
    # 통신 토폴로지로 관리한다"고 못박은 자리다. 태그는 Haystack 4 의 `controller`
    # ("Microprocessor based device used in a control system … or via network
    # protocols", lib:phIct). Haystack 4 에 `gateway` 는 **없다** — 지어내지 않는다.
    if "communication card" in t:
        why = ("통신 카드는 장비가 아니라 장비의 프로토콜을 BAS 로 바꿔 주는 부품이다 — "
               "제품명 %r 이 그렇게 밝힌다. JCI 문서 분류(category)는 이 문서가 걸리는 "
               "냉동기의 분류라 따르지 않았다." % name)
        return "e16", "HVAC.FIELD.CONTROLLER", "controller", ["controller"], [why], why
    if "rooftop" in t or "ypal" in t:
        return "e5", "HVAC.AIR.RTU", "rooftop", ["rooftop"], [], None
    # 제품명이 설비 종류를 안 밝히는 것이 있다 — 'YKN2Open Control Board' 는 장비가
    # 아니라 **게이트웨이 이름**이다. 그때 두 번째 근거인 JCI 문서 분류를 쓴다.
    # ⚠ 기존 옥상형 3건의 분류는 'Packaged Rooftop Units'(다른 문자열)라 이 규칙이
    #   닿지 않는다 — 회귀 없음을 확인하고 넣었다.
    if (category or "").strip() == "Rooftop Packaged Unit":
        why = ("설비 종류를 제품명 %r 이 안 밝혀 JCI 문서 분류 'Rooftop Packaged Unit' "
               "에서 가져왔다" % name)
        return "e5", "HVAC.AIR.RTU", "rooftop", ["rooftop"], [why], why
    tags, gaps = ["chiller"], []
    suffix = None
    for word, sfx, _tag in MECHANISM:
        if word.lower() in t:
            suffix = sfx
            break
    cmech, ccool = CATEGORY.get((category or "").strip(), (None, None))
    if suffix and cmech and suffix != cmech:
        gaps.append("압축 방식이 이름과 문서 분류에서 다르다 — 이름 %r vs 분류 %r. "
                    "더 구체적인 이름을 따랐다." % (suffix, category))
    if not suffix and cmech:
        suffix = cmech
        gaps.append("압축 방식을 제품명이 안 밝혀 JCI 문서 분류 %r 에서 가져왔다" % category)
    cat = "HVAC.PLANT.CHILLER" + ("." + suffix if suffix else "")
    if suffix:
        tag = MECH_TAG.get(suffix)
        if tag:
            tags.append(tag)
        else:
            gaps.append("압축 방식 '%s' 는 Haystack 4 chillerMechanism 에 값이 없다"
                        "(chiller-scroll 미정의) — 태그를 지어내지 않는다" % suffix)
    cool = None
    for word, tg in COOLING:
        if word.lower() in t:
            cool = tg
            break
    if not cool and ccool:
        cool = ccool
    if cool:
        tags.append(cool)
    if "heat pump" in t:
        tags.append("heatPump")
    return "e9", cat, "chiller", tags, gaps, None


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


TAB_FOOT = re.compile(r"Tab:\s*(\S.*?)\s*$")


def tab_name(file_name, page):
    """쪽 꼬리말의 `Tab: <시트 이름>` 을 읽는다. 없으면 None.

    JCI E-Link 문서는 엑셀 워크북을 찍어 낸 것이라 **모든 쪽 꼬리말에 시트 이름**이
    박혀 있다 — 'Tab: YCWS Style F,G' · 'Tab: YS SSS' · 'Tab: without VSD'.
    블록 제목이 없는 판을 '구간 2' 로 부르고 있었는데, 문서는 처음부터 이름을
    달고 있었다(이름 없던 판 37개 전부에 있었다 — 실측 누락 0건).
    """
    if not file_name or not page:
        return None
    path = os.path.join(DATA, "raw", file_name)
    if not os.path.exists(path):
        return None
    try:
        import fitz
        doc = fitz.open(path)
        try:
            if not 1 <= page <= doc.page_count:
                return None
            for line in doc[page - 1].get_text().split("\n"):
                m = TAB_FOOT.search(line.strip())
                if m:
                    return re.sub(r"\s{2,}", " ", m.group(1)).strip()
        finally:
            doc.close()
    except Exception:
        return None
    return None


def build_interfaces(row, fam, rows, skipped, block=None):
    """문서 하나 → 판(인터페이스) 목록. 한 문서가 판을 여럿 담을 수 있다."""
    base = iface_id(row["file"])
    body = BODY_APPLIES.get(row.get("id") or "")
    # ⚠ `or` 로 이으면 **빈 목록이 판단으로 안 선다** — BODY_APPLIES 가 "제목의 코드는
    #   덮는 제품이 아니다"라고 적어 둔 문서에서 다시 applies_to(제목) 로 흘러간다.
    codes = body["codes"] if body else applies_to(row["title"])
    rev0 = {}
    m = REV.search(row["title"]) or REV.search(row["file"])
    if m:
        rev0["doc"] = "Rev " + re.sub(r"[\s_]+", " ", m.group(1)).strip()
    # 펌웨어 판 — 이 목록이 그 펌웨어에서만 존재하는 계통이 있다. SC-EQ 설정 포인트
    # 6점은 원문 1쪽이 "Provides BAS system writable configuration points" 라고 밝힌
    # 3.0.0.1114 릴리스의 새 항목이다. 판 구분을 잃으면 구형 카드에도 있는 줄 안다.
    mf = FW.search(row["title"] or "")
    if mf:
        rev0["firmware"] = mf.group(1)
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
        # 판 이름은 ⑴ 블록 제목 ⑵ 쪽 꼬리말의 시트 이름 ⑶ 마지막에야 '구간 N' 이다.
        tab = tab_name(row["file"], pages[0] if pages else None)
        if tab:
            rev["tab"] = tab
        if len(parts) > 1:
            rev["block"] = (titles[0] if titles else None) or tab or "구간 %d" % n
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
        if body:
            it.setdefault("gaps", []).append(body["why"])
        # 같은 표를 싣는 다른 문서를 대조하고 판에서 뺐다는 사실을 판에 남긴다
        for other_id, why_dup in CORROBORATED.get(row.get("id") or "", ()):
            it.setdefault("gaps", []).append("%s (문서ID %s)" % (why_dup, other_id))
        gaps = []
        if len(fams) > 1:
            gaps.append("한 문서에 계통이 섞였다: %s"
                        % ", ".join("%s %d점" % kv for kv in fams.most_common()))
        if why:
            it["note"] = why
        out.append(it)
    # 판이 어느 제품 것인지는 **판 이름이 밝힌다**. E-Link 문서는 제품별로 시트를
    # 나눠 두고 꼬리말에 시트 이름을 박아 둔다 — 'YCWS Style F,G' / 'YCRS-REMOTE
    # Style F,G', 'YS Standard' / 'YS SSS' / 'YN Standard' / 'YN SSS'.
    # 이름이 덮는 제품 중 **딱 하나**를 지목할 때만 좁힌다. 'Master'·'without VSD'
    # 처럼 제품을 안 밝히는 이름이면 문서가 안 가른 것이니 그대로 둔다.
    if codes and len(codes) > 1:
        picked = {}
        for it in out:
            nm = (it.get("revision") or {}).get("block") or ""
            hit = [c for c in codes if re.search(r"\b%s\b" % re.escape(c), nm, re.I)]
            if len(hit) == 1:
                picked[it["id"]] = hit[0]
        # 덮는 제품이 하나도 안 빠지고 갈렸을 때만 반영한다 — 일부만 가려지면
        # 나머지 판이 어느 제품인지 여전히 모르는 셈이라 문서를 앞서가게 된다.
        if picked and set(picked.values()) == set(codes) and len(picked) == len(out):
            for it in out:
                it["appliesTo"] = [picked[it["id"]]]
                it.setdefault("gaps", []).append(
                    "판 이름이 제품을 밝혀 %s 만 덮는 것으로 좁혔다" % picked[it["id"]])
        elif len(out) == len(codes):
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
        dcats = collections.Counter(r["category"] for r, _p in items if r.get("category"))
        equip, cat, tag, tags, cgaps, basis = equip_of(
            key, dcats.most_common(1)[0][0] if dcats else "")
        mid = S.model_id(VENDOR, key)
        n = sum(i["pointCount"] for i in ifaces)
        rec = {
            "id": mid, "equipId": equip, "vendor": VENDOR, "model": key, "name": key,
            "cat": cat, "tag": tag, "tags": tags, "status": "active",
            # ⚠ 근거는 **실제로 쓴 것**을 적는다. 제품명이 설비 종류를 안 밝혀
            #   문서 분류로 간 건은 그렇게 적어야 나중에 되짚을 수 있다.
            "classifiedBy": basis or
                            "JCI 카탈로그 제품명 %r 의 낱말 (압축 방식·응축 방식)" % key,
            "summary": "BAS 포인트 리스트 %d건에서 취입 — 오브젝트 %d점" % (len(ifaces), n),
            "has": {"spec": False, "points": True}, "ede": False,
            "spec": [], "io": [], "elec": None,
            # 통신표는 **프로토콜당 한 줄**이다. 판마다 한 줄씩 내면 같은 프로토콜이
            # 판 수만큼 되풀이돼(YT 12줄) 모델 단추의 프로토콜 배지까지 중복된다.
            "comm": comm_rows(ifaces),
            "points": [],
            "gap": "정격·형번이 없다 — BAS 포인트 문서만 있고 제품 카탈로그는 따로 수집해야 한다."
                   + (" " + " / ".join(cgaps) if cgaps else "")
                   + (" " + " / ".join(notes) if notes else "")
                   + (" " + MODEL_GAP[key] if key in MODEL_GAP else ""),
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
    """저장 이름 → (문서ID, 제목, 제품명, 문서 분류). 취입 뒤에도 근거를 되찾을 수 있어야 한다."""
    cat = catalog()
    out = {}
    for doc_id, _site, name in SRC.JCI_BAS_POINTS:
        m = cat.get(doc_id) or {}
        out[name] = (doc_id, m.get("title", ""),
                     m.get("prod", "") or BLANK_PROD.get(doc_id, ""), m.get("category", ""))
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
        # IOM 본문형(vendor_jci_ipu) 판은 **손대지 않는다**. 파서도 문서 성격도 달라
        # E-Link 규칙으로 다시 짜면 라벨·주석이 날아가고, `_doc_meta()` 에 IOM 문서가
        # 없어 설비 분류가 제품명 낱말로 되돌아간다(Versecon 이 공조기 → 냉동기로
        # 뒤집혔다). 그대로 통과시키고 E-Link 판만 다시 짠다.
        keep = [it for it in m["interfaces"] if IOM_NOTE in (it.get("note") or "")]
        todo = [it for it in m["interfaces"] if IOM_NOTE not in (it.get("note") or "")]
        if not todo:
            continue
        by_file = collections.OrderedDict()
        for it in todo:
            f0 = it["sourceFile"]
            e = by_file.setdefault(f0, {"points": [], "excluded": {}, "note": it.get("note")})
            e["points"].extend(it.get("points") or [])
            for k, v in (it.get("excluded") or {}).items():
                e["excluded"][k] = e["excluded"].get(k, 0) + v
        ifaces = []
        cats = collections.Counter()
        for f0, e in by_file.items():
            doc_id, title, prod, dcat = meta.get(f0, ("", m["model"], "", ""))
            if dcat:
                cats[dcat] += 1
            row = {"file": f0, "title": title or m["model"], "id": doc_id}
            ifaces.extend(build_interfaces(row, "", e["points"], e["excluded"],
                                           block=BLOCK_OF.get(prod)))
        # 문서 분류는 그 제품 문서들이 가장 많이 붙은 것을 쓴다(한 제품에 문서가 여럿이다)
        equip, cat, tag, tags, cgaps, basis = equip_of(
            m["model"], cats.most_common(1)[0][0] if cats else "")
        m["equipId"], m["cat"], m["tag"], m["tags"] = equip, cat, tag, tags
        m["classifiedBy"] = basis or ("JCI 카탈로그 제품명 %r 의 낱말 "
                                      "(압축 방식·응축 방식)" % m["model"])
        # 손대지 않은 IOM 본문 판을 **원래 자리**로 되돌린다. 여기서 id 순으로 다시
        # 줄 세우면 판 내용은 그대로인데 순서만 뒤바뀌어 헛diff 가 난다(24모델 ±10,000줄).
        pos = {it["id"]: k for k, it in enumerate(m["interfaces"])}
        firstpos = {}
        for k, it in enumerate(m["interfaces"]):      # ⚠ 바깥 카운터 n 을 가리지 않게
            firstpos.setdefault(it["sourceFile"], k)
        ifaces = sorted(ifaces + keep,                      # 새로 갈린 판은 같은 문서 옆에
                        key=lambda i: (pos.get(i["id"], firstpos.get(i["sourceFile"], 1 << 20)),
                                       i["id"]))
        m["interfaces"] = ifaces
        m["comm"] = comm_rows(ifaces)
        m["summary"] = ("BAS 포인트 리스트 %d건 · 판 %d개에서 취입 — 오브젝트 %d점"
                        % (len(by_file) + len(keep), len(ifaces),
                           sum(i["pointCount"] for i in ifaces)))
        if cgaps and cgaps[0] not in m["gap"]:
            m["gap"] = m["gap"] + " " + " / ".join(cgaps)
        # 모델 단위의 판단 근거는 apply 가 심는다 — refresh 만 돌린 판에서 빠지지 않게
        mg = MODEL_GAP.get(m["model"])
        if mg and mg not in m["gap"]:
            m["gap"] = m["gap"] + " " + mg
        with open(path, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
        models.append(m)
        n += 1
    made = write_aliases(models)
    print("갱신 %d모델 · 판 %d개 · 별칭 모델 %d건"
          % (n, sum(len(x["interfaces"]) for x in models), made))
    return 0


def _body_applies_files():
    """BODY_APPLIES 로 코드를 얻은 문서의 저장 이름 → 근거 문장.

    별칭 레코드가 '문서 제목의 제품 나열'이라고 적는데, 이 문서들은 제목이 아니라
    **본문**이 밝힌 것이라 그대로 두면 근거가 틀린다.
    """
    by_id = {i: n for i, _s, n in SRC.JCI_BAS_POINTS}
    return {by_id[i]: v["why"] for i, v in BODY_APPLIES.items() if i in by_id}


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
    # 다른 추출기가 만든 **진짜 모델**도 센다. 별칭은 '그 코드로 찾을 길이 없다'를
    # 메우는 것이라, 코드에 정격을 가진 제품 모델이 생기면 더 만들 이유가 없다 —
    # 실제로 RTC·RTH 가 YKN2Open 게이트웨이의 별칭이면서 동시에 제품 모델로도
    # 있게 됐다(정격 취입 후). 별칭 자신은 세지 않는다 — 그러면 전부 사라진다.
    for path in glob.glob(os.path.join(DATA, "models", "*.json")):
        with open(path, encoding="utf-8") as f:
            other = json.load(f)
        if other.get("aliasOf") or other.get("extractor", "").startswith("vendor_jci") \
                and other.get("interfaces"):
            continue
        for c in re.findall(CODE_WORD, other.get("model") or ""):
            have.add(c)
    want = collections.OrderedDict()
    for m in models:
        for it in m["interfaces"]:
            for c in it.get("appliesTo") or []:
                if c not in have:
                    want.setdefault(c, (m, it))
    body_why = _body_applies_files()
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
            "classifiedBy": (body_why[it["sourceFile"]]
                             if it["sourceFile"] in body_why
                             else "문서 제목의 제품 나열 — %s" % it["label"][:70]),
            "gap": "제품 정식명·정격·형번 미상 — JCI 카탈로그가 이 코드에 제품명을 주지 "
                   "않는다. 문서 %s에 코드로만 나온다."
                   % ("본문" if it["sourceFile"] in body_why else "제목"),
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
VIEW = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>York 포인트 취입 검사대</title>
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
/* 제품 33건 × 7분류가 세로로 길다 — 분류는 접고, 이름 검색으로 바로 좁힌다 */
.rsearch{padding:10px 12px 4px}
.rsearch input{width:100%;padding:5px 9px;border:1px solid var(--line);border-radius:6px;
 background:var(--panel);color:var(--ink);font:inherit;font-size:12px}
aside details.grp>summary{padding:7px 16px 5px;font-size:10.5px;letter-spacing:.09em;
 text-transform:uppercase;color:var(--faint);font-weight:700;cursor:pointer;
 user-select:none}
aside details.grp>summary:hover{color:var(--dim)}
aside button.item{display:grid;grid-template-columns:1fr auto;gap:8px;width:100%;
 text-align:left;padding:4px 16px;border-left:2px solid transparent;align-items:center}
aside button.item:hover{background:var(--accent-soft)}
aside button.item[aria-current="true"]{background:var(--panel);border-left-color:var(--accent)}
/* 레일 3단째 — 판. 모델보다 한 단 들여 쓰고 글씨를 낮춰 단계가 눈에 보이게 한다 */
aside .ifsub{display:flex;flex-direction:column}
aside button.ifitem{display:grid;grid-template-columns:1fr auto;gap:6px;width:100%;
 text-align:left;background:none;border:0;border-left:3px solid transparent;
 padding:4px 14px 4px 30px;font-size:11.5px;color:var(--dim);cursor:pointer}
aside button.ifitem:hover{background:var(--accent-soft);color:var(--ink)}
aside button.ifitem[aria-current="true"]{color:var(--accent);font-weight:650;
 border-left-color:var(--accent);background:var(--panel)}
aside button.ifitem .ifn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
aside button.ifitem .ifq{font-family:var(--mono);font-size:10.5px;color:var(--faint)}
/* 판 항목은 두 줄 — 위는 구성('without VSD'), 아래는 어느 경로로 읽는 판인지 */
aside button.ifitem{grid-template-columns:1fr auto;row-gap:1px}
aside button.ifitem .ifp{grid-column:1/-1;font-size:10px;color:var(--faint);
 letter-spacing:.02em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
aside button.ifitem[aria-current="true"] .ifp{color:var(--dim)}
.iname{font-size:12.5px;line-height:1.3}
.icount{font-size:10.5px;color:var(--faint);white-space:nowrap;
 font-family:ui-monospace,Consolas,monospace}
.icount em{font-style:normal;color:var(--accent);font-weight:700}
.cool{font-style:normal;font-size:10px;margin-left:6px;padding:0 5px;border-radius:3px;
 background:var(--accent-soft);color:var(--dim);font-family:ui-monospace,Consolas,monospace}

main{overflow-y:auto;padding:0 0 60px}
.pad{padding:12px 20px 20px}
h2{margin:0 0 2px;font-size:20px;font-weight:650;letter-spacing:-.015em;text-wrap:balance}
.sub{color:var(--dim);font-size:12.5px}
.hsub{font-size:12px;color:var(--faint);font-weight:450;letter-spacing:0;margin-left:8px}
/* 판 고르기 — 표를 첫 화면에 올리려고 카드 대신 한 줄 알약/셀렉트로 줄였다 */
.ifc{border:1px solid var(--line);background:var(--panel);border-radius:999px;
 padding:3px 10px;font-size:11.5px;color:var(--dim);display:inline-flex;gap:6px;
 align-items:baseline;white-space:nowrap}
.ifc b{font-family:ui-monospace,Consolas,monospace;font-size:10.5px;color:var(--faint);
 font-weight:600}
.ifc[aria-pressed="true"]{border-color:var(--accent);background:var(--accent-soft);
 color:var(--ink)}
.ifc[aria-pressed="true"] b{color:var(--accent)}
select#ifsel{padding:4px 8px;border:1px solid var(--line);border-radius:6px;
 background:var(--panel);color:var(--ink);font:inherit;font-size:12px;max-width:420px}
/* 출처·제외 행·남은 판단·교차 대조 — 근거 팝업이 따로 있으니 요약 한 줄로 접는다.
   지우지 않는다: 펼치면 전과 같은 카드가 그대로 나온다 */
details.meta{margin:6px 0 0;font-size:12px}
details.meta>summary{cursor:pointer;color:var(--dim);font-size:11.5px;padding:2px 0;
 user-select:none}
details.meta>summary:hover{color:var(--ink)}
details.meta>summary .mono{color:var(--faint)}
details.meta .card{margin-top:8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
 padding:12px 14px;margin-top:14px;font-size:12.5px}
.card b.lbl{display:block;font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;
 color:var(--faint);margin-bottom:4px}
.card.warn{border-left:3px solid var(--warn);background:var(--warn-soft)}
.card.hole{border-left:3px solid var(--hole);background:var(--hole-soft)}
.kv{display:flex;gap:18px;flex-wrap:wrap;color:var(--dim)}
.kv span b{color:var(--ink);font-weight:600}

/* 고르는 것(판)과 거르는 것(검색·필터)을 한 줄에 모은다 — 표가 첫 화면에 보이게 */
.tools{display:flex;gap:8px;row-gap:6px;align-items:center;flex-wrap:wrap;margin:8px 0 6px}
input[type=search]{flex:0 1 240px;padding:5px 10px;border:1px solid var(--line);
 border-radius:6px;background:var(--panel);color:var(--ink);font:inherit;font-size:12.5px}
.rowcount{font-size:11.5px;color:var(--faint);font-family:ui-monospace,Consolas,monospace}
/* 필터 칩 — 0행 칩은 지우지 않고 흐리게만. "이 판에는 그게 없다"도 정보라서다 */
.flbl{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--faint);
 font-weight:700;margin:0 2px 0 6px}
.fchip{border:1px solid var(--line);background:var(--panel);border-radius:999px;
 padding:3px 10px;font-size:11.5px;color:var(--dim);display:inline-flex;gap:6px;
 align-items:baseline}
.fchip b{font-family:ui-monospace,Consolas,monospace;font-size:10.5px;color:var(--faint);
 font-weight:600}
.fchip[aria-pressed="true"]{border-color:var(--accent);background:var(--accent-soft);
 color:var(--ink)}
.fchip[aria-pressed="true"] b{color:var(--accent)}
.fchip.off{opacity:.45}
.pager{display:flex;gap:10px;align-items:center;margin:6px 0;font-size:11.5px;
 color:var(--dim)}
.pager button{padding:3px 10px;border:1px solid var(--line);border-radius:5px;
 font-size:11.5px;color:var(--dim)}
.pager button:hover:not(:disabled){background:var(--accent-soft);color:var(--ink)}
.pager button:disabled{opacity:.4;cursor:default}
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
/* 원문 대조 팝업 — 값이 맞는지는 원문과 나란히 놓고 봐야 판단할 수 있다 */
tbody tr.src{cursor:zoom-in}
dialog#zoom{width:94vw;height:92vh;max-width:none;max-height:none;padding:0;border:0;
 border-radius:10px;background:var(--panel);color:var(--ink);overflow:hidden}
dialog#zoom::backdrop{background:rgba(0,0,0,.62)}
.ztop{display:flex;align-items:center;gap:8px;padding:8px 12px;
 border-bottom:1px solid var(--line);font-size:12px}
.ztop .zsp{flex:1}
.ztop button,.ztop a{padding:3px 9px;border:1px solid var(--line);border-radius:5px;
 font-size:11.5px;color:var(--dim);text-decoration:none}
.ztop button:hover,.ztop a:hover{background:var(--accent-soft);color:var(--ink)}
#zv{position:relative;width:100%;height:calc(92vh - 39px);overflow:hidden;
 background:var(--rail);touch-action:none;cursor:grab}
#zv.drag{cursor:grabbing}
#zi{position:absolute;top:0;left:0;transform-origin:0 0;
 box-shadow:0 1px 14px rgba(0,0,0,.25);background:#fff}
@media (max-width:820px){
  .app{grid-template-columns:1fr;height:auto}
  aside{border-right:0;border-bottom:1px solid var(--line);max-height:220px}
}
</style>
</head><body>
<header>
  <h1>York 포인트 취입 검사대 <span>__BUILT__ · JCI/York BAS 포인트 리스트</span></h1>
  <div class="stats">
    <div class="flow"><b id="sDocs">0</b> 문서 <span class="arrow">&#8594;</span> <b id="sModels">0</b> 제품</div>
    <div class="stat"><b id="sIfs">0</b> 판</div>
    <div class="stat"><b id="sPts">0</b> 오브젝트</div>
    <div class="stat good"><b>0</b> 검증 오류</div>
    <div class="stat"><b id="sHole">0</b> 별칭 제품</div>
  </div>
</header>
<dialog id="zoom">
  <div class="ztop"><span id="zt"></span>
    <span class="zsp"></span>
    <button id="zfit">화면 맞춤</button><button id="z100">100%</button>
    <span id="zlv" class="mono">100%</span>
    <!-- 원문 탭은 이름(neuros-src) 하나를 재사용한다 — 카탈로그 근거표와 같은 이름이라
         두 화면이 한 탭을 나눠 쓴다. rel="noopener" 는 빼 둔다(명세상 noopener 면 이름이
         무시될 수 있다). 대상은 로컬 PDF 라 opener 노출로 잃을 것이 없다. -->
    <a id="zpdf" target="neuros-src">원문 PDF</a>
    <button id="zx">닫기 (Esc)</button></div>
  <div id="zv"><img id="zi" alt="원문 쪽"></div>
</dialog>
<div class="app">
  <aside>
    <div class="rsearch"><input type="search" id="rq" placeholder="제품 찾기 — 이름 · 코드"></div>
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
// 한 판이 244행까지 간다 — 한꺼번에 그리면 훑을 수 없어 100행씩 끊는다.
// page·filt 는 판을 바꾸면 초기화한다(다른 판의 필터가 이어지면 빈 표만 보게 된다).
var PAGE = 100, page = 1, filt = {};
// 메타 접기의 펼침 상태 — render 가 화면을 통째로 다시 그려도 사용자가 펼쳐 둔
// 것을 잊지 않도록 밖에 둔다
var metaOpen = false;

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
            ['HVAC.AIR.RTU','옥상형 공조기'],
            ['HVAC.AIR.SELFCONTAINED','자립형 공조기']];
// ⚠ 이 목록은 **손으로 적은 것**이라 새 분류가 생기면 조용히 빠진다 — 실제로
//    자립형 2제품(167점)이 레일에서 사라졌고 머리글은 39, 레일은 37 이었다.
//    그래서 목록에 없는 분류는 버리지 않고 '그 밖에' 로 모은다. 빠지느니 뭉쳐 둔다.
function kindsOf(models){
  var out = KIND.slice(), known = {};
  KIND.forEach(function(k){ known[k[0]] = 1; });
  var rest = models.filter(function(m){ return !known[m.cat]; });
  if(rest.length){
    var cats = {}; rest.forEach(function(m){ cats[m.cat] = 1; });
    Object.keys(cats).forEach(function(c){ out.push([c, '그 밖에 — ' + c]); });
  }
  return out;
}
var COOL = {airCooling:'공랭', waterCooling:'수냉'};
// 분류는 접는다 — 기본은 지금 보고 있는 제품이 속한 분류만 펼친다(render 가 연다).
// 세로 33줄이 항상 펼쳐져 있으면 레일이 스크롤로만 다녀야 해서다.
rail.innerHTML = kindsOf(D.models).map(function(k){
  var list = D.models.map(function(m, i){ return {m:m, i:i}; })
    .filter(function(x){ return x.m.cat === k[0]; });
  if(!list.length) return '';
  return '<details class="grp"><summary>' + k[1] + ' <b>' + list.length + '</b></summary>'
    + list.map(function(x){
        var cool = (x.m.tags || []).map(function(t){ return COOL[t]; }).filter(Boolean)[0];
        return '<button class="item" data-id="' + x.i + '"><span class="iname">'
          + esc(x.m.model) + (cool ? '<i class="cool">' + cool + '</i>' : '') + '</span>'
          + '<span class="icount"><em>' + x.m.ifs.length + '</em>판 &middot; ' + pts(x.m)
          + '</span></button>'
          // 판은 **고른 제품 아래에만** 편다. 100판을 늘 펼치면 레일이 스크롤 전용이 된다.
          + '<div class="ifsub" data-for="' + x.i + '"></div>';
      }).join('') + '</details>';
}).join('');

var PROTO = {bacnet:'BACnet', modbus:'Modbus', n2:'N2', lon:'LON',
             yorktalk:'York Talk', logix:'Logix', elink:'E-Link'};
function protoName(p){ return PROTO[p] || p; }
// 판 이름은 계통+개정만으로는 안 갈린다 — YK 는 EM/SSS 와 VSD 가 같은 'Rev K 04d' 다.
// 문서 이름이 유일한 구분자라 칩에 함께 보인다.
function chipTail(x){ return x.id.replace(/^[a-z0-9]+-/, ''); }

// [열쇠, 화면 이름, 원문 열 이름]. 원문 열 이름은 th 의 title 로 단다 — "원문에
// description 열이 있는데 반영이 안 됐다"는 오해가 실제로 있었다(오브젝트명이 그것이다).
var COLS = [['n','오브젝트명','POINT LIST DESCRIPTION'],
            ['s','짧은 이름','ISN LINC Descriptive Text'],
            ['b','BACnet'],['m','Modbus'],['d','N2'],['l','LON'],
            ['y','York Talk','ENG PAGE REF'],['k','YT 종별','York Talk Point Type'],
            ['c','문자 위치','York Talk Character Position'],
            ['x','ASCII 쪽','ASCII PAGE REF'],
            ['g','Logix'],['u','단위'],
            ['w','R/W'],['a','적용 조건'],['t','상태·열거'],['o','비고'],['p','쪽']];

// ── 진행 현황 ────────────────────────────────────────────────────────────────
// "어디까지 됐나"에 답하는 화면. 두 축으로 본다 — 설비 타입별로 무엇이 쌓였나,
// 그리고 **문서 포털에 있는 것 대비** 얼마나 가져왔나. 뒤쪽이 없으면 "다 했다"를
// 확인할 방법이 없다.
var SITE_KO = {chillers:'냉동기 포털', ductedsystems:'덕트·옥상형 포털', bas:'제어·계측 포털(Metasys)'};
function renderProgress(){
  var byKind = kindsOf(D.models).map(function(k){
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
    + '이 소스는 <b>BAS 포인트 리스트</b>다. 오브젝트 매핑 자동화는 ' + D.models.length + '제품 전부 되지만, '
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
      + '</tbody></table></div>';
  }
  // 안 가져온 것을 **열어 본 결과**. 전에는 여기에 '포인트 표가 있는 문서는 하나뿐'
  // 이라고 적혀 있었는데, 표식 낱말로만 훑은 짐작이었고 실제로는 셋이었다.
  if(D.missDetail && D.missDetail.groups && D.missDetail.groups.length){
    var md = D.missDetail;
    h += '<h3 class="ph">안 가져온 것을 열어 봤다</h3>'
      + '<div class="sub" style="padding:0 0 8px">' + esc(md.note) + '</div>'
      + md.groups.map(function(g){
          var cls = g.key === 'point-table' ? 'card hole' : 'card';
          return '<div class="' + cls + '"><b class="lbl">' + esc(g.ko) + ' — '
            + g.n + '건</b><ul style="margin:6px 0 0;padding-left:18px">'
            + g.docs.map(function(x){
                return '<li>' + (x.taken ? '<b style="color:var(--ok)">취입됨</b> · ' : '')
                  + esc(x.title) + (g.docs.length <= 6
                      ? '<div style="color:var(--dim)">' + esc(x.why) + '</div>' : '')
                  + '</li>'; }).join('')
            + '</ul></div>'; }).join('');
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

// 레일 3단째 — 고른 제품의 판. 본문 셀렉트와 같은 것을 가리키고 서로 따라간다.
function renderRailIfs(){
  document.querySelectorAll('#rail .ifsub').forEach(function(box){
    var mi = box.dataset.for;
    if(String(mi) !== String(cur)){ box.innerHTML = ''; return; }
    var m = D.models[mi | 0];
    if(!m || m.ifs.length < 2){ box.innerHTML = ''; return; }   // 판 하나면 단계를 만들지 않는다
    box.innerHTML = m.ifs.map(function(x, i){
      var path = railIfPath(x);
      return '<button class="ifitem" data-if="' + i + '" aria-current="' + (i === ifi) + '"'
        + ' title="' + esc(x.label || '') + '">'
        + '<span class="ifn">' + esc(railIfName(x)) + '</span>'
        + '<span class="ifq">' + x.n + '</span>'
        + (path ? '<span class="ifp">' + esc(path) + '</span>' : '')
        + '</button>'; }).join('');
  });
}
// 레일에 쓸 짧은 판 이름 — **구성**을 가리킨다('without VSD' 처럼).
// 블록 이름이 정본이고, 없으면 문서 제목에서 구분되는 대목을 떼어 온다:
//   'YK OptiView BAS E-Link (Rev K_04d) EM and SSS Data Maps OptiView Based Equipment'
//   → 개정 괄호 뒤 ~ 'Based Equipment' 앞 = 'EM and SSS Data Maps'
// 보드 번호까지 붙은 블록 이름은 앞에서 끊는다(YT OptiView … Micro Board: 031-…).
function railIfName(x){
  var nm = (x.rev && x.rev.block) || '';
  if(!nm){
    var t = String(x.label || '');
    var after = t.indexOf(')') >= 0 ? t.slice(t.indexOf(')') + 1) : t;
    nm = after.replace(/\s*(?:Non-?)?OptiView Based Equipment\s*$/i, '').trim();
    if(!nm) nm = (x.rev && x.rev.doc) || chipTail(x);
  }
  nm = nm.split(/\s+(?:ELINK|YORK TALK|Micro Board|MicroGateway)/i)[0]
         .replace(/[\u200b-\u200f\ufeff]/g, '').trim();   // 원문 제목에 폭 없는 문자가 섞여 있다
  return nm.length > 40 ? nm.slice(0, 39) + '…' : nm;
}
// 판 이름만으로는 '무엇의 without VSD 인지' 알 수 없다. 어느 경로로 읽는 판인지를
// **문서가 쓴 낱말 그대로** 한 줄 더 보인다 — 제어반 세대(OptiView / Non-OptiView)와
// 통신 경로(E-Link 게이트웨이 / 계통). 짐작해 옮기지 않는다.
function railIfPath(x){
  var t = String(x.label || '');
  var out = [];
  if(/Non-?OptiView/i.test(t)) out.push('Non-OptiView');
  else if(/OptiView/i.test(t)) out.push('OptiView');
  out.push(/E-?Link/i.test(t) ? 'E-Link' : (x.family || ''));
  return out.filter(Boolean).join(' · ');
}
function ifRailTitle(x){
  return [x.family, x.rev && x.rev.doc, x.src].filter(Boolean).join(' · ');
}

function render(){
  document.querySelectorAll('aside .item').forEach(function(b){
    b.setAttribute('aria-current', String(b.dataset.id) === String(cur)); });
  renderRailIfs();
  // 지금 보는 제품이 속한 분류는 펼쳐 둔다. 다른 분류를 강제로 닫지는 않는다 —
  // 사용자가 손으로 연 것을 렌더마다 도로 닫으면 훑어보기가 안 된다.
  var cb = document.querySelector('#rail .item[aria-current="true"]');
  if(cb && cb.closest('details')) cb.closest('details').open = true;
  if(cur === '__progress__'){ main.innerHTML = renderProgress(); return; }
  if(cur === '__holes__'){ main.innerHTML = renderHoles(); return; }
  var m = D.models[cur | 0];
  var it = m.ifs[Math.min(ifi, m.ifs.length - 1)];
  var use = COLS.filter(function(c){
    return it.points.some(function(p){ return p[c[0]] !== undefined; }); });
  // 필터 칩 — 이미 데이터에 있는 열쇠만 쓴다. 프로토콜은 이 판이 실제로 가진 블록만,
  // t·a·u 는 값이 없어도 세운다(흐리게 남는 것 자체가 "이 판에는 없다"는 정보다).
  var chips = [];
  [['b','BACnet'],['m','Modbus'],['d','N2'],['l','LON'],['y','York Talk'],['g','Logix']]
    .forEach(function(c){
      if(it.points.some(function(p){ return p[c[0]] !== undefined; }))
        chips.push({k:'has:' + c[0], lbl:c[1]});
    });
  var rws = {};
  it.points.forEach(function(p){ if(p.w) rws[p.w] = 1; });
  Object.keys(rws).sort().forEach(function(v){ chips.push({k:'rw:' + v, lbl:'R/W ' + v}); });
  [['t','상태·열거 있음'],['a','적용 조건 있음'],['u','단위 있음']].forEach(function(c){
    chips.push({k:'has:' + c[0], lbl:c[1]}); });
  // 켜진 칩은 전부 AND — rw 는 값 일치, 나머지는 그 열쇠의 존재로 본다
  function chipPass(k, p){
    var v = k.slice(k.indexOf(':') + 1);
    return k.indexOf('rw:') === 0 ? p.w === v : p[v] !== undefined;
  }
  var rows = it.points.filter(function(p){
    if(term && JSON.stringify(p).toLowerCase().indexOf(term) < 0) return false;
    for(var k in filt) if(!chipPass(k, p)) return false;
    return true; });
  // 판 고르기 — 카드 여러 줄이 표를 화면 밖으로 밀어냈다. 4판까지는 알약 한 줄,
  // 넘으면 셀렉트(YT 는 9판이라 알약으로도 한 줄이 안 된다).
  // 레일과 같은 말을 쓴다 — 구성('without VSD') · 경로('Non-OptiView · E-Link') · 개정.
  // 전에는 계통 코드(E-Link/YorkTalk)가 앞에 와서 '무엇의 without 인지'가 안 보였다.
  function ifLabel(x){
    var nm = railIfName(x), doc = (x.rev && x.rev.doc) || '';
    // 블록 이름이 없는 판은 이름 자리에 개정을 쓴다 — 뒤에 또 붙이면 'Rev 2.9 · Rev 2.9'
    return [nm, railIfPath(x), doc === nm ? '' : doc,
            x.rev && x.rev.firmware].filter(Boolean).join(' · ');
  }
  var pick;
  if(m.ifs.length > 4){
    pick = '<select id="ifsel" title="판 고르기">' + m.ifs.map(function(x, i){
      return '<option value="' + i + '"' + (i === ifi ? ' selected' : '') + '>'
        + esc(ifLabel(x) + ' · ' + x.n + '점') + '</option>'; }).join('') + '</select>';
  } else if(m.ifs.length > 1){
    pick = m.ifs.map(function(x, i){
      return '<button class="ifc" data-if="' + i + '" aria-pressed="' + (i === ifi)
        + '" title="' + esc(x.protocols.map(protoName).join(' · ')) + '">'
        + esc(ifLabel(x)) + '<b>' + x.n + '</b></button>'; }).join('');
  } else {
    pick = '<span class="rowcount" title="판이 하나뿐이다">' + esc(ifLabel(it)) + '</span>';
  }
  var h = '<div class="pad"><h2>' + esc(m.model)
    + '<span class="hsub">' + esc(m.cat) + ' · 계열 ' + esc(m.equipId) + ' · '
    + m.ifs.length + '판 · ' + pts(m) + '점</span></h2>'
    + '<div class="tools">' + pick
    + '<input type="search" id="q" placeholder="이 판에서 찾기 — 이름 · 주소 · 단위" value="'
    + esc(term) + '"><span class="rowcount">' + rows.length + ' / ' + it.points.length + '행</span>'
    + '<span class="flbl">필터</span>'
    + chips.map(function(c){
        // 칩 숫자 = 지금 걸린 필터·검색 위에 이 칩까지 켰을 때 남는 행 수.
        // AND 라서 켜진 칩에는 곧 현재 남은 행 수가 나온다.
        var cnt = rows.filter(function(p){ return chipPass(c.k, p); }).length;
        return '<button class="fchip' + (cnt ? '' : ' off') + '" data-fk="' + c.k
          + '" aria-pressed="' + !!filt[c.k] + '">' + esc(c.lbl) + '<b>' + cnt
          + '</b></button>';
      }).join('') + '</div>';
  // 출처·제외 행·남은 판단·교차 대조는 접는다 — 근거는 행 클릭 원문 팝업이 이미 있고,
  // 카드 네 장이 표를 첫 화면 밖으로 밀었다. 지우지는 않는다: 펼치면 그대로 나온다.
  var exN = Object.keys(it.excluded || {}).reduce(function(a, k){
    return a + it.excluded[k]; }, 0);
  var sumBits = ['출처 ' + it.src + (it.pages ? ' p' + it.pages.join('~') : '')];
  if(it.appliesTo) sumBits.push('덮는 제품 ' + it.appliesTo.length);
  if(exN) sumBits.push('세지 않은 행 ' + exN);
  if(it.gaps) sumBits.push('남은 판단 ' + it.gaps.length + '건');
  if(m.crosscheck) sumBits.push('교차 대조 못함');
  h += '<details class="meta"' + (metaOpen ? ' open' : '') + '><summary><span class="mono">'
    + esc(sumBits.join(' · ')) + '</span></summary>'
    + '<div class="card"><b class="lbl">이 판의 출처</b><div class="kv">'
    + '<span class="mono">' + esc(it.src) + (it.pages ? ' p' + it.pages.join('~') : '') + '</span>'
    + (it.appliesTo ? '<span>덮는 제품 <b class="mono">' + esc(it.appliesTo.join(' · ')) + '</b></span>' : '')
    + '</div><div style="margin-top:6px;color:var(--dim)">' + esc(it.label) + '</div></div>';
  // 행 클릭으로 원문이 뜬다는 건 안내가 없으면 아무도 모른다. 문구는 그림 임베드 여부에 맞춘다.
  h += '<div class="sub" style="margin:8px 0 0">행을 누르면 그 포인트의 원문 쪽이 뜬다 — '
    + (((D.imgs || {})[it.src])
        ? '휠로 확대·축소, 끌어서 이동, Esc 로 닫기.'
        : '이 문서는 그림이 없어 원문 PDF 로 화면을 떠난다 — <code>--no-pages</code> 로 '
          + '뽑았거나 원문 파일을 못 찾은 경우다. <code>ingest_jci.py --export</code> 로 '
          + '다시 뽑으면 여기서 바로 보인다.')
    + '</div>';
  if(it.excluded) h += '<div class="card"><b class="lbl">포인트로 세지 않은 행</b>'
    + Object.keys(it.excluded).map(function(k){ return esc(exKo(k)) + ' <b>' + it.excluded[k] + '</b>행'; }).join(' · ')
    + ' — 조용히 빼지 않고 여기 적는다.</div>';
  if(it.gaps) h += '<div class="card warn"><b class="lbl">남은 판단</b>' + esc(it.gaps.join(' / ')) + '</div>';
  if(m.crosscheck) h += '<div class="card"><b class="lbl">교차 대조</b>' + esc(m.crosscheck) + '</div>';
  h += '</details>';
  var npg = Math.max(1, Math.ceil(rows.length / PAGE));
  if(page > npg) page = npg;
  var lo = (page - 1) * PAGE, hi = Math.min(rows.length, lo + PAGE);
  function pager(loc){
    if(rows.length <= PAGE) return '';   // 한 쪽에 다 들어가면 페이징 UI 를 아예 안 그린다
    return '<div class="pager"><button class="pgb" data-d="-1" data-loc="' + loc + '"'
      + (page <= 1 ? ' disabled' : '') + '>이전</button><span class="mono">'
      + page + '/' + npg + '쪽 &middot; ' + rows.length + '행 중 ' + (lo + 1) + '~' + hi
      + '</span><button class="pgb" data-d="1" data-loc="' + loc + '"'
      + (page >= npg ? ' disabled' : '') + '>다음</button></div>';
  }
  h += pager('t')
    + '<div class="tw"><table><thead><tr>'
    + use.map(function(c){ return '<th' + (c[2] ? ' title="원문 열 이름: ' + esc(c[2]) + '"' : '')
        + '>' + c[1] + '</th>'; }).join('') + '</tr></thead><tbody>'
    + rows.slice(lo, hi).map(function(p){
        // 행을 누르면 그 포인트가 나온 원문 쪽이 뜬다 — 값 대조는 원문 옆에서만 된다
        var at = p.p ? (' class="src" data-src="' + esc(it.src) + '" data-pg="' + p.p + '"') : '';
        return '<tr' + at + '>' + use.map(function(c){
          var v = p[c[0]];
          var cls = (c[0] === 'n' || c[0] === 'o' || c[0] === 't') ? 'nm' : 'num mono';
          return '<td class="' + cls + '">' + esc(v === undefined ? '' : v) + '</td>';
        }).join('') + '</tr>';
      }).join('')
    + '</tbody></table>' + (rows.length ? '' : '<div class="empty">찾은 게 없어요</div>') + '</div>'
    + pager('b') + '</div>';
  main.innerHTML = h;
  main.querySelectorAll('.ifc').forEach(function(b){
    b.addEventListener('click', function(){ ifi = +b.dataset.if; term = ''; page = 1; filt = {};
      render(); }); });
  var sel = document.getElementById('ifsel');
  if(sel) sel.addEventListener('change', function(){
    ifi = +sel.value; term = ''; page = 1; filt = {}; render(); });
  var md = main.querySelector('details.meta');
  if(md) md.addEventListener('toggle', function(){ metaOpen = md.open; });
  main.querySelectorAll('.fchip').forEach(function(b){
    b.addEventListener('click', function(){
      var k = b.dataset.fk;
      if(filt[k]) delete filt[k]; else filt[k] = true;
      page = 1; render(); }); });
  main.querySelectorAll('.pgb').forEach(function(b){
    b.addEventListener('click', function(){
      page += +b.dataset.d; render();
      // 아래쪽 페이저로 넘기면 새 쪽 머리가 화면 밖이라 표 위로 끌어올린다
      if(b.dataset.loc === 'b'){
        var t = main.querySelector('.tools'); if(t) t.scrollIntoView(); } }); });
  var q = document.getElementById('q');
  if(q) q.addEventListener('input', function(){
    term = q.value.trim().toLowerCase(); page = 1;
    var at = q.selectionStart;
    render();
    var q2 = document.getElementById('q');
    if(q2){ q2.focus(); q2.setSelectionRange(at, at); } });
}
document.querySelectorAll('aside .item').forEach(function(b){
  b.addEventListener('click', function(){ cur = b.dataset.id; ifi = 0; term = ''; page = 1;
    filt = {}; render(); main.scrollTop = 0; }); });
// 레일의 판 버튼은 렌더마다 다시 만들어지므로 상위에서 위임으로 받는다
document.getElementById('rail').addEventListener('click', function(e){
  var b = e.target.closest && e.target.closest('.ifitem');
  if(!b) return;
  ifi = +b.dataset.if; term = ''; page = 1; filt = {};
  render(); main.scrollTop = 0;
});
// 레일 제품 검색 — 접힌 분류 안까지 이름으로 찾는다. 검색 중에는 걸린 분류를 펼치고,
// 비우면 기본 상태(보고 있는 제품의 분류만 펼침)로 돌아간다.
var rq = document.getElementById('rq');
rq.addEventListener('input', function(){
  var t = rq.value.trim().toLowerCase();
  document.querySelectorAll('#rail details.grp').forEach(function(d){
    var any = false;
    d.querySelectorAll('.item').forEach(function(b){
      var hit = !t || b.textContent.toLowerCase().indexOf(t) >= 0;
      b.style.display = hit ? '' : 'none';
      if(hit) any = true;
    });
    d.style.display = any ? '' : 'none';
    d.open = t ? true : !!d.querySelector('.item[aria-current="true"]');
  });
});
render();

// ── 원문 대조 팝업 ───────────────────────────────────────────────────────────
// 그림이 임베드돼 있으면(--with-pages, WebP 회색조라 전 문서 기본) 팝업에서 휠로
// 확대·끌어서 이동한다. 없는 쪽만 원문 PDF 를 그 쪽으로 연다.
// 제외 사유 열쇠는 파서가 쓰는 영문이다 — 화면에는 뜻을 적는다
var EXKO = {reserved:'예약 슬롯', revision:'개정이력표', codeTable:'상태 코드표',
            notes:'표 아래 NOTES', band:'구분 행', banner:'되풀이된 머리글',
            headerMislabeled:'머리글이 데이터와 어긋난 표',
            headerGlitch:'머리글에 값이 배어난 쪽', foreign:'남의 계통 표',
            unrestored:'조판 아티팩트 복원 실패'};
function exKo(k){ return EXKO[k] || k; }
function pdfHref(file, page){
  return '../pipeline/data/raw/' + encodeURIComponent(String(file).split('#')[0])
       + (page ? '#page=' + page : '');
}
var zoom = document.getElementById('zoom'), zv = document.getElementById('zv'),
    zi = document.getElementById('zi');
var zs = 1, zx = 0, zy = 0, natW = 0, natH = 0;
function zapply(){
  zi.style.transform = 'translate(' + zx + 'px,' + zy + 'px) scale(' + zs + ')';
  document.getElementById('zlv').textContent = Math.round(zs * 100) + '%';
}
function zfit(){
  if(!natW) return;
  zs = Math.min(zv.clientWidth / natW, zv.clientHeight / natH);
  zx = (zv.clientWidth - natW * zs) / 2; zy = (zv.clientHeight - natH * zs) / 2;
  zapply();
}
zi.onload = function(){ natW = zi.naturalWidth; natH = zi.naturalHeight;
  zi.style.width = natW + 'px'; zi.style.height = natH + 'px'; zfit(); };
zv.addEventListener('wheel', function(e){
  e.preventDefault();
  var r = zv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  // 커서가 가리키는 지점을 고정한 채 배율을 바꾼다
  var k = Math.exp(-e.deltaY * 0.0015);
  var ns = Math.min(8, Math.max(0.05, zs * k));
  zx = mx - (mx - zx) * (ns / zs); zy = my - (my - zy) * (ns / zs); zs = ns;
  zapply();
}, {passive:false});
var zdrag = false, zpx = 0, zpy = 0;
zv.addEventListener('pointerdown', function(e){ zdrag = true; zpx = e.clientX; zpy = e.clientY;
  zv.classList.add('drag'); zv.setPointerCapture(e.pointerId); });
zv.addEventListener('pointermove', function(e){ if(!zdrag) return;
  zx += e.clientX - zpx; zy += e.clientY - zpy; zpx = e.clientX; zpy = e.clientY; zapply(); });
zv.addEventListener('pointerup', function(){ zdrag = false; zv.classList.remove('drag'); });
zv.addEventListener('dblclick', function(){ if(zs < 1.5){ zs = 2; zapply(); } else { zfit(); } });
document.getElementById('zfit').onclick = zfit;
document.getElementById('z100').onclick = function(){
  var cx = zv.clientWidth / 2, cy = zv.clientHeight / 2;
  zx = cx - (cx - zx) * (1 / zs); zy = cy - (cy - zy) * (1 / zs); zs = 1; zapply(); };
document.getElementById('zx').onclick = function(){ zoom.close(); };
window.addEventListener('resize', function(){ if(zoom.open) zfit(); });
document.addEventListener('click', function(e){
  var tr = e.target.closest && e.target.closest('tr.src');
  if(!tr) return;
  var src = tr.dataset.src, pg = tr.dataset.pg;
  var img = ((D.imgs || {})[src] || {})[pg];
  var href = pdfHref(src, pg);
  // 그림이 없으면 원문 PDF 를 그 쪽으로. 창 이름을 주어 **탭 하나를 재사용**한다 —
  // 카탈로그(gen2.srcLink)와 같은 이름이라 두 화면이 한 탭을 나눠 쓴다.
  if(!img){ window.open(href, 'neuros-src'); return; }
  document.getElementById('zt').textContent = src + ' — 원문 ' + pg + '쪽';
  document.getElementById('zpdf').href = href;
  zs = 1; zx = 0; zy = 0; natW = 0;
  zi.src = img;
  zoom.showModal();
});
</script>
</body></html>
"""


# 포털 스냅샷에서 '포인트 표가 있을 법한 문서'를 고르는 힌트. 취입률을 재는 데만 쓴다 —
# 이걸로 파싱하지 않는다(파싱 판정은 표 머리글로 한다).
PT_HINT = re.compile(r"points?\s*list|data\s*map|point\s*map|BAS\b|E-?Link|SC-?EQ|"
                     r"BACnet|Modbus|N2\b|LON\b|protocol", re.I)

# 눈으로 확인한 구멍. **원문을 열어 센 것만 적는다** — 짐작은 적지 않는다.
KNOWN_GAPS = [
    {"what": "SC-EQ 통신 카드 자체의 설정 포인트",
     "docs": "SI0371(펌웨어 3.0.0.1114) 1쪽 · 통신카드 설치설명서 46쪽 — 같은 6점",
     "found": "BV65000·AV65000·MV65003·SV65000·MV65001·MV65002 + 'Manual Select "
              "Chiller Model' 값 44종 (2026-08-21 원문 실측)",
     "why": "장비가 아니라 통신 카드의 설정값이라 어느 제품에 붙일지가 판단이다. "
            "표 머리글이 'Point name | BACnet | Modbus | N2 | Description' 으로 "
            "기존 어느 계통과도 다르다."},
    {"what": "SC-EQ 펌웨어 릴리스 노트 6건 — 이름만 있고 주소가 없다",
     "docs": "3.4.0.12 · 3.5.0.11 · 3.5.0.12 · 4.0.0.76 · 4.2.0.20 · 4.3",
     "found": "'Long Name | Notes | Available to Customer BAS' — 합 343행이지만 "
              "주소 열이 아예 없고 구획 머리행('YVAM Write Data')이 섞여 있다",
     "why": "지금 SC-EQ 파서에 그냥 물리면 배너가 포인트가 되고 가용성 열이 날아간다. "
            "게다가 판(제품이 내보내는 전체 목록)이 아니라 그 펌웨어가 더한 것의 "
            "델타라, 실을지 자체가 정해진 적 없다."},
    {"what": "정격 (용량·COP·전류)",
     "docs": "이 소스에 없음",
     "found": "제품 39건 전부 0",
     "why": "BAS 포인트 리스트 포털이라 정격이 실리지 않는다. York 제품 카탈로그를 "
            "따로 수집해야 시뮬레이터가 쓸 수 있다(짝 규칙). "
            "✓ 옥상형 한 갈래는 풀렸다 — 같은 포털의 Roomtop RTC/RTH 기술 가이드 "
            "2건(제목만 스페인어, 본문 영문)에서 형번 12건의 냉방·난방 능력과 "
            "소비전력을 취입했다(모델 …rtc-rth-compact-horizontal-heat-pump-roomtop). "
            "YKN2Open 이 덮는 그 제품이라 짝이 맞는다. "
            "⚠ 남은 냉동기 정격은 **포털 안에 있다** — 지금까지의 그물이 "
            "'포인트 리스트 낌새'뿐이라 정격 문서를 한 번도 열거하지 않았을 뿐이다. "
            "제목으로 세면 272건(냉동기 32 · 덕트·옥상형 211 · 제어 29)이고, 그 안에 "
            "'YK Style H … Engineering Guide'·'YZ Style A'·'YMC2'·'YVAA Style B' 처럼 "
            "우리가 포인트를 가진 바로 그 모델이 있다."},
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


# 안 가져온 것을 **열어 본 결과**. 짐작을 화면에 적지 않으려고 파일로 뺐다 —
# 표식 낱말로만 훑던 때는 '포인트 표가 있는 문서는 하나뿐'이라고 적혀 있었는데
# 실제로는 셋이었다(2026-08-21 31건 전수 실측).
MISS_VERDICT = os.path.join(DATA, "jci-portal-miss.json")
VERDICT_KO = [
    ("point-table", "포인트 표가 있다"),
    ("name-only", "이름만 — 주소 없는 펌웨어 릴리스 노트"),
    ("translation", "번역본 — 내용이 같다"),
    ("no-point-table", "포인트 표가 없다 — 배선도·공지·킷·호환표"),
]


def miss_detail():
    """'안 가져온 것'의 실측 판정. 파일이 없으면 빈 값 — 화면이 그 절을 생략한다."""
    if not os.path.exists(MISS_VERDICT):
        return None
    with open(MISS_VERDICT, encoding="utf-8") as f:
        d = json.load(f)
    by = collections.OrderedDict((k, []) for k, _ko in VERDICT_KO)
    for e in d.get("docs") or []:
        by.setdefault(e["verdict"], []).append(e)
    return {"note": d.get("note", ""), "asOf": d.get("asOf", ""),
            "groups": [{"key": k, "ko": ko, "n": len(by.get(k) or []),
                        "docs": [{"title": x["title"], "why": x["why"],
                                  "taken": bool(x.get("taken"))}
                                 for x in (by.get(k) or [])]}
                       for k, ko in VERDICT_KO if by.get(k)]}


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


def _charpos(v):
    """yorktalk.charPos {start,end} → '120' 또는 '120~124'. 한 글자면 범위 표기가 소음이다."""
    if not isinstance(v, dict) or v.get("start") is None:
        return None
    a, b = v.get("start"), v.get("end")
    return str(a) if b in (None, a) else "%s~%s" % (a, b)


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
        # asciiPageRef 는 제 열('x')이 생겼다 — 여기 대신 넣으면 ENG/ASCII 구분이 사라진다
        "y": yt.get("coord") or yt.get("pageRef"),
        "x": yt.get("asciiPageRef"),
        "c": _charpos(yt.get("charPos")),
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
    out["missDetail"] = miss_detail()
    out["knownGaps"] = KNOWN_GAPS
    return out


def _ink_box(page, probe_dpi=50, pad=4):
    """쪽에서 흰 여백이 아닌 부분의 경계(표시 좌표). 못 구하면 None(=전면 그대로)."""
    import numpy as np
    import fitz
    try:
        pix = page.get_pixmap(dpi=probe_dpi)
    except Exception:
        return None
    if not pix.width or not pix.height:
        return None
    a = np.frombuffer(pix.samples, dtype=np.uint8)
    a = a.reshape(pix.height, pix.stride)[:, : pix.width * pix.n]
    a = a.reshape(pix.height, pix.width, pix.n)
    ink = a[:, :, :3].min(axis=2) < 245          # 거의 흰색이면 여백으로 본다
    ys, xs = np.where(ink)
    if not len(xs):
        return None                               # 빈 쪽
    s = 72.0 / probe_dpi
    r = fitz.Rect(int(xs.min()) * s - pad, int(ys.min()) * s - pad,
                  (int(xs.max()) + 1) * s + pad, (int(ys.max()) + 1) * s + pad)
    return r & page.rect


def render_pages(want, dpi=110, quality=35):
    """원문 쪽 → base64 WebP 회색조. ({저장이름: {쪽: dataURI}}, 실패 집계)

    JPEG 컬러 150dpi 는 217쪽에 base64 54MB 라 전 문서를 못 넣었다(실측 — 그때는
    --only 로 문서를 골라야 했다). WebP 회색조 110dpi 는 같은 217쪽이 q40 25.7MB ·
    q35 24.5MB(실측) — 전 문서를 넣을 수 있어 **기본으로 전부 넣는다**. 원문이
    흑백 표라 회색조로 잃는 것이 없다. 실패(파일 없음·쪽 범위 밖·렌더 오류)는
    조용히 넘기지 않고 세어 돌려준다.
    """
    import base64
    import io
    import fitz
    from PIL import Image
    out = {}
    fails = collections.Counter()
    for name, pages in sorted(want.items()):
        path = os.path.join(DATA, "raw", name)
        if not os.path.exists(path):
            fails["원문 파일 없음"] += 1
            continue
        doc = fitz.open(path)
        got = {}
        for pg in sorted(pages):
            if pg < 1 or pg > doc.page_count:
                fails["쪽 번호가 문서 범위 밖"] += 1
                continue
            try:
                page = doc[pg - 1]
                # 내용이 있는 데까지만 자른다 — 원문 여백이 쪽마다 3~4cm 다.
                # 해상도는 그대로라 읽는 데 잃는 것이 없고 크기는 25.4MB → 20MB 로 준다.
                #
                # ⚠ 자를 범위를 **찍히는 픽셀**로 정한다. 내용 종류를 열거하는 방식으로
                #    두 번 틀렸다: ⑴ 글자 좌표만 보다가 표 괘선(도형)을 잘랐고(110쪽),
                #    ⑵ 도형·이미지를 더했더니 이번엔 **90° 회전된 쪽**에서 잘렸다(135쪽)
                #    — get_text/get_drawings 는 회전 **전** 좌표를 주는데 get_pixmap 의
                #    clip 은 회전 **후** 좌표를 받아서 좌표계가 어긋났다.
                #    낮은 해상도로 한 번 그려 흰 여백이 아닌 칸의 경계를 찾으면 좌표계도
                #    내용 종류도 신경 쓸 일이 없다. 배경이 깔린 쪽은 전면이 되는데,
                #    그건 '덜 자른' 것이라 안전한 실패다.
                clip = _ink_box(page)
                pix = page.get_pixmap(dpi=dpi, clip=clip)
                img = Image.frombytes("RGB", [pix.width, pix.height],
                                      pix.samples).convert("L")
                buf = io.BytesIO()
                img.save(buf, format="WEBP", quality=quality)
            except Exception:
                fails["렌더 실패"] += 1
                continue
            got[str(pg)] = ("data:image/webp;base64,"
                            + base64.b64encode(buf.getvalue()).decode("ascii"))
        doc.close()
        if got:
            out[name] = got
    return out, fails


def audit_pages(only=None):
    """임베드 대상 쪽이 **실제로 안 잘렸는지** 독립 경로로 확인한다.

    자르기(_ink_box)와 같은 방법으로 확인하면 같은 맹점을 그대로 통과한다 — 실제로
    글자 좌표로 고치고 글자 좌표로 확인해 "0쪽"을 보고했다가, 90° 회전된 쪽에서
    135쪽이 잘려 있는 것을 사용자가 눈으로 찾아냈다(규칙 4: 교차 대조를 믿는다).
    여기서는 **전면을 그려** 잉크 경계를 구하고 자를 범위와 견준다.
    """
    import numpy as np
    import fitz
    data = view_data()
    want = {}
    for m in data["models"]:
        for it in m["ifs"]:
            if only and only.lower() not in it["src"].lower():
                continue
            for pt in it["points"]:
                if pt.get("p"):
                    want.setdefault(it["src"], set()).add(pt["p"])
    tot = cut = 0
    worst = []
    for name, pages in sorted(want.items()):
        path = os.path.join(DATA, "raw", name)
        if not os.path.exists(path):
            continue
        doc = fitz.open(path)
        for pg in sorted(pages):
            if not 1 <= pg <= doc.page_count:
                continue
            page = doc[pg - 1]
            tot += 1
            c = _ink_box(page)
            if c is None:
                continue
            pix = page.get_pixmap(dpi=50)
            a = np.frombuffer(pix.samples, dtype=np.uint8)
            a = a.reshape(pix.height, pix.stride)[:, : pix.width * pix.n]
            a = a.reshape(pix.height, pix.width, pix.n)
            ys, xs = np.where(a[:, :, :3].min(axis=2) < 245)
            if not len(xs):
                continue
            k = 72.0 / 50
            ink = fitz.Rect(xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k)
            over = [c.x0 - ink.x0, c.y0 - ink.y0, ink.x1 - c.x1, ink.y1 - c.y1]
            if max(over) > 1:
                cut += 1
                worst.append((max(over), name, pg,
                              [round(v, 1) for v in over]))
        doc.close()
    worst.sort(reverse=True)
    print("임베드 대상 %d쪽 · 잘리는 쪽 %d" % (tot, cut))
    for _, n, pg, o in worst[:10]:
        print("   %s p%d  좌%s 상%s 우%s 하%s" % (n, pg, *o))
    return 1 if cut else 0


def export(out_path=None, with_pages=True, only=None, quality=35):
    out_path = out_path or os.path.join(HERE, "..", "review", "jci-ingest.html")
    data = view_data()
    data["imgs"] = {}
    if with_pages:
        # --only 가 없으면 전 문서를 넣는다 — 팝업이 안 뜨는 문서를 없애는 것이 목적이다
        want = {}
        for m in data["models"]:
            for it in m["ifs"]:
                if only and only.lower() not in it["src"].lower():
                    continue
                for pt in it["points"]:
                    if pt.get("p"):
                        want.setdefault(it["src"], set()).add(pt["p"])
        data["imgs"], fails = render_pages(want, quality=quality)
        print("  원문 쪽 그림 %d문서 %d쪽"
              % (len(data["imgs"]), sum(len(v) for v in data["imgs"].values())))
        if fails:
            print("  ⚠ 그림 실패 %d건 — %s" % (sum(fails.values()),
                  " · ".join("%s %d" % kv for kv in fails.most_common())))
    # ⚠ 머리글 날짜를 소스에 적어 두면 낡는다 — 실제로 2026-08-14 로 굳어 있어
    #   8/21 에 만든 파일이 8/14 로 보였다. 만든 날짜를 그때 박는다.
    import datetime
    built = datetime.date.today().isoformat()
    html = VIEW.replace("__BUILT__", built).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("  %s" % os.path.normpath(out_path))
    print("  제품 %d · 문서 %d · 판 %d · 오브젝트 %d · 별칭 %d · %.1f MB"
          % (len(data["models"]), data["docs"], data["totalIfs"], data["totalPoints"],
             len(data["alias"]), os.path.getsize(out_path) / 1024.0 / 1024.0))
    return 0


# ── IOM 본문형(IPU/Series-100) 취입 ──────────────────────────────────────────
# 냉동기는 포인트 리스트가 별도 문서지만 옥상형·자립형은 IOM 본문에 묻혀 있다.
# 문서 성격이 달라 소스도 파서도 따로지만, **모델에 담기는 모양은 같다**(interfaces[]).
IOM_PROD = {                       # 카탈로그가 제품명을 안 준 문서 — 제목에서 옮겨 적는다
    "90-105 Tons, Mod G (Current), Series 100": "Series 100 (YPAL)",
    "TempMaster OmniElite 90-105 Tons": "OmniElite",
}
# 카탈로그 제품명 → 우리 모델 이름. 같은 제품군을 한 모델로 모은다.
IOM_MODEL = {
    "Series 100 (YPAL)": "YPAL Packaged Rooftop Unit",   # 기존 모델과 같은 제품군이다
    "YPAL": "YPAL Packaged Rooftop Unit",
    "OmniElite": "TempMaster OmniElite Packaged Rooftop Unit",
    "Millenium": "Millenium Packaged Rooftop Unit",
    "V2 to V4": "Rooftop 25/30/40 Ton (IPU Control)",
    "Versecon": "Versecon YSWU/YSWD Water-Cooled Self-Contained",
    "L-Series": "L-Series LSWU/LSWD/LSWF Self-Contained",
}
IOM_EQUIP = {                      # 문서 분류 → (계열, cat, tag)
    "Applied Packaged Rooftop Units": ("e5", "HVAC.AIR.RTU", "rooftop"),
    "Rooftop Packaged Unit": ("e5", "HVAC.AIR.RTU", "rooftop"),
    "Air Conditioners": ("e5", "HVAC.AIR.RTU", "rooftop"),
    "Air and Water-Cooled Self-Contained Units": ("e5", "HVAC.AIR.SELFCONTAINED", "ahu"),
}


# 공조기 포털 — 제품마다 모델을 만들 자리. 두 제품이 **같은 157행**을 쓰므로 목록은
# 주 제품 하나에만 붙인다(스키마: 같은 목록을 제품 수만큼 복제하지 마라).
AIR_MODELS = {
    "JCI_AIR_YKL-lowprofile-ahu.pdf": {
        "key": "YKL Compact Low Profile AHU",
        "equip": "e5", "cat": "HVAC.AIR.AHU", "tag": "ahu",
        "label": "유닛 제어반 Modbus 레지스터",
        "appliesTo": ["YKH", "YKL"],
        "primary": True,
    },
    "JCI_AIR_YKH-heat-recovery.pdf": {
        "key": "YKH Residential Heat Recovery Unit",
        "equip": "e12", "cat": "HVAC.WATER.HX.ERV", "tag": "heatRecovery",
        "primary": False,
    },
}


def apply_air(dry=False):
    """공조기 포털 Modbus 레지스터 표 → 모델의 interfaces[].

    두 문서(YKH·YKL)의 157행이 **글자까지 100% 같다** — 같은 유닛 제어반이다.
    그래서 목록은 주 제품(YKL, 공조기 계열)에만 붙이고 YKH 는 그 사실을 적은 모델로
    둔다. 같은 1,000점을 제품 수만큼 복제하면 한쪽만 고쳐지는 날이 온다(스키마 경고).
    """
    import vendor_jci_air as A
    import vendor_jci_ipu as IPU
    import fitz
    import scan_jci as SC

    made = pts_total = 0
    for path in CO.files_of(A.SOURCE):
        fname = os.path.basename(path)
        spec = AIR_MODELS.get(fname)
        if not spec:
            print("  ⚠ %s — 모델 자리가 정해지지 않았다" % fname)
            continue
        rows_in = []
        doc = fitz.open(path)
        for pi in range(doc.page_count):
            try:
                tabs = doc[pi].find_tables().tables
            except Exception:
                continue
            for t in tabs:
                data = t.extract()
                if len(data) < 4:
                    continue
                head = SC.table_header(data)
                if not head or not A.HEAD.search(head[0]):
                    continue
                for r in data[head[1]:]:
                    # ⚠ 셀 글자를 여기서 만든다 — 아래첨자를 제자리에 돌린 뒤 줄바꿈을
                    #   눌러야 한다. 그냥 누르면 'CO2' 가 'CO 2' 로 굳는다(67fd3b6 재발).
                    cells = [IPU.join_subscripts(x or "").replace("\n", " ").strip()
                             for x in r]
                    if any(cells):
                        rows_in.append((pi + 1, cells))
        doc.close()
        points, skipped = A.parse_doc(path, rows_in, None)
        print("  · %-46s %4d점 %s" % (fname[:46], len(points), skipped or ""))
        if not points:
            continue
        if not spec["primary"]:
            main = next(v["key"] for v in AIR_MODELS.values() if v["primary"])
            print("    ↷ 주 제품이 아니다 — 같은 157행이라 목록은 %r 에만 둔다" % main)
            continue
        iid = "air-modbus"
        for pt in points:
            pt["provenance"]["interfaceId"] = iid
        pages = sorted({pt["provenance"]["sourcePage"] for pt in points})
        iface = {"id": iid, "label": spec["label"], "family": A.FAMILY,
                 "protocols": ["modbus"], "sourceFile": fname,
                 "sourcePages": pages, "pointCount": len(points),
                 "appliesTo": spec.get("appliesTo"), "status": "extracted",
                 "note": "유닛 제어반의 홀딩 레지스터 목록. 같은 표가 YKH 매뉴얼에도 "
                         "글자까지 똑같이 실려 있다(157행 전수 대조) — 같은 제어반이라 "
                         "제품마다 복제하지 않고 여기 한 벌만 둔다.",
                 "points": points}
        iface = {k: v for k, v in iface.items() if v is not None}
        mid = S.model_id(VENDOR, spec["key"])
        path_m = os.path.join(DATA, "models", mid + ".json")
        before = None
        if os.path.exists(path_m):
            with open(path_m, encoding="utf-8") as f:
                rec = json.load(f)
            before = json.dumps(rec, ensure_ascii=False, sort_keys=True)
            old = [i for i in (rec.get("interfaces") or []) if i["sourceFile"] != fname]
            rec["interfaces"] = old + [iface]
        else:
            rec = {"id": mid, "equipId": spec["equip"], "vendor": VENDOR,
                   "model": spec["key"], "name": spec["key"], "cat": spec["cat"],
                   "tag": spec["tag"], "tags": [spec["tag"]], "status": "active",
                   "has": {"spec": False, "points": True}, "ede": False,
                   "spec": [], "io": [], "elec": None, "points": [],
                   "classifiedBy": "JCI 공조기 포털 문서 분류",
                   "gap": "정격·형번이 없다 — 매뉴얼 본문의 Modbus 레지스터 표만 취입했다. "
                          "표가 readWrite 를 안 주고, Range 는 배율이 걸린 raw 값이라 "
                          "공학 범위로 못 올렸다(포인트마다 gaps 에 적혀 있다).",
                   "extractor": "vendor_jci_air", "sourceDoc": fname,
                   "interfaces": [iface]}
        # 규칙 ④ — 만든 방법으로 확인하지 않는다. 표 인식 대신 줄 읽기로 다시 돌려 맞춰 본다.
        rec["crosscheck"] = A.crosscheck(path, points)
        n = sum(i["pointCount"] for i in rec["interfaces"])
        rec["summary"] = "유닛 제어반 Modbus 레지스터 %d판에서 취입 — 오브젝트 %d점" % (
            len(rec["interfaces"]), n)
        # 비교는 레코드를 **끝까지 만든 뒤**에 한다. 중간에 빠져나가면 그 뒤에 붙는 것
        # (교차 대조 같은 것)이 영영 기록되지 않는다 — 실제로 그래서 빠졌다.
        if before is not None and json.dumps(rec, ensure_ascii=False, sort_keys=True) == before:
            print("    ↷ %s — 이미 취입한 문서, 변경 없음" % mid)
            continue
        made += 1
        pts_total += len(points)
        if dry:
            print("    (dry) %s — 판 %d · %d점" % (mid, len(rec["interfaces"]), n))
            continue
        with open(path_m, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        print("    → %s — 판 %d · %d점" % (mid, len(rec["interfaces"]), n))
    print("\n모델 %d건 · 새 오브젝트 %d점" % (made, pts_total))
    return 0


def apply_iom(dry=False):
    """IOM 본문 포인트 표 → 모델의 interfaces[]. 제품이 이미 있으면 판을 잇는다."""
    import vendor_jci_ipu as P
    try:
        cat = catalog()
    except (OSError, ValueError):
        # 전체 JCI 카탈로그 스냅샷은 44MB라 저장소에 싣지 않는다. 본문 스캔의
        # 추적 가능한 prod/cat 메타만으로도 이 16건은 재현돼야 한다.
        cat = {}
    groups = collections.OrderedDict()
    for h, path in P.docs():
        meta = dict(cat.get(h.get("id"), {}))
        meta.setdefault("prod", h.get("prod") or "")
        meta.setdefault("category", h.get("cat") or "")
        prod = meta.get("prod") or ""
        if not prod:
            for k, v in IOM_PROD.items():
                if k.lower() in (h.get("title") or "").lower():
                    prod = v
                    break
        key = IOM_MODEL.get(prod, prod or os.path.basename(path))
        groups.setdefault(key, []).append((h, path, meta))

    made = pts = 0
    for key, items in groups.items():
        ifaces = []
        for h, path, meta in items:
            rows, unk, head, skipped = P.parse_doc(path)
            if unk:
                detail = ", ".join("%s×%s" % item for item in sorted(unk.items()))
                raise ValueError("%s: 못 알아본 포인트 표 열 — %s" %
                                 (os.path.basename(path), detail))
            if not rows:
                print("  ⚠ %-58s 0점" % os.path.basename(path)[:58])
                continue
            row = {"file": os.path.basename(path), "title": h.get("title") or "",
                   "id": h.get("id", "")}
            made_ifs = build_interfaces(row, P.FAMILY, rows, skipped)
            for it in made_ifs:
                basis = it.get("note") or ""
                it["note"] = " · ".join(x for x in (
                    basis, IOM_NOTE) if x)
            ifaces.extend(made_ifs)
            print("  · %-58s %5d점" % ((h.get("title") or "")[:58], len(rows)))
        if not ifaces:
            continue
        equip, cat4, tag = IOM_EQUIP.get(
            (items[0][2] or {}).get("category", ""), ("e5", "HVAC.AIR.RTU", "rooftop"))
        mid = S.model_id(VENDOR, key)
        path_m = os.path.join(DATA, "models", mid + ".json")
        new_ifaces = ifaces
        if os.path.exists(path_m):
            # 같은 제품이 이미 있다 — 새 문서는 잇고, 같은 sourceFile은 최신 파서
            # 결과로 교체한다. 그래야 파서 결함을 고친 뒤 삭제 없이 재생성할 수 있다.
            with open(path_m, encoding="utf-8") as f:
                rec = json.load(f)
            old_ifaces = rec.get("interfaces") or []
            have = {i["sourceFile"] for i in old_ifaces}
            new_ifaces = [i for i in ifaces if i["sourceFile"] not in have]
            incoming_sources = {i["sourceFile"] for i in ifaces}
            merged_ifaces = ([i for i in old_ifaces
                              if i.get("sourceFile") not in incoming_sources] + ifaces)
            if merged_ifaces == old_ifaces:
                print("  ↷ %s — 이미 취입한 문서, 변경 없음" % mid)
                continue
            rec["interfaces"] = merged_ifaces
        else:
            rec = {"id": mid, "equipId": equip, "vendor": VENDOR, "model": key,
                   "name": key, "cat": cat4, "tag": tag, "tags": [tag],
                   "status": "active", "has": {"spec": False, "points": True},
                   "ede": False, "spec": [], "io": [], "elec": None, "points": [],
                   "classifiedBy": "JCI 문서 분류 %r" % (items[0][2] or {}).get("category", ""),
                   "gap": "정격·형번이 없다 — IOM 본문의 포인트 표만 취입했다. "
                          "형번별 정격은 같은 매뉴얼의 다른 절이나 제품 카탈로그에서 따로 와야 한다.",
                   "extractor": "vendor_jci", "sourceDoc": ifaces[0]["sourceFile"],
                   "interfaces": ifaces}
        n = sum(i["pointCount"] for i in rec["interfaces"])
        rec["summary"] = ("BAS 포인트 표 %d판에서 취입 — 오브젝트 %d점"
                          % (len(rec["interfaces"]), n))
        rec["comm"] = comm_rows(rec["interfaces"])
        made += 1
        pts += sum(i["pointCount"] for i in new_ifaces)
        if dry:
            print("  (dry) %s — 판 %d · %d점" % (mid, len(rec["interfaces"]), n))
            continue
        with open(path_m, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        print("  ✓ %s — 판 %d · 총 %d점" % (mid, len(rec["interfaces"]), n))
    print("\n모델 %d건 · 새 오브젝트 %d점" % (made, pts))

    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="JCI 포인트 리스트 취입")
    ap.add_argument("--route", action="store_true", help="계통 판정만 (빠름)")
    ap.add_argument("--apply", action="store_true", help="모델 레코드 생성")
    ap.add_argument("--dry", action="store_true", help="파싱은 하되 쓰지 않는다")
    ap.add_argument("--no-crosscheck", action="store_true", help="교차 대조 건너뛰기")
    ap.add_argument("--apply-air", action="store_true",
                    help="공조기 포털 Modbus 레지스터 표 취입")
    ap.add_argument("--apply-iom", action="store_true",
                    help="IOM 본문형(IPU/Series-100) 취입")
    ap.add_argument("--export", action="store_true",
                    help="검토 화면 review/jci-ingest.html 을 낸다")
    # 원문 쪽 그림은 **기본으로 넣는다**. 안 넣으면 행을 눌렀을 때 보여 줄 그림이 없어
    # 원문 PDF 로 화면을 떠나 버리는데, 그게 이 화면의 목적(파싱 육안 대조)을 깬다.
    # 예전 기본값(넣지 않음)으로 뽑았다가 "왜 자꾸 원문 파일로 넘어가냐"를 반복해서 밟았다.
    ap.add_argument("--no-pages", action="store_true",
                    help="원문 쪽 그림을 넣지 않는다 (가볍다 — 시험용. --out 으로 딴 데 써야 한다)")
    ap.add_argument("--out", help="낼 파일 경로 (기본: review/jci-ingest.html)")
    ap.add_argument("--audit-pages", action="store_true",
                    help="원문 쪽 그림이 잘리지 않는지 전면 렌더로 대조한다 (잘리면 exit 1)")
    ap.add_argument("--with-pages", action="store_true",
                    help="(이제 기본값이라 아무 일도 하지 않는다 — 예전 명령을 위해 남겨 둔다)")
    ap.add_argument("--refresh", action="store_true",
                    help="취입한 모델의 메타만 다시 계산 (PDF 재파싱 없음)")
    ap.add_argument("--only", help="저장 이름에 이 글자가 든 문서만")
    a = ap.parse_args(argv)
    if a.audit_pages:
        return audit_pages(only=a.only)
    if a.apply_air:
        return apply_air(dry=a.dry)
    if a.apply_iom:
        return apply_iom(dry=a.dry)
    if a.export:
        # 그림 없는 축소본이 산출물을 덮으면, 행을 눌러도 팝업이 안 뜨고 원문 PDF 로
        # 나가 버린다. 작업 중 빠른 확인용으로 뽑았다가 그대로 두어 실제로 밟았다 —
        # 축소본은 반드시 딴 경로로 뺀다.
        if a.no_pages and not a.out:
            print("✗ --no-pages 는 시험용이라 산출물을 덮을 수 없다. --out 으로 딴 경로를 준다.")
            print("  예: python ingest_jci.py --export --no-pages --out probe.html")
            return 2
        return export(out_path=a.out, with_pages=not a.no_pages, only=a.only)
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
