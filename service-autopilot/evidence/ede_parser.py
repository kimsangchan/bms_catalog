# -*- coding: utf-8 -*-
"""BACnet EDE 파서 (BIG-EU Engineering Data Exchange)

EDE는 벤더가 배포하는 유일한 공통 기계판독 포맷이다. 4파일 세트를 읽어
카탈로그의 모델 포인트 구조로 변환한다.

  <name>_EDE_File.CSV        본체 — 오브젝트 목록
  <name>_EDE_StateTexts.CSV  다중상태 값의 상태 문자열
  <name>_EDE_Units.CSV       단위 코드 → 이름
  <name>_EDE_ObjTypes.CSV    오브젝트 타입 코드 → 이름

구분자(`,` 또는 `;`)와 인코딩(UTF-8 BOM / CP1252)이 파일마다 달라 자동 판별한다.
"""
import csv, io, os, re, glob, json

# BACnet 표준 오브젝트 타입 enum → canonical 약어
BACNET_TYPE = {
    0: ("AI", "Analog Input"), 1: ("AO", "Analog Output"), 2: ("AV", "Analog Value"),
    3: ("BI", "Binary Input"), 4: ("BO", "Binary Output"), 5: ("BV", "Binary Value"),
    8: ("Dev", "Device"), 13: ("MSI", "Multi-state Input"), 14: ("MSO", "Multi-state Output"),
    19: ("MSV", "Multi-state Value"), 15: ("NC", "Notification Class"),
    20: ("TL", "Trend Log"), 29: ("SV", "Structured View"), 10: ("File", "File"),
    17: ("Sched", "Schedule"), 6: ("Cal", "Calendar"), 12: ("Loop", "Loop"),
}
UNIT_SHORT = {
    "degrees-celsius": "℃", "degrees-fahrenheit": "℉", "percent": "%", "volts": "V",
    "amperes": "A", "milliamperes": "mA", "ohms": "Ω", "kilowatts": "kW",
    "kilowatt-hours": "kWh", "watts": "W", "hertz": "Hz", "seconds": "s", "hours": "h",
    "minutes": "min", "cubic-meters-per-hour": "㎥/h", "cubic-meters-per-second": "㎥/s",
    "liters-per-second": "L/s", "liters-per-minute": "L/min", "liters-per-hour": "L/h",
    "pascals": "Pa", "kilopascals": "kPa", "degrees-angular": "°", "millimeters": "mm",
    "no-units": "—", "parts-per-million": "ppm", "percent-relative-humidity": "%RH",
}


