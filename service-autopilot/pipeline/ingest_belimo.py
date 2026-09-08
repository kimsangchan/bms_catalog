# -*- coding: utf-8 -*-
"""Belimo 필드기기 — 형번별 정격 취입 (제품 데이터시트 49건).

  PYTHONIOENCODING=utf-8 python ingest_belimo.py          바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_belimo.py --run    실제로 기록한다

왜 전용으로 읽나
  `data/raw/belimo_*_datasheet_*.pdf` 49건이 **어떤 모델도 참조하지 않는 고아**였다.
  그 바람에 Belimo 19모델(오브젝트 492점)이 정격 0 이었다 — 포인트는 통신 맵
  (`belimo_Modbus-Register_*` · `belimo_BACnet_Interface-description_*`)에서 왔는데
  그 문서에는 토크·소비전력이 없다. 문서를 더 구할 필요가 없었고 **짝만 안 지어져 있었다.**

  범용 추출기(specs.py)를 돌리면 **표 0개**가 나온다. 이 데이터시트는 표가 아니라
  `라벨↵값` 두 줄짜리 텍스트이기 때문이다:
      Power consumption in operation
      1.5 W
  그래서 라벨 다음 줄을 값으로 읽는다.

  밸브 계열(EV·EP·D6…)은 다르다 — 첫 쪽에 **Type Overview** 라는 형번 표가 있고
  거기에 DN·V'nom·Kvs·PN 이 형번마다 적혀 있다. 이건 x 좌표로 열을 갈라 읽는다.
  ⚠ 토큰 수로 열을 세면 안 된다 — `1 1/4`(1과 1/4 인치)처럼 한 칸이 낱말 둘이다.

담는 범위 (규칙 0)
  `data/equip-requirements.json` 의 e16.actuator · e16.valve · e6.vav 가 요구하는 것만.
  전기 정격(운전/정지 소비전력·전압·변압기 용량) · 토크 · 구동 시간 · 소음 ·
  밸브의 DN·V'nom·Kvs·PN. 재질·보호등급·배선 규격은 계산에 안 들어가 담지 않는다.
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# 모델 ↔ 데이터시트. 짝의 근거는 각 모델의 통신 맵이 덮는 제품군이다.
# 값은 파일이름 조각(접두 `belimo_` 와 접미 `_datasheet_*.pdf` 는 뺀다).
SHEETS = {
    "belimo-damper-actuator-modbus": [
        "AFB24-SR", "AFRB24-SR", "AFX24-MFT", "AMB24-3", "AMX24-MFT", "ARB24-3",
        "GMB24-3", "GMX24-MFT", "LF24-S_US", "LM24A-MOD", "LMB24-3", "LMB24-3-T",
        "LMB24-SR", "LMX24-MFT", "NFB24-SR", "NFX24-MFT", "NMB24-3", "NMQB24-MFT",
        "NMX24-MFT", "TFB24-S", "FSAF24A"],
    "belimo-air-water-actuator-modbus": ["LR24A-MOD", "NR24A-MOD", "SR24A-MOD",
                                         "LRB24-3", "LVKB24-3"],
    "belimo-butterfly-valve-actuator-modbus": ["D6..BL", "D6..N", "GK24A-MOD"],
    "belimo-energy-valve-dn-15-50-version-4-modbus": [
        "EV..R2_BAC", "EV..R2_KBAC", "EV..R3_BAC", "EV..F_BAC", "EV050_ARX-E_N4HT"],
    "belimo-6-way-epiv-modbus": ["EP..R2_BAC", "EP050_LRX-E"],
    "belimo-thermal-energy-meter-modbus": ["22PE-1U..", "22PE-5U..", "22PEM-1U..",
                                           "G-22PEM-A01"],
    "belimo-vav-compact-modbus": ["LMV-D3-MOD", "NMV-D3-MOD"],
    "belimo-cq24a-bac-modbus": ["CQ24A-BAC"],
    "belimo-flow-sensor-22pf": ["22PF-1U.."],
    "belimo-sensors-22dt-22ut": ["22DTH-56M", "22DTM-56", "22UTH-560X"],
    "belimo-vru-d3-bac": ["VRU-D3-BAC"],
}
# 같은 제품군의 BACnet 판은 Modbus 판과 **같은 기기**다 — 정격도 같다.
ALSO = {
    "belimo-damper-actuator-bacnet": "belimo-damper-actuator-modbus",
    "belimo-air-water-actuator-bacnet": "belimo-air-water-actuator-modbus",
    "belimo-butterfly-valve-actuator-bacnet": "belimo-butterfly-valve-actuator-modbus",
    "belimo-energy-valve-dn-15-50-version-4-bacnet":
        "belimo-energy-valve-dn-15-50-version-4-modbus",
    "belimo-6-way-epiv-bacnet": "belimo-6-way-epiv-modbus",
    "belimo-thermal-energy-meter-bacnet": "belimo-thermal-energy-meter-modbus",
    "belimo-vav-compact-bacnet": "belimo-vav-compact-modbus",
    "belimo-vav-compact-mv-d3-mod": "belimo-vav-compact-modbus",
}

# 항목 이름은 `한글 · 원문영문 (단위)` 로 통일한다(LS·삼성과 같은 관례).
# ⚠ 괄호 안에는 단위만 둔다 — datasets.label_unit 이 괄호를 통째로 단위로 읽는다.
ITEMS = [
    ("정격 전압", "Nominal voltage", "", r"^Nominal voltage$"),
    ("운전 중 소비전력", "Power consumption in operation", "W",
     r"^Power consumption in operation$"),
    ("정지 시 소비전력", "Power consumption in rest position", "W",
     r"^Power consumption in rest position$"),
    ("변압기 용량", "Transformer sizing", "VA",
     r"^Transformer sizing$|^Power consumption for wire sizing$"),
    ("모터 토크", "Torque motor", "", r"^Torque motor$|^Torque$|^Torque motor nominal"),
    ("구동 시간", "Running time", "",
     r"^Running Time \(Motor\)$|^Running time \(motor\)$|^Running time motor$|"
     r"^Running time$"),
    ("소음", "Sound power level", "dB",
     r"^Sound power level, motor$|^Sound power level$"),
]
QTY = ["voltage", "power", "power", "power", "torque", "time", "sound"]

# Type Overview 표에서 담을 열 — 요구 항목에 있는 것만.
COLS = [("공칭 구경", "DN", "mm", r"^DN$"),
        ("공칭 유량", "V'nom", "m³/h", r"^V'nom \[m³/h\]$"),
        ("유량계수 Kvs", "Kvs", "m³/h", r"^Kvs( \[m³/h\])?$"),
        ("최대 유량계수 Kvmax", "Kvmax", "m³/h", r"^Kvmax( \[m³/h\])?$"),
        ("압력 등급", "PN", "", r"^PN$")]


def sheet_path(tag):
    for suffix in ("en-us", "en-gb"):
        p = os.path.join(DATA, "raw", "belimo_%s_datasheet_%s.pdf" % (tag, suffix))
        if os.path.exists(p):
            return p
    return None


def _lines(path):
    """첫 쪽 글줄.

    ⚠ 이 문서는 값 안에 **줄바꿈 없는 빈칸**(U+00A0)을 쓴다. 그대로 두면
    'AC/DC\\xa024\\xa0V' 가 저장돼 화면·CSV 에서 깨진다.
    """
    import fitz
    doc = fitz.open(path)
    return [x.strip() for x in doc[0].get_text().replace(" ", " ").split("\n")]


def read_pairs(path):
    """요구 항목만 뽑는다. 모양이 둘이라 둘 다 읽는다.

      `라벨↵값`    대부분의 액추에이터·밸브
      `• 라벨 값`  미터·센서(22PE·22DT)는 머리 요약 목록에만 적는다
    """
    lines = _lines(path)
    out = {}
    for i, ln in enumerate(lines):
        for ko, en, _u, pat in ITEMS:
            if ko in out:
                continue
            if re.match(pat, ln):
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j]:
                        out[ko] = lines[j]
                        break
            elif ln.startswith("• "):
                m = re.match(pat.replace("$", r"\s+(.+)$"), ln[2:].strip())
                if m and m.lastindex:
                    out[ko] = m.group(m.lastindex).strip()
    return out


def read_type_overview(path):
    """첫 쪽의 Type Overview 표 → {형번: {열이름: 값}}.

    ⚠ 토큰 수로 열을 세면 안 된다 — `1 1/4` 처럼 한 칸이 낱말 둘인 데가 있다.
    머리글 두 줄(`Type DN Rp G V'nom … Kvs theor. PN` / `["] ["] [l/s] [l/min] [m³/h]`)의
    낱말 x 를 모아 열 중심으로 삼고, 값 낱말을 가장 가까운 열에 붙인다.
    """
    import fitz
    doc = fitz.open(path)
    page = doc[0]
    band = collections.defaultdict(list)
    for w in page.get_text("words"):
        band[round(w[1] / 3)].append(w)
    lines = []
    for k in sorted(band):
        ws = sorted(band[k], key=lambda w: w[0])
        lines.append((ws[0][1], ws))

    head = None
    for idx, (_y, ws) in enumerate(lines):
        if [w[4] for w in ws][:1] == ["Type"] and len(ws) >= 5:
            head = idx
            break
    if head is None:
        # 한 칸이 한 줄씩 내려앉은 판(D6..BL 등) — x 로 못 가르니 줄을 끊어 읽는다
        return read_type_overview_stacked(path)

    # ⚠ 열 이름으로 칸을 담으면 안 된다 — `V'nom` 이 셋(l/s·l/min·m³/h)이고 단위 줄에
    #   `[m³/h]` 가 V'nom·Kvs 두 번 나와, 이름을 열쇠로 쓰면 두 열이 한 칸으로 뭉친다
    #   (실제로 '1.5 3.2' 처럼 유량과 Kvs 가 붙어 나왔다). **인덱스로 담는다.**
    cols = []                       # [중심 x, 이름, 단위]
    for w in lines[head][1]:
        cx = (w[0] + w[2]) / 2
        # 'Kvs theor.' 처럼 한 열 이름이 낱말 둘인 데가 있다. 잣대는 **소문자 + 바짝 붙음**
        # 둘 다다. 소문자만 보면 'n(gl)' 같은 진짜 열을 잃고(그 값 3.2 가 PN 칸으로
        # 흘러들었다), 거리만 보면 'Rp'·'G' 처럼 좁은 열을 잃는다(DN 칸이 '15 1/2' 가 됐다).
        if cols and cx - cols[-1][0] < 40 and w[4][0].islower():
            continue
        cols.append([cx, w[4], ""])
    if head + 1 < len(lines):       # 단위 줄을 가장 가까운 열에 붙인다
        for w in lines[head + 1][1]:
            if not w[4].startswith("["):
                continue
            cx = (w[0] + w[2]) / 2
            j = min(range(len(cols)), key=lambda i: abs(cols[i][0] - cx))
            cols[j][2] = w[4]

    out = collections.OrderedDict()
    for _y, ws in lines[head + 1:]:
        first = ws[0][4]
        if not re.match(r"^[A-Z][A-Z0-9]{1,6}[A-Z0-9.+\-]*$", first) or len(ws) < 4:
            if out:
                break               # 표가 끝났다
            continue
        cells = collections.defaultdict(list)
        for w in ws[1:]:
            cx = (w[0] + w[2]) / 2
            j = min(range(len(cols)), key=lambda i: abs(cols[i][0] - cx))
            cells[j].append(w[4])
        out[first] = {col_key(cols, j): " ".join(v) for j, v in cells.items()}
    return out


def col_key(cols, j):
    """열 이름 — 같은 이름이 여럿이라 단위를 붙여 가른다 (`V'nom [m³/h]`)."""
    name, unit = cols[j][1], cols[j][2]
    return ("%s %s" % (name, unit)).strip()


def read_type_overview_stacked(path):
    """머리글도 값도 **한 줄에 한 칸씩** 내려앉은 Type overview (D6..BL·D6..N).

    x 좌표로 가를 열이 아예 없다 — 열 이름을 먼저 세고 값을 그 수만큼 끊는다.
    단위 줄(`[m³/h]`)은 열이 아니라 앞 열의 단위라 세지 않는다.
    """
    lines = _lines(path)
    try:
        i = next(k for k, l in enumerate(lines) if re.match(r"^Type overview$", l, re.I))
    except StopIteration:
        return {}
    cols, j = [], i + 1
    while j < len(lines):
        l = lines[j]
        if not l:
            j += 1
            continue
        if l.startswith("["):                 # 단위 줄 — 앞 열에 딸린다
            j += 1
            continue
        if re.match(r"^[A-Z][A-Z0-9]{1,6}[A-Z0-9.+\-]*$", l) and cols and l != "Type":
            break                             # 첫 형번이 나왔다
        cols.append(l)
        j += 1
    if len(cols) < 3:
        return {}
    vals = []
    while j < len(lines):
        l = lines[j]
        if not l:
            j += 1
            continue
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9./\- ]*$", l):
            break
        vals.append(l)
        j += 1
    n = len(cols)
    out = collections.OrderedDict()
    for k in range(0, len(vals) - n + 1, n):
        chunk = vals[k:k + n]
        if not re.match(r"^[A-Z][A-Z0-9]", chunk[0]):
            break
        out[chunk[0]] = dict(zip(cols[1:], chunk[1:]))
    return out


def build():
    tables = {}
    gaps = collections.defaultdict(list)
    for mid, tags in SHEETS.items():
        codes, files, cells, ov = [], [], collections.defaultdict(dict), {}
        for tag in tags:
            path = sheet_path(tag)
            if not path:
                gaps[mid].append("데이터시트를 못 찾았다: %s" % tag)
                continue
            code = tag.replace("_US", "").replace("..", "xx")
            codes.append(code)
            files.append(os.path.basename(path))
            for ko, val in read_pairs(path).items():
                cells[ko][code] = val
            for c, vals in read_type_overview(path).items():
                ov[c] = vals
        if not codes:
            continue
        rows, quants = [], []
        for (ko, en, unit, _p), q in zip(ITEMS, QTY):
            if ko not in cells:
                continue
            name = "%s · %s (%s)" % (ko, en, unit) if unit else "%s · %s" % (ko, en)
            rows.append([name] + [cells[ko].get(c, "") for c in codes])
            quants.append(q)
        t = []
        if rows:
            t.append({
                "title": "형번별 정격 — %s (데이터시트 %d건)" % (mid_name(mid), len(codes)),
                "page": 1, "orientation": "row", "kind": "rating",
                "header": ["항목"] + codes, "quantities": quants, "rows": rows,
                # ⚠ 대표 파일 이름을 지어내면 안 된다 — 대장(collected.json)에 없는 원문을
                #   인용하게 되고 다른 PC 에서 재현이 안 된다(시험이 잡는다).
                "source": files[0],
                "sourceNote": ("형번마다 데이터시트가 따로다 — 열 하나가 문서 하나다: %s"
                               % " · ".join(files)),
            })
        if ov:
            ocodes = list(ov)
            orows, oq = [], []
            for ko, en, unit, pat in COLS:
                key = next((k for k in set().union(*[set(v) for v in ov.values()])
                            if re.match(pat, k)), None)
                if not key:
                    continue
                vals = [ov[c].get(key, "") for c in ocodes]
                if not any(vals):
                    continue
                orows.append(["%s · %s (%s)" % (ko, en, unit) if unit
                              else "%s · %s" % (ko, en)] + vals)
                oq.append({"DN": "length", "V'nom": "flow", "Kvs": "flow",
                           "Kvmax": "flow", "PN": "pressure"}.get(en, ""))
            if orows:
                t.append({
                    "title": "형번별 정격 — %s Type Overview" % mid_name(mid),
                    "page": 1, "orientation": "row", "kind": "rating",
                    "header": ["항목"] + ocodes, "quantities": oq, "rows": orows,
                    "source": files[0],
                    "sourceNote": "Type Overview 표를 가진 문서: %s" % " · ".join(files),
                })
        if t:
            tables[mid] = (t, gaps[mid])
    return tables


def mid_name(mid):
    return mid.replace("belimo-", "").replace("-", " ").title()


def main(argv):
    run = "--run" in argv
    tables = build()
    tot = sum(len(x["rows"]) for t, _g in tables.values() for x in t)
    print("Belimo 정격 — 모델 %d건 · 표 %d개 · %d행"
          % (len(tables), sum(len(t) for t, _ in tables.values()), tot))
    for mid, (t, g) in sorted(tables.items()):
        print("  %-46s 표 %d · 형번 %d" % (mid, len(t), len(t[0]["header"]) - 1))
        for x in t[:1]:
            for r in x["rows"][:3]:
                print("       %-46s %s" % (r[0][:46], r[1:4]))
        for line in g:
            print("       ⚠ %s" % line)

    changed = 0
    for mid, (t, g) in list(tables.items()) + [
            (k, tables[v]) for k, v in ALSO.items() if v in tables]:
        p = os.path.join(DATA, "models", mid + ".json")
        if not os.path.exists(p):
            print("  ⚠ 모델이 없다: %s" % mid)
            continue
        m = json.load(io.open(p, encoding="utf-8"))
        keep = [x for x in (m.get("specTables") or [])
                if not str(x.get("source") or "").startswith("belimo_")]
        m["specTables"] = keep + t
        m["has"] = dict(m.get("has") or {}, spec=True)
        note = ("정격은 제품 데이터시트에서 왔다(통신 맵에는 없다). "
                "담은 것은 요구 항목(e16.actuator·e16.valve·e6.vav)뿐이다 — "
                "재질·보호등급·배선 규격은 계산에 안 들어가 담지 않았다.")
        gap = m.get("gap") or ""
        if isinstance(gap, str) and "제품 데이터시트에서 왔다" not in gap:
            m["gap"] = (gap + " " + note + (" " + " ".join(g) if g else "")).strip()
        changed += 1
        if run:
            with io.open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(m, f, ensure_ascii=False, indent=1)
                f.write("\n")
    print("\n모델 %d건에 붙인다" % changed)
    if not run:
        print("(미리보기다. 기록하려면 --run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
