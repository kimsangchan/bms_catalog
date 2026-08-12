# -*- coding: utf-8 -*-
"""JCI Native 계열 포인트 리스트 → point-schema 구조.

계통이 무엇인가
  York 냉동기·루프탑의 **게이트웨이 없는 직결 통신** 문서 묶음이다. 두 갈래다.

  ① Native (4건) — YCAV/YCIV · YVAA/YVFA/YAGK · YSAA · Scroll Chiller.
     한 보드가 BACnet MS/TP · Modbus RTU · N2 셋을 동시에 낸다("No external
     Gateway is required"). LON 열이 아예 없다.
       Item Ref Num | BACnet Name | BACnet Object Instance | Modbus Address
       | Modbus Data Type Supported | Modbus Scaling | N2 Metasys
       | Engineering Units(Imperial·SI) | Point List Description | 1‥10
  ② Native/Panel (2건) — ECO2 루프탑 한 대의 **패널 표시명 기준** 목록.
     같은 장비인데 프로토콜 블록이 문서별로 배타적이다.
       YPAL 판: LON Object Name · SNVT TYPE · N2 Metasys Address (BACnet 없음)
       ECO2 판: BACnet NAME · BACNET Object/Instance · MODBUS … (LON 없음)
     이 계통만 'READ WRITE' 열과 'Availability' 열을 명시적으로 준다.

이 계통에서 실제로 밟은 함정 (전부 원문으로 확인했다)
  1. **1쪽을 통째로 버리면 안 된다.** 표 인식이 1쪽의 개정이력표(Native) ·
     NOTES 상자(Panel)를 포인트 표와 **한 그리드로 묶어** 낸다. 그래서 표의
     0행 머리글이 'Item|Version|York P/N' 이거나 'NOTES' 다. 0행만 보고
     걸러내면 1쪽에 실린 포인트가 조용히 사라진다 — 실측 Native 4건 132점,
     Panel 2건 73점, 합 205점(전체 677점의 30%)이 1쪽에 있다.
     **머리글은 표 아무 행에나 있다**고 보고 찾는다.
  2. **머리글 낱말이 쪼개진다.** 'Availabi lity'(YPAL) · 'Availb ility'(ECO2,
     원문 오타) · 'BACNET Object/Insta nce'. 공백을 지운 형태로 맞춰야 한다.
     못 맞추면 그 열이 통째로 빠진다.
  3. **밑줄이 뭉개진다 — 그것도 문서마다 다른 방식으로.** 표 인식이
     'S2_HI_MTR_T' 는 공백으로('_ _ S2 HI MTR T'), 'COND_FAN_1A' 는 아예
     지워서('CONDFAN1A') 뱉는다. 게다가 칸 안에서 줄바꿈된 이름은 원문에서도
     두 조각이다('S1_COND_FAN_' + 'VSD_FAULT'). 단순 치환은 금물이라
     **같은 쪽 get_text() 를 1·2·3 낱말 이어붙인 색인으로 만들어 대조**하고
     실제로 있는 낱말만 복원한다(point-schema lon.snvtType 주석).
  4. **'Modbus Data Type Supported' 열에 데이터형이 없다.** 값이 '03,04' ·
     '01,03,05,06,15' 로 **함수코드**다(ECO2 문서의 별도 'Modbus Function
     Codes' 열과 값 모양이 같다). 머리글만 믿고 modbus.dataType 에 넣으면
     Signed/Unsigned 자리에 함수코드가 들어간다 → functionCodes 로 보내고
     dataType 은 gap. 데이터형은 표가 아니라 NOTES 5번 문장에만 있다
     ("Modbus values are all of type signed") — 행 단위 근거가 아니라 안 싣는다.
  5. **Native 는 'READ WRITE' 열이 없고 밴드 행이 대신한다.**
     'ANALOG WRITE POINTS' · 'BINARY READ ONLY POINTS' 같은 구분 행을 물고
     내려가야 readWrite 와 group 이 생긴다(point-schema nonPointColumns.bandRows).
     밴드를 그냥 버리면 이 계통 전체가 readWrite 미상이 된다.
  6. **이름이 다 빈 행은 예약 슬롯이다.** 번호만 있고 나머지가 비었다 —
     실측 Panel 16행. 포인트로 싣지 않고 세어서 돌려준다.
  7. **긴 이름 열의 유무가 갈린다.** Native 는 'Point List Description' 이
     사람이 읽는 이름이다. Panel 은 그런 열이 아예 없다 — 'PANEL DISPLAYED
     NAME' 은 shortName 이고 name 으로 승격하지 않는다(point-schema common.name).
     Panel 레코드는 name 을 비우고 gaps 에 '문서에 긴 이름 열 없음' 을 적는다.

  ⚠ 과제 지시와 원문이 갈린 곳 — Native 의 'BACnet Object Instance' 열은
     인스턴스만 주지 않는다. 실측 값이 전부 'AI25' · 'BI17' · 'AV1' 꼴이고
     같은 문서 NOTES 3번이 "BACnet Object Types: 0 = Analog In, 1 = Analog
     Out, …" 로 타입 체계를 밝힌다. 즉 **타입은 열이 아니라 값 접두에 있다.**
     지어내는 것이 아니라 읽는 것이므로 bacnet.objectType 으로 올리되,
     어디서 왔는지 알 수 있게 bacnet.objectTypeSource 에 근거를 적고 원표기를
     sourceColumns 에 남긴다. 접두가 없거나 schema.py 가 모르는 값일 때만
     gaps 에 'bacnet.objectType' 을 적는다. (YZD 의 'BO0001' 함정과는 다르다 —
     저쪽은 접두가 BACnet 의미가 아니었고, 여기는 문서가 BACnet 이라고 밝힌다.)

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_native.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_native.py --parse <문서ID|파일경로>
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PROBE = os.path.join(DATA, "raw", "_probe_jci")
sys.path.insert(0, HERE)
import specs as SP      # noqa: E402
import schema as S      # noqa: E402

FAMILY_NATIVE = "Native"
FAMILY_PANEL = "Native/Panel"

# 머리글 낱말 → 우리 열 이름. **공백을 지운 머리글**에 맞춘다 —
# 'Availabi lity' · 'Availb ility' · 'BACNET Object/Insta nce' 처럼 낱말이
# 쪼개져 나오는 것을 여기서 흡수한다(함정 2). 순서가 곧 우선순위다.
COLMAP = [
    ("itemRef",    r"^ItemRefNum"),
    # 'Point List Code: S=…' 범례와 머리글이 한 칸에 합쳐져 오므로 부분일치로 찾는다
    ("longName",   r"PointListDescription"),
    ("panelName",  r"PANELDISPLAYEDNAME$"),
    ("bacName",    r"^BACnetNAME$"),
    ("bacObj",     r"^BACnet.*Object.*Instance"),
    ("mbAddress",  r"^MODBUSAddress$|^ModbusAddress$"),
    ("mbFunc",     r"^ModbusFunctionCodes"),
    ("mbRef",      r"^ModbusReferences"),
    # ⚠ 머리글은 '데이터형'이라 하는데 값은 함수코드다 — 라우팅은 row_to_point 에서
    ("mbTypeCol",  r"^ModbusDataTypeSupported"),
    ("mbScale",    r"^ModbusScaling"),
    ("n2",         r"^N2Metasys"),
    ("lonName",    r"^LONObjectName"),
    ("snvt",       r"^SNVTTYPE$|SNVTType$"),
    ("unitSI",     r"^SI$|^EngineeringUnitsSI$"),
    ("unitIP",     r"^(Engineering|ENG)UNITS"),
    ("readWrite",  r"^READWRITE$"),
    ("avail",      r"^Avail\w*lity$"),
    ("note",       r"^COMMENTS$"),
    ("matrix",     r"^([1-9]|10)$"),
]

# 'AI25' · 'AI 37' · 'AI_1' · 'AV1' → (타입, 인스턴스)
OBJ = re.compile(r"^([A-Za-z]{2,4})\s*[._\-]?\s*(\d+)$")
# 'ADF 29' · 'ADF62' · 'BD 1' · 'BD20' → (종별, 주소)
N2 = re.compile(r"^([A-Z]{2,3})\s*(\d+)$")
# 'ANALOG WRITE POINTS' · 'BINARY READ ONLY POINTS' · 'READS:' — 포인트가 아니라 밴드
BAND = re.compile(r"^(ANALOG|BINARY|READS|WRITES)\b", re.I)
# 머리글 아래 붙는 주석 참조 줄 — 'See Note 1,2' · 'Notes 4,8' · 'Note 7'
NOTEREF = re.compile(r"^(See\s+)?Notes?\s*[\d,\s]*$", re.I)
# 'Modbus References' 의 레지스터 대역 표기
REFCLASS = {"0X": "coil", "1X": "discrete-input",
            "3X": "input-register", "4X": "holding-register"}
# 'READ WRITE' 열 허용값
RW = {"R": "R", "W": "W", "R/W": "R/W", "RW": "R/W", "W/R": "R/W"}
# 값이 아니라 '없음'을 뜻하는 셀 (point-schema rules.emptyMeansAbsent)
ABSENT = {"", "-", "—", "_", "n/a", "na", "none", "*"}


def clean(v):
    """조판 아티팩트를 지운다 — 게이트를 걸기 **전에** 해야 한다.

    이 계통은 밑줄 글리프가 별도 조각으로 잡혀 '_ _ S2 HI MTR T' ·
    '_ SNVT count f _' 처럼 온다. 앵커 정규식을 그 앞에 걸면 오염된 값이
    그냥 통과해 최후 방어선이 무력해진다 (point-schema rules.artifactCleanupFirst).
    여기서는 **가장자리 조각만** 뗀다 — 가운데 공백이 원래 밑줄인지는
    혼자 판단할 수 없어 restore() 가 원문 토큰과 대조해 정한다.
    """
    t = SP._c(v)
    t = re.sub(r"^[_\s]+|[_\s]+$", "", t)
    return t.strip()


def squeeze(h):
    """머리글에서 공백을 지운다 — 낱말이 쪼개진 머리글을 붙여 알아보려고."""
    return re.sub(r"\s+", "", SP._c(h))


def scrambled(h, target):
    """글자가 섞이거나 흩어진 머리글인가 — 글자 집합으로 알아본다.

    이 계통의 손상은 대개 공백 삽입이라 squeeze() 로 잡히지만, 'Availbility'
    처럼 **원문 오타**까지 겹치면 정규식이 놓친다. 그때를 위한 마지막 그물이다.
    글자가 하나라도 모자라면 아니라고 본다(SC-EQ 어댑터와 같은 판정).
    """
    from collections import Counter
    a = re.sub(r"[^a-z]", "", (h or "").lower())
    b = re.sub(r"[^a-z]", "", target.lower())
    if not a or len(a) > len(b) * 2:
        return False
    ca, cb = Counter(a), Counter(b)
    # 오타로 한 글자쯤 빠지는 것은 봐준다 — 두 글자 넘게 모자라면 아니다
    return sum((cb - ca).values()) <= 1


def header_map(head):
    """머리글 → {우리이름: 열번호}. 못 알아본 열은 원문 이름 그대로 남긴다.

    matrix('1'~'10')는 여러 칸이라 리스트로 모은다 — 형번 적용 행렬이다.
    '_head' 에는 원문 머리글을 표기 그대로 담는다 — sourceColumns 키로 쓴다.
    """
    out, unknown = {"_head": {}}, {}

    def put(name, i, h):
        if name == "matrix":
            out.setdefault("matrix", []).append((squeeze(h), i))
        else:
            out.setdefault(name, i)
            out["_head"].setdefault(name, h)

    for i, h in enumerate(head):
        h = SP._c(h)
        if not h:
            continue
        sq = squeeze(h)
        for name, pat in COLMAP:
            if re.search(pat, sq, re.I):
                put(name, i, h)
                break
        else:
            if "avail" not in out and scrambled(sq, "Availability"):
                put("avail", i, h)          # 'Availbility' 같은 원문 오타
            elif "readWrite" not in out and scrambled(sq, "ReadWrite"):
                put("readWrite", i, h)
            else:
                unknown[h[:40]] = i
    return out, unknown


def is_header(row):
    """이 행이 포인트 표의 머리글인가. 표 **아무 행**에나 있을 수 있다(함정 1)."""
    return "ITEMREFNUM" in squeeze(" ".join(SP._c(c) for c in row)).upper()


def is_notes_marker(row):
    """'NOTES' 한 칸만 있는 행 — 여기부터 아래는 주석 상자다."""
    filled = [SP._c(c) for c in row if SP._c(c)]
    return len(filled) == 1 and filled[0].upper() in ("NOTES", "NOTE")


def merge_header(rows, i):
    """머리글이 두 줄인 Native 형을 한 줄로 합친다.

    Native 는 'Engineering Units' 아래 'Imperial|SI' 가, 'Point List Code:
    S = Standard…' 범례 아래 'Point List Description|1|2|…10' 이 따로 온다.
    윗줄만 읽으면 이름 열과 형번 행렬이 통째로 사라진다.
    """
    head = [SP._c(c) for c in rows[i]]
    nxt = [SP._c(c) for c in rows[i + 1]] if i + 1 < len(rows) else []
    if not nxt or not re.search(r"PointListDescription", squeeze(" ".join(nxt)), re.I):
        return head, i + 1
    merged = []
    for j in range(max(len(head), len(nxt))):
        a = head[j] if j < len(head) else ""
        b = nxt[j] if j < len(nxt) else ""
        merged.append((a + " " + b).strip())
    return merged, i + 2


def page_index(page):
    """쪽 원문 → (원문 그대로, 구분자 지운 열쇠 → 원래 낱말).

    밑줄 복원을 대조할 유일한 근거다. 표 인식은 같은 밑줄을 문서마다 다르게
    망가뜨린다 — 'S2_HI_MTR_T' 는 공백으로('S2 HI MTR T'), 'COND_FAN_1A' 는
    아예 지워서('CONDFAN1A') 온다. 그래서 공백·밑줄을 모두 지운 열쇠로 찾는다.
    한 열쇠에 서로 다른 낱말이 둘 이상 걸리면 모호하므로 복원하지 않는다.
    """
    text = page.get_text()
    toks = text.split()
    # 이름이 칸 안에서 줄바꿈되면 원문에서도 두 조각이 된다
    # ('S1_COND_FAN_' + 'VSD_FAULT'). 그래서 이어붙인 2·3 낱말도 색인한다 —
    # 짧은 쪽을 먼저 찾아 쓰고, 같은 열쇠에 다른 낱말이 걸리면 포기한다.
    return text, [_key_index("".join(toks[i:i + n]) for i in range(len(toks) - n + 1))
                  for n in (1, 2, 3)]


def _key_index(strings):
    d = {}
    for s in strings:
        key = re.sub(r"[\s_]+", "", s)
        if not key:
            continue
        if key in d and d[key] != s:
            d[key] = None          # 모호 — 복원 금지 표식
        else:
            d.setdefault(key, s)
    return d


def restore(v, ctx):
    """밑줄이 뭉개진 값을 원문과 대조해 되돌린다.

    '_ _ S2 HI MTR T' → 'S2_HI_MTR_T', 'CONDFAN1A' → 'COND_FAN_1A',
    '_ SNVT count f _' → 'SNVT_count_f'.
    **단순 치환은 하지 않는다**(point-schema lon.snvtType: "복원은 get_text()
    대조로, 밑줄 단순 치환 금지"). 원문에 그 낱말이 실제로 있을 때만 복원을
    인정하고, 아니면 손대지 않은 값과 False 를 돌려준다.
    'SPARE AV1' 처럼 원문에도 공백인 값은 그대로 통과시킨다 — 안 그러면
    멀쩡한 이름이 전부 '복원 실패'로 잡힌다.
    """
    text, grams = ctx
    t = clean(v)
    if not t:
        return t, True
    key = re.sub(r"[\s_]+", "", t)
    for g in grams:
        if key in g:
            return (t, False) if g[key] is None else (g[key], True)
    return t, (t in text)


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계)."""
    import fitz
    doc = fitz.open(path)
    rows, unknown_cols, head_seen = [], {}, None
    skipped = {"reserved": 0, "banner": 0, "band": 0, "unrestored": 0}
    fname = os.path.basename(path)
    # ⚠ 밴드는 **쪽을 넘어 이어진다** — 'ANALOG READ ONLY POINTS' 가 1쪽에서
    #   시작해 2쪽까지 가고 'BINARY READ ONLY POINTS' 가 3쪽에서 이어받는다
    #   (Ul95·p4Eq·PqH6 에서 확인). 표마다 초기화하면 2쪽 이후가 readWrite 미상이
    #   된다 — 실측 Native 398점 중 186점이 그렇게 비었다.
    group = None
    for pi, pg in enumerate(doc):
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        ctx = page_index(pg)
        for t in tabs:
            data = t.extract()
            if len(data) < 2:
                continue
            # ⚠ 머리글은 0행에 있다고 가정하지 않는다 — 1쪽에서는 개정이력표·
            #   NOTES 상자와 한 그리드로 묶여 중간 행에 온다(함정 1).
            hi = next((i for i, r in enumerate(data) if is_header(r)), None)
            if hi is None:
                continue
            head, start = merge_header(data, hi)
            cmap, unk = header_map(head)
            unknown_cols.update(unk)
            head_seen = head
            fam = FAMILY_NATIVE if "longName" in cmap else FAMILY_PANEL
            for r in data[start:]:
                # ⚠ NOTES 상자가 포인트 표 **아래**에 같은 그리드로 붙는 쪽이
                #   있다(Native 3쪽). 그 뒤 행은 전부 주석이라 포인트로 읽으면
                #   'Modbus values are all of type signed.' 가 이름이 된다.
                if is_notes_marker(r):
                    break
                rec, why = row_to_point(r, cmap, fam, fname, pi + 1, ctx, group)
                if isinstance(why, tuple):          # 밴드 행 — 뒤 행들이 물려받는다
                    group = why[1]
                    skipped["band"] += 1
                    continue
                if rec:
                    rows.append(rec)
                    if rec["provenance"].get("_unrestored"):
                        skipped["unrestored"] += rec["provenance"].pop("_unrestored")
                elif why:
                    skipped[why] = skipped.get(why, 0) + 1
    doc.close()
    return rows, unknown_cols, head_seen, skipped


def row_to_point(row, cmap, family, fname, page, ctx, group):
    """행 하나 → 포인트 레코드. 포인트가 아니면 (None, 사유)."""
    def cell(key):
        i = cmap.get(key)
        return clean(row[i]) if i is not None and i < len(row) else ""

    def cell_raw(key):
        i = cmap.get(key)
        return SP._c(row[i]) if i is not None and i < len(row) else ""

    item = cell("itemRef")
    long_name = cell("longName")
    panel = cell("panelName")
    filled = [clean(c) for c in row if clean(c)]

    if is_header(row):
        return None, "banner"
    # ── 밴드 행 · 주석 참조 줄 ────────────────────────────────────────
    #   'ANALOG WRITE POINTS'(Native, 한 칸) · 'READS:'(Panel, 머리글 바로 아래
    #   'See Note 1,2' 들과 한 줄에 온다). 열이 아니라 구분 행이라 여기서 물고
    #   내려가야 readWrite·group 이 생긴다(point-schema nonPointColumns.bandRows).
    #   판정: 값 칸이 전부 밴드 낱말이거나 주석 참조뿐인 행.
    #   ⚠ 진짜 밴드는 **혼자 있는 한 칸**이다. YPAL 1쪽의 'READS:' 는 'See Note
    #   1,2' 들과 같은 줄에 있고 닫는 'WRITES:' 가 문서 어디에도 없다 — 이걸
    #   밴드로 물면 3쪽의 쓰기 포인트까지 'READS:' 가 붙는다(READ WRITE 열이
    #   'W' 라고 말하는데도). 그래서 주석 참조와 섞인 줄은 밴드가 아니라 배너다.
    if filled and all(BAND.match(c) or NOTEREF.match(c) for c in filled):
        if len(filled) == 1 and BAND.match(filled[0]):
            return None, ("band", filled[0])
        return None, "banner"

    short = panel
    bac_name = cell("bacName")
    if not (long_name or short or bac_name):
        # ⚠ 예약 슬롯 — 번호만 있고 이름이 전부 빈 행이다(point-schema
        #   rules.reservedSlotNotAPoint). 원문이 빈칸이므로 포인트가 아니다.
        if item or filled:
            return None, "reserved"
        return None, None

    rec = {"common": {}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": family}}
    raw, gaps = {}, []
    unrestored = 0

    if item:
        rec["provenance"]["srcRef"] = item
    if group:
        rec["common"]["group"] = group

    # ── 이름 ─────────────────────────────────────────────────────────
    if family == FAMILY_NATIVE:
        if long_name:
            rec["common"]["name"] = long_name
    else:
        # ⚠ 'PANEL DISPLAYED NAME' 은 짧은 이름이다. name 으로 승격하면 다른
        #   계통의 name(사람이 읽는 설명문)과 성격이 어긋난다.
        if short:
            rec["common"]["shortName"] = short
        gaps.append("name — 문서에 긴 이름 열 없음('PANEL DISPLAYED NAME'은 shortName)")

    # ── BACnet ───────────────────────────────────────────────────────
    if bac_name:
        nm, ok = restore(cell_raw("bacName"), ctx)
        if not ok:
            unrestored += 1
            raw[_headname(cmap, "bacName") or "BACnet Name"] = cell_raw("bacName")
        rec["blocks"].setdefault("bacnet", {})["objectName"] = nm
    obj = cell("bacObj")
    if obj and obj.lower() not in ABSENT:
        m = OBJ.match(obj)
        canon = S.TYPE_ALIAS.get(m.group(1).upper(), m.group(1).upper()) if m else None
        if canon in S.BACNET_TYPES:
            b = rec["blocks"].setdefault("bacnet", {})
            b["objectType"] = canon
            b["instance"] = int(m.group(2))
            # ⚠ 타입 전용 열이 없다 — 타입은 이 값의 접두에서 읽었다.
            #   어디서 왔는지 남겨야 나중에 되짚을 수 있다.
            b["objectTypeSource"] = "'%s' 값 접두 (문서에 오브젝트 타입 전용 열 없음)" % (
                _headname(cmap, "bacObj") or "BACnet Object Instance")
            raw[_headname(cmap, "bacObj") or "BACnet Object Instance"] = cell_raw("bacObj")
        else:
            raw[_headname(cmap, "bacObj") or "BACnet Object Instance"] = obj
            gaps.append("bacnet.objectType — 접두를 알아볼 수 없다(%r)" % obj)

    # ── N2 ───────────────────────────────────────────────────────────
    n2 = cell("n2")
    if n2 and n2.lower() not in ABSENT:
        m = N2.match(n2)
        if m:
            rec["blocks"].setdefault("n2", {})["pointType"] = m.group(1)
            rec["blocks"]["n2"]["address"] = int(m.group(2))
        else:
            raw[_headname(cmap, "n2") or "N2 Metasys"] = n2

    # ── Modbus ───────────────────────────────────────────────────────
    mb = {}
    a = cell("mbAddress")
    if a and re.match(r"^\d+$", a):
        mb["address"] = int(a)
        mb["addressBase"] = "unknown"       # 0/1-base 를 문서가 안 밝힌다
    elif a and a.lower() not in ABSENT:
        raw[_headname(cmap, "mbAddress") or "MODBUS Address"] = a
    sc = cell("mbScale")
    if sc and sc.lower() not in ABSENT:
        mb["scaleRaw"] = sc                 # 'x10'/'Div 10' — 방향 확정 전이라 수치화 보류
    fc = cell("mbFunc")
    if fc and fc.lower() not in ABSENT:
        codes = [int(x) for x in re.findall(r"\d+", fc)]
        if codes:
            mb["functionCodes"] = codes
    # ⚠ 'Modbus Data Type Supported' 열 — 머리글은 데이터형인데 값이 함수코드다.
    #   머리글만 믿고 dataType 에 넣으면 Signed/Unsigned 자리에 '03,04' 가 앉는다.
    dt = cell("mbTypeCol")
    if dt and dt.lower() not in ABSENT:
        norm = {"unsigned": "Unsigned", "signed": "Signed"}.get(dt.lower())
        if norm:
            mb["dataType"] = norm
        elif re.match(r"^[\d,\s]+$", dt):
            codes = [int(x) for x in re.findall(r"\d+", dt)]
            if codes:
                mb.setdefault("functionCodes", codes)
            raw[_headname(cmap, "mbTypeCol") or "Modbus Data Type Supported"] = dt
            gaps.append("modbus.dataType — 머리글은 데이터형이나 값이 함수코드다"
                        "(데이터형은 NOTES 문장에만 있어 행 단위 근거가 없다)")
        else:
            raw[_headname(cmap, "mbTypeCol") or "Modbus Data Type Supported"] = dt
    rf = cell("mbRef")
    if rf and rf.lower() not in ABSENT:
        raw[_headname(cmap, "mbRef") or "Modbus References"] = rf
        toks = [x.strip().upper() for x in re.split(r"[,\s]+", rf) if x.strip()]
        if len(toks) == 1 and toks[0] in REFCLASS:
            mb["refClass"] = REFCLASS[toks[0]]
        # 여러 대역을 동시에 주면('4X, 3X') 단일 enum 으로 못 줄인다 — 원표기만 남긴다
    if mb:
        rec["blocks"]["modbus"] = mb

    # ── LON (YPAL 판만) ──────────────────────────────────────────────
    nv = cell("lonName")
    if nv and nv.lower() not in ABSENT:
        name, ok = restore(cell_raw("lonName"), ctx)
        if not ok:
            unrestored += 1
            raw[_headname(cmap, "lonName") or "LON Object Name"] = cell_raw("lonName")
        lon = rec["blocks"].setdefault("lon", {})
        lon["nvName"] = name
        low = name.lower()
        for pre in ("nvi", "nvo", "nci"):
            if low.startswith(pre):
                lon["direction"] = pre
                break
    sv = cell("snvt")
    if sv and sv.lower() not in ABSENT:
        stype, ok = restore(cell_raw("snvt"), ctx)
        if ok:
            rec["blocks"].setdefault("lon", {})["snvtType"] = stype
        else:
            unrestored += 1
            raw[_headname(cmap, "snvt") or "SNVT TYPE"] = cell_raw("snvt")

    # ── 단위 ─────────────────────────────────────────────────────────
    for key, field in (("unitIP", "unitIP"), ("unitSI", "unitSI")):
        u = cell(key)
        if not u or u.lower() in ABSENT:
            continue
        # '0/1' · '0, 1' 은 단위가 아니라 값 집합이다 — 단위 자리에 넣지 않는다
        if re.match(r"^[\d\s,/]+$", u):
            raw[_headname(cmap, key) or key] = u
            continue
        rec["common"][field] = u

    # ── 읽기/쓰기 ────────────────────────────────────────────────────
    rw = cell("readWrite")
    if rw:
        v = RW.get(rw.upper().replace(" ", ""))
        if v:
            rec["common"]["readWrite"] = v
        else:
            raw[_headname(cmap, "readWrite") or "READ WRITE"] = rw
    elif group:
        # Native 는 열이 없다 — 밴드 행이 유일한 근거다
        if re.search(r"READ\s*ONLY", group, re.I):
            rec["common"]["readWrite"] = "R"
        elif re.search(r"\bWRITE", group, re.I):
            rec["common"]["readWrite"] = "W"

    # ── 형번 적용 ────────────────────────────────────────────────────
    av = cell("avail")
    if av:
        if av.upper() in ("S", "O", "N"):
            rec["common"]["availability"] = {"code": av.upper(), "raw": av}
        else:
            rec["common"]["availability"] = {"raw": av}
    elif cmap.get("matrix"):
        got = [(lab, clean(row[i])) for lab, i in cmap["matrix"]
               if i < len(row) and clean(row[i])]
        if got:
            vals = {v for _, v in got}
            a2 = {"raw": " ".join("%s=%s" % kv for kv in got),
                  "column": ",".join(lab for lab, _ in got)}
            if len(vals) == 1 and next(iter(vals)).upper() in ("S", "O", "N"):
                a2["code"] = next(iter(vals)).upper()
            rec["common"]["availability"] = a2
            gaps.append("availability — 1~10 열 번호↔형번 대응표가 문서에 없다")

    # ── 비고 · 상태 ──────────────────────────────────────────────────
    note = cell_raw("note")
    if note:
        st = read_states(note)
        if st:
            rec["common"]["states"] = [{"code": c, "label": l} for c, l in st]
            raw[_headname(cmap, "note") or "COMMENTS"] = note
        else:
            rec["common"]["note"] = note
    # 이름에 눌러붙은 상태 열거 — 'Chilled Liquid Type [0=Water, 1=Glycol]'
    nm = rec["common"].get("name")
    if nm and "states" not in rec["common"]:
        st, rest, clipped = split_states(nm)
        if st:
            rec["common"]["states"] = [{"code": c, "label": l} for c, l in st]
            rec["common"]["name"] = rest
            raw[_headname(cmap, "longName") or "Point List Description"] = nm
            if clipped:
                gaps.append("states — 원문 대괄호가 닫히지 않았다(칸 폭에 잘림)."
                            " 뒤에 상태가 더 있을 수 있다")

    if unrestored:
        rec["provenance"]["_unrestored"] = unrestored
    if raw:
        rec["provenance"]["sourceColumns"] = raw
    if gaps:
        rec["provenance"]["gaps"] = gaps
    for k in ("common", "blocks"):
        if not rec[k]:
            del rec[k]
    return rec, None


def _headname(cmap, key):
    """sourceColumns 에 쓸 원문 머리글 — 표기 그대로 남긴다.

    'Availabi lity' 처럼 쪼개진 표기도 정규화하지 않는다(point-schema
    provenance.sourceColumns: "열 머리글은 쪽마다 흔들려도 표기 그대로 둔다").
    """
    return (cmap.get("_head") or {}).get(key)


# '0 = OFF, 1 = ON' · '0 - DRY BULB; 1 - SINGLE ENTHALPY' · '0 = OFF / 1 = ON'
# 구분자에 '/' 를 넣어야 한다 — 안 넣으면 라벨이 다음 항목까지 삼킨다
STATE = re.compile(r"(-?\d+)\s*[=\-:]\s*([^,;/0-9][^,;/]*)")


def split_states(text):
    """이름에 눌러붙은 상태 열거를 뗀다 → (states, 남은 이름, 잘림 여부).

    세 모양이 온다.
      'Chilled Liquid Type [0=Water, 1=Glycol]'            닫힌 대괄호
      'Sys 1 System State [0=Stopped, … 5=Pre-Run'         ⚠ **원문이 칸 폭에
          잘려 닫는 괄호가 없다**(실측 6행). 닫힌 것만 찾으면 상태가 통째로
          빠지고, 그렇다고 잘린 것을 완전한 목록처럼 실으면 뒤에 더 있는지
          알 수 없다 — 그래서 싣되 gaps 에 잘림을 적는다.
      'Flow Switch Status: 0=Off, 1=On'                    괄호 없이 콜론
    '[0-14]'(값 범위)처럼 '='·':' 가 없는 괄호는 상태가 아니라 건드리지 않는다.
    """
    clipped = False
    m = re.search(r"[\[(]([^\[\]()]*?\d\s*[=:][^\[\]()]*)[\])]", text)
    if not m:
        m = re.search(r"\[([^\[\]]*\d\s*[=:][^\[\]]*)$", text)
        clipped = bool(m)
    if not m:
        m = re.search(r":\s*(\d+\s*=[^\[\]]*)$", text)
    if not m:
        return [], text, False
    st = read_states(m.group(1))
    if not st:
        return [], text, False
    return st, SP._c(text[:m.start()] + text[m.end():]).strip(" :,"), clipped


def read_states(text):
    got = []
    for code, label in STATE.findall(text or ""):
        label = SP._c(label).strip(" .,;·")
        if label:
            got.append((code, label[:80]))
    return got if len(got) >= 2 else []


def main(argv):
    ap = argparse.ArgumentParser(description="JCI Native 계열 어댑터")
    ap.add_argument("--scan", action="store_true", help="계통 전체 파싱 통계")
    ap.add_argument("--parse", help="문서 하나 (파일경로 또는 ID 앞자리)")
    ap.add_argument("--limit", type=int, default=6, help="--parse 시 보여줄 행 수")
    a = ap.parse_args(argv)

    if a.parse:
        cands = ([a.parse] if os.path.exists(a.parse)
                 else glob.glob(os.path.join(PROBE, a.parse + "*")))
        if not cands:
            print("파일을 못 찾겠다: %s" % a.parse)
            return 1
        rows, unk, head, skip = parse_doc(cands[0])
        print("%s — 포인트 %d" % (os.path.basename(cands[0]), len(rows)))
        if head:
            print("머리글: %s" % " | ".join(h[:24] for h in head if h))
        if unk:
            print("못 알아본 열: %s" % ", ".join(unk))
        print("뺀 행: %s" % ", ".join("%s %d" % kv for kv in skip.items() if kv[1]))
        for r in rows[:a.limit]:
            print("\n" + json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    if a.scan:
        from collections import Counter
        tot, allunk, allskip = Counter(), Counter(), Counter()
        hit = 0
        for f in sorted(glob.glob(os.path.join(PROBE, "*.pdf"))):
            rows, unk, head, skip = parse_doc(f)
            if not rows:
                continue
            hit += 1
            fam = rows[0]["provenance"]["family"]
            tot[fam] += len(rows)
            for u in unk:
                allunk[u] += 1
            for k, v in skip.items():
                allskip[k] += v
            for r in rows:
                for blk, fields in (r.get("blocks") or {}).items():
                    for k in fields:
                        tot["  %s.%s" % (blk, k)] += 1
                for k in (r.get("common") or {}):
                    tot["  " + k] += 1
                if (r.get("provenance") or {}).get("gaps"):
                    tot["  (gaps)"] += 1
            print("  %-30s %5d점  %-12s  뺀 행 %s" % (
                os.path.basename(f)[:30], len(rows), fam,
                ", ".join("%s %d" % kv for kv in skip.items() if kv[1]) or "없음"))
        print("\n문서 %d건에서 파싱 · 합계 %d점" % (
            hit, sum(v for k, v in tot.items() if not k.startswith("  "))))
        for k, v in tot.most_common():
            print("   %-30s %6d" % (k, v))
        print("\n뺀 행 합계: %s" % ", ".join("%s %d" % kv for kv in allskip.items()))
        if allunk:
            print("\n못 알아본 열 (문서 수)")
            for k, v in allunk.most_common(12):
                print("   %-44s %d" % (k[:44], v))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
