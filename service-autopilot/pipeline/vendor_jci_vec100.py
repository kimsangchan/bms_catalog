# -*- coding: utf-8 -*-
"""Verasys VEC100 Generic RTU Controller — SBH 메뉴 항목 표 어댑터.

이 계통은 주소가 없다
  열이 다섯인데 주소 열이 하나도 없다:

    Object or parameter | Description | Adjustable | Defaults | Enum set or range
    Unit Status         | Shows …     | Read Only  |          | 0 = Idle 1 = SD Alarm …

  오브젝트별 BACnet 타입·인스턴스도 Modbus 레지스터도 **원문 어디에도 없다.** 문서가
  밝히는 주소는 장치 수준뿐이다 — 컨트롤러 주소 4~127, "Sets the BACnet ID of the
  device"(p28·p30), p45 "Verasys BACnet MS/TP Communications". 그래서 blocks 를 만들
  수 없고, 이 목록은 **매핑에 바로 못 쓴다.** 이름·읽기쓰기·기본값·범위를 아는 목록이다.
  주소 있는 목록과 섞어 세지 않도록 validate 의 points-unaddressed 가 수를 드러낸다.

메뉴 경로가 행 정체성의 절반이다
  표가 통짜가 아니라 메뉴별 소표 43~47개로 쪼개져 실리고, 캡션이 경로를 준다
  ('Table 13: Status menu' · 'Table 58: Details : Service : Factory').
  **이름만으로 합치면 안 된다** — 'Commissioning : Econ Temp PID Data' 와
  'Heating PID Data' 와 'Cooling PID Data' 세 메뉴의 PID 파라미터는 설명 글자까지
  같지만 서로 다른 오브젝트다. 같은 이름이 한 문서에서 여섯 번 나오기도 한다
  (Supply Air Temperature). 그래서 열쇠는 (메뉴 경로, 이름)이다.

  ⚠ 그래서 여기서 세는 수는 **메뉴 항목 수이지 컨트롤러 오브젝트 수가 아니다.**
    문서가 오브젝트 ID 를 안 주므로 참 오브젝트 수는 산출할 수 없다 — 추측으로
    병합하지 않는다.

'Enum set or range' 한 열에 세 가지가 섞여 있다
  상태 코드표('0 = Idle 1 = SD Alarm …') · 범위('40°F to 80°F (4°C to 27°C)') ·
  단위만('°F (°C)'·'ppm'). 통째로 states 로 밀면 범위와 단위가 상태로 둔갑한다.
  성격을 갈라 담고, 못 가른 것은 원표기만 남긴다.
"""
import re

FAMILY = "Verasys/Menu"
SOURCE = "jci-vec100-points"

HEAD = re.compile(r"Object\s*or\s*parameter.*Description.*(?:Adjustable|Enum)",
                  re.I | re.S)
# 캡션 — 'Table 27: Details : Setup menu' 에서 메뉴 경로를 얻는다
CAPTION = re.compile(r"Table\s+\d+\s*[:.]\s*(.+?)\s*$", re.I)
RW = {"adjustable": "R/W", "read only": "R", "readonly": "R"}
# '0 = Idle 1 = SD Alarm' · '3 = Nickel 4 = Platinum' — 0 으로 시작하지 않는 것도 있다
ENUM = re.compile(r"(\d+)\s*=\s*([^0-9=]+?)(?=\s+\d+\s*=|$)")
# '40°F to 80°F (4°C to 27°C)' · '4 to 127'
RANGE = re.compile(r"^\s*(-?[\d.]+)\s*([^\d]*?)\s*to\s*(-?[\d.]+)\s*([^()]*?)\s*(?:\((.+)\))?\s*$")
EMPTY = {"", "-", "--", "N/A", "n/a"}


def is_point_table(head):
    return bool(HEAD.search(head or ""))


def menu_of(caption):
    """'Table 27: Details : Setup menu' → 'Details : Setup'"""
    m = CAPTION.search((caption or "").strip())
    if not m:
        return ""
    s = re.sub(r"\s*menu\s*$", "", m.group(1), flags=re.I).strip()
    return re.sub(r"\s+", " ", s)


def _enum(raw):
    """상태 코드표일 때만 states 를 만든다. 범위·단위는 여기로 안 온다."""
    raw = (raw or "").strip()
    if raw in EMPTY or "=" not in raw:
        return None
    out = [{"code": c, "label": lab.strip(" .,")} for c, lab in ENUM.findall(raw)]
    return out if len(out) >= 2 else None


def _range_or_unit(raw):
    """→ (범위 dict|None, 단위 문자열|None). 못 가르면 (None, None).

    범위와 단위가 같은 열에 오므로 성격을 갈라야 한다. 갈라지지 않으면 손대지 않고
    원표기만 남긴다 — 지어내면 시뮬레이터가 그대로 믿는다.
    """
    raw = (raw or "").strip()
    if raw in EMPTY or "=" in raw:
        return None, None
    m = RANGE.match(raw)
    if m:
        lo, u1, hi, u2, _si = m.groups()
        unit = (u1 or u2 or "").strip() or None
        try:
            return {"min": float(lo), "max": float(hi)}, unit
        except ValueError:
            return None, unit
    # 'ppm' · '°F (°C)' 처럼 단위만 온 칸
    if len(raw) <= 24 and not re.search(r"\d", raw):
        return None, raw
    return None, None


