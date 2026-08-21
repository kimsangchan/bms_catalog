# -*- coding: utf-8 -*-
"""JCI YKN2Open 게이트웨이 포인트 리스트 → point-schema 구조. (9번째 계통)

계통이 무엇인가
  앞의 8계통은 전부 **장비가 직접 내보내는** 목록이었다. 이것은 다르다 —
  YKN2Open 은 FieldServer QuickServer 를 담은 **BMS 액세서리 키트**이고,
  장비의 JCI Metasys N2(RS-485)를 BACnet/IP 또는 Modbus TCP/IP 로 **바꿔 준다**
  (원문 4쪽: kit S606791244 = FS-QS-1010-0122 BACnet/IP, S606791245 =
  FS-QS-1010-0117 Modbus TCP/IP). 그래서 표가 벤더 포인트표가 아니라
  **게이트웨이 설정표** 모양이다 — 파서 넷이 다 못 잡던 이유다.

  덮는 장비는 원문 4쪽이 밝힌다: "cold units and heat pumps from Roomtop
  (RTC-RTH-L), ACTIVA Rooftop, Large ACTIVA Rooftop, VITALITY VAC/VAH/VCH-VIR
  of R410A equipped with the YKN2Open control". 게이트웨이 한 대에 장비
  **최대 5대**(원문 7쪽 A) — 그래서 노드가 MBPSrv1~5 · VirtualDev11~15 다.

표 다섯 종 — 둘만 포인트다
  ① Modbus variables (9쪽, 37행)   ★ 포인트
       N2Open-Type | N2Address | Map Descriptor Name | Modbus Address
       | Modbus Scale | Description | Value/Units | Range
  ② Bacnet variables (11·12쪽, 49행) ★ 포인트
       Object-name | Object-type | Object-type-text | Object-instance
       | Description | State-text-reference | Unit-code | Value/Units | Range
  ③ Map Descriptor 설정표 (10·13쪽)  — 게이트웨이 내부 배선(Server/Passive,
       Data Array, Node Name). 장비 포인트가 아니다.
  ④ Node 주소표 (10·13쪽)           — MBPSrv1~5 / VirtualDev11~15 통신 노드.
  ⑤ Alarms (13쪽, 24행)             — 코드표. 포인트가 아니라 **Error Code
       포인트의 값 집합**이라 states 로 풀어 붙인다(아래 함정 4).

이 계통에서 실제로 밟은 함정 (전부 원문 코드포인트로 확인했다)
  1. **하이픈이 세 종류다.** 칸 안에서 줄바꿈된 낱말은 `U+2010 HYPHEN` + 개행으로
     끊기고('Suction Temper‐\\nature 1'), 열거값 구분자는 `U+2011 NON-BREAKING
     HYPHEN` 이다('0 ‑ OFF'). ASCII '-' 는 진짜 이름의 일부다('Close-Open').
     실측 U+2010 46개가 **전부** 개행 앞이고 예외 0 — 그래서 짐작으로 고르지
     않고 코드포인트로 가른다. 한 벌로 뭉개면 'Close-Open' 이 'CloseOpen' 이
     되거나 이름이 'Temper ature' 로 굳는다(아래첨자 오염 113건과 같은 사고다).
  2. **'Range' 열이 세 가지를 담는다.** 수치 범위('-50 min / 160 max'·'0-100')
     · 열거값('0 ‑ OFF 1 ‑ Cool 2 ‑ Heat …') · 참조 문장('Alarm code (11 a 46).
     See alarm table'). 전부 rangeSI 로 밀면 Mode 포인트의 운전모드 5종이 범위로
     둔갑한다. 모양을 보고 states·rangeSI·note 로 가른다.
  3. **'Value / Units' 열도 단위가 아닐 때가 있다.** '°C'·'%'·'Hours' 는 단위지만
     'Integer'·'Auto/Manual'·'Off/On'·'--' 는 값의 성격이다. 단위 자리에 넣으면
     단위 사전이 오염된다 — 단위로 인정되는 것만 unitSI 로 올리고 나머지는
     원표기(unitSIRaw)만 남긴다.
  4. **Error Code 의 값 집합이 다른 표에 있다.** AI 31 'Error Code' 의 Range 가
     "Alarm code (11 a 46). See alarm table" 이라고 가리키고, 13쪽 Alarms 표가
     그 표다. 참조를 풀어 states 로 붙이되 statesRef 를 지우지 않는다(어디서
     왔는지 추적). ⚠ 표에는 11~46 말고 **91~99(Thermostat)도 있다** — 원문이
     밝힌 범위와 어긋나므로 전부 싣고 그 사실을 gap 에 적는다.
  5. **두 표는 같은 포인트를 두 번 적은 것이다.** Modbus 37행과 BACnet 49행을
     더하면 86 이지만 실제 포인트는 49 다. 다만 **문서가 'AO 는 AV 다'라고
     말하지는 않는다** — 그래서 타입 대응표를 지어내지 않고 **설명문 + 번호가
     둘 다 같을 때만** 한 포인트로 합친다. 안 맞으면 합치지 않고 gap 에 적는다.
  6. **배율 표기가 두 가지다.** 읽기(AI)는 '/10', 쓰기(AO)는 'x /10' 이다.
     '/10' 은 방향이 명시적이라 scale=0.1 로 올리지만, 'x /10' 은 곱셈·나눗셈
     기호가 함께 있어 문서가 방향을 확정하지 않는다 — scaleRaw 만 남기고 수치는
     비운다(point-schema modbus.scale: "방향을 틀리면 시뮬레이터가 100배 틀린다").

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_ykn2open.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_ykn2open.py --parse <문서ID|파일경로>
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SOURCE = "jci-york-bas-points"

sys.path.insert(0, HERE)
import schema as S      # noqa: E402

FAMILY = "YKN2Open"

# 칸 안 줄바꿈 하이픈 (U+2010 + 개행) — 낱말이 끊긴 자리다. 붙인다.
WRAP_HYPHEN = re.compile("‐\\s*\n\\s*")
# 열거값 구분자 (U+2011) — 진짜 내용이다. 지우지 않는다.
ENUM_DASH = "‑"
# '0 ‑ OFF 1 ‑ Cool …' · '0-100' 과 구별해야 하므로 구분자를 U+2011 로 못박는다
# ⚠ 항목 경계를 줄바꿈으로 잡으면 안 된다 — 원문이 **양쪽으로** 어긋난다.
#   9쪽은 항목을 붙여 쓰고('0 ‑ OFF (forced)1 ‑ ON. Reset'), 12쪽은 라벨 가운데서
#   줄을 바꾼다('1 ‑ Fan manual\ncontinuo'). 줄바꿈을 경계로 삼았더니 12쪽 두 행이
#   조용히 열거가 아니게 되어 비고로 샜다. 경계는 **다음 코드**뿐이다.
ENUM_ITEM = re.compile(r"(\d+)\s*[%s-]\s*([^\d].*?)(?=\s*\d+\s*[%s-]|\s*$)"
                       % (ENUM_DASH, ENUM_DASH), re.S)
# '-50 min / 160 max' · '10min 32max' · '0-100' · '0-50000'
RANGE_MINMAX = re.compile(r"^(-?[\d.]+)\s*min\s*/?\s*(-?[\d.]+)\s*max$", re.I)
RANGE_DASH = re.compile(r"^(-?[\d.]+)\s*-\s*(-?[\d.]+)$")
# 단위로 인정하는 것만. 문서에 실제로 나온 것 그대로다 — 사전을 여기서 넓히지 않는다
UNIT_OK = {"°c": "°C", "%": "%", "hours": "h"}
# 값이 아니라 '없음'을 뜻하는 셀 (point-schema rules.emptyMeansAbsent)
ABSENT = {"", "-", "--", "—", "_", "n/a", "na", "none"}

# BACnet 표준 오브젝트 타입 코드 — 문서가 Object-type(숫자)과 Object-type-text
# (이름)를 **둘 다** 준다. 둘이 어긋나면 지어내지 않고 gap 에 적는다.
BAC_CODE = {0: "AI", 1: "AO", 2: "AV", 3: "BI", 4: "BO", 5: "BV",
            13: "MSI", 14: "MSO", 19: "MSV"}

COLMAP_MB = [("n2Type", r"^N2OpenType$"), ("n2Addr", r"^N2Address$"),
             ("mapDesc", r"^MapDescriptorName$"), ("mbAddr", r"^ModbusAddress$"),
             ("mbScale", r"^ModbusScale$"), ("desc", r"^Description$"),
             ("units", r"^Value/?Units$"), ("range", r"^Range$")]
COLMAP_BAC = [("objName", r"^Object-?name$"), ("objTypeText", r"^Object-?type-?text$"),
              ("objType", r"^Object-?type$"), ("instance", r"^Object-?instance$"),
              ("desc", r"^Description$"), ("statesRef", r"^State-?text-?reference$"),
              ("unitCode", r"^Unit-?code$"), ("units", r"^Value/?Units$"),
              ("range", r"^Range$")]


def docs():
    """이 파서가 훑을 문서 목록 — 정본은 대장(collected.json)이다."""
    import collect
    return collect.files_of(SOURCE)


def clean(v):
    """조판 아티팩트를 지운다 — 게이트를 걸기 **전에** 해야 한다.

    ⑴ 줄바꿈 하이픈(U+2010+개행)은 낱말이 끊긴 자리라 **붙인다**.
    ⑵ 남은 개행은 칸 안 줄바꿈이라 공백으로.
    ⑶ 표 인식이 밑줄 글리프를 가장자리 조각으로 뱉는다('CMDAI001 _ _') — 뗀다.
    U+2011(열거 구분자)과 ASCII '-'(이름의 일부)는 **손대지 않는다**(함정 1).
    """
    t = WRAP_HYPHEN.sub("", str(v or ""))
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^[_\s]+|[_\s]+$", "", t)
    return t.strip()


def squeeze(h):
    """머리글에서 공백과 밑줄 조각을 지운다 — 쪼개진 머리글을 붙여 알아보려고.

    ⚠ 밑줄은 **낱말 가운데**에도 박힌다. 'Modbus Ad‐\\n_\\ndress' 가 clean() 을
    거치면 'Modbus Ad_ dress' 라 공백만 지워서는 'ModbusAddress' 가 안 된다.
    이걸 놓쳐서 Modbus 표 37행을 통째로 못 읽고 BACnet 49행만 남았다 — 주소가
    세 프로토콜에서 하나로 줄어든 줄도 모르게 지나갈 뻔했다.
    """
    return re.sub(r"[\s_]+", "", clean(h))


def header_map(head, colmap):
    """머리글 → ({우리이름: 열번호}, 못 알아본 열)."""
    out, unknown = {"_head": {}}, {}
    for i, h in enumerate(head):
        h = clean(h)
        if not h:
            continue
        sq = squeeze(h)
        for name, pat in colmap:
            if name in out:
                continue
            if re.search(pat, sq, re.I):
                out[name] = i
                out["_head"][name] = h
                break
        else:
            unknown[h[:40]] = i
    return out, unknown


def _headname(cmap, key):
    """sourceColumns 의 열쇠로 쓸 열 이름. 밑줄 조각은 뗀다.

    표 인식이 밑줄 글리프를 낱말 사이에 흘려 'Map Descrip_ tor Name' 으로 준다.
    그대로 열쇠에 쓰면 원문에 없는 이름이 근거로 남는다.
    """
    h = (cmap.get("_head") or {}).get(key)
    if not h:
        return h
    return re.sub(r"\s{2,}", " ", re.sub(r"_+\s*", "", h)).strip()


def kind_of(head_cells):
    """표 머리글 → 'modbus' · 'bacnet' · None(포인트 표가 아니다).

    ⚠ 'Map Descriptor Name' 은 **양쪽에 다 나온다** — 9쪽 포인트 표의 한 열이면서
    10·13쪽 게이트웨이 설정표의 첫 열이기도 하다. 그래서 그 낱말로 가르면
    설정표가 포인트로 들어온다. 포인트 표에만 있는 열로 판정한다.
    """
    sq = squeeze(" | ".join(c or "" for c in head_cells))
    if re.search(r"N2OpenType", sq, re.I) and re.search(r"ModbusAddress", sq, re.I):
        return "modbus"
    if re.search(r"Object-?instance", sq, re.I) and re.search(r"Object-?name", sq, re.I):
        return "bacnet"
    return None


def states_of(text):
    """열거값 문장 → [{code,label}]. 열거가 아니면 빈 목록.

    '0 ‑ OFF\\n1 ‑ Cool\\n2 ‑ Heat\\n3 ‑ Auto\\n5 ‑ Emerg Heat' →
    [{'0','OFF'},{'1','Cool'},…]. 구분자가 U+2011 이라 '0-100'(범위)과 섞이지
    않는다 — 다만 '1-Fan manual continuo' 처럼 원문이 ASCII '-' 로 흔들리는
    행이 있어 **U+2011 이 한 번이라도 나온 칸에서만** ASCII '-' 도 받아 준다.
    """
    raw = str(text or "")
    if ENUM_DASH not in raw:
        return []
    out = []
    for m in ENUM_ITEM.finditer(raw):
        label = re.sub(r"\s+", " ", m.group(2)).strip(" .")
        if label:
            out.append({"code": m.group(1), "label": label})
    return out if len(out) >= 2 else []


def range_of(text):
    """수치 범위 칸 → {min,max}. 범위가 아니면 None."""
    t = clean(text)
    for pat in (RANGE_MINMAX, RANGE_DASH):
        m = pat.match(t)
        if m:
            return {"min": float(m.group(1)), "max": float(m.group(2))}
    # '10min 32max' — 슬래시 없이 붙여 쓴 판
    m = re.match(r"^(-?[\d.]+)\s*min\s+(-?[\d.]+)\s*max$", t, re.I)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(2))}
    return None


def _num(v):
    m = re.match(r"^-?\d+$", clean(v))
    return int(clean(v)) if m else None


def alarm_table(doc):
    """13쪽 Alarms 코드표 → ([{code,label}], 위치 열이 있었나).

    Error Code 포인트가 "See alarm table" 로 가리키는 그 표다(함정 4).
    머리글이 'Number | Alarm | Location' 인 표만 받는다.
    """
    out, had_loc = [], False
    for pg in doc:
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            hi = next((i for i, r in enumerate(data)
                       if re.search(r"^Number$", squeeze(r[0] if r else ""), re.I)
                       and any(re.search(r"^Alarm$", squeeze(c or ""), re.I) for c in r)), None)
            if hi is None:
                continue
            had_loc = any(re.search(r"^Location$", squeeze(c or ""), re.I) for c in data[hi])
            for r in data[hi + 1:]:
                code, label = clean(r[0] if r else ""), clean(r[1] if len(r) > 1 else "")
                if re.match(r"^\d+$", code) and label:
                    out.append({"code": code, "label": label})
    return out, had_loc


def row_to_point(row, cmap, kind, fname, page):
    """행 하나 → 포인트 레코드. 포인트가 아니면 (None, 사유)."""
    def cell(key):
        i = cmap.get(key)
        return clean(row[i]) if i is not None and i < len(row) else ""

    def raw(key):
        i = cmap.get(key)
        return str(row[i] or "") if i is not None and i < len(row) else ""

    desc = cell("desc")
    if not desc:
        return None, "reserved"
    if squeeze(desc).lower() == "description":          # 머리글이 되풀이된 행
        return None, "banner"

    rec = {"common": {}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": FAMILY}}
    src, gaps = {}, []
    rec["common"]["name"] = desc

    # ── Range 열 — 세 가지가 섞여 있다(함정 2) ───────────────────────────
    rng_raw = raw("range")
    if clean(rng_raw).lower() not in ABSENT:
        sts = states_of(rng_raw)
        rg = range_of(rng_raw)
        if sts:
            rec["common"]["states"] = sts
        elif rg:
            rec["common"]["rangeSI"] = rg
        else:
            rec["common"]["note"] = clean(rng_raw)
            # ⚠ 열거 구분자가 있는데 못 풀었으면 조용히 비고로 흘리지 않는다 —
            #   실제로 12쪽 두 행이 그렇게 샜고, 합칠 때 반대쪽이 채워 줘서
            #   결과만 보면 멀쩡해 보였다.
            if ENUM_DASH in rng_raw:
                gaps.append("states — 열거 구분자(U+2011)가 있는데 항목을 못 갈랐다: %r"
                            % clean(rng_raw)[:60])
        src[_headname(cmap, "range") or "Range"] = clean(rng_raw)

    # ── Value / Units 열 — 단위가 아닐 때가 있다(함정 3) ─────────────────
    u = cell("units")
    if u.lower() not in ABSENT:
        rec["common"]["unitSIRaw"] = u
        if u.lower() in UNIT_OK:
            rec["common"]["unitSI"] = UNIT_OK[u.lower()]

    if kind == "modbus":
        n2t, n2a = cell("n2Type"), _num(cell("n2Addr"))
        if n2t and n2a is not None:
            # N2Open 종별 표기는 'AI/AO/DI/DO' 다. point-schema n2.pointType 은
            # ADF·ADI·BD 만 받으므로 **강제로 맞추지 않는다** — 원표기를 남긴다.
            rec["blocks"]["n2"] = {"address": n2a}
            src[_headname(cmap, "n2Type") or "N2Open-Type"] = n2t
            gaps.append("n2.pointType — 문서 표기가 'AI/AO/DI/DO'(N2Open 종별)라 "
                        "사전값(ADF·ADI·BD)에 없다. 원표기는 sourceColumns 에 뒀다")
        mba = _num(cell("mbAddr"))
        if mba is not None:
            mb = {"address": mba,
                  # ⚠ 0-base/1-base 를 문서가 밝히지 않는다. 값이 0xxxx·3xxxx·4xxxx
                  #   대역(Modbus 엔티티 번호)이지만 그것과 base 는 별개다.
                  "addressBase": "unknown"}
            lead = clean(cell("mbAddr"))[:1]
            mb["refClass"] = {"0": "coil", "1": "discrete-input",
                              "3": "input-register", "4": "holding-register"}.get(lead) or None
            if not mb["refClass"]:
                mb.pop("refClass")
                gaps.append("modbus.refClass — 주소 %s 가 알려진 대역(0/1/3/4xxxx)이 아니다"
                            % mba)
            sc = cell("mbScale")
            if sc.lower() not in ABSENT:
                mb["scaleRaw"] = sc
                if re.fullmatch(r"/\s*(\d+)", sc):
                    mb["scale"] = 1.0 / float(re.sub(r"[^\d]", "", sc))
                else:
                    # 'x /10' — 곱셈·나눗셈 기호가 함께 있다(함정 6)
                    gaps.append("modbus.scale — 배율 원표기 %r 이 곱셈·나눗셈 기호를 "
                                "함께 써 방향을 확정하지 못했다. 수치로 올리지 않았다" % sc)
            rec["blocks"]["modbus"] = mb
        md = cell("mapDesc")
        if md:
            # FieldServer 의 Map Descriptor 이름('CMDAI001') — 게이트웨이가 이
            # 포인트를 부르는 식별자다. 사람이 읽는 이름이 아니므로 name 으로
            # 승격하지 않고 shortName 에 둔다.
            rec["common"]["shortName"] = md
            src[_headname(cmap, "mapDesc") or "Map Descriptor Name"] = md
    else:
        b = {}
        code = _num(cell("objType"))
        text = cell("objTypeText")
        by_code = BAC_CODE.get(code) if code is not None else None
        by_text = S.TYPE_LONG.get(re.sub(r"\s+", "_", text.lower())) if text else None
        if by_code and by_text and by_code != by_text:
            gaps.append("bacnet.objectType — 숫자 열(%s→%s)과 이름 열(%r→%s)이 어긋난다. "
                        "숫자를 따랐다" % (code, by_code, text, by_text))
        canon = by_code or by_text
        if canon in S.BACNET_TYPES:
            b["objectType"] = canon
        elif text:
            # 'Analog Value In/Out' 처럼 표준 이름이 아닌 표기 — 숫자가 정본이다
            gaps.append("bacnet.objectType — 이름 열 %r 이 표준 표기가 아니다" % text)
        inst = _num(cell("instance"))
        if inst is not None:
            b["instance"] = inst
        nm = cell("objName")
        if nm:
            b["objectName"] = nm
        if b:
            rec["blocks"]["bacnet"] = b
        if text:
            src[_headname(cmap, "objTypeText") or "Object-type-text"] = text
        sref = cell("statesRef")
        if sref.lower() not in ABSENT:
            rec["common"]["statesRef"] = sref
        uc = _num(cell("unitCode"))
        if uc is not None:
            # BACnet engineering-units 열거 번호. 우리 단위 사전과 다른 체계라
            # 옮겨 적지 않고 원표기로만 둔다.
            src[_headname(cmap, "unitCode") or "Unit-code"] = str(uc)

    if src:
        rec["provenance"]["sourceColumns"] = src
    if gaps:
        rec["provenance"]["gaps"] = gaps
    return rec, None


def _merge(a, b):
    """같은 포인트의 두 판(Modbus 표 · BACnet 표)을 한 레코드로 합친다.

    ⚠ 타입 대응표('AO 는 AV 다')를 **지어내지 않는다** — 문서가 그렇게 말한 적이
    없다. 설명문과 번호가 둘 다 같을 때만 같은 포인트로 본다(함정 5).
    """
    out = {"common": dict(a["common"]), "blocks": dict(a["blocks"]),
           "provenance": dict(a["provenance"])}
    for k, v in b["common"].items():
        out["common"].setdefault(k, v)
    out["blocks"].update(b["blocks"])
    src = dict(a["provenance"].get("sourceColumns") or {})
    src.update(b["provenance"].get("sourceColumns") or {})
    if src:
        out["provenance"]["sourceColumns"] = src
    gaps = list(a["provenance"].get("gaps") or []) + list(b["provenance"].get("gaps") or [])
    if gaps:
        out["provenance"]["gaps"] = gaps
    pages = sorted({a["provenance"].get("sourcePage"), b["provenance"].get("sourcePage")}
                   - {None})
    if pages:
        out["provenance"]["sourcePage"] = pages[0]
        if len(pages) > 1:
            out["provenance"]["sourcePages"] = pages
    return out


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계)."""
    import fitz
    doc = fitz.open(path)
    fname = os.path.basename(path)
    mb_rows, bac_rows = [], []
    unknown, head_seen = {}, None
    skipped = {"reserved": 0, "banner": 0, "gatewayConfig": 0}
    for pi, pg in enumerate(doc):
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if len(data) < 3:
                continue
            # ⚠ 0행은 표 제목('Modbus variables')이라 비어 있는 칸이 대부분이다.
            #   머리글은 그 아래 행이다 — 표 앞 3행에서 찾는다.
            hi = next((i for i, r in enumerate(data[:3]) if kind_of(r)), None)
            if hi is None:
                # 게이트웨이 설정표·노드표·알람표 — 포인트가 아니다
                skipped["gatewayConfig"] += max(0, len(data) - 1)
                continue
            kind = kind_of(data[hi])
            cmap, unk = header_map(data[hi], COLMAP_MB if kind == "modbus" else COLMAP_BAC)
            unknown.update(unk)
            head_seen = [clean(c) for c in data[hi]]
            for r in data[hi + 1:]:
                rec, why = row_to_point(r, cmap, kind, fname, pi + 1)
                if rec is None:
                    if why:
                        skipped[why] = skipped.get(why, 0) + 1
                    continue
                (mb_rows if kind == "modbus" else bac_rows).append(rec)

    # ── Error Code 의 값 집합을 알람표에서 푼다 (함정 4) ──────────────────
    alarms, had_loc = alarm_table(doc)
    doc.close()

    # ── 두 표 합치기 (함정 5) ────────────────────────────────────────────
    by_key = {}
    for r in bac_rows:
        inst = (r["blocks"].get("bacnet") or {}).get("instance")
        by_key[(r["common"]["name"].lower(), inst)] = r
    out, paired = [], set()
    for r in mb_rows:
        inst = (r["blocks"].get("n2") or {}).get("address")
        key = (r["common"]["name"].lower(), inst)
        mate = by_key.get(key)
        if mate is not None:
            paired.add(id(mate))
            out.append(_merge(mate, r))
        else:
            r["provenance"].setdefault("gaps", []).append(
                "Modbus 표에만 있고 BACnet 표에 짝(설명문+번호가 같은 행)이 없다 — "
                "합치지 않았다")
            out.append(r)
    for r in bac_rows:
        if id(r) not in paired:
            out.append(r)

    # 포인트 종별은 BACnet 오브젝트 타입에서 유도한다(point-schema pointKind)
    for r in out:
        bt = (r["blocks"].get("bacnet") or {}).get("objectType")
        if bt in ("AI", "AO", "AV"):
            r["common"]["pointKind"] = "analog"
        elif bt in ("BI", "BO", "BV"):
            r["common"]["pointKind"] = "binary"
        # readWrite 는 채우지 않는다 — 이 문서에 R/W 열이 없고, point-schema
        # readWrite 가 "BACnet 타입에서 추측 금지"라고 못박는다.
        r["provenance"].setdefault("gaps", []).append(
            "readWrite — 문서에 읽기/쓰기 열이 없다. 오브젝트 타입으로 추측하지 않았다")
        if alarms and re.search(r"see\s+alarm\s+table", r["common"].get("note") or "", re.I):
            r["common"]["statesRef"] = r["common"]["note"]
            r["common"]["states"] = alarms
            r["common"].pop("note", None)
            g = r["provenance"].setdefault("gaps", [])
            g.append("states — 원문이 밝힌 범위(11~46) 밖의 코드 %d개(91~99 Thermostat)가 "
                     "알람표에 함께 있어 전부 실었다"
                     % sum(1 for a in alarms if int(a["code"]) > 46))
            if had_loc:
                g.append("알람표의 'Location' 열(YKN2Open · 2 Circuit · Accessory · "
                         "Thermostat)은 states 구조에 자리가 없어 싣지 않았다")
    return out, unknown, head_seen, skipped


def main(argv):
    ap = argparse.ArgumentParser(description="JCI YKN2Open 게이트웨이 포인트 취입")
    ap.add_argument("--scan", action="store_true", help="대장의 문서를 훑어 머리글만 본다")
    ap.add_argument("--parse", help="문서ID 또는 파일 경로")
    a = ap.parse_args(argv)
    if a.parse:
        path = a.parse if os.path.exists(a.parse) else None
        if path is None:
            for p in docs():
                if a.parse in os.path.basename(p):
                    path = p
                    break
        if not path:
            print("문서를 못 찾았다: %s" % a.parse)
            return 1
        rows, unk, head, skipped = parse_doc(path)
        print("머리글: %s" % head)
        print("포인트 %d점 · 못 알아본 열 %s · 뺀 행 %s" % (len(rows), list(unk), skipped))
        for r in rows[:5]:
            print("  " + json.dumps(r, ensure_ascii=False)[:200])
        return 0
    if a.scan:
        for p in docs():
            rows, unk, head, _s = parse_doc(p)
            if rows:
                print("%-46s %5d점 %s" % (os.path.basename(p)[:46], len(rows), list(unk)))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