def _read(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1")


def _rows(text):
    """구분자 자동 판별 후 행 목록 반환"""
    head = text.splitlines()[:12]
    semi = sum(l.count(";") for l in head)
    comma = sum(l.count(",") for l in head)
    delim = ";" if semi > comma else ","
    return list(csv.reader(io.StringIO(text), delimiter=delim)), delim


def parse_ede(folder, stem=None):
    """EDE 4파일 세트 → {device, points[], meta{}}"""
    def find(suffix):
        pat = os.path.join(folder, ("%s*%s*" % (stem, suffix)) if stem else ("*%s*" % suffix))
        got = [p for p in glob.glob(pat) if p.lower().endswith(".csv")]
        return got[0] if got else None

    main = find("EDE_File") or find("EDE")
    if not main:
        raise FileNotFoundError("EDE 본체 파일을 찾지 못했습니다: %s" % folder)

    # 상태 문자열
    states = {}
    p = find("StateTexts")
    if p:
        rr, _ = _rows(_read(p))
        for r in rr:
            if not r or not r[0].strip().lstrip("#").strip().isdigit():
                continue
            states[int(r[0].strip())] = [c.strip().strip('"') for c in r[1:] if c.strip()]

    # 단위
    units = {}
    p = find("Units")
    if p:
        rr, _ = _rows(_read(p))
        for r in rr:
            if len(r) >= 2 and r[0].strip().strip('"').isdigit():
                units[int(r[0].strip().strip('"'))] = r[1].strip().strip('"')

    # 본체
    text = _read(main)
    rr, delim = _rows(text)
    meta, hdr_i = {}, None
    for i, r in enumerate(rr):
        if not r:
            continue
        c0 = r[0].strip()
        if c0.startswith("#") and "keyname" in " ".join(r).lower():
            hdr_i = i
            break
        if c0 in ("PROJECT_NAME", "VERSION_OF_REFERENCEFILE", "TIMESTAMP_OF_LAST_CHANGE",
                  "AUTHOR_OF_LAST_CHANGE", "VERSION_OF_LAYOUT") and len(r) > 1:
            meta[c0] = r[1].strip()
    if hdr_i is None:
        raise ValueError("EDE 헤더 행(keyname…)을 찾지 못했습니다")

    cols = [c.strip().lstrip("#").strip().lower() for c in rr[hdr_i]]
    def ix(*names):
        for n in names:
            for j, c in enumerate(cols):
                if n in c:
                    return j
        return -1
    i_name, i_type = ix("object-name"), ix("object-type")
    i_inst, i_desc = ix("object-instance"), ix("description")
    i_set, i_st = ix("settable"), ix("state-text")
    i_unit = ix("unit-code", "unit")
    i_min, i_max = ix("min-present-value"), ix("max-present-value")

    device, points = None, []
    for r in rr[hdr_i + 1:]:
        if len(r) <= max(i_name, i_type, i_inst) or not r[0].strip() or r[0].strip().startswith("#"):
            continue
        try:
            otype = int(float(r[i_type]))
            oinst = int(float(r[i_inst]))
        except (ValueError, IndexError):
            continue
        abbr, full = BACNET_TYPE.get(otype, ("T%d" % otype, "type %d" % otype))
        name = r[i_name].strip()
        desc = r[i_desc].strip() if 0 <= i_desc < len(r) else ""
        note = []
        if desc and desc.lower() != "description":
            note.append(desc)
        # 단위
        u = "—"
        if 0 <= i_unit < len(r) and r[i_unit].strip():
            try:
                uname = units.get(int(float(r[i_unit])), "")
                u = UNIT_SHORT.get(uname, uname or "—")
            except ValueError:
                pass
        # 상태 문자열
        if 0 <= i_st < len(r) and r[i_st].strip():
            try:
                st = states.get(int(float(r[i_st])))
                if st:
                    note.append(" / ".join(st))
            except ValueError:
                pass
        # 범위
        lo = r[i_min].strip() if 0 <= i_min < len(r) else ""
        hi = r[i_max].strip() if 0 <= i_max < len(r) else ""
        if lo or hi:
            note.append("범위 %s~%s" % (lo or "?", hi or "?"))
        if 0 <= i_set < len(r) and r[i_set].strip().upper() in ("Y", "TRUE", "1"):
            note.append("쓰기 가능")
        if abbr == "Dev":
            device = {"name": name, "inst": oinst}
            continue
        points.append({"inst": oinst, "type": abbr, "unitDisp": u,
                       "name": name, "note": " · ".join(note)})
    points.sort(key=lambda x: (x["type"], x["inst"]))
    return {"device": device, "points": points, "meta": meta,
            "source": os.path.basename(main), "delimiter": delim,
            "stateTexts": len(states), "units": len(units)}


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "ede")
    out = parse_ede(folder, sys.argv[2] if len(sys.argv) > 2 else None)
    print("장치      :", out["device"])
    print("메타      :", out["meta"])
    print("구분자    : '%s' · 상태문자열 %d집합 · 단위 %d종" %
          (out["delimiter"], out["stateTexts"], out["units"]))
    print("포인트    : %d개" % len(out["points"]))
    for p in out["points"]:
        print("  %-4s %-4d %-6s %-22s %s" % (p["type"], p["inst"], p["unitDisp"],
                                             p["name"][:22], p["note"][:64]))
    json.dump(out["points"], open(os.path.join(os.path.dirname(folder), "belimo_vav_ede.json"),
                                  "w", encoding="utf-8"), ensure_ascii=False, indent=1)
