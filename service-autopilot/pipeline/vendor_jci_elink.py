# -*- coding: utf-8 -*-
"""JCI E-Link 게이트웨이 계통 포인트 리스트 → point-schema 구조.

계통이 무엇인가
  York 냉동기·공조기의 **E-Link 게이트웨이** 데이터 맵. 이 저장소가 본 JCI 문서
  가운데 가장 크고(29건) 가장 험한 묶음이다. E-Link 는 York 내부 프로토콜
  (York Talk)을 현장 프로토콜(BACnet·LON·N2·Modbus)로 바꿔 주는 상자라서,
  한 행에 **네 프로토콜 주소가 나란히** 실린다. point-schema 가 평면 필드를
  버리고 blocks 로 간 이유가 바로 이 표다.

  ⚠ SC-EQ 와 달리 **머리글이 표의 0행이 아니다.** 아래 함정을 먼저 읽어라.

세 하위형 (한 문서 안에 섞여 있을 수 있다 — 문서가 아니라 **머리글**로 가른다)
  ① E-Link/BACnet(GPIC)     ENG PAGE REF | GPIC Object Type | BACnet Object &
                            Instance | BACnet Object Name | LON Profile Name |
                            LON SNVT Type | N2 Metasys Address | MODBUS(Address|
                            Scale) | ENG Units(IMP[|SI]) | POINT LIST DESCRIPTION
                            | 1..10 | ENG PAGE REF(되풀이)
  ② E-Link/BACnet(Typ-Ins)   GPIC 열이 없고 'BACnet Object Typ/Ins' 한 칸에
                            타입+인스턴스('AV29')가 붙어 온다.
  ③ E-Link/YorkTalk          BACnet·LON·MODBUS 열이 **아예 없다**. ASCII PAGE REF ·
                            York Talk Point Type · ISN LINC Descriptive Text ·
                            York Talk Character Position · N2 Address 뿐이다.
                            (HryI9 처럼 ①②와 ③이 쪽 단위로 번갈아 나오는 문서가 있다)

이 계통이 실제로 밟은 함정 — 하나씩 방어한다
  1. **개정이력표와 포인트표가 한 그리드로 병합된다.** 블록 첫 쪽의 0행은
     'Item|Version|Rev|Date|YORK P N|Chksum|Baud|COMMENTS'(포인트가 아니라
     펌웨어 이력)이고 진짜 머리글은 r11~r14 어디쯤에 있다. 이어지는 쪽에서는
     0행이 정상 머리글이다 — **같은 문서 안에서 머리글 위치가 다르다.**
     → 0행을 머리글로 삼지 않는다. 표 안에서 앵커 낱말(ENG PAGE REF·ASCII PAGE
       REF·BACnet Object Typ/&·York Talk Point Type)을 담은 행을 찾아 쓴다.
  2. **머리글이 2~4줄 스택이다.** 1줄 열이름 / 2줄 'POINT LIST CODE: S=STANDARD…'
     / 3줄 하위열(Address|Scale|IMP|SI|POINT LIST DESCRIPTION|1..10) / 4줄
     'see notes 2,3'. → 스택을 세로로 이어 붙인 합성 머리글로 열을 판정한다.
  3. **POINT LIST DESCRIPTION 의 열 번호가 10 또는 11로 다르다** (ENG Units 가
     1열이냐 2열이냐에 따라). → 고정 인덱스 금지, 오직 합성 머리글 매칭.
  4. **③ YorkTalk 13건은 'GPIC Object Type' 열이 전 행 공란이다.** 열이 있다고
     매핑하면 타입이 전부 null 이 된다(point-schema rules.emptyMeansAbsent).
     타입은 'York Talk Point Type'(A./D./Code)에서 온다. ※ **'D. Control' 을
     빠뜨리면 기동·정지 명령 행이 통째로 사라진다.**
  5. **② Typ-Ins 의 'BACnet Object Name' 열에는 사람이 읽는 이름이 없다** —
     'YT2 S01 P35' 같은 York Talk 좌표다 → yorktalk.coord. 진짜 이름은
     'POINT LIST DESCRIPTION' 열이다. 값 모양(^YT\\d+ S\\d+ P\\d+$)으로도 한 번 더
     막는다 — 예전 '이름 자리에 벤더 코드'(59.5%→99.8%) 사고와 같은 유형이다.
  6. **밑줄이 별도 조각으로 떨어져 나온다.** '_ _ YT2 S01 P04' · '_ RET AIR.TEMP' ·
     '_ SNVT switch (95)'. 게이트보다 **아티팩트 제거를 먼저** 한다
     (point-schema rules.artifactCleanupFirst).
     ⚠ SNVT 이름은 밑줄이 **공백으로 바뀌어** 온다('SNVT count f (51)'). 공백을
     밑줄로 되돌리는 단순 치환은 금지 — 같은 쪽 get_text() 에 원형
     'SNVT_count_f' 가 있을 때만 복원하고, 없으면 이름을 만들지 않는다
     (번호 (51) 은 확실하므로 snvtIndex 만 남긴다).
  7. **이름이 빈 행은 예약 슬롯이다.** E-Link 는 P03~P84 를 쓰든 안 쓰든 통째로
     할당해 둔다. 실으면 목록이 2~3배 부풀고 BMS 매핑 화면이 정체불명 행으로
     덮인다. **판정 기준 열이 하위형마다 다르다**(point-schema 가 공통 규칙을
     포기하고 어댑터에 위임한 자리):
       GPIC    → BACnet Object Name 과 DESCRIPTION 이 **둘 다** 비면 예약
       Typ-Ins → DESCRIPTION 만으로 판정(좌표·nvName 은 빈 슬롯에도 자동 생성된다)
       YorkTalk→ ISN LINC 와 DESCRIPTION 이 **둘 다** 비면 예약
  8. **표 아래 NOTES 1~30 행이 포인트 행으로 잡힌다.** 'NOTES' 행을 만나면 그
     표는 거기서 끝난다 — 아래 숫자 행을 예약 슬롯으로 세면 통계가 거짓이 된다.
  9. **한 문서에 변형이 여러 개 들어 있다** (YR OptiView 1~4쪽 Standard Starter /
     5~8쪽 Solid State Starter — 주소가 다르다). 머리글이 0행이 아닌 표가
     나올 때마다 새 블록으로 끊고 제목을 provenance.block 에 남긴다 — 나중에
     모델을 나눌 근거다. ⚠ provenance.block 은 point-schema 미등재 필드다
     (사전 등재 필요). 지금은 근거를 잃지 않으려고 먼저 담아 둔다.
 10. **같은 폴더에 남이 맡은 계통이 섞여 있다.** 'Item Ref Num | BACnet Name |
     BACnet Object Instance …' 는 Native 계통이지 E-Link 가 아니다(3건). 앵커에
     걸리지 않으므로 자동으로 빠지지만, 조용히 빠지면 안 되니 세어서 보고한다.
 11. **머리글 칸 하나에 데이터가 배어 나오는 쪽이 있다** (7Lqu5 6쪽: 'York Talk
     Point Type' 자리에 'D. Monitor'). 스택 병합이 대개 되살리지만, 되살아났는지
     세어 두지 않으면 모른다 → skipped.headerGlitch.
 12. **머리글 자체가 데이터와 어긋난 쪽이 있다** (HryI9 2·4쪽). 머리글은
     'ASCII Page Ref | York Talk Point Type' 인데 값은 'AV29 | YT2 S01 P35' 로
     1·3쪽(Typ-Ins)과 같다 — 딴 계통 서식에서 복사된 머리글이다. 글자만 믿으면
     **BACnet 오브젝트가 ASCII 페이지 번호 자리에** 들어간다(57점). 값 모양이
     머리글과 다르면 값을 믿는다 — repair_header().
 13. **'MV1 /AV401' 처럼 한 오브젝트가 두 표기로 온다**(GPIC 7건 53점). 설정에
     따라 형태가 달라지는 것이라 둘째를 버리면 조용히 사라진다 → alternates.

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_elink.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_elink.py --parse <문서ID|파일경로>
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SOURCE = "jci-york-bas-points"


def docs():
    """이 파서가 훑을 문서 목록 — 정본은 대장(collected.json)이다.

    조사 단계에는 임시 폴더(data/raw/_probe_jci)를 훑었는데 그 폴더가 이 PC 에만
    있어 다른 곳에서 재현이 안 됐다. 등록 후에는 대장이 목록을 준다.
    """
    import collect
    return collect.files_of(SOURCE)
sys.path.insert(0, HERE)
import specs as SP      # noqa: E402
import schema as S      # noqa: E402

FAMILY_GPIC = "E-Link/BACnet(GPIC)"
FAMILY_TYPINS = "E-Link/BACnet(Typ-Ins)"
FAMILY_YT = "E-Link/YorkTalk"

# 표 안에서 머리글 행을 찾아내는 앵커. 0행을 머리글로 삼지 않기 위한 장치다.
#   'ENG PAGE'(REF 없음)는 코드표(SC.4 등) 머리글이라 일부러 걸리지 않게 뒀다.
ANCHOR = re.compile(r"ENG\s*PAGE\s*REF|ASCII\s*PAGE\s*REF"
                    r"|BACnet\s*Object\s*(Typ|&)|York\s*Talk\s*Point\s*Type", re.I)
# 다른 계통(Native)의 머리글 — E-Link 가 아니다. 세어서 보고만 한다
FOREIGN = re.compile(r"Item\s*Ref\s*Num|PANEL\s*DISPLAYED\s*NAME|^Long Name", re.I)
# 머리글 스택 2~4줄째임을 알아보는 낱말
SUBHEAD = re.compile(r"POINT\s*LIST|^Address$|^Scale$|^Imperial$|^Imp\.?$|^IMP$"
                     r"|^SI$|see\s*notes?|^([1-9]|10)$", re.I)
# 'NOTES' 행 — 여기서 표가 끝난다
NOTES_ROW = re.compile(r"^NOTES?\b", re.I)

# 합성 머리글 → 우리 열 이름. **순서가 곧 우선순위**다
#   GPIC 형과 Typ-Ins 형을 따로 두는 이유: 둘 다 '타입+인스턴스'를 담지만
#   어느 열이 있느냐가 곧 하위형 판정이라 합쳐 두면 family 를 못 정한다.
COLMAP = [
    # 'ENG BPAGE REF' · 'ENG L PAGE REF' — 원문 오타다(point-schema 도 이 오타를
    # 예로 든다). 되풀이되는 맨 끝 열이라 값은 안 잃지만, 못 알아본 열로 남으면
    # 진짜 미상 열과 구분이 안 된다 → 낱글자 하나를 허용해 흡수한다
    ("pageRef",   r"^ENG\s*[A-Z]?\s*PAGE\s*REF"),
    ("asciiRef",  r"^ASCII\s*PAGE\s*REF"),
    ("gpic",      r"GPIC\s*Object\s*Type"),
    ("bacObjInst", r"BACnet\s*Object\s*&\s*Instance"),
    ("bacTypIns", r"BACnet\s*Object\s*Typ"),
    # 쪽에 따라 'BACnet Object Name' 이 'BACnet Object' 로 잘려 나온다(gk4oF 2쪽).
    # 놓치면 그 쪽 23점의 오브젝트 이름이 통째로 사라진다 — 실측 50/73 → 73/73
    ("bacName",   r"^BACnet\s*Object\s*Name|^BACnet\s*Object$"),
    ("ytType",    r"York\s*Talk\s*Point\s*Type"),
    ("shortName", r"(ISN\s*LINC|PANEL)\s*Descriptive\s*Text"),
    ("charPos",   r"York\s*Talk\s*Character\s*Position"),
    ("lonName",   r"LON\s*Profile\s*Name"),
    ("snvt",      r"SNVT"),
    ("n2",        r"^N2\b"),
    ("mbAddress", r"MODBUS\s*Address|^MODBUS\s+Address|^Address\b"),
    ("mbScale",   r"^Scale\b|MODBUS.*Scale"),
    ("desc",      r"POINT\s*LIST\s*DESCRIPTION"),
    ("unitSI",    r"^SI\b"),
    ("unitIP",    r"(ENG|Engineering)\s*UNITS?|Imperial|^IMP\b|^Imp\.?$"),
]

# 'AV1' · 'BV125' · 'MV3' → (타입, 인스턴스)
OBJ = re.compile(r"^([A-Za-z]{2,4})\s*[.\-]?\s*(\d+)$")
# 'MV1 /AV401' — 한 오브젝트가 설정에 따라 두 형태로 나온다(GPIC 7건 53점).
# 첫째를 본체로 삼고 둘째는 alternates 로 남긴다 — 버리면 조용히 사라진다
# (SC-EQ 어댑터가 같은 표기를 실측 50건에서 먼저 만났다)
OBJ_ALT = re.compile(r"^([A-Za-z]{2,4}\s*\d+)\s*/\s*([A-Za-z]{2,4}\s*\d+)$")
# 'ADF 1' · 'BD 24' · 'ADI 10' → (종별, 주소)
N2 = re.compile(r"^([A-Z]{2,3})\s*(\d+)$")
# 'SNVT_temp_p (105)' — 밑줄이 공백으로 깨진 'SNVT count f (51)' 도 잡는다
SNVT = re.compile(r"(SNVT[A-Za-z0-9_ ]*?)\s*\((\d+)\)")
# 같은 쪽 원문 텍스트에서 건져 올릴 정상 SNVT 이름
SNVT_WORD = re.compile(r"SNVT_[A-Za-z0-9_]+")
# 'P03' — 이 계통의 행 키
PREF = re.compile(r"^P\s?\d{1,3}$", re.I)
# Typ-Ins 형 'BACnet Object Name' 열의 실체 — 이름이 아니라 York Talk 좌표
YTCOORD = re.compile(r"^YT\d+\s+S\d+\s+P\d+$", re.I)
# '8 - 11'(아날로그 구간) · '115'(디지털 단일 위치)
CHARPOS = re.compile(r"^(\d+)(?:\s*[-–]\s*(\d+))?$")

# York Talk 포인트 종별 — point-schema blocks.yorktalk.pointType 허용값 5종.
#   ⚠ 'D. Control'(기동·정지·부하 명령)을 빼면 13건 전부에서 명령 행이 사라진다
YT_TYPES = {"a. control": "A. Control", "a. monitor": "A. Monitor",
            "d. control": "D. Control", "d. monitor": "D. Monitor",
            "code monitor": "Code Monitor"}
# 종별 → common.pointKind (문서 원문이 아니라 규정된 파생)
YT_KIND = {"A. Control": "analog", "A. Monitor": "analog",
           "D. Control": "binary", "D. Monitor": "binary",
           "Code Monitor": "code"}
AVAIL_CODES = {"S", "O", "N"}


def clean(v):
    """조판 아티팩트를 지운다 — 게이트를 걸기 **전에** 해야 한다.

    표 인식이 밑줄 글리프를 별도 텍스트 조각으로 뱉어 '_ _ YT2 S01 P04' ·
    '_ RET AIR.TEMP' · '_ SNVT switch (95)' 처럼 온다. 앵커 정규식(^…$)을 그
    앞에 걸면 오염된 값이 그냥 통과해 최후 방어선이 무력해진다
    (point-schema rules.artifactCleanupFirst).

    ⚠ SNVT 셀의 **공백↔밑줄은 여기서 건드리지 않는다.** 'SNVT count f' 를
    기계적으로 'SNVT_count_f' 로 바꾸면 문서에 없는 이름을 지어내게 된다 —
    복원은 restore_snvt() 가 같은 쪽 원문과 대조해서만 한다.
    """
    t = SP._c(v)
    t = re.sub(r"^[_\s]+|[_\s]+$", "", t)
    return t.strip()


def merge_header(data, h, end):
    """머리글 스택(2~4줄)을 열마다 세로로 이어 붙여 합성 머리글을 만든다.

    'MODBUS' + 'Address' + 'see notes 2,3' → 'MODBUS Address see notes 2,3'.
    이렇게 해야 ENG Units 가 1열이든 2열이든 DESCRIPTION 열을 번호가 아니라
    이름으로 찾을 수 있다 (함정 3).
    """
    ncol = max(len(r) for r in data[h:end])
    out = []
    for i in range(ncol):
        parts = []
        for r in data[h:end]:
            v = clean(r[i]) if i < len(r) else ""
            if v and v not in parts:
                parts.append(v)
        out.append(" ".join(parts))
    return out


def find_header(data):
    """머리글 행 번호. 못 찾으면 None (0행을 머리글로 삼지 않는다 — 함정 1)."""
    for ri, r in enumerate(data[:26]):
        if ANCHOR.search(" | ".join(clean(c) for c in r)):
            return ri
    return None


def header_band(data, h):
    """머리글 스택이 끝나는 행 번호(제외). 첫 칸이 채워지면 데이터 시작이다."""
    end = h + 1
    while end < len(data) and end - h <= 4:
        r = data[end]
        if clean(r[0] if r else ""):
            break
        vals = [clean(c) for c in r if clean(c)]
        if not vals or not any(SUBHEAD.search(v) for v in vals):
            break
        end += 1
    return end


def header_map(head):
    """합성 머리글 → {우리이름: 열번호}. 못 알아본 열은 원문 이름 그대로 남긴다.

    되풀이되는 'ENG PAGE REF'(맨 끝 열)는 setdefault 로 첫 번째만 쓴다.
    1~10 형번 적용 열은 avail 아래 {번호: 열번호} 로 따로 모은다.
    """
    out, unknown = {}, {}
    avail = {}
    for i, h in enumerate(head):
        h = SP._c(h)
        if not h:
            continue
        if re.match(r"^([1-9]|10)$", h):
            avail[int(h)] = i
            continue
        # 머리글 칸에 그 열의 **값 어휘**가 배어 나온 쪽이 있다 (함정 11)
        if h.lower() in YT_TYPES:
            out.setdefault("ytType", i)
            continue
        for name, pat in COLMAP:
            if re.search(pat, h, re.I):
                out.setdefault(name, i)
                break
        else:
            unknown[h[:40]] = i
    if avail:
        out["avail"] = avail
    return out, unknown


def repair_header(cmap, sample):
    """머리글이 데이터와 어긋난 쪽을 **값 모양으로** 바로잡는다.

    실측(HryI9 2·4쪽): 머리글은 'Eng Page Ref | ASCII Page Ref | York Talk Point
    Type | …' 인데 그 아래 값은 'P35 | AV29 | YT2 S01 P35 | …' 로 1·3쪽(Typ-Ins)과
    똑같다. 원문 머리글이 딴 계통 서식에서 복사돼 온 것이다.
    머리글 글자만 믿으면 **BACnet 오브젝트 'AV29' 가 ASCII 페이지 번호 자리에,
    좌표 'YT2 S01 P35' 가 포인트 종별 자리에 들어간다** — 57점이 통째로 어긋난다.
    point-schema columnGuards 가 이 열을 두고 '값 모양으로 판정' 하라고 못 박은
    바로 그 자리다.

    증거 기준: BACnet 열이 없다고 판정된 표에서, ASCII 자리 값이 BACnet 오브젝트
    꼴이고 종별 자리 값이 York Talk 좌표 꼴인 행이 2행 이상이면 오기로 본다.
    """
    if "bacObjInst" in cmap or "bacTypIns" in cmap:
        return cmap, False
    if "asciiRef" not in cmap or "ytType" not in cmap:
        return cmap, False
    hits = 0
    for row in sample:
        a = clean(row[cmap["asciiRef"]]) if cmap["asciiRef"] < len(row) else ""
        y = clean(row[cmap["ytType"]]) if cmap["ytType"] < len(row) else ""
        m = OBJ.match(a)
        if m and S.TYPE_ALIAS.get(m.group(1).upper(),
                                  m.group(1).upper()) in S.BACNET_TYPES \
                and YTCOORD.match(y):
            hits += 1
    if hits < 2:
        return cmap, False
    cmap = dict(cmap)
    cmap["bacTypIns"] = cmap.pop("asciiRef")
    cmap["bacName"] = cmap.pop("ytType")
    return cmap, True


def family_of(cmap):
    if "bacObjInst" in cmap:
        return FAMILY_GPIC
    if "bacTypIns" in cmap:
        return FAMILY_TYPINS
    return FAMILY_YT


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계).

    쪽마다 표를 찾고, 표마다 머리글 행을 **직접 찾아** 판정한다. 머리글이 0행이
    아닌 표는 새 블록의 시작이다(그 위는 개정이력·제목) — 함정 1·9.
    """
    import fitz
    doc = fitz.open(path)
    rows, unknown_cols, head_seen = [], {}, None
    skipped = {"reserved": 0, "banner": 0, "band": 0, "notes": 0,
               "revision": 0, "headerGlitch": 0, "headerMislabeled": 0,
               "codeTable": 0, "foreign": 0}
    block = {"index": 0, "title": ""}
    for pi, pg in enumerate(doc):
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        words = set(SNVT_WORD.findall(pg.get_text()))
        for t in tabs:
            data = t.extract()
            if len(data) < 2:
                continue
            h = find_header(data)
            if h is None:
                flat = " | ".join(clean(c) for r in data[:3] for c in r)
                if FOREIGN.search(flat):
                    skipped["foreign"] += 1        # 남이 맡은 Native 계통 (함정 10)
                elif re.search(r"ENG\s*PAGE\b", flat, re.I):
                    skipped["codeTable"] += 1      # SC.4 등 상태 코드표
                continue
            end = header_band(data, h)
            head = merge_header(data, h, end)
            if FOREIGN.search(" | ".join(head)):
                skipped["foreign"] += 1
                continue
            cmap, unk = header_map(head)
            if "pageRef" not in cmap and "asciiRef" not in cmap:
                # SC-EQ('BACnet Object & Instance')처럼 앵커에는 걸리지만 ENG PAGE
                # REF 가 없는 표 = 남이 맡은 계통이다. 조용히 넘기지 않고 센다
                skipped["foreign"] += 1
                continue
            unknown_cols.update(unk)
            head_seen = head
            cmap, mislabeled = repair_header(cmap, data[end:end + 8])
            if mislabeled:
                skipped["headerMislabeled"] += 1
            fam = family_of(cmap)
            # 머리글 칸에 그 열의 값이 배어 나온 쪽 (함정 11). 스택 병합이
            # 대개 되살리지만, 되살아났는지 여부를 세어 두지 않으면 모른다
            if "ytType" in cmap and any(v in head[cmap["ytType"]]
                                        for v in YT_TYPES.values()):
                skipped["headerGlitch"] += 1
            # 머리글이 0행이 아니면 그 위는 제목·개정이력 = 새 블록의 시작
            if h > 0 or block["index"] == 0:
                block = {"index": block["index"] + 1,
                         "title": block_title(data, h)}
                skipped["revision"] += sum(
                    1 for r in data[:h] if len([c for c in r if clean(c)]) >= 2)
            ctx = {"block": dict(block), "group": "", "snvt": words,
                   "mislabeled": mislabeled}
            for ri, r in enumerate(data[end:], end):
                vals = [clean(c) for c in r]
                nz = [v for v in vals if v]
                if not nz:
                    continue
                if NOTES_ROW.match(vals[0] or "") and len(nz) <= 2:
                    skipped["notes"] += sum(
                        1 for r2 in data[ri + 1:]
                        if any(clean(c) for c in r2))
                    break                           # 표 끝 (함정 8)
                if ANCHOR.search(" | ".join(vals)):
                    skipped["banner"] += 1          # 표 안에 되풀이된 머리글
                    continue
                if len(nz) == 1 and vals[0] and not PREF.match(vals[0]):
                    ctx["group"] = vals[0]          # 'SECTION 2' 같은 구분 행
                    skipped["band"] += 1
                    continue
                rec, why = row_to_point(r, cmap, fam, os.path.basename(path),
                                        pi + 1, ctx)
                if rec:
                    rows.append(rec)
                elif why:
                    skipped[why] = skipped.get(why, 0) + 1
    doc.close()
    return rows, unknown_cols, head_seen, skipped


