# -*- coding: utf-8 -*-
"""판정 — 문서가 어떤 장비이고 그 안에 장치가 몇 대인지 문서에서 읽어낸다.

손으로 적으면 문서 수만큼 손이 든다. 수백 벤더로 늘리려면 판정도 자동이어야 한다.
다만 **문서에 없는 것은 지어내지 않는다** — 냉각 방식(공랭/수랭)처럼 표지에 없는 값은
비워 두고, 있는 근거만 쓴다.

  · 장비 계열 = 포인트 이름에 나타나는 부속의 증거 (증발기·응축기 → 냉동기)
  · 구간 이름 = PDF 목차의 프로파일 표제 (SCC/DAC, Simplex/Duplex)
  · 제품·컨트롤러 = 표지 첫 줄들
"""
import re

# 장비 계열 판정 규칙 — (계열, 분류, 태그, [증거 정규식], 최소 증거 수)
# 위에서부터 검사하고 증거가 가장 많은 것을 고른다.
RULES = [
    ("e9", "HVAC.PLANT.CHILLER", "chiller", [
        r"\bevaporator\b", r"\bcondenser\b", r"chilled water", r"\bchiller\b",
        r"\brefrigerant\b", r"compressor \w*(?:1|2|a|b)\b"], 3),
    ("e11", "HVAC.PLANT.BOILER", "boiler", [
        r"\bboiler\b", r"\bburner\b", r"\bflue\b", r"hot water (?:supply|return) temp"], 2),
    ("e10", "HVAC.PLANT.COOLINGTOWER", "coolingTower", [
        r"cooling tower", r"\bbasin\b", r"tower fan"], 2),
    ("e5", "HVAC.AIR.AHU", "ahu", [
        r"\beconomizer\b", r"outdoor air damper", r"supply (?:air|fan)", r"discharge air",
        r"return air", r"mixed air", r"exhaust (?:air|fan)", r"\bfilter\b"], 3),
    ("e8", "HVAC.AIR.TERMINAL.VRF", "vrf", [
        r"\bindoor unit\b", r"\boutdoor unit\b", r"\bvrf\b", r"expansion valve"], 2),
    ("e15", "HVAC.AUX.VFD", "vfd", [
        r"\bdrive\b", r"output frequency", r"motor current", r"\bvfd\b"], 3),
    ("e14", "HVAC.PLANT.PUMP", "pump", [
        r"\bpump\b", r"\bhead\b", r"\bimpeller\b"], 2),
]


def _plain(pat):
    """정규식을 사람이 읽을 말로 — 근거 설명에 쓴다."""
    s = pat.replace(r"\b", "").replace(r"\w*", " ")
    s = re.sub(r"\(\?:([^)]*)\)", lambda m: m.group(1).split("|")[0], s)
    return re.sub(r"[\\^$?*+()\[\]{}|]", "", s).strip()


# 표지에 제품군이 그대로 적혀 있는 경우 — 포인트 이름만으로는 안 잡히는 장비를 구한다.
# 예: 인버터 문서의 포인트는 '아날로그입력 53' 처럼 범용 이름이라 증거가 없다.
TITLE_RULES = [
    ("e15", "HVAC.AUX.VFD", "vfd",
     r"\bVLT\b|frequency converter|frequenzumrichter|variable speed drive|\bVFD\b|soft starter"),
    ("e14", "HVAC.PLANT.PUMP", "pump", r"\bpump\b|pumpe\b|grundfos"),
    ("e8", "HVAC.AIR.TERMINAL.VRF", "vrf", r"\bVRV\b|\bVRF\b|intelligent touch manager"),
    ("e9", "HVAC.PLANT.CHILLER", "chiller", r"\bchiller\b"),
]


def classify_equip(points, doctext=""):
    """장비 계열을 판정한다 → (계열, 분류, 태그, 근거설명).

    1순위는 포인트 이름의 부속 증거다 — 실제로 그 장비에 달린 것을 보기 때문에 가장 믿을 만하다.
    포인트 이름이 범용이라 증거가 안 나오면 표지 제품명으로 내려간다.
    """
    blob = " ".join((p.get("name") or "") + " " + (p.get("note") or "")
                    for p in points).lower()
    best = None
    for eq, cat, tag, pats, need in RULES:
        hits = [pat for pat in pats if re.search(pat, blob)]
        if len(hits) >= need and (best is None or len(hits) > best[0]):
            best = (len(hits), eq, cat, tag,
                    "포인트 이름 증거 %d종: %s" % (len(hits),
                                            ", ".join(_plain(h) for h in hits[:4])))
    if best:
        return best[1], best[2], best[3], best[4]
    for eq, cat, tag, pat in TITLE_RULES:
        m = re.search(pat, doctext or "", re.I)
        if m:
            return eq, cat, tag, "표지 제품명 근거: %r" % m.group(0)
    return None, None, None, "판정 근거 부족 — 사람이 정해야 한다"


