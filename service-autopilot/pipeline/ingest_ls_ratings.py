# -*- coding: utf-8 -*-
"""LS ELECTRIC H100 — 형번별 정격 취입 (본체 매뉴얼 11.1 Input and Output Specifications).

  PYTHONIOENCODING=utf-8 python ingest_ls_ratings.py          바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_ls_ratings.py --run    실제로 기록한다

왜 전용으로 읽나
  일반 사양 추출기(specs.py)를 매뉴얼 633쪽에 통째로 돌렸더니 표 130개 · 2,153행이
  들어왔는데 **대부분 정격이 아니었다** — 설정표·배선표·비고까지 딸려 왔다.
  사용자가 "정격이랑 상관도 없는 내용이 다 들어가 있다" 고 짚었고 맞는 말이다.
  규칙 0(요구 항목을 먼저 정하고 문서를 연다)을 어긴 것이다.

  그래서 **시뮬레이터가 쓰는 것만** 가져온다. 인버터에서 그것은 —
    형번 · 적용 전동기(kW·HP) · 정격 용량(kVA) · 정격 출력전류(A) ·
    입력 전압·주파수 · 출력 주파수
  나머지(치수·단자 나사 토크·퓨즈·제동저항)는 계산에 안 쓰므로 담지 않는다.

원문 구조 (PDF 574~579쪽, 전압·용량대별 6표)
  가로가 형번(0008 · 0015 …), 세로가 항목이다. 항목 이름은 **세로로 병합된 칸**이라
  ('Applied Motor' 하나가 HP 행과 kW 행을 함께 덮는다) 표 인식 결과만 보면 라벨이
  흩어진다. 그래서 낱말 좌표로 읽고, 라벨은 그 행에 걸친 왼쪽 글자를 모아 만든다.
"""
import io
import json
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)

MODEL_ID = "ls-electric-h100-vfd"
DOC = "LS_H100_UserManual_EN_190621.pdf"
PAGES = range(574, 580)

# 담을 항목 — 시뮬레이터가 전력·발열을 계산하는 데 쓰는 것만.
# 원문 라벨의 일부만 맞아도 잡는다(줄바꿈·병합으로 조각나기 때문).
WANT = [
    ("적용 전동기", r"applied\s*motor"),
    ("정격 용량", r"rated\s*capacity"),
    ("정격 출력전류", r"rated\s*current|rated\s*output\s*current"),
    ("출력 주파수", r"output\s*frequency"),
    ("입력 전압", r"working\s*voltage|input\s*voltage|voltage\s*\(v\)"),
    ("입력 주파수", r"input\s*frequency|frequency\s*\(hz\)"),
    ("중량", r"\bweight\b"),
]
MODEL_ROW = re.compile(r"model\s*h100", re.I)
CODE = re.compile(r"^\d{4}$")


def rows_of(page):
    """낱말을 줄로 묶는다 — y 가 가까우면 같은 줄."""
    ws = page.get_text("words")          # (x0,y0,x1,y1,word,block,line,no)
    band = collections.defaultdict(list)
    for w in ws:
        band[round(w[1] / 4)].append(w)
    out = []
    for k in sorted(band):
        out.append(sorted(band[k], key=lambda w: w[0]))
    # 같은 줄이 두 밴드로 갈리면 붙인다
    merged = []
    for r in out:
        if merged and abs(r[0][1] - merged[-1][0][1]) < 5:
            merged[-1] = sorted(merged[-1] + r, key=lambda w: w[0])
        else:
            merged.append(r)
    return merged


def rows_of(page):
    """낱말을 줄로 묶는다 — y 가 가까우면 같은 줄."""
    ws = page.get_text("words")          # (x0,y0,x1,y1,word,block,line,no)
    band = collections.defaultdict(list)
    for w in ws:
        band[round(w[1] / 4)].append(w)
    out = []
    for k in sorted(band):
        out.append(sorted(band[k], key=lambda w: w[0]))
    # 같은 줄이 두 밴드로 갈리면 붙인다
    merged = []
    for r in out:
        if merged and abs(r[0][1] - merged[-1][0][1]) < 5:
            merged[-1] = sorted(merged[-1] + r, key=lambda w: w[0])
        else:
            merged.append(r)
    return merged


