# -*- coding: utf-8 -*-
"""LS ELECTRIC H100 — 내장 RS-485(LS INV 485 / Modbus-RTU) 공통영역 맵 취입.

  PYTHONIOENCODING=utf-8 python ingest_ls_rs485.py          바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_ls_rs485.py --run    실제로 기록한다

무엇을 세우나
  같은 제품(H100)의 **두 번째 판**이다(D-016). 첫째는 BACnet/IP 옵션 카드가 내보내는
  오브젝트 76점(ingest_ls), 이쪽은 **본체에 내장된 RS-485** 가 여는 레지스터 창이다.
  두 판은 같은 값을 다른 통로로 낸다 — 한 배열에 뭉치면 어느 통로인지 잃는다.

  ✅ BACnet 쪽 AI13~AI19 가 '(Refer to the common area parameter address 0h0305)' 라고
     가리키던 그 표가 바로 이것이다. 두 판이 여기서 맞물린다.

원문 구조 (본체 매뉴얼 633쪽 중 PDF 374~392)
    7.3.8   Compatible Common Area Parameter        0h0000~0h001B
    7.3.9.1 Monitoring Area Parameter (Read Only)   0h0300~
    7.3.9.2 Control Area Parameter (Read/Write)     0h0380~
    7.3.9.3 Inverter Memory Control Area Parameter  0h03E0~
  머리글: Comm. Address | Parameter | Scale | Unit | R/W | Assigned Content by Bit
  (7.3.9.2·7.3.9.3 은 R/W 열이 없다 — 절 제목이 이미 읽기/쓰기를 밝힌다.)

⚠ 'Assigned Content by Bit' 에는 두 가지가 섞여 온다.
    · '0: 0.75kW, 1: 1.5kW, …' 같은 **코드 열거** → states
    · 'B15 … B0 …' 같은 **비트필드** → 스키마에 담을 자리가 없다.
      원문 그대로 두고 gap 에 적는다. 비트 배정을 states 로 만들면 코드값이 거짓이 된다.

⚠ Scale 열은 분해능이다 — '0.1 / A' 는 원시값 1이 0.1A 라는 뜻이다.
  즉 공학값 = 원시값 × 0.1 (point-schema 의 정의 방향과 같다).
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

SRC_ID = "ls-electric-h100"
DOC = "LS_H100_UserManual_EN_190621.pdf"
MODEL_ID = "ls-electric-h100-vfd"
IFACE_ID = "rs485-modbus"
FAMILY = "Drive/Modbus"          # 이미 있는 계통이다 — 드라이브가 여는 레지스터 창

# 절 → (쪽 범위, 화면 이름, 절이 밝힌 읽기/쓰기)
SECTIONS = [
    ("7.3.8 Compatible Common Area Parameter", 374, 377, None),
    ("7.3.9.1 Monitoring Area Parameter (Read Only)", 379, 387, "R"),
    ("7.3.9.2 Control Area Parameter (Read/Write)", 388, 390, "R/W"),
    ("7.3.9.3 Inverter Memory Control Area Parameter (Read and Write)", 391, 392, "R/W"),
]

ADDR = re.compile(r"^0h([0-9A-Fa-f]{4})$")
BIT = re.compile(r"\bB\d{1,2}\b")
# ⚠ 쉼표로만 가르면 안 된다 — 원문이 구분자를 들쎄날쎄 쓴다
#   ('0: 0.75kW, 1: 1.5kW, 2: 2.2kW 3: 3.7kW 4: 5.5kW, 5: 7.5kW …').
#   쉼표만 보면 '2: 2.2kW 3: 3.7kW 4: 5.5kW' 가 한 라벨이 된다(실측).
#   다음 코드가 나올 때까지를 라벨로 본다.
CODE = re.compile(r"(-?\d+)\s*:\s*(.+?)(?=\s*,?\s*-?\d+\s*:|$)")
HEADLBL = ("Comm.", "Address", "Parameter", "Scale", "Unit", "R/W",
           "Assigned Content by Bit", "Assigned content by bit",
           "Changeable", "During", "Running", "Function")


def ledger_entry():
    led = json.load(io.open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    for url, v in led.items():
        if v.get("source") == SRC_ID and v.get("file") == DOC:
            return url, v
    raise SystemExit("대장에 %s / %s 가 없다 — collect.py --run %s" % (SRC_ID, DOC, SRC_ID))


def printed_no(page, fallback):
    for line in page.get_text().splitlines()[:4]:
        s = line.strip()
        if s.isdigit() and 1 <= int(s) <= 999:
            return int(s)
    return fallback


def frags(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines") or []:
            for sp in l["spans"]:
                s = sp["text"].strip()
                if s:
                    out.append({"y": round(sp["bbox"][1], 1),
                                "x": round(sp["bbox"][0], 1), "t": s})
    out.sort(key=lambda f: (f["y"], f["x"]))
    return out


def bands(page):
    """행 경계는 표 격자에서 가져온다 — 값이 여러 줄인 행이 많다(비트필드)."""
    # ⚠ 격자가 한 행을 여러 조각으로 더 쪼갠다. 안쪽 조각을 남기면 **행의 첫 줄이
    #    잘린다** — 주소가 셀 안에서 가운데 정렬이라 이름의 첫 줄이 주소보다 위에
    #    있기 때문이다(실측: 0h0002 가 'Inverter input voltage' 인데 'voltage' 만 남았다).
    #    겹치지 않는 것 중 **큰 것부터** 골라 진짜 행 경계를 되살린다.
    cand = []
    for tb in page.find_tables().tables:
        for r in tb.rows:
            y0, y1 = round(r.bbox[1], 1), round(r.bbox[3], 1)
            if 4 < y1 - y0 < 420:
                cand.append((y0, y1))
    out = []
    for b in sorted(set(cand), key=lambda b: b[0] - b[1]):     # 높이 큰 것부터
        if not any(b[0] < o[1] and o[0] < b[1] for o in out):
            out.append(b)
    return sorted(out)


def anchors(fs):
    """머리글에서 열 x 를 얻는다. 못 얻으면 그 쪽은 건너뛴다(짐작하지 않는다)."""
    a = {}
    for f in fs:
        if f["t"] in ("Parameter", "Scale", "Unit", "R/W") and f["t"] not in a:
            a[f["t"]] = f["x"]
        if f["t"].lower().startswith("assigned") and "Content" not in a:
            a["Content"] = f["x"]
        if f["t"] == "Function" and "Content" not in a:
            a["Content"] = f["x"]
    return a


def read_page(page, prev=None):
    """이어지는 쪽에는 머리글이 없다 — 앞 쪽의 열 위치를 물려받는다."""
    fs = frags(page)
    first = min([f["y"] for f in fs if ADDR.match(f["t"])] or [10 ** 6])
    a = anchors([f for f in fs if f["y"] < first]) or {}
    if "Parameter" not in a or "Content" not in a:
        a = prev or {}
    if "Parameter" not in a or "Content" not in a:
        return [], a
    bd = bands(page)
    # ⚠ 머리글 끝을 HEADLBL 전체로 재면 안 된다 — 'R/W' 는 머리글 낱말이면서
    #    **데이터에도 나온다**(R/W 열의 값이다). 그걸로 재면 머리글 끝이 표 아래로
    #    내려가 행이 통째로 잘린다(실측: 7행 중 1행만 남았다).
    #    첫 주소보다 **위에 있는** 머리글 낱말만 본다.
    hy = max([f["y"] for f in fs if f["t"] in HEADLBL and f["y"] < first] or [0])
    body = [f for f in fs if f["y"] > hy + 2]

    rows = []
    for f in body:
        if not ADDR.match(f["t"]):
            continue
        band = next((b for b in bd if b[0] - 1 <= f["y"] < b[1]), None)
        lo, hi = (band[0] - 1, band[1]) if band else (f["y"] - 8, f["y"] + 10)
        # ⚠ 격자가 두 행을 한 밴드로 묶어 놓기도 한다 — 그러면 아랫행 이름이
        #    윗행으로 딸려 간다(실측: 0h03E5 가 0h03E6 의 이름까지 먹었다).
        #    같은 밴드에 다른 주소가 있으면 그 중간에서 자른다.
        for g in body:
            if g is f or not ADDR.match(g["t"]) or not (lo <= g["y"] < hi):
                continue
            mid = (f["y"] + g["y"]) / 2.0
            if g["y"] < f["y"]:
                lo = max(lo, mid)
            else:
                hi = min(hi, mid)
        seg = [g for g in body if lo <= g["y"] < hi]
        col = collections.defaultdict(list)
        for g in seg:
            if ADDR.match(g["t"]):
                continue
            x = g["x"]
            if x < a["Parameter"] - 6:
                continue
            # ⚠ 왼쪽 칸(이름·배율·단위·R/W)은 주소 곁에 짧게 붙고, **내용 칸만**
            #    세로로 길다(비트 배정이 열두 줄이기도 하다). 그래서 왼쪽 칸에는
            #    좁은 창을 씌운다 — 안 그러면 윗행 이름의 꼬리가 딸려 온다
            #    (실측: 0h0340 이 윗행의 'Fdb' 를, 0h03E7 이 'codes' 를 먹었다).
            if x < a["Content"] - 6 and abs(g["y"] - f["y"]) > 9:
                continue
            if x < a.get("Scale", 10 ** 6) - 6:
                col["name"].append(g)
            elif x < a.get("Unit", 10 ** 6) - 6:
                col["scale"].append(g)
            elif x < a.get("R/W", a["Content"]) - 6:
                col["unit"].append(g)
            elif x < a["Content"] - 6:
                col["rw"].append(g)
            else:
                col["content"].append(g)
        # ⚠ y 로만 정렬하면 위첨자가 앞으로 튄다 — '1st' 가 'st' + '1' 로 갈려
        #    'the number of st poles for the 1 motor' 가 된다(실측).
        #    같은 줄로 볼 만큼 가까운 y 는 한 칸으로 묶고 x 로 읽는다.
        join = (lambda k, sep=" ": re.sub(
            r"\s+", " ", sep.join(g["t"] for g in sorted(
                col[k], key=lambda g: (round(g["y"] / 4.0), g["x"])))).strip())
        # 위첨자 서수는 조각이 갈려 '1 st motor' 가 된다 — 영어 서수는 붙여 쓴다
        nm = re.sub(r"(\d)\s+(st|nd|rd|th)\b", r"\1\2", join("name"))
        rows.append({"addr": f["t"].upper().replace("0H", "0h"),
                     "name": nm, "scale": join("scale"),
                     "unit": join("unit"), "rw": join("rw"),
                     "content": join("content")})
    return rows, a


def collect(doc):
    out = []
    for title, p0, p1, rw in SECTIONS:
        n, anc = 0, None
        for p in range(p0, p1 + 1):
            page = doc[p - 1]
            got, anc = read_page(page, anc)
            for r in got:
                r.update({"section": title, "page": p,
                          "printed": printed_no(page, p), "sectionRW": rw})
                out.append(r)
                n += 1
        if not n:
            raise SystemExit("절 %r 에서 한 행도 못 읽었다 (PDF %d~%d)" % (title, p0, p1))
    return out


def crosscheck(doc, rows):
    """쪽 글자 흐름에서 '주소'와 '이름'이 **서로 곁에** 있는지 다시 읽어 맞춘다.

    본 판독이 좌표이므로 대조는 글자 흐름 쪽으로 한다 — 같은 경로로 두 번 읽으면
    같은 맹점을 그대로 통과한다.
    ⚠ 순서로 맞추면 안 된다. 이 문서는 행에 따라 이름이 주소보다 **먼저** 나온다
       ('Inverter model' 다음에 '0h0300'). 그래서 앞뒤 어느 쪽이든 가까이 있으면
       맞은 것으로 본다.
    ⚠ 표 인식(find_tables)으로도 못 한다. 이 표는 격자가 한 행을 여러 조각으로
       쪼개서 주소와 이름이 **다른 행**으로 떨어진다(실측: 그렇게 재니 49.7% 였다).
    """
    flat, win = {}, 160
    for p in {r["page"] for r in rows}:
        flat[p] = re.sub(r"\s+", "", doc[p - 1].get_text()).lower()
    same, diff = 0, []
    for r in rows:
        f, ad = flat[r["page"]], r["addr"].lower()
        nm = re.sub(r"\s+", "", r["name"]).lower()
        ok = False
        for m in re.finditer(re.escape(ad), f):
            if nm and nm in f[max(0, m.start() - win): m.end() + win]:
                ok = True
                break
        if ok:
            same += 1
        elif len(diff) < 8:
            diff.append("%s %s" % (r["addr"], r["name"][:26]))
    return {"method": "쪽 글자 흐름에서 주소 곁에 이름이 있는지 다시 읽어 맞췄다"
                      "(본 판독은 좌표 경로다)",
            "total": len(rows), "both": same,
            "rate": round(same / len(rows), 4) if rows else 0.0, "diff": diff}


def build_points(meta, rows):
    pts, seen = [], set()
    for r in rows:
        if r["addr"] in seen:
            continue
        seen.add(r["addr"])
        common = {"name": r["name"]}
        gaps = []
        if r["unit"] and r["unit"] != "-":
            common["unitSI"] = common["unitSIRaw"] = r["unit"]
        rw = r["rw"] if r["rw"] in ("R", "W", "R/W") else r["sectionRW"]
        if rw:
            common["readWrite"] = rw
        content = r["content"]
        if content and content != "-":
            if BIT.search(content):
                # 비트필드다 — 스키마에 담을 자리가 없다. 코드 열거로 만들면
                # 'B15' 의 배정 내용이 present-value 처럼 읽혀 거짓이 된다.
                common["note"] = content
                gaps.append("common.states — 값이 코드 열거가 아니라 **비트필드**다"
                            "(B15~B0 배정). 포인트 스키마에 비트 배정을 담을 자리가 "
                            "없어 원문 그대로 note 에 두었다.")
            else:
                codes = CODE.findall(content)
                if len(codes) >= 2:
                    common["states"] = [{"code": c, "label": l.strip()}
                                        for c, l in codes]
                else:
                    common["note"] = content
        mod = {"address": int(r["addr"][2:], 16), "addressBase": "1-base",
               "refClass": "holdingRegister"}
        if re.match(r"^\d*\.?\d+$", r["scale"] or "") and float(r["scale"]) != 1:
            # Scale 열은 분해능이다 — '0.1 / A' 는 원시값 1이 0.1A 라는 뜻이다.
            mod["scale"], mod["scaleRaw"] = float(r["scale"]), r["scale"]
        pts.append({
            "common": common,
            "blocks": {"modbus": mod},
            "provenance": {
                "sourceFile": meta["file"], "sourcePage": r["printed"],
                "family": FAMILY,
                "sourceColumns": {
                    "Comm. Address": r["addr"], "Parameter": r["name"],
                    "Scale": r["scale"] or "-", "Unit": r["unit"] or "-",
                    "R/W": r["rw"] or "-",
                    "Assigned Content by Bit": content or "-",
                    "절": r["section"],
                },
                "status": "extracted", "interfaceId": IFACE_ID,
                **({"gaps": gaps} if gaps else {}),
            },
        })
        pts[-1]["common"]["group"] = r["section"]
    return pts


def main(argv):
    import fitz
    run = "--run" in argv
    url, meta = ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, SRC_ID))
    doc = fitz.open(path)

    rows = collect(doc)
    cc = crosscheck(doc, rows)
    pts = build_points(meta, rows)

    per = collections.Counter(p["common"]["group"] for p in pts)
    print("판 %s — %d점 (원문 행 %d · 주소 중복 %d 제외)"
          % (IFACE_ID, len(pts), len(rows), len(rows) - len(pts)))
    for title, _p0, _p1, _rw in SECTIONS:
        print("   %-62s %3d점" % (title[:62], per[title]))
    print("   상태 %d · 단위 %d · 배율 %d · 비트필드 %d"
          % (sum(1 for p in pts if p["common"].get("states")),
             sum(1 for p in pts if p["common"].get("unitSI")),
             sum(1 for p in pts if p["blocks"]["modbus"].get("scale")),
             sum(1 for p in pts if any("비트필드" in g
                                       for g in (p["provenance"].get("gaps") or [])))))
    print("   교차 대조 %d/%d = %.1f%%" % (cc["both"], cc["total"], 100 * cc["rate"]))
    if cc["diff"]:
        print("   ⚠ 안 맞은 것:", " · ".join(cc["diff"]))

    mp = os.path.join(DATA, "models", MODEL_ID + ".json")
    model = json.load(io.open(mp, encoding="utf-8"))
    iface = {
        "id": IFACE_ID, "label": "내장 RS-485 (LS INV 485 / Modbus-RTU)",
        "family": FAMILY, "protocols": ["modbus"],
        "sourceFile": meta["file"],
        "sourcePages": sorted({p["provenance"]["sourcePage"] for p in pts}),
        "pointCount": len(pts), "appliesTo": ["H100"], "status": "extracted",
        "note": ("본체에 내장된 RS-485 가 여는 공통영역 레지스터 창. BACnet/IP 옵션 "
                 "카드 판(bacnet-ip)과 **같은 제품의 다른 통로**다 — 그 판의 AI13~AI19 가 "
                 "'Refer to the common area parameter address 0h0305' 라고 가리키던 "
                 "표가 바로 이것이다. 주소는 원문이 16진('0h0305')으로 적고 여기서는 "
                 "10진으로 정규화했다(원표기는 sourceColumns 에). Scale 열은 분해능이라 "
                 "공학값 = 원시값 × Scale 이다."),
        "crosscheck": cc,
        "gaps": ["비트필드 행(B15~B0 배정)은 states 로 만들지 않았다 — 스키마에 비트 "
                 "배정을 담을 자리가 없다. 원문 그대로 note 에 있다.",
                 "슬레이브 ID·통신속도는 현장 설정값이라 이 표에 없다(원문 COM 그룹)."],
        "points": pts,
    }
    others = [i for i in (model.get("interfaces") or []) if i["id"] != IFACE_ID]
    # 먼저 들어온 판(BACnet)의 대조 결과가 모델 자리에만 있었다 — 판으로 옮긴다.
    old = model.get("crosscheck") or {}
    for o in others:
        if "crosscheck" not in o and old.get("total"):
            o["crosscheck"] = old
    model["interfaces"] = others + [iface]
    total = sum(len(i["points"]) for i in model["interfaces"])
    # 모델 자리에는 판들의 **합**을 둔다 — 76/76 만 적혀 있으면 233점 중
    # 76점만 잰 것처럼 읽힌다.
    tot = sum((i.get("crosscheck") or {}).get("total", 0) for i in model["interfaces"])
    both = sum((i.get("crosscheck") or {}).get("both", 0) for i in model["interfaces"])
    model["crosscheck"] = {
        "method": "판마다 다른 경로로 다시 읽어 맞췄다 — 자세한 것은 "
                  "interfaces[].crosscheck 에 있다",
        "total": tot, "both": both,
        "rate": round(both / tot, 4) if tot else 0.0, "diff": []}
    model["summary"] = ("BACnet/IP 옵션 매뉴얼 + 본체 매뉴얼 · 판 %d개에서 취입 — "
                        "오브젝트 %d점" % (len(model["interfaces"]), total))
    if not run:
        print("\n(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n→ %s  (판 %d · 합계 %d점)"
          % (os.path.relpath(mp, HERE), len(model["interfaces"]), total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
