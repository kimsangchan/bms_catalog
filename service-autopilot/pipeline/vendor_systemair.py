# -*- coding: utf-8 -*-
"""Systemair Geniox 퀵가이드의 Quick selection → 크기별 치수 표.

퀵가이드의 크기표(Unit size 10~31 + Width/Height/Length)는 그래픽 조판이라
표 인식이 못 집지만, 텍스트 층에는 '라벨 → 크기 수만큼 값' 구조가 온전히
남아 있다(AAON·Lennox 전례). 회전형(rotary) 열교환기 구성을 대표로 떠서
'행=크기, 열=치수' 표로 만들어 모델 specTables 에 넣는다 — 크기 행 사다리
(size_row_units)가 읽는다.

길이는 열교환기 구성(회전/판형/역류/히트펌프)마다 다르다 — 대표 구성만 싣고
구성별 차이는 근거 쪽(퀵가이드 12쪽)에서 본다. 크기별 풍량은 SystemairCAD
선정 SW 전용이라 공개 카탈로그에 없다(gap 에 기록).

실행:  python vendor_systemair.py        (멱등 — 같은 source 표는 갈아끼운다)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
MID = "systemair-access-geniox-geniox-go-ahu-modbus"
SRC = "Systemair_Geniox_QuickGuide.pdf"
TABLE_SOURCE = SRC + "#quickselection"


def parse_sizes(pdf):
    import fitz
    doc = fitz.open(pdf)
    lines, page_no = None, None
    for pi in range(doc.page_count):
        t = doc[pi].get_text()
        if "Quick selection Geniox" in t and "Rotary heat exchanger" in t:
            lines = [ln.strip() for ln in t.splitlines()]
            page_no = pi + 1
            break
    if not lines:
        return None
    # 'Rotary heat exchanger' 블록부터 읽는다 (대표 구성 — 크기 10~31 전체)
    try:
        start = lines.index("Rotary heat exchanger")
    except ValueError:
        return None
    block = lines[start:]

    def values_after(label, count=None):
        for i, ln in enumerate(block):
            if ln == label:
                vals = []
                for v in block[i + 1:]:
                    if re.match(r"^\d{2,4}$", v):
                        vals.append(v)
                        if count and len(vals) == count:
                            break
                    else:
                        break
                return vals
        return []

    sizes = values_after("Unit size")
    if len(sizes) < 3:
        return None
    n = len(sizes)
    width = values_after("Width", n)
    height = values_after("Height*", n) or values_after("Height", n)
    length = values_after("Length", n)
    rows = []
    for i, code in enumerate(sizes):
        rows.append([code,
                     width[i] if i < len(width) else "",
                     height[i] if i < len(height) else "",
                     length[i] if i < len(length) else ""])
    return {
        # 'Size' 머리글은 크기 행 사다리(size_row_units)의 모양 게이트용 표준 표기다
        "title": "General data — Geniox sizes (quick guide, rotary heat exchanger)",
        "header": ["Size", "Width (mm)", "Height (mm)", "Length (mm)"],
        "rows": rows, "quantities": [],
        "orientation": "column", "kind": "rating",
        "page": page_no, "source": TABLE_SOURCE,
    }


def main():
    table = parse_sizes(os.path.join(RAW, SRC))
    if not table:
        print("Quick selection 크기표를 못 찾았다")
        return 1
    path = os.path.join(HERE, "data", "models", MID + ".json")
    m = json.load(open(path, encoding="utf-8"))
    keep = [t for t in m.get("specTables", []) if t.get("source") != TABLE_SOURCE]
    m["specTables"] = keep + [table]
    m["has"] = dict(m.get("has", {}), spec=True)
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("크기 %d개 주입 (%s)" % (len(table["rows"]), TABLE_SOURCE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