def block_title(data, h):
    """머리글 위에 있는 제목 행 — 'YT OptiView w/ Standard Starter …' · 'SECTION 2'."""
    for r in data[:h]:
        vals = [clean(c) for c in r if clean(c)]
        if not vals:
            continue
        if re.match(r"^Item$", vals[0], re.I):      # 개정이력표 머리글
            break
        if len(vals) <= 3 and len(vals[0]) > 2:
            return " ".join(vals)[:120]
    return ""


def restore_snvt(name, words):
    """깨진 SNVT 이름을 같은 쪽 원문과 대조해 복원한다 — 대조 실패면 만들지 않는다.

    표 인식이 'SNVT_count_f' 를 'SNVT count f' 로 뱉는 쪽이 있다. 공백을 밑줄로
    바꾸는 단순 치환은 문서에 없는 이름을 지어내는 짓이라 금지다
    (point-schema blocks.lon.snvtType). 같은 쪽 get_text() 에 원형이 실제로
    있을 때만 복원한다.
    """
    if "_" in name:
        return name
    cand = re.sub(r"\s+", "_", name)
    return cand if cand in words else None


def row_to_point(row, cmap, family, fname, page, ctx):
    def cell(key):
        i = cmap.get(key)
        return clean(row[i]) if i is not None and i < len(row) else ""

    page_ref = cell("pageRef")
    desc = cell("desc")
    short = cell("shortName")
    bac_name = cell("bacName")
    obj = cell("bacObjInst") or cell("bacTypIns")
    if not (page_ref or desc or short or obj):
        return None, None

    # ── 예약 슬롯: 이름 자리가 빈 행은 포인트가 아니다 (함정 7) ────────────
    #   기준 열이 하위형마다 다르다 — point-schema rules.reservedSlotNotAPoint 가
    #   공통 규칙을 포기하고 어댑터에 위임한 자리라 여기에 근거를 적어 둔다.
    if family == FAMILY_GPIC:
        named = bool(desc or bac_name)
    elif family == FAMILY_TYPINS:
        # 좌표(YT2 S01 P08)·nvName 은 빈 슬롯에도 자동 생성되므로 기준이 못 된다
        named = bool(desc)
    else:
        named = bool(desc or short)
    if not named:
        return None, "reserved"

    rec = {"common": {}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": family,
        "block": ctx["block"]}}
    raw, gaps = {}, []
    if ctx.get("mislabeled"):
        gaps.append("원문 머리글이 데이터와 어긋나 값 모양으로 열 재판정")

    # ── 이름 · 짧은 이름 ─────────────────────────────────────────────
    if desc:
        name, states = split_states(desc)
        if name:
            rec["common"]["name"] = name
            if len(name) > 120:
                gaps.append("이름 120자 초과 — 설명 문단이 눌러붙었는지 확인 필요")
        if states:
            rec["common"]["states"] = [{"code": c, "label": l} for c, l in states]
    if short:
        rec["common"]["shortName"] = short
    if ctx["group"]:
        rec["common"]["group"] = ctx["group"]

    # ── York Talk 좌표계 ─────────────────────────────────────────────
    yt = {}
    if page_ref:
        yt["pageRef"] = page_ref.replace(" ", "")
    ascii_ref = cell("asciiRef")
    if ascii_ref:
        yt["asciiPageRef"] = ascii_ref.replace(" ", "")
    ytt = cell("ytType")
    if ytt:
        canon = YT_TYPES.get(re.sub(r"\s+", " ", ytt).lower())
        if canon:
            yt["pointType"] = canon
            rec["common"]["pointKind"] = YT_KIND[canon]
        else:
            raw["York Talk Point Type"] = ytt
            gaps.append("York Talk 종별 허용값 밖(%r)" % ytt)
    cp = cell("charPos")
    if cp:
        m = CHARPOS.match(cp)
        if m:
            a = int(m.group(1))
            yt["charPos"] = {"start": a, "end": int(m.group(2) or a)}
        else:
            raw["York Talk Character Position"] = cp

    # ── BACnet: 'AV1' → 타입 + 인스턴스 ──────────────────────────────
    alt = None
    if obj:
        ma = OBJ_ALT.match(obj)
        if ma:
            obj, alt = ma.group(1).replace(" ", ""), ma.group(2).replace(" ", "")
        m = OBJ.match(obj)
        if m:
            ty = m.group(1).upper()
            canon = S.TYPE_ALIAS.get(ty, ty)
            if canon in S.BACNET_TYPES:
                rec["blocks"].setdefault("bacnet", {})["objectType"] = canon
                rec["blocks"]["bacnet"]["instance"] = int(m.group(2))
                if canon != ty:
                    raw["BACnet Object & Instance"] = obj
                if alt:
                    rec["blocks"]["bacnet"]["alternates"] = [alt]
                    raw["BACnet Object & Instance"] = "%s /%s" % (obj, alt)
            else:
                raw["BACnet Object & Instance"] = obj
                gaps.append("BACnet 타입 미상(%r)" % ty)
        else:
            raw["BACnet Object & Instance"] = obj
            gaps.append("BACnet 오브젝트 표기 해석 불가(%r)" % obj)
    # 'BACnet Object Name' 열 — GPIC 형만 진짜 이름이다 (함정 5).
    #   값 모양으로 한 번 더 막는다: YT 좌표가 오면 무조건 yorktalk.coord 로.
    if bac_name:
        if YTCOORD.match(bac_name):
            yt["coord"] = re.sub(r"\s+", " ", bac_name).upper()
        elif family == FAMILY_TYPINS:
            raw["BACnet Object Name"] = bac_name
            gaps.append("Typ-Ins 이름 열이 좌표 꼴이 아니다(%r)" % bac_name[:40])
        else:
            rec["blocks"].setdefault("bacnet", {})["objectName"] = bac_name
            rec["common"].setdefault("name", bac_name)

    # ── N2: 'ADF 1' → 종별 + 주소 ────────────────────────────────────
    n2 = cell("n2")
    if n2:
        m = N2.match(n2)
        if m:
            rec["blocks"].setdefault("n2", {})["pointType"] = m.group(1)
            rec["blocks"]["n2"]["address"] = int(m.group(2))
        else:
            raw["N2 Address"] = n2

    # ── Modbus ──────────────────────────────────────────────────────
    mb = {}
    a = cell("mbAddress")
    if a and re.match(r"^\d+$", a):
        mb["address"] = int(a)
        mb["addressBase"] = "unknown"       # 0/1-base 를 문서가 밝히지 않는다
        if a.lstrip("0") != a:
            raw["MODBUS Address"] = a       # '0001' 원표기 보존
    elif a:
        raw["MODBUS Address"] = a
    sc = cell("mbScale")
    if sc:
        mb["scaleRaw"] = sc                 # 곱/나눗 방향 확정 전이라 수치화 보류
        if "*" in sc:
            mb["scaleUserConfigurable"] = True   # NOTES 의 '*' = 현장 설정 가능
    if mb:
        rec["blocks"]["modbus"] = mb

    # ── LON ─────────────────────────────────────────────────────────
    nv = cell("lonName")
    if nv and nv.lower() not in ("none", "n/a", "-", "—"):
        rec["blocks"].setdefault("lon", {})["nvName"] = nv
        low = nv.lower()
        for pre in ("nvi", "nvo", "nci"):
            if low.startswith(pre):
                rec["blocks"]["lon"]["direction"] = pre
                break
    sv = cell("snvt")
    if sv and sv.lower() not in ("none", "n/a", "-", "—"):
        # 표준 번호가 없는 쪽이 있다('SNVT_temp_p' 만) — 번호가 없다고 이름까지
        # 버리면 LON 매핑이 통째로 빈다. 번호와 이름을 따로 다룬다
        m = SNVT.search(sv)
        part = (m.group(1) if m else sv).strip()
        nm = restore_snvt(part, ctx["snvt"]) if part.upper().startswith("SNVT") else None
        if nm:
            rec["blocks"].setdefault("lon", {})["snvtType"] = nm
        else:
            raw["LON SNVT Type"] = sv
            gaps.append("SNVT 이름 밑줄 복원 실패 — 번호만 신뢰"
                        if m else "SNVT 표기 해석 불가")
        if m:
            rec["blocks"].setdefault("lon", {})["snvtIndex"] = int(m.group(2))

    # ── E-Link 게이트웨이 내부 오브젝트 ──────────────────────────────
    #   ⚠ YorkTalk 13건은 이 열이 전 행 공란이다 — 값이 있을 때만 만든다
    gp = cell("gpic")
    if gp:
        rec["blocks"].setdefault("elink", {})["gpicType"] = gp

    # ── 단위 ────────────────────────────────────────────────────────
    for key, field in (("unitIP", "IP"), ("unitSI", "SI")):
        u = cell(key)
        if not u or u in S.NO_UNIT:
            continue
        rec["common"]["unit%sRaw" % field] = u
        c = S.canon_unit(deg_fix(u))
        if c:
            rec["common"]["unit" + field] = c

    # ── 1~10 형번 적용표 (S=표준 O=옵션 N=해당없음) ───────────────────
    #   ⚠ 포인트 값이 아니다. 번호↔형번 대응표는 문서에 없다(별도 문서) —
    #     대응을 모르므로 raw 로만 남기고 형번 배정은 하지 않는다
    av = {}
    for n, i in sorted((cmap.get("avail") or {}).items()):
        v = clean(row[i]) if i < len(row) else ""
        if v:
            av[n] = v
    if av:
        rec["common"]["availability"] = {
            "raw": ",".join("%d=%s" % (n, v) for n, v in sorted(av.items()))}
        vals = set(av.values())
        if len(vals) == 1 and next(iter(vals)) in AVAIL_CODES:
            rec["common"]["availability"]["code"] = next(iter(vals))
        if len(av) == 1:
            rec["common"]["availability"]["column"] = next(iter(av))

    if yt:
        rec["blocks"]["yorktalk"] = yt
    if raw:
        rec["provenance"]["sourceColumns"] = raw
    if gaps:
        rec["provenance"]["gaps"] = gaps
    for k in ("common", "blocks"):
        if not rec[k]:
            del rec[k]
    return rec, None


