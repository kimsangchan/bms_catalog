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
    "id": ["object identifier", "identifier", "object id", "obj id", "id",
           "objekt-id", "objektkennung", "object type"],
    # 'object nmae' 는 오타가 아니라 원문 그대로다 — Trane RTHD 문서가 그렇게 썼고,
    # 이걸 못 알아봐서 설명 열이 이름 자리로 들어와 81행이 오염됐다.
    "name": ["object name", "object nmae", "point name", "diagnostic name",
             "designation",
             "objektname", "nom de l'objet", "nombre del objeto"],
    "unit": ["unit", "units", "einheit", "unité", "unidad"],
    "desc": ["description", "beschreibung", "descripción"],
    "range": ["valid range", "range", "bereich"],
    "rw": ["read/write", "read", "r/w", "zugriff"],
    "dep": ["configuration", "dependency", "abhängigkeit"],
    "states": ["object states", "states", "zustände"],
    # 'register' 단독도 받는다 — Danfoss Modbus 모듈 문서가 이렇게 쓴다.
    # BACnet 문서에도 'Register Type' 열이 있지만 그쪽은 ID 열을 먼저 찾으므로
    # 이 별칭까지 오지 않는다.
    "modbus": ["modbus register", "modbus address", "register address",
               "modbus-register", "address", "register"],
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


def extract_tables(pdf, default_type=None):
    """표 인식 추출. 오브젝트 ID 열이 'AI-10101' 형태든 '1' 형태든 처리."""
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
            if i_id < 0 or i_nm < 0:
                continue
            i_ds, i_un = idx(*COL["desc"]), idx(*COL["unit"])
            i_rg, i_rw = idx(*COL["range"]), idx(*COL["rw"])
            i_dp, i_st = idx(*COL["dep"]), idx(*COL["states"])
            i_ra = idx("register\naddres", "register address", "address")
            i_rt = idx("register\ntype", "register type")
            i_rd = idx("relinquish")
            # 이 표가 다루는 오브젝트 타입 (섹션 제목에서 온 기본값)
            for r in data[1:]:
                if not r or len(r) <= max(i_id, i_nm):
                    continue
                raw_id = _c(r[i_id])
                pid = parse_objid(raw_id)
                if pid:
                    typ, inst = pid
                elif mb_mode and BARE_ID.match(raw_id):
                    typ, inst = "MB", int(raw_id)
                elif mb_mode and HEX_REG.match(raw_id):
                    typ, inst = "MB", int(HEX_REG.match(raw_id).group(2), 16)
                elif BARE_ID.match(raw_id) and default_type:
                    typ, inst = default_type, int(raw_id)
                else:
                    continue
                name = _c(r[i_nm])
                if not name or len(name) < 3:
                    continue
                note = []
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
                rows.append({"type": S.canon_type(typ), "inst": inst,
                             "name": name, "unitRaw": UNIT_HINT.get(u, u or None),
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


def extract_by_section(pdf):
    """ID가 숫자만인 Trane 냉동기 문서용 — 페이지 섹션 제목으로 타입을 준다."""
    import fitz
    doc = fitz.open(pdf)
    types = section_types(pdf)
    rows = []
    for i, pg in enumerate(doc):
        dt = types.get(i)
        if not dt:
            continue
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if len(data) < 2:
                continue
            hdr = [_c(c).lower() for c in data[0]]
            i_id = next((j for j, h in enumerate(hdr) if "identifier" in h), -1)
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
        if p:
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
