# -*- coding: utf-8 -*-
"""JCI 공조기(airhandling) 포털 — 유닛 제어반 Modbus 레지스터 표 어댑터.

이 계통이 왜 따로 있나
  냉동기·옥상형과 표 생김새가 다르다. BACnet 이름·오브젝트 타입이 없고, 열이 다섯이다:

    PLC register Address | Parameter number | Name | Range | Details
    40001                | 0                | Unit open and close variable | 0, 1 | 0: Off 1: On

  아는 열 이름이 'REGISTER ADDRESS' 하나뿐이라 본문 스캔이 오래 못 찾았다
  (scan_jci.MIN_KINDS 참조). 2026-08-31 에 문턱을 고치고서야 잡혔다.

주소를 무엇으로 볼 것인가 — 데이터가 정해 줬다
  두 열이 다 주소처럼 보인다. 157행 전부에서 **PLC register = 40001 + Parameter number**
  가 성립한다(코드로 확인한다 — 어긋나면 그 행은 gap 으로 남긴다). 즉 Parameter number
  가 0-base 주소이고 40001 쪽은 PLC 표기다. address 에는 0-base 값을 넣고 원표기는
  sourceColumns 에 그대로 남긴다.

문서가 말한 것만 적는다
  · refClass·dataType — 표 바로 위 문장이 "All Modbus parameters are holding register
    and signed integer 16" 이라고 밝힌다. 그래서 holding-register · Signed 다.
  · Range — '0 to 999' 같은 수 범위가 **공학값이 아니다**. 같은 표가 "280 이 28ºC 를
    뜻한다"고 적는다(배율이 행마다 다르고 표가 배율 열을 안 준다). 그래서 rangeSI 를
    채우지 않고 원표기만 남기고 gap 에 적는다 — 시뮬레이터가 raw 를 공학값으로 믿으면 안 된다.
  · states — Details 가 '0: Off 1: On' 처럼 Range 의 코드를 **전부** 풀어 준 행에서만
    만든다. 하나라도 안 풀리면 만들지 않는다(짐작 금지).
  · readWrite — 표에 없다. gap 이다.
"""
import os
import re

FAMILY = "AirHandling/Modbus"
SOURCE = "jci-airhandling-points"
# 이 표를 알아보는 표식 — 다섯 열이 이 순서로 붙은 머리글만 이 계통이다.
HEAD = re.compile(r"PLC\s*register\s*Address\s*\|\s*Parameter\s*number\s*\|\s*Name", re.I)
PLC_BASE = 40001

_RANGE = re.compile(r"^\s*(-?\d+)\s*to\s*(-?\d+)\s*$")
_CODES = re.compile(r"^\s*(\d+(?:\s*,\s*\d+)*)\s*$")


def _codes_of(range_raw):
    """Range 가 코드 목록이면 그 코드들 → ['0','1'] · '0 to 5' → ['0'..'5'].

    범위형도 코드 목록이다. '0 to 5' 인 모드 값이 Details 에서 여섯 가지로 다 풀리는
    행이 실제로 있다 — 쉼표형만 보면 그것을 놓친다. 다만 폭이 크면 열거가 아니라
    계측값이므로 손대지 않는다(온도 '-400 to 999' 같은 것).
    """
    m = _CODES.match(range_raw or "")
    if m:
        return [c.strip() for c in m.group(1).split(",")]
    m = _RANGE.match(range_raw or "")
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 <= hi - lo <= 20:
            return [str(i) for i in range(lo, hi + 1)]
    return None


def _states(range_raw, details):
    """Details 가 Range 의 코드를 **전부** 풀어 줄 때만 상태 목록을 만든다.

    '0, 1' + '0: Off 1: On' → [{code:'0',label:'Off'}, {code:'1',label:'On'}]
    하나라도 안 풀리면 None — 반쯤 채운 열거는 없느니만 못하다.
    """
    codes = _codes_of(range_raw)
    if not codes or not details:
        return None
    found = dict(re.findall(r"(\d+)\s*:\s*([^0-9][^:]*?)(?=\s+\d+\s*:|$)", details))
    out = []
    for c in codes:
        lab = (found.get(c) or "").strip(" .")
        if not lab:
            return None
        out.append({"code": c, "label": lab})
    return out