def deg_fix(u):
    """'F°'·'C°' → '°F'·'°C'. 어휘 차이가 아니라 도(°) 글리프 위치 문제다."""
    return re.sub(r"^([FC])\s*°$", r"°\1", u)


STATE = re.compile(r"(-?\d+)\s*[=\-:]\s*([^,;0-9][^,;\]\)]*)")
# 이름 꼬리의 '(0=Off, 1=On)' · '[0=Stop, 1=Run]'
TAIL = re.compile(r"\s*[\(\[]([^\(\[\]\)]*=[^\(\[\]\)]*)[\)\]]\s*$")


def split_states(text):
    """'Mode (0=Vent, 1=Heating)' → ('Mode', [('0','Vent'), ('1','Heating')]).

    상태 의미가 이름에 눌러붙어 오는 것이 이 계통의 기본이다. 떼지 않으면
    이름이 설명 문단이 되고 상태 열거는 어디에도 안 남는다
    (point-schema common.name). 2개 미만이면 손대지 않는다 — '(0-4)' 같은
    범위 표기를 상태로 오인하지 않기 위해서다.
    """
    m = TAIL.search(text)
    if not m:
        return text, []
    got = read_states(m.group(1))
    if not got:
        return text, []
    return text[:m.start()].strip(" .,;-"), got


