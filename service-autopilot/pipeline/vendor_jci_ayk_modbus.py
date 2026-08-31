# -*- coding: utf-8 -*-
"""AYK550 인버터의 4xxxx 고정 레지스터 창 어댑터 (Drive/Modbus).

같은 매뉴얼에 표가 셋 — 이것은 그중 셋째다
  ① 9열 FLN 포인트 목록 97점        ← vendor_jci_fln 이 이미 취입
  ② 4열 리포트 7종                  ← ①의 부분집합. 취입 대상 아님
  ③ 4열 Modbus 고정 레지스터 16행   ← **이 파일**

  ③은 ①과 **다른 항목**이다. 이름이 하나도 안 겹친다(0/16). 같은 드라이브를 다른
  프로토콜 창구로 여는 것이라 판을 따로 둔다.

주소 — 레지스터 번호를 그대로 쓰면 한 칸 어긋난다
  원문이 못 박는다: "The AYK550 supports the zero-based addressing of the Modbus
  specification. Holding register 40002 is addressed as 0001 in a Modbus message."
  즉 **전문 주소 = 레지스터 번호 − 40001** 이다. 40000 을 빼면 한 칸 밀린다.
  선행 숫자 '4' 는 주소 필드에 안 들어간다 — "the leading digit is not included in
  the address field of a Modbus message."

문서가 말한 것만
  · refClass — 기능코드 표가 "03 Read holding 4xxxx registers" 라고 밝힌다 → holding-register.
  · dataType — **전 레지스터에 일반화하면 안 된다.** signed 16비트 명시는 40005…40012
    Actual 값에만 있다("16-bit words containing a sign bit and a 15-bit integer").
    나머지는 원문에 없어 gap 이다.
  · readWrite — Access 열이 준다(R · R/W). 앞선 표들이 못 주던 것을 이 표는 준다.
  · Remarks 는 note 로 보존한다. 프로파일 조건("Supported only if the drive is
    configured to use the YORK Drives Profile (5305 = 0)")이 거기 들어 있다.

  ⚠ 표에 없는 레지스터가 있다 — 40013…40030, 40035…40099 는 정의되지 않았고,
    40101…49999 는 드라이브 파라미터로 **규칙 매핑**이라 행이 없다. 레지스터마다
    행이 있으리라 기대하면 안 된다.
"""
import re

FAMILY = "Drive/Modbus"
SOURCE = "jci-airhandling-fln"          # 같은 문서에서 나온다 — 소스를 새로 만들지 않는다
REG_BASE = 40001                        # 전문 주소 = 레지스터 − REG_BASE (원문 명시)

HEAD = re.compile(r"Modbus\s*Register.*Access.*Remarks", re.I | re.S)
REG = re.compile(r"^\s*(4\d{4})\s*$")
ACCESS = {"R": "R", "R/W": "R/W", "RW": "R/W", "W": "W"}
# 자료형을 원문이 밝힌 구간 — Actual 값만이다
SIGNED_FROM, SIGNED_TO = 40005, 40012
EMPTY = {"", "-", "--", "N/A"}


def is_point_table(head):
    return bool(HEAD.search(head or ""))


