# -*- coding: utf-8 -*-
"""사양 추출 — 카탈로그·설계 가이드에서 **정격 사양 표**를 뽑는다.

포인트 리스트와 사양 표는 구조가 다르다.

  포인트 표 : 한 줄 = 포인트 하나        (AI-1 · 냉수 출구온도 · ℃)
  사양 표   : 한 줄 = **형번 하나**,      (H1 · 0.25–1.5 kW · 2.1 kg · 265 mm)
              열   = 속성

그래서 같은 추출기로는 못 읽는다. 통합 포인트 리스트에는 정격이 아예 실리지 않아
(각 모델의 gap 에 적어 둔 대로) 카탈로그·설계 가이드를 따로 읽어야 한다.

시뮬레이터에 필요한 값 — 정격전압·전류·소비전력·용량·효율 — 이 여기서 나온다.

실행
  python specs.py data/raw/<파일>.pdf        무엇이 잡히는지 본다
  python specs.py --scan                     수집한 문서 전부 훑는다
  python specs.py --attach <모델ID> <파일>    모델에 붙인다
"""
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
sys.path.insert(0, HERE)
import schema as S  # noqa: E402

# 열 이름에서 물리량을 알아본다. 시뮬레이터가 쓰려면 '이 열이 무엇인가'를 알아야 한다.
QUANTITY = [
    ("power", r"\bpower\b|\bkW\b|\bhp\b|출력|소비\s*전력|정격\s*출력|leistung"),
    ("current", r"\bcurrent\b|\bamp|\bA\b|전류|strom"),
    ("voltage", r"\bvolt|\bV\b|전압|spannung"),
    ("frequency", r"\bfrequency\b|\bHz\b|주파수|frequenz"),
    ("efficiency", r"efficien|\bCOP\b|\bEER\b|\bIPLV\b|\bSEER\b|효율"),
    ("loss", r"\bloss(es)?\b|손실|verlust"),
    ("capacity", r"capacity|\bton\b|\bRT\b|\bkcal|용량|능력"),
    ("airflow", r"air\s*flow|\bCFM\b|m³/h|m3/h|풍량"),
    ("pressure", r"pressure|\bPa\b|\bbar\b|압력"),
    ("speed", r"\bspeed\b|\brpm\b|회전수|drehzahl"),
    ("torque", r"torque|\bNm\b|토크|drehmoment"),
    ("temperature", r"temperature|°C|℃|°F|온도"),
    ("weight", r"weight|\bkg\b|\blb\b|중량|무게"),
    ("dimension", r"height|width|depth|\bmm\b|치수|높이|너비|깊이"),
    ("noise", r"noise|sound|\bdB\b|소음"),
    ("protection", r"protection rating|\bIP\d|보호등급"),
]
# 사양 표인지 가리는 신호 — 물리량 이름이거나 대괄호 단위가 있으면 사양 표다
UNIT_BRACKET = re.compile(r"\[[^\]]{1,14}\]")
SPECWORD = re.compile("|".join(p for _, p in QUANTITY), re.I)
NUMERIC = re.compile(r"\d")


