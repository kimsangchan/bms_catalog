# -*- coding: utf-8 -*-
"""LG AHU 통신 킷(0CAA0-02M) Modbus 맵 재취입 — 옛 추출본이 버린 것을 되찾는다.

  PYTHONIOENCODING=utf-8 python ingest_lg_ahu.py          바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_lg_ahu.py --run    실제로 기록한다

왜 다시 하나
  기존 두 모델은 extractor='table' 로 뽑혀 **판(interfaces)이 없고**(그래서 대조대에
  안 뜬다) 원문 'Value explanation' 열을 통째로 버렸다. 실측(2026-09-04):
    원문 47점 전부가 Value explanation 을 가졌는데 취입본은 상태 0 · 범위 0 · 단위 0.
    게다가 note 에 '●' 가 들어가 있었다 — 그건 설명이 아니라 **함수코드 표시**다.
  개수(19+28=47)만 맞고 내용이 비어 있었다.

⚠ 이 모델들은 정격(specTables 17개 · 형번)을 이미 갖고 있다. **덮어쓰지 않는다** —
  points 를 interfaces 로 갈아 끼우고 나머지 키는 그대로 둔다.

⚠ 배율 (x10) 의 방향
  원문은 '-50.0℃~100.0℃ (x10)' · '16.0℃~30.0℃ (x10, 1℃)' · '0, 2.0V~10V (x10, 0.5V)'
  처럼 **소수점을 함께** 쓴다. Modbus 레지스터는 정수라 그 값을 그대로 실을 수 없다 —
  ×10 해야 정수가 된다. 즉 원시값이 실제값의 10배다:
        공학값 = 원시값 × 0.1        (point-schema 의 정의 방향)
  반대로 읽으면 25℃가 250℃가 되고 범위도 -500~1000℃ 라는 말이 안 되는 값이 된다.
  scaleRaw 에 원표기 'x10' 을 함께 남긴다(schema 의 동반 의무).

⚠ Reserved 행은 포인트가 아니다(point-schema reservedSlotNotAPoint) — 52행을 뺀다.
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)

SRC_ID = "lg-ahu-comm-kit"
DOC = "LG_AHU_CommKit_0CAA0-02M_PDB.pdf"
FAMILY = "LG/AHUKit-Modbus"
PAGES = (68, 69, 70)

# 원문 '■Modbus points of PAHCMR000' → 어느 모델의 맵인가
KITS = {
    "PAHCMR000": ("lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcmr000",
                  "modbus", "Modbus 맵 (환기 RA 제어 킷)", ["PAHCMR000"]),
    "PAHCMS000": ("lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcms000",
                  "modbus", "Modbus 맵 (급기 SA 제어 킷)", ["PAHCMS000"]),
}

# 레지스터 앞자리 → 종류. 원문이 표로 못 박았다(0x01 Read Coils 00001~ 등).
REFCLASS = {"0": "coil", "1": "discreteInput", "3": "inputRegister",
            "4": "holdingRegister"}
# 함수코드 열 1~6 ↔ 0x01~0x06. 원문 'Function Code' 표의 Code 열이 그렇게 준다.
FC_WRITE = {5, 6}

ROW = re.compile(r"^([0134]\d{4})$")
STATE = re.compile(r"^\s*(\d+)\s*:\s*(.+?)\s*$")
UNIT = r"(?:\u2103|\u00b0C|V|%)"
# '-50.0℃~100.0℃ (x10)' · '16.0℃~30.0℃ (x10, 1℃)' · '0~255' · '0~255 [kBtu]'
# ⚠ 단위가 **숫자마다** 붙는다. 끝에 한 번만 오는 줄 알고 짰다가 범위 11점을 놓쳤다.
RANGE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(" + UNIT + r")?\s*~\s*"
                   r"(-?\d+(?:\.\d+)?)\s*(" + UNIT + r")?\s*"
                   r"(?:\[(\w+)\])?\s*(?:\(([^)]*)\))?\s*$")


def ledger_entry():
    led = json.load(io.open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    for url, v in led.items():
        if v.get("source") == SRC_ID and v.get("file") == DOC:
            return url, v
    raise SystemExit("대장에 %s / %s 가 없다 — collect.py --run %s" % (SRC_ID, DOC, SRC_ID))


def printed_no(page, fallback):
    """머리글의 인쇄 쪽번호. 이 문서는 PDF 쪽 - 1 이지만 가정하지 않고 읽는다."""
    for line in page.get_text().splitlines()[:6]:
        s = line.strip()
        if s.isdigit() and 1 <= int(s) <= 999:
            return int(s)
    return fallback


def read_rows(doc):
    """쪽 글자 흐름에서 행을 읽는다.

    한 행은 '레지스터 / 설명 / ● 또는 - 여섯 / Value explanation' 순으로 온다.
    표 인식을 쓰지 않는다 — 이 표는 ● 글리프가 셀 경계와 어긋나 열이 밀린다.
    """
    out, kit = [], None
    for p in PAGES:
        page = doc[p - 1]
        pr = printed_no(page, p)
        lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
        i = 0
        while i < len(lines):
            m = re.match(r"^■\s*Modbus points of\s*(\w+)", lines[i])
            if m:
                kit = m.group(1)
                i += 1
                continue
            if ROW.match(lines[i]):
                reg, desc = lines[i], lines[i + 1] if i + 1 < len(lines) else ""
                fc, j = [], i + 2
                while j < len(lines) and lines[j] in ("●", "-") and len(fc) < 6:
                    fc.append(lines[j])
                    j += 1
                # ⚠ 값이 한 줄이 아니다. 40003 은 '16 ~ 30℃ … 3),' 다음 줄에
                #    '12 ~ 50℃ … 4)' 가 이어진다(유선 리모컨 종류에 따라 갈린다).
                #    한 줄만 집으면 나머지를 통째로 잃는다.
                vs = []
                while j < len(lines) and not ROW.match(lines[j]) \
                        and not lines[j].startswith(("■", "Register", "Note", "Code")):
                    vs.append(lines[j])
                    j += 1
                out.append({"page": p, "printed": pr, "kit": kit, "reg": reg,
                            "desc": desc, "fc": fc,
                            "val": re.sub(r"\s+", " ", " ".join(vs)).strip()})
                i = j
                continue
            i += 1
    return out


FOOT = re.compile(r"^(\d)\)\s*(.+)$")


def footnotes(doc):
    """쪽마다 'Note' 아래 붙는 각주를 읽는다 — 표의 'N)' 이 가리키는 곳이다.

    ⚠ 각주를 안 풀면 값이 통째로 뜻을 잃는다. '1xxxx 2)' 는 그 자체로는 아무 말도
       아니지만 각주 2 가 'Error Code : 1 x yyy (x : Module Number, yyy : Error Code)'
       라고 밝힌다. '16 ~ 30℃ 3), 12 ~ 50℃ 4)' 도 각주가 '유선 리모컨 standard II /
       III' 라고 조건을 준다.
    """
    # ⚠ **쪽이 아니라 킷 단위로** 묶는다. 표가 쪽을 넘어가고(PAHCMS000 은 68~69쪽)
    #    각주는 마지막 쪽에만 붙는다 — 쪽으로 묶으면 68쪽 행이 70쪽 각주를 못 찾는다.
    #    게다가 번호가 킷마다 **다른 뜻**이다(PAHCMR000 의 1)은 통신 설정, PAHCMS000 의
    #    1)은 용량비 표다). 섞으면 엉뚱한 설명이 붙는다.
    out, kit = {}, None
    for p in PAGES:
        lines = [l.strip() for l in doc[p - 1].get_text().splitlines() if l.strip()]
        for n, l in enumerate(lines):
            m = re.match(r"^■\s*Modbus points of\s*(\w+)", l)
            if m:
                kit = m.group(1)
            if l == "Note" and kit:
                for x in lines[n + 1:]:
                    f = FOOT.match(x)
                    if not f:
                        break
                    out.setdefault(kit, {})[f.group(1)] = f.group(2).strip()
    return out


def crosscheck(doc, rows):
    """표 인식(find_tables)으로 한 번 더 읽어 레지스터·설명 짝을 맞춘다.

    본 판독이 글자 흐름이므로 대조는 **표 인식** 쪽으로 한다 — 다른 경로여야 뜻이 있다.
    """
    cells = collections.defaultdict(set)
    for p in PAGES:
        for tb in doc[p - 1].find_tables().tables:
            for r in tb.extract():
                vals = [re.sub(r"\s+", "", str(c or "")) for c in r]
                for n, v in enumerate(vals):
                    if ROW.match(v):
                        cells[p].add((v, "".join(vals[n + 1:n + 3])))
    same, diff = 0, []
    for r in rows:
        key = re.sub(r"\s+", "", r["desc"])
        if any(a == r["reg"] and key and key in b for a, b in cells[r["page"]]):
            same += 1
        elif len(diff) < 8:
            diff.append("%s %s" % (r["reg"], r["desc"]))
    return {"method": "표 인식(find_tables)으로 레지스터·설명 짝을 다시 읽어 맞췄다"
                      "(본 판독은 쪽 글자 흐름이다)",
            "total": len(rows), "both": same,
            "rate": round(same / len(rows), 4) if rows else 0.0, "diff": diff}


def parse_value(val):
    """Value explanation → (states, range, unit, scale, scaleRaw, note, gaps).

    원문 값은 15종뿐이라(2026-09-04 전수) 일반 정규식으로 뭉뚱그리지 않고 갈랐다:
      상태  '0: Off / 1: On' · '0: Cooling / 2: Fan / 4: Heating' · '1 : Low / 2 : Middle'
      범위  '-50.0℃~100.0℃ (x10)' · '16.0℃~30.0℃ (x10, 1℃)' · '0~255' · '0~255 [kBtu]'
      나머지 '0, 2.0V~10V (x10, 0.5V)' · '1xxxx 2)' · 두 범위가 겹친 것 → 산문 + gap
    """
    v = re.sub(r"\s+", " ", val or "").strip()
    if not v or v == "-":
        return [], None, "", None, "", "", []

    parts = [x for x in v.split("/") if x.strip()]
    if len(parts) >= 2 and all(STATE.match(x) for x in parts):
        return ([{"code": STATE.match(x).group(1), "label": STATE.match(x).group(2)}
                 for x in parts], None, "", None, "", "", [])

    # 각주 표시('3),' '4)')를 떼고 다시 본다 — 값이 아니라 참조다.
    # ⚠ 앞에 **빈칸이 있을 때만** 뗀다. 안 그러면 '(x10)' 의 닫는 괄호를 각주로
    #    오인해 '(x1' 로 잘라 버린다 — 실제로 그래서 온도 범위 5점을 놓쳤다.
    body = re.sub(r"\s\d\)\s*,?\s*$", "", v).strip()
    m = RANGE.match(body)
    if m:
        lo, u1, hi, u2, br, note = m.groups()
        unit = (u1 or u2 or br or "").replace("\u2103", "\u00b0C")
        rng = {"raw": body, "min": float(lo) if "." in lo else int(lo),
               "max": float(hi) if "." in hi else int(hi)}
        scale, sraw = None, ""
        if note and re.search(r"x\s*10", note, re.I):
            # 원시값이 실제값의 10배다 — 범위에 소수점이 있어(-50.0 · 2.0) 정수
            # 레지스터에 그대로 실을 수 없기 때문이다. 공학값 = 원시값 × 0.1.
            scale, sraw = 0.1, "x10"
        return [], rng, unit, scale, sraw, "", []

    # 두 범위가 겹친 칸 — 유선 리모컨 종류에 따라 갈린다(원문 각주 3)·4)).
    # 어느 쪽인지 이 표만으로는 못 정한다 → 하나를 고르지 않는다.
    if len(RANGE.findall(re.sub(r"\s*\d\)\s*,?", " ", v))) >= 2 or v.count("~") >= 2:
        return [], None, "", None, "", v, [
            "common.range — 한 칸에 범위가 둘이다(%r). 원문 각주가 '유선 리모컨 "
            "standard II / III' 에 따라 갈린다고 적었다 — 어느 쪽인지 이 표만으로는 "
            "못 정해 하나를 고르지 않았다." % v]

    return [], None, "", None, "", v, [
        "common.states / common.range — 원문 Value explanation 을 기계로 가르지 "
        "않았다(%r). 상태 열거도 순수 범위도 아니다 — 원문 그대로 남겼다." % v]


def build_iface(meta, kit, rows, foot):
    iid, _proto, label, applies = KITS[kit][1], None, KITS[kit][2], KITS[kit][3]
    pts, pages = [], []
    for r in rows:
        pages.append(r["printed"])
        states, rng, unit, scale, sraw, prose, gaps = parse_value(r["val"])
        fcs = [n + 1 for n, x in enumerate(r["fc"]) if x == "●"]
        # ⚠ 이름에 붙은 각주 표시를 뗀다 — 'Capacity 1)' 로 두면 BMS 가 그 이름으로
        #    오브젝트를 찾는다. 원문 그대로는 sourceColumns['Description'] 에 남는다.
        name = re.sub(r"\s*\d\)\s*$", "", r["desc"]).strip()
        common = {"name": name}
        notes = [prose] if prose else []
        # 값·이름이 가리키는 각주를 풀어 붙인다 — 안 풀면 '1xxxx 2)' 가 아무 말도 아니다
        seen = []
        for mk in re.findall(r"(\d)\)", "%s %s" % (r["desc"], r["val"])):
            txt = (foot.get(r["kit"]) or {}).get(mk)
            if txt and mk not in seen:
                seen.append(mk)
                notes.append("원문 각주 %s) %s" % (mk, txt))
        if notes:
            common["note"] = " · ".join(notes)
        if unit:
            common["unitSI"] = common["unitSIRaw"] = unit
        if rng:
            common["range"] = rng
        if states:
            common["states"] = states
        if fcs:
            # 쓰기 함수코드(0x05 Write Single Coil · 0x06 Write Single Holding)가
            # 붙어 있으면 쓸 수 있는 점이다. 원문이 표로 준 것이라 추측이 아니다.
            w = bool(set(fcs) & FC_WRITE)
            rd = bool(set(fcs) - FC_WRITE)
            common["readWrite"] = "R/W" if (w and rd) else ("W" if w else "R")
        mod = {"address": int(r["reg"]), "addressBase": "1-base",
               "refClass": REFCLASS[r["reg"][0]]}
        if fcs:
            mod["functionCodes"] = fcs
        if scale is not None:
            mod["scale"], mod["scaleRaw"] = scale, sraw
        pts.append({
            "common": common,
            "blocks": {"modbus": mod},
            "provenance": {
                "sourceFile": meta["file"], "sourcePage": r["printed"],
                "family": FAMILY,
                "sourceColumns": {
                    "Register": r["reg"], "Description": r["desc"],
                    "Function Code": " ".join(
                        "0x0%d" % n for n in fcs) or "-",
                    "Value explanation": r["val"] or "-",
                },
                "status": "extracted", "interfaceId": iid,
                **({"gaps": gaps} if gaps else {}),
            },
        })
    return {
        "id": iid, "label": label, "family": FAMILY, "protocols": ["modbus"],
        "sourceFile": meta["file"], "sourcePages": sorted(set(pages)),
        "pointCount": len(pts), "appliesTo": applies, "status": "extracted",
        "note": ("원문 10절 'Control Function' 의 Modbus 맵. 레지스터는 5자리 절대 "
                 "표기이고 앞자리가 종류를 정한다(0 코일 · 1 디스크리트 입력 · "
                 "3 입력 레지스터 · 4 홀딩 레지스터) — 원문이 함수코드 표로 못 박았다"
                 "(0x01 Read Coils 00001~ · 0x02 Read Discrete inputs 10001~ · "
                 "0x03 Read Holding 40001~ · 0x04 Read Input 30001~ · "
                 "0x05 Write Single Coil · 0x06 Write Single Holding). "
                 "통신 설정은 9600bps · 패리티 없음 · 스톱비트 1 이고 슬레이브 주소는 "
                 "8장에서 정한다. ⚠ 배율 'x10' 은 **원시값이 실제값의 10배**라는 뜻이다 "
                 "— 원문이 범위를 '-50.0℃~100.0℃' 처럼 소수점으로 적는데 정수 "
                 "레지스터에 그대로 실을 수 없기 때문이다. 공학값 = 원시값 × 0.1."),
        "gaps": ["Reserved 행 52개는 포인트로 세지 않았다(자리표시다).",
                 "슬레이브 주소는 현장 설정값이라 이 표에 없다(원문 8장)."],
        "points": pts,
    }


def main(argv):
    import fitz
    run = "--run" in argv
    url, meta = ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, SRC_ID))
    doc = fitz.open(path)

    rows = read_rows(doc)
    foot = footnotes(doc)
    unknown = sorted({r["kit"] for r in rows} - set(KITS))
    if unknown:
        raise SystemExit("KITS 에 없는 킷: %s" % unknown)
    real = [r for r in rows if r["desc"] != "Reserved"]
    cc = crosscheck(doc, real)
    print("원문 행 %d · Reserved %d 제외 → %d점 · 교차 대조 %d/%d = %.1f%%"
          % (len(rows), len(rows) - len(real), len(real),
             cc["both"], cc["total"], 100 * cc["rate"]))
    if cc["diff"]:
        print("   ⚠ 안 맞은 것:", " · ".join(cc["diff"]))

    for kit, (mid, iid, label, _ap) in KITS.items():
        mine = [r for r in real if r["kit"] == kit]
        if not mine:
            raise SystemExit("%s 의 행이 하나도 없다 — 판독을 봐라" % kit)
        iface = build_iface(meta, kit, mine, foot)
        n_s = sum(1 for p in iface["points"] if p["common"].get("states"))
        n_r = sum(1 for p in iface["points"] if p["common"].get("range"))
        n_u = sum(1 for p in iface["points"] if p["common"].get("unitSI"))
        n_sc = sum(1 for p in iface["points"] if (p["blocks"]["modbus"]).get("scale"))
        print("   %-10s %2d점 · 상태 %2d · 범위 %2d · 단위 %2d · 배율 %2d  원문 %s쪽"
              % (kit, len(iface["points"]), n_s, n_r, n_u, n_sc, iface["sourcePages"]))

        mp = os.path.join(DATA, "models", mid + ".json")
        model = json.load(io.open(mp, encoding="utf-8"))
        # ⚠ 정격(specTables·형번)은 건드리지 않는다 — 이 재취입은 포인트만 갈아 끼운다.
        model["interfaces"] = [iface]
        model["points"] = []
        model["extractor"] = "ingest_lg_ahu"
        model["crosscheck"] = cc
        model["summary"] = ("PDB 1건 · 판 1개에서 취입 — Modbus %d점 (사양 표 %d개)"
                            % (len(iface["points"]), len(model.get("specTables") or [])))
        if not run:
            continue
        with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(model, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("      → %s" % os.path.relpath(mp, HERE))

    if not run:
        print("\n(미리보기다. 기록하려면 --run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
