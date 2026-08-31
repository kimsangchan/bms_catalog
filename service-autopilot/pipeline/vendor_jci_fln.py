# -*- coding: utf-8 -*-
"""Siemens APOGEE P1/FLN 포인트 데이터베이스 어댑터 (JCI AYK550 인버터).

표가 셋 섞여 있다 — 하나만 골라야 한다
  이 매뉴얼 한 권에 표가 세 종류 있고, 셋 다 우리 표식에 걸린다:

    ① 9열  Point # | Type | Subpoint Name | Factory Default | Engr. Units |
            Slope | Intercept | On Text | Off Text          ← **이것이 포인트 목록**
    ② 4열  Point # | Type | Subpoint Name | Data            ← 리포트 7종. 부분집합이다
    ③ 4열  Modbus Register | ... | Access | Remarks         ← 같은 문서의 Modbus 표

  ②를 포인트로 세면 안 된다. 원문이 못 박는다 — "By providing views of selected
  points, these reports are often easier to work with than views of the full point
  database." 실제로 리포트 7종의 고유 번호 85개가 **전부** 9열 목록 안에 있다.
  ③은 계통 자체가 다르다(FLN 이 아니라 Modbus).
  그래서 여기서는 **9열 머리글만** 받는다.

원문이 안 밝히는 것이 많다 — 보존하고 해석하지 않는다
  · Type(LAO/LAI/LDO/LDI) 풀이가 문서에 없다. 코드 그대로 둔다.
  · On/Off Text 는 있는데 **어느 코드가 ON 인지** 안 준다. 0/1 대응은 관례일 뿐이라
    common.states 로 올리지 않고 글자만 보존한 뒤 gaps 에 적는다.
  · 'Slope' 는 unbundle 시 새 값 계산법만 주고, '공학값 = 원시값×slope+intercept'
    라는 변환 방향은 안 준다. 값만 담고 뜻은 사전 note 가 경고한다.
  · 중괄호 {03} 은 각주가 정해 준다 — "Point numbers that appear in brackets { }
    may be unbundled at the field panel."

  값이 둘인 칸은 영국단위(SI) 병기다(각주 b: 값이 하나면 두 단위계에서 같다).
  괄호가 떨어져 나온 추출본('0.134 0.1')도 있어 두 형태를 다 읽는다.
"""
import os
import re

FAMILY = "APOGEE/FLN"
SOURCE = "jci-airhandling-fln"

# 9열 목록만 받는다. 리포트(4열)·Modbus 표는 이 표식이 없다.
HEAD = re.compile(r"Subpoint\s*Name.*(?:Engr\.?\s*Units|Slope).*Intercept", re.I | re.S)
# 포인트 번호 — '01' 또는 '{03}'
NUM = re.compile(r"^\{?\s*(\d{1,3})\s*\}?$")
TYPES = ("LAI", "LAO", "LDI", "LDO")
# '77 (25)' · '0.18 (0.1)' · 괄호가 떨어진 '0.134 0.1'
DUAL = re.compile(r"^\s*(-?[\d.]+)\s*(?:\(\s*(-?[\d.]+)\s*\)|\s+(-?[\d.]+))\s*$")
EMPTY = {"", "-", "--", "N/A", "n/a"}


def _num(s):
    try:
        return float(s) if "." in s else int(s)
    except (TypeError, ValueError):
        return None


def _dual(raw):
    """영국단위(SI) 병기 → (SI 값, 원표기). 값이 하나면 두 단위계에서 같다(각주 b)."""
    raw = (raw or "").strip()
    if raw in EMPTY:
        return None, ""
    m = DUAL.match(raw)
    if m:
        return _num(m.group(2) or m.group(3)), raw
    return _num(raw), raw


def _units(raw):
    """'° F (° C)' → (IP, SI). 하나뿐이면 둘이 같다."""
    raw = (raw or "").strip()
    if raw in EMPTY:
        return None, None
    m = re.match(r"^(.*?)\s*\(\s*(.*?)\s*\)\s*$", raw)
    if m and m.group(1) and m.group(2):
        return m.group(1).strip(), m.group(2).strip()
    return raw, raw


def is_point_table(head):
    return bool(HEAD.search(head or ""))


