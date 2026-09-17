# -*- coding: utf-8 -*-
"""JCI IPU/Series-100 계통 — 옥상형·자립형 IOM **본문**에 묻힌 포인트 표.

계통이 무엇인가
  JCI 는 냉동기만 포인트 리스트를 별도 문서로 낸다. 공조기·옥상형·자립형은
  200쪽짜리 설치·운전 매뉴얼(IOM) **본문 후반**(대개 p110~190대)에 표를 묻어 둔다.
  제목에는 아무 낌새가 없다 — 'Installation, Operation and Maintenance' 다.
  그래서 제목으로 문서를 고르던 동안 이 계통이 통째로 빠져 있었다(본문 전수 스캔
  1,492건에서 21문서 4,250행을 찾았다 — scan_jci.py).

표 한 벌 (6열, 머리글이 표의 0행)
  BACnet NAME | USER INTERFACE NAME | READ/WRITE | BACnet OBJECT TYPE AND INSTANCE
  | MODBUS REGISTER ADDRESS | POINTS LIST DESCRIPTION

  · 이름이 셋이다 — 기계 이름(BACnet NAME) · 사람 이름(USER INTERFACE NAME) ·
    설명 문장(POINTS LIST DESCRIPTION). 셋을 한 칸에 뭉치면 나중에 못 가른다.
  · 오브젝트는 'AI01' 처럼 타입+제로패딩 인스턴스가 한 칸에 온다.
  · Modbus 는 3자리 평문 주소다(514). 0-base/1-base 를 문서가 밝히지 않는다.

실측 함정
  1. **밑줄 아티팩트가 거의 전 행에 있다** — 'ACT SAT SP _ _'. PDF 조판이 밑줄
     글리프를 별도 조각으로 뱉는다(YZD 에서 겪은 것과 같은 함정). 게이트보다 먼저
     지운다(point-schema rules.artifactCleanupFirst). 꼬리와 낱말 사이에 홀로 선
     '_' 만 지운다 — 'SNVT_lev_percent' 처럼 낱말에 붙은 밑줄까지 지우면 다른
     계통이 깨진다.
  2. **열 수가 3~7 로 흔들린다.** 표 인식이 열을 합치거나 쪼갠다. 위치로 매핑하면
     문서마다 깨지므로 **머리글 글자**로 매핑한다.
  3. 표가 수십 쪽에 걸치고 쪽마다 머리글이 되풀이된다 — 머리글 행은 포인트가 아니다.

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_ipu.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_ipu.py --parse <문서ID|제목 조각>
"""
import argparse
import io
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SCAN = os.path.join(DATA, "jci-body-scan.json")
# 본문 스캔은 두 번 돌았다. 첫 판(jci-body-scan)은 1,492건 대상이라
# 덕트·옥상형 포털을 다 덮지 못했고, 두 번째 판(jci-duct-verdict)이 1,207건을
# 전수로 다시 훑어 L-Series 같은 누락분을 찾아냈다. 둘 다 스캔 산출물이라
# 손으로 옮겨 적지 않고 여기서 합쳐 읽는다 — 한쪽만 보면 뒤에 찾은 문서가
# 제품명을 잃고 파일이름으로 새 모델을 만들어 버린다.
VERDICT = os.path.join(DATA, "jci-duct-verdict.json")
RAW = os.path.join(DATA, "raw", "_scan_jci")
FAMILY = "IPU/Series-100"
sys.path.insert(0, HERE)