# 목차 표제에서 프로파일·장치 이름을 딴다.
TOCSPLIT = re.compile(
    r"^(.*?)\s*(?:network variable|nv|configuration parameters?|config parameters?)",
    re.I)
TOCTAIL = re.compile(
    r"(?:network variable|configuration parameters?|config parameters?)\s*"
    r"(?:inputs?|outputs?)?\s*(.*)$", re.I)


def segment_names(pdf):
    """PDF 목차에서 구간 이름을 순서대로 뽑는다.

    Trane LonTalk 문서는 목차가 'SCC Network Variable Inputs' / 'DAC …' 처럼
    프로파일 이름을 앞에 달거나, 'Config Parameters Simplex' 처럼 뒤에 단다.
    둘 다 훑어서 처음 나온 순서대로 돌려준다. 목차가 없으면 빈 목록.
    """
    import fitz
    toc = fitz.open(pdf).get_toc()
    seen, out = set(), []
    for _, title, _ in toc:
        t = title.strip()
        name = None
        m = TOCSPLIT.match(t)
        if m and m.group(1).strip():
            name = m.group(1).strip()
        if not name:
            m2 = TOCTAIL.search(t)
            if m2 and m2.group(1).strip():
                name = m2.group(1).strip()
        if not name or len(name) > 24:
            continue
        k = name.lower()
        if k not in seen:
            seen.add(k)
            out.append(name)
    return out


TITLE_NOISE = re.compile(r"^(date|firmware|reference|bas-pts)", re.I)
# 표지에 있지만 제품명이 아닌 줄 — 표어·문서종류·주소·법적 문구
NOT_PRODUCT = re.compile(
    r"^(engineering tomorrow|design guide|installation guide|operating guide|"
    r"programming guide|programmierhandbuch|betriebsanleitung|fact sheet|"
    r"user manual|quick guide|application guide|www\.|https?:|\S+\.(com|net|org)|"
    r"contents?|table of contents|copyright|all rights reserved|"
    r"bacnet|lontalk|modbus|convenient .*)$", re.I)
# 제품명다움 — 상표기호·모델코드(영문+숫자 조합)가 있으면 제품명일 가능성이 높다
PRODUCTISH = re.compile(r"[™®]|\b[A-Z]{2,}[\s-]?\d{2,}\b|\b(model|series|type)\b", re.I)


def title_info(pdf):
    """표지에서 제품·컨트롤러·펌웨어를 읽는다.

    줄 순서가 벤더마다 다르다 — Trane 은 '컨트롤러 / 프로토콜 / 제품' 이고
    Danfoss 는 표어가 첫 줄에 온다. 그래서 위치가 아니라 **제품명다움**으로 고른다.
    """
    import fitz
    d = fitz.open(pdf)
    raw = [re.sub(r"\s+", " ", x).strip() for x in d[0].get_text().split("\n")]
    lines = [x for x in raw if 2 < len(x) < 70 and not TITLE_NOISE.match(x)]
    # 상표기호를 떼고 걸러야 한다 — 'BACnet®' 이 기호 때문에 제품명으로 뽑혔었다
    def bare(x):
        return re.sub(r"[™®©]", "", x).strip()
    usable = [x for x in lines if not NOT_PRODUCT.match(bare(x))]

    # Trane 계열은 첫 줄이 '<컨트롤러> Integration Points List' 로 고정이다
    ctl = ""
    if lines and re.search(r"Integration Poin[st]*s? List", lines[0], re.I):
        ctl = re.sub(r"Integration Poin[st]*s? List", "", lines[0], flags=re.I).strip()
        usable = [x for x in usable if x != lines[0]]

    picked = [x for x in usable if PRODUCTISH.search(x)] or usable
    prod = picked[0] if picked else (lines[0] if lines else "")
    if not ctl and len(picked) > 1:
        # 제품명 후보가 여럿이면 두 번째를 컨트롤러·모듈 이름으로 본다
        ctl = picked[1] if len(picked[1]) < len(prod) else ""

    proto = next((x for x in lines if re.match(r"^(BACnet|LonTalk|Modbus)", x, re.I)), "")
    fw = next((x.split(":", 1)[1].strip() for x in
               re.sub(r"\s+", " ", d[0].get_text()).split("Firmware Release:")[1:2]), "")
    return {"controller": ctl, "protocol": proto.strip("® "), "product": prod,
            "firmware": fw.split("Reference")[0].strip()[:40]}