def parse_rows(rows_in, fname):
    """(쪽, 셀목록) 목록 → 포인트 레코드. 9열 목록 행만 들어온다고 가정하지 않고 거른다."""
    out, skipped = [], {}
    seen = {}
    for page, cells in rows_in:
        cells = [(c or "").strip() for c in cells]
        if len(cells) < 7:
            skipped["짧은 행"] = skipped.get("짧은 행", 0) + 1
            continue
        num_raw, typ, name = cells[0], cells[1].upper(), cells[2]
        m = NUM.match(num_raw)
        if not m or typ not in TYPES or not name:
            # 쪽마다 되풀이되는 머리글('#' | 'Type')이 여기로 온다
            skipped["머리글·빈 행"] = skipped.get("머리글·빈 행", 0) + 1
            continue
        addr = int(m.group(1))
        fac, units, slope_raw, icept_raw = cells[3], cells[4], cells[5], cells[6]
        on_txt = cells[7] if len(cells) > 7 else ""
        off_txt = cells[8] if len(cells) > 8 else ""

        blk = {"address": addr, "pointType": typ,
               "unbundlable": bool(re.match(r"^\s*\{", num_raw))}
        slope, slope_raw_s = _dual(slope_raw)
        if slope is not None:
            blk["slope"] = slope
            blk["slopeRaw"] = slope_raw_s
        icept, icept_raw_s = _dual(icept_raw)
        if icept is not None:
            blk["intercept"] = icept
            blk["interceptRaw"] = icept_raw_s
        if (fac or "").strip() not in EMPTY:
            blk["factoryDefault"] = fac.strip()
        if (on_txt or "").strip() not in EMPTY:
            blk["onText"] = on_txt.strip()
        if (off_txt or "").strip() not in EMPTY:
            blk["offText"] = off_txt.strip()

        common = {"name": name}
        ip, si = _units(units)
        if ip:
            common["unitIP"] = ip
            common["unitIPRaw"] = units.strip()
        if si:
            common["unitSI"] = si
            common["unitSIRaw"] = units.strip()

        gaps = ["common.readWrite"]
        if "onText" in blk or "offText" in blk:
            # 글자는 있는데 어느 코드가 ON 인지 원문이 안 준다 — 지어내지 않는다
            gaps.append("common.states")
        if icept is None and (icept_raw or "").strip() in EMPTY:
            gaps.append("blocks.fln.intercept")

        src = {"Point #": num_raw, "Type": typ, "Factory Default": fac,
               "Engr. Units": units, "Slope": slope_raw, "Intercept": icept_raw,
               "On Text": on_txt, "Off Text": off_txt}
        rec = {"common": common, "blocks": {"fln": blk},
               "provenance": {"sourceFile": fname, "sourcePage": page,
                              "family": FAMILY, "status": "extracted",
                              "sourceColumns": {k: v for k, v in src.items()
                                                if (v or "").strip() not in EMPTY},
                              "gaps": sorted(set(gaps))}}
        if addr in seen:
            # 쪽 넘김으로 같은 행이 두 번 잡히면 버린다. 다른 내용이면 그건 원문 문제라
            # 세어서 드러낸다 — 조용히 덮지 않는다.
            if seen[addr] != name:
                skipped["같은 번호 다른 이름"] = skipped.get("같은 번호 다른 이름", 0) + 1
            else:
                skipped["쪽 넘김 중복"] = skipped.get("쪽 넘김 중복", 0) + 1
            continue
        seen[addr] = name
        out.append(rec)
    out.sort(key=lambda r: r["blocks"]["fln"]["address"])
    return out, skipped


def crosscheck(path, points):
    """표 인식이 아니라 **쪽 글자 흐름**으로 다시 읽어 대조한다 (규칙 ④).

    기존 crosscheck.py 는 BACnet 타입·인스턴스로 짝을 만드는데 이 표엔 그 열이 없다.
    그래서 계통 전용 대조를 둔다 — 글자 흐름에서 포인트 번호와 Type 코드가 잇달아
    오는 자리를 찾아 그 다음 낱말이 이름과 맞는지 본다.
    """
    import fitz

    doc = fitz.open(path)
    seen = {}
    for i in range(doc.page_count):
        lines = [l.strip() for l in doc[i].get_text().splitlines()]
        for n, ln in enumerate(lines):
            m = NUM.match(ln)
            if not m:
                continue
            nxt = [x for x in lines[n + 1:n + 4] if x]
            if len(nxt) < 2 or nxt[0].upper() not in TYPES:
                continue
            seen.setdefault(int(m.group(1)), nxt[1])
    doc.close()

    both = hit = 0
    misses = []
    for p in points:
        addr = p["blocks"]["fln"]["address"]
        line = seen.get(addr)
        if line is None:
            continue
        both += 1
        name = p["common"]["name"]
        if line.startswith(name[:18]) or name.startswith(line[:18]):
            hit += 1
        elif len(misses) < 5:
            misses.append({"point": addr, "표인식": name, "줄읽기": line[:40]})
    out = {"rate": round(hit / both, 4) if both else 0.0, "both": both,
           "total": len(points),
           "method": "표 인식 대신 쪽 글자 흐름에서 '포인트 번호 + Type 코드' 가 "
                     "잇달아 오는 자리를 찾아 이름을 다시 읽었다"}
    if misses:
        out["misses"] = misses
    return out