# 머리글 글자 → 우리 열쇠. 표 인식이 열을 합쳐도 글자로 찾으면 걸린다.
# 머리글은 **공백을 다 지우고** 맞춘다. 같은 표인데 문서마다 조판이 다르다 —
# 'B A C N E T NAME' · 'IN STANCE' · 'USER INTER- FACE NAME' 이 전부 같은 열이다.
# 공백 하나 때문에 열을 못 알아보면 그 열의 값이 통째로 사라지는데, 파싱은 성공한
# 것처럼 보인다(실측: N2 주소 열을 5문서에서 통째로 버리고 있었다).
COLMAP = [
    ("objName", r"BACNETNAME"),
    ("uiName", r"USERINTERFACENAME"),
    ("rw", r"READ/?WRITE"),
    ("obj", r"OBJECTTYPEANDINSTANCE"),
    ("modbus", r"MODBUSREGISTER"),
    ("desc", r"POINTS?LISTDESCRIPTION"),
    # 문서에 따라 LON·단위 열이 더 있다. 없는 문서가 많지만 있을 때 버리면 안 된다
    ("snvt", r"SNVT"),
    ("unit", r"ENGUNITS"),
    ("n2", r"N2ADDRESS"),
]
OBJ = re.compile(r"^([A-Za-z]{2,3})\s*0*(\d{1,4})$")
# 한 칸에 오브젝트가 둘인 행이 있다 — 'AV83 BV07'(HEAT ENABLE). 설정에 따라
# 아날로그로도 바이너리로도 나오는 점이라 둘째를 버리면 조용히 사라진다.
OBJ2 = re.compile(r"^([A-Za-z]{2,3}\s*\d{1,4})(?:\s+([A-Za-z]{2,3}\s*\d{1,4}))+$")
RW = {"R": "R", "W": "W", "R/W": "R/W", "RW": "R/W", "W/R": "R/W"}


# 첨자를 받을 수 있는 원소 기호 — validate.SUBSCRIPT 와 같은 집합을 쓴다.
# 넓히면(H·O·N 같은 한 글자) 'AI 2' 같은 멀쩡한 값까지 붙여 버린다.
_ELEM = re.compile(r"\b(?:Re)?(?:CO|NO|SO|NH|CH)\b(?!\d)")
# 첨자 줄 — 숫자만 있다. 한 줄에 첨자가 둘이면 '2 2' 로 온다.
# 뒤에 '_' 가 붙어 오는 판도 있다('CO 1 OUT\n2_ _'): 원문의 밑줄이 첨자와 함께
# 이 줄로 밀려난 것이다. 그 밑줄은 앞 줄의 공백 자리로 돌아가야 한다.
_SUBLINE = re.compile(r"^(\d(?:\s+\d)*)((?:\s*_)*)$")


def join_subscripts(s):
    """아래첨자를 제자리에 되돌린다.

    PyMuPDF 는 CO2 의 '2' 를 **제 줄로** 떼어낸다 — 셀 원문이 실제로 이렇게 온다:
        'CO Level Of The\n2\nOutside Air'        -> CO2 Level Of The Outside Air
        'Displays the actual OA air CO (PPM)\n2' -> ... CO2 (PPM)
        'CO level. "CO lvl inside BAS" must\n2 2\n...'  첨자 둘이 한 줄에 온다
    그냥 줄바꿈을 공백으로 바꾸면 'CO Level Of The 2 Outside Air' 로 굳는다.
    각주 번호처럼 보여 검수를 통과한다 — 실제로 113건이 확정본에 들어갔었다(67fd3b6).
    그때는 데이터만 고쳐 재파싱하면 되살아났다. 여기서 자리를 잡아야 끝난다.

    ⚠ 숫자 개수와 앞 줄의 첨자 없는 원소 기호 개수가 **딱 맞을 때만** 붙인다.
       어긋나면 손대지 않는다 — 짐작으로 채우면 시뮬레이터가 그대로 믿는다.
       안 붙인 것은 validate 의 subscript-split 경고가 잡는다.
    """
    out = []
    for ln in (s or "").split("\n"):
        t = ln.strip()
        m0 = _SUBLINE.match(t) if (out and t) else None
        if m0:
            digits = m0.group(1).split()
            unders = m0.group(2).count("_")
            spots = list(_ELEM.finditer(out[-1]))
            if len(spots) == len(digits):
                prev = out[-1]
                for m, d in reversed(list(zip(spots, digits))):
                    prev = prev[:m.end()] + d + prev[m.end():]
                # 밀려난 밑줄 되돌리기 — 개수가 앞 줄 공백 수와 **딱 맞을 때만**.
                # 'CO 1 OUT' + '2_ _' → 공백 2 · 밑줄 2 → 'CO2_1_OUT'. 어긋나면
                # 어느 공백이 밑줄이었는지 알 수 없으므로 손대지 않는다.
                if unders and unders == prev.count(" "):
                    prev = prev.replace(" ", "_")
                out[-1] = prev
                continue
        out.append(ln)
    return "\n".join(out)


