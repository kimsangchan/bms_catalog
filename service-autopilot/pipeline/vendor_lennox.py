# -*- coding: utf-8 -*-
"""Lennox Enlight EHB 의 General Data → 정격 사양 표 (LGT 가스/전기 + LHT 히트펌프).

EHB 의 SPECIFICATIONS 표는 PDF 표 인식에서 구간 라벨(General Data·Cooling
Performance)이 항목 라벨과 한 칸으로 눌려 라벨-값 짝이 끊긴다. 텍스트 층에는
'라벨 → 형번 수만큼 값' 구조가 온전히 남아 있어, 그걸 전치 표(첫 행=형번)로
만들어 모델 specTables 에 넣는다 — 일반 형번 사다리(첫 행 형번 인식)가 그대로 읽는다.

문서마다 라벨 표기가 조금씩 다르다(LGT '(Btuh) 3ph' ↔ LHT '- Btuh') — 패턴은
유연하게 잡고, 실린 라벨은 **매치된 원문 줄 그대로**(각주 위첨자만 뗀 것) 쓴다.
'- - -' 는 해당 전원/형번에 적용 없음 표기라 빈 값으로 옮긴다.
같은 라벨이 두 번 나오면(LHT 의 Total Unit Power — 냉방 절·난방 절) 첫 번째
(냉방 절)만 쓴다.

실행:  python vendor_lennox.py        (멱등 — 같은 source 표는 갈아끼운다)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
MID = "lennox-core-unit-controller-enlight-model-l-rooftop-bacnet"

DOCS = [
    ("Lennox_Enlight_LGT_EHB_210977.pdf", "Enlight LGT 3-6 Ton"),
    ("Lennox_Enlight_LHT_EHB_2411.pdf", "Enlight LHT 13-20 Ton"),
]

# 문서 라벨을 유연 패턴으로 — 실외/실내 코일처럼 같은 라벨이 다른 뜻으로 두 번
# 나오는 항목(face area 류)은 싣지 않는다. 값 네 개가 한 줄로 눌리는 라벨
# (Compressor Type)도 뺀다.
LABELS = [
    r"Nominal Tonnage",
    r"Gross Cooling Capacity - Btuh",
    r"Net Cooling Capacity (\(Btuh\) 3ph|- Btuh)",
    r"AHRI Rated Air Flow (\(cfm-high/low\) 3ph|- cfm)",
    r"EER \(Btuh/Watt\)( - 3ph)?",
    r"IEER \(Btuh/Watt\)( 3ph)?",
    r"SEER \(Btuh/Watt\) - 208/230V-3ph",
    r"SEER2 \(Btuh/Watt\) 1,3ph",
    r"Total Unit Power (\(kW\) 3ph|- kW)",
    r"Sound Rating Number \(SRN\) \(dBA\)",
    r"Total High Heat Capacity - Btuh",
    r"C\.O\.P\.",
]


def parse_general_data(pdf):
    import fitz
    doc = fitz.open(pdf)
    lines, page_no = None, None
    for pi in range(doc.page_count):
        t = doc[pi].get_text()
        if "General Data" in t and "Model Number" in t:
            lines = [re.sub(r"\s+", " ", ln).strip() for ln in t.splitlines()]
            page_no = pi + 1
            break
    if not lines:
        return None
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

    def first_match(pattern):
        regex = re.compile(r"^[12¹²]?\s*(%s)\s*$" % pattern)
        for i, ln in enumerate(lines):
            m = regex.match(ln)
            if m:
                vals = lines[i + 1:i + 1 + n]
                vals = [("" if re.match(r"^[-\s]+$", v) else v) for v in vals]
                return m.group(1), vals
        return None, None

    rows = [["Model Number"] + codes]
    for pattern in LABELS:
        label, vals = first_match(pattern)
        if label and vals and len(vals) == n:
            rows.append([label] + vals)
    if len(rows) < 3:
        return None
    tons = first_match(r"Nominal Tonnage")[1] or [""] * n
    return rows, tons, page_no


def build_table(pdf_name, title_suffix):
    parsed = parse_general_data(os.path.join(RAW, pdf_name))
    if not parsed:
        return None
    rows, tons, page_no = parsed
    return {
        # 제목의 'General data' 는 형번 사다리의 제목 게이트에 걸리기 위한 표준 표기다
        "title": "General data — %s (EHB text)" % title_suffix,
        "header": [""] + tons,
        "rows": rows, "quantities": [],
        "orientation": "row", "kind": "rating",
        "page": page_no, "source": pdf_name + "#generaldata",
    }


def main():
    path = os.path.join(HERE, "data", "models", MID + ".json")
    m = json.load(open(path, encoding="utf-8"))
    injected = 0
    for pdf_name, suffix in DOCS:
        if not os.path.exists(os.path.join(RAW, pdf_name)):
            print("· %s 없음 — 건너뜀" % pdf_name)
            continue
        table = build_table(pdf_name, suffix)
        if not table:
            print("· %s General Data 를 못 찾았다" % pdf_name)
            continue
        src = table["source"]
        m["specTables"] = [t for t in m.get("specTables", [])
                          if t.get("source") != src] + [table]
        injected += 1
        print("형번 %d개 · 항목 행 %d개 주입 (%s)"
              % (len(table["rows"][0]) - 1, len(table["rows"]) - 1, src))
    if not injected:
        return 1
    m["has"] = dict(m.get("has", {}), spec=True)
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