def parse_rows(rows_in, fname):
    out, skipped = [], {}
    seen = {}
    for page, cells in rows_in:
        cells = [(c or "").strip() for c in cells]
        if len(cells) < 3:
            skipped["짧은 행"] = skipped.get("짧은 행", 0) + 1
            continue
        reg_raw, name, access = cells[0], cells[1], cells[2]
        remarks = cells[3] if len(cells) > 3 else ""
        m = REG.match(reg_raw)
        if not m or not name:
            # 쪽마다 되풀이되는 머리글이 여기로 온다
            skipped["머리글·빈 행"] = skipped.get("머리글·빈 행", 0) + 1
            continue
        reg = int(m.group(1))
        addr = reg - REG_BASE
        gaps = []

        blk = {"address": addr, "addressBase": "0", "refClass": "holding-register"}
        if SIGNED_FROM <= reg <= SIGNED_TO:
            blk["dataType"] = "Signed"
        else:
            # 원문이 이 구간 밖의 자료형을 밝히지 않는다 — 앞 표의 'Signed' 를 베끼지 않는다
            gaps.append("blocks.modbus.dataType")

        common = {"name": name}
        rw = ACCESS.get(access.upper().replace(" ", ""))
        if rw:
            common["readWrite"] = rw
        elif access.strip() not in EMPTY:
            gaps.append("common.readWrite")
        if remarks.strip() not in EMPTY:
            common["note"] = remarks

        src = {"Modbus Register": reg_raw, "Access": access, "Remarks": remarks}
        rec = {"common": common, "blocks": {"modbus": blk},
               "provenance": {"sourceFile": fname, "sourcePage": page,
                              "family": FAMILY, "status": "extracted",
                              "sourceColumns": {k: v for k, v in src.items()
                                                if (v or "").strip() not in EMPTY},
                              "gaps": sorted(set(gaps))}}
        if reg in seen:
            if seen[reg] != name:
                skipped["같은 레지스터 다른 이름"] = skipped.get("같은 레지스터 다른 이름", 0) + 1
            else:
                skipped["쪽 넘김 중복"] = skipped.get("쪽 넘김 중복", 0) + 1
            continue
        seen[reg] = name
        out.append(rec)
    out.sort(key=lambda r: r["blocks"]["modbus"]["address"])
    return out, skipped


def crosscheck(path, points):
    """표 인식이 아니라 쪽 글자 흐름으로 다시 읽어 대조한다 (규칙 ④).

    ⚠ vendor_jci_air 의 대조를 그대로 못 쓴다 — 그쪽은 레지스터 다음 줄이 숫자
      (Parameter number)라고 가정하는데 이 문서엔 그 열이 없다. 여기서는 레지스터
      바로 다음 줄이 **이름**이다.

    ⚠ **포인트가 인용한 쪽만 읽는다.** 문서 전체를 훑으면 같은 레지스터 번호가
      다른 표에도 나와 엉뚱한 줄을 집는다 — 프로토콜 대조표가 'Modbus 40002 /
      N2 AO1 / FLN 60' 처럼 적어 두어서, 전체 훑기로는 40002 의 이름이 'AO1' 로
      읽혔다(실측 3건이 그렇게 어긋났다). 대조는 "우리가 근거로 댄 그 쪽에 그렇게
      적혀 있나" 를 묻는 것이지 "이 번호가 문서 어딘가에 있나" 가 아니다.
    """
    import fitz

    want = {p["provenance"]["sourcePage"] for p in points
            if isinstance(p.get("provenance", {}).get("sourcePage"), int)}
    doc = fitz.open(path)
    seen = {}
    for i in range(doc.page_count):
        if want and (i + 1) not in want:
            continue
        lines = [l.strip() for l in doc[i].get_text().splitlines()]
        for n, ln in enumerate(lines):
            if not REG.match(ln):
                continue
            nxt = [x for x in lines[n + 1:n + 3] if x]
            if nxt:
                seen.setdefault(int(ln), nxt[0])
    doc.close()

    both = hit = 0
    misses = []
    for p in points:
        reg = p["blocks"]["modbus"]["address"] + REG_BASE
        line = seen.get(reg)
        if line is None:
            continue
        both += 1
        name = p["common"]["name"]
        if line.startswith(name[:14]) or name.startswith(line[:14]):
            hit += 1
        elif len(misses) < 5:
            misses.append({"reg": reg, "표인식": name, "줄읽기": line[:40]})
    out = {"rate": round(hit / both, 4) if both else 0.0, "both": both,
           "total": len(points),
           "method": "표 인식 대신 쪽 글자 흐름에서 4xxxx 레지스터 다음 줄의 이름을 다시 읽었다"}
    if misses:
        out["misses"] = misses
    return out