def clean(v):
    """조판 아티팩트를 먼저 지운다 — 게이트를 그 앞에 걸면 오염된 값이 통과한다."""
    s = join_subscripts(v).replace("\n", " ")
    s = re.sub(r"(?:\s+_)+\s*$", "", s)          # 꼬리 '_ _'
    s = re.sub(r"\s+_\s+", " ", s)               # 낱말 사이에 홀로 선 '_'
    return re.sub(r"\s+", " ", s).strip()


def norm_head(s):
    """머리글만 한 번 더 편다 — 값에는 쓰지 않는다.

    같은 표인데 문서마다 조판이 다르다. 실측 두 가지:
      · 소프트 하이픈  'OBJECT TYPE AND IN(soft)STANCE'
      · 벌어진 자간    'B A C N E T NAME' · 'USER I N T E R F A C E NAME'
    이대로 두면 열을 못 알아보고 그 열의 값이 통째로 사라진다(실측 1문서 5열).
    값까지 이렇게 펴면 한 글자짜리 진짜 값('R')이 이웃과 붙으므로 머리글에만 쓴다.
    """
    s = (s or "").replace(chr(0xAD), "").replace(chr(0x2010), "-")
    # 줄바꿈 하이픈도 편다 — 'USER INTER- FACE NAME'(Versecon). 이 열을 못 읽으면
    # 그 문서의 이름이 통째로 빈다(실측 163점/181행).
    s = re.sub(r"(?<=[A-Za-z])-\s+(?=[A-Za-z])", "", s)
    s = re.sub(r"(?:\b\w\b[ ]){2,}\b\w\b",
               lambda m: m.group(0).replace(" ", ""), s)
    return re.sub(r"\s+", " ", s).strip()

def header_map(head):
    """머리글 행 → ({열쇠: 열번호}, 못 알아본 열)."""
    cmap, unknown = {}, []
    for i, cell in enumerate(head):
        c = norm_head(clean(cell))
        if not c:
            continue
        flat = re.sub(r"\s+", "", c)
        for key, pat in COLMAP:
            if re.search(pat, flat, re.I):
                cmap.setdefault(key, i)
                break
        else:
            unknown.append(c[:40])
    return cmap, unknown


