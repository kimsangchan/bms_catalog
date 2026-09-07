# -*- coding: utf-8 -*-
"""Danfoss VLT HVAC Basic Drive FC 101 — 내장 RS-485(Modbus RTU) 취입.

  PYTHONIOENCODING=utf-8 python ingest_danfoss_fc101.py          바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_danfoss_fc101.py --run    실제로 기록한다

왜 이 제품인가
  현장 인버터 222대의 유력 후보다. 근거 둘 —
  ⑴ 포인트 이름 `INV_SPEED_FC101` 이 다른 `INV_*` 6점과 **같은 762회**다.
     한 대의 설비 태그라면 1회여야 하므로 SI 템플릿에 박힌 모델명이다.
  ⑵ 그 7점이 FC 101 판독 파라미터와 1:1 로 맞는다:
     DCLINK_VOLTAGE=16-30 · HEATsink TEMP=16-34 · OUT_CURRENT=16-14 ·
     OUT_VOLTAGE=16-12 · OUT_PWR=16-10 · RUN_TIME=15-01 · ACCUM_PWR=15-02.
  ⚠ 그래도 **확정은 아니다**. 나이아가라 Workbench 의 Vendor/Model 두 줄이 있어야 한다.

원문 두 건이 한 판을 이룬다
  MG18B502 Programming Guide  — 파라미터 본문(이름·범위·단위·기본값·선택지)
  MG18C702 Design Guide       — 코일 표(p91) · 고정 레지스터 표(p92) · 주소 규칙(p94)

★ 주소가 **표가 아니라 식**이다 (Design Guide p94 원문):
    "The parameter number is translated to Modbus as (10 x parameter number) decimal.
     Example: Reading parameter 3-12 ...: The holding register 3120 holds the value."
  즉 3-12 → 312 → 3120. 이 식을 그대로 적고, 레지스터 번호는 1부터 센다
  (p97: "Register addresses start at 0, that is, register 1 is addressed as 0" —
   번호와 전선 위 주소가 1 만큼 다르다는 뜻이라 addressBase 는 "1" 이다).
  32비트 파라미터는 레지스터를 둘 쓴다(3-14 → 3410·3411). 어느 것이 32비트인지는
  **부록 파라미터 목록(p108~124)의 Type 열**이 준다 — 데이터형·변환지수·기본값이 거기
  표로 다 있다. ⚠ 처음엔 본문만 보고 "문서에 없다" 고 gap 에 적었다. 틀렸다 —
  본문에 없으면 부록을 먼저 뒤진다.
"""
import collections
import io
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import schema as SC  # noqa: E402  — 범위 칸 판정의 정본

MODEL_ID = "danfoss-fc-101"
IFACE_ID = "modbus-rtu"
FAMILY = "Drive/Modbus"
PARAM_DOC = "MG18B502.pdf"
BUS_DOC = "MG18C702.pdf"

PNU = re.compile(r"^(\d{1,2}-\d{2})\s\s+(\S.*)$")
SEC = re.compile(r"^\d+\.\d+(?:\.\d+)?\s+(\d{1,2}-\d\*)\s+(.+)$")
BRACKET = re.compile(r"\[\s*([^\[\]]+?)\s*\]")
OPTION = re.compile(r"\[(\d+)\]\s*(\*?)\s*")
# '0 - 65535 V' · '0.01 - 1000.00 A' · '-4999 - 4999 ProcessCtrlUnit' · '0 - 0x7fffffff. h'
RANGE = re.compile(r"^(-?[\d.]+|0x[0-9a-fA-F.]+)\s*-\s*(-?[\d.]+|0x[0-9a-fA-F.]+)\s*(.*)$")


