# -*- coding: utf-8 -*-
"""Mitsubishi PAC-IF013 AHU 설계 가이드라인의 표준 풍량 표 → 조합 실외기 형번 표.

가이드라인 13쪽 'Standard air flow volume' 표는 조합 가능한 Mr.Slim 실외기
시리즈(ZRP/P/SHW/ZM)×용량 코드(35~250)별로 AHU 표준 풍량 최소/최대(m³/h)를
정한다 — 인터페이스 킷의 형번급 근거다. 표 인식이 겹칸 배치라 못 집으므로
텍스트 층에서 떠서 전치 표(첫 행=형번)로 주입한다(AAON·Lennox 전례).

형번은 시리즈 행+용량 열의 조합 표기다(예: ZRP35 — 실제 실외기 PUHZ-ZRP35,
Rebel 'DPS 003' 조합 전례). 시리즈마다 같은 열이라도 용량 코드가 다르다
(ZRP71 열의 SHW 는 80) — 행의 코드 그대로 조합한다.

실행:  python vendor_mitsubishi.py        (멱등 — 같은 source 표는 갈아끼운다)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
MID = "mitsubishi-electric-pac-if013b-sif013b-mr-slim-ahu-interface-modbus"
SRC = "Mitsubishi_PAC-IF013_AHU_Design_Guideline.pdf"
TABLE_SOURCE = SRC + "#airflow"

SERIES = ("ZRP", "P", "SHW", "ZM")


def parse_airflow(pdf):
    import fitz
    doc = fitz.open(pdf)
    text, page_no = None, None
    for pi in range(doc.page_count):
        t = doc[pi].get_text()
        if "Standard air flow volume" in t and "Model capacity of outdoor unit" in t:
            text, page_no = " ".join(t.split()), pi + 1
            break
    if not text:
        return None
    # 'ZRP 35 50 60 71 100 125 140 200 250 P – – … ZM …' — 시리즈 행 4개
    series_vals = {}
    m = re.search(r"Model capacity of outdoor unit\s+ZRP((?:\s+[\d–-]+){9})"
                  r"\s+P((?:\s+[\d–-]+){9})\s+SHW((?:\s+[\d–-]+){9})"
                  r"\s+ZM((?:\s+[\d–-]+){9})", text)
    if not m:
        return None
    for name, grp in zip(SERIES, m.groups()):
        series_vals[name] = grp.split()
    mx = re.search(r"Maximum air volume \[m³/min\](?:\s+[\d.]+){9}\s+\[m³/h\]((?:\s+\d+){9})", text)
    mn = re.search(r"Minimum air volume \[m³/min\](?:\s+[\d.]+){9}\s+\[m³/h\]((?:\s+\d+){9})", text)
    if not (mx and mn):
        return None
    hi, lo = mx.group(1).split(), mn.group(1).split()
    codes, airflow = [], []
    for series in SERIES:
        for col, size in enumerate(series_vals[series]):
            if not re.match(r"^\d{2,3}$", size):
                continue
            codes.append("%s%s" % (series, size))
            airflow.append("%s – %s" % (lo[col], hi[col]))
    if not codes:
        return None
    return {
        # 제목의 'General data' 는 형번 사다리의 제목 게이트에 걸리기 위한 표준 표기다
        "title": "General data — Mr.Slim outdoor units for AHU (design guideline text)",
        "header": [""] + [c[len(s):] if c.startswith(s) else c
                          for c, s in ((c, next(x for x in SERIES if c.startswith(x)))
                                       for c in codes)],
        "rows": [
            ["Model"] + codes,
            ["Standard air flow volume (m³/h)"] + airflow,
        ],
        "quantities": [],
        "orientation": "row", "kind": "rating",
        "page": page_no, "source": TABLE_SOURCE,
    }


def main():
    table = parse_airflow(os.path.join(RAW, SRC))
    if not table:
        print("표준 풍량 표를 못 찾았다")
        return 1
    path = os.path.join(HERE, "data", "models", MID + ".json")
    m = json.load(open(path, encoding="utf-8"))
    keep = [t for t in m.get("specTables", []) if t.get("source") != TABLE_SOURCE]
    m["specTables"] = keep + [table]
    m["has"] = dict(m.get("has", {}), spec=True)
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("형번 %d개 주입 (%s)" % (len(table["rows"][0]) - 1, TABLE_SOURCE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
