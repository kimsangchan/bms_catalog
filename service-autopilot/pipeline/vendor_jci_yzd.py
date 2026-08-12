# -*- coding: utf-8 -*-
"""JCI YZD-Logix 계통 포인트 리스트 → point-schema 구조.

계통이 무엇인가
  York YZD 원심 냉동기(OptiView 제어반 + PLC 시퀀싱 패널)의 BAS 프로토콜 목록
  ('YZD BAS Protocol List Rev 1.4', 문서 1건 · 11쪽). 조사한 JCI 8계통 중
  **유일하게 Allen-Bradley ControlLogix PLC 태그를 함께 싣는다** — 냉동기 제어반이
  Logix PLC 이고 Modbus 게이트웨이가 그 태그를 레지스터에 실어 내보내는 구조다.
  그래서 이 계통만 5번째 프로토콜 축(blocks.logix)이 생긴다.

  표는 앞 4쪽뿐이고 뒤 7쪽(5~11)은 상태 코드표 SC.1~SC.14 다 — 2열짜리 별표이며
  포인트가 아니다. 'Logix Tag' 머리글이 있는 표만 취한다.

머리글 9열
  Modbus | BACnet | Count | Logix Tag | Description | Enum Set | IP Units | SI Units
  | Modbus Scale

★ 함정 1 — **'BACnet' 열은 BACnet 오브젝트가 아니다** (가장 위험하다)
  실측: 40001 → 'BO0001' 인데 실제로는 °F 아날로그 **설정값**(Deg F · x10 배율),
        00001 → 'AO0001' 인데 실제로는 0/1 **기동 명령**,
        40009 → 'BI0009' 인데 0/1 상태값.
  접두 두 글자가 BACnet 타입이 아니라 (4xxxx→B / 0xxxx→A) × (쓰기→O / 읽기→I)
  인코딩이다. 범용 타입 파서(schema.canon_type)에 태우면 온도 설정값이
  Binary Output 으로 박힌다. point-schema columnGuards 가 이것을 **검증 오류**로
  못박아 두었다: "YZD-Logix 계통 문서에서 bacnet 블록이 생성되면 검증 오류".
  → 이 어댑터는 bacnet 블록을 **절대** 만들지 않는다. 원문은
    provenance.sourceColumns['BACnet'] 에 그대로 두고, 해석 가능한 것만
    modbus.refClass(레지스터 대역에서) · common.readWrite(O/I 또는 밴드에서) 로 뺀다.
  같은 열이 문서 안에서 **중복·역행**한다는 증거도 있다 — 'BI0049'·'BI0050' 이
  Count 48·49 와 64·65 와 80·81 과 96·97 에 네 번씩 재사용된다(실측 12행).
  진짜 오브젝트 인스턴스라면 있을 수 없는 일이라, 승격 금지의 방증이다.

★ 함정 2 — 밴드 행(구역 제목)이 포인트 행 사이에 섞인다
  'Setpoint write data' · 'Digital write data' · 'System 1 OptiView read data' ·
  'System 2 OptiView data' 4개. 첫 칸만 차 있고 나머지 8칸이 빈 행이라 포인트가
  아니다. 그런데 **아래 행들의 읽기/쓰기와 그룹을 정하는 유일한 출처**라
  버리면 안 된다 — 상태로 물고 내려가며 common.group · common.readWrite 에 준다.
  밴드는 쪽을 넘어 이어진다(1쪽 'System 1 …read' 가 2쪽 전체를 덮고, 3쪽
  'System 2 …' 가 4쪽을 덮는다) — 쪽마다 초기화하면 2·4쪽 107점의 그룹이 날아간다.
  ⚠ 'System 2 OptiView data' 에는 원문에 read/write 낱말이 **없다**(get_text 로 확인).
    지어내지 않고 BACnet 인코딩의 I/O 로 보충한다.

★ 함정 3 — 예약 슬롯
  Logix Tag 가 'Reserved' 이고 Description 이 빈 행이 216행 중 **60행(28%)**이다.
  주소(40014·40016·40019…)는 이어지는데 쓰이지 않는 자리다. 실으면 목록이 38%
  부풀고 BMS 매핑 화면에 정체 불명 행이 대량으로 뜬다. 뺀 수는 세어 돌려준다.
  ⚠ 다른 계통(E-Link)은 이름 칸이 '빈칸'이지만 여기는 **'Reserved' 라고 적혀 있다** —
    "이름 열이 비었나"로만 판정하면 60행이 전부 통과한다.

★ 함정 4 — 밑줄 아티팩트
  표 인식이 밑줄 글리프를 별도 조각으로 뱉어 원문 'SP_RemLeavingChilledSP' 가
  'SP RemLeavingChilledSP _' 로 온다(밑줄이 공백이 되고 끝에 '_' 하나가 붙는다).
  Logix 태그는 PLC 에 그대로 써야 하는 문자열이라 이걸 그냥 저장하면 못 쓴다.
  게이트보다 먼저 지우고(rules.artifactCleanupFirst), 복원은 **get_text() 대조**로
  한다 — 밑줄을 기계적으로 되돌리면 진짜 공백이 든 태그('COMPR MOTOR RUN')가 깨진다.

그 밖에 문서가 준 것 / 안 주는 것
  · 'Count' 는 레지스터 개수가 아니라 순번이다(= BACnet 인코딩 숫자 − 1).
    provenance.srcRef 로만 두고 검증에 쓴다 — 어긋나는 12행이 함정 1의 증거다.
  · 단위 표기에 오타가 있다: 'Votls'(Volts) · 'N/a'. 고쳐 넣지 않고 unitIPRaw 로
    보존하고 gaps 에 적는다. 'Deg F (Diff)'·'PSIA'·'PSID'·'kPaD' 는 정규 단위표에
    없어(차온·절대압) 역시 원표기만 남는다.
  · Modbus 주소는 5자리 Modicon 표기(40001·00001)다. 앞자리는 주소가 아니라
    **대역**이므로 modbus.refClass 로 빼고(4xxxx→holding · 0xxxx→coil) 주소는
    뒷 4자리만 쓴다. 통째로 정수화하면 '40001'→40001 인데 '00001'→1 이 되어
    같은 표기가 대역에 따라 다르게 정규화된다. 원표기는 sourceColumns 에 남는다.
    ⚠ 이 문서는 0-base/1-base 를 밝히지 않는다 → addressBase 는 'unknown' 이다.
      Modicon 관례로는 40001 이 첫 홀딩 레지스터라 1-base 지만, 그건 문서가
      아니라 관례가 하는 말이라 여기서 확정하지 않는다(틀리면 전 레지스터가
      한 칸씩 어긋난다).
  · 배율 어휘는 'x10'·'x1'·'x 10'·'N/A' 뿐이다. 곱/나눗 방향을 문서가 확정하지
    않으므로 scaleRaw 만 채우고 modbus.scale(수치)은 비운다(columnGuards).
  · 상태 코드표 참조('See SC.1 on Status Codes Tab')는 statesRef 에 'SC.1' 로 남긴다.
    5~11쪽의 SC.1~SC.14 표는 부속표라 포인트로 세지 않는다 — --scan 이 몇 표
    몇 코드인지만 보고한다(나중에 states 로 푸는 건 별도 패스).

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_yzd.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_yzd.py --parse <문서ID|파일경로>
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

FAMILY_YZD = "YZD-Logix"

# 머리글 낱말 → 우리 열 이름.
#   'Modbus' 와 'Modbus Scale' 은 앞자리가 같다 — 앵커(^Modbus$)로 갈라야 한다.
#   순서를 바꾸면 주소 열이 배율 열로 먹힌다.
COLMAP = [
    ("mbRef",     r"^Modbus$"),
    ("mbScale",   r"^Modbus Scale"),
    ("bacRaw",    r"^BACnet"),          # ⚠ BACnet 이 아니다 — 승격 금지(함정 1)
    ("count",     r"^Count$"),
    ("logix",     r"^Logix Tag"),
    ("desc",      r"^Description"),
    ("enumSet",   r"^Enum Set"),
    ("ipUnits",   r"^IP Units"),
    ("siUnits",   r"^SI Units"),
]

# '40001' · '00001' — 5자리 Modicon 표기. 앞자리가 레지스터 대역이다
MB_REF = re.compile(r"^([0134])(\d{4})$")
REF_CLASS = {"0": "coil", "1": "discrete-input",
             "3": "input-register", "4": "holding-register"}

# 'BO0001' · 'AO0001' · 'BI0049' — BACnet 처럼 생겼지만 아니다(함정 1).
#   앞글자 = 레지스터 대역(4xxxx→B / 0xxxx→A), 뒷글자 = 방향(O 쓰기 / I 읽기)
BAC_ENC = re.compile(r"^([AB])([IO])(\d+)$", re.I)
ENC_RW = {"I": "R", "O": "W"}

# '0=Off, 1=On' · '1 = Standard 2 = Enhanced' · '0=Local 1=BAS 2=Analog …'
#   구분자가 쉼표일 때도 있고 줄바꿈(→ 공백)일 때도 있다. 다음 '숫자=' 직전까지를
#   라벨로 끊는다 — 탐욕 매칭을 두면 '0=Local' 하나가 뒷 항목을 통째로 삼킨다.
STATE = re.compile(r"(-?\d+)\s*[=:\-]\s*(.+?)(?=\s*[,;]|\s+-?\d+\s*[=:\-]|$)")
# 이름 끝에 붙은 상태 열거: 'Motor Run [0=Off, 1=On]' · '… (0=Stop, 1=Run)'
INLINE = re.compile(r"\s*[\[(]([^\]\)]*\d+\s*[=\-][^\]\)]*)[\])]\s*$")
# 'See SC.1 on Status Codes Tab' — 표 인식이 폭에 맞춰 잘라 'Codes T' 로도 온다
SCREF = re.compile(r"\bSC\.(\d+)\b", re.I)


def clean(v):
    """조판 아티팩트를 지운다 — 게이트를 걸기 **전에** 해야 한다.

    표 인식이 밑줄 글리프를 별도 조각으로 뱉어 'SP RemLeavingChilledSP _' 처럼
    끝에 '_' 가 붙어 온다. 앵커 정규식을 그 앞에 걸면 오염된 값이 그냥 통과해
    최후 방어선이 무력해진다 (point-schema rules.artifactCleanupFirst).
    밑줄을 공백으로 되돌리는 일은 여기서 하지 않는다 — 진짜 공백이 든 태그
    ('COMPR MOTOR RUN')와 구별할 수 없어서 restore_tag() 가 원문 대조로 판정한다.
    """
    t = SP._c(v)
    return re.sub(r"^[_\s]+|[_\s]+$", "", t).strip()


def scrambled(h, target):
    """글자 순서가 뒤섞인 머리글인가 — 글자 집합으로 알아본다.

    조판에 따라 표 인식이 글자 조각 순서를 뒤집는 쪽이 있다(SC-EQ 계통 실측:
    'Enum Set' → '0EnuUmnd Sefeinted'). 이 계통에서 그 열을 놓치면 상태 열거가,
    'Logix Tag' 를 놓치면 **이 계통에만 있는 5번째 프로토콜 축이 통째로** 빠진다.
    위치로 때우면 다른 쪽에서 깨지므로 글자 집합이 같은지로 판정한다.
    """
    a = re.sub(r"[^a-z]", "", (h or "").lower())
    b = re.sub(r"[^a-z]", "", target.lower())
    if not a or len(a) < len(b):
        return False
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    if sum((cb - ca).values()):                 # target 글자가 하나라도 빠지면 아니다
        return False
    if len(a) > len(b) * 3:                     # 다른 열까지 삼킨 조각은 보류
        return False
    for other in ("modbus", "bacnet", "count", "logixtag", "description",
                  "enumset", "ipunits", "siunits", "modbusscale"):
        if not sum((Counter(other) - ca).values()) and len(other) > len(b):
            return False                        # 더 긴 다른 열과도 맞으면 판정 보류
    return True


def header_map(head):
    """머리글 → {우리이름: 열번호}. 못 알아본 열은 원문 이름 그대로 남긴다."""
    out, unknown = {}, {}
    for i, h in enumerate(head):
        h = SP._c(h)
        if not h:
            continue
        for name, pat in COLMAP:
            if re.search(pat, h, re.I):
                out.setdefault(name, i)
                break
        else:
            for name, label in (("enumSet", "Enum Set"), ("logix", "Logix Tag")):
                if name not in out and scrambled(h, label):
                    out[name] = i
                    break
            else:
                unknown[h[:40]] = i
    return out, unknown


def underscore_map(page):
    """밑줄이 든 원문 낱말 색인 — 'spremleavingchilledsp' → 'SP_RemLeavingChilledSP'.

    표 인식은 밑줄을 잃지만 get_text() 는 온전히 준다. 두 경로를 대조해 복원한다
    (point-schema blocks.logix.tag: "get_text() 대조로 판정").
    """
    out = {}
    for tok in re.split(r"\s+", page.get_text()):
        if "_" in tok:
            out[re.sub(r"[^0-9a-z]", "", tok.lower())] = tok.strip()
    return out


def restore_tag(tag, umap):
    """표에서 깨진 Logix 태그를 원문 표기로 되돌린다. 못 찾으면 건드리지 않는다."""
    if not tag:
        return tag, False
    key = re.sub(r"[^0-9a-z]", "", tag.lower())
    real = umap.get(key)
    if real and real != tag:
        return real, True
    return tag, False


def is_band(cells):
    """구역 제목 행인가 — 첫 칸만 차 있고 나머지가 전부 빈 행."""
    return bool(cells and cells[0]) and not any(cells[1:])


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계).

    밴드(구역 제목)는 쪽을 넘어 이어지므로 문서 단위 상태로 물고 내려간다.
    """
    import fitz
    doc = fitz.open(path)
    rows, unknown_cols, head_seen = [], {}, None
    skipped = {"reserved": 0, "band": 0, "banner": 0}
    band = ""
    for pi, pg in enumerate(doc):
        # 1,000쪽짜리 문서까지 표 인식을 돌리면 --scan 이 몇 분씩 걸린다.
        # 'Logix Tag' 머리글이 있는 표는 그 쪽 본문에도 반드시 그 글자가 있다.
        try:
            txt = pg.get_text()
        except Exception:
            continue
        if "Logix Tag" not in txt:
            continue
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        umap = underscore_map(pg)
        for t in tabs:
            data = t.extract()
            if len(data) < 2:
                continue
            head = [SP._c(c) for c in data[0]]
            # 5~11쪽 상태 코드표(2열)는 포인트 표가 아니다 — 머리글로 갈린다
            if not re.search(r"Logix Tag", " ".join(head), re.I):
                continue
            cmap, unk = header_map(head)
            unknown_cols.update(unk)
            head_seen = head
            for r in data[1:]:
                cells = [clean(c) for c in r]
                if is_band(cells):
                    band = cells[0]
                    skipped["band"] += 1
                    continue
                rec, why = row_to_point(r, cmap, band, os.path.basename(path),
                                        pi + 1, umap)
                if rec:
                    rows.append(rec)
                elif why:
                    skipped[why] = skipped.get(why, 0) + 1
    doc.close()
    return rows, unknown_cols, head_seen, skipped


