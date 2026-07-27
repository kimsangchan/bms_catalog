# -*- coding: utf-8 -*-
"""벤더 PDF 텍스트 → 포인트/레지스터 표 파싱"""
import re, json, os, sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdfs")

UNIT_MAP = {"Temperature": ("AI", "℃"), "Percent": ("AI", "%"), "Pressure": ("AI", "kPa"),
            "Time": ("AI", "h"), "Power": ("AI", "kW"), "Energy": ("AI", "kWh"),
            "Frequency": ("AI", "Hz"), "Current": ("AI", "A"), "Voltage": ("AI", "V"),
            "Flow": ("AI", "㎥/h"), "No Units": ("AV", "—"), "": ("—", "—")}


def trane_cgam():
    """Trane Symbio 800 CGAM — 'Object Identifier | Object Name | Description | Units' 표"""
    t = open(os.path.join(D, "trane_cgam.txt"), encoding="utf-8", errors="replace").read()
    rows, unit_q = [], []
    for ln in t.split("\n"):
        s = ln.rstrip()
        if not s.strip():
            continue
        # 오른쪽 끝의 단위 토큰을 큐에 모은다(레이아웃상 한 줄 밀려 나옴)
        mu = re.search(r"\s{3,}(Temperature|Percent|Pressure|Time|Power|Energy|Frequency|"
                       r"Current|Voltage|Flow|No Units)\s*$", s)
        if mu:
            unit_q.append(mu.group(1))
        m = re.match(r"\s{2,}(\d{1,4})\s{2,}([A-Z][^|]{4,70}?)\s{3,}", s)
        if not m:
            m = re.match(r"\s{2,}(\d{1,4})\s{2,}([A-Z].{4,70})$", s)
        if m:
            inst, name = int(m.group(1)), m.group(2).strip()
            name = re.sub(r"\s{2,}.*$", "", name).strip()
            if len(name) < 5 or name.lower().startswith(("object", "date", "reference")):
                continue
            rows.append({"inst": inst, "name": name})
    # 단위 큐를 순서대로 배분
    for i, r in enumerate(rows):
        u = unit_q[i] if i < len(unit_q) else ""
        t_, ud = UNIT_MAP.get(u, ("—", "—"))
        r["type"], r["unitDisp"], r["note"] = t_, ud, u
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x["inst"]):
        if r["inst"] in seen:
            continue
        seen.add(r["inst"]); out.append(r)
    return out


def grundfos_modbus():
    """Grundfos Modbus — '레지스터번호 이름 ...' 표 (§9.2~9.9)"""
    t = open(os.path.join(D, "grundfos_modbus.txt"), encoding="utf-8", errors="replace").read()
    rows = []
    for ln in t.split("\n"):
        s = ln.rstrip()
        m = re.match(r"\s*(\d{3,5})\s+([A-Za-z][A-Za-z0-9 _\-\./%()]{5,60}?)\s{2,}(.*)$", s)
        if m:
            addr, name, rest = m.group(1), m.group(2).strip(), m.group(3).strip()
            if len(name) < 6:
                continue
            rows.append({"inst": int(addr), "type": "—", "unitDisp": "—",
                         "name": name, "note": rest[:60]})
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x["inst"]):
        if r["inst"] in seen:
            continue
        seen.add(r["inst"]); out.append(r)
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "trane"):
        p = trane_cgam()
        json.dump(p, open(os.path.join(D, "..", "trane_cgam.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("Trane CGAM: %d 점 (%s~%s)" % (len(p), p[0]["inst"], p[-1]["inst"]) if p else "Trane 0")
        for r in p[:12]:
            print("   %4d %-4s %-4s %s" % (r["inst"], r["type"], r["unitDisp"], r["name"][:56]))
    if which in ("all", "grundfos"):
        g = grundfos_modbus()
        json.dump(g, open(os.path.join(D, "..", "grundfos_modbus.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\nGrundfos Modbus: %d 레지스터" % len(g))
        for r in g[:12]:
            print("   %5d %-40s %s" % (r["inst"], r["name"][:40], r["note"][:40]))
