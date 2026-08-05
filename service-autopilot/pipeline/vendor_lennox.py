# -*- coding: utf-8 -*-
"""Lennox Enlight LGT EHB 의 General Data → 정격 사양 표.

EHB 20쪽 SPECIFICATIONS 표는 PDF 표 인식에서 구간 라벨(General Data·Cooling
Performance)이 항목 라벨과 한 칸으로 눌려 라벨-값 짝이 끊긴다. 텍스트 층에는
'라벨 → 형번 수만큼 값' 구조가 온전히 남아 있어, 그걸 전치 표(첫 행=형번)로
만들어 모델 specTables 에 넣는다 — 일반 형번 사다리(첫 행 형번 인식)가 그대로 읽는다.

'- - -' 는 문서에서 해당 전원/형번에 적용 없음 표기라 빈 값으로 옮긴다
(예: IEER 는 072 3상만, SEER 는 036~060 만 게재).

실행:  python vendor_lennox.py        (멱등 — 같은 source 표는 갈아끼운다)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
MID = "lennox-core-unit-controller-enlight-model-l-rooftop-bacnet"
SRC = "Lennox_Enlight_LGT_EHB_210977.pdf"
TABLE_SOURCE = SRC + "#generaldata"

# 문서 라벨 그대로 옮긴다 (각주 위첨자 1/¹ 만 뗀다). 실외/실내 코일처럼 같은
# 라벨이 두 번 나오는 항목은 뜻이 갈려 싣지 않는다 — 원문표 후보에서 본다.
LABELS = [
    (r"Nominal Tonnage", "Nominal Tonnage"),
    (r"Gross Cooling Capacity - Btuh", "Gross Cooling Capacity - Btuh"),
    (r"[1¹]\s*Net Cooling Capacity \(Btuh\) 3ph", "Net Cooling Capacity (Btuh) 3ph"),
    (r"[1¹]\s*AHRI Rated Air Flow \(cfm-high/low\) 3ph",
     "AHRI Rated Air Flow (cfm-high/low) 3ph"),
    (r"[1¹]\s*EER \(Btuh/Watt\) - 3ph", "EER (Btuh/Watt) - 3ph"),
    (r"[1¹]\s*IEER \(Btuh/Watt\) 3ph", "IEER (Btuh/Watt) 3ph"),
    # Compressor Type 은 텍스트 층에서 값 네 개가 한 줄로 눌려 짝을 못 만든다 — 뺀다
]


def parse_general_data(pdf):
    import fitz
    doc = fitz.open(pdf)
    lines, page_no = [], None
    for pi in range(doc.page_count):
        t = doc[pi].get_text()
        if "General Data" in t and "Model Number" in t:
            lines = [ln.strip() for ln in t.splitlines()]
            page_no = pi + 1
            break
    if not lines:
        return None
    # 형번 — 'Model Number' 다음 줄부터 형번 토큰이 이어진다 (LGT036H4E …)
    try:
        mi = lines.index("Model Number")
    except ValueError:
        return None
    codes = []
    for ln in lines[mi + 1:]:
        if re.match(r"^[A-Z]{2,4}\d{3}[A-Z0-9]*$", ln):
            codes.append(ln)
        else:
            break
    if len(codes) < 2:
        return None
    n = len(codes)

    def values_after(pattern):
        regex = re.compile("^" + pattern + "$")
        for i, ln in enumerate(lines):
            if regex.match(ln):
                vals = lines[i + 1:i + 1 + n]
                # '- - -' = 해당 형번/전원에 적용 없음 → 빈 값
                return [("" if re.match(r"^[-\s]+$", v) else v) for v in vals]
        return None

    rows = [["Model Number"] + codes]
    for pattern, label in LABELS:
        vals = values_after(pattern)
        if vals and len(vals) == n:
            rows.append([label] + vals)
    if len(rows) < 3:
        return None
    tons = values_after(r"Nominal Tonnage") or [""] * n
    return {
        # 제목의 'General data' 는 형번 사다리의 제목 게이트에 걸리기 위한 표준 표기다
        "title": "General data — Enlight LGT 3-6 Ton (EHB text)",
        "header": [""] + tons,
        "rows": rows, "quantities": [],
        "orientation": "row", "kind": "rating",
        "page": page_no, "source": TABLE_SOURCE,
    }


def main():
    table = parse_general_data(os.path.join(RAW, SRC))
    if not table:
        print("General Data 를 못 찾았다")
        return 1
    path = os.path.join(HERE, "data", "models", MID + ".json")
    m = json.load(open(path, encoding="utf-8"))
    keep = [t for t in m.get("specTables", []) if t.get("source") != TABLE_SOURCE]
    m["specTables"] = keep + [table]
    m["has"] = dict(m.get("has", {}), spec=True)
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("형번 %d개 · 항목 행 %d개 주입 (%s)"
          % (len(table["rows"][0]) - 1, len(table["rows"]) - 1, TABLE_SOURCE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