def read_page_words(page):
    """한 쪽 → (형번 목록, [(항목, [값…])])

    라벨이 **3단 계층**이다 — 'Rated output › Rated Current (A) › Single-Phase'.
    가운데·오른쪽 칸은 세로로 병합돼 빈 줄이 생기므로 위에서 이어받는다.
    값이 전 형번 공통이면 원문이 한 칸으로 병합해 둔다('0–400 Hz') — 그런 줄은
    열마다 쪼개지 말고 문장 하나로 되돌린다. 쪼개 두면 'Hz' 만 든 칸이 생긴다.
    """
    rows = rows_of(page)
    head = None
    for r in rows:
        if MODEL_ROW.search(" ".join(w[4] for w in r)):
            head = r
            break
    if head is None:
        return None, []
    cols = [(w[4], (w[0] + w[2]) / 2) for w in head if CODE.match(w[4])]
    if len(cols) < 2:
        return None, []
    left = min(c[1] for c in cols) - 14
    gaps = [b[1] - a[1] for a, b in zip(cols, cols[1:])]
    win = (min(gaps) / 2.0 - 1) if gaps else 26

    # 라벨 영역의 세로 칸(밴드) 경계 — 왼쪽 글자들의 x 를 모아 무리 짓는다
    xs = sorted({round(w[0]) for r in rows for w in r
                 if (w[0] + w[2]) / 2 < left and w[4].strip()})
    bands, cur = [], []
    for x in xs:
        if cur and x - cur[-1] > 18:
            bands.append(cur[0])
            cur = []
        cur.append(x)
    if cur:
        bands.append(cur[0])
    bands = bands[:3] or [0]

    def band_of(w):
        cx = w[0]
        i = 0
        for j, bx in enumerate(bands):
            if cx >= bx - 4:
                i = j
        return i

    carry = [""] * len(bands)
    got = []
    for r in rows:
        if r is head:
            continue
        cells = [""] * len(bands)
        for w in r:
            if (w[0] + w[2]) / 2 < left and w[4].strip():
                i = band_of(w)
                cells[i] = (cells[i] + " " + w[4]).strip()
        right = [w for w in r if (w[0] + w[2]) / 2 >= left and w[4].strip()]
        if not right:
            # 값 없는 줄 = 라벨만 있는 줄. 이어받을 값으로 둔다
            for i, c in enumerate(cells):
                if c:
                    carry[i] = c
                    carry[i + 1:] = [""] * (len(carry) - i - 1)
            continue
        for i, c in enumerate(cells):
            if c:
                carry[i] = c
                carry[i + 1:] = [""] * (len(carry) - i - 1)
        parts, seen = [], set()
        for c in carry:
            c = c.strip()
            if c and c not in seen:
                seen.add(c)
                parts.append(c)
        label = " › ".join(parts)

        vals = []
        for _code, cx in cols:
            # 창을 열 간격의 절반으로 잡는다. 고정폭(26pt)으로 두었더니 열이 좁은
            # 쪽(400 V 5.5–22 kW)에서 이웃 값이 함께 잡혀 '5.5 7.5' 처럼 번졌다.
            hit = [w[4] for w in right if abs((w[0] + w[2]) / 2 - cx) < win]
            vals.append(" ".join(hit).strip())
        filled = [v for v in vals if v]
        # 글자가 섞여 있으면 원문이 한 칸으로 병합한 **공통값**이다 — 문장으로 되돌린다
        if len(filled) >= 2 and any(re.search(r"[A-Za-z]", v) for v in filled):
            vals = [" ".join(w[4] for w in sorted(right, key=lambda w: w[0]))]                    + [""] * (len(cols) - 1)
        got.append((label, vals))
    pat = re.search(r"Model\s+(H100)\s*X+\s*[–-]\s*(\d)",
                    " ".join(w[4] for w in head), re.I)
    codes = ["%s%s-%s" % (c[0], pat.group(1).upper(), pat.group(2)) for c in cols]         if pat else [c[0] for c in cols]
    return codes, got