def row_to_point(vals, cmap, fname, page):
    import schema as S

    def get(k):
        i = cmap.get(k)
        return clean(vals[i]) if i is not None and i < len(vals) else ""

    obj = get("obj")
    # FIX: normalize separators in BACnet object string (e.g. "BV5, AV81", "BV6-AV82")
    obj = re.sub(r'[,|&/\-]', ' ', obj)
    obj = re.sub(r'\s+', ' ', obj).strip()
    
    ui, desc = get("uiName"), get("desc")
    name = ui or desc
    if not name and not obj:
        return None, "empty"
    rec = {"common": {}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": FAMILY}}
    raw, gaps = {}, []
    if name:
        rec["common"]["name"] = name
    on = get("objName")
    if on:
        rec["common"]["shortName"] = on
        rec["blocks"].setdefault("bacnet", {})["objectName"] = on
    if desc and ui:
        rec["common"]["note"] = desc          # 설명 문장은 이름과 다른 자리다
    alts = []
    if OBJ2.match(obj):
        parts = obj.split()
        obj, alts = parts[0], parts[1:]
    m = OBJ.match(obj)
    if m:
        ty = S.TYPE_ALIAS.get(m.group(1).upper(), m.group(1).upper())
        if ty in S.BACNET_TYPES:
            rec["blocks"].setdefault("bacnet", {})["objectType"] = ty
            rec["blocks"]["bacnet"]["instance"] = int(m.group(2))
            if alts:
                rec["blocks"]["bacnet"]["alternates"] = alts
        else:
            raw["BACnet OBJECT TYPE AND INSTANCE"] = obj
            gaps.append("BACnet 타입이 표준 밖(%r)" % obj)
    elif obj:
        raw["BACnet OBJECT TYPE AND INSTANCE"] = obj
        gaps.append("오브젝트 표기를 못 갈랐다(%r)" % obj)
    mb = get("modbus")
    if re.fullmatch(r"\d{1,6}", mb):
        rec["blocks"].setdefault("modbus", {})["address"] = int(mb)
        # 문서가 0-base/1-base 를 밝히지 않는다 — 관례로 정하면 전 레지스터가 밀린다
        rec["blocks"]["modbus"]["addressBase"] = "unknown"
    elif mb:
        raw["MODBUS REGISTER ADDRESS"] = mb
    rw = RW.get(get("rw").upper().replace(" ", ""))
    if rw:
        rec["common"]["readWrite"] = rw
    n2 = get("n2")
    m2 = re.match(r"^([A-Za-z]{2,3})\s*(\d{1,4})$", n2)
    if m2:
        rec["blocks"].setdefault("n2", {})["pointType"] = m2.group(1).upper()
        rec["blocks"]["n2"]["address"] = int(m2.group(2))
    elif n2:
        raw["N2 ADDRESS"] = n2
    snvt = get("snvt")
    if snvt and snvt.upper() not in ("N/A", "-", "NONE"):
        rec["blocks"].setdefault("lon", {})["snvtType"] = snvt
    un = get("unit")
    if un and un.upper() not in ("N/A", "-", "NONE"):
        # 단위 칸에 상태 열거가 들어오는 행이 있다 — 바이너리 점의 '0, 1'.
        # 라벨이 없으므로 완전한 상태 열거가 아니다. states 로 승격하면 CSV 에서는
        # 빈 라벨이 버려져 모델과 배포본이 달라진다 — 원문 칸에만 보존한다.
        if re.fullmatch(r"[\d\s,/]+", un):
            raw["ENG UNITS"] = un
        else:
            rec["common"]["unitIPRaw"] = un
    if raw:
        rec["provenance"]["sourceColumns"] = raw
    if gaps:
        rec["provenance"]["gaps"] = gaps
    if not rec["blocks"]:
        return None, "noaddr"
    return rec, None


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계)."""
    import fitz
    doc = fitz.open(path)
    rows, unknown, head_seen = [], Counter(), None
    skipped = Counter()
    fname = os.path.basename(path)
    for pi in range(doc.page_count):
        try:
            tabs = doc[pi].find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if len(data) < 2:
                continue
            head = [clean(c) for c in data[0]]
            cmap, unk = header_map(head)
            if "obj" not in cmap and "objName" not in cmap:
                continue                       # 이 표는 우리 것이 아니다
            head_seen = head_seen or head
            unknown.update(unk)
            unmerged = []
            for r in data[1:]:
                if "obj" in cmap and cmap["obj"] < len(r) and "modbus" in cmap and cmap["modbus"] < len(r):
                    obj_raw = r[cmap["obj"]] or ""
                    mb_raw = r[cmap["modbus"]] or ""
                    # fix wrapped BACnet lines e.g. "AV85, BV9\nAV88,\nBV10"
                    obj_raw = re.sub(r',\s*\n\s*', ', ', obj_raw)
                    ol = [x.strip() for x in obj_raw.split('\n') if x.strip()]
                    ml = [x.strip() for x in mb_raw.split('\n') if x.strip()]
                    # verify they are merged rows (BACnet formats and digits)
                    if len(ol) > 1 and len(ol) == len(ml) and all(re.match(r"^[A-Za-z]{2,3}[\s,\-]*\d+", x) for x in ol) and all(x.isdigit() for x in ml):
                        ui_raw = r[cmap.get("uiName", -1)] if "uiName" in cmap and cmap["uiName"] < len(r) else ""
                        ul = [x.strip() for x in ui_raw.split('\n') if x.strip()]
                        for i in range(len(ol)):
                            new_r = list(r)
                            new_r[cmap["obj"]] = ol[i]
                            new_r[cmap["modbus"]] = ml[i]
                            if len(ul) == len(ol):
                                new_r[cmap.get("uiName", -1)] = ul[i]
                            unmerged.append(new_r)
                        continue
                unmerged.append(r)
                
            for r in unmerged:
                vals = [clean(c) for c in r]
                if not any(vals):
                    continue
                # 쪽마다 되풀이되는 머리글은 포인트가 아니다
                if re.search(r"OBJECT\s*TYPE\s*AND\s*INSTANCE", " ".join(vals), re.I):
                    skipped["banner"] += 1
                    continue
                rec, why = row_to_point(vals, cmap, fname, pi + 1)
                if rec:
                    rows.append(rec)
                    continue
                # 주소 칸이 빈 채 이름만 있는 행은 **앞 포인트의 다른 이름**이다.
                # 같은 BI26 이 전기히터면 'ELECT HEAT STAGE 1 STATUS', 가스로면
                # 'STAGED GAS FURN 1 LO STATUS' 로 불린다 — 버리면 그 이름으로 못 찾는다.
                if why == "noaddr" and rows:
                    # 주소 칸이 빈 행은 셋 중 하나다 — 어느 **열**에서 왔는지로 가른다.
                    prev = rows[-1]["common"]
                    ui = clean(vals[cmap["uiName"]]) if cmap.get("uiName", 99) < len(vals) else ""
                    ds = clean(vals[cmap["desc"]]) if cmap.get("desc", 99) < len(vals) else ""
                    handled = False
                    if ui:
                        # 이름 열에 온 것 = 설치 구성에 따른 다른 이름
                        prev.setdefault("altNames", []).append(ui)
                        skipped["altName"] += 1
                        handled = True
                    if ds:
                        m = re.match(r"^(-?\d+)\s*[-=:]\s*(.+)$", ds)
                        if m:
                            # 설명 열의 숫자 줄 = 앞 포인트의 상태 열거
                            prev.setdefault("states", []).append(
                                {"code": m.group(1), "label": m.group(2)[:80]})
                            skipped["stateCont"] += 1
                        else:
                            # 설명 열의 문장 = 앞 행 설명이 줄 넘어 이어진 것
                            prev["note"] = (prev.get("note", "") + " " + ds).strip()
                            skipped["noteCont"] += 1
                        handled = True
                    if handled:
                        continue
                if why:
                    skipped[why] += 1
    doc.close()
    return rows, dict(unknown), head_seen, dict(skipped)


SOURCE = "jci-york-iom-points"


def docs():
    """이 계통이 훑을 문서 — 정본은 대장(collected.json)이다.

    본문 스캔(scan_jci.py)이 후보를 골라 줬지만 그 임시 폴더는 이 PC 에만 있다.
    등록을 마친 뒤에는 대장이 목록을 준다 — 다른 PC 에서 collect.py --run 한 번이면
    같은 목록이 선다(JCI 냉동기 56건에서 같은 이유로 겪었다).
    """
    import collect
    out = []
    by_file = {}
    if os.path.exists(SCAN):
        hits = json.load(io.open(SCAN, encoding="utf-8"))["hits"]
        import sources as SRC
        name_of = {i: n for i, _s, n in getattr(SRC, "JCI_IOM_POINTS", [])}
        for h in hits:
            if h["id"] in name_of:
                by_file[name_of[h["id"]]] = h
    if os.path.exists(VERDICT):
        import sources as SRC
        name_of = {i: n for i, _s, n in getattr(SRC, "JCI_IOM_POINTS", [])}
        for h in json.load(io.open(VERDICT, encoding="utf-8"))["판정"]:
            if h.get("id") in name_of:
                by_file.setdefault(name_of[h["id"]], h)
    for path in collect.files_of(SOURCE):
        h = by_file.get(os.path.basename(path)) or {"id": os.path.basename(path),
                                                    "title": os.path.basename(path)}
        out.append((h, path))
    return out


def main(argv):
    ap = argparse.ArgumentParser(description="JCI IPU/Series-100 계통 어댑터")
    ap.add_argument("--scan", action="store_true", help="적중 문서 전체 파싱 통계")
    ap.add_argument("--parse", help="문서 ID 또는 제목 조각")
    ap.add_argument("--limit", type=int, default=4)
    a = ap.parse_args(argv)
    if a.parse:
        for h, p in docs():
            if a.parse.lower() in h["id"].lower() or a.parse.lower() in h["title"].lower():
                rows, unk, head, skip = parse_doc(p)
                print("%s\n  %d점 · 못 알아본 열 %s · 뺀 행 %s"
                      % (h["title"][:78], len(rows), unk or "없음", skip or "없음"))
                if head:
                    print("  머리글: %s" % " | ".join(x[:22] for x in head if x))
                for r in rows[:a.limit]:
                    print("\n" + json.dumps(r, ensure_ascii=False, indent=1))
                return 0
        print("못 찾겠다: %s" % a.parse)
        return 1
    if a.scan:
        tot = Counter()
        for h, p in docs():
            rows, unk, head, skip = parse_doc(p)
            tot["문서"] += 1
            tot["포인트"] += len(rows)
            for k, v in skip.items():
                tot["뺀:" + k] += v
            print("  %-62s %5d점  %s" % (h["title"][:62], len(rows), skip or ""))
            if unk:
                print("       못 알아본 열: %s" % ", ".join(list(unk)[:5]))
        print("\n%s" % dict(tot))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