def crosscheck(path, points):
    """표 인식과 **다른 경로**로 원문을 한 번 더 읽어 대조한다 (규칙 ④).

    왜 필요한가
      이 계통은 정답 대조셋도 없고 기존 crosscheck.py 도 못 쓴다 — 그쪽은 BACnet
      타입·인스턴스로 짝을 만드는데 이 표엔 그런 열이 없다. 그렇다고 확인을 건너뛰면
      "만든 방법으로 검증"하는 셈이라, 표 인식이 열을 밀어 읽어도 아무도 모른다.

    어떻게 다른 경로인가
      표 인식(find_tables)을 쓰지 않고 **쪽 글자 흐름**을 읽는다. 이 표는 글자 흐름에서
      이렇게 온다 — 레지스터가 제 줄에 서고, 다음 줄이 파라미터 번호, 그 다음이 이름이다:

          40001
          0
          Unit open and close variable 0, 1

      레지스터 번호를 열쇠로 삼아 이름 첫 낱말들이 맞는지 본다. 두 경로가 같은 답을
      내면 열 밀림은 아니다.
    """
    import fitz

    doc = fitz.open(path)
    seen = {}
    for i in range(doc.page_count):
        lines = [ln.strip() for ln in doc[i].get_text().splitlines()]
        for n, ln in enumerate(lines):
            if not re.fullmatch(r"4\d{4}", ln):
                continue
            rest = [x for x in lines[n + 1:n + 4] if x]
            if len(rest) < 2 or not re.fullmatch(r"\d+", rest[0]):
                continue
            seen.setdefault(int(ln), rest[1])
    doc.close()

    both = hit = 0
    misses = []
    for p in points:
        plc = (p["provenance"].get("sourceColumns") or {}).get("PLC register Address")
        if not plc or not re.fullmatch(r"\d+", plc):
            continue
        line = seen.get(int(plc))
        if line is None:
            continue
        both += 1
        name = p["common"]["name"]
        # 줄 읽기 쪽은 이름 뒤에 Range 가 붙어 오므로 앞쪽 일치를 본다
        if line.startswith(name[:24]) or name.startswith(line[:24]):
            hit += 1
        elif len(misses) < 5:
            misses.append({"reg": plc, "표인식": name[:48], "줄읽기": line[:48]})
    rate = round(hit / both, 4) if both else 0.0
    out = {"rate": rate, "both": both, "total": len(points),
           "method": "표 인식 대신 쪽 글자 흐름에서 4xxxx 레지스터를 열쇠로 이름을 다시 읽었다"}
    if misses:
        out["misses"] = misses
    return out

def parse_doc(path, rows_in, pages_in):
    """추출된 표 행 → 포인트 레코드 목록.

    rows_in 은 (쪽, 셀목록) 목록이다 — 표 인식은 부르는 쪽(ingest)이 이미 했다.
    여기서는 열 뜻매김만 한다. 파싱과 표 인식을 한 함수에 넣지 않는다.
    """
    fname = os.path.basename(path)
    out, skipped = [], {}
    for page, cells in rows_in:
        cells = [(c or "").strip() for c in cells]
        if len(cells) < 5:
            skipped["짧은 행"] = skipped.get("짧은 행", 0) + 1
            continue
        plc, param, name, rng, details = cells[:5]
        if not name or not re.fullmatch(r"\d+", param or ""):
            skipped["이름·번호 없음"] = skipped.get("이름·번호 없음", 0) + 1
            continue
        addr = int(param)
        gaps = []
        # 두 주소 열이 어긋나면 어느 쪽이 주소인지 단정하지 않는다
        if re.fullmatch(r"\d+", plc or "") and int(plc) != PLC_BASE + addr:
            gaps.append("blocks.modbus.address")
        common = {"name": name}
        if details:
            common["note"] = details
        st = _states(rng, details)
        if st:
            common["states"] = st
        elif rng:
            # 수 범위는 raw 다 — 배율을 문서가 행마다 주지 않아 공학값으로 못 올린다
            gaps.append("common.rangeSI" if _RANGE.match(rng) else "common.states")
        gaps.append("common.readWrite")
        src = {"PLC register Address": plc, "Parameter number": param, "Range": rng}
        out.append({
            "common": common,
            "blocks": {"modbus": {"address": addr, "addressBase": "0",
                                  "refClass": "holding-register", "dataType": "Signed"}},
            "provenance": {"sourceFile": fname, "sourcePage": page, "family": FAMILY,
                           "sourceColumns": {k: v for k, v in src.items() if v},
                           "gaps": sorted(set(gaps)), "status": "extracted"},
        })
    return out, skipped