# 원문 라벨(잎)은 또렷한데 바깥 라벨('Rated output' · 'Rated input')은 세로 병합이라
# 좌표로 안 잡힌다. 표 구조가 6쪽 모두 같으므로 **줄 순서로 구간을 가른다** —
# 'Output Voltage' 줄까지가 출력부, 그 뒤가 입력부다. 그래야 같은 이름의
# 'Rated Current (A)' 두 줄이 출력전류와 입력전류로 갈린다(원문 그림으로 확인했다).
def _c(x):
    """셀 글자 다듬기. ± 는 심볼 글꼴이라  로 나온다 — 되돌린다."""
    t = (x or "").replace("", "±").replace("", "°")
    return re.sub(r"\s+", " ", t).strip()


def read_page_table(page):
    """한 쪽 → (형번 목록, [(라벨, [값…])])

    ★ 값은 **표 인식**에서 가져온다. 낱말 좌표로 읽었더니 원문이 한 칸으로 병합해 둔
      값이 조각났다('60' 과 'Hz(±5%)' 가 따로). 표 인식은 병합 칸을 통째로 준다.
      라벨은 반대로 표 인식에서도 흩어지지만(3단 세로 병합), 구간·항목 판정은
      **값 자체**를 근거로 하므로(‘VAC’ → 입력 전압, ‘3-Phase’ → 3상) 문제가 없다.
    """
    tabs = page.find_tables().tables
    if not tabs:
        return None, []
    data = [[_c(c) for c in r] for r in max(tabs, key=lambda t: len(t.extract())).extract()]
    hi = next((i for i, r in enumerate(data)
               if any(MODEL_ROW.search(c) for c in r)), None)
    if hi is None:
        return None, []
    head = data[hi]
    idx = [j for j, c in enumerate(head) if CODE.match(c)]
    if len(idx) < 2:
        return None, []
    # 원문 머리글이 형번 규칙을 준다 — 'Model H100 XXXX–2' 의 XXXX 자리가 열 코드다.
    # 치수 표(p587)가 '0008H100-4' 로 적으므로 그 표기로 맞춘다. 코드만 담으면
    # 형번 사다리가 '0008' 을 형번으로 못 알아본다(숫자뿐이라).
    pat = re.search(r"Model\s+(H100)\s*X+\s*[–-]\s*(\d)", " ".join(head), re.I)
    if pat:
        codes = ["%s%s-%s" % (head[j], pat.group(1).upper(), pat.group(2)) for j in idx]
    else:
        codes = [head[j] for j in idx]
    lab_cols = [j for j in range(len(head)) if j < min(idx)]

    out = []
    for r in data[hi + 1:]:
        label = " ".join(r[j] for j in lab_cols if j < len(r) and r[j]).strip()
        vals = [r[j] if j < len(r) else "" for j in idx]
        if not any(vals):
            # 병합 칸이 형번 열 **밖**에 놓이는 쪽이 있다(400 V 5.5–22 kW).
            # 코드 열이 다 비었으면 라벨 오른쪽 전체에서 글자 든 칸 하나를 찾는다.
            tail = [c for c in r[min(idx):] if c and re.search(r"[A-Za-z]", c)]
            if len(tail) == 1:
                vals = [tail[0]] + [""] * (len(idx) - 1)
        if not label and not any(vals):
            continue
        out.append((label, vals))
    return codes, out


# 항목 이름은 **`한글 (원문 영문)`** 한 가지로 통일한다. 우리가 이름을 붙이는 자리는
# 여기뿐이다 — 다른 모델의 정격은 원문 표를 그대로 담으므로 원문 이름이 남는다(규칙 1).
#
# ⚠ 한 번 잘못 좁혔다. '형번마다 값이 다른 줄만' 담았더니 출력 주파수·출력 전압과
#   입력부(Working Voltage · Input Frequency)가 통째로 빠졌다. 그것들은 원문에서
#   **모든 형번을 덮는 병합 칸**이라 값이 한 칸에만 들어 있었을 뿐, 없는 값이 아니다.
#   병합 칸은 전 형번에 해당하므로 모든 열에 같은 값을 채운다(원문의 뜻 그대로다).
NUM = re.compile(r"^-?[\d.,]+$")