def parse_rows(rows_in, fname):
    """(쪽, 메뉴경로, 셀목록) 목록 → 포인트 레코드."""
    out, skipped = [], {}
    seen = set()
    for page, menu, cells in rows_in:
        cells = [(c or "").strip() for c in cells]
        if len(cells) < 3:
            skipped["짧은 행"] = skipped.get("짧은 행", 0) + 1
            continue
        name, desc, adj = cells[0], cells[1], cells[2]
        default = cells[3] if len(cells) > 3 else ""
        enum_raw = cells[4] if len(cells) > 4 else ""
        # 머리글 행이 그대로 오면 포인트가 된다 — 'Adjustable' 이 머리글 칸에도
        # 있어 rw 판정을 통과해 버린다. 지금은 table_header 가 걷어내서 안 오지만,
        # 부르는 쪽에 기대지 말고 여기서도 막는다. ⚠ 행 전체가 머리글일 때만 무른다 —
        # 'Description' 은 **진짜 포인트 이름이기도 하다**(Controller : Network 메뉴의
        # 장치 설명 필드). 이름 하나로 걸러내면 진짜를 버린다.
        if is_point_table(" | ".join(cells)):
            skipped["머리글·빈 행"] = skipped.get("머리글·빈 행", 0) + 1
            continue
        rw = RW.get(adj.strip().lower())
        if not name or not rw:
            # 쪽마다 되풀이되는 머리글이 여기로 온다
            skipped["머리글·빈 행"] = skipped.get("머리글·빈 행", 0) + 1
            continue

        common = {"name": name, "readWrite": rw}
        if desc not in EMPTY:
            common["note"] = desc
        if menu:
            common["group"] = menu           # 메뉴 경로 — 행 정체성의 절반
        gaps = []
        st = _enum(enum_raw)
        if st:
            common["states"] = st
        else:
            rng, unit = _range_or_unit(enum_raw)
            if rng:
                common["rangeSI"] = rng
            if unit:
                common["unitSI"] = unit
                common["unitSIRaw"] = enum_raw
            if enum_raw not in EMPTY and not rng and not unit:
                gaps.append("common.states")
        # 이 계통은 주소가 없다 — 없는 것을 없다고 적는다
        gaps.append("blocks")

        src = {"Adjustable": adj, "Defaults": default, "Enum set or range": enum_raw,
               "메뉴": menu}
        rec = {"common": common, "blocks": {},
               "provenance": {"sourceFile": fname, "sourcePage": page,
                              "family": FAMILY, "status": "extracted",
                              "sourceColumns": {k: v for k, v in src.items()
                                                if (v or "").strip() not in EMPTY},
                              "gaps": sorted(set(gaps))}}
        key = (menu, name)
        if key in seen:
            skipped["쪽 넘김 중복"] = skipped.get("쪽 넘김 중복", 0) + 1
            continue
        seen.add(key)
        out.append(rec)
    return out, skipped


def crosscheck(path, points):
    """표 인식이 아니라 쪽 글자 흐름으로 대조한다 (규칙 ④).

    주소가 없어 기존 대조기들의 열쇠(레지스터·포인트 번호)를 못 쓴다. 대신 이 표에만
    있는 성질을 쓴다 — 모든 행이 'Adjustable' 또는 'Read Only' 를 갖는다.

    ⚠ 열쇠로 **'Read Only' 만** 쓴다. 'Adjustable' 은 **머리글에도 있어**
      (Object or parameter | Description | Adjustable | Defaults | …) 소표 43~47개마다
      한 번씩 더 세어진다 — 그것으로 맞추면 82% 가 나오고, 그 82% 는 결함이 아니라
      머리글 몫이다. 결함과 조판을 구분 못 하는 열쇠는 대조에 못 쓴다.
      'Read Only' 는 머리글에 없어 데이터 행에서만 나온다.
    """
    import fitz

    want = {p["provenance"]["sourcePage"] for p in points
            if isinstance(p.get("provenance", {}).get("sourcePage"), int)}
    doc = fitz.open(path)
    n_txt = 0
    for i in range(doc.page_count):
        if want and (i + 1) not in want:
            continue
        n_txt += len(re.findall(r"\bRead\s+Only\b", doc[i].get_text()))
    doc.close()
    got = sum(1 for p in points if (p.get("common") or {}).get("readWrite") == "R")
    rate = round(min(got, n_txt) / max(got, n_txt), 4) if max(got, n_txt) else 0.0
    return {"rate": rate, "both": min(got, n_txt), "total": len(points),
            "method": "표 인식 대신 쪽 글자 흐름에서 'Read Only' 낱말 수를 세어 읽기전용 "
                      "행수와 맞췄다 — 'Adjustable' 은 머리글에도 있어 열쇠로 못 쓴다",
            "textCount": n_txt}
