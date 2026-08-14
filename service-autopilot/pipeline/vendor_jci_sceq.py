# -*- coding: utf-8 -*-
"""JCI SC-EQ 계통 포인트 리스트 → point-schema 구조.

계통이 무엇인가
  York 냉동기 BAS 포인트 리스트 중 'SC-EQ' 표기를 쓰는 19건. 이 저장소가 본
  JCI 문서 8계통 가운데 **구조 함정이 없는 유일한 묶음**이다 — 쪽이 세로이고
  머리글이 표의 0행이며 개정이력표와 병합되지 않는다. 그래서 첫 어댑터로 골랐다.

  ⚠ 같은 JCI 안에서도 계통마다 표가 다르다. RTU(Simplicity SE)는 7열이고
  E-Link 계열은 개정이력표와 한 그리드로 병합돼 머리글이 중간 행에 있다.
  **문서 유형이나 벤더로 일반 규칙을 세우려 하면 깨진다** — 정격 쪽에서
  vendor_aaon·vendor_lennox 를 따로 둔 것과 같은 이유다.

표 두 모양 (열 매핑 한 벌로 덮인다)
  SC-EQ 13열   Long Name | Short Name | Notes | IP Units | SI Units | Enum Set
               | BACnet Object & Instance | N2 Metasys Address | MODBUS… | LON SNVT Type
  YMAE 15열    위에서 Notes·LON 이 빠지고 **IP/SI Min·Max 4열**과 Modbus Function
               Code 가 붙는다. 'BACoid Object & Instance' 는 'BACnet…' 과 같은 뜻.
               ★ 값 범위를 주는 유일한 계통이다 — 시뮬레이터 클램프에 쓸 수 있다.

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_sceq.py --scan
  PYTHONIOENCODING=utf-8 python vendor_jci_sceq.py --parse <문서ID|파일경로>
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SOURCE = "jci-york-bas-points"


def docs():
    """이 파서가 훑을 문서 목록 — 정본은 대장(collected.json)이다.

    조사 단계에는 임시 폴더(data/raw/_probe_jci)를 훑었는데 그 폴더가 이 PC 에만
    있어 다른 곳에서 재현이 안 됐다. 등록 후에는 대장이 목록을 준다.
    """
    import collect
    return collect.files_of(SOURCE)
sys.path.insert(0, HERE)
import specs as SP      # noqa: E402
import schema as S      # noqa: E402
import pointmap as PM   # noqa: E402

FAMILY_SCEQ = "SC-EQ"
FAMILY_YMAE = "YMAE-15"

# 머리글 낱말 → 우리 열 이름. 표기 흔들림을 여기서 흡수한다
#   'BACnet Object & Instance' · 'BACoid Object & Instance' → 같은 것
COLMAP = [
    ("longName",   r"^Long Name"),
    ("shortName",  r"^Short Name"),
    ("notes",      r"^Notes$"),
    ("ipMin",      r"^IP Min"),
    ("ipMax",      r"^IP Max"),
    ("ipUnits",    r"^IP Units"),
    ("siMin",      r"^SI Min"),
    ("siMax",      r"^SI Max"),
    ("siUnits",    r"^SI Units"),
    ("enumSet",    r"^Enum Set"),
    ("bacnet",     r"^(BACnet|BACoid).*Object.*Instance"),
    ("n2",         r"^N2 Metasys"),
    ("mbAddress",  r"^MODBUS Address|^Modbus Address"),
    ("mbScale",    r"^MODBUS Scale|^Modbus Scale"),
    ("mbType",     r"^MODBUS Data Type|^Modbus Data Type"),
    ("mbFunc",     r"^Modbus Function Code|^MODBUS Function"),
    ("lonName",    r"^LON Profile Name|^LON SNVT Profile"),
    ("snvt",       r"SNVT Type|^SNVT"),
]

# 'AV1' · 'MV65001' · 'BV24' → (타입, 인스턴스)
OBJ = re.compile(r"^([A-Za-z]{2,4})\s*[.\-]?\s*(\d+)$")
# 'MV101 /AV411' — 한 오브젝트가 설정에 따라 두 형태로 나온다(실측 50건).
# 첫째를 본체로 삼고 둘째는 alternates 로 남긴다 — 버리면 조용히 사라진다.
OBJ_ALT = re.compile(r"^([A-Za-z]{2,4}\s*\d+)\s*/\s*([A-Za-z]{2,4}\s*\d+)$")
# 'ADF 1' · 'ADI 201' · 'BD 24' → (종별, 주소)
N2 = re.compile(r"^([A-Z]{2,3})\s*(\d+)$")
# 'SNVT_temp_p (105)' — 밑줄이 별도 조각으로 잡혀 '_ SNVT temp p _' 로 오는 경우가 있다
SNVT = re.compile(r"([A-Za-z_]*SNVT[A-Za-z_ ]*?)\s*\((\d+)\)")


def clean(v):
    """조판 아티팩트를 지운다 — 게이트를 걸기 **전에** 해야 한다.

    PDF 표 인식이 밑줄 글리프를 별도 텍스트 조각으로 뱉어 '_ _ YT2 S02 P04' ·
    '_ SNVT_lev_percent _' 처럼 온다. 앵커 정규식을 그 앞에 걸면 오염된 값이
    그냥 통과해 최후 방어선이 무력해진다 (point-schema rules.artifactCleanupFirst).
    """
    t = SP._c(v)
    t = re.sub(r"^[_\s]+|[_\s]+$", "", t)
    t = re.sub(r"\s*_\s*", "_", t) if "SNVT" in t else t
    return t.strip()


def scrambled(h, target):
    """글자 순서가 뒤섞인 머리글인가 — 글자 집합으로 알아본다.

    조판에 따라 표 인식이 글자 조각 순서를 뒤집는 쪽이 있다. 실측: YZ 문서 3쪽의
    'Enum Set' 이 '0EnuUmnd Sefeinted' 로 나온다(원문 텍스트에는 정상).
    **이 열을 놓치면 상태 열거가 통째로 빠진다** — 위치로 때우면 다른 문서에서
    깨지므로 글자 집합이 같은지로 판정한다.
    """
    a = re.sub(r"[^a-z]", "", (h or "").lower())
    b = re.sub(r"[^a-z]", "", target.lower())
    if not a or len(a) < len(b):
        return False
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    if sum((cb - ca).values()):                 # target 글자가 하나라도 빠지면 아니다
        return False
    # 깨진 머리글은 글자가 **늘어난다**('Enum Set' 7자 → 16자). 길이로 자르면
    # 놓치므로, 대신 다른 열 이름을 잘못 삼키지 않는지로 막는다.
    if len(a) > len(b) * 3:
        return False
    for other in ("longname", "shortname", "notes", "ipunits", "siunits",
                  "bacnetobjectinstance", "n2metasysaddress", "modbusaddress",
                  "modbusscale", "modbusdatatype", "lonprofilename", "lonsnvttype"):
        if not sum((Counter(other) - ca).values()) and len(other) > len(b):
            return False                        # 더 긴 다른 열과도 맞으면 판정 보류
    return True


def header_map(head):
    """머리글 → {우리이름: 열번호}. 못 알아본 열은 원문 이름 그대로 남긴다."""
    out, unknown = {}, {}
    for i, h in enumerate(head):
        h = SP._c(h)
        if not h:
            continue
        for name, pat in COLMAP:
            if re.search(pat, h, re.I):
                out.setdefault(name, i)
                break
        else:
            if "enumSet" not in out and scrambled(h, "Enum Set"):
                out["enumSet"] = i          # 글자가 뒤섞인 'Enum Set'
            else:
                unknown[h[:40]] = i
    return out, unknown


def parse_doc(path):
    """문서 → (포인트 목록, 못 알아본 열, 머리글, 뺀 행 통계)."""
    import fitz
    doc = fitz.open(path)
    rows, unknown_cols, head_seen = [], {}, None
    skipped = {"reserved": 0, "banner": 0}
    for pi, pg in enumerate(doc):
        try:
            tabs = pg.find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if len(data) < 2:
                continue
            head = [SP._c(c) for c in data[0]]
            if not re.search(r"Long Name", " ".join(head), re.I):
                continue
            cmap, unk = header_map(head)
            unknown_cols.update(unk)
            head_seen = head
            fam = FAMILY_YMAE if "ipMin" in cmap else FAMILY_SCEQ
            for r in data[1:]:
                rec, why = row_to_point(r, cmap, fam, os.path.basename(path), pi + 1)
                if rec:
                    rows.append(rec)
                elif why:
                    skipped[why] = skipped.get(why, 0) + 1
    doc.close()
    return rows, unknown_cols, head_seen, skipped


def row_to_point(row, cmap, family, fname, page):
    def cell(key):
        i = cmap.get(key)
        return clean(row[i]) if i is not None and i < len(row) else ""

    long_name = cell("longName")
    short = cell("shortName")
    obj = cell("bacnet")
    if not (long_name or short or obj):
        return None, None
    # 표 안에 되풀이되는 머리글 행·구역 밴드는 포인트가 아니다
    if long_name.lower().startswith("long name"):
        return None, "banner"
    # ⚠ **예약 슬롯은 포인트가 아니다** (point-schema rules.reservedSlotNotAPoint).
    #   원문에 주소만 있고 이름이 둘 다 빈 행이 있다 — 실측 745/2,580(29%).
    #   번호는 이어지는데(BV1·BV2·**BV3**·BV4) 이름만 없다. 제조사가 주소를 잡아
    #   두고 아직 안 쓰는 자리다. 이름 없이 실으면 목록이 29% 부풀고, BMS 매핑
    #   화면에서 무엇에 쓰는 오브젝트인지 알 수 없는 행이 대량으로 나온다.
    if not (long_name or short):
        return None, "reserved"

    rec = {"common": {}, "blocks": {}, "provenance": {
        "sourceFile": fname, "sourcePage": page, "family": family}}
    raw, gaps = {}, []

    if long_name:
        rec["common"]["name"] = long_name
    if short:
        rec["common"]["shortName"] = short
    # 'Notes' 열은 비고가 아니라 **적용 조건**이다 — 실측: 'If EEV or R-410a' ·
    # 'If Heatpump' · 'If two system unit' · 'If YCWL'. 즉 "이 옵션이 있어야
    # 이 오브젝트가 나온다"는 뜻이라 availability 로 담는다. note 로 두면 화면에서
    # "값이 없다"와 "옵션이라 해당 없음"이 구분되지 않는다(정격 쪽 appliesWhen 과 같은 개념).
    note = cell("notes")
    if note:
        if re.match(r"^\s*(if|only|when|requires)\b", note, re.I):
            rec["common"]["availability"] = note
        else:
            rec["common"]["note"] = note

    # ── BACnet: 'AV1' → 타입 + 인스턴스 ──────────────────────────────
    alt = None
    if obj:
        ma = OBJ_ALT.match(obj)
        if ma:
            obj, alt = ma.group(1).replace(" ", ""), ma.group(2).replace(" ", "")
        m = OBJ.match(obj)
        if m:
            ty = m.group(1).upper()
            canon = S.TYPE_ALIAS.get(ty, ty)
            if canon in S.BACNET_TYPES:
                rec["blocks"].setdefault("bacnet", {})["objectType"] = canon
                rec["blocks"]["bacnet"]["instance"] = int(m.group(2))
                if canon != ty:
                    raw["BACnet Object & Instance"] = obj
                if alt:
                    rec["blocks"]["bacnet"]["alternates"] = [alt]
                    raw["BACnet Object & Instance"] = "%s /%s" % (obj, alt)
            else:
                raw["BACnet Object & Instance"] = obj
                gaps.append("BACnet 타입 미상(%r)" % ty)
        else:
            raw["BACnet Object & Instance"] = obj
            gaps.append("BACnet 오브젝트 표기 해석 불가(%r)" % obj)

    # ── N2: 'ADF 1' → 종별 + 주소 ────────────────────────────────────
    n2 = cell("n2")
    if n2:
        m = N2.match(n2)
        if m:
            rec["blocks"].setdefault("n2", {})["pointType"] = m.group(1)
            rec["blocks"]["n2"]["address"] = int(m.group(2))
        else:
            raw["N2 Metasys Address"] = n2

    # ── Modbus ──────────────────────────────────────────────────────
    mb = {}
    a = cell("mbAddress")
    if a and re.match(r"^\d+$", a):
        mb["address"] = int(a)
        mb["addressBase"] = "unknown"      # 0/1-base 를 문서가 안 밝힌다
    elif a:
        raw["MODBUS Address"] = a
    sc = cell("mbScale")
    if sc:
        mb["scaleRaw"] = sc                # 방향(곱/나눗) 확정 전이라 수치화 보류
    dt = cell("mbType")
    if dt:
        norm = {"UnSigned": "Unsigned", "unsigned": "Unsigned", "signed": "Signed"}
        v = norm.get(dt, dt)
        if v in ("Signed", "Unsigned"):
            mb["dataType"] = v
        else:
            raw["MODBUS Data Type"] = dt
    fc = cell("mbFunc")
    if fc:
        codes = [int(x) for x in re.findall(r"\d+", fc)]
        if codes:
            mb["functionCodes"] = codes
    if mb:
        rec["blocks"]["modbus"] = mb

    # ── LON: 네트워크 변수 이름 + SNVT 형식 ───────────────────────────
    #   'nvoLvgCHWTemp' 의 nvi/nvo 접두가 방향(입력/출력)을 말한다
    nv = cell("lonName")
    if nv and nv.lower() not in ("none", "n/a", "-", "—"):
        rec["blocks"].setdefault("lon", {})["nvName"] = nv
        low = nv.lower()
        if low.startswith("nvi"):
            rec["blocks"]["lon"]["direction"] = "NV"
        elif low.startswith("nvo"):
            rec["blocks"]["lon"]["direction"] = "NV"
        elif low.startswith("nci"):
            rec["blocks"]["lon"]["direction"] = "NCI"
    sv = cell("snvt")
    if sv:
        m = SNVT.search(sv)
        if m:
            rec["blocks"].setdefault("lon", {})["snvtType"] = m.group(1).strip("_ ")
            rec["blocks"]["lon"]["snvtIndex"] = int(m.group(2))
        else:
            raw["LON SNVT Type"] = sv

    # ── 단위 · 범위 ──────────────────────────────────────────────────
    for key, field in (("ipUnits", "unitIP"), ("siUnits", "unitSI")):
        u = cell(key)
        if not u:
            continue
        if u.lower() in ("none", "n/a", "-", "—"):
            continue
        rec["common"][field] = u
    for lo, hi, field in (("ipMin", "ipMax", "rangeIP"), ("siMin", "siMax", "rangeSI")):
        a2, b2 = cell(lo), cell(hi)
        if a2 and b2 and re.match(r"^-?[\d.]+$", a2) and re.match(r"^-?[\d.]+$", b2):
            rec["common"][field] = {"min": float(a2), "max": float(b2)}

    # ── 상태 열거 ────────────────────────────────────────────────────
    es = cell("enumSet")
    if es:
        st = read_states(es)
        if st:
            rec["common"]["states"] = [{"code": c, "label": l} for c, l in st]
        else:
            rec["common"]["statesRef"] = es    # '(See Table 3)' 같은 참조

    if raw:
        rec["provenance"]["sourceColumns"] = raw
    if gaps:
        rec["provenance"]["gaps"] = gaps
    for k in ("common", "blocks"):
        if not rec[k]:
            del rec[k]
    return rec, None


STATE = re.compile(r"(-?\d+)\s*[=\-:]\s*([^,;0-9][^,;]*)")


def read_states(text):
    got = []
    for code, label in STATE.findall(text or ""):
        label = label.strip(" .,;·")
        if label:
            got.append((code, label[:80]))
    return got if len(got) >= 2 else []


def doc_titles():
    """문서 ID → (제목, 제품명). 조사 스냅샷이 있으면 쓰고 없으면 빈 값."""
    p = os.path.join(DATA, "haystack", "_jci_docs.json")
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as f:
        docs = json.load(f)
    for lst in docs.values():
        for x in lst:
            def meta(k):
                for m in (x.get("metadata") or []):
                    if m.get("key") == k:
                        return (m.get("values") or [""])[0]
                return ""
            out[x["id"]] = (x.get("title", ""), meta("prodname"), meta("category"))
    return out


def render_pages(path, pages, dpi=150):
    """원문 쪽을 그림으로. 대조하려면 값 옆에 원문이 있어야 한다."""
    import base64
    import fitz
    out = {}
    try:
        doc = fitz.open(path)
    except Exception:
        return out
    for pno in sorted(pages):
        if pno < 1 or pno > doc.page_count:
            continue
        pix = doc[pno - 1].get_pixmap(dpi=dpi)
        out[str(pno)] = ("data:image/jpeg;base64," + base64.b64encode(
            pix.tobytes("jpeg", jpg_quality=78)).decode("ascii"))
    doc.close()
    return out


def export_html(out_path):
    """파싱 결과를 볼 수 있는 표로 낸다 — 숫자만 보고는 판단할 수 없다.

    원문 쪽 그림을 함께 담는다. 행을 누르면 그 오브젝트가 실린 쪽이 뜬다 —
    추출이 맞는지는 원문과 나란히 놓고 봐야 판단할 수 있다.
    """
    titles = doc_titles()
    docs = []
    for f in docs():
        rows, unk, head, skip = parse_doc(f)
        if not rows:
            continue
        did = os.path.basename(f)[:-4]
        title, prod, cat = titles.get(did, ("", "", ""))
        # 파일명이 ID 를 정규화한 것이라 앞자리로도 찾아본다
        if not title:
            for k, v in titles.items():
                if k[:14] == did[:14]:
                    title, prod, cat = v
                    break
        pages = {r["provenance"]["sourcePage"] for r in rows}
        docs.append({"id": did, "title": title or did, "product": prod,
                     "category": cat, "family": rows[0]["provenance"]["family"],
                     "points": rows, "skipped": skip,
                     "pageImages": render_pages(f, pages)})
    docs.sort(key=lambda d: (-len(d["points"])))
    data = {"docs": docs,
            "total": sum(len(d["points"]) for d in docs),
            "reserved": sum((d.get("skipped") or {}).get("reserved", 0) for d in docs)}
    html = (PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return data


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>JCI 오브젝트 목록 — SC-EQ 계통</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
  --bg:#fafaf9; --panel:#fff; --ink:#18181b; --dim:#71717a; --faint:#a1a1aa;
  --line:#e4e4e7; --line2:#f4f4f5; --accent:#15803d; --accent-bg:#f0fdf4;
  --warn:#b45309; --warn-bg:#fffbeb; --sel:#f4f4f5;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,"Cascadia Mono",Consolas,monospace;
  --bac:#1d4ed8; --bac-bg:#eff6ff;   /* BACnet */
  --n2:#b45309;  --n2-bg:#fffbeb;    /* N2 Metasys */
  --mb:#7c3aed;  --mb-bg:#f5f3ff;    /* Modbus */
  --lon:#0f766e; --lon-bg:#f0fdfa;   /* LON */
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#18181b; --panel:#1f1f23; --ink:#f4f4f5; --dim:#a1a1aa; --faint:#71717a;
  --line:#3f3f46; --line2:#27272a; --accent:#4ade80; --accent-bg:#14251a;
  --warn:#fbbf24; --warn-bg:#2a2113; --sel:#27272a;
  --bac:#93c5fd; --bac-bg:#17233d;
  --n2:#fbbf24;  --n2-bg:#2a2113;
  --mb:#c4b5fd;  --mb-bg:#241d3d;
  --lon:#5eead4; --lon-bg:#0f2b28;}}
:root[data-theme="dark"]{
  --bg:#18181b; --panel:#1f1f23; --ink:#f4f4f5; --dim:#a1a1aa; --faint:#71717a;
  --line:#3f3f46; --line2:#27272a; --accent:#4ade80; --accent-bg:#14251a;
  --warn:#fbbf24; --warn-bg:#2a2113; --sel:#27272a;
  --bac:#93c5fd; --bac-bg:#17233d;
  --n2:#fbbf24;  --n2-bg:#2a2113;
  --mb:#c4b5fd;  --mb-bg:#241d3d;
  --lon:#5eead4; --lon-bg:#0f2b28;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif}
header{position:sticky;top:0;z-index:9;background:var(--panel);
  border-bottom:1px solid var(--line);padding:13px 18px}
h1{margin:0 0 3px;font-size:17px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:13px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
select,input{font:inherit;font-size:13px;padding:5px 9px;border:1px solid var(--line);
  border-radius:7px;background:var(--panel);color:var(--ink)}
input{min-width:230px}
.wrap{padding:16px 18px 60px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums}
th,td{padding:6px 9px;text-align:left;border-bottom:1px solid var(--line2);
  vertical-align:top;white-space:nowrap}
thead th{position:sticky;top:0;background:var(--line2);font-size:11px;
  letter-spacing:.05em;text-transform:uppercase;color:var(--dim);z-index:1}
td.name{white-space:normal;min-width:190px;max-width:330px}
td.m{font-family:var(--mono);font-size:11.5px}
td.st{white-space:normal;max-width:230px;font-size:11.5px;color:var(--dim)}
td.av{color:var(--warn)}
tbody tr:hover{background:var(--sel);cursor:zoom-in}
dialog{border:none;border-radius:12px;padding:0;background:var(--panel);
  max-width:96vw;max-height:96vh;overflow:hidden}
dialog::backdrop{background:rgba(0,0,0,.75)}
dialog .zh{padding:9px 14px;font-size:13px;border-bottom:1px solid var(--line);
  color:var(--dim);display:flex;gap:12px;align-items:center}
dialog .zh .hint{margin-left:auto;font-size:11.5px;color:var(--faint)}
dialog .zh button{font:inherit;font-size:12px;padding:2px 9px;border:1px solid var(--line);
  border-radius:6px;background:var(--panel);color:var(--ink);cursor:pointer}
.view{width:94vw;height:86vh;overflow:hidden;background:#fff;position:relative;
  cursor:grab;touch-action:none}
.view.drag{cursor:grabbing}
.view img{position:absolute;left:0;top:0;transform-origin:0 0;
  max-width:none;max-height:none;user-select:none;-webkit-user-drag:none}
.tag{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:4px;
  font-family:var(--mono);background:var(--bac-bg);color:var(--bac)}
.tag.n2{background:var(--n2-bg);color:var(--n2)}
.tag.mb{background:var(--mb-bg);color:var(--mb)}
.tag.lo{background:var(--lon-bg);color:var(--lon)}
.protos{float:right;display:flex;gap:5px}
.proto{font:10.5px var(--mono);padding:1px 7px;border-radius:4px;font-weight:400}
.proto b{font-weight:600}
.proto.bacnet{background:var(--bac-bg);color:var(--bac)}
.proto.n2{background:var(--n2-bg);color:var(--n2)}
.proto.modbus{background:var(--mb-bg);color:var(--mb)}
.proto.lon{background:var(--lon-bg);color:var(--lon)}
.docrow{background:var(--line2);font-weight:600}
.docrow td{padding:9px;font-size:12.5px}
.docrow .cat{font-weight:400;color:var(--dim);margin-left:8px}
.docrow .skip{color:var(--faint);font-style:italic}
.empty{padding:36px;text-align:center;color:var(--dim)}
</style>
<header>
  <h1>JCI 오브젝트 목록 — SC-EQ 계통</h1>
  <div class="sub" id="sub"></div>
  <div class="bar">
    <select id="doc"></select>
    <input id="q" placeholder="이름·주소 검색 (예: chilled, AV1, ADF)">
    <span style="font-size:12px;color:var(--dim)">행을 누르면 원문 쪽이 뜬다</span>
    <select id="proto">
      <option value="">프로토콜 전체</option>
      <option value="bacnet">BACnet 있는 것</option>
      <option value="n2">N2 있는 것</option>
      <option value="modbus">Modbus 있는 것</option>
      <option value="lon">LON 있는 것</option>
      <option value="states">상태 열거 있는 것</option>
      <option value="range">값 범위 있는 것</option>
      <option value="avail">적용 조건 있는 것 (옵션 의존)</option>
    </select>
  </div>
</header>
<dialog id="zoom">
  <div class="zh"><span id="zt"></span>
    <button id="zfit">화면 맞춤</button><button id="z100">100%</button>
    <span id="zlv"></span>
    <span class="hint">휠 = 확대·축소 · 끌어서 이동 · Esc 닫기</span></div>
  <div class="view" id="zv"><img id="zi" alt="원문 쪽"></div>
</dialog>
<div class="wrap"><div class="tw"><table>
  <thead><tr>
    <th>이름</th><th>짧은 이름</th><th>BACnet</th><th>N2</th><th>Modbus</th>
    <th>LON</th><th>단위 IP/SI</th><th>범위</th><th>상태</th><th>적용 조건</th><th>비고</th>
  </tr></thead>
  <tbody id="rows"></tbody>
</table></div></div>
<script>
const D = __DATA__;
const esc = s => String(s==null?"":s).replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

const sel=document.getElementById('doc');
sel.innerHTML = '<option value="">문서 전체 ('+D.total+'점)</option>' +
  D.docs.map((d,i)=>'<option value="'+i+'">'+esc(d.title.slice(0,60))+' — '+d.points.length+'점</option>').join('');

function cell(p, path){
  const [b,f]=path.split('.');
  const v=(p.blocks&&p.blocks[b]||{})[f];
  return v==null?'':v;
}
function row(p){
  const c=p.common||{}, bl=p.blocks||{};
  const bac=bl.bacnet?('<span class="tag">'+esc(bl.bacnet.objectType)+'.'+esc(bl.bacnet.instance)+'</span>'):'';
  const n2 =bl.n2?('<span class="tag n2">'+esc(bl.n2.pointType)+' '+esc(bl.n2.address)+'</span>'):'';
  const mb =bl.modbus?('<span class="tag mb">'+esc(bl.modbus.address)+
       (bl.modbus.scaleRaw?(' · '+esc(bl.modbus.scaleRaw)):'')+
       (bl.modbus.dataType?(' · '+esc(bl.modbus.dataType)):'')+'</span>'):'';
  const lon=bl.lon?('<span class="tag lo">'+esc(bl.lon.nvName||bl.lon.snvtType||'LON')+'</span>'):'';
  const u=[c.unitIP,c.unitSI].filter(Boolean);
  const un=u.length?esc(u.join(' / ')):'';
  const rg=c.rangeIP?(c.rangeIP.min+'~'+c.rangeIP.max):'';
  const st=c.states?c.states.map(s=>s.code+'='+s.label).join(', '):(c.statesRef||'');
  const pv=p.provenance||{};
  return '<tr data-d="'+(p._di==null?'':p._di)+'" data-pg="'+esc(pv.sourcePage)+
    '" title="눌러서 원문 '+esc(pv.sourcePage)+'쪽 보기"><td class="name">'+esc(c.name||'')+'</td><td class="m">'+esc(c.shortName||'')+
    '</td><td>'+bac+'</td><td>'+n2+'</td><td>'+mb+'</td><td class="m">'+lon+
    '</td><td class="m">'+un+'</td><td class="m">'+esc(rg)+'</td><td class="st">'+esc(st)+
    '</td><td class="st av">'+esc(c.availability||'')+'</td><td class="st">'+esc(c.note||'')+'</td></tr>';
}
function render(){
  const di=sel.value, q=document.getElementById('q').value.trim().toLowerCase();
  const pr=document.getElementById('proto').value;
  const docs = di===''?D.docs:[D.docs[+di]];
  let out='', n=0;
  docs.forEach(d=>{
    let ps=d.points;
    if(q) ps=ps.filter(p=>JSON.stringify(p).toLowerCase().includes(q));
    if(pr==='states') ps=ps.filter(p=>(p.common||{}).states);
    else if(pr==='range') ps=ps.filter(p=>(p.common||{}).rangeIP);
    else if(pr==='avail') ps=ps.filter(p=>(p.common||{}).availability);
    else if(pr) ps=ps.filter(p=>(p.blocks||{})[pr]);
    if(!ps.length) return;
    n+=ps.length;
    const di=D.docs.indexOf(d);
    ps.forEach(p=>{p._di=di;});
    const sup={bacnet:0,n2:0,modbus:0,lon:0};
    d.points.forEach(p=>{const b=p.blocks||{};for(const k in sup) if(b[k]) sup[k]++;});
    const badges=Object.keys(sup).filter(k=>sup[k]).map(k=>
      '<span class="proto '+k+'">'+({bacnet:'BACnet',n2:'N2',modbus:'Modbus',lon:'LON'})[k]+
      ' <b>'+sup[k]+'</b></span>').join('');
    out+='<tr class="docrow"><td colspan="11">'+esc(d.title)+
      (d.product?('<span class="cat">'+esc(d.product)+'</span>'):'')+
      '<span class="cat">'+esc(d.family)+' · '+ps.length+'점</span>'+
      (((d.skipped||{}).reserved)?('<span class="cat skip">예약 슬롯 '+d.skipped.reserved+'행 제외</span>'):'')+
      '<span class="protos">'+badges+'</span></td></tr>';
    out+=ps.map(row).join('');
  });
  document.getElementById('rows').innerHTML = out ||
    '<tr><td colspan="11" class="empty">해당하는 오브젝트가 없다.</td></tr>';
  document.getElementById('sub').textContent =
    '문서 '+D.docs.length+'건 · 오브젝트 '+D.total+'점 · 지금 보이는 것 '+n+'점' +
    (D.reserved?('  (예약 슬롯 '+D.reserved+'행은 이름이 없어 제외 — 원문이 빈칸이다)'):'');
}
document.addEventListener('click', e=>{
  const tr=e.target.closest('tr[data-pg]');
  if(!tr) return;
  const d=D.docs[+tr.dataset.d], pg=tr.dataset.pg;
  const img=(d&&d.pageImages||{})[pg];
  if(!img){ return; }
  document.getElementById('zi').src=img;
  document.getElementById('zt').textContent=d.title+' — 원문 '+pg+'쪽';
  zs=1; zx=0; zy=0; natW=0;
  document.getElementById('zoom').showModal();
});
const zv=document.getElementById('zv'), zi=document.getElementById('zi');
let zs=1, zx=0, zy=0, natW=0, natH=0;
function apply(){
  zi.style.transform='translate('+zx+'px,'+zy+'px) scale('+zs+')';
  document.getElementById('zlv').textContent=Math.round(zs*100)+'%';
}
function fit(){
  if(!natW) return;
  zs=Math.min(zv.clientWidth/natW, zv.clientHeight/natH);
  zx=(zv.clientWidth-natW*zs)/2; zy=(zv.clientHeight-natH*zs)/2;
  apply();
}
zi.onload=()=>{ natW=zi.naturalWidth; natH=zi.naturalHeight;
  zi.style.width=natW+'px'; zi.style.height=natH+'px'; fit(); };
zv.addEventListener('wheel', e=>{
  e.preventDefault();
  const r=zv.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  // 커서가 가리키는 지점을 고정한 채 배율을 바꾼다
  const k=Math.exp(-e.deltaY*0.0015);
  const ns=Math.min(8, Math.max(0.05, zs*k));
  zx=mx-(mx-zx)*(ns/zs); zy=my-(my-zy)*(ns/zs); zs=ns;
  apply();
}, {passive:false});
let dragging=false, px=0, py=0;
zv.addEventListener('pointerdown', e=>{ dragging=true; px=e.clientX; py=e.clientY;
  zv.classList.add('drag'); zv.setPointerCapture(e.pointerId); });
zv.addEventListener('pointermove', e=>{ if(!dragging) return;
  zx+=e.clientX-px; zy+=e.clientY-py; px=e.clientX; py=e.clientY; apply(); });
zv.addEventListener('pointerup', e=>{ dragging=false; zv.classList.remove('drag'); });
zv.addEventListener('dblclick', ()=>{ zs<1.5?(zs=2,apply()):fit(); });
document.getElementById('zfit').onclick=fit;
document.getElementById('z100').onclick=()=>{
  const cx=zv.clientWidth/2, cy=zv.clientHeight/2;
  zx=cx-(cx-zx)*(1/zs); zy=cy-(cy-zy)*(1/zs); zs=1; apply(); };
window.addEventListener('resize', ()=>{ if(document.getElementById('zoom').open) fit(); });
sel.onchange=render;
document.getElementById('q').oninput=render;
document.getElementById('proto').onchange=render;
render();
</script>
"""