def read_states(text):
    got = []
    for code, label in STATE.findall(text or ""):
        label = label.strip(" .,;·")
        if label:
            got.append((code, label[:80]))
    return got if len(got) >= 2 else []


def main(argv):
    ap = argparse.ArgumentParser(description="JCI E-Link 계통 어댑터")
    ap.add_argument("--scan", action="store_true", help="계통 전체 파싱 통계")
    ap.add_argument("--parse", help="문서 하나 (파일경로 또는 ID 앞자리)")
    ap.add_argument("--limit", type=int, default=6, help="--parse 시 보여줄 행 수")
    a = ap.parse_args(argv)

    if a.parse:
        cands = ([a.parse] if os.path.exists(a.parse)
                 else [p for p in docs() if a.parse.lower() in os.path.basename(p).lower()])
        if not cands:
            print("파일을 못 찾겠다: %s" % a.parse)
            return 1
        rows, unk, head, skip = parse_doc(cands[0])
        print("%s — 포인트 %d" % (os.path.basename(cands[0]), len(rows)))
        if head:
            print("머리글: %s" % " | ".join(h[:24] for h in head if h))
        if unk:
            print("못 알아본 열: %s" % ", ".join(unk))
        print("뺀 행: %s" % ", ".join("%s %d" % (k, v)
                                      for k, v in skip.items() if v))
        for r in rows[:a.limit]:
            print("\n" + json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    if a.scan:
        from collections import Counter
        tot, fams, allunk, allskip = Counter(), Counter(), Counter(), Counter()
        files = docs()
        hit = 0
        for f in files:
            rows, unk, head, skip = parse_doc(f)
            for k, v in skip.items():
                allskip[k] += v
            if not rows:
                continue
            hit += 1
            here = Counter(r["provenance"]["family"] for r in rows)
            fams.update(here)
            for u in unk:
                allunk[u] += 1
            blocks = len({(r["provenance"]["family"],
                           r["provenance"]["block"]["index"]) for r in rows})
            for r in rows:
                for blk, fields in (r.get("blocks") or {}).items():
                    for k in fields:
                        tot["  %s.%s" % (blk, k)] += 1
                for k in (r.get("common") or {}):
                    tot["  " + k] += 1
                if (r.get("provenance") or {}).get("gaps"):
                    tot["  (gaps)"] += 1
            print("  %-26s %5d점  블록 %d  %s"
                  % (os.path.basename(f)[:24], len(rows), blocks,
                     " + ".join("%s %d" % (k.split("/")[-1], v)
                                for k, v in here.most_common())))
        print("\n문서 %d건에서 파싱 · 포인트 %d점" % (hit, sum(fams.values())))
        for k, v in fams.most_common():
            print("   %-26s %6d" % (k, v))
        print("\n채워진 자리")
        for k, v in tot.most_common():
            print("   %-26s %6d" % (k, v))
        print("\n뺀 행 (포인트로 싣지 않은 것)")
        for k, v in allskip.most_common():
            print("   %-26s %6d" % (k, v))
        if allunk:
            print("\n못 알아본 열 (문서 수)")
            for k, v in allunk.most_common(20):
                print("   %-44s %d" % (k[:44], v))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
