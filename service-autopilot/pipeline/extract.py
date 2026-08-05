# -*- coding: utf-8 -*-
"""추출기 — 문서 1건 → 포인트 목록.

추출 방식이 여러 개고 품질 차이가 크다. 초기에 쓴 '단어 좌표/단위 큐' 방식은
타입을 못 붙이거나 이름을 엉뚱한 인스턴스에 붙였다. 표 인식이 가장 정확하므로
그것을 기본으로 두고, 안 되는 문서만 다른 방식으로 내려간다.

  table  PyMuPDF find_tables()  — 셀 경계를 직접 인식. 기본값
  ede    BIG-EU EDE 4파일 세트  — 벤더 배포 CSV. 가장 정확
  layout pdftotext -layout      — 표 인식 실패 시 최후

실행:  python extract.py <pdf> --out <model.json>
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schema as S  # noqa: E402

# 구분자로 '-', 공백, ':' 을 모두 받는다 — Danfoss 는 'AI: 0' 처럼 콜론을 쓴다.
# NC(알림)·TL(추세)·EE(이벤트)·SO(스케줄)·CO(달력) 도 BACnet 표준 오브젝트다.
# 인스턴스를 대괄호로 감싸는 표기도 받는다 — Belimo 는 'AI[1]' 처럼 쓴다.
OBJID = re.compile(
    r"^(AI|AO|AV|BI|BO|BV|MI|MO|MV|MSI|MSO|MSV|NC|TL|EE|SO|CO|Dev|SV|LAV)"
    r"[\s:-]*\[?\s*(\d{1,6})\s*\]?$", re.I)
BARE_ID = re.compile(r"^(\d{1,6})$")
# ebm-papst 는 레지스터를 'D000'·'D14A' 처럼 문자+16진으로 쓴다. 값은 16진이다
# (문서에 D149·D14A 가 이어진다). 원표기는 비고에 남긴다.
HEX_REG = re.compile(r"^([A-Z])([0-9A-F]{3})$")
# Swegon 은 Modbus 참조 표기 '0x0001·1x0501·3x0004·4x0094' 를 쓴다 — 표준 절대
# 참조로 편다 (1x0501 → 10501, 4x0094 → 40094). 앞자리가 테이블(코일/입력/레지스터)이다.
MODBUS_REF = re.compile(r"^([0134])x(\d{4})$")
# 'Analog Input, 1' / 'Binary Value 3' 처럼 타입을 풀어 쓴 형식 — CH530 문서가 이렇게 쓴다.
# 이걸 못 읽어 RTHD(CH530) 문서에서 0점이 나왔다.
SPELLED = re.compile(
    r"^(analog|binary|multi-?state)\s+(input|output|value)s?\s*,?\s*(\d{1,6})$", re.I)
SPELLED_TYPE = {("analog", "input"): "AI", ("analog", "output"): "AO",
                ("analog", "value"): "AV", ("binary", "input"): "BI",
                ("binary", "output"): "BO", ("binary", "value"): "BV",
                ("multistate", "input"): "MSI", ("multistate", "output"): "MSO",
                ("multistate", "value"): "MSV"}


CASED = {"ai": "AI", "ao": "AO", "av": "AV", "bi": "BI", "bo": "BO", "bv": "BV",
         "mi": "MI", "mo": "MO", "mv": "MV", "msi": "MSI", "mso": "MSO", "msv": "MSV",
         "nc": "NC", "tl": "TL", "ee": "EE", "so": "SO", "co": "CO", "dev": "Dev",
         "sv": "SV", "lav": "LAV"}


def parse_objid(raw):
    """오브젝트 ID 문자열 → (타입, 인스턴스). 표기 세 가지를 모두 받는다."""
    m = OBJID.match(raw)
    if m:
        return CASED.get(m.group(1).lower(), m.group(1).upper()), int(m.group(2))
    m = SPELLED.match(raw)
    if m:
        fam = m.group(1).lower().replace("-", "").replace("multistate", "multistate")
        t = SPELLED_TYPE.get((fam, m.group(2).lower()))
        if t:
            return t, int(m.group(3))
    return None
ALPHA = re.compile(r"[A-Za-z]")


def nameish(s):
    """이름 같은 문자열인가 — 알파벳 3자 이상. '3E9' 같은 고장코드 16진값을 걸러낸다."""
    return len(ALPHA.findall(s)) >= 3
UNIT_HINT = {"Temperature": "℃", "Pressure": "kPa", "Percent": "%", "Time": "h",
             "Power": "kW", "Energy": "kWh", "Amps": "A", "Volts": "V",
             "Frequency": "Hz", "No Units": None, "Real": None, "Enumerated": None,
             "Boolean": None, "°F": "℉", "°C": "℃"}


def _c(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()


# 열 이름은 벤더·언어마다 다르다. 여기 한 곳에만 모아 둔다.
# 새 벤더에서 표를 못 읽으면 대개 여기에 별칭 하나를 더하면 된다.
COL = {
    # 'object type' 은 마지막에 둔다 — Belimo 는 ID 열 이름이 'Object Type [Instance]'
    # 이지만, 두 열이 다 있는 문서에서는 'object identifier' 가 먼저 잡혀야 한다.
    # 맨 뒤 'object' 단독은 최후 보루 — AAON VCCX2 는 ID 열 이름이 그냥 'Object'
    # ('AI: 1' 값)다. 다른 별칭이 다 실패했을 때만 온다.
    "id": ["object identifier", "identifier", "object id", "obj id", "id",
           "objekt-id", "objektkennung", "object type", "object"],
    # 'object nmae' 는 오타가 아니라 원문 그대로다 — Trane RTHD 문서가 그렇게 썼고,
    # 이걸 못 알아봐서 설명 열이 이름 자리로 들어와 81행이 오염됐다.
    # 'data label' · 'data description' 이 'object name' 보다 **앞**이다.
    # Vertiv/Liebert 는 사람이 읽는 이름을 이 칸에 두고 Object Name 에는
    # '5598_1_2' 같은 내부 코드를 적는다. 순서를 바꾸면 이름 자리가 코드로 채워진다.
    # 같은 문서 안에서도 표마다 'Data Label' 과 'Data Description' 이 섞여 나온다 —
    # 정밀공조 CW 계열은 표 115개 중 34개가 후자라, 이걸 빼먹으면 그만큼이 코드가 됐다.
    # 'property description' 은 JCI Simplicity SE, 'data point' 는 Daikin ED 의
    # Modbus 표('Chiller Data Point') — 없으면 설명 열이 이름 자리에 들어온다.
    # 맨 뒤의 'name' 단독은 최후 보루다 — Swegon 은 열 이름이 그냥 'Name' 이라
    # 이게 없으면 설명 열이 이름 자리에 들어온다.
    "name": ["data label", "data description", "object name", "object nmae",
             "point name", "data point", "diagnostic name", "designation",
             "property description", "objektname", "nom de l'objet", "nombre del objeto",
             "parameter", "name"],
    # 'dim' 은 Siemens Climatix — 단위 열 이름이 'Dim' 이다.
    "unit": ["unit", "units", "dim", "einheit", "unité", "unidad"],
    "desc": ["description", "beschreibung", "descripción"],
    "range": ["valid range", "range", "bereich"],
    "rw": ["read/write", "read", "r/w", "access", "zugriff"],
    "notes": ["notes", "note", "bemerkung"],
    "dep": ["configuration", "dependency", "abhängigkeit"],
    "states": ["object states", "states", "zustände"],
    # 'register' 단독도 받는다 — Danfoss Modbus 모듈 문서가 이렇게 쓴다.
    # BACnet 문서에도 'Register Type' 열이 있지만 그쪽은 ID 열을 먼저 찾으므로
    # 이 별칭까지 오지 않는다. 'modbus' 단독은 Swegon GOLD — ID 열 이름이 'Modbus' 다.
    "modbus": ["modbus register", "modbus address", "register address",
               "modbus-register", "address", "register", "modbus"],
    # 타입과 번호를 한 칸에 'AI-4' 로 적지 않고 열을 갈라 적는 벤더가 있다
    # (JCI VRF 게이트웨이: 'Object Type'=AI, 'BACnet Instance Number'=4).
    # 이때는 두 열을 합쳐야 오브젝트가 된다 — 아래 split 모드.
    "objtype": ["bacnet object type", "object type", "obj type"],
    "instance": ["bacnet instance number", "instance number",
                 "object instance", "instance"],
}


def _mk_idx(hdr):
    """열 찾기 — 헤더의 공백은 무시한다.

    같은 문서 안에서도 'NV #' / 'NV#' / 'Object\\nIdentifier' 처럼 표기가 흔들린다.
    공백을 넣어 비교하다가 IntelliPak 문서의 Send 표 10개(150여 행)를 통째로
    놓친 적이 있다. 그래서 양쪽 공백을 지우고 비교한다.
    """
    flat = [re.sub(r"\s+", "", h) for h in hdr]

    def idx(*names):
        for n in names:
            key = re.sub(r"\s+", "", n)
            for j, h in enumerate(flat):
                if key in h:
                    return j
        return -1
    return idx


# 단위 칸 모양 가드 — 단위는 짧은 토큰이다. 표 각주 문장(Lennox CORE 'These legacy
# alarm reporting objects are obsolete …')이나 범위+기본값(Daikin '-40 – 230°F -40 –
# 110°C Default: NA')이 단위 칸으로 눌려 들어오면 단위가 아니라 비고로 보낸다.
# 'Seconds since Midnight'(Vertiv)·'mV Ω 0 / 1 °C °F'(Belimo 설정별 단위 나열)처럼
# 문서가 정말 단위로 적은 표기는 그대로 둔다 — 소문자 낱말 3연속+40자(문장)나
# 숫자-대시-숫자(범위)+온도단위가 있어야만 옮긴다.
UNIT_PROSE = re.compile(r"(?:[a-z]{3,}\s+){2}[a-z]{3,}")
UNIT_RANGE = re.compile(r"\d[\s.°]*[-–][\s.°]*\d")


def unit_or_note(u):
    """(단위, 비고로 보낼 원문) — 단위 칸 값이 단위가 아니면 비고로 옮긴다."""
    text = (u or "").strip()
    if not text:
        return "", ""
    if len(text) > 40 and UNIT_PROSE.search(text):
        return "", text
    if UNIT_RANGE.search(text) and (re.search(r"°\s*[FC]|Default", text) or len(text) > 24):
        return "", "범위 " + text
    # 'Default:' 는 단위 칸에 올 낱말이 아니다 — 숫자 범위 없이 문장으로만 적힌
    # 경우('Amp range varies by chiller model Default: NA', Daikin)도 비고로 보낸다
    if re.search(r"Default\s*:", text):
        return "", text
    return text, ""


# 한 문서에 장치가 둘이고 **번호를 다시 쓰는** 경우를 표 제목으로 가른다.
# JCI VRF 게이트웨이는 실내기 표와 실외기 표가 AI-16 을 각각 다른 뜻으로 쓴다 —
# 가르지 않으면 뒤 표가 앞 표를 덮어써서 실외기 포인트가 조용히 사라진다.
SECT_CAPTION = re.compile(r"points for (indoor|outdoor) units", re.I)


def captions(pdf):
    """[(페이지, 제목 하단 y, 구간이름)] — 표 제목이 어디서 무엇으로 바뀌는지."""
    import fitz
    out = []
    for i, pg in enumerate(fitz.open(pdf)):
        for b in pg.get_text("blocks"):
            m = SECT_CAPTION.search(re.sub(r"\s+", " ", b[4]))
            if m:
                out.append((i, b[3], m.group(1).lower()))
    return out


def sect_at(caps, page, y):
    """이 위치를 덮는 표 제목 — 같은 쪽 위쪽, 없으면 앞 쪽의 마지막 제목."""
    best = None
    for cp, cy, s in caps:
        if cp < page or (cp == page and cy <= y):
            best = s
    return best


def _header_row(data, look=3):
    """머리글이 몇 번째 행인가. 못 찾으면 None.

    벤더가 표 위에 배너 행('Controller | Liebert iCOM v4')을 얹어 두면 첫 행에는
    열 이름이 없다. 앞 몇 행만 본다 — 더 내려가면 자료 행을 머리글로 착각한다.
    """
    for i in range(min(look, len(data) - 1)):
        hdr = [_c(c).lower() for c in data[i]]
        idx = _mk_idx(hdr)
        has_id = (idx(*COL["id"]) >= 0 or idx(*COL["modbus"]) >= 0
                  or (idx(*COL["objtype"]) >= 0 and idx(*COL["instance"]) >= 0))
        if has_id and idx(*COL["name"]) >= 0:
            return i
    return 0 if len(data) > 1 else None


def extract_tables(pdf, default_type=None, pages=None):
    """표 인식 추출. 오브젝트 ID 열이 'AI-10101' 형태든 '1' 형태든 처리.

    pages=(시작, 끝) 은 **0부터 세는 반열린 구간**이다. 한 문서에 제품 수십 개가
    들어 있는 통합 레퍼런스(Vertiv IntelliSlot 1,748쪽)에서 제품 하나만 뽑을 때 쓴다.
    통째로 훑으면 느리고, 제품끼리 인스턴스 번호가 겹쳐 서로를 덮는다.
    """
    import fitz
    doc = fitz.open(pdf)
    caps = captions(pdf)
    rng = range(*pages) if pages else range(doc.page_count)
    rows = []
    for pg in (doc[i] for i in rng):
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if len(data) < 2:
                continue
            # 머리글이 첫 행이 아닐 수 있다. Vertiv/Liebert 는 표마다 위에
            # 'Controller | Liebert iCOM v4' 배너 행을 하나 얹어 두는데, 첫 행만
            # 보다가 정밀공조 최대 계열(CW·CWA·DSE·PDX/PCW)을 통째로 놓쳤다.
            h0 = _header_row(data)
            if h0 is None:
                continue
            hdr = [_c(c).lower() for c in data[h0]]
            idx = _mk_idx(hdr)
            i_id = idx(*COL["id"])
            # 진단 알람도 BACnet 오브젝트다 — Ascend 문서는 이름 열을 'Diagnostic Name'
            # 으로 쓰는데, 이걸 못 알아봐서 알람 BI 488점을 통째로 놓쳤었다.
            i_nm = idx(*COL["name"])
            # Modbus 레지스터 표는 ID 열 이름이 다르고 인스턴스가 레지스터 주소다.
            # 이름 열도 'Object Name' 이 아니라 'Description' 인 경우가 많다.
            i_mb = idx(*COL["modbus"])
            mb_mode = i_id < 0 and i_mb >= 0
            if mb_mode:
                i_id = i_mb
                if i_nm < 0:
                    i_nm = idx(*COL["desc"])
            # 타입 열 / 번호 열이 갈라져 있는가. 같은 열을 가리키면 아니다 —
            # Belimo 는 열 이름 자체가 'Object Type [Instance]' 라 둘 다 걸린다.
            i_ty, i_in = idx(*COL["objtype"]), idx(*COL["instance"])
            split_mode = i_ty >= 0 and i_in >= 0 and i_ty != i_in
            # 타입이 열이 아니라 **머리글에** 적힌 표 — Siemens Climatix 는
            # 'Analog input, object name' + 'Object instance' 구조라 타입 열이 없다.
            head_type = None
            if i_id < 0 and not split_mode and i_in >= 0 and i_nm >= 0:
                mh = re.search(r"(analog|binary|multi-?state)\s+(input|output|value)",
                               " ".join(hdr), re.I)
                if mh:
                    fam = mh.group(1).lower().replace("-", "")
                    head_type = SPELLED_TYPE.get((fam, mh.group(2).lower()))
                    if head_type:
                        i_id = i_in
            if (i_id < 0 and not split_mode) or i_nm < 0:
                continue
            i_ds, i_un = idx(*COL["desc"]), idx(*COL["unit"])
            # 'Data Description' 을 이름으로 쓴 표에서는 설명 열이 이름 열과 같은 칸을
            # 가리킨다. 그대로 두면 비고가 이름을 한 번 더 되뇐다.
            if i_ds == i_nm:
                i_ds = -1
            i_rg, i_rw = idx(*COL["range"]), idx(*COL["rw"])
            i_dp, i_st = idx(*COL["dep"]), idx(*COL["states"])
            # 단위를 제 열에 두지 않고 비고에 'Units: deg C' 로 적는 문서가 있다
            # (Vertiv/Liebert). 비고 열을 안 읽으면 온도 포인트가 전부 단위 미상이 된다.
            i_nt = idx(*COL["notes"])
            # 이름 열이 'Data Label' 인 문서에서 'Object Name' 은 벤더 내부 코드다.
            # 버리지 않고 비고에 남긴다 — 현장에서 이 코드로 조회한다.
            i_on = idx("object name")
            i_ra = idx("register\naddres", "register address", "address")
            i_rt = idx("register\ntype", "register type")
            i_rd = idx("relinquish")
            # Systemair Access — 'Modbus type'(Input Register (3x)) 과 'Modbus address'
            # (0041) 가 갈라진 표. 주소만 쓰면 3x/4x/1x 가 겹쳐 663개 주소가 dedupe 로
            # 조용히 사라진다 — Swegon 참조표기와 같은 절대 참조(타입×10000+주소)로 편다.
            i_mt = idx("modbus type")
            i_bn = idx("bacnet")
            i_fn = idx("function")
            # EXOL 경로명(VentSettings.SAlaAcknowAll_)은 공백이 없다 — 셀 줄바꿈이
            # 이름 중간에 공백을 끼워 넣으므로 EXOL 열이 있는 문서에선 걷어낸다
            exol_doc = any("exol" in h for h in
                           (re.sub(r"\s+", "", x) for x in hdr))
            # 이 표가 다루는 오브젝트 타입 (섹션 제목에서 온 기본값)
            for r in data[h0 + 1:]:
                if not r or len(r) <= max(i_id, i_nm, i_ty, i_in):
                    continue
                split = None
                if split_mode:
                    t_raw = S.canon_type(_c(r[i_ty]))
                    n_raw = _c(r[i_in])
                    if t_raw in S.OBJ_TYPES and BARE_ID.match(n_raw):
                        split = (t_raw, int(n_raw))
                raw_id = _c(r[i_id]) if i_id >= 0 else ""
                pid = parse_objid(raw_id)
                extra_note = ""
                if split:
                    typ, inst = split
                elif pid:
                    typ, inst = pid
                elif mb_mode and BARE_ID.match(raw_id):
                    mp = (re.search(r"\(([0134])x\)", _c(r[i_mt]))
                          if 0 <= i_mt < len(r) else None)
                    if mp:
                        typ = "MB"
                        inst = int(mp.group(1)) * 10000 + int(raw_id)
                        extra_note = "원표기 %sx%04d" % (mp.group(1), int(raw_id))
                    else:
                        typ, inst = "MB", int(raw_id)
                elif mb_mode and MODBUS_REF.match(raw_id):
                    mr = MODBUS_REF.match(raw_id)
                    typ, inst = "MB", int(mr.group(1)) * 10000 + int(mr.group(2))
                    extra_note = "원표기 " + raw_id
                elif mb_mode and HEX_REG.match(raw_id):
                    typ, inst = "MB", int(HEX_REG.match(raw_id).group(2), 16)
                elif BARE_ID.match(raw_id) and head_type:
                    typ, inst = head_type, int(raw_id)
                elif BARE_ID.match(raw_id) and default_type:
                    typ, inst = default_type, int(raw_id)
                elif (BARE_ID.match(raw_id) and 0 <= i_mb != i_id
                      and i_mb < len(r) and BARE_ID.match(_c(r[i_mb]))
                      and int(_c(r[i_mb])) > 0):
                    # JCI Simplicity SE — ID 열(BACOid)에 타입이 없어 오브젝트로 못
                    # 만든다. 같은 행의 Modbus 주소를 레지스터 포인트로 취입하고
                    # BACnet OID 는 비고에 남긴다 (타입은 LIT-12011950 참조).
                    typ, inst = "MB", int(_c(r[i_mb]))
                    extra_note = "BACnet OID %s (타입 열 없음)" % raw_id
                else:
                    continue
                name = _c(r[i_nm])
                if exol_doc and " " in name:
                    name = name.replace(" ", "")
                if not name or len(name) < 3:
                    continue
                note = [extra_note] if extra_note else []
                if mb_mode and 0 <= i_bn < len(r) and _c(r[i_bn]):
                    note.append("BACnet " + _c(r[i_bn]))
                if mb_mode and 0 <= i_fn < len(r) and _c(r[i_fn]):
                    note.append(_c(r[i_fn]))
                for i, pfx in ((i_ds, ""), (i_st, ""), (i_rg, "범위 "), (i_rd, "기본 ")):
                    if 0 <= i < len(r) and _c(r[i]):
                        note.append(pfx + _c(r[i]))
                if 0 <= i_rw < len(r) and _c(r[i_rw]).lower().startswith(("read/w", "r/w", "write")):
                    note.append("쓰기 가능")
                if 0 <= i_dp < len(r) and _c(r[i_dp]) and not _c(r[i_dp]).lower().startswith("all "):
                    note.append("조건: " + _c(r[i_dp]))
                if 0 <= i_ra < len(r) and _c(r[i_ra]).isdigit():
                    note.append("Modbus %s %s" % (_c(r[i_rt]) if 0 <= i_rt < len(r) else "reg",
                                                  _c(r[i_ra])))
                u = _c(r[i_un]) if 0 <= i_un < len(r) else ""
                if 0 <= i_nt < len(r) and _c(r[i_nt]):
                    nt = _c(r[i_nt])
                    mu = re.match(r"units?\s*[:=]\s*(.+?)\s*$", nt, re.I)
                    if mu and not u:
                        u = mu.group(1)
                    else:
                        note.append(nt)
                if 0 <= i_on < len(r) and i_on != i_nm and _c(r[i_on]):
                    note.append("코드 " + _c(r[i_on]))
                u, spill = unit_or_note(u)
                if spill:
                    note.append(spill)
                rows.append({"type": S.canon_type(typ), "inst": inst,
                             "name": name, "unitRaw": UNIT_HINT.get(u, u or None),
                             "unit": S.canon_unit(UNIT_HINT.get(u, u)),
                             "note": " · ".join(note)[:240],
                             "sect": sect_at(caps, pg.number, t.bbox[1])})
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: (x["type"], x["inst"])):
        # 구간이 나뉜 문서는 구간까지 넣어 유일성을 본다 — 안 넣으면 실외기 AI-16 이
        # 실내기 AI-16 에 밀려 사라진다.
        k = (r.get("sect"), r["type"], r["inst"]) if r.get("sect") else (r["type"], r["inst"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def section_types(pdf):
    """'Analog Inputs' 같은 섹션 제목으로 표별 기본 타입을 추정 (ID가 숫자만인 문서용)."""
    import fitz
    doc = fitz.open(pdf)
    MAP = {"analog input": "AI", "analog output": "AO", "analog value": "AV",
           "binary input": "BI", "binary output": "BO", "binary value": "BV",
           "multi-state input": "MSI", "multi-state output": "MSO", "multi-state value": "MSV"}
    per_page = {}
    for i, pg in enumerate(doc):
        txt = pg.get_text().lower()
        for k, v in MAP.items():
            if k in txt:
                per_page[i] = v
                break
    return per_page


# 표 캡션에 든 타입 — 'Table 13. Analog Output (AO) Objects List' (Lennox CORE).
# 페이지 섹션 제목보다 정확하다: 한 쪽에 AO 표 끝과 AV 표 시작이 같이 있으면
# 페이지 타입은 한쪽을 뒤집어쓴다.
CAPTION_TYPE = re.compile(r"\((AI|AO|AV|BI|BO|BV|MSI|MSO|MSV)\)\s*Objects?\s*List", re.I)


def extract_by_section(pdf):
    """ID가 숫자만인 문서용 — 표 캡션의 '(AO) Objects List'(Lennox CORE)가 1순위,
    없으면 페이지 섹션 제목(Trane 냉동기)으로 타입을 준다."""
    import fitz
    doc = fitz.open(pdf)
    types = section_types(pdf)
    rows = []
    for i, pg in enumerate(doc):
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if len(data) < 2:
                continue
            dt = types.get(i)
            # 캡션이 표의 첫 행으로 눌려 들어오는 문서(Lennox) — 타입을 읽고 걷어낸다
            cap = CAPTION_TYPE.search(_c(data[0][0]))
            if cap and len(data) > 2:
                dt = cap.group(1).upper()
                data = data[1:]
            if not dt:
                continue
            hdr = [_c(c).lower() for c in data[0]]
            i_id = next((j for j, h in enumerate(hdr)
                         if "identifier" in h or "object id" in h), -1)
            i_nm = next((j for j, h in enumerate(hdr) if "object name" in h), -1)
            if i_id < 0 or i_nm < 0:
                continue
            i_ds = next((j for j, h in enumerate(hdr) if "description" in h), -1)
            i_un = next((j for j, h in enumerate(hdr) if "unit" in h), -1)
            i_st = next((j for j, h in enumerate(hdr) if "state" in h), -1)
            i_rg = next((j for j, h in enumerate(hdr) if "range" in h), -1)
            for r in data[1:]:
                if len(r) <= max(i_id, i_nm):
                    continue
                rid = _c(r[i_id])
                if BARE_ID.match(rid):
                    typ, inst = dt, int(rid)
                else:
                    pid = parse_objid(rid)
                    if not pid:
                        continue
                    typ, inst = pid
                name = _c(r[i_nm])
                if len(name) < 3:
                    continue
                note = [x for x in (_c(r[i_ds]) if 0 <= i_ds < len(r) else "",
                                    _c(r[i_st]) if 0 <= i_st < len(r) else "",
                                    ("범위 " + _c(r[i_rg])) if 0 <= i_rg < len(r) and _c(r[i_rg]) else "") if x]
                u = _c(r[i_un]) if 0 <= i_un < len(r) else ""
                u, spill = unit_or_note(u)
                if spill:
                    note.append(spill)
                rows.append({"type": S.canon_type(typ), "inst": inst, "name": name,
                             "unitRaw": UNIT_HINT.get(u, u or None),
                             "unit": S.canon_unit(UNIT_HINT.get(u, u)),
                             "note": " · ".join(note)[:240]})
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: (x["type"], x["inst"])):
        k = (r["type"], r["inst"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out



def extract_lontalk(pdf, keep_order=False):
    """LonTalk 문서 — Network Variable(SNVT) 표. BAS-PTS 시리즈에 BACnet과 섞여 있다.

    타입은 이름 접두어로 갈린다: nci… = 설정 변수(NCI), nvi/nvo… = 실시간 변수(NV).
    keep_order=True 면 문서 순서를 유지한다 — 프로파일 분할(split_profiles)에 필요하다.
    """
    import fitz
    doc = fitz.open(pdf)
    rows = []
    for pg in doc:
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if len(data) < 2:
                continue
            hdr = [_c(c).lower() for c in data[0]]
            idx = _mk_idx(hdr)
            i_id = idx("nv #", "nv index", "profile index")
            # 'Network Variable Type' 은 문서 오기(誤記)로 보이지만 이름 열이 맞다 —
            # IntelliPak 문서의 Send 표 300여 행이 여기에 걸려 있다.
            i_nm = idx("network variable name", "network variable type",
                       "configuration variable", "point name")
            if i_id < 0 or i_nm < 0:
                continue
            i_ty = idx("snvt", "variable type")
            if i_ty == i_nm:          # 'Network Variable Type' 열을 SNVT로 오인하지 않는다
                i_ty = idx("snvt")
            i_ds = idx("variable description", "description")
            i_hb = idx("hrtbt")
            direction = "출력(Send)" if any("send" in h for h in hdr) else (
                "입력(Recv)" if any("recv" in h for h in hdr) else "")
            for r in data[1:]:
                if len(r) <= max(i_id, i_nm):
                    continue
                rid = _c(r[i_id])
                if not re.match(r"^\d{1,4}$", rid):
                    continue
                name = _c(r[i_nm])
                if len(name) < 3:
                    continue
                snvt = _c(r[i_ty]) if 0 <= i_ty < len(r) else ""
                note = [x for x in (snvt, _c(r[i_ds]) if 0 <= i_ds < len(r) else "",
                                    direction,
                                    ("HrtBt " + _c(r[i_hb])) if 0 <= i_hb < len(r) and _c(r[i_hb]) else "") if x]
                typ = "NCI" if name[:3].lower() == "nci" else "NV"
                rows.append({"type": typ, "inst": int(rid), "name": name,
                             "unitRaw": None, "unit": None, "note": " · ".join(note)[:240]})
    seq = rows if keep_order else sorted(rows, key=lambda x: (x["type"], x["inst"]))
    seen, out = set(), []
    for r in seq:
        k = (r["type"], r["inst"], r["name"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def split_profiles(rows):
    """한 문서에 장치·프로파일이 여러 개 섞인 경우 문서 순서대로 잘라낸다.

    근거: 같은 (타입, 인스턴스)가 다른 이름으로 다시 나오면 새 장치가 시작된 것이다.
    LonTalk 프로파일은 NV 번호가 프로파일마다 0부터 다시 시작하고, BACnet 문서도
    실내기·실외기가 한 파일에 들어오면 같은 일이 벌어진다. 문서별 규칙이 아니라
    '번호가 이미 쓰였는가'만 보므로 어느 문서에나 통한다.

    입력은 반드시 문서 순서(keep_order=True)여야 한다.
    """
    segs, cur, used = [], [], set()
    for r in rows:
        k = (r["type"], r["inst"])
        if k in used:
            segs.append(cur)
            cur, used = [], set()
        cur.append(r)
        used.add(k)
    if cur:
        segs.append(cur)
    return [sorted(s, key=lambda x: (x["type"], x["inst"])) for s in segs]


def count_data_rows(pdf):
    """표 안에서 '데이터 행처럼 보이는' 행 수 — 추출 누락을 재는 잣대.

    추출기가 헤더 표기를 못 알아보면 표를 통째로 건너뛰는데, 결과만 보면
    조용히 적게 나온 것과 원래 적은 것을 구분할 수 없다. 그래서 추출기와
    무관하게 '1열이 번호이거나 오브젝트 ID이고 2열에 이름이 있는 행'을 센다.

    같은 (번호, 이름)이 여러 표에 반복되는 것은 문서 편집상 중복이므로 한 번만 센다.
    이렇게 해야 '추출기가 놓친 것'과 '원래 중복이라 지운 것'이 섞이지 않는다.
    """
    import fitz
    seen = set()
    for pg in fitz.open(pdf):
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if len(data) < 2 or len(data[0]) < 2:
                continue
            for r in data[1:]:
                a, b = _c(r[0]), _c(r[1]) if len(r) > 1 else ""
                if (BARE_ID.match(a) or parse_objid(a)) and nameish(b):
                    seen.add((a, b))
    return len(seen)


def classify(pdf):
    """문서가 어느 프로토콜 계열인지 — 추출기 선택에 쓴다."""
    import fitz
    txt = " ".join(fitz.open(pdf)[i].get_text() for i in range(min(4, fitz.open(pdf).page_count))).lower()
    if "snvt" in txt or "network variable" in txt:
        return "lontalk"
    if "object identifier" in txt or "bacnet" in txt:
        return "bacnet"
    if "register" in txt:
        return "modbus"
    return "unknown"


def extract(pdf, mode="auto"):
    fam = classify(pdf)
    if fam == "lontalk":
        p = extract_lontalk(pdf)
        # SNVT 가 이 정도는 나와야 진짜 LonWorks 문서다. Daikin ED 문서는 표 제목이
        # 'BACnet Network Variables' 라 lontalk 으로 오판됐고, SNVT 추출이 2점을 내고
        # 조기 반환해 BACnet 표 285점을 통째로 버린 적이 있다.
        if len(p) >= 20:
            return p, "lontalk"
    if mode in ("auto", "table"):
        p = extract_tables(pdf)
        if len(p) >= 20 and sum(1 for x in p if x["type"] != "—") > len(p) * 0.8:
            return p, "table"
    p2 = extract_by_section(pdf)
    if len(p2) > len(p if mode != "section" else []):
        return p2, "table+section"
    return p, "table"


if __name__ == "__main__":
    pdf = sys.argv[1]
    pts, how = extract(pdf)
    tc = collections.Counter(p["type"] for p in pts)
    print("%s → %d점 (%s) 타입분포 %s" % (os.path.basename(pdf), len(pts), how, dict(tc)))
    for p in pts[:10]:
        print("   %-4s %-6d %-5s %s" % (p["type"], p["inst"], p["unitRaw"] or "-", p["name"][:52]))
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        json.dump(pts, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("→", out)
