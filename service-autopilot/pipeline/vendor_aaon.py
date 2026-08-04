# -*- coding: utf-8 -*-
"""AAON RN 브로슈어의 캐비닛 블록 → 정격 사양 표.

브로슈어의 캐비닛 소개(A~E)는 그래픽 조판이라 표 인식이 못 집지만, 텍스트 층에는
'Nominal cfm | RN-006 | 2,000 …' 구조가 온전히 남아 있다. 이를 전치 표
(머리글=형번, 행=항목)로 만들어 모델 specTables 에 넣는다 — 일반 형번 사다리
(머리글 형번 인식)가 그대로 읽는다.

톤수는 IOM 형번 규약('006 = 6 ton Capacity')이 근거다. IEER/EER 는 캐비닛
단위의 'Up to' 값이라 그대로 'Up to N' 으로 적는다 — 형번별 확정값이 아니다.

실행:  python vendor_aaon.py        (멱등 — 같은 source 표는 갈아끼운다)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
MID = "aaon-vccx2-rn-rq-series-rooftop-bacnet"
SRC = "AAON_RN_Series_Brochure.pdf"
TABLE_SOURCE = SRC + "#cabinets"


def parse_cabinets(pdf):
    import fitz
    doc = fitz.open(pdf)
    text, page_no = "", 1
    for pi in range(min(10, doc.page_count)):
        t = doc[pi].get_text()
        if "Nominal cfm" in t:
            text, page_no = t, pi + 1
            break
    if not text:
        return None
    # 'A–Cabinet … Nominal cfm RN-006 2,000 RN-007 2,500 … Dimensions'
    blocks = re.split(r"([A-E])–Cabinet", text)
    units = []  # (cabinet, code, cfm, ieer, eer, config)
    for i in range(1, len(blocks) - 1, 2):
        cab, body = blocks[i], blocks[i + 1]
        ieer = re.search(r"Air-Cooled IEER\s*\n?\s*Up to ([\d.]+)", body)
        eer = re.search(r"Air-Cooled EER\s*\n?\s*Up to ([\d.]+)", body)
        conf = re.search(r"Configuration\s*\n?\s*(\w+)", body)
        for m in re.finditer(r"RN-(\d{3})\s*\n?\s*([\d,]{3,7})", body):
            units.append({
                "cabinet": cab, "code": "RN-%s" % m.group(1),
                "tons": str(int(m.group(1))), "cfm": m.group(2),
                "ieer": ("Up to %s" % ieer.group(1)) if ieer else "—",
                "eer": ("Up to %s" % eer.group(1)) if eer else "—",
                "config": conf.group(1) if conf else "—",
            })
    if not units:
        return None
    # 같은 형번이 수직/수평 캐비닛에 겹치면 처음 것만 (수직이 먼저 나온다)
    seen, uniq = set(), []
    for u in units:
        if u["code"] in seen:
            continue
        seen.add(u["code"])
        uniq.append(u)
    header = [""] + [u["code"] for u in uniq]
    rows = [
        ["NOMINAL CAPACITY (tons) — IOM 형번 규약('006 = 6 ton')"] + [u["tons"] for u in uniq],
        ["Nominal CFM"] + [u["cfm"] for u in uniq],
        ["Cabinet"] + [u["cabinet"] for u in uniq],
        ["EER (Air-Cooled, cabinet up-to)"] + [u["eer"] for u in uniq],
        ["IEER (Air-Cooled, cabinet up-to)"] + [u["ieer"] for u in uniq],
        ["Configuration"] + [u["config"] for u in uniq],
    ]
    return {
        # 제목의 'General data' 는 형번 사다리의 제목 게이트에 걸리기 위한 표준 표기다
        "title": "General data — RN Series cabinets (brochure text)",
        "header": header, "rows": rows, "quantities": [],
        "orientation": "row", "kind": "rating",
        "page": page_no, "source": TABLE_SOURCE,
    }


def main():
    table = parse_cabinets(os.path.join(RAW, SRC))
    if not table:
        print("캐비닛 블록을 못 찾았다")
        return 1
    path = os.path.join(HERE, "data", "models", MID + ".json")
    m = json.load(open(path, encoding="utf-8"))
    keep = [t for t in m.get("specTables", []) if t.get("source") != TABLE_SOURCE]
    m["specTables"] = keep + [table]
    m["has"] = dict(m.get("has", {}), spec=True)
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("형번 %d개 · 표 1개 주입 (%s)" % (len(table["header"]) - 1, TABLE_SOURCE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