# 원문 순서 그대로. (한글, 원문, 구간, 상/하 구분)
# 물리량(quantity)은 사전(units)이 아는 이름으로 적는다 — 빈칸으로 두면
# units.py --sync 가 무엇을 담는 값인지 몰라 확정본을 못 만든다.
QTY = ["power", "power", "capacity", "current", "current", "frequency", "voltage",
       "voltage", "voltage", "frequency", "frequency", "current", "weight"]

ITEMS = [
    ("적용 전동기", "Applied Motor", "HP"),
    ("적용 전동기", "Applied Motor", "kW"),
    ("정격 용량", "Rated Capacity", "kVA"),
    ("정격 출력전류", "Rated Current", "A, 3상"),
    ("정격 출력전류", "Rated Current", "A, 단상"),
    ("출력 주파수", "Output Frequency", ""),
    ("출력 전압", "Output Voltage", "V"),
    ("입력 전압", "Working Voltage", "V, 3상"),
    ("입력 전압", "Working Voltage", "V, 단상"),
    ("입력 주파수", "Input Frequency", "3상"),
    ("입력 주파수", "Input Frequency", "단상"),
    ("정격 입력전류", "Rated Current", "A"),
    ("중량", "Weight", "kg"),
]


def name_of(i):
    """항목 이름 형식 — **`한글 [구분] · 원문영문 (단위)`** 하나로 통일한다.

    ⚠ 괄호 안에는 **단위만** 둔다. 처음에 '(Applied Motor, kW)' 로 적었더니
      확정본 동기화가 괄호를 통째로 단위로 읽어 'Applied Motor, kW' 가 단위가 됐다
      (datasets.label_unit 은 괄호 안을 단위로 본다).
    """
    ko, en, unit = ITEMS[i]
    kind = ""
    if unit and ("상" in unit):
        parts = [x.strip() for x in unit.split(",")]
        kind = " " + parts[-1]
        unit = parts[0] if parts[0] not in ("3상", "단상") else ""
    head = "%s%s · %s" % (ko, kind, en)
    return "%s (%s)" % (head, unit) if unit else head


def classify(label, vals, phase):
    """줄 → (항목 번호, 구간). 원문 라벨 조각과 **값 자체**를 함께 본다.

    바깥 라벨('Rated output' · 'Rated input')은 세로 병합이라 좌표로 안 잡히고,
    잎 라벨도 'Rated Three-Phase' 처럼 붙어 나온다. 그래서 값도 근거로 쓴다 —
    입력 전압 줄의 값이 '3-Phase 200–240 VAC …' · '1-Phase 240 VAC …' 라 상 구분이
    값 안에 적혀 있다(원문 그림으로 확인).
    """
    l = re.sub(r"\s+", " ", (label or "")).strip().lower()
    v = " ".join(x for x in vals if x).strip()
    vl = v.lower()
    if not l and not v:
        return None, phase
    if l.startswith("•") or "technical specification" in l or l.startswith("model"):
        return None, phase
    if "applied" in l or l in ("hp", "kw"):
        return (0 if "hp" in l else 1), phase
    if "rated capacity" in l:
        return 2, phase
    if "output frequency" in l:
        return 5, phase
    if "output voltage" in l:
        return 6, "input"                       # 이 줄까지가 출력부다
    if "working voltage" in l or (phase == "input" and "vac" in vl):
        return (7 if "3-phase" in vl or "three" in l else 8), "input"
    if phase == "input" and "hz" in vl:
        return (9 if "50" in vl or "three" in l else 10), phase
    if ("rated current" in l or "three-phase" in l or "single-phase" in l
            or l.startswith(("three-", "single-")) or l == "phase"):
        if phase == "input":
            return 11, phase
        return (3 if "three" in l else 4), phase
    if "weight" in l:
        return 12, phase
    return None, phase


def collect(rows, codes, got, prefer_merged):
    """분류해 담는다. prefer_merged 면 병합 칸(문장) 값만, 아니면 숫자 값만 담는다."""
    phase = "output"
    for label, vals in rows:
        i, phase = classify(label, vals, phase)
        if i is None:
            continue
        filled = [v for v in vals if (v or "").strip()]
        if not filled:
            continue
        nums = sum(1 for v in vals if NUM.match((v or "").strip()))
        if prefer_merged:
            # 원문이 전 형번을 덮는 병합 칸 — 모든 열이 같은 값이다
            if len(filled) == 1 and re.search(r"[A-Za-z]", filled[0]) and nums == 0:
                got.setdefault(i, [filled[0]] * len(codes))
        elif nums >= 2:
            got.setdefault(i, list(vals))
    return got