def main(argv):
    ap = argparse.ArgumentParser(description="JCI SC-EQ 계통 어댑터")
    ap.add_argument("--scan", action="store_true", help="계통 19건 전체 파싱 통계")
    ap.add_argument("--parse", help="문서 하나 (파일경로 또는 ID 앞자리)")
    ap.add_argument("--export", action="store_true", help="볼 수 있는 표로 낸다")
    ap.add_argument("--limit", type=int, default=6, help="--parse 시 보여줄 행 수")
    a = ap.parse_args(argv)

    if a.export:
        out = os.path.join(HERE, "..", "review", "jci-points.html")
        data = export_html(out)
        print("  %s" % os.path.normpath(out))
        print("  문서 %d건 · 오브젝트 %d점 · %.1f MB"
              % (len(data["docs"]), data["total"],
                 os.path.getsize(out) / 1024.0 / 1024.0))
        return 0

    if a.parse:
        cands = ([a.parse] if os.path.exists(a.parse)
                 else [p for p in docs() if a.parse.lower() in os.path.basename(p).lower()])
        if not cands:
            print("파일을 못 찾겠다: %s" % a.parse)
            return 1
        rows, unk, head, skip = parse_doc(cands[0])
        print("%s — 포인트 %d" % (os.path.basename(cands[0]), len(rows)))
        if head:
            print("머리글: %s" % " | ".join(h[:20] for h in head if h))
        if unk:
            print("못 알아본 열: %s" % ", ".join(unk))
        for r in rows[:a.limit]:
            print("\n" + json.dumps(r, ensure_ascii=False, indent=1))
        return 0

    if a.scan:
        from collections import Counter
        tot = Counter()
        allunk = Counter()
        files = docs()
        hit = 0
        for f in files:
            rows, unk, head, skip = parse_doc(f)
            if not rows:
                continue
            hit += 1
            fam = rows[0]["provenance"]["family"]
            tot[fam] += len(rows)
            for u in unk:
                allunk[u] += 1
            for r in rows:
                for blk, fields in (r.get("blocks") or {}).items():
                    for k in fields:
                        tot["  %s.%s" % (blk, k)] += 1
                for k in (r.get("common") or {}):
                    tot["  " + k] += 1
                if (r.get("provenance") or {}).get("gaps"):
                    tot["  (gaps)"] += 1
            print("  %-50s %5d점  %s" % (os.path.basename(f)[:50], len(rows), fam))
        print("\n문서 %d건에서 파싱" % hit)
        for k, v in tot.most_common():
            print("   %-26s %6d" % (k, v))
        if allunk:
            print("\n못 알아본 열 (문서 수)")
            for k, v in allunk.most_common(12):
                print("   %-44s %d" % (k[:44], v))
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
