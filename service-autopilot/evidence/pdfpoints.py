# -*- coding: utf-8 -*-
"""PDF → 텍스트 → (인스턴스, 단위, 포인트명) 표. Trane Symbio 계열 포인트 리스트용."""
import re, zlib, json, sys

UNITS = ["Temp", "Real", "Pressure", "Binary", "Percent", "Amps", "Volts", "Hours",
         "Enum", "Multistate", "Flow", "Power", "Time", "Bool"]
TYPEMAP = {"Temp": ("AI", "℃"), "Pressure": ("AI", "kPa"), "Percent": ("AI", "%"),
           "Amps": ("AI", "A"), "Volts": ("AI", "V"), "Hours": ("AI", "h"),
           "Real": ("AV", "—"), "Binary": ("BI", "—"), "Enum": ("MSI", "—"),
           "Flow": ("AI", "㎥/h"), "Power": ("AI", "kW"), "": ("—", "—")}

def pdftext(path):
    raw = open(path, "rb").read()
    parts = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            parts.append(zlib.decompress(m.group(1)))
        except Exception:
            pass
    txt = b"\n".join(parts).decode("latin1")
    chunks = re.compile(r"\((?:\\.|[^()\\])*\)", re.S).findall(txt)
    s = " ".join(c[1:-1] for c in chunks)
    return s.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")

def split_camel(s):
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    return s.strip()

def points(path):
    d = re.sub(r"[^\x20-\x7e]", " ", pdftext(path))
    d = re.sub(r"\s+", "", d)
    rows, prev = [], 0
    for m in re.finditer(r"(?<!\d)(3\d{4})(?!\d)", d):
        seg, prev = d[prev:m.start()], m.end()
        unit = ""
        for u in UNITS:
            if seg.endswith(u):
                unit, seg = u, seg[: -len(u)]
                break
        nm = re.search(r"([A-Z][A-Za-z0-9]{3,60})$", seg)
        name = nm.group(1) if nm else seg[-40:]
        if len(name) < 4:
            continue
        t, ud = TYPEMAP.get(unit, ("—", "—"))
        rows.append({"inst": int(m.group(1)), "type": t, "unitDisp": ud, "name": split_camel(name)})
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: x["inst"]):
        if r["inst"] in seen:
            continue
        seen.add(r["inst"])
        out.append(r)
    return out

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    p = points(src)
    json.dump(p, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%s → %d 점 (%s~%s)" % (dst, len(p), p[0]["inst"] if p else "-", p[-1]["inst"] if p else "-"))
    for r in p[:8]:
        print("   %5d %-4s %-5s %s" % (r["inst"], r["type"], r["unitDisp"], r["name"][:52]))
