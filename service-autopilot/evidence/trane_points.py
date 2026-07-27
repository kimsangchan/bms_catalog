# -*- coding: utf-8 -*-
"""Trane Symbio 800 (UC800) 통합 포인트 리스트 PDF 추출 텍스트 → 포인트 표"""
import re, json

txt = open("trane.txt", encoding="utf-8").read()
d = re.sub(r"[^\x20-\x7e]", " ", txt)
d = re.sub(r"\s+", "", d)

UNITS = ["Temp", "Real", "Pressure", "Binary", "Percent", "Amps", "Volts", "Hours",
         "Enum", "Multistate", "Flow", "Power", "Time", "Bool"]

# 인스턴스 번호 위치 수집
hits = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r"(?<!\d)(3\d{4})(?!\d)", d)]
rows, prev_end = [], 0
for s, e, inst in hits:
    seg = d[prev_end:s]
    prev_end = e
    unit = ""
    for u in UNITS:
        if seg.endswith(u):
            unit = u
            seg = seg[: -len(u)]
            break
    # 앞쪽 잡음 제거: 마지막 대문자 시작 토큰 덩어리만
    m = re.search(r"([A-Z][A-Za-z0-9]{3,60})$", seg)
    name = m.group(1) if m else seg[-40:]
    if len(name) < 4:
        continue
    rows.append({"inst": int(inst), "unit": unit, "raw": name})

# 중복 제거 + 정렬
seen, out = set(), []
for r in sorted(rows, key=lambda x: x["inst"]):
    if r["inst"] in seen:
        continue
    seen.add(r["inst"])
    out.append(r)

def split_camel(s):
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return s

TYPEMAP = {"Temp": ("AI", "℃"), "Pressure": ("AI", "kPa"), "Percent": ("AI", "%"),
           "Amps": ("AI", "A"), "Volts": ("AI", "V"), "Hours": ("AI", "h"),
           "Real": ("AV", "—"), "Binary": ("BI", "—"), "Enum": ("MSI", "—"),
           "Flow": ("AI", "㎥/h"), "Power": ("AI", "kW"), "": ("—", "—")}

for r in out:
    r["name"] = split_camel(r["raw"])
    t, u = TYPEMAP.get(r["unit"], ("—", "—"))
    r["type"], r["unitDisp"] = t, u

print("추출 포인트:", len(out), "인스턴스 범위:", out[0]["inst"], "~", out[-1]["inst"])
for r in out[:25]:
    print("  %5d  %-4s %-6s %s" % (r["inst"], r["type"], r["unitDisp"], r["name"][:58]))
json.dump(out, open("trane_points.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
