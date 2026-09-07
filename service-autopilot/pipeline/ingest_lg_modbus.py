# -*- coding: utf-8 -*-
"""LG AC Smart — **Modbus-TCP** 포인트 목록 취입 (같은 문서의 다른 통로).

  PYTHONIOENCODING=utf-8 python ingest_lg_modbus.py          바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_lg_modbus.py --run    실제로 기록한다

왜 따로 있나
  이 게이트웨이는 **BACnet 과 Modbus-TCP 두 통로**로 같은 기기를 연다. 우리는
  BACnet 쪽(ingest_lg, 164점)만 담고 Modbus 쪽을 통째로 빠뜨리고 있었다 —
  사용자가 "내 눈엔 57페이지부터 모드버스 같은데?" 라고 짚어 드러났다. 맞다.
  원문 p53 이 'Objects (Modbus-TCP)' 로 절을 열고 p54~62 에 목록이 있다.

  D-016 대로 **판이 다르면 따로 담는다** — 같은 기기의 같은 값이라도 통로가 다르면
  주소 체계가 다르다(BACnet 인스턴스 ↔ Modbus 레지스터).

원문 구조 (PDF 54~62)
  기기군 셋 × 함수코드 두 갈래
    Indoor Unit   p54 코일(0x01/0x05) · p55 홀딩 레지스터(0x03/0x06)
    Ventilation   p57 코일            · p58 홀딩 레지스터
    AHU           p60 코일            · p61~62 홀딩 레지스터
  표는 **전치**다 — 세로가 속성(Register·Function·Name·Object Name·Inactive/Active
  또는 Text-0~5), 가로가 포인트다. BACnet 쪽과 같은 조판이라 같은 방식으로 읽는다.

⚠ Text-n 칸에는 상태 이름만 오는 게 아니다. 'SET ROOM TEMPERATURE' 는 Text-0 이
   '°C' 인데 그건 **단위**다. 상태로 만들면 '0 = °C' 라는 거짓이 생긴다 —
   schema 의 단위 판정을 써서 가른다.
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import schema as SC  # noqa: E402  — 단위·상태 판정의 정본

MODEL_ID = "lg-ac-smart-bacnet-gateway"
DOC = "LG_ACSmart_BACnet_MFL69023101.pdf"
FAMILY = "LG/ACSmart-BACnet"

# 기기군 → (판 id, 쪽 목록, 원문이 부르는 이름)
GROUPS = [
    ("실내기", "modbus-tcp-indoor", [54, 55], ["Indoor unit"]),
    ("환기(ERV)", "modbus-tcp-ventilation", [57, 58], ["ERV"]),
    ("공조기(AHU)", "modbus-tcp-ahu", [60, 61, 62], ["AHU"]),
]

# 함수코드 — 원문 p53 표 그대로
FC = {
    "read single coil": (1, "coil", "R"),
    "coil read": (1, "coil", "R"),
    "write single coil": (5, "coil", "W"),
    "coil write": (5, "coil", "W"),
    "read holding registers": (3, "holding-register", "R"),
    "write single registers": (6, "holding-register", "W"),
    "write single register": (6, "holding-register", "W"),
}
ATTR = {"register": "reg", "function": "fn", "name": "name",
        "inactive": "s0", "active": "s1"}


def _c(x):
    return re.sub(r"\s+", " ", (x or "").replace("", "±")).strip()


def read_page(page):
    """전치 표 한 쪽 → 포인트 목록 [{reg, fn, name, obj, states[], unit}]"""
    out = []
    for t in page.find_tables().tables:
        data = [[_c(c) for c in r] for r in t.extract()]
        if len(data) < 3 or len(data[0]) < 3:
            continue
        rows = {}
        texts = []
        for r in data:
            key = (r[0] or "").lower()
            if key.startswith("object name"):
                rows["obj"] = r
            elif key.startswith("text-"):
                texts.append(r)
            else:
                for k, v in ATTR.items():
                    if key.startswith(k):
                        rows[v] = r
        if "reg" not in rows or "obj" not in rows:
            continue
        texts.sort(key=lambda r: r[0].lower())      # Text-0, Text-1 …
        cols = len(rows["reg"])
        fn = ""
        for j in range(1, cols):
            reg = rows["reg"][j] if j < len(rows["reg"]) else ""
            if not re.match(r"^\d+$", reg or ""):
                continue
            cell = rows.get("fn", [""] * cols)[j] if "fn" in rows else ""
            if cell:
                fn = cell
            obj = rows["obj"][j] if j < len(rows["obj"]) else ""
            if not obj:
                continue
            states, unit, ref = [], None, None
            if "s0" in rows or "s1" in rows:
                for code, key in (("0", "s0"), ("1", "s1")):
                    v = rows.get(key, [""] * cols)[j] if key in rows else ""
                    if v:
                        states.append({"code": code, "label": v})
            for i, tr in enumerate(texts):
                v = tr[j] if j < len(tr) else ""
                if not v:
                    continue
                # ⚠ 단위가 Text 칸에 앉아 있다('°C'). 상태로 만들면 거짓이 된다.
                if SC.canon_unit(v) and not SC.is_state_text(v):
                    unit = v
                elif v.lower().startswith("reference") and v.lower().endswith("code"):
                    # 값이 아니라 **참조**다 — 코드표가 이 문서에 없다.
                    # 상태로 만들면 '0 = Reference …' 라는 거짓이 생긴다.
                    # BACnet 판(ingest_lg.NOTE_CELLS)도 같은 문구를 statesRef 로 둔다.
                    ref = v
                else:
                    states.append({"code": str(i), "label": v})
            out.append({"reg": int(reg), "fn": fn, "ref": ref,
                        "name": rows.get("name", [""] * cols)[j] if "name" in rows else "",
                        "obj": obj, "states": states, "unit": unit})
    return out


def build(doc):
    ifaces = []
    for ko, iid, pages, applies in GROUPS:
        pts, seen, gaps = [], set(), []
        for pg in pages:
            if pg > doc.page_count:
                continue
            for r in read_page(doc[pg - 1]):
                fc = FC.get((r["fn"] or "").lower())
                if not fc:
                    gaps.append("함수코드를 못 알아본 줄: '%s' (레지스터 %d)"
                                % (r["fn"], r["reg"]))
                    continue
                code, refclass, rw = fc
                key = (refclass, rw, r["reg"])
                if key in seen:
                    continue
                seen.add(key)
                common = {"name": r["name"] or r["obj"], "shortName": r["obj"],
                          "readWrite": rw, "group": r["fn"]}
                if r["unit"]:
                    common["unitSI"] = SC.canon_unit(r["unit"]) or r["unit"]
                    common["unitSIRaw"] = r["unit"]
                if r["states"]:
                    common["states"] = r["states"]
                if r.get("ref"):
                    common["statesRef"] = r["ref"]
                pts.append({
                    "common": common,
                    "blocks": {"modbus": {"address": r["reg"], "addressBase": "1",
                                          "refClass": refclass,
                                          "functionCodes": [code]}},
                    "provenance": {"sourceFile": DOC, "sourcePage": pg,
                                   "family": FAMILY, "status": "extracted",
                                   "interfaceId": iid,
                                   "sourceColumns": {"Register": str(r["reg"]),
                                                     "Function": r["fn"],
                                                     "Name": r["name"],
                                                     "Object Name": r["obj"]}},
                })
        if not pts:
            continue
        ifaces.append({
            "id": iid, "label": "Modbus-TCP Point List : %s" % ko,
            "family": FAMILY, "protocols": ["modbus"],
            "sourceFile": DOC, "sourcePages": pages,
            "pageBase": "pdf",
            "pointCount": len(pts), "appliesTo": applies, "status": "extracted",
            "note": ("같은 게이트웨이의 **Modbus-TCP 통로**다(원문 p53 'Objects "
                     "(Modbus-TCP)'). BACnet 판과 같은 값을 다른 주소 체계로 낸다 — "
                     "코일은 함수코드 01h(읽기)/05h(쓰기), 홀딩 레지스터는 "
                     "03h(읽기)/06h(쓰기). 레지스터 번호는 기기 한 대 기준이고 "
                     "오브젝트 이름의 _XXX 가 유닛 주소다(BACnet 판과 같은 규칙)."),
            "gaps": (gaps or []) + [
                "레지스터 번호는 **기기 한 대 기준**이다. 여러 대를 붙일 때의 "
                "주소 오프셋 규칙은 원문 이 절에 없다 — BACnet 쪽은 인스턴스 식이 "
                "있지만 Modbus 쪽은 없다."],
            "points": pts,
        })
    return ifaces


def main(argv):
    import fitz
    run = "--run" in argv
    doc = fitz.open(os.path.join(DATA, "raw", DOC))
    ifaces = build(doc)
    tot = sum(len(i["points"]) for i in ifaces)
    print("Modbus-TCP 판 %d개 · %d점" % (len(ifaces), tot))
    for i in ifaces:
        c = collections.Counter(p["blocks"]["modbus"]["refClass"] for p in i["points"])
        rw = collections.Counter(p["common"]["readWrite"] for p in i["points"])
        print("  %-34s %3d점  %s · %s" % (i["label"][:34], len(i["points"]),
                                          dict(c), dict(rw)))
        for p in i["points"][:3]:
            print("       %-4s %-26s %s" % (p["blocks"]["modbus"]["address"],
                                            p["common"]["name"][:26],
                                            [s["label"] for s in
                                             (p["common"].get("states") or [])][:4]))

    mp = os.path.join(DATA, "models", MODEL_ID + ".json")
    m = json.load(io.open(mp, encoding="utf-8"))
    ids = {i["id"] for i in ifaces}
    keep = [i for i in (m.get("interfaces") or []) if i["id"] not in ids]
    m["interfaces"] = keep + ifaces
    n = sum(len(i["points"]) for i in m["interfaces"])
    m["summary"] = ("AC Smart BACnet 게이트웨이 — 판 %d개 · 오브젝트 %d점 "
                    "(BACnet %d · Modbus-TCP %d)"
                    % (len(m["interfaces"]), n, n - tot, tot))
    print("\n판 %d개 → %d개 · 합계 %d점" % (len(keep), len(m["interfaces"]), n))
    if not run:
        print("(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("→ %s" % os.path.relpath(mp, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
