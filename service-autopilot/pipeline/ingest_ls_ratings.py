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


def read_page(page):
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
    return [c[0] for c in cols], got


# 원문 라벨(잎)은 또렷한데 바깥 라벨('Rated output' · 'Rated input')은 세로 병합이라
# 좌표로 안 잡힌다. 표 구조가 6쪽 모두 같으므로 **줄 순서로 구간을 가른다** —
# 'Output Voltage' 줄까지가 출력부, 그 뒤가 입력부다. 그래야 같은 이름의
# 'Rated Current (A)' 두 줄이 출력전류와 입력전류로 갈린다(원문 그림으로 확인했다).
# 담을 줄 = **형번마다 값이 다른 것**. 원문에는 전 형번 공통값(출력 주파수 0–400 Hz ·
# 입력 전압 3-Phase 200–240 VAC …)도 있는데, 그건 한 칸으로 병합돼 있어 형번별 값이
# 아니고 전압대(표 제목)로 이미 정해진다. 시뮬레이터가 형번을 골라 쓰는 값만 담는다.
# 그렇게 좁히면 라벨 조각('Three-' · 'Phase')이 전류로 오인되는 문제도 함께 사라진다.
NUM = re.compile(r"^-?[\d.,]+$")


def classify(label, phase):
    """줄 이름 → 우리 항목. 구간(출력부/입력부)은 줄 순서로 가른다.

    바깥 라벨('Rated output' · 'Rated input')은 세로 병합이라 좌표로 안 잡힌다.
    원문 그림으로 확인한 순서가 늘 같다 — 'Output Voltage' 줄 뒤가 입력부다.
    """
    l = re.sub(r"\s+", " ", (label or "")).strip().lower()
    if not l:
        return None, phase
    if "output voltage" in l:
        return None, "input"                 # 여기서부터 입력부
    if "applied" in l or l in ("hp", "kw"):
        return ("적용 전동기 (HP)" if "hp" in l else "적용 전동기 (kW)"), phase
    if "rated capacity" in l:
        return "정격 용량 (kVA)", phase
    if "weight" in l:
        return "중량 (kg)", phase
    # 라벨이 'Rated Three-Phase' 로 붙어 나오기도 한다(병합 칸이 좌우로 섞인다).
    # 'rated current' 만 보다가 400 V 30–90 kW 의 3상 출력전류 한 줄을 놓쳤다.
    if ("rated current" in l or "three-phase" in l or "single-phase" in l
            or l.startswith(("three-", "single-")) or l == "phase"):
        if phase != "output":
            return "정격 입력전류 (A)", phase
        kind = "3상" if "three" in l else ("단상" if "single" in l else "")
        return ("정격 출력전류 (A) %s" % kind).strip(), phase
    return None, phase


def build(doc):
    out = []
    for pg in PAGES:
        if pg > doc.page_count:
            continue
        page = doc[pg - 1]
        codes, rows = read_page(page)
        if not codes:
            continue
        title = ""
        for r in rows_of(page)[:6]:
            t = " ".join(w[4] for w in r)
            if re.search(r"Three\s*Phase|Single\s*Phase", t):
                title = re.sub(r"^Technical Specification\s*\d*\s*", "", t).strip()
                break
        keep, phase, seen = [], "output", set()
        for label, vals in rows:
            ko, phase = classify(label, phase)
            if not ko:
                continue
            # **형번마다 값이 다른 줄만** 담는다 — 숫자 값이 두 칸 이상이어야 한다.
            # 공통값(병합 칸)은 첫 칸에만 들어오므로 여기서 자연히 걸러진다.
            if sum(1 for v in vals if NUM.match((v or "").strip())) < 2:
                continue
            name, i = ko, 2
            while name in seen:
                name, i = "%s #%d" % (ko, i), i + 1
            seen.add(name)
            keep.append([name] + vals)
        if keep:
            out.append({"title": "형번별 정격 — %s" % (title or "H100"),
                        "page": pg, "orientation": "column",
                        "header": ["항목"] + codes,
                        "quantities": [None] * (len(codes) + 1),
                        "rows": keep, "kind": "rating"})
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
