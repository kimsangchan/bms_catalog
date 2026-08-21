# -*- coding: utf-8 -*-
"""JCI Roomtop RTC/RTH 기술 가이드 → 정격 사양 표.

왜 벤더 파서인가
  이 저장소의 JCI 문서는 전부 BAS 포인트/IOM 이라 **정격이 한 건도 없었다**
  (제품 39건 전부 0 — 시뮬레이터가 못 쓴다). 냉동기 포털의 '안 가져온 것'을
  전수로 열어 보다 찾은 유일한 정격 문서가 이 둘이다(K판·L판). 같은 제품을
  YKN2Open 게이트웨이가 BAS 로 내보내므로 **짝이 맞는다**.

  일반 추출기(specs.extract_specs)도 표는 잡지만 **열 정렬이 깨진다** —
  find_tables 가 그은 칸이 모델 두 개를 한 칸에 넣어(`'4.7 5.2'`) RTH-15K 의
  값에 RTH-20K 값이 딸려 들어온다. 정격이 한 칸만 밀려도 시뮬레이터는 그대로
  믿으므로, 칸이 아니라 **모델 머리글의 x 좌표**로 값을 배정한다.

이 문서에서 실제로 밟은 함정
  1. **임베드 폰트의 ToUnicode 가 1 밀려 있다.** `Gen_*` 폰트로 찍힌 글자는
     한 칸씩 높게 나온다 — 'MPT DPNQPOFOUFT' 는 실제 'LOS COMPONENTES' 이고
     숫자도 밀린다('348' → 실제 '237'). 문서 스팬의 40% 가 이 폰트다.
     ⚠ **정격 표는 깨끗한 Helvetica 라 무사하다** — 밀린 것은 도면·배선도
     라벨뿐이다(2026-08-21 전수 확인). 그래도 파서가 폰트로 갈라 되돌린다.
     되돌리지 않으면 표 제목·단위가 깨진 채 화면에 나간다.
  2. **제목은 스페인어인데 본문은 영문이다.** 포털 제목만 보고 '번역본'으로
     분류하면 정격이 통째로 사라진다 — 실제로 그럴 뻔했다.
  3. **한 칸이 두 줄인 행이 있다.** 'Power supply' 는 첫 모델만 라벨 줄에 있고
     나머지는 아래 두 줄에 230.3.50 / 400.3.50 으로 나뉜다. 라벨 없는 줄을
     앞 행에 이어 붙이지 않으면 5개 모델의 전원이 사라진다.
  4. **원문 오타를 고치지 않는다.** K판 10쪽 실내팬 표의 6 mm WG 소비전력이
     373 W 로 앞뒤(455·480)보다 낮다. 깨끗한 폰트로 그렇게 **적혀 있다** —
     추정으로 고치지 않고 gap 에 적는다.

무엇을 뽑나 (요구 프로파일 e5.rtu 기준)
  Nominal capacities  냉방능력·냉방 소비전력·난방능력·난방 소비전력  ← 핵심 4종
  Test conditions     그 값이 어느 조건에서 잰 것인지 (ratingCondition)
  Physical data       압축기·코일·팬 모터·냉매 충전량·치수·중량
  Nominal air flows   실내/실외 정격 풍량과 이용 가능 정압 (L판만)

실행
  PYTHONIOENCODING=utf-8 python vendor_jci_rth.py --dump     쪽·표만 본다
  PYTHONIOENCODING=utf-8 python vendor_jci_rth.py            모델에 주입 (멱등)
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
sys.path.insert(0, HERE)
import schema as S      # noqa: E402
import specs as SP      # noqa: E402

VENDOR = "Johnson Controls / YORK"
MODEL_NAME = "RTC·RTH Compact Horizontal Heat Pump (Roomtop)"
MID = S.model_id(VENDOR, "RTC-RTH Compact Horizontal Heat Pump Roomtop")

DOCS = [("JCI_RTH-K_TechnicalGuide.pdf", "K"),
        ("JCI_RTH-L_TechnicalGuide.pdf", "L")]

# 'RTH-07K' · 'RTH07L' · 'RTH 30L'
MODEL_CODE = re.compile(r"^RTH\s*-?\s*(\d{2})\s*([KL])$", re.I)
# 값 칸이 시작하는 x — 왼쪽은 그룹 이름·라벨·단위 자리다(실측 라벨 81, 단위 158~185)
VALUE_X = 200.0
# 왼쪽 여백에 세로로 놓인 **묶음 이름**. 진짜 행 라벨과 x 가 1pt 차이라 좌표로는
# 못 가른다 — 두 문서(K·L)에 실제로 나온 낱말만 적는다. 이 묶음이 어느 행을
# 덮는지는 배치가 어긋나 알 수 없어(블록 경계와 y 가 안 맞는다) 쓰지 않고 뗀다.
MARGIN_WORDS = {"Model", "Compressor", "Indoor", "Outdoor", "coil", "fan",
                "motor", "Weight"}


def dec(t):
    """ToUnicode 가 1 밀린 폰트의 글자를 되돌린다 (함정 1).

    공백(0x20)은 그대로 둔다 — 자간 때문에 PyMuPDF 가 끼워 넣은 진짜 공백이라
    한 칸 내리면 0x1F 제어문자가 된다. 원문의 낱말 사이 공백은 '!' 로 찍혀 있어
    이 규칙으로 정확히 공백이 된다.
    """
    return "".join(chr(ord(c) - 1) if ord(c) > 0x20 else c for c in t)


def page_lines(pg):
    """쪽 → {y: [(x0, x1, 글자)]}. Gen_* 폰트는 되돌려서 담는다."""
    out = {}
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                t = s["text"]
                if not t.strip():
                    continue
                if s["font"].startswith("Gen_"):
                    t = dec(t)
                y = round((s["bbox"][1] + s["bbox"][3]) / 2, 1)
                # 줄 높이만큼 흔들리는 y 를 하나로 모은다 — 같은 줄인데 0.3 씩
                # 다른 스팬이 있어 그대로 쓰면 행이 잘게 쪼개진다
                key = next((k for k in out if abs(k - y) <= 2.0), y)
                out.setdefault(key, []).append((s["bbox"][0], s["bbox"][2], t.strip()))
    for k in out:
        out[k].sort()
    return out


def model_columns(lines, with_y=False):
    """모델 머리글 줄 → [(코드, x중심)]. 3개 미만이면 그 쪽엔 없다."""
    best, best_y = [], None
    for y in sorted(lines):
        cols = []
        for x0, x1, t in lines[y]:
            m = MODEL_CODE.match(t.replace(" ", " ").strip())
            if m:
                cols.append(("RTH-%s%s" % (m.group(1), m.group(2).upper()),
                             (x0 + x1) / 2))
        if len(cols) > len(best):
            best, best_y = cols, y
    if len(best) < 3:
        return ([], None) if with_y else []
    return (best, best_y) if with_y else best


def _num(t):
    return bool(re.match(r"^[-+]?[\d.,]+$", t.replace(" ", "")))


def row_label(cells):
    """값 칸 왼쪽 조각들 → 라벨. 단위 칸이 따로 떨어져 있어 함께 붙인다."""
    return re.sub(r"\s{2,}", " ", " ".join(t for _x0, _x1, t in cells)).strip()


def physical_data(pg, cols):
    """모델=열 표를 x 좌표로 읽는다. 반환 [(라벨, [모델별 값])].

    ⚠ find_tables 의 칸을 쓰지 않는다 — 그 칸이 모델 둘을 하나로 묶는다(위 설명).
    """
    if not cols:
        return []
    lines = page_lines(pg)
    # ⚠ 머리글 **위**는 읽지 않는다. 4쪽 위쪽에 온도조절기 그림이 있어 그 글자가
    #   라벨 없는 줄로 잡혀 첫 행('Amount')에 통째로 붙었다. 머리글 줄 자체도 뺀다.
    _c2, head_y = model_columns(lines, with_y=True)
    xs = [x for _c, x in cols]
    ent = []
    for y in sorted(lines):
        if head_y is not None and y <= head_y + 1:
            continue
        left = [c for c in lines[y] if c[0] < VALUE_X]
        vals = [c for c in lines[y] if c[0] >= VALUE_X]
        if not vals:
            continue
        slot = [[] for _ in cols]
        for x0, x1, t in vals:
            c = (x0 + x1) / 2
            slot[min(range(len(xs)), key=lambda i: abs(xs[i] - c))].append(t)
        # 왼쪽 여백의 **묶음 이름**만 뗀다(함정 5). 같은 x 자리에 진짜 라벨도 있어
        # 좌표로는 못 가른다 — 'Refrigerant load'(24.4) 와 'Compressor'(25.5) 가
        # 1pt 차이다. 그래서 문서에 실제로 나온 묶음 낱말만 목록으로 뗀다.
        words = [t for _a, _b, t in left]
        label = row_label([c for c in left if c[2] not in MARGIN_WORDS])
        ent.append([y, label, [" ".join(s) for s in slot], words])

    # 라벨 없는 줄은 **가까운 쪽** 행에 붙인다(함정 3). 앞이라고 단정하면 안 된다 —
    # 'Power supply' 는 둘째 줄이 라벨 줄 **위**에 있어(376 → 379) 앞 행인
    # 'Nominal power' 에 전원이 붙어 버렸다.
    labeled = [i for i, e in enumerate(ent) if e[1]]
    for i, e in enumerate(ent):
        if e[1]:
            continue
        prev = max((j for j in labeled if j < i), default=None)
        nxt = min((j for j in labeled if j > i), default=None)
        pick = prev if nxt is None else nxt if prev is None else (
            prev if abs(ent[prev][0] - e[0]) <= abs(ent[nxt][0] - e[0]) else nxt)
        if pick is None:
            continue
        ent[pick][2] = [(a + " / " + b).strip(" /") if b else a
                        for a, b in zip(ent[pick][2], e[2])]
    rows = [(e[1], e[2]) for e in ent if e[1]]

    # 같은 라벨이 되풀이된다('Nominal power kW' 가 압축기·실내팬·실외팬 셋).
    # 묶음 이름을 못 붙이므로 **원문에 나온 순번**만 적는다 — 어느 것이 무엇인지는
    # 문서 배치가 말해 주지 않는다(gap 에 적었다).
    cnt = {}
    for lab, _v in rows:
        cnt[lab] = cnt.get(lab, 0) + 1
    dup, seen = {k for k, n in cnt.items() if n > 1}, {}
    out = []
    for lab, v in rows:
        if lab in dup:
            seen[lab] = seen.get(lab, 0) + 1
            lab = "%s (원문 %d번째)" % (lab, seen[lab])
        out.append((lab, v))
    return out


def anchor_y(lines, pattern):
    """그 낱말이 처음 나오는 줄의 y. 없으면 None."""
    for y in sorted(lines):
        if re.search(pattern, " ".join(t for _a, _b, t in lines[y]), re.I):
            return y
    return None


def by_model_rows(pg, cols_wanted=4, y_from=None, y_to=None):
    """모델=행 표 → {코드: [값…]}. 행 첫 칸이 모델 코드다.

    ⚠ y 구간을 반드시 준다. 한 쪽에 모델=행 표가 **둘 이상** 있다 — K판 7쪽은
    위가 Nominal capacities(6 900 W), 아래가 Nominal flows(1970 m3/h)인데
    구간을 안 주면 아래 표가 위 표를 덮어써 냉방능력이 풍량이 된다.
    실제로 그렇게 나와서 잡았다.
    """
    lines = page_lines(pg)
    out = {}
    for y in sorted(lines):
        if y_from is not None and y < y_from:
            continue
        if y_to is not None and y > y_to:
            continue
        cells = lines[y]
        if not cells:
            continue
        # ⚠ 모델 코드가 줄 **첫 칸**이라고 보면 안 된다. 원문이 2단 조판이라
        #   'Comp. absorbed power 0.980 … | RTH07L | 1 490 …' 처럼 왼쪽 단의
        #   다른 표와 한 줄에 온다 — 첫 칸만 보다가 6모델 중 2개를 놓쳤다.
        idx = next((i for i, c in enumerate(cells)
                    if MODEL_CODE.match(c[2].replace(" ", " ").strip())), None)
        if idx is None:
            continue
        m = MODEL_CODE.match(cells[idx][2].replace(" ", " ").strip())
        code = "RTH-%s%s" % (m.group(1), m.group(2).upper())
        vals, cur, prev = [], [], None
        for x0, x1, t in cells[idx + 1:]:
            if not _num(t):
                continue
            # '6 900' 은 스팬이 둘로 끊긴다 — 가까우면 한 값이다
            if prev is not None and x0 - prev < 6:
                cur.append(t)
            else:
                if cur:
                    vals.append("".join(cur))
                cur = [t]
            prev = x1
        if cur:
            vals.append("".join(cur))
        if len(vals) >= cols_wanted:
            out[code] = vals[:cols_wanted]
    return out


def find_page(doc, *anchors, need_models=True):
    """본문에 이 낱말들이 다 있는 첫 쪽 (0-base). 없으면 None.

    ⚠ 낱말만으로 고르면 **목차 쪽**이 먼저 걸린다 — 2쪽 Index 에 'Physical data'
    가 있어 거기서 모델 열을 못 찾고 멈췄다. 그래서 모델 코드가 3개 이상 있는
    쪽만 받는다(표가 있는 쪽이라는 뜻이다).
    """
    for i in range(doc.page_count):
        lines = page_lines(doc[i])
        t = " ".join(t for cs in lines.values() for _a, _b, t in cs)
        if not all(re.search(a, t, re.I) for a in anchors):
            continue
        if need_models and len(model_columns(lines)) < 3 and not by_model_rows(doc[i], 1):
            continue
        return i
    return None


def table(title, codes, rows, page, source):
    """specTables 항목 — 머리글=형번, 행=항목(전치). 일반 형번 사다리가 읽는 모양이다.

    제목에 'Physical data' 를 넣는 것은 사다리의 제목 게이트에 걸리기 위해서다
    (vendor_aaon 이 'General data' 를 넣는 것과 같은 이유). 뒤에 원문 표 이름과
    쪽을 그대로 붙여 무엇에서 왔는지 잃지 않는다.
    """
    # 물리량은 **행 라벨**에서 뽑는다. 이 표는 전치라(머리글=형번) 열 이름으로
    # 세는 기본 경로가 아무것도 못 찾는다 — 비워 뒀더니 용량·전력이 다 있는데도
    # validate 가 '시뮬레이터에 쓸 값이 아니다'라고 경고했다.
    qs = sorted({q for q in (SP.quantity_of(lab) for lab, _v in rows) if q})
    return {"title": title, "header": [""] + codes,
            "rows": [[lab] + vals for lab, vals in rows],
            "quantities": qs, "orientation": "row", "kind": "rating",
            "page": page, "source": source}


def parse_doc(path, gen):
    """문서 하나 → (specTables, 메모)"""
    import fitz
    doc = fitz.open(path)
    fname = os.path.basename(path)
    out, notes = [], []

    # ── ① Nominal capacities — 핵심 4종 ────────────────────────────────
    p = find_page(doc, r"Nominal capacities", r"Cooling capacity")
    if p is not None:
        lines = page_lines(doc[p])
        y0 = anchor_y(lines, r"Nominal capacities")
        y1 = anchor_y(lines, r"Test conditions")
        vals = by_model_rows(doc[p], 4, y0, y1)
        if vals:
            codes = sorted(vals, key=lambda c: int(c[4:6]))
            out.append(table(
                "Physical data — Nominal capacities (RTH-%s, 원문 %d쪽)" % (gen, p + 1),
                codes,
                [("Cooling capacity (W)", [vals[c][0] for c in codes]),
                 ("Cooling consumption (W)", [vals[c][1] for c in codes]),
                 ("Heating capacity (W)", [vals[c][2] for c in codes]),
                 ("Heating consumption (W)", [vals[c][3] for c in codes])],
                p + 1, fname + "#nominal"))
        miss = [c for c in ("07", "10", "15", "20", "25", "30")
                if "RTH-%s%s" % (c, gen) not in vals]
        if miss:
            notes.append("Nominal capacities 에서 못 읽은 모델 %s — 원문에서 그 행의 "
                         "칸이 눌려 있다(같은 쪽 다른 행은 읽힌다)" % ", ".join(miss))

    # ── ② Test conditions — 그 값이 어느 조건인가 ──────────────────────
    p = find_page(doc, r"Test conditions", r"Outdoor temp")
    if p is not None:
        lines = page_lines(doc[p])
        for y in sorted(lines):
            nums = [t for _a, _b, t in lines[y] if _num(t)]
            if len(nums) == 8:
                out.append({
                    "title": "Test conditions — 정격을 잰 조건 (RTH-%s, 원문 %d쪽)"
                             % (gen, p + 1),
                    "header": ["", "Summer outdoor DB", "Summer outdoor WB",
                               "Summer indoor DB", "Summer indoor WB",
                               "Winter outdoor DB", "Winter outdoor WB",
                               "Winter indoor DB", "Winter indoor WB"],
                    "rows": [["°C"] + nums],
                    "quantities": ["temperature"], "orientation": "row",
                    "kind": "rating",
                    "page": p + 1, "source": fname + "#testcond"})
                break

    # ── ③ Physical data — 압축기·코일·팬·냉매·치수 ─────────────────────
    p = find_page(doc, r"Physical data")
    if p is not None:
        cols = model_columns(page_lines(doc[p]))
        if cols:
            codes = [c for c, _x in cols]
            rows = [(lab, vals) for lab, vals in physical_data(doc[p], cols)
                    if any(v for v in vals)]
            if rows:
                out.append(table(
                    "Physical data (RTH-%s, 원문 %d쪽)" % (gen, p + 1),
                    codes, rows, p + 1, fname + "#physical"))

    # ── ④ Nominal air flows — 정격 풍량·이용 가능 정압 ─────────────────
    p = find_page(doc, r"Nominal\s+flows?")
    if p is not None:
        lines = page_lines(doc[p])
        y0 = anchor_y(lines, r"Nominal\s+flows?")
        vals = by_model_rows(doc[p], 4, y0, None)
        if vals:
            codes = sorted(vals, key=lambda c: int(c[4:6]))
            out.append(table(
                # 능력표와 **같은 쪽**의 다른 표다. 저장소의 (Continued) 규약으로
                # 이어 붙이면 형번 하나가 한 레코드가 된다 — 쪽이 같아 출처도
                # 어긋나지 않는다(datasets.merge_continued_unit_rows).
                "Physical data — Nominal capacities (RTH-%s, 원문 %d쪽) (Continued)"
                % (gen, p + 1),
                codes,
                [("Indoor nominal air flow (m3/h)", [vals[c][0] for c in codes]),
                 ("Indoor available pressure (Pa)", [vals[c][1] for c in codes]),
                 ("Outdoor nominal air flow (m3/h)", [vals[c][2] for c in codes]),
                 ("Outdoor available pressure (Pa)", [vals[c][3] for c in codes])],
                p + 1, fname + "#airflow"))
    doc.close()
    return out, notes


GAP = ("정격은 명판 대조로 확인했다 — 3쪽 Nominal power 24값이 능력표와 전부 일치한다"
       "(다른 쪽에 따로 인쇄된 값이라 같은 표를 두 번 읽은 것이 아니다). "
       "⚠ Physical data 의 되풀이 라벨은 **어느 장치 것인지 못 밝혔다** — "
       "'Nominal power kW' 가 압축기·팬 둘로 셋인데, 묶음 이름이 왼쪽 여백에 "
       "세로로 놓여 블록 경계와 y 가 어긋난다. 지어내지 않고 원문 순번만 적었고, "
       "그래서 팬 모터·코일 값은 형번 확정본에 올리지 않는다. "
       "⚠ 4쪽 Physical data 는 화면에는 싣되 형번 확정본에는 안 올린다 — 확정본은 "
       "형번 하나에 출처 표·쪽이 하나라, 7·8쪽 능력표와 다른 쪽인 값을 같은 레코드에 "
       "넣으면 출처가 어긋난다(냉매 충전량이 그것이다). "
       "BAS 포인트는 이 문서에 없다 — 같은 제품을 YKN2Open 게이트웨이가 내보낸다"
       "(모델 %s 의 'ykn2open-bms-gateway' 판, 49점). "
       "⚠ K판 10쪽 실내팬 표의 6 mm WG 소비전력이 373 W 로 앞뒤(455·480)보다 낮다 — "
       "깨끗한 폰트로 그렇게 적혀 있어 고치지 않았다(원문 오타로 보인다). "
       "⚠ 문서의 임베드 폰트(Gen_*) 40%% 는 ToUnicode 가 1 밀려 있다. 정격 표는 "
       "깨끗한 폰트라 무사하고, 도면·배선도 라벨만 파서가 되돌린다.")


def main(argv):
    ap = argparse.ArgumentParser(description="JCI Roomtop RTC/RTH 정격 취입")
    ap.add_argument("--dump", action="store_true", help="주입하지 않고 표만 본다")
    a = ap.parse_args(argv)

    tables, notes = [], []
    for fname, gen in DOCS:
        path = os.path.join(RAW, fname)
        if not os.path.exists(path):
            print("  · %s 없음 — collect.py --run jci-york-rth-tech-guide" % fname)
            continue
        ts, ns = parse_doc(path, gen)
        tables.extend(ts)
        notes.extend(ns)
        print("  · %-36s 표 %d개" % (fname, len(ts)))
        for t in ts:
            print("      %-52s %d행 × %d형번"
                  % (t["title"][:52], len(t["rows"]), len(t["header"]) - 1))
    if a.dump:
        for t in tables:
            print("\n### %s" % t["title"])
            print("   " + " | ".join(t["header"]))
            for r in t["rows"]:
                print("   " + " | ".join(str(c) for c in r))
        return 0
    if not tables:
        print("표를 못 찾았다")
        return 1

    path = os.path.join(DATA, "models", MID + ".json")
    m = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    srcs = {t["source"] for t in tables}
    keep = [t for t in m.get("specTables", []) if t.get("source") not in srcs]
    m.update({
        "id": MID, "equipId": "e5", "vendor": VENDOR,
        "model": MODEL_NAME, "name": MODEL_NAME,
        "cat": "HVAC.AIR.RTU", "tag": "rooftop", "tags": ["rooftop", "heatPump"],
        "status": "active",
        "classifiedBy": "원문 표지 — 'Compact Horizontal Air-Air Heat Pump', "
                        "본문 4쪽이 옥상형(Roomtop) 계열임을 밝힌다",
        "summary": "제품 기술 가이드 2건(K판·L판)에서 정격 취입 — 사양 표 %d개"
                   % (len(keep) + len(tables)),
        "has": {"spec": True, "points": False}, "ede": False,
        "spec": m.get("spec") or [], "io": [], "elec": None, "comm": [], "points": [],
        "specTables": keep + tables,
        "gap": GAP % "johnson-controls-york-ykn2open-control-board"
               + ("" if not notes else " " + " / ".join(notes)),
        "extractor": "vendor_jci_rth",
        "sourceDoc": DOCS[0][0],
    })
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n모델 %s — 사양 표 %d개" % (MID, len(m["specTables"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
