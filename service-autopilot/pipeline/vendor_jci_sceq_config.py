# -*- coding: utf-8 -*-
"""JCI SC-EQ 통신 카드 **자체의 설정 포인트** → point-schema 구조. (10번째 계통)

계통이 무엇인가
  앞의 9계통 중 'SC-EQ' 계통(문서 20건)은 **냉동기가 SC-EQ 를 통해 내보내는** 목록이다
  ('Long Name | Short Name | BACnet | Modbus | N2 …'). 이것은 다르다 — 표가 담은 여섯
  점은 냉동기의 값이 아니라 **SC-EQ 카드 자신의 설정값**이다: 카드의 BACnet 장치 이름·
  인스턴스 ID·문자 인코딩·단위계·붙어 있는 냉동기 기종.
  그래서 머리글이 통째로 다르다 — `Point name | BACnet | Modbus | N2 | Description`.
  이 다섯 낱말 조합은 기존 9계통 어디에도 없다.

  이 여섯 점은 펌웨어가 만든 것이다. 원문 1쪽 개요가 밝힌다 — "Provides BAS system
  writable configuration points eliminating the need for an SC-AP to set these
  parameters in the field"(SC-EQ Firmware 3.0.0.1114). 그전에는 SC-AP 공구로만
  바꿀 수 있었다.

문서 두 건이 같은 표를 싣는다 — 판은 하나다
  ① SI0371 (2쪽) 'SC-EQ Firmware 3.0.0.1114'  … 6점 + **값 표(Table 1) 44종**
  ② 450.50-N1 (60쪽) 'SC-EQ Communication Card Installation Instructions' 46쪽
     'Table 8 - Manual Modbus addresses' … 같은 6점. 값 표는 없고 "Refer to SI0371."
     로 ①에 넘긴다.
  글자 흐름(get_text)으로 따로 읽어 대조했다 — 이름·BACnet·Modbus·N2 네 칸이 여섯 행
  모두 같다. 다른 것은 'N/A'/'n/a' 대소문자와 설명문 어투뿐이다. 값 표를 가진 ① 을
  판으로 삼고 ② 는 근거로만 남긴다(ingest_jci.CORROBORATED).

이 계통에서 실제로 밟은 함정
  1. **값 표에 머리글 행이 없다.** 'Table 1' 의 0행이 이미 데이터다
     ('None (Disables Manual Select) | 0'). 이 저장소의 다른 표는 전부 0행이나 그
     언저리가 머리글이라 습관대로 0행을 버리면 **코드 0(=수동 선택 끄기)** 이 통째로
     사라진다 — 커미셔닝에서 가장 먼저 쓰는 값이다.
  2. **값 표가 두 벌 나란히 놓여 있다.** 실제 열은 [이름|코드|빈칸|이름|코드] 다.
     행 순서로 읽으면 0, 233, 200, 234 … 로 두 벌이 엇갈리고, 왼쪽 벌만 읽으면
     44종 중 22종이 조용히 사라진다. **벌 단위로 세로로** 읽어야 문서 순서가 된다.
  3. **데이터형·배율이 표 밖 각주에 있다.** "Note: Modbus addresses 65001 and 65002
     are Scaled X1 and Unsigned" — 표만 읽으면 modbus.dataType 이 통째로 빈다.
     각주가 **주소를 지목**하므로 그 두 점에만 붙인다(N/A 인 넷에 붙이면 거짓이 된다).
  4. **'MV' 와 'SV'.** MV65001 의 MV 는 BACnet 표준 표기가 아니다 — schema.TYPE_ALIAS
     가 MSV 로 통일한다. SV65000 의 SV(String Value)는 흔치 않아 '타입이 아니다'라고
     버리기 쉬운데 schema.BACNET_TYPES 에 있는 값이다. 버리면 장치 이름 포인트가
     주소 없이 남는다.
  5. **Modbus 65001 은 알려진 대역이 아니다.** 0/1/3/4xxxx(코일·이산입력·입력/보유
     레지스터) 어디에도 안 든다. 앞자리 '6' 을 보고 종류를 지어내지 않고 gap 에 적는다.
  6. **참조가 다른 문서를 가리킨다.** ② 의 'Refer to SI0371.' 은 그 문서 안에서 풀
     수 없다. 못 푼 참조를 조용히 비고로 흘리지 않고 statesRef + gap 으로 남긴다.
  7. **msvOffset.** point-schema columnGuards 는 '참조형 코드표를 풀어 states 를 채운
     포인트에 bacnet 블록이 있으면 msvOffset 기록 의무'라고 한다. 그런데 이 문서에는
     E-Link·SC-EQ 코드표에 있던 '*for BACnet MSV values add 1 to number' 노트가
     **없다**. 없는 보정을 1 로 지어내면 44종 기종 선택이 통째로 한 칸 밀린다 —
     비워 두고 gap 에 그 사실을 적는다.

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_sceq_config.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_sceq_config.py --parse <문서ID|파일경로>
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SOURCE = "jci-york-bas-points"

sys.path.insert(0, HERE)
import schema as S      # noqa: E402

FAMILY = "SC-EQ/Config"

# 값이 아니라 '없음'을 뜻하는 셀 (point-schema rules.emptyMeansAbsent)
ABSENT = {"", "-", "--", "—", "_", "n/a", "na", "none"}

# 머리글 → 우리 이름. squeeze() 를 거친 문자열과 맞춘다.
COLMAP = [("name", r"^Pointname$"), ("bacnet", r"^BACnet$"), ("modbus", r"^Modbus$"),
          ("n2", r"^N2$"), ("desc", r"^Description$")]

# 'BV65000' · 'MV65003' — 타입 문자 + 인스턴스. 타입 정규화는 schema.canon_type 이
# 정본이다(MV→MSV). 사전을 여기서 새로 만들지 않는다(point-schema authority).
BAC_OBJ = re.compile(r"^([A-Za-z]{2,3})\s*(\d{1,7})$")
# 'ADI 201' — point-schema blocks.n2.pointType 허용값 3종
N2_ADDR = re.compile(r"^(ADF|ADI|BD)\s*(\d+)$", re.I)
# '0 = Auto 1 = Manual' · '0 = ISO(UCS-2), 1 = ASCII'
#   ⚠ 항목 경계를 쉼표로 잡으면 안 된다 — SI0371 은 쉼표 없이 붙여 쓰고
#     ('0 = Auto 1 = Manual') 450.50-N1 은 쉼표를 쓴다. 경계는 **다음 코드 '='** 뿐이다.
#   ⚠ 라벨 안에 숫자가 있다('ISO(UCS-2)') — 뒤에 '=' 가 붙을 때만 경계로 본다.
ENUM_ITEM = re.compile(r"(-?\d+)\s*=\s*(.*?)(?=\s*,?\s*-?\d+\s*=|\s*$)", re.S)
# 표 밖 각주 (함정 3)
MB_NOTE = re.compile(r"Modbus\s+addresses?\s+(.*?)\s+are\s+Scaled\s+(\S+?)\s+and\s+"
                     r"(Signed|UnSigned|Unsigned)\b", re.I | re.S)
# 값 표를 알아보는 유일한 근거 — 표 안에는 머리글이 없다(함정 1)
MODEL_CAPTION = re.compile(r"Table\s*1\s*[-–—]\s*MANUAL\s+SELECT\s+CHILLER\s+MODELS", re.I)
# 못 푼 참조인지 ('See Table 1 below' · 'Refer to SI0371.')
REFERENCE = re.compile(r"^\s*(?:see|refer\s+to)\b", re.I)
# point-schema blocks.modbus.dataType normalize
DTYPE = {"signed": "Signed", "unsigned": "Unsigned"}


def docs():
    """이 파서가 훑을 문서 목록 — 정본은 대장(collected.json)이다."""
    import collect
    return collect.files_of(SOURCE)


def clean(v):
    """조판 아티팩트를 지운다 — 게이트를 걸기 **전에** 해야 한다.

    이 계통의 칸 안 줄바꿈은 낱말이 아니라 **구절**을 끊는다
    ('Manual Select Chiller Model' + 개행 + '(YT2 only)'), 그래서 붙이지 않고
    공백으로 바꾼다. YKN2Open 처럼 U+2010 으로 낱말을 끊는 판은 이 문서에 없다
    (실측 0건).
    """
    t = re.sub(r"\s+", " ", str(v or ""))
    t = re.sub(r"^[_\s]+|[_\s]+$", "", t)
    return t.strip()


def squeeze(h):
    """머리글에서 공백과 밑줄 조각을 지운다 — 쪼개진 머리글을 붙여 알아보려고."""
    return re.sub(r"[\s_]+", "", clean(h))


def header_map(head, colmap):
    """머리글 → ({우리이름: 열번호}, 못 알아본 열)."""
    out, unknown = {"_head": {}}, {}
    for i, h in enumerate(head):
        h = clean(h)
        if not h:
            continue
        sq = squeeze(h)
        for name, pat in colmap:
            if name in out:
                continue
            if re.search(pat, sq, re.I):
                out[name] = i
                out["_head"][name] = h
                break
        else:
            unknown[h[:40]] = i
    return out, unknown


def _headname(cmap, key):
    """sourceColumns 의 열쇠로 쓸 원문 열 이름."""
    return (cmap.get("_head") or {}).get(key)


def is_point_head(cells):
    """이 행이 이 계통의 표 머리글인가.

    표식은 **표 머리글**이다 — 본문 글자 흐름으로 잡으면 안 된다(ingest_jci.marks_of).
    다섯 낱말이 이 순서로 붙어 나오는 표는 기존 9계통에 없다.
    """
    sq = squeeze(" | ".join(c or "" for c in cells))
    return bool(re.search(r"Pointname\|BACnet\|Modbus\|N2", sq, re.I))


def _pairs(data):
    """[이름|코드] 벌의 열 번호 짝 목록. 값 표가 아니면 빈 목록 (함정 2).

    판정은 **값 모양**으로 한다 — 머리글이 없으니 이름으로 가를 수가 없다.
    코드 열: 빈칸 아닌 셀이 2개 이상이고 전부 정수.
    이름 열: 그 왼쪽 열이고, 빈칸 아닌 셀이 2개 이상이며 전부 정수는 아니다.
    """
    ncol = max((len(r) for r in data), default=0)
    col = [[clean(r[j]) if j < len(r) else "" for r in data] for j in range(ncol)]
    out = []
    for j in range(1, ncol):
        code = [c for c in col[j] if c]
        name = [c for c in col[j - 1] if c]
        if len(code) >= 2 and all(re.fullmatch(r"\d+", c) for c in code) \
                and len(name) >= 2 and not all(re.fullmatch(r"\d+", c) for c in name):
            out.append((j - 1, j))
    return out


def chiller_models(doc):
    """'Table 1 - MANUAL SELECT CHILLER MODELS' → ([{code,label}], 쪽번호).

    표 안에 머리글이 없으므로(함정 1) **쪽의 표제**로 표를 지목한다. 모양만으로
    고르면 이 계통 밖 문서의 숫자 표까지 값 표로 둔갑한다.
    벌 단위로 세로로 읽어 문서 순서를 지킨다(함정 2).
    """
    out, page = [], None
    for pi, pg in enumerate(doc):
        if not MODEL_CAPTION.search(pg.get_text() or ""):
            continue
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            pairs = _pairs(data)
            if not pairs:
                continue
            page = pi + 1
            for ni, ci in pairs:                    # 벌 하나를 끝까지 (세로로)
                for r in data:
                    nm = clean(r[ni]) if ni < len(r) else ""
                    cd = clean(r[ci]) if ci < len(r) else ""
                    if nm and re.fullmatch(r"\d+", cd):
                        out.append({"code": cd, "label": nm})
    return out, page


def modbus_notes(doc):
    """표 밖 각주 → {Modbus 주소: {scaleRaw, dataType}} (함정 3).

    각주가 주소를 지목한다("Modbus addresses 65001 and 65002 are …") — 그 주소에만
    붙인다. 표 전체에 뿌리면 Modbus 가 'N/A' 인 네 점에도 데이터형이 생긴다.
    """
    out = {}
    for pg in doc:
        for m in MB_NOTE.finditer(pg.get_text() or ""):
            info = {"scaleRaw": clean(m.group(2)).rstrip("."),
                    "dataType": DTYPE.get(clean(m.group(3)).lower())}
            for a in re.findall(r"\d+", m.group(1)):
                out[int(a)] = dict(info)
    return out


def states_of(text):
    """'0 = Auto 1 = Manual' → [{code,label}]. 열거가 아니면 빈 목록."""
    raw = str(text or "")
    if "=" not in raw:
        return []
    out = []
    for m in ENUM_ITEM.finditer(raw):
        label = re.sub(r"\s+", " ", m.group(2)).strip(" ,.")
        if label:
            out.append({"code": m.group(1), "label": label})
    return out if len(out) >= 2 else []


def row_to_point(row, cmap, fname, page, notes, models):
    """행 하나 → 포인트 레코드. 포인트가 아니면 (None, 사유)."""
    def cell(key):
        i = cmap.get(key)
        return clean(row[i]) if i is not None and i < len(row) else ""

    name = cell("name")
    if not name:
        return None, "blank"
    if squeeze(name).lower() == "pointname":            # 머리글이 되풀이된 행
        return None, "banner"

    rec = {"common": {"name": name}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": FAMILY}}
    src, gaps = {}, []

    # ── BACnet 'BV65000' (함정 4) ────────────────────────────────────────
    b = cell("bacnet")
    if b.lower() not in ABSENT:
        src[_headname(cmap, "bacnet") or "BACnet"] = b
        m = BAC_OBJ.match(b)
        if m:
            canon = S.canon_type(m.group(1).upper())
            blk = {"instance": int(m.group(2))}
            if canon in S.BACNET_TYPES:
                blk["objectType"] = canon
            else:
                gaps.append("bacnet.objectType — 표기 %r 이 schema.BACNET_TYPES 에 없다. "
                            "인스턴스만 실었다" % m.group(1))
            rec["blocks"]["bacnet"] = blk
        else:
            gaps.append("bacnet — 칸 %r 이 '타입+인스턴스' 꼴이 아니다. 원표기만 남겼다" % b)

    # ── Modbus (함정 3·5) ────────────────────────────────────────────────
    mb = cell("modbus")
    if mb.lower() not in ABSENT:
        src[_headname(cmap, "modbus") or "Modbus"] = mb
        if re.fullmatch(r"\d+", mb):
            addr = int(mb)
            # ⚠ 0-base/1-base 를 문서가 밝히지 않는다 — 'unknown' 으로 명시한다
            #   (point-schema columnGuards 'MODBUS Address': 동반 의무).
            blk = {"address": addr, "addressBase": "unknown"}
            if mb[0] not in "0134":
                gaps.append("modbus.refClass — 주소 %d 가 알려진 대역(0/1/3/4xxxx)이 "
                            "아니다. 앞자리로 레지스터 종류를 지어내지 않았다" % addr)
            note = notes.get(addr)
            if note:
                if note.get("dataType"):
                    blk["dataType"] = note["dataType"]
                if note.get("scaleRaw"):
                    # point-schema columnGuards 'MODBUS Scale' — 어휘→수치 변환표가
                    # 확정되기 전엔 수치화 보류. 같은 계통(vendor_jci_sceq)도 같다.
                    blk["scaleRaw"] = note["scaleRaw"]
                    gaps.append("modbus.scale — 각주 원표기 %r. 곱·나눗 방향을 문서가 "
                                "밝히지 않아 수치로 올리지 않았다" % note["scaleRaw"])
                src["Note (표 밖 각주)"] = ("Modbus addresses … are Scaled %s and %s"
                                          % (note.get("scaleRaw"), note.get("dataType")))
            else:
                gaps.append("modbus.dataType — 표에 데이터형 열이 없고 각주도 이 주소를 "
                            "지목하지 않는다")
            rec["blocks"]["modbus"] = blk
        else:
            gaps.append("modbus.address — 칸 %r 이 숫자가 아니다. 원표기만 남겼다" % mb)

    # ── N2 'ADI 201' ─────────────────────────────────────────────────────
    n2 = cell("n2")
    if n2.lower() not in ABSENT:
        src[_headname(cmap, "n2") or "N2"] = n2
        m = N2_ADDR.match(n2)
        if m:
            rec["blocks"]["n2"] = {"pointType": m.group(1).upper(),
                                   "address": int(m.group(2))}
        else:
            gaps.append("n2 — 칸 %r 이 'ADF/ADI/BD 번호' 꼴이 아니다. 원표기만 남겼다" % n2)

    # ── Description — 열거 · 참조 · 자유문 세 가지가 섞여 있다 ───────────
    desc = cell("desc")
    if desc.lower() not in ABSENT:
        src[_headname(cmap, "desc") or "Description"] = desc
        sts = states_of(desc)
        if sts:
            rec["common"]["states"] = sts
        elif REFERENCE.match(desc):
            rec["common"]["statesRef"] = desc
            if models and re.search(r"\bTable\s*1\b", desc, re.I):
                rec["common"]["states"] = [dict(x) for x in models]
                # ⚠ 없는 보정을 지어내면 44종이 통째로 한 칸 밀린다 (함정 7)
                gaps.append("bacnet.msvOffset — 참조 코드표를 풀어 states 를 채웠는데 "
                            "이 문서에는 '*for BACnet MSV values add 1 to number' 같은 "
                            "보정 노트가 없다. 0 으로도 1 로도 단정하지 않고 비웠다")
            else:
                gaps.append("states — 참조 %r 가 이 문서 밖을 가리켜 값 표를 풀지 "
                            "못했다" % desc)
        else:
            rec["common"]["note"] = desc

    if src:
        rec["provenance"]["sourceColumns"] = src
    if gaps:
        rec["provenance"]["gaps"] = gaps
    return rec, None


# BACnet 오브젝트 타입 → common.pointKind (문서 원문이 아니라 규정된 파생).
#   MSV 는 값이 코드다 — E-Link 계통이 'Code Monitor' 를 code 로 두는 것과 같은 자리다.
#   SV(String Value)는 허용값 셋(analog·binary·code) 어디에도 없다 → 비우고 gap.
KIND = {"AV": "analog", "AI": "analog", "AO": "analog",
        "BV": "binary", "BI": "binary", "BO": "binary",
        "MSV": "code", "MSI": "code", "MSO": "code"}


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계)."""
    import fitz
    doc = fitz.open(path)
    fname = os.path.basename(path)
    rows, unknown, head_seen = [], {}, None
    skipped = {"modelCodeTable": 0, "nonPointTable": 0}
    models, _mpage = chiller_models(doc)
    notes = modbus_notes(doc)
    for pi, pg in enumerate(doc):
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if not data:
                continue
            # 머리글은 0행이지만 표 제목이 앞에 붙는 판을 대비해 앞 3행에서 찾는다
            hi = next((i for i, r in enumerate(data[:3]) if is_point_head(r)), None)
            if hi is None:
                # 값 표는 '뺀 행'이 아니라 **다른 포인트의 states 로 쓰인 행**이다.
                # 조용히 버리지 않고 사유와 함께 센다(제외 행을 표면화하는 규칙).
                if _pairs(data) and MODEL_CAPTION.search(pg.get_text() or ""):
                    skipped["modelCodeTable"] += len(data)
                else:
                    skipped["nonPointTable"] += len(data)
                continue
            cmap, unk = header_map(data[hi], COLMAP)
            unknown.update(unk)
            head_seen = [clean(c) for c in data[hi]]
            for r in data[hi + 1:]:
                rec, why = row_to_point(r, cmap, fname, pi + 1, notes, models)
                if rec is None:
                    if why:
                        skipped[why] = skipped.get(why, 0) + 1
                    continue
                rows.append(rec)
    doc.close()

    for r in rows:
        bt = (r["blocks"].get("bacnet") or {}).get("objectType")
        kind = KIND.get(bt)
        if kind:
            r["common"]["pointKind"] = kind
        elif bt:
            r["provenance"].setdefault("gaps", []).append(
                "pointKind — BACnet 타입 %r 은 허용값 셋(analog·binary·code) 어디에도 "
                "맞지 않는다. 지어내지 않고 비웠다" % bt)
        # readWrite 열이 없다. 개요 문장은 '이 표가 쓰기 가능하다'까지만 말하고
        # 포인트별 방향은 밝히지 않는다 — point-schema 가 타입 추측을 금한다.
        r["provenance"].setdefault("gaps", []).append(
            "readWrite — 문서에 읽기/쓰기 열이 없다. 원문 개요가 'Provides BAS system "
            "writable configuration points' 라고만 밝혀 포인트별 방향을 확정하지 못했다")
    return rows, unknown, head_seen, skipped


def main(argv):
    ap = argparse.ArgumentParser(description="JCI SC-EQ 통신 카드 설정 포인트 취입")
    ap.add_argument("--scan", action="store_true", help="대장의 문서를 훑어 머리글만 본다")
    ap.add_argument("--parse", help="문서ID 또는 파일 경로")
    a = ap.parse_args(argv)
    if a.parse:
        path = a.parse if os.path.exists(a.parse) else None
        if path is None:
            for p in docs():
                if a.parse in os.path.basename(p):
                    path = p
                    break
        if not path:
            print("문서를 못 찾았다: %s" % a.parse)
            return 1
        rows, unk, head, skipped = parse_doc(path)
        print("머리글: %s" % head)
        print("포인트 %d점 · 못 알아본 열 %s · 뺀 행 %s" % (len(rows), list(unk), skipped))
        for r in rows:
            print("  " + json.dumps(r, ensure_ascii=False)[:260])
        return 0
    if a.scan:
        for p in docs():
            rows, unk, head, _s = parse_doc(p)
            if rows:
                print("%-46s %5d점 %s" % (os.path.basename(p)[:46], len(rows), list(unk)))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
