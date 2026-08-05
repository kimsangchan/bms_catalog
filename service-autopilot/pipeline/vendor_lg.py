# -*- coding: utf-8 -*-
"""LG AHU 통신 킷 PDB 의 EEV 킷 조합표 → 형번 표.

PDB 6.1 Capacity Range 표는 킷과 조합하는 팽창밸브 킷(EEV Kit) 형번
(PRLK048A0 등)별 용량 지수 범위(kW)와 통신 킷(PAHCMR000/PAHCMS000) 호환을
정한다 — Mitsubishi 조합 실외기와 같은 '조합 형번' 근거다. 통신 킷 모델
(환기 RA/급기 SA)마다 호환 'O' 인 EEV 킷만 그 모델의 형번으로 싣는다.

용량 지수 범위는 머리글에 'min–max kW' 로 조합해 용량대(capacityClass)로
쓴다 — 문서 두 열(Minimum/Maximum)의 표기 조합이다.

실행:  python vendor_lg.py        (멱등 — 같은 source 표는 갈아끼운다)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
SRC = "LG_AHU_CommKit_0CAA0-02M_PDB.pdf"
MODELS = {
    "lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcmr000": "PAHCMR000",
    "lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcms000": "PAHCMS000",
}


def parse_eev_kits(pdf):
    """[(형번, min, max, 호환R, 호환S)] + 쪽 번호."""
    import fitz
    doc = fitz.open(pdf)
    for pi in range(doc.page_count):
        if "EEV Kit" not in doc[pi].get_text():
            continue
        try:
            tabs = doc[pi].find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if not data or "EEV Kit" not in str(data[0][0] or ""):
                continue
            kits = []
            for r in data[1:]:
                cells = [str(c or "").strip() for c in r]
                if not cells or not re.match(r"^PRLK\w+$", cells[0]):
                    continue
                kits.append((cells[0], cells[1], cells[2],
                             cells[3] if len(cells) > 3 else "",
                             cells[4] if len(cells) > 4 else ""))
            if kits:
                return kits, pi + 1
    return None, None


def main():
    kits, page_no = parse_eev_kits(os.path.join(RAW, SRC))
    if not kits:
        print("EEV 킷 표를 못 찾았다")
        return 1
    for mid, kit_name in MODELS.items():
        col = 3 if kit_name == "PAHCMR000" else 4
        mine = [k for k in kits if k[col].upper().startswith("O")]
        if not mine:
            print("%s: 호환 킷 없음" % kit_name)
            continue
        table = {
            # 제목의 'General data' 는 형번 사다리 게이트, 'EEV kit' 은 역할 판정 근거다
            "title": "General data — EEV kit combination for %s (PDB)" % kit_name,
            "header": [""] + ["%s–%s kW" % (k[1], k[2]) for k in mine],
            "rows": [["Model"] + [k[0] for k in mine]],
            "quantities": [],
            "orientation": "row", "kind": "rating",
            "page": page_no, "source": SRC + "#eevkits",
        }
        path = os.path.join(HERE, "data", "models", mid + ".json")
        m = json.load(open(path, encoding="utf-8"))
        m["specTables"] = [t for t in m.get("specTables", [])
                          if t.get("source") != table["source"]] + [table]
        m["has"] = dict(m.get("has", {}), spec=True)
        json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("%s: EEV 킷 형번 %d개 주입" % (kit_name, len(mine)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