def band_rw(band):
    """밴드 제목에서 읽기/쓰기를 읽는다. 낱말이 없으면 지어내지 않는다."""
    b = (band or "").lower()
    if re.search(r"\bwrite\b", b):
        return "W"
    if re.search(r"\bread\b", b):
        return "R"
    return None


def row_to_point(row, cmap, band, fname, page, umap):
    def cell(key):
        i = cmap.get(key)
        return clean(row[i]) if i is not None and i < len(row) else ""

    mb_ref = cell("mbRef")
    bac_raw = cell("bacRaw")
    tag = cell("logix")
    desc = cell("desc")
    if not (mb_ref or bac_raw or tag or desc):
        return None, None
    # 표 안에 되풀이되는 머리글 행은 포인트가 아니다
    if mb_ref.lower() == "modbus" or tag.lower() == "logix tag":
        return None, "banner"
    # ⚠ **예약 슬롯은 포인트가 아니다** (point-schema rules.reservedSlotNotAPoint).
    #   이 계통은 빈칸이 아니라 태그 자리에 'Reserved' 라고 **적어 둔다** — 실측
    #   216행 중 60행(28%). 주소는 이어지지만 제조사가 아직 안 쓰는 자리다.
    if not desc and (not tag or tag.lower().startswith("reserved")):
        return None, "reserved"

    rec = {"common": {}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": FAMILY_YZD}}
    raw, gaps = {}, []

    # ── 이름 · 상태 ──────────────────────────────────────────────────
    #   'Motor Run [0=Off, 1=On]' → 이름 'Motor Run' + states. 붙여 두면
    #   BMS 매핑 화면의 이름이 상태 문구까지 달고 다닌다(point-schema common.name)
    name, states = desc, []
    m = INLINE.search(desc)
    if m:
        got = read_states(m.group(1))
        if got:
            states = got
            name = desc[:m.start()].strip(" .,;-")
    if name:
        rec["common"]["name"] = name

    es = cell("enumSet")
    if es:
        ref = SCREF.search(es)
        got = read_states(es)
        if ref:
            # 표 인식이 열 폭에 맞춰 잘라 같은 참조가 'Status Codes T'(1·2쪽) 와
            # 'Status Codes Tab'(4쪽) 두 표기로 온다 — 잘림도 조판 아티팩트다.
            # 코드표를 찾는 데 쓰이는 건 'SC.n' 하나뿐이라 그것만 남기고
            # 원문 셀은 sourceColumns 에 그대로 둔다.
            rec["common"]["statesRef"] = "SC.%s" % ref.group(1)
            raw["Enum Set"] = es
        elif got:
            states = got                        # 열거가 더 완전하면 이쪽을 쓴다
        else:
            raw["Enum Set"] = es                # '0/1' — 라벨이 없어 states 가 못 된다
    if states:
        rec["common"]["states"] = [{"code": c, "label": l} for c, l in states]

    # ── Logix 태그: 이 계통만 갖는 5번째 프로토콜 축 ───────────────────
    if tag:
        real, fixed = restore_tag(tag, umap)
        rec["blocks"]["logix"] = {"tag": real}
        if fixed:
            raw["Logix Tag"] = tag              # 표 인식이 뱉은 깨진 표기 보존

    # ── Modbus: 5자리 Modicon 표기 → 주소 + 대역 ──────────────────────
    mb = {}
    if mb_ref:
        raw["Modbus"] = mb_ref                  # 원표기 보존(point-schema)
        m = MB_REF.match(mb_ref)
        if m:
            # 앞자리는 주소가 아니라 대역이다 → refClass 로 빼고 주소는 뒷 4자리.
            # 통째로 정수화하면 '40001'→40001 인데 '00001'→1 이 되어 같은 표기가
            # 대역에 따라 다르게 정규화된다. 대역은 refClass 가 말하게 한다.
            mb["refClass"] = REF_CLASS[m.group(1)]
            mb["address"] = int(m.group(2))
            mb["addressBase"] = "unknown"       # 문서가 0/1-base 를 안 밝힌다
        elif re.match(r"^\d+$", mb_ref):
            mb["address"] = int(mb_ref)
            mb["addressBase"] = "unknown"
            gaps.append("Modbus 5자리 Modicon 표기가 아니다(%r) — 대역 판정 불가"
                        % mb_ref)
        else:
            gaps.append("Modbus 주소 표기 해석 불가(%r)" % mb_ref)
    sc = cell("mbScale")
    if sc and sc.upper() not in ("N/A", "-", "—"):
        mb["scaleRaw"] = sc                     # 방향(곱/나눗) 미확정 → 수치화 보류
    elif sc:
        raw["Modbus Scale"] = sc                # 'N/A' = 배율 없음. 값이 아니라 보존만
    if mb:
        rec["blocks"]["modbus"] = mb

    # ── 'BACnet' 열: **승격 금지**. 방향 글자만 읽고 원문은 그대로 둔다 ──
    #   point-schema columnGuards: "YZD-Logix 계통 문서에서 bacnet 블록이
    #   생성되면 검증 오류". 여기서 blocks['bacnet'] 을 만드는 코드는 없다.
    enc_rw = None
    if bac_raw:
        raw["BACnet"] = bac_raw
        me = BAC_ENC.match(bac_raw)
        if me:
            enc_rw = ENC_RW[me.group(2).upper()]
        else:
            gaps.append("BACnet 열 인코딩 해석 불가(%r)" % bac_raw)

    # ── 읽기/쓰기 · 그룹: 밴드 행에서 물려받는다 ───────────────────────
    if band:
        rec["common"]["group"] = band
    rw = band_rw(band)
    if rw and enc_rw and rw != enc_rw:
        gaps.append("밴드(%s)와 BACnet 열 방향(%s)이 어긋난다" % (rw, enc_rw))
    if rw:
        rec["common"]["readWrite"] = rw
    elif enc_rw:
        rec["common"]["readWrite"] = enc_rw      # 밴드에 read/write 낱말이 없는 구역
    else:
        gaps.append("readWrite")

    # ── 단위: 정규화되면 unitIP/SI, 원표기는 언제나 …Raw ─────────────────
    for key, field, raw_field in (("ipUnits", "unitIP", "unitIPRaw"),
                                  ("siUnits", "unitSI", "unitSIRaw")):
        u = cell(key)
        if not u or u.upper() in ("N/A", "-", "—", "NONE"):
            continue                            # rules.emptyMeansAbsent
        rec["common"][raw_field] = u
        canon = S.canon_unit(u)
        if canon:
            rec["common"][field] = canon
        else:
            gaps.append("%s 정규화 불가(%r)" % (field, u))

    # ── Count: 레지스터 개수가 아니라 순번이다 → 검증용 ────────────────
    cnt = cell("count")
    if cnt:
        rec["provenance"]["srcRef"] = cnt
        raw["Count"] = cnt
        m2 = BAC_ENC.match(bac_raw or "")
        if m2 and re.match(r"^\d+$", cnt) and int(m2.group(3)) - 1 != int(cnt):
            # 함정 1의 방증 — 'BI0049' 가 Count 48·64·80·96 에 네 번 재사용된다
            gaps.append("Count(%s)와 BACnet 열 번호(%s)가 어긋난다"
                        % (cnt, m2.group(3)))

    # ── 포인트 종별(파생): 이 계통은 오브젝트 타입 열이 없다 ────────────
    #   근거 없는 판정 금지(point-schema common.pointKind) — 아래 셋만 인정한다
    kind = None
    if rec["common"].get("statesRef"):
        kind = "code"                            # 상태 코드표 참조
    elif states:
        kind = "binary" if {c for c, _ in states} <= {"0", "1"} else "code"
    elif raw.get("Enum Set") == "0/1":
        kind = "binary"                          # 라벨은 없지만 0/1 이라고 적혀 있다
    elif rec["blocks"].get("modbus", {}).get("scaleRaw"):
        kind = "analog"                          # 배율이 붙은 수치값
    if kind:
        rec["common"]["pointKind"] = kind

    if raw:
        rec["provenance"]["sourceColumns"] = raw
    if gaps:
        rec["provenance"]["gaps"] = gaps
    for k in ("common", "blocks"):
        if not rec[k]:
            del rec[k]
    return rec, None


def read_states(text):
    """'0=Off, 1=On' → [('0','Off'), ('1','On')]. 둘 미만이면 상태로 안 본다.

    둘 이상을 요구하는 이유: 하이픈도 등호 대신 쓰이는데('0-Disabled, 1=Enabled')
    설명문의 하이픈('Setpoint - Selected')을 상태로 오인할 수 있어서다.
    """
    got = []
    for code, label in STATE.findall(text or ""):
        label = label.strip(" .,;·_")
        if label and not re.match(r"^\d+$", label):
            got.append((code, label[:80]))
    return got if len(got) >= 2 else []


def code_tables(path):
    """부속 상태 코드표 SC.1~SC.14 를 센다 — **포인트가 아니라는 것을 보이려고**.

    5~11쪽의 2열 표다. statesRef('See SC.1')를 나중에 풀 재료이지만, 포인트 표와
    같은 문서에 있어 표 인식이 한 줄로 섞어 세기 쉽다. 여기서 따로 세어
    포인트 수에 섞이지 않았음을 확인한다.
    """
    import fitz
    doc = fitz.open(path)
    out = {}
    for pg in doc:
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if len(data) < 3 or len(data[0]) != 2:
                continue
            m = SCREF.search(SP._c(data[0][0]) + " " + SP._c(data[1][1]))
            if not m:
                continue
            key = "SC.%s" % m.group(1)
            box = out.setdefault(key, {})
            for r in data[1:]:
                c, l = SP._c(r[0]), SP._c(r[1])
                if re.match(r"^\d+$", c) and l:
                    box[c] = l
    doc.close()
    return out


def main(argv):
    ap = argparse.ArgumentParser(description="JCI YZD-Logix 계통 어댑터")
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
            print("머리글: %s" % " | ".join(h[:20] for h in head if h))
        print("뺀 행: %s" % ", ".join("%s %d" % kv for kv in skip.items() if kv[1]))
        if unk:
            print("못 알아본 열: %s" % ", ".join(unk))
        ct = code_tables(cands[0])
        if ct:
            print("부속 코드표(포인트 아님): %s"
                  % ", ".join("%s %d코드" % (k, len(v)) for k, v in sorted(ct.items())))
        for r in rows[:a.limit]:
            print("\n" + json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    if a.scan:
        from collections import Counter
        tot, allunk, bands = Counter(), Counter(), Counter()
        files = sorted(glob.glob(os.path.join(PROBE, "*.pdf")))
        hit = 0
        for f in files:
            rows, unk, head, skip = parse_doc(f)
            if not rows:
                continue
            hit += 1
            tot[FAMILY_YZD] += len(rows)
            for k, v in skip.items():
                tot["(뺀 행) " + k] += v
            for u in unk:
                allunk[u] += 1
            for r in rows:
                for blk, fields in (r.get("blocks") or {}).items():
                    for k in fields:
                        tot["  %s.%s" % (blk, k)] += 1
                for k in (r.get("common") or {}):
                    tot["  " + k] += 1
                if (r.get("provenance") or {}).get("srcRef"):
                    tot["  srcRef"] += 1
                for g in ((r.get("provenance") or {}).get("gaps") or []):
                    tot["(gap) " + re.sub(r"\(.*", "", g).strip()] += 1
                bands[(r.get("common") or {}).get("group", "(없음)")] += 1
                if "bacnet" in (r.get("blocks") or {}):
                    tot["!! bacnet 블록 생성 — 검증 오류"] += 1
            print("  %-50s %5d점  %s" % (os.path.basename(f)[:50], len(rows),
                                         FAMILY_YZD))
            ct = code_tables(f)
            if ct:
                print("    부속 코드표 %d개 · %d코드 (포인트로 세지 않았다)"
                      % (len(ct), sum(len(v) for v in ct.values())))
        print("\n문서 %d건에서 파싱" % hit)
        for k, v in tot.most_common():
            print("   %-34s %6d" % (k, v))
        if bands:
            print("\n밴드(그룹)별")
            for k, v in bands.most_common():
                print("   %-40s %6d" % (k[:40], v))
        if allunk:
            print("\n못 알아본 열 (문서 수)")
            for k, v in allunk.most_common(12):
                print("   %-44s %d" % (k[:44], v))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