def build(doc):
    """두 경로를 합친다.

    ⚠ 한 경로로는 안 된다 — 실측으로 확인했다.
      · 낱말 좌표: 숫자 열은 정확한데 병합 칸이 조각난다('60' 과 'Hz(±5%)' 가 따로).
      · 표 인식  : 병합 칸은 통째로 주는데 쪽에 따라 행을 잃는다(400 V 30–90 kW 는
                   13항목 중 7개만 나왔다).
      그래서 숫자는 낱말에서, 병합 칸은 표 인식에서 가져와 항목 번호로 합친다.
    """
    out = []
    for pg in PAGES:
        if pg > doc.page_count:
            continue
        page = doc[pg - 1]
        codes_w, rows_w = read_page_words(page)
        codes_t, rows_t = read_page_table(page)
        codes = codes_w or codes_t
        if not codes:
            continue
        got = {}
        if codes_w and len(codes_w) == len(codes):
            collect(rows_w, codes, got, prefer_merged=False)
        if codes_t and len(codes_t) == len(codes):
            collect(rows_t, codes, got, prefer_merged=True)
            collect(rows_t, codes, got, prefer_merged=False)
        # 표 인식이 병합 칸을 통째로 잃는 쪽이 있다(400 V 5.5–22 kW 는 여섯 줄이 빈다).
        # 그럴 때만 낱말 경로의 병합 값을 쓴다 — 그쪽은 ± 가 빠지고 조각날 수 있어
        # 우선순위를 뒤에 둔다.
        if codes_w and len(codes_w) == len(codes):
            collect(rows_w, codes, got, prefer_merged=True)
        title = ""
        for r in rows_of(page)[:6]:
            t = " ".join(w[4] for w in r)
            if re.search(r"Three\s*Phase|Single\s*Phase", t):
                title = re.sub(r"^Technical Specification\s*\d*\s*", "", t).strip()
                break
        keep = [[name_of(i)] + got[i] for i in sorted(got)]
        if keep:
            out.append({"title": "형번별 정격 — %s" % (title or "H100"),
                        # 세로가 항목, 가로가 형번이다 — 물리량은 **줄**에 붙는다
                        "page": pg, "orientation": "row",
                        "header": ["항목"] + codes,
                        "quantities": [QTY[i] for i in sorted(got)],
                        "rows": keep, "kind": "rating",
                        "note": "원문이 전 형번을 덮는 병합 칸으로 적은 값(출력 주파수·"
                                "전압·입력 전압·주파수)은 모든 형번 열에 같은 값으로 폈다."})
    return out


def main(argv):
    import fitz
    run = "--run" in argv
    doc = fitz.open(os.path.join(DATA, "raw", DOC))
    tabs = build(doc)
    n = sum(len(t["rows"]) for t in tabs)
    print("형번별 정격 표 %d개 · %d행" % (len(tabs), n))
    for t in tabs:
        print("  p%-4d %-46s 형번 %2d · 항목 %d"
              % (t["page"], t["title"][:46], len(t["header"]) - 1, len(t["rows"])))
        for r in t["rows"]:
            print("       %-22s %s" % (r[0][:22], " · ".join(x or "—" for x in r[1:])[:78]))

    mp = os.path.join(DATA, "models", MODEL_ID + ".json")
    m = json.load(io.open(mp, encoding="utf-8"))
    before = len(m.get("specTables") or [])
    # 이 문서에서 온 것은 **전부 걷어내고** 정격만 다시 넣는다.
    keep = [t for t in (m.get("specTables") or []) if t.get("source") != DOC]
    m["specTables"] = keep + [dict(t, source=DOC) for t in tabs]
    m["has"] = dict(m.get("has") or {}, spec=bool(m["specTables"]))
    print("\n사양 표 %d개 → %d개 (이 문서에서 온 것만 갈아 끼운다)"
          % (before, len(m["specTables"])))
    if not run:
        print("(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("→ %s" % os.path.relpath(mp, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
