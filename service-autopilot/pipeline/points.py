# -*- coding: utf-8 -*-
"""포인트 비고(note) 분해 — 한 칸에 뭉친 것을 열로 되돌린다.

무엇이 문제인가
  extract.py 는 원문에서 **열이 나뉘어 있던** 것을 ' · ' 로 이어 붙여 note 한 칸에
  넣는다(그리고 240자에서 자른다). 실측 note 21,219건 중 조각 2개 이상이 11,512건
  (54%), 상태 열거가 들어 있는 것이 5,559건(26%)이다.

  화면에서는 읽을 만하지만 **CSV 로 내보내면 그 한 칸을 다시 사람이 파싱해야 한다.**
  그리고 우리 목표에 이 정보들이 직접 쓰인다:

    상태 열거 (0=Auto 1=Forced Occupied)  → BMS 상태 텍스트 테이블
    쓰기 가능                              → 읽기전용 / 제어점 구분
    범위                                   → 시뮬레이터 클램프·유효성 검사
    Modbus 레지스터 · 원표기                → 실제 통신 설정값

  형번 CSV(export_units.py)는 이미 value/unit 을 나눠 두었다. 같은 기준을 포인트에도
  적용한다.

무엇을 하나
  원본 note 는 **건드리지 않는다**(비파괴). 되파싱해서 파생 열만 만든다.
  extract.py 를 고쳐 애초에 나눠 담는 것이 정답이지만 그건 97모델 재추출이라
  회귀 확인이 필요하다 — 먼저 여기서 얼마나 풀리는지 본다.

  ⚠ 240자에서 잘린 257건은 되파싱으로도 복구되지 않는다. 그건 extract.py 수정 몫이다.

실행
  PYTHONIOENCODING=utf-8 python points.py            # 얼마나 풀리는지 요약
  PYTHONIOENCODING=utf-8 python points.py --export   # CSV 3종 생성
  PYTHONIOENCODING=utf-8 python points.py --sample 12
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "datasets")

# extract.py 가 붙이는 조각 접두. 여기 없는 조각은 설명으로 본다.
TAGS = [
    ("origRaw",    "원표기 "),
    ("rangeRaw",   "범위 "),
    ("defaultRaw", "기본 "),
    ("condition",  "조건: "),
    ("code",       "코드 "),
    ("bacnetName", "BACnet "),
    ("regRaw",     "Modbus "),
]
WRITABLE = "쓰기 가능"

# 상태 열거 — '0 = Auto' / '1: Forced Occupied' 가 이어진다.
# 다음 '숫자=' 가 나오기 전까지를 라벨로 본다.
ENUM = re.compile(r"(-?\d+)\s*[=:]\s*(.*?)(?=\s*-?\d+\s*[=:]|$)")
# 값 범위 — '-40 – 230' · '0 to 100' · '0..100'
RANGE = re.compile(r"^\s*(-?[\d.,]+)\s*(?:–|-|~|\.\.\.?|to)\s*(-?[\d.,]+)")
NUM = re.compile(r"^-?[\d.,]+$")
TRUNC = 238          # extract.py 가 240 에서 자른다 — 그 언저리면 잘린 것으로 본다


def parse_note(note):
    """note 한 칸 → 구조화 dict. 못 알아본 것은 descr 에 그대로 남긴다."""
    out = {"descr": "", "writable": "", "states": [],
           "rangeMin": "", "rangeMax": "", "truncated": ""}
    for k, _ in TAGS:
        out[k] = ""
    if not note:
        return out
    if len(note) >= TRUNC:
        out["truncated"] = "Y"

    descr = []
    for piece in note.split(" · "):
        p = piece.strip()
        if not p:
            continue
        if p == WRITABLE:
            out["writable"] = "Y"
            continue
        hit = False
        for key, pre in TAGS:
            if p.startswith(pre):
                val = p[len(pre):].strip()
                out[key] = (out[key] + " / " + val) if out[key] else val
                hit = True
                break
        if not hit:
            descr.append(p)
    out["descr"] = " · ".join(descr)

    # 상태 열거는 범위 칸에도, 설명 칸에도 들어온다 — 둘 다 본다.
    for src in (out["rangeRaw"], out["descr"]):
        st = read_states(src)
        if len(st) >= 2:
            out["states"] = st
            break

    # 범위 칸이 열거가 아니라 진짜 수치 범위인 경우
    if not out["states"] and out["rangeRaw"]:
        m = RANGE.match(out["rangeRaw"])
        if m:
            out["rangeMin"], out["rangeMax"] = m.group(1), m.group(2)
    return out


def read_states(text):
    """'0 = Auto 1 = Forced' → [(0,'Auto'), (1,'Forced')]

    두 개 이상 이어져 있어야 열거로 본다. 문장 속 '값을 1 로' 같은 표현은
    등호·콜론이 없어 걸리지 않는다.
    """
    if not text:
        return []
    got = []
    for code, label in ENUM.findall(text):
        label = label.strip(" .,;·")
        if not label or NUM.match(label):
            continue
        got.append((code, label[:80]))
    return got if len(got) >= 2 else []


def load():
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        with open(f, encoding="utf-8") as fp:
            yield json.load(fp)


def iface_rows(m, base):
    """새 형식(interfaces[].points[]) → 같은 CSV 한 줄.

    왜 여기에 붙이나: BMS 가 가져가는 출구는 이 CSV 하나다. 구조가 둘로 갈렸다고
    출구도 둘이 되면 소비자가 두 벌을 합쳐야 한다 — **한 줄 모양은 그대로 두고
    판을 가리는 열(interfaceId·family·revision)과 프로토콜 열만 늘린다.**
    interfaceId 가 없으면 같은 제품의 다른 판이 CSV 에서 섞인다(D-016 이 막은 사고).
    """
    for it in (m.get("interfaces") or []):
        rev = it.get("revision") or {}
        for p in (it.get("points") or []):
            c = p.get("common") or {}
            b = p.get("blocks") or {}
            pv = p.get("provenance") or {}
            bac, mb = b.get("bacnet") or {}, b.get("modbus") or {}
            n2, lon = b.get("n2") or {}, b.get("lon") or {}
            yt, lg = b.get("yorktalk") or {}, b.get("logix") or {}
            value_range = c.get("rangeIP") or c.get("rangeSI") or {}
            # availability 는 계통마다 모양이 다르다 — SC-EQ 는 {raw,code,column},
            # E-Link 는 문자열 하나다. 둘 다 받는다.
            av = c.get("availability")
            av = av.get("raw") if isinstance(av, dict) else (av or "")
            r = dict(base)
            r.update({
                "interfaceId": it.get("id"), "family": it.get("family"),
                "revision": " ".join(x for x in (rev.get("doc"), rev.get("block"),
                                                 rev.get("firmware")) if x),
                "type": bac.get("objectType") or "", "inst": bac.get("instance"),
                "name": c.get("name") or lon.get("nvName") or "",
                "altNames": " | ".join(c.get("altNames") or []),
                "shortName": c.get("shortName") or "",
                "unit": c.get("unitIP") or c.get("unitSI") or "",
                "unitRaw": c.get("unitIPRaw") or c.get("unitSIRaw") or "",
                "sourceFile": pv.get("sourceFile") or "",
                "sourcePage": pv.get("sourcePage") or "",
                "writable": c.get("readWrite") or "",
                "modbusRegister": mb.get("address", ""),
                "modbusBase": mb.get("addressBase") or "",
                "modbusRefClass": mb.get("refClass") or "",
                "modbusScaleFactor": mb.get("scaleRaw") or "",
                "modbusSignedFlag": mb.get("dataType") or "",
                "n2": ("%s %s" % (n2.get("pointType") or "", n2.get("address"))).strip()
                      if n2 else "",
                "lon": lon.get("snvtType") or lon.get("nvName") or "",
                "yorktalk": yt.get("coord") or yt.get("pageRef") or "",
                "logix": lg.get("tag") or "",
                "condition": av,
                "descr": c.get("note") or "",
                "rangeMin": value_range.get("min", ""),
                "rangeMax": value_range.get("max", ""),
                "rangeRaw": ("%s – %s" % (value_range.get("min"), value_range.get("max"))
                             if value_range else ""),
                "bacnetName": bac.get("objectName") or "",
                "noteRaw": "",
            })
            states = [(s.get("code"), s.get("label"))
                      for s in (c.get("states") or []) if s.get("label")]
            # 옛 형식 전용 파생 열은 빈 값으로 채운다 — 요약·CSV 가 열을 항상 기대한다
            for k in FIELDS:
                r.setdefault(k, "")
            r["stateCount"] = len(states)
            yield r, states


def rows():
    for m in load():
        base = {"modelId": m.get("id"), "equipId": m.get("equipId"),
                "vendor": m.get("vendor"), "model": m.get("model")}
        for r in iface_rows(m, base):
            yield r
        for p in (m.get("points") or []):
            d = parse_note(p.get("note"))
            r = dict(base)
            r.update({"type": p.get("type"), "inst": p.get("inst"),
                      "name": p.get("name"), "unit": p.get("unit") or "",
                      "unitRaw": p.get("unitRaw") or "",
                      "sourceFile": p.get("sourceFile") or "",
                      "sourcePage": p.get("sourcePage") or "",
                      "bacOid": p.get("bacOid") or "",
                      "modbusRegister": p.get("modbusRegister") or "",
                      "modbusScaleFactor": p.get("modbusScaleFactor") or "",
                      "modbusBooleanFlag": p.get("modbusBooleanFlag") or "",
                      "modbusSignedFlag": p.get("modbusSignedFlag") or "",
                      "modbusOffset": p.get("modbusOffset") or "",
                      "modbusWritableFlag": p.get("modbusWritableFlag") or "",
                      "noteRaw": p.get("note") or ""})
            r.update({k: v for k, v in d.items() if k != "states"})
            r["stateCount"] = len(d["states"])
            yield r, d["states"]


# 새 열은 **뒤에 붙인다** — 앞 열 순서를 바꾸면 이 CSV 를 읽던 쪽이 깨진다.
FIELDS = ["modelId", "equipId", "vendor", "model", "type", "inst", "name",
          "unit", "unitRaw", "sourceFile", "sourcePage", "writable",
          "bacOid", "modbusRegister", "modbusScaleFactor", "modbusBooleanFlag",
          "modbusSignedFlag", "modbusOffset", "modbusWritableFlag",
          "rangeMin", "rangeMax", "rangeRaw", "defaultRaw", "regRaw",
          "origRaw", "bacnetName", "condition", "code",
          "stateCount", "truncated", "descr", "noteRaw",
          "interfaceId", "family", "revision", "shortName", "altNames",
          "modbusBase", "modbusRefClass", "n2", "lon", "yorktalk", "logix"]
STATE_FIELDS = ["modelId", "type", "inst", "name", "stateCode", "stateLabel", "interfaceId"]


def export():
    os.makedirs(OUT, exist_ok=True)
    pts, sts = [], []
    for r, states in rows():
        pts.append(r)
        for code, label in states:
            sts.append({"modelId": r["modelId"], "interfaceId": r.get("interfaceId", ""),
                        "type": r["type"], "inst": r["inst"], "name": r["name"],
                        "stateCode": code, "stateLabel": label})
    write(os.path.join(OUT, "points.csv"), pts, FIELDS)
    write(os.path.join(OUT, "point-states.csv"), sts, STATE_FIELDS)
    print("  data/datasets/points.csv        %d행" % len(pts))
    print("  data/datasets/point-states.csv  %d행" % len(sts))


def write(path, data, fields):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in data:
            w.writerow(r)


def summarize(sample=0):
    n = 0
    c = Counter()
    samples = []
    for r, states in rows():
        n += 1
        if r["noteRaw"]:
            c["note 있음"] += 1
        for k in ("writable", "rangeMin", "regRaw", "origRaw", "bacnetName",
                  "condition", "code", "defaultRaw"):
            if r[k]:
                c[k] += 1
        if states:
            c["states(상태 열거)"] += 1
            c["  상태 행 합계"] += len(states)
            if sample and len(samples) < sample:
                samples.append((r, states))
        if r["truncated"]:
            c["truncated(240자 절단)"] += 1
        if r["noteRaw"] and not (states or r["writable"] or r["rangeMin"]
                                or any(r[k] for k, _ in TAGS)):
            c["설명뿐 — 분해할 것 없음"] += 1
    print("포인트 %d건" % n)
    for k, v in c.most_common():
        print("  %-22s %6d" % (k, v))
    if samples:
        print("\n상태 열거 분해 예시")
        for r, st in samples:
            print("  %s %s-%s %s" % (r["modelId"][:26], r["type"], r["inst"],
                                     (r["name"] or "")[:34]))
            for code, label in st[:5]:
                print("      %-4s → %s" % (code, label))


def main(argv):
    ap = argparse.ArgumentParser(description="포인트 비고 분해")
    ap.add_argument("--export", action="store_true", help="CSV 생성")
    ap.add_argument("--sample", type=int, default=0, help="분해 예시 N건")
    a = ap.parse_args(argv)
    summarize(a.sample)
    if a.export:
        print()
        export()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
