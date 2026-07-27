# -*- coding: utf-8 -*-
"""Trane Symbio 800 IntelliCore Split (RAUK) 포인트 리스트 파싱.

앞선 두 시도(텍스트 줄 단위 / 단어 좌표 밴드)는 표 셀 안의 줄바꿈 때문에
이름이 엉뚱한 인스턴스에 붙었다. PyMuPDF의 `find_tables()`가 셀 경계를 직접
인식하므로 그것으로 해결한다. 다른 벤더 PDF에도 재사용 가능한 일반 파서.
"""
import re, json, os, sys
import fitz

OBJID = re.compile(r"^(AI|AO|AV|BI|BO|BV|MI|MO|MV)-?(\d{3,6})$")
UNIT_KO = {"°F": "℉", "°C": "℃", "%": "%", "Amps": "A", "Volts": "V", "kW": "kW",
           "None": "—", "*": "—", "": "—"}


def cell(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()


def parse(pdf):
    doc = fitz.open(pdf)
    rows, cols_seen = [], set()
    for pg in doc:
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if not data:
                continue
            hdr = [cell(c).lower() for c in data[0]]
            cols_seen.add(len(hdr))

            def idx(*names, default=-1):
                for n in names:
                    for j, h in enumerate(hdr):
                        if n in h:
                            return j
                return default
            i_name = idx("object name")
            i_desc = idx("description")
            i_unit = idx("unit")
            i_rng = idx("valid range")
            i_rw = idx("read")
            i_dep = idx("configuration")
            i_reg = idx("register\naddres", "register addres", "address")
            i_rtype = idx("register\ntype", "register type")
            i_states = idx("object states")
            for r in data[1:]:
                if not r or not r[0]:
                    continue
                m = OBJID.match(cell(r[0]))
                if not m:
                    continue
                typ, inst = m.group(1), int(m.group(2))
                name = cell(r[i_name]) if 0 <= i_name < len(r) else ""
                if not name:
                    continue
                note = []
                if 0 <= i_desc < len(r) and cell(r[i_desc]):
                    note.append(cell(r[i_desc]))
                if 0 <= i_states < len(r) and cell(r[i_states]):
                    note.append(cell(r[i_states]))
                if 0 <= i_rng < len(r) and cell(r[i_rng]):
                    note.append("범위 " + cell(r[i_rng]))
                if 0 <= i_rw < len(r) and cell(r[i_rw]).lower().startswith("read/w"):
                    note.append("쓰기 가능")
                if 0 <= i_dep < len(r) and cell(r[i_dep]) and cell(r[i_dep]) != "All RAUK Units":
                    note.append("조건: " + cell(r[i_dep]))
                if 0 <= i_reg < len(r) and cell(r[i_reg]).isdigit():
                    rt = cell(r[i_rtype]) if 0 <= i_rtype < len(r) else ""
                    note.append("Modbus %s %s" % (rt or "reg", cell(r[i_reg])))
                u = cell(r[i_unit]) if 0 <= i_unit < len(r) else ""
                rows.append({"inst": inst, "type": typ,
                             "unitDisp": UNIT_KO.get(u, u or "—"),
                             "name": name, "note": " · ".join(note)[:220]})
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: (x["type"], x["inst"])):
        k = (r["type"], r["inst"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out, cols_seen


if __name__ == "__main__":
    HERE = os.path.dirname(os.path.abspath(__file__))
    pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pdfs", "trane_split.pdf")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "trane_rauk.json")
    p, cols = parse(pdf)
    named = [r for r in p if len(r["name"]) >= 6]
    withreg = [r for r in p if "Modbus" in r["note"]]
    print("추출 %d점 · 이름 있음 %d · Modbus 레지스터 대응 %d · 표 열수 %s"
          % (len(p), len(named), len(withreg), sorted(cols)))
    for r in p[:16]:
        print("  %-3s-%-6d %-4s %-40s %s" % (r["type"], r["inst"], r["unitDisp"],
                                             r["name"][:40], r["note"][:56]))
    json.dump(p, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→", out)