def norm(s):
    """리가처(ff fi)를 풀고 공백을 고른다 — 원문이 'o(ff)'·'0x7(ff)(ff)f' 로 나온다."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip()


def read_params(doc):
    """Programming Guide 본문 → 파라미터 블록. 줄 단위로 읽는다."""
    blocks, order, cur, sec = {}, [], None, None
    for i, page in enumerate(doc):
        for raw in unicodedata.normalize("NFKC", page.get_text()).split("\n"):
            ln = raw.rstrip()
            m = SEC.match(ln.strip())
            if m:
                sec = "%s %s" % (m.group(1), m.group(2).strip())
                continue
            m = PNU.match(ln)
            if m:
                cur = m.group(1)
                if cur not in blocks:
                    # 같은 파라미터가 쪽을 넘기며 머리글로 되풀이된다(15-06 이 그렇다).
                    # 처음 것만 세운다 — 나중 것을 별개로 만들면 개수가 부푼다.
                    blocks[cur] = {"name": m.group(2).strip(), "page": i + 1,
                                   "sec": sec, "body": []}
                    order.append(cur)
                continue
            if cur:
                blocks[cur]["body"].append(ln)
    return order, blocks


def parse_block(b):
    """블록 본문 → (종류, 기본값, 범위, 단위, 설명, 상태목록)."""
    body = norm(" ".join(b["body"]))
    kind = "range" if body.startswith("Range:") else (
        "option" if body.startswith("Option:") else "other")
    body = re.sub(r"^(Range:|Option:)\s*", "", body)
    body = re.sub(r"^Function:\s*", "", body)
    default = rng = unit = None
    states = []
    if kind == "option":
        opts = list(OPTION.finditer(body))
        desc = body[:opts[0].start()].strip() if opts else body
        for j, m in enumerate(opts):
            end = opts[j + 1].start() if j + 1 < len(opts) else len(body)
            label = body[m.end():end].strip()
            if m.group(2):
                default = m.group(1)
            # 설명문이 라벨 뒤에 이어 붙는다. 첫 문장 앞까지가 라벨이다.
            label = re.split(r"\.\s", label)[0].strip(" .")
            if label:
                states.append({"code": m.group(1), "label": label[:80]})
    else:
        m = BRACKET.search(body)
        if m:
            default = norm(body[:m.start()]).rstrip("*").strip() or None
            inner = norm(m.group(1))
            r = RANGE.match(inner)
            if r:
                rng = "%s - %s" % (r.group(1), r.group(2))
                unit = (r.group(3) or "").strip() or None
            else:
                rng = inner
            desc = body[m.end():].strip()
        else:
            desc = body
    if default:
        default = default.rstrip("*").strip() or None
    return kind, default, rng, unit, norm(desc), states


def read_param_list(doc):
    """부록 '파라미터 목록'(p108~) — 본문에 없는 것을 여기가 준다.

    ⚠ 처음엔 이 표를 못 보고 "어느 파라미터가 32비트인지 문서에 없다" 고 gap 에
      적었다. **틀렸다.** 본문(3장)은 이름·범위·설명만 주고, 데이터형·변환지수·
      기본값은 부록이 표로 준다. 본문만 읽고 '없다'고 단정하지 말 것.

    열: Par. No. # | Parameter description | Default value | 2-set-up |
        Change during operation | Conversion index | Type
    """
    rows, factors, types = {}, {}, {}
    for page in doc:
        for t in page.find_tables().tables:
            data = [[norm(c or "") for c in r] for r in t.extract()]
            if not data or not data[0]:
                continue
            head = data[0]
            if head[0].startswith("Conv. index"):
                # 변환지수 → 배수 (p107). 10의 거듭제곱이 아닌 것도 있다(74 → 3600)
                for idx, fac in zip(head[1:], data[1][1:]):
                    factors[idx] = fac
            elif head[:1] == ["Data type"]:
                for r in data[1:]:
                    if len(r) >= 3:
                        types[r[2]] = r[1]
            elif head[0].startswith("Par. No."):
                for r in data[1:]:
                    if re.fullmatch(r"\d{1,2}-\d{2}", r[0] or ""):
                        rows[r[0]] = {"name": r[1], "default": r[2], "setup": r[3],
                                      "changeDuringOp": r[4], "conv": r[5],
                                      "type": r[6] if len(r) > 6 else ""}
    return rows, factors, types


def read_coils(doc):
    """Design Guide p91 코일 표 3개 — 대역 · 상태어 비트 · 제어어 비트."""
    page = doc[90]
    out = {"ranges": [], "status": [], "control": []}
    for t in page.find_tables().tables:
        data = [[norm(c or "") for c in r] for r in t.extract()]
        head = data[0]
        if head[:1] == ["Coil number"]:
            out["ranges"] = [r for r in data[1:] if r[0]]
        elif head[:1] == ["Coil"]:
            rows = [r for r in data[1:] if r[0].isdigit()]
            if rows:
                key = "status" if int(rows[0][0]) >= 33 else "control"
                out[key].extend(rows)
    return out


def read_bus_registers(doc):
    """Design Guide p92 고정 레지스터 표 (40001~)."""
    for t in doc[91].find_tables().tables:
        data = [[norm(c or "") for c in r] for r in t.extract()]
        if data[0][:1] == ["Bus address"]:
            return [r for r in data[1:] if r and r[0].isdigit()]
    return []


BITS = {"Int8": 8, "Uint8": 8, "Int16": 16, "Uint16": 16, "N2": 16, "V2": 16,
        "Int32": 32, "Uint32": 32}


def type_bits(t):
    """부록 'Type' 열 → 레지스터 폭. VisStr[n] 은 문자열이라 폭을 매기지 않는다."""
    return BITS.get((t or "").strip())


def conv_scale(idx, factors):
    """변환지수 → 배수. 공학값 = 원시값 × 배수 (원문 p97: 1-24 에 738 = 7.38 A)."""
    raw = factors.get((idx or "").strip())
    if not raw:
        return None
    if "/" in raw:
        a, b = raw.split("/", 1)
        try:
            return float(a) / float(b)
        except ValueError:
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def build(order, blocks, coils, busregs, plist, factors):
    pts = []

    def add(common, block, prov):
        pts.append({"common": common, "blocks": block, "provenance": dict(
            {"family": FAMILY, "status": "extracted", "interfaceId": IFACE_ID}, **prov)})

    # 본문에 없고 부록에만 있는 파라미터도 세운다(1-11·14-61 이 그렇다).
    order = list(order) + [p for p in plist if p not in blocks]
    for pnu in order:
        b = blocks.get(pnu)
        app = plist.get(pnu) or {}
        if b is None:
            b = {"name": app.get("name") or pnu, "page": 108, "sec": None, "body": []}
        kind, default, rng, unit, desc, states = parse_block(b)
        default = app.get("default") or default
        common = {"name": b["name"], "shortName": pnu}
        if b["sec"]:
            common["group"] = b["sec"]
        if unit:
            common["unitSI"] = common["unitSIRaw"] = unit
        if rng:
            # ⚠ 사전이 정한 모양은 문자열이 아니라 {raw, min?, max?} 다.
            #   처음에 문자열로 넣었다가 대조대(verify_points.row_of)가 터졌다 —
            #   validate 는 이걸 안 잡는다. 판정은 schema.parse_range 가 정본이다.
            common["range"] = SC.parse_range(rng) or {"raw": rng}
        if states:
            common["states"] = states
        if desc:
            common["note"] = desc[:400]
        gaps = []
        if default:
            # 기본값을 담을 자리가 스키마에 없다 — 지어내지 말고 원문 칸에 남긴다
            gaps.append("기본값 '%s' 은 sourceColumns 에만 있다 — 스키마에 기본값 자리가 없다"
                        % default)
        reg = int(pnu.replace("-", "")) * 10
        mod = {"address": reg, "addressBase": "1", "refClass": "holding-register"}
        bits = type_bits(app.get("type"))
        if bits:
            mod["bits"] = bits
        t = (app.get("type") or "")
        if t.startswith("Uint"):
            mod["dataType"] = "Unsigned"
        elif t.startswith("Int"):
            mod["dataType"] = "Signed"
        sc = conv_scale(app.get("conv"), factors)
        if sc is not None and sc != 1:
            mod["scale"], mod["scaleRaw"] = sc, "conv index %s" % app["conv"]
        add(common,
            {"modbus": mod},
            {"sourceFile": PARAM_DOC, "sourcePage": b["page"],
             "sourceColumns": {"파라미터 번호": pnu, "이름": b["name"],
                               "Range/Option": kind,
                               "기본값": default or "-", "범위": rng or "-",
                               "단위": unit or "-", "절": b["sec"] or "-",
                               "Type(부록)": app.get("type") or "-",
                               "Conversion index(부록)": app.get("conv") or "-",
                               "2-set-up(부록)": app.get("setup") or "-",
                               "Change during operation(부록)":
                                   app.get("changeDuringOp") or "-"},
             "srcRef": "주소 = 파라미터번호 x 10 (Design Guide %s p94)" % BUS_DOC,
             **({"gaps": gaps} if gaps else {})})

    def coil_name(zero, one):
        """비트 이름은 **부정이 아닌 쪽**을 쓴다.

        원문은 0/1 의 뜻만 준다('03 | DC brake | No DC brake'). 1쪽을 그대로 이름으로
        쓰면 'No DC brake' 라는 점이 생겨 기능이 뒤집혀 읽힌다. 어느 쪽도 부정이
        아니거나 둘 다면 1쪽을 쓴다 — 지어내지 않고 원문 두 칸은 states 에 그대로 남는다.
        """
        neg = re.compile(r"^(no|not)\b|\bnot\b", re.I)
        z, o = bool(neg.search(zero or "")), bool(neg.search(one or ""))
        if z and not o:
            return one
        if o and not z:
            return zero
        return one or zero

    DASH = ("", "-", "–", "—")
    for row in coils["control"] + coils["status"]:
        num = int(row[0])
        zero, one = row[1], row[2]
        if zero in DASH and one in DASH:
            continue          # 원문이 뜻을 안 준 비트다(코일 15) — 만들지 않는다
        name = coil_name(zero, one)
        states = [{"code": c, "label": v} for c, v in (("0", zero), ("1", one))
                  if v not in DASH]
        add({"name": name, "shortName": "coil %d" % num,
             "group": "코일 %s" % ("33-48 상태어" if num >= 33 else "01-16 제어어"),
             "states": states,
             "readWrite": "R" if num >= 33 else "W"},
            {"modbus": {"address": num, "addressBase": "1", "refClass": "coil"}},
            {"sourceFile": BUS_DOC, "sourcePage": 91,
             "sourceColumns": {"Coil": row[0], "0": zero, "1": one}})

    for row in coils["ranges"]:
        first = re.split(r"[–-]", row[0])[0]
        if not first.isdigit() or int(first) in (1, 33, 66):
            continue     # 1-16·33-48 은 위에서 비트별로 세웠고 66~ 은 예약이다
        add({"name": row[1], "shortName": "coil %s" % row[0],
             "group": "코일 대역", "readWrite": "W" if "Master" in row[2] else "R",
             "note": "코일 %s 를 16비트 값 하나로 쓴다(%s). 비트별 의미가 아니라 "
                     "값이라 한 점으로 둔다." % (row[0], row[2])},
            {"modbus": {"address": int(first), "addressBase": "1", "refClass": "coil"}},
            {"sourceFile": BUS_DOC, "sourcePage": 91,
             "sourceColumns": {"Coil number": row[0], "Description": row[1],
                               "Signal direction": row[2]},
             "gaps": ["16비트 값이 코일 대역에 걸쳐 있다 — 스키마에 '코일 n개로 이루어진 "
                      "레지스터'를 담을 자리가 없어 시작 코일 하나로 뒀다."]})

    for row in busregs:
        content, access = row[3], row[4]
        if content in ("Reserved", "Free"):
            continue
        common = {"name": content, "shortName": row[2], "group": "고정 레지스터",
                  "note": row[5]}
        rw = {"Read only": "R", "Read/Write": "R/W"}.get(access)
        if rw:
            common["readWrite"] = rw
        add(common,
            {"modbus": {"address": int(row[1]), "addressBase": "1",
                        "refClass": "holding-register"}},
            {"sourceFile": BUS_DOC, "sourcePage": 92,
             "sourceColumns": {"Bus address": row[0], "Bus register": row[1],
                               "PLC register": row[2], "Content": content,
                               "Access": access}})
    return pts


def crosscheck(doc, order, blocks):
    """표 인식과 **다른 경로**로 다시 읽어 맞춘다 — 낱말 좌표층으로 이름을 되짚는다.

    같은 get_text() 줄 결과를 다시 세면 같은 맹점을 그대로 통과한다.
    """
    # ⚠ **그 파라미터가 정의된 쪽에서만** 되짚는다. 문서 곳곳에 같은 번호가
    #   딴 뜻으로 나온다 — p10 의 사양표에 '0-10 V DC' 가 있어 0-10 Active Set-up
    #   과 부딪혔고, p18 의 요약 목록은 이름을 줄여 적는다('6-22 T54 Low Current').
    #   문서 전체에서 첫 등장을 집으면 그런 것들이 전부 불일치로 잡혀 대조가 거짓말을 한다.
    bypage = collections.defaultdict(set)
    for pnu, b in blocks.items():
        bypage[b["page"]].add(pnu)
    seen = {}
    for pg, pnus in bypage.items():
        rows = collections.defaultdict(list)
        for w in doc[pg - 1].get_text("words"):   # (x0,y0,x1,y1,word,block,line,no)
            rows[round(w[1] / 3)].append(w)
        for key in rows:
            ws = sorted(rows[key], key=lambda w: w[0])
            if not ws:
                continue
            head = unicodedata.normalize("NFKC", ws[0][4])
            if head in pnus and len(ws) > 1:
                seen.setdefault(head, unicodedata.normalize("NFKC", ws[1][4]))
    both = same = 0
    diff = []
    for pnu in order:
        if pnu in seen:
            both += 1
            first = blocks[pnu]["name"].split()[0]
            if seen[pnu].strip(" .,") == first.strip(" .,"):
                same += 1
            elif len(diff) < 8:
                diff.append("%s: 줄=%s / 낱말=%s" % (pnu, first, seen[pnu]))
    return {"method": "낱말 좌표층으로 파라미터 번호+이름 첫 낱말을 다시 읽어 맞췄다",
            "total": len(order), "both": both, "same": same,
            "rate": round(same / both, 4) if both else 0.0, "diff": diff}


def main(argv):
    import fitz
    run = "--run" in argv
    pdoc = fitz.open(os.path.join(DATA, "raw", PARAM_DOC))
    bdoc = fitz.open(os.path.join(DATA, "raw", BUS_DOC))
    order, blocks = read_params(pdoc)
    plist, factors, _types = read_param_list(pdoc)
    coils = read_coils(bdoc)
    busregs = read_bus_registers(bdoc)
    pts = build(order, blocks, coils, busregs, plist, factors)
    cc = crosscheck(pdoc, order, blocks)

    print("파라미터 %d · 코일 %d · 고정 레지스터 %d  -> 합계 %d점"
          % (len(order),
             len(coils["control"]) + len(coils["status"]) + len(coils["ranges"]),
             len(busregs), len(pts)))
    print("  단위 %d · 범위 %d · 상태 %d · 설명 %d"
          % (sum(1 for p in pts if p["common"].get("unitSI")),
             sum(1 for p in pts if p["common"].get("range")),
             sum(1 for p in pts if p["common"].get("states")),
             sum(1 for p in pts if p["common"].get("note"))))
    print("  교차 대조 %d/%d = %.1f%%" % (cc["same"], cc["both"], 100 * cc["rate"]))
    for d in cc["diff"]:
        print("     [주의]", d)

    mp = os.path.join(DATA, "models", MODEL_ID + ".json")
    model = json.load(io.open(mp, encoding="utf-8"))
    iface = {
        "id": IFACE_ID, "label": "내장 RS-485 (Modbus RTU)",
        "family": FAMILY, "protocols": ["modbus"],
        "sourceFile": PARAM_DOC,
        "sourcePages": sorted({p["provenance"]["sourcePage"] for p in pts}),
        "pointCount": len(pts), "appliesTo": ["FC 101"], "status": "extracted",
        # 이 문서 본문에는 인쇄 쪽번호가 아예 없다(머리글이 '3.12.3 16-3* Drive Status').
        # 밝히지 않으면 대조대가 인쇄번호로 알고 다시 찾아 엉뚱한 쪽을 띄운다.
        "pageBase": "pdf",
        "note": ("파라미터는 Programming Guide %s 본문에서, 코일·고정 레지스터는 "
                 "Design Guide %s p91~92 표에서 왔다. **파라미터 주소는 표가 아니라 "
                 "식이다** — 주소 = 파라미터번호 x 10 (p94: '3-12 -> holding register "
                 "3120'). 레지스터 번호는 1부터 세고, 전선 위 주소는 그보다 1 작다"
                 "(p97). 옵션 카드 없이 본체 RS-485 만으로 열린다."
                 % (PARAM_DOC, BUS_DOC)),
        "crosscheck": cc,
        "gaps": ["⚠ **원문 두 곳이 어긋난다.** 부록 파라미터 목록은 3-14 를 Int16(16비트)로 "
                 "적는데, Design Guide p94 의 예는 같은 3-14 를 '(32 bit)' 라며 레지스터 "
                 "둘(3410·3411)을 쓴다고 한다. 폭은 **부록 Type 열**을 따랐다(체계적 출처라서). "
                 "현장에서 32비트로 읽히면 부록이 아니라 예가 맞는 것이다.",
                 "기본값은 sourceColumns 에만 있다 — 스키마에 기본값 자리가 없다. "
                 "'ExpressionLimit'(용량따라 다름)처럼 수치가 아닌 것도 섞여 있다.",
                 "읽기/쓰기 구분은 코일·고정 레지스터에만 있다. 파라미터 쪽은 원문에 "
                 "R/W 열이 없어 비웠다 — '판독(16-**)은 읽기 전용'은 규약이지 문서 기재가 아니다.",
                 "코일 17-32·49-64 는 16비트 값이 코일 대역에 걸친 것이라 시작 코일 "
                 "하나로 뒀다(스키마에 담을 자리가 없다)."],
        "points": pts,
    }
    others = [i for i in (model.get("interfaces") or []) if i["id"] != IFACE_ID]
    model["interfaces"] = others + [iface]
    model["has"] = dict(model.get("has") or {}, points=True)
    model["crosscheck"] = cc
    model["summary"] = ("팬·펌프용 HVAC 전용 인버터. 정격은 Fact Sheet·전기데이터, "
                        "오브젝트는 내장 RS-485 Modbus %d점." % len(pts))
    if not run:
        print("\n(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n-> %s  (판 %d · %d점)"
          % (os.path.relpath(mp, HERE), len(model["interfaces"]), len(pts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
