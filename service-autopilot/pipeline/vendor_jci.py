# -*- coding: utf-8 -*-
"""JCI Simplicity SE 오브젝트 보강 — Premier Start-Up 가이드의 BACnet Points List.

왜 벤더 전용인가
  회사마다 포인트 문서의 생김새가 다르다. 문서 유형으로 규칙을 세우려다 실패했다 —
  JCI 는 장비의 Start-Up & Operation Guide 안에 포인트 표가 있는데, AAON 은 IOM 에
  없고 Technical Guide 에 있다. 일반 규칙은 벤더마다 깨진다.
  정격 쪽에서 이미 같은 결론에 도달해 vendor_aaon·vendor_lennox·vendor_lg·
  vendor_mitsubishi·vendor_systemair 를 따로 두었다. 오브젝트 쪽도 같게 간다.

JCI 문서 두 종의 역할이 다르다
  ① 5177447-UTS-A-1215  Technical Supplement: Simplicity SE Point Mapping (Firmware v1072)
     → 이름·BACOid·Modbus 레지스터. **타입도 단위도 없다.** 우리 모델의 정본.
  ② 5586996-JSG-A-520   25–50 Ton Premier RTU Start-Up & Operation Guide, Table 32
     → BACnet Attributes | Object Type | Object ID | Read/Write | Short | Long | Point Definitions (Units)
     → **타입·단위·상태열거·읽기쓰기가 여기 있다.**

  둘은 같은 Simplicity SE 오브젝트 공간(29500~30079)을 쓰므로 **Object ID 로 잇는다**.
  다만 완전히 겹치지는 않는다 — ①은 v1072 초집합, ②는 2020년 대형기 실목록이라
  겹침 185 / 우리만 179 / 저쪽만 137 이다. 못 채운 것은 지어내지 않고 그대로 둔다.

  ⚠ 이름은 ①이 서술형('Supply Air Temperature'), ②가 약칭('DAT')이라 **이름으로 잇지
  않는다.** 실측 유사도가 3%까지 떨어진다 — Object ID 만이 신뢰할 수 있는 열쇠다.

실행
  PYTHONIOENCODING=utf-8 python vendor_jci.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci.py --apply
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
sys.path.insert(0, HERE)
import specs as SP  # noqa: E402

SRC = "JCI_SunPremier_25-50t_StartUp_5586996-JSG-A-520.pdf"
TARGET = "johnson-controls-york-simplicity-se-smart-equipment-york-rooftop-units-modbus"

OID = re.compile(r"^\d{4,6}$")
# 'Point Definitions (Units)' 칸은 설명 문장 + 괄호 단위 + 상태 열거가 한데 있다.
#   'Displays the active ZT (°F)'
#   'A BAS command to adjust ZT alarm setpoint offset (0.0–25.0°F)'
#   '0 = Normal 1 = Pressurize 2 = Depressurize 3 = Purge 4 = Shutdown'
UNIT_PAREN = re.compile(r"\(([^()]{1,28})\)")
UNIT_TOKEN = re.compile(
    r"(°F|°C|℃|%RH|%|ppm|psi|inWC|in\. wg|in wg|CFM|GPM|kW|W|V|A|Hz|rpm|"
    r"minutes|minute|min|seconds|sec|hours|hour|hrs)\s*$", re.I)
STATE = re.compile(r"(-?\d+)\s*=\s*(.*?)(?=\s*-?\d+\s*=|$)")


def unit_of(text):
    """괄호 안 꼬리에서 단위만 집는다. 범위(0.0–25.0°F)면 단위 부분만 남긴다."""
    for m in UNIT_PAREN.finditer(text or ""):
        inner = m.group(1).strip()
        u = UNIT_TOKEN.search(inner)
        if u:
            return u.group(1)
    return ""


def states_of(text):
    """'0 = Normal 1 = Pressurize' → [(코드, 라벨)]. 두 개 이상이어야 열거로 본다."""
    got = []
    for code, label in STATE.findall(text or ""):
        label = label.strip(" .,;·")
        if not label or re.match(r"^-?[\d.]+$", label):
            continue
        got.append((code, label[:80]))
    return got if len(got) >= 2 else []


def parse_points_list(pdf=None):
    """Table 32 → {objectId: {...}}"""
    import fitz
    path = pdf or os.path.join(RAW, SRC)
    doc = fitz.open(path)
    out = {}
    for pi, pg in enumerate(doc):
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if not data or len(data[0]) != 7:
                continue
            head = " ".join(SP._c(c) for c in data[0])
            if "Object Type" not in head:
                continue
            for r in data[1:]:
                c = [SP._c(x) for x in r]
                if not OID.match(c[2] or ""):
                    continue
                defs = c[6] or ""
                out[int(c[2])] = {
                    "attr": c[0], "type": c[1], "rw": c[3],
                    "short": c[4], "long": c[5], "defs": defs,
                    "unit": unit_of(defs), "states": states_of(defs),
                    "page": pi + 1,
                }
    doc.close()
    return out


# JCI 표기 → 우리 타입 코드. 문서에 없는 타입은 만들지 않는다.
TYPE_MAP = {"AV": "AV", "MV": "MSV", "CSV": "CSV", "BV": "BV",
            "AI": "AI", "BI": "BI", "AO": "AO", "BO": "BO"}


def apply_to_model(model_id, dry=True):
    ref = parse_points_list()
    path = os.path.join(DATA, "models", "%s.json" % model_id)
    m = json.load(open(path, encoding="utf-8"))
    pts = m.get("points") or []
    hit = t_set = u_set = s_set = rw_set = 0
    for p in pts:
        oid = p.get("bacOid")
        r = ref.get(oid) if oid else None
        if not r:
            continue
        hit += 1
        ty = TYPE_MAP.get(r["type"])
        if ty and p.get("type") != ty:
            if not dry:
                p["type"] = ty
            t_set += 1
        if r["unit"] and not p.get("unit"):
            if not dry:
                p["unit"] = r["unit"]
                p["unitRaw"] = r["unit"]
            u_set += 1
        if r["states"] and not p.get("states"):
            if not dry:
                p["states"] = [{"code": c, "label": l} for c, l in r["states"]]
            s_set += 1
        if r["rw"] and not p.get("readWrite"):
            if not dry:
                p["readWrite"] = r["rw"]
            rw_set += 1
        if not dry:
            p["typeSource"] = SRC
    miss = sum(1 for p in pts if p.get("bacOid") and p["bacOid"] not in ref)
    print("참조 문서 %d점 · 모델 %d점" % (len(ref), len(pts)))
    print("  Object ID 매칭 %d · 미매칭 %d" % (hit, miss))
    print("  타입 %d · 단위 %d · 상태열거 %d · 읽기쓰기 %d" % (t_set, u_set, s_set, rw_set))
    if not dry:
        gap = m.get("gap") or ""
        note = ("Simplicity SE 오브젝트 %d점 중 %d점은 타입·단위 미상 — 정본 문서"
                "(%s)에 두 열이 없고, 보강 문서(%s)는 v1072 이후 판이라 대역이 어긋난다."
                % (len(pts), miss, m.get("sourceDoc"), SRC))
        if note not in gap:
            m["gap"] = (gap + " " if gap else "") + note
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
        print("  반영 완료 — %s" % os.path.basename(path))
    else:
        print("  (미리보기 — --apply 로 실제 반영)")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="JCI Simplicity SE 오브젝트 보강")
    ap.add_argument("--scan", action="store_true", help="참조 문서 파싱 결과 요약")
    ap.add_argument("--apply", action="store_true", help="모델에 반영")
    ap.add_argument("--model", default=TARGET)
    a = ap.parse_args(argv)

    if a.scan:
        ref = parse_points_list()
        import collections
        print("Table 32 파싱: %d점" % len(ref))
        print("  타입:", dict(collections.Counter(v["type"] for v in ref.values())))
        print("  단위 있는 점: %d" % sum(1 for v in ref.values() if v["unit"]))
        print("  상태열거 있는 점: %d" % sum(1 for v in ref.values() if v["states"]))
        print()
        print("  단위 표본:")
        for v in list(ref.values()):
            if v["unit"]:
                print("     %-26s %-5s %s" % (v["attr"][:26], v["unit"], v["defs"][:52]))
        return 0
    return apply_to_model(a.model, dry=not a.apply)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