def _c(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()


def quantity_of(header_cell):
    """열 이름 → 물리량 이름. 못 알아보면 None (지어내지 않는다)."""
    h = _c(header_cell)
    for name, pat in QUANTITY:
        if re.search(pat, h, re.I):
            return name
    return None


def merge_header(data):
    """머리글이 두 줄로 나뉜 표를 한 줄로 합친다.

    사양 표는 'Power [kW (hp)]' 아래에 '3x200–240 V / 3x380–480 V' 처럼 하위 열이
    붙는 경우가 흔하다. 위 칸이 비어 있으면 아래 칸을, 둘 다 있으면 이어 붙인다.
    """
    if len(data) < 2:
        return [_c(c) for c in data[0]], data[1:]
    h0 = [_c(c) for c in data[0]]
    h1 = [_c(c) for c in data[1]]
    # 두 번째 줄이 값이면(숫자가 많으면) 머리글이 아니다
    if sum(1 for c in h1 if NUMERIC.search(c)) > len(h1) * 0.4:
        return h0, data[1:]
    merged = []
    for a, b in zip(h0, h1 + [""] * (len(h0) - len(h1))):
        merged.append((a + " " + b).strip() if a and b else (a or b))
    return merged, data[2:]


def looks_like_spec(header, rows):
    """이 표가 정격 사양 표인가 → 방향 문자열, 아니면 None.

    사양 표는 방향이 두 가지다.

      column  열 이름이 속성 (Danfoss: 행=형번, 열=kW·A·kg)
      row     **첫 칸이 속성** (Trane 카탈로그: 행=항목, 열=형번 — 전치돼 있다)

    어느 쪽이든 값 칸에 숫자가 실제로 있어야 한다. 그래야 목차·부호 설명표를 거른다.
    """
    cells = [c for r in rows for c in map(_c, r) if c]
    if not cells or sum(1 for c in cells if NUMERIC.search(c)) < max(3, len(cells) * 0.2):
        return None
    head = " | ".join(header)
    if SPECWORD.search(head) or UNIT_BRACKET.search(head):
        return "column"
    # 전치형 — 첫 열에 속성 이름이 줄줄이 있다
    first = [_c(r[0]) for r in rows if r]
    if sum(1 for c in first if SPECWORD.search(c) or UNIT_BRACKET.search(c)) >= 3:
        return "row"
    return None


def caption(pg, table_bbox, limit=90):
    """표 바로 위 텍스트 — 표 제목으로 쓴다."""
    y = table_bbox[1]
    above = [b for b in pg.get_text("blocks") if b[3] <= y + 2 and b[3] > y - 90]
    if not above:
        return ""
    txt = _c(sorted(above, key=lambda b: -b[3])[0][4])
    return txt[:limit]


def extract_specs(pdf, max_pages=None):
    """문서 → 사양 표 목록"""
    import fitz
    doc = fitz.open(pdf)
    out, seen = [], set()
    for pi, pg in enumerate(doc):
        if max_pages and pi >= max_pages:
            break
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if len(data) < 3 or len(data[0]) < 2:
                continue
            header, rows = merge_header(data)
            rows = [[_c(c) for c in r] for r in rows if any(_c(c) for c in r)]
            if len(rows) < 2:
                continue
            orient = looks_like_spec(header, rows)
            if not orient:
                continue
            key = (tuple(header), len(rows), rows[0][0] if rows[0] else "")
            if key in seen:            # 같은 표가 여러 쪽에 이어지면 한 번만
                continue
            seen.add(key)
            # 물리량은 속성이 적힌 쪽에서 읽는다 — 전치형은 첫 열이 속성이다
            qs = ([quantity_of(h) for h in header] if orient == "column"
                  else [quantity_of(r[0]) for r in rows])
            out.append({
                "title": caption(pg, t.bbox),
                "page": pi + 1,
                "orientation": orient,
                "header": header,
                "quantities": qs,
                "rows": rows,
            })
    return out


# ── 두 번째 방식: 항목/값 두 줄 구조 ────────────────────────────────────
# 데이터시트는 표가 아니라 라벨 한 줄, 값 한 줄로 적는 경우가 많다.
#   Power consumption in operation
#   1.5 W
# 이걸 표로 인식하려 하면 0개가 나온다 (Belimo 데이터시트가 그랬다).
SECTION = re.compile(r"^(technical data|[\w /]*\bdata\b|materials?|safety notes?|"
                     r"기술\s*자료|사양)$", re.I)
VALUEISH = re.compile(
    r"^(AC|DC|IP\d|±|<|>|≤|≥|-?\d)"            # AC 24 V · IP54 · ±10% · 1.5 W
    r"|^[\d.,]+\s*(\.\.\.|~|-)\s*[\d.,]+"       # 19.2...28.8
    r"|\b\d+(\.\d+)?\s*(W|VA|V|A|mA|Nm|in-lb|Hz|s|min|°|℃|°C|°F|%|kg|lb|mm|in|dB|rpm)\b",
    re.I)
# 숫자 앞에 글자·하이픈이 붙어 있으면 단위가 아니다 — 'UL94-5VA' 를 '5 VA' 로 읽었다.
UNIT_TAIL = re.compile(
    r"(?<![A-Za-z0-9.\-])(\d[\d.,]*)\s*"
    r"(W|VA|kW|V|A|mA|Nm|in-lb|Hz|s|min|°C|℃|°F|%|kg|lb|mm|in|dBA?|rpm|"
    r"m³/h|m3/h|Pa|kPa|bar)\b")
# 라벨이 아닌 줄 — 머리글·꼬리말·안내문
NOT_LABEL = re.compile(r"^(www\.|picture may|subject to change|\d+\s*/\s*\d+$|"
                       r"technical data sheet|•)", re.I)


def extract_pairs(pdf, max_pages=6):
    """항목/값 두 줄 구조 → [(구역, 항목, 값, 단위)]"""
    import fitz
    doc = fitz.open(pdf)
    out, section = [], ""
    for pi in range(min(max_pages, doc.page_count)):
        lines = [_c(x) for x in doc[pi].get_text().split("\n")]
        lines = [x for x in lines if x and not NOT_LABEL.match(x)]
        i = 0
        while i < len(lines) - 1:
            cur, nxt = lines[i], lines[i + 1]
            if SECTION.match(cur):
                section = cur
                i += 1
                continue
            # 라벨은 숫자로 시작하지 않고, 값 줄은 값처럼 보여야 한다
            if (not VALUEISH.match(cur) and VALUEISH.search(nxt)
                    and 2 < len(cur) < 60 and len(nxt) < 60):
                mu = UNIT_TAIL.search(nxt)
                out.append({"section": section, "label": cur, "value": nxt,
                            "unit": mu.group(2) if mu else "", "page": pi + 1})
                i += 2
                continue
            i += 1
    # 같은 항목이 여러 쪽에 되풀이되면 처음 것만
    seen, uniq = set(), []
    for r in out:
        k = (r["label"], r["value"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


# 값 맨 앞의 수치에 붙은 단위만 인정한다. 제출자료처럼 값이 문장인 경우
# 문장 아무 데서나 단위를 주우면 엉뚱해진다 — 습도 '5 to 95% RH, 30°C dew point'
# 에서 °C 를 집어 습도의 단위를 온도로 적은 적이 있다.
LEAD_UNIT = re.compile(
    r"^\s*(?:[-–]?\d[\d.,]*)\s*(?:(?:to|~|\.\.\.|[-–])\s*[-–]?\d[\d.,]*\s*)?"
    r"(VDC|VAC|kW|W|VA|V|A|mA|Hz|°C|℃|°F|%|kg|lb|mm|in|dBm|dBA?|rpm|Mbps|bps)\b",
    re.I)


def lead_unit(val):
    m = LEAD_UNIT.match(val or "")
    return m.group(1) if m else ""


def extract_labeled(pdf, max_pages=6):
    """2열 '항목 | 값' 사양 표 → [(구역, 항목, 값, 단위)]

    extract_pairs 와 겨루는 게 아니라 서로 다른 문서 형태를 맡는다.
    extract_pairs 는 줄 순서로 읽어 '항목 다음 줄이 값' 인 문서를 처리한다.
    그런데 조판이 표로 되어 있으면 원문 텍스트 순서가 뒤섞인다 — JCI 제출자료는
    항목 덩어리와 값 덩어리가 따로 나와서 줄 순서로 읽으면 엉뚱하게 짝지어진다.
    표 인식으로는 정확히 잡히므로 그쪽을 쓴다.

    표 규칙
      · 값 칸이 빈 첫 행 = 구역 제목 ('VRF Smart Gateway Specifications')
      · 항목 칸이 빈 행  = 앞 항목의 값이 이어지는 줄
    """
    import fitz
    doc = fitz.open(pdf)
    out = []
    for pi in range(min(max_pages, doc.page_count)):
        pg = doc[pi]
        try:
            tabs = pg.find_tables()
        except Exception:
            continue
        for t in tabs.tables:
            data = t.extract()
            if not data or len(data[0]) != 2 or len(data) < 3:
                continue
            section, last = "", None
            for r in data:
                lab, val = _c(r[0]), _c(r[1])
                if lab and not val:
                    section = lab          # 구역 제목
                    continue
                if not lab and val and last is not None:
                    last["value"] += " / " + val   # 값이 이어지는 줄
                    continue
                if not lab or not val:
                    continue
                last = {"section": section, "label": lab, "value": val,
                        "unit": lead_unit(val), "note": "", "page": pi + 1}
                out.append(last)
    seen, uniq = set(), []
    for r in out:
        k = (r["section"], r["label"])
        if k in seen:
            continue
        seen.add(k)
        # 'Note: ...' 은 값이 아니라 값에 붙은 단서다. 값 칸에 남겨 두면 요약 타일이
        # 문장을 통째로 받아 한 글자씩 세로로 늘어진다 — 비고 칸으로 옮긴다.
        m = re.split(r"\s*\bNote:\s*", r["value"], maxsplit=1)
        if len(m) == 2:
            r["value"], r["note"] = m[0].strip(" /"), m[1].strip()
        uniq.append(r)
    return uniq


def labeled_to_spec(rows, source):
    """항목/값 표 → 카탈로그 표시용 [항목, 값, 단위, 조건·비고, 근거]

    4번째 칸은 단서가 있으면 단서, 없으면 표의 구역 제목이다 — 화면은 용어 분류로
    다시 묶으므로 구역 제목보다 단서가 더 쓸모 있다.
    """
    return [[r["label"], r["value"], r["unit"] or "—",
             r["note"] or r["section"] or "—", "%s p%d" % (source, r["page"])]
            for r in rows]


def pairs_to_spec(pairs, source):
    """항목/값 목록 → 카탈로그 표시용 [항목, 값, 단위, 구역, 근거]"""
    return [[p["label"], re.sub(r"\s*%s$" % re.escape(p["unit"]), "", p["value"]).strip()
             if p["unit"] else p["value"], p["unit"] or "—",
             p["section"] or "—", "%s p%d" % (source, p["page"])] for p in pairs]


# ── 표의 성격 ────────────────────────────────────────────────────────────────
# 카탈로그에서 뽑은 표를 전부 '정격 사양'이라 부르면 안 된다. 실제로는 성격이
# 다른 세 가지가 섞여 있다 (실측: 표 1,254개 중 정격은 소수였다).
#   rating 원문 정격 후보 — 전압·전류·능력·효율 후보. 모델군·옵션 표일 수 있어 바로 확정값은 아니다.
#   perf   성능 — 조건을 넣고 찾아보는 표 (온도별 능력, 풍량×정압별 축동력).
#   dim    치수·중량 — 설치용. 계산에는 안 쓴다.
#   etc    부속·참고 — 호환표·배선표·선정표처럼 값은 있지만 바로 계산값은 아니다.
KIND_KO = {"rating": "정격 사양", "perf": "성능표 (조건별 조회)",
           "dim": "치수·중량", "etc": "기타"}
KIND_ORDER = ["rating", "perf", "dim", "etc"]

PERF_WORD = re.compile(
    r"fan performance|\bbhp\b|static pressure|외부\s*정압|"
    r"(gross|net|total|cooling|heating)\s+capacit|capacit\w* (at|vs)|"
    r"performance data|part load|ipl[vc]\b|throw distance|pressure drop|"
    r"성능표|조건별\s*조회|coil capacity|air temperature rise", re.I)
DIM_WORD = re.compile(
    r"dimension|weight|clearance|shipping|rigging|center of gravity|"
    r"roof curb|service clearance|connection drawing|suction lines?|liquid lines?|"
    r"\bfigure\b|치수|중량|외형", re.I)
RATING_WORD = re.compile(
    r"general data|mains supply|ratings?\b|electrical data|nominal|정격", re.I)
# 정격처럼 보이는 단위가 있어도 쓰임새가 다른 표. 다른 설비에도 같은 원칙을 적용한다:
# "바로 계산하는 기본값"이 아니라 "무엇과 맞는가/어떻게 연결하는가"이면 참고다.
REFERENCE_WORD = re.compile(
    r"accessor(y|ies)|used with|unit wiring|wiring diagram|field supplied|"
    r"single point connection|control stages?|fuse|circuit breaker|"
    r"plenum|grille|isolator|subbase|compatib|selection table|"
    r"\bcabinet\b|features?|benefits?|배선|차단기|퓨즈|호환|부속|액세서리|선정표", re.I)
# 시뮬레이터가 쓰는 물리량 — 이게 있으면 치수 낱말이 섞여 있어도 정격 표다
RATING_Q = {"power", "current", "voltage", "capacity", "efficiency", "airflow"}


def table_kind(t):
    """사양 표 하나의 성격. 제목 낱말만 보지 않고 표 구조도 본다."""
    qs = [x for x in (t.get("quantities") or []) if x]
    txt = "%s %s" % (t.get("title") or "", " ".join(str(h) for h in t["header"]))
    if PERF_WORD.search(txt):
        return "perf"
    if REFERENCE_WORD.search(txt):
        return "etc"
    # 조회 격자 — 같은 물리량 열이 넷 이상 되풀이되면 '조건을 바꿔 가며 읽는 표'다.
    # 열이 형번인 전치 표(orientation='row')는 되풀이가 정상이므로 제외한다.
    if t.get("orientation") == "column" and qs:
        top, n = collections.Counter(qs).most_common(1)[0]
        if n >= 4 and len(set(qs)) <= 2:
            return "perf"
    if DIM_WORD.search(txt) or (qs and set(qs) <= {"dimension", "weight"}):
        return "dim"
    if RATING_WORD.search(txt) or (set(qs) & RATING_Q):
        return "rating"
    return "etc"


# 제목 자리에 제목이 아닌 게 들어온 경우 — 표 위쪽 글자를 줍다 보니 치수 값이나
# 각주를 집는다. 실측 예: '93 11/32” (2363)', 'CFM RPM BHP RPM BHP …'
NUMTITLE = re.compile(r'^[\d\s./"”“()\-–,;:×x]+$')


TABLE_NO = re.compile(r"^(table|tabla|tableau|tabelle|표)\s*\d", re.I)


def title_is_junk(title, header):
    ti = (title or "").strip()
    if len(ti) < 4 or NUMTITLE.match(ti):
        return True
    # 문서가 스스로 붙인 표 제목·절 번호는 건드리지 않는다. 열 이름과 낱말이
    # 겹친다는 이유로 'Table 5. General data — 3 to 5 tons' 나
    # '5.2.2 Mains Supply' 까지 갈아치운 적이 있다.
    if TABLE_NO.match(ti) or re.match(r"^\d+(\.\d+)+\s", ti):
        return False
    words = [w.lower() for w in re.findall(r"[A-Za-z가-힣]{2,}", ti)]
    if not words:
        return True
    # 같은 낱말이 세 번 이상 되풀이되면 제목이 아니라 열 이름을 늘어놓은 것이다
    # ('CFM RPM BHP RPM BHP RPM BHP …')
    if collections.Counter(words).most_common(1)[0][1] >= 3:
        return True
    # 긴 제목인데 전부 열 이름이면 머리글을 주운 것이다
    hwords = set(w for h in header for w in str(h).lower().split())
    return len(ti) > 30 and all(w in hwords for w in words)


def fix_title(t):
    """제목이 제목이 아니면 표의 성격과 쪽으로 대신 짓는다. 지어내지 않는다 —
    '무슨 표인지'는 성격에서, '어디서 왔는지'는 쪽 번호에서 온다."""
    if not title_is_junk(t.get("title"), t["header"]):
        return t.get("title")
    return "%s — %s p%s" % (KIND_KO[t.get("kind") or table_kind(t)],
                            t.get("source") or "원문", t.get("page"))


def digest(tables):
    """표에서 물리량이 붙은 열만 골라 요약 — 무엇을 확보했는지 한눈에 본다."""
    got = {}
    for t in tables:
        for q in t["quantities"]:
            if q:
                got[q] = got.get(q, 0) + 1
    return got


def main(argv):
    if "--scan" in argv:
        files = sorted(glob.glob(os.path.join(RAW, "*.pdf")) +
                       glob.glob(os.path.join(RAW, "*.PDF")))
        print("%-52s %5s %6s  %s" % ("문서", "표", "행", "확보한 물리량"))
        print("─" * 96)
        for f in files:
            try:
                ts = extract_specs(f)
            except Exception as e:
                print("%-52s  실패 %s" % (os.path.basename(f)[:52], str(e)[:30]))
                continue
            if not ts:
                continue
            d = digest(ts)
            print("%-52s %5d %6d  %s"
                  % (os.path.basename(f)[:52], len(ts), sum(len(t["rows"]) for t in ts),
                     ", ".join("%s×%d" % kv for kv in sorted(d.items(), key=lambda x: -x[1])[:8])))
        return 0

    if "--apply" in argv:
        # 사양 문서 ↔ 모델 연결표를 읽어 한꺼번에 붙인다.
        # 카탈로그 하나가 여러 모델(형번 계열)을 덮으므로 1:N 이다.
        mp = json.load(open(os.path.join(DATA, "spec-map.json"), encoding="utf-8"))
        # --only 로 문서를 골라 돌린다. 전체 재적용은 대형 카탈로그 때문에 오래 걸려
        # 새로 넣은 것만 확인하고 싶을 때가 많다.
        only = argv[argv.index("--only") + 1].lower() if "--only" in argv else None
        done = 0
        for fname, mids in mp.items():
            if fname.startswith("_"):
                continue
            if only and only not in fname.lower():
                continue
            path = os.path.join(RAW, fname)
            if not os.path.exists(path):
                print("  · %s 없음" % fname)
                continue
            ts = extract_specs(path)
            if not ts:
                print("  · %-44s 사양 표 없음" % fname[:44])
                continue
            for mid in mids:
                mpath = os.path.join(DATA, "models", mid + ".json")
                if not os.path.exists(mpath):
                    print("  ⚠ 모델 없음: %s" % mid)
                    continue
                m = json.load(open(mpath, encoding="utf-8"))
                keep = [t for t in m.get("specTables", []) if t.get("source") != fname]
                m["specTables"] = keep + [dict(t, source=fname) for t in ts]
                m["has"] = dict(m.get("has", {}), spec=True)
                json.dump(m, open(mpath, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                done += 1
            print("%-46s 표 %2d · 행 %4d → 모델 %d건  %s"
                  % (fname[:46], len(ts), sum(len(t["rows"]) for t in ts), len(mids),
                     ", ".join(sorted({q for t in ts for q in t["quantities"] if q}))[:44]))
        print("\n사양 적용 %d건" % done)
        return 0

    if "--variant" in argv:
        # 데이터시트는 **형번 하나**를 다룬다. 통신 맵은 제품군 단위라 층이 다르다 —
        # 제품군 모델 아래 형번 목록으로 붙인다. 사용자가 제품군을 고르고 형번을 고르면
        # 그 형번의 정격이 나온다.
        i = argv.index("--variant")
        fam, fname = argv[i + 1], argv[i + 2]
        path = os.path.join(DATA, "models", fam + ".json")
        m = json.load(open(path, encoding="utf-8"))
        pairs = extract_pairs(os.path.join(RAW, fname))
        if not pairs:
            print("  · %s — 항목/값을 못 찾았다" % fname)
            return 1
        # 형번은 파일 이름에서 딴다 (belimo_LMB24-3-T_datasheet_en-us.pdf → LMB24-3-T)
        mm = re.search(r"_([A-Z0-9][\w.-]*?)_datasheet", fname)
        code = mm.group(1) if mm else os.path.splitext(fname)[0]
        vs = [v for v in m.get("variants", []) if v["code"] != code]
        vs.append({"code": code, "source": fname,
                   "spec": pairs_to_spec(pairs, fname)})
        m["variants"] = sorted(vs, key=lambda v: v["code"])
        m["has"] = dict(m.get("has", {}), spec=True)
        json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        key = [p for p in pairs if re.search(r"power|voltage|torque|current", p["label"], re.I)]
        print("%-38s ← %-14s 항목 %d개 (전기·구동 %d)"
              % (fam[:38], code, len(pairs), len(key)))
        return 0

    # 이미 붙여 둔 사양 표에 성격(kind)을 매기고, 제목이 아닌 제목을 고쳐 준다.
    # 다시 추출하지 않는다 — 표 내용은 그대로고 분류만 얹는다.
    if "--kinds" in argv:
        import collections as _c
        tally, fixed = _c.Counter(), 0
        for path in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
            m = json.load(open(path, encoding="utf-8"))
            ts = m.get("specTables") or []
            if not ts:
                continue
            for t in ts:
                # 앞서 고친 제목이 있으면 원문으로 되돌린 뒤 다시 판정한다 —
                # 판정 규칙을 고쳤을 때 되풀이해 돌릴 수 있어야 한다.
                if t.get("titleRaw") is not None:
                    t["title"] = t.pop("titleRaw")
                t["kind"] = table_kind(t)
                tally[t["kind"]] += 1
                new = fix_title(t)
                if new != t.get("title"):
                    t["titleRaw"] = t.get("title")
                    t["title"] = new
                    fixed += 1
            json.dump(m, open(path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        print("사양 표 %d개 분류 · 제목 %d개 고침" % (sum(tally.values()), fixed))
        for k in KIND_ORDER:
            print("  %-18s %d개" % (KIND_KO[k], tally[k]))
        return 0

    # 2열 '항목 | 값' 사양 표를 모델의 spec 에 넣는다 (형번이 하나인 장치용).
    # 항목 이름은 원문 영문 그대로 둔다 — 한글·설명·시뮬레이터 중요도는
    # 카탈로그가 용어 사전(spec-terms.json)으로 붙여 주므로 여기서 번역하지 않는다.
    if "--label" in argv:
        i = argv.index("--label")
        mid, fname = argv[i + 1], argv[i + 2]
        path = os.path.join(DATA, "models", mid + ".json")
        m = json.load(open(path, encoding="utf-8"))
        rows = extract_labeled(os.path.join(RAW, fname))
        if not rows:
            print("  · %s — 2열 사양 표를 못 찾았다" % fname)
            return 1
        m["spec"] = labeled_to_spec(rows, fname)
        m["has"] = dict(m.get("has", {}), spec=True)
        json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("%-46s ← %-40s 사양 %d항목" % (mid[:46], fname[:40], len(rows)))
        return 0

    if "--attach" in argv:
        i = argv.index("--attach")
        mid, fname = argv[i + 1], argv[i + 2]
        path = os.path.join(DATA, "models", mid + ".json")
        m = json.load(open(path, encoding="utf-8"))
        ts = extract_specs(os.path.join(RAW, fname))
        m["specTables"] = [dict(t, source=fname) for t in ts]
        m["has"] = dict(m.get("has", {}), spec=bool(ts))
        json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("%s ← 사양 표 %d개 (%d행) · 물리량 %s"
              % (mid, len(ts), sum(len(t["rows"]) for t in ts), digest(ts)))
        return 0

    pdf = argv[0]
    ts = extract_specs(pdf)
    print("%s — 사양 표 %d개" % (os.path.basename(pdf), len(ts)))
    for t in ts[:6]:
        print("\n■ p%-3d %s" % (t["page"], t["title"][:70]))
        print("   열: %s" % " | ".join("%s%s" % (h[:18], "(" + q + ")" if q else "")
                                      for h, q in zip(t["header"], t["quantities"])))
        for r in t["rows"][:3]:
            print("     %s" % " :: ".join(c[:14] for c in r))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
