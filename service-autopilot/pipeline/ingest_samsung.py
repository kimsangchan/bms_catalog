# -*- coding: utf-8 -*-
"""삼성 MIM-B17BN BACnet 게이트웨이 / DMS2.5 — 오브젝트 목록 취입.

  PYTHONIOENCODING=utf-8 python ingest_samsung.py            바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_samsung.py --run      실제로 기록한다

무엇을 세우나
  제품 = BACnet 게이트웨이 하나, 판 = 기기군(실내기 Basic/Advanced · AHU 킷 ·
  EHS · ERV · DVM CHILLER · SIM/PIM · 중앙제어기 · 실외기 인터페이스 모듈 ·
  게이트웨이 · DDC). LG AC Smart 를 세운 것과 같은 자리다(D-016).

⚠ **표 인식(find_tables)으로 읽지 않는다.**
  이 문서는 밑줄이 조각으로 떨어져 셀값이 'ACRoomTempxxxxxxxx _ _' 로 나온다
  (원문은 'AC_RoomTemp_xx_xxxxxx'). 최후 방어선인 앵커 정규식을 그 앞에 걸면
  오염된 값이 **그냥 통과한다**(point-schema artifactCleanupFirst).
  그래서 **글자 조각의 좌표**로 읽는다 — 조각마다 x 를 보고 열을 정한다.

⚠ 글자 흐름 순서(get_text())도 못 쓴다.
  한 쪽에 표가 둘일 때 캡션이 앞 표의 행들 **뒤에** 나온다(E-63 실측).
  좌표로 다시 세워야 사람이 보는 순서가 된다.

⚠ 값 칸의 뜻은 **오브젝트 타입**이 정한다 — LG 와 같은 짜임이다.
  머리글이 'Unit | Inactive | Active | Text-1~Text-5' 인데 Unit 과 Text-1 의 x 가
  거의 같다(255.4 vs 253.0). 열 위치로는 못 가른다.
    아날로그(AI/AO/AV) → 첫 값이 단위
    이진(BI/BO/BV)     → 0=Inactive · 1=Active
    멀티스테이트(MI/MO/MV) → Text-N 이 그대로 상태값이다(1부터)
  ✅ 1부터인 근거가 원문 안에 있다 — 실내기 16번 AC_FanFlow 의 값이 표가 아니라
     문장으로 '1: None, 2: Vertical, 3: Horizon, …' 이라고 적혀 있다.

⚠ 인스턴스 번호는 표가 준다(LG 와 다른 점). 대신 **이름에 자리표시**가 있다
  ('AC_RoomTemp_xx_xxxxxx'). 그 xx 가 무엇인지 이 문서는 밝히지 않는다 —
  E-61 이 주는 것은 **Device ID** 규칙뿐이다. 지어내지 않고 gap 에 적는다.
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
import schema as SC  # noqa: E402  — 단위·범위 판정의 정본

SRC_ID = "samsung-dms25-bacnet"
DOC = "Samsung_DMS25_BACnet_LonWorks_InstallGuide_EN_DB68-06095A-05.pdf"
MODEL_ID = "samsung-mim-b17bn-bacnet-gateway"
FAMILY = "Samsung/DMS-BACnet"
PAGES = list(range(62, 74))          # E-62~73. 인쇄 쪽번호는 아래에서 읽어 확인한다

TYPES = ("AI", "AO", "AV", "BI", "BO", "BV", "MI", "MO", "MV",
         "MSI", "MSO", "MSV", "NC")
KIND = {"AV": "analog", "AI": "analog", "AO": "analog",
        "BV": "binary", "BI": "binary", "BO": "binary",
        "MSV": "code", "MSI": "code", "MSO": "code",
        "MV": "code", "MI": "code", "MO": "code"}
ANALOG = ("AI", "AO", "AV")

INST = re.compile(r"^\*{0,2}\s*(\d+)$")
NAME = re.compile(r"^[A-Za-z][\w.]*_xx")
CAPTION = re.compile(r"^(.*?)\s+has following point list", re.I)
HEADING = re.compile(r"^([A-Za-z][\w /.()]*?)\s*\[(Basic|Advanced|Basic, Advanced)\]$")

# 머리글 낱말. 표마다 머리글이 다르다 — E-73 은 'Control and Monitoring | Status Value' 다.
HEADLBL = {"Instance", "Number", "Object", "Type", "Object Type", "Object Name",
           "Unit", "Status value", "Status Value", "Inactive", "Active",
           "Inactive Active", "Control and", "Monitoring", "Text-4 Text-5",
           "Text-1 Text-2 Text-3 Text-4 Text-5"}
HEADLBL |= {"Text-%d" % i for i in range(1, 6)}
# 값 칸이 **여럿**인 표의 머리글. E-73 처럼 'Status Value' 한 칸뿐인 표는
# 값을 x 로 쪼개면 안 된다 — 한 문장이 여러 조각으로 흩어져 들어온다.
MULTILBL = {"Inactive", "Active", "Inactive Active", "Text-1", "Unit",
            "Text-1 Text-2 Text-3 Text-4 Text-5"}

# 판 id 는 원문이 부르는 이름에서 만든다 — 없는 말을 지어내지 않는다.
SLUG = {
    "Indoor Unit [Basic]": ("indoor-basic", "실내기 [Basic]", ["Indoor Unit"]),
    "Indoor Unit [Advanced]": ("indoor-advanced", "실내기 [Advanced]", ["Indoor Unit"]),
    "AHU Kit [Basic]": ("ahu-basic", "AHU 킷 [Basic]", ["AHU kit"]),
    "AHU Kit [Advanced]": ("ahu-advanced", "AHU 킷 [Advanced]", ["AHU kit"]),
    "EHS [Basic]": ("ehs-basic", "EHS [Basic]", ["EHS"]),
    "EHS [Advanced]": ("ehs-advanced", "EHS [Advanced]", ["EHS"]),
    "ERV or ERV Plus unit": ("erv", "ERV / ERV Plus", ["ERV", "ERV Plus"]),
    "DVM CHILLER Unit": ("dvm-chiller", "DVM CHILLER", ["DVM CHILLER"]),
    "SIM/PIM [Basic, Advanced]": ("sim-pim", "SIM/PIM", ["SIM", "PIM"]),
    "SIM/PIM": ("sim-pim", "SIM/PIM", ["SIM", "PIM"]),
    "Centralized Controller (OnOff Controller)":
        ("centralized-controller", "중앙제어기 (OnOff Controller)",
         ["Centralized Controller (OnOff Controller)"]),
    "Interface Module (Outdoor Unit)":
        ("interface-module-odu", "실외기 인터페이스 모듈",
         ["Interface Module (Outdoor Unit)"]),
    "Interface Module (Outdoor Unit) [Basic]":
        ("interface-module-odu-basic", "실외기 인터페이스 모듈 [Basic]",
         ["Interface Module (Outdoor Unit)"]),
    "Interface Module (Outdoor Unit) [Advanced]":
        ("interface-module-odu-advanced", "실외기 인터페이스 모듈 [Advanced]",
         ["Interface Module (Outdoor Unit)"]),
    "DVM CHILLER Unit [Basic]": ("dvm-chiller-basic", "DVM CHILLER [Basic]",
                                 ["DVM CHILLER"]),
    "DVM CHILLER Unit [Advanced]": ("dvm-chiller-advanced", "DVM CHILLER [Advanced]",
                                    ["DVM CHILLER"]),
    "BACnet Gateway [Basic, Advanced]":
        ("gateway", "BACnet 게이트웨이", ["BACnet Gateway"]),
    "BACnet Gateway": ("gateway", "BACnet 게이트웨이", ["BACnet Gateway"]),
    "DDC [Basic, Advanced]": ("ddc", "DDC", ["DDC"]),
    "DDC": ("ddc", "DDC", ["DDC"]),
}


def ledger_entry():
    led = json.load(io.open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    for url, v in led.items():
        if v.get("source") == SRC_ID and v.get("file") == DOC:
            return url, v
    raise SystemExit("대장에 %s / %s 가 없다 — collect.py --run %s" % (SRC_ID, DOC, SRC_ID))


def printed_no(page, fallback):
    """머리글 'E-62' 의 숫자. 오프셋을 가정하지 않고 읽는다."""
    for line in page.get_text().splitlines()[:3]:
        m = re.match(r"^E-(\d+)$", line.strip())
        if m:
            return int(m.group(1))
    return fallback


def frags(page):
    """글자 조각을 좌표와 함께. **줄이 아니라 span** 이다 —
    줄로 묶으면 이름과 단위가 한 줄에 붙어 나온다('…_xxxxxx Minute', E-65 실측)."""
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


def row_bands(page):
    """표의 가로 격자선에서 행 y 밴드를 얻는다.

    ⚠ 글자는 좌표로 읽지만 **행 경계는 격자에서 가져온다.** 번호가 셀 안에서
       가운데 정렬이라 y 만으로는 못 가른다 — E-73 2번은 번호가 y=142.4 인데
       그 행의 값은 y=123.4 부터 시작한다(다섯 줄짜리 셀). 번호 기준으로 자르면
       그 값이 앞 행으로 딸려 가 1번 상태가 '… 0: Normal, 8: Emergency stop …' 이 된다.
       표 인식은 **셀 글자를 믿지 않되**(밑줄이 조각난다) 격자는 쓸 만하다.
    """
    out = []
    for tb in page.find_tables().tables:
        for r in tb.rows:
            y0, y1 = round(r.bbox[1], 1), round(r.bbox[3], 1)
            if 4 < y1 - y0 < 200:
                out.append((y0, y1))
    # 다른 밴드를 통째로 품는 것은 행이 아니라 묶음이다 — 뺀다
    out = [b for b in out
           if not any(a is not b and a[0] >= b[0] and a[1] <= b[1] for a in out)]
    return sorted(set(out))


def band_of(bands, y):
    for y0, y1 in bands:
        if y0 - 1 <= y < y1:
            return (y0, y1)
    return None


def cluster(vals, gap=9.0):
    """x 가 가까운 조각을 한 칸으로 묶는다(줄바꿈된 셀)."""
    out = []
    for f in sorted(vals, key=lambda f: (f["x"], f["y"])):
        if out and f["x"] - out[-1][-1]["x"] <= gap:
            out[-1].append(f)
        else:
            out.append([f])
    return out


def join_name(parts):
    """줄바꿈된 이름을 잇는다 — 밑줄에서 잘렸으면 **붙이고** 아니면 빈칸을 둔다.

    'BACnetApp_Error_' + 'Code_xx' → 'BACnetApp_Error_Code_xx'
    'DI_01_xx_xx' + '(BACnet Gateway Reserved)' → 빈칸을 둔다(원문의 빈칸이다)
    """
    s = parts[0]
    for p in parts[1:]:
        s += ("" if s.endswith("_") or p.startswith("_") else " ") + p
    s = re.sub(r"\s+", " ", s).strip()
    # ⚠ 'AC_BV_1_Reserved _xx_xxxxxx' — 밑줄 앞뒤의 빈칸은 조판이다.
    #    근거: 원문 E-61~73 에서 '_xx' 는 518회 전부 붙어 있고 빈칸 낀 꼴은 **0회**다.
    return re.sub(r"\s*_\s*", "_", s) if re.search(r"\s_|_\s", s) else s


def read_page(page, pno):
    """한 쪽 → [{group, rows:[…]}]. 표는 머리글('Instance')마다 새로 시작한다."""
    fs = frags(page)
    # ⚠ 절대 x 를 쓰지 않는다 — 홀·짝 쪽의 왼쪽 여백이 다르다(E-62 x=70.0 · E-63 x=35.9).
    #    'Instance' 바로 밑에 같은 x 로 'Number' 가 오는 것을 보고 머리글을 찾고,
    #    그 x 를 이 표의 번호 열 위치로 삼는다.
    bands = row_bands(page)
    heads = []
    for f in fs:
        if f["t"] != "Instance":
            continue
        if any(g["t"] == "Number" and abs(g["x"] - f["x"]) < 4
               and 2 < g["y"] - f["y"] < 14 for g in fs):
            heads.append(f)
    if not heads:
        return []
    out = []
    foot = page.rect.height - 34            # 쪽 밑 머리말('73 E-')을 뺀다
    for n, hf in enumerate(heads):
        # ⚠ 머리글 높이를 **고정값으로 건너뛰지 않는다.** +24 로 잡았더니 표마다
        #    머리글 줄 수가 달라 **1번 행이 통째로 잘렸다**(E-71·E-73 실측).
        #    머리글 낱말이 실제로 끝나는 자리를 재서 그 아래부터 읽는다.
        near = [f for f in fs if hf["y"] - 18 <= f["y"] <= hf["y"] + 32
                and f["t"] in HEADLBL]
        top = (max(f["y"] for f in near) if near else hf["y"]) + 5
        bot = heads[n + 1]["y"] - 30 if n + 1 < len(heads) else foot
        body = [f for f in fs if top <= f["y"] < bot]
        # ⚠ 값 칸 x 를 머리글에서 가져오면 안 된다 — 머리글은 가운데 정렬이라
        #    실제 값보다 오른쪽이다(E-73: 'Status Value' x=263.9 · 값 x=220.6).
        #    그걸 경계로 쓰면 값이 이름 칸으로 새어 이름이 'When the error occurred,
        #    send event to list SIM_Notify_xx_xx …' 가 된다(실측).
        #    머리글은 **표가 여러 값 칸을 갖는지**만 알려 준다.
        multi = any(f["t"] in MULTILBL for f in near)
        # 이 표 위의 소제목·캡션이 기기군을 정한다. 소제목('Indoor Unit [Advanced]')이
        # 캡션('Single indoor unit has …')보다 정확하다 — 판본까지 말해 준다.
        above = sorted([f for f in fs if f["y"] < hf["y"]], key=lambda f: -f["y"])
        label = cap = None
        for f in above:
            if cap is None:
                m = CAPTION.match(f["t"])
                if m:
                    cap = re.sub(r"^Single\s+", "", m.group(1)).strip()
                    continue
            if HEADING.match(f["t"]):
                # 캡션에서 40pt 안쪽에 있는 소제목만 이 표의 것이다
                if cap is None or hf["y"] - f["y"] < 60:
                    label = f["t"].strip()
                break
            if cap is not None and hf["y"] - f["y"] > 60:
                break
        out.append({"page": pno, "group": label or cap, "inst_x": hf["x"],
                    "multi": multi, "bands": bands, "frags": body})
    return out


def is_name(s):
    """이름 칸의 조각인가 — 줄바꿈된 뒷조각과 괄호 주석까지 이름 칸으로 본다."""
    return bool(NAME.match(s)) or s.startswith("(")


def parse_rows(body, inst_x, multi=True, bands=()):
    """조각 → 포인트 행. 열은 **내용으로 찾은 앵커의 x** 로 가른다."""
    insts = [f for f in body if INST.match(f["t"]) and abs(f["x"] - inst_x) < 16]
    if not insts:
        return []
    types = [f for f in body if f["t"] in TYPES]
    names = [f for f in body if NAME.match(f["t"])]
    if not types or not names:
        return []
    type_x = min(f["x"] for f in types)
    name_x = min(f["x"] for f in names)
    # 값 칸의 시작 = 타입 칸 오른쪽에서 **이름도 주석도 아닌** 첫 조각의 x.
    # 내용으로 먼저 가르고 남은 것에서 재므로 표마다 여백이 달라도 흔들리지 않는다.
    # ⚠ 이름 칸 **자리에 있는** 조각은 빼고 잰다. 줄바꿈된 이름의 뒷조각이 늘
    #    이름처럼 생기지는 않는다('BACnetApp_Error_' 에는 _xx 가 없다). 그걸 값으로
    #    보면 vx 가 이름 칸 왼쪽으로 밀려 **그 판이 통째로 0행이 된다**(실측: 판 셋).
    rest = [f["x"] for f in body
            if f["x"] > type_x + 4 and abs(f["x"] - name_x) > 6
            and not is_name(f["t"]) and f["t"] not in TYPES]
    vx = (min(rest) - 4) if rest else (name_x + 400)
    if vx <= name_x:
        vx = name_x + 400

    rows = []
    for n, iv in enumerate(insts):
        # 격자 밴드가 있으면 그것이 정답이다(번호는 셀 가운데 정렬이라 y 로는 못 가른다).
        bd = band_of(bands, iv["y"])
        if bd:
            lo, hi = bd
        else:
            # 격자를 못 얻은 표만 어림으로 — 줄바꿈된 셀의 첫 줄이 번호보다 위에 놓인다
            gap = (iv["y"] - insts[n - 1]["y"]) / 2 if n else 3
            lo = iv["y"] - min(9.0, max(3.0, gap))
            nxt = insts[n + 1] if n + 1 < len(insts) else None
            hi = (nxt["y"] - min(9.0, max(3.0, (nxt["y"] - iv["y"]) / 2))
                  if nxt else 10 ** 6)
        seg = [f for f in body if lo <= f["y"] < hi]
        desc = [f for f in seg if iv["x"] + 8 < f["x"] < type_x - 5]
        ty = [f for f in seg if abs(f["x"] - type_x) < 12 and f["t"] in TYPES]
        nm = [f for f in seg if name_x - 6 <= f["x"] < vx]
        val = [f for f in seg if f["x"] >= vx]
        if not ty or not nm:
            continue
        rows.append({
            "no": int(INST.match(iv["t"]).group(1)),
            "mark": iv["t"].replace(INST.match(iv["t"]).group(1), "").strip(),
            "type": ty[0]["t"],
            "name": join_name([f["t"] for f in sorted(nm, key=lambda f: f["y"])]),
            "desc": re.sub(r"\s+", " ", " ".join(
                f["t"] for f in sorted(desc, key=lambda f: (f["y"], f["x"])))).strip(),
            "vals": ([re.sub(r"\s+", " ", " ".join(
                f["t"] for f in sorted(c, key=lambda f: f["y"]))).strip()
                for c in cluster(val)] if multi else
                ([re.sub(r"\s+", " ", " ".join(
                    f["t"] for f in sorted(val, key=lambda f: (f["y"], f["x"])))).strip()]
                 if val else [])),
        })
    return rows


def crosscheck(doc, tables):
    """표 좌표가 아닌 **쪽 글자 흐름**에서 이름을 다시 읽어 맞춘다."""
    flat = {t["page"]: re.sub(r"\s+", "", doc[t["page"] - 1].get_text()) for t in tables}
    same, total, diff = 0, 0, []
    for t in tables:
        for r in t["rows"]:
            total += 1
            if re.sub(r"\s+", "", r["name"].split(" (")[0]) in flat[t["page"]]:
                same += 1
            elif len(diff) < 8:
                diff.append("%d쪽 %s" % (t["printed"], r["name"]))
    return {"method": "쪽 글자 흐름에서 오브젝트 이름을 다시 읽어 맞췄다"
                      "(좌표 판독 경로가 아니다)",
            "total": total, "both": same,
            "rate": round(same / total, 4) if total else 0.0, "diff": diff}


# 쉼표로 갈린 코드 열거만 읽는다 — '1: None, 2: Vertical, 3: Horizon' · '0: Normal, 8: …'
# ⚠ '/' 로 갈린 것은 읽지 않는다. 라벨 안에 '/' 가 들어 있어('8 : 33 kg/cm² / 14 : Auto
#   control') 기계로 자르면 '33 kg' 이 된다. 그런 칸은 산문으로 남기고 gap 에 적는다.
INLINE = re.compile(r"(\d+)\s*:\s*([^,\n]+)")
# 코드표가 이 문서 밖에 있다고 가리키는 칸
REFERS = re.compile(r"(?i)^(refer to .*code|bacnet error code)$")
# 'Inactive : All devices Off' — 이진값의 뜻을 문장으로 적은 것
INACT = re.compile(r"(?i)^inactive\s*:\s*(.+)$")
BLANK = ("-", "\u2014", "")


def unitish(s):
    """단위처럼 생겼나 — 짧고 빈칸이 없다('°C' '°C(°F)' 'kWh' 'Minute' 'μg/m3').

    ⚠ 열 이름으로 정하지 않는다. 같은 칸에 단위·코드표 참조·열거·산문이 섞여 온다
       (실측: 'Refer to list of error code' · 'Use when displayed temperature type').
    """
    return bool(s) and " " not in s and len(s) <= 10


def states_of(vals, ty):
    """값 칸 → (단위, 상태, 코드표참조, 산문, gap). 뜻은 **오브젝트 타입**이 정한다."""
    vals = [v for v in vals if v and v not in BLANK]
    if not vals:
        return "", [], "", "", []
    joined = re.sub(r"\s+", " ", " ".join(vals)).strip()

    if ty == "NC":
        # 알림 클래스다 — 상태값이 아니라 동작 설명이다. 상태로 만들면 없는 코드가 생긴다.
        return "", [], "", joined, []

    if ty in ("BI", "BO", "BV"):
        m = INACT.match(joined)
        if m and len(vals) == 1:
            # 원문이 이진값의 뜻을 문장으로 적었다 — Inactive 쪽만 알려 준다
            return "", [{"code": "0", "label": m.group(1).strip()}], "", "", []
        # 머리글이 'Inactive | Active' 라고 못 박았다 — BACnet 이진값 0/1 과 맞는다
        return "", [{"code": str(i), "label": v} for i, v in enumerate(vals[:2])], \
            "", " ".join(vals[2:]), []

    if ty in ANALOG:
        if REFERS.match(joined):
            return "", [], joined, "", []
        if "," in joined and len(INLINE.findall(joined)) >= 2:
            return "", [{"code": c, "label": l.strip()}
                        for c, l in INLINE.findall(joined)], "", "", []
        if re.search(r"\d\s*:", joined):
            return "", [], "", joined, [
                "common.states — 값 칸이 코드 열거인데 '/' 로 갈려 있고 라벨 안에도 "
                "'/' 가 들어 있다('8 : 33 kg/cm² / 14 : Auto control'). 기계로 자르면 "
                "잘못 자른다 — 원문 그대로 두었다."]
        if unitish(vals[0]):
            return vals[0], [], "", " ".join(vals[1:]), []
        return "", [], "", joined, []

    # 멀티스테이트 — Text-N 이 그대로 상태값이다(1부터).
    # 근거: 원문 실내기 16번 AC_FanFlow 가 '1: None, 2: Vertical, 3: Horizon, …' 이다.
    if "," in joined and len(INLINE.findall(joined)) >= 2:
        return "", [{"code": c, "label": l.strip()}
                    for c, l in INLINE.findall(joined)], "", "", []
    return "", [{"code": str(i + 1), "label": v} for i, v in enumerate(vals)], "", "", []


def build(meta, tables, cc):
    ifaces, total = [], 0
    seen = collections.OrderedDict()
    for t in tables:
        seen.setdefault(t["slug"], []).append(t)
    for slug, ts in seen.items():
        label, applies = ts[0]["label"], ts[0]["applies"]
        pts, pages = [], []
        for t in ts:
            pages.append(t["printed"])
            for r in t["rows"]:
                unit, states, ref, prose, vgaps = states_of(r["vals"], r["type"])
                common, gaps = {"name": r["name"].split(" (")[0]}, list(vgaps)
                if r["desc"]:
                    common["note"] = r["desc"]
                if " (" in r["name"]:
                    # 괄호 주석은 이름이 아니다 — 붙여 두면 BMS 가 그 이름으로 찾는다.
                    # 괄호째 비고로 옮긴다.
                    common["note"] = ((common.get("note", "") + " (")
                                      + r["name"].split(" (", 1)[1]).strip()
                kind = KIND.get(r["type"])
                if kind:
                    common["pointKind"] = kind
                # states_of 가 unitish() 로 이미 걸렀다 — 여기서 다시 거르면 안 된다.
                # ⚠ looks_like_range 는 '숫자가 섞였나' 만 본다. 그걸 다시 걸었더니
                #    'μg/m3' 가 3 때문에 범위로 몰려 단위가 셋 통째로 빠졌다(실측).
                rng = SC.parse_range(unit)
                if rng:
                    common["range"] = rng
                elif unit:
                    common["unitSIRaw"] = unit
                    common["unitSI"] = unit.replace("℃", "°C")
                if states:
                    common["states"] = states
                if ref:
                    common["statesRef"] = ref
                if prose:
                    common["note"] = (common.get("note", "") + " "
                                      + prose).strip()
                gaps.append("이름의 자리표시(xx·xxxxxx) — 이 문서는 무엇이 들어가는지 "
                            "밝히지 않는다. E-61 이 주는 것은 Device ID 규칙뿐이다.")
                src = {"Instance Number": str(r["no"]), "Object Type": r["type"],
                       "Object Name": r["name"], "Object": r["desc"]}
                if r["mark"]:
                    src["표식"] = r["mark"]
                if unit:
                    src["Unit / Status value"] = unit
                if prose:
                    src["Status value / 비고"] = prose
                pts.append({
                    "common": common,
                    "blocks": {"bacnet": {"objectType": r["type"], "instance": r["no"]}},
                    "provenance": {"sourceFile": meta["file"], "sourcePage": t["printed"],
                                   "family": FAMILY, "sourceColumns": src,
                                   "status": "extracted", "interfaceId": slug,
                                   "gaps": gaps},
                })
        total += len(pts)
        ifaces.append({
            "id": slug, "label": label, "family": FAMILY, "protocols": ["bacnet"],
            "sourceFile": meta["file"], "sourcePages": sorted(set(pages)),
            "pointCount": len(pts), "appliesTo": applies, "status": "extracted",
            "note": ("게이트웨이가 이 기기군에 대해 내보내는 오브젝트 목록. "
                     "인스턴스 번호는 표가 직접 준다. 디바이스 ID 는 자동 생성이고 "
                     "규칙이 원문 E-61 에 있다 — DNET(게이트웨이 1~40) + CPP(기기 종류별 "
                     "대역: 중앙제어기 000~015 · SIM/PIM 100~115 · DMS DI/DO 300~315 · "
                     "실외기 인터페이스/실내기 400~655 · 게이트웨이 900) + INDOOR(0~63, "
                     "실내기가 아니면 64) 를 자릿수로 이어 붙인다. 원문 예: DNET 9 · "
                     "실내기 주소 01.01.32 → CPP 400+1×16+1=417 → Device ID 941732."),
            "gaps": ["이름의 자리표시(xx·xxxxxx)가 무엇으로 채워지는지 원문이 밝히지 않는다.",
                     "'*'·'**' 표식은 선택 지원을 뜻한다(원문 E-63: '(*) Mark is "
                     "optionally supported. For a fresh duct, (**) mark is supported.') "
                     "— 어느 형번에서 지원되는지는 이 문서에 없다."],
            "points": pts,
        })
    return {
        "id": MODEL_ID, "equipId": "e5", "vendor": "Samsung",
        "model": "MIM-B17BN", "name": "BACnet Gateway (DMS2.5)",
        "cat": "HVAC.AIR.VRF", "tag": "vrf", "tags": ["vrf"], "status": "active",
        "coversDevices": ("원문이 판마다 덮는 장치를 직접 밝힌다 — 실내기(Basic/Advanced) · "
                          "AHU 킷 · EHS · ERV/ERV Plus · DVM CHILLER · SIM/PIM · "
                          "중앙제어기(OnOff Controller) · 실외기 인터페이스 모듈 · "
                          "게이트웨이 자신 · DDC. 전부 삼성 장치다."),
        "classifiedBy": ("게이트웨이지만 덮는 기기군의 주력이 VRF 실내기라 LG AC Smart 와 "
                         "같은 자리에 둔다. ⚠ classify.py 의 규칙표는 VRF 를 e8 에 "
                         "맞춰 두었다 — LG 와 이 모델이 함께 e5 에 있는 것이 맞는지는 "
                         "아직 정하지 않았다(두 모델을 같이 옮겨야 한다)."),
        "summary": "BACnet 게이트웨이 설치설명서 1건 · 판 %d개에서 취입 — 오브젝트 %d점"
                   % (len(ifaces), total),
        "has": {"spec": False, "points": True}, "ede": False,
        "spec": [], "io": [], "elec": None, "points": [],
        "gap": ("정격·형번이 없다 — 게이트웨이 설치설명서라 제품 카탈로그가 따로 필요하다. "
                "오브젝트 이름의 자리표시(xx·xxxxxx)가 무엇으로 채워지는지도 원문이 "
                "밝히지 않는다. 같은 문서의 LonWorks SNVT 표(E-88~100)는 아직 취입하지 "
                "않았다 — 프로토콜이 다른 별도의 판이다."),
        "extractor": "ingest_samsung", "sourceDoc": meta["file"],
        "interfaces": ifaces, "crosscheck": cc,
    }


def collect_tables(doc):
    tables, cur = [], None
    for p in PAGES:
        page = doc[p - 1]
        pr = printed_no(page, p)
        for tb in read_page(page, p):
            if tb["group"]:
                cur = tb["group"]
            rows = parse_rows(tb["frags"], tb["inst_x"], tb["multi"], tb["bands"])
            # ⚠ 번호가 있는데 행이 0이면 열 가르기가 어긋난 것이다 — 조용히 넘기면
            #    그 판이 통째로 빠지고 총계만 보면 알아채기 어렵다(실제로 셋 잃었다).
            insts = [f for f in tb["frags"] if INST.match(f["t"])
                     and abs(f["x"] - tb["inst_x"]) < 16]
            if insts and not rows:
                raise SystemExit("원문 %d쪽 %r: 번호 %d개인데 행이 0이다 — 열 가르기를 봐라"
                                 % (pr, tb["group"], len(insts)))
            if not rows:
                continue
            g = cur or "?"
            # '[Basic, Advanced]' 는 **두 판본이 같은 목록**이라는 뜻이라 판을 나누지
            # 않는다. '[Basic]' · '[Advanced]' 가 따로 붙은 것만 판이 갈린다.
            key = g if g in SLUG else re.sub(r"\s*\[Basic, Advanced\]$", "", g)
            if key not in SLUG:
                raise SystemExit("SLUG 에 없는 기기군: %r (원문 %d쪽) — 표를 넓혀라" % (g, pr))
            slug, label, applies = SLUG[key]
            tables.append({"page": p, "printed": pr, "group": g, "slug": slug,
                           "label": label, "applies": applies, "rows": rows})
    return tables


def main(argv):
    import fitz
    run = "--run" in argv
    url, meta = ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, SRC_ID))
    doc = fitz.open(path)

    tables = collect_tables(doc)
    cc = crosscheck(doc, tables)
    model = build(meta, tables, cc)

    print("모델 %s" % model["id"])
    for i in model["interfaces"]:
        print("   %-24s %3d점  원문 %s쪽" % (i["id"], i["pointCount"], i["sourcePages"]))
    n = sum(i["pointCount"] for i in model["interfaces"])
    print("   합계 %d점 · 교차 대조 %d/%d = %.1f%%" % (n, cc["both"], cc["total"],
                                                 100 * cc["rate"]))
    if cc["diff"]:
        print("   ⚠ 안 맞은 것:", " · ".join(cc["diff"]))

    out = os.path.join(DATA, "models", MODEL_ID + ".json")
    if not run:
        print("\n(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n→ %s" % os.path.relpath(out, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
