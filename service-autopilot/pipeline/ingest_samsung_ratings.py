# -*- coding: utf-8 -*-
"""삼성 시스템에어컨 — 형번별 정격 취입 (SEC 스펙 가이드, 국내 60Hz).

  PYTHONIOENCODING=utf-8 python ingest_samsung_ratings.py            바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_samsung_ratings.py --run      실제로 기록한다
  PYTHONIOENCODING=utf-8 python ingest_samsung_ratings.py --probe 13 한 쪽만 눈으로 본다

왜 전용으로 읽나
  범용 추출기(specs.py)가 이 문서에서 표 127개·4,088행을 가져왔는데 **값이 뭉개져 있었다.**
  사용자가 짚은 그대로다 — 'DVM S (프리미엄) 39점' 표의 첫 행에 "23.0 26.5 21.7" 처럼
  **서로 다른 3개 행의 값이 한 칸에** 공백으로 이어 붙어 있었다.

  원인은 이 문서의 조판이다. 행 라벨이 3단(대분류·중분류·소분류)이고 대분류와 단위가
  **세로로 병합**돼 글자가 병합 구간 한가운데 앉는다. find_tables 는 그 묶음을 한 행으로
  접으면서 3개 행의 값을 한 칸에 밀어 넣었다. 게다가 한 쪽에 **좌·우 두 표**가 나란히 있어
  오른쪽 절반을 잃거나 뒤섞었다.

원문 구조 — 추측할 필요가 없다
  이 PDF 는 셀 눈금선을 **얇은 채움 사각형**(get_drawings 의 type='f')으로 그린다.
  세로선 = 폭<3·높이>=4, 가로선 = 높이<3·폭>=4. 그리고 **병합된 칸에는 그 선이 없다.**
  그래서 병합을 추론하지 않고 읽는다:
    세로 병합 = 그 열 대역에 아래쪽 가로선이 없다   가로 병합 = 그 행 대역에 오른쪽 세로선이 없다
  글자는 병합 구간의 **한가운데** 앉으므로 ffill·bfill 둘 다 틀린다 — 칸을 먼저 만들고
  그 사각형에 중심이 드는 낱말을 담아야 맞는다.

  좌·우 두 표는 **x 간격으로 가르면 안 된다**(표 사이 여백 48pt 가 값 칸 피치 72pt 보다 좁다).
  쪽 한가운데(x=615)로 자른다. 반쪽 안에서 위·아래로 겹친 표는 가로선 y 간격으로 가른다.

담는 범위 (규칙 0)
  형번이 **열로 오는** 정격표만 담는다. 다음 셋은 조판이 달라 이번에 담지 않고 gap 에 남긴다 —
  ERV 환기(p61~63, 열이 형번이 아니라 풍량 구분), DVM AHU(p50, 라벨 4단·한 열에 표 둘),
  Hydro Unit(p59, 한 열에 형번 둘).
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

MODEL_ID = "samsung-mim-b17bn-bacnet-gateway"
DOC = "Samsung_SEC_SpecGuide_KR_2017-03.pdf"
SPLIT_X = 615.0            # 쪽 한가운데 — 좌·우 두 표를 가르는 자리
TOL = 1.5                  # 같은 눈금선으로 볼 오차(pt)
BLOCK_GAP = 30.0           # 이보다 크게 벌어지면 다른 표

# 담지 않는 쪽 — 조판이 달라 이 판독기로는 틀리게 읽힌다(gap 에 사유를 남긴다).
SKIP_PAGES = {50, 59, 61, 62, 63}

# 행 라벨 → 물리량. 시뮬레이터가 단위 문자열을 다시 파싱하지 않게 미리 붙인다.
QTY = [
    (r"소비전력|출력", "power"),
    (r"효율|EER|COP|IEER|등급", "efficiency"),
    (r"전류|차단기", "current"),
    (r"풍량", "airflow"),
    (r"정압", "pressure"),
    (r"중량", "weight"),
    (r"충진량", "mass"),
    (r"온도", "temperature"),
    (r"전원\s*사양", "voltage"),
    (r"치수|액관|가스관|배관|전원선|통신선|배수관", "dimension"),
    (r"능력|성능|냉방|난방|용량|냉동톤", "capacity"),
]
# 형번으로 볼 문자열 — 계열마다 모양이 다르다(AHU-J-60 · NJ0521CXB2 · AVXDSH052B3 …).
CODE = re.compile(r"^(?:[A-Z]{2,6}\d{3,4}[A-Z0-9]*|AHU-[A-Z]-\d+)$")


def _c(t):
    return re.sub(r"\s+", " ", (t or "").replace("", "±")).strip()


def rules(page):
    """눈금선을 모은다 → (세로선 [(x,y0,y1)], 가로선 [(y,x0,x1)])"""
    V, H = [], []
    for d in page.get_drawings():
        if d.get("type") != "f":
            continue
        r = d["rect"]
        w, h = r.width, r.height
        if w < 3 and h >= 4:
            V.append(((r.x0 + r.x1) / 2, r.y0, r.y1))
        elif h < 3 and w >= 4:
            H.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
    return V, H


def cluster(vals, tol):
    out = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def blocks(H):
    """가로선 y 를 표 단위로 묶는다 — y 가 BLOCK_GAP 넘게 벌어지면 다른 표."""
    ys = cluster([y for y, a, b in H], TOL)
    if len(ys) < 4:
        return []
    out, cur = [], [ys[0]]
    for y in ys[1:]:
        if y - cur[-1] > BLOCK_GAP:
            out.append(cur)
            cur = []
        cur.append(y)
    out.append(cur)
    return [b for b in out if len(b) >= 4]


def covered(segs, key, a, b):
    """key 자리의 눈금선이 (a,b) 구간을 덮나. 선은 칸마다 토막나 있어 겹침을 더해서 본다."""
    got = 0.0
    for k, s0, s1 in segs:
        if abs(k - key) <= TOL:
            got += max(0.0, min(b, s1) - max(a, s0))
    return got >= (b - a) * 0.6


def read_block(page, V, H, ys):
    """표 하나 → (칸 얻는 함수, xs, ys, 사각형).

    ⚠ **값 칸에는 행 구분선이 아예 없다.** 대분류 묶음(성능 3행 등)을 하나의 상자로만
    긋고 그 안은 비워 둔다. 그래서 '선이 없으면 병합'을 값 열에 그대로 적용하면
    3개 행의 값이 한 칸으로 뭉쳐진다 — find_tables 가 낸 것과 똑같은 사고다.
    세로 병합 판정은 **라벨 열에만** 쓰고(vmerge 인자), 값 열은 늘 한 행씩 읽는다.

    그리고 병합 칸은 위로도 걸어 올라가야 한다. 아래로만 걸으면 묶음의 **마지막 행**이
    한가운데 앉은 글자를 놓친다 — 실제로 '저온 난방' 행에서 대분류 '성능' 이 사라졌다.
    """
    y0, y1 = ys[0], ys[-1]
    segs = [(y, a, b) for y, a, b in H if y0 - TOL <= y <= y1 + TOL]
    if not segs:
        return None
    xa = min(a for _, a, _ in segs)
    xb = max(b for _, _, b in segs)
    xs = cluster([xa, xb] + [x for x, a, b in V
                             if xa - 2 <= x <= xb + 2 and b > y0 + 2 and a < y1 - 2], TOL)
    if len(xs) < 3:
        return None
    words = [w for w in page.get_text("words")
             if xa - 2 <= (w[0] + w[2]) / 2 <= xb + 2 and y0 <= (w[1] + w[3]) / 2 <= y1]
    nrow, ncol = len(ys) - 1, len(xs) - 1
    vseg = [(x, a, b) for x, a, b in V if xa - 2 <= x <= xb + 2]

    def cell(i, j, vmerge=True):
        top = bot = i
        if vmerge:
            while top > 0 and not covered(segs, ys[top], xs[j], xs[j + 1]):
                top -= 1
            while bot + 1 < nrow and not covered(segs, ys[bot + 1], xs[j], xs[j + 1]):
                bot += 1
        # 가로 병합은 **그 행 높이**로만 본다 — 세로선이 행마다 토막나 있기 때문이다.
        left = right = j
        while left > 0 and not covered(vseg, xs[left], ys[i], ys[i + 1]):
            left -= 1
        while right + 1 < ncol and not covered(vseg, xs[right + 1], ys[i], ys[i + 1]):
            right += 1
        return (xs[left], ys[top], xs[right + 1], ys[bot + 1], left, right)

    def text(c):
        cx0, cy0, cx1, cy1 = c[:4]
        got = [w for w in words if cx0 <= (w[0] + w[2]) / 2 <= cx1
               and cy0 <= (w[1] + w[3]) / 2 <= cy1]
        got.sort(key=lambda w: (round(w[1] / 4), w[0]))
        return _c(" ".join(w[4] for w in got))

    return cell, text, xs, ys, (xa, y0, xb, y1)


def title_of(page, rect):
    """표 제목 — 표 위 26pt 안의 글자."""
    xa, y0, xb, _ = rect
    got = [w for w in page.get_text("words")
           if xa - 4 <= (w[0] + w[2]) / 2 <= xb + 4 and y0 - 26 <= (w[1] + w[3]) / 2 < y0 - 2]
    got.sort(key=lambda w: (round(w[1] / 4), w[0]))
    return _c(" ".join(w[4] for w in got))


def quantity(label):
    for pat, q in QTY:
        if re.search(pat, label, re.I):
            return q
    return ""


def build_table(page, pno, half, V, H, ys):
    got = read_block(page, V, H, ys)
    if not got:
        return []
    cell, text, xs, ys, rect = got
    nrow, ncol = len(ys) - 1, len(xs) - 1

    def header_at(ri):
        """이 행이 형번 머리글인가 → (값 대역 시작 열, 열 묶음, 형번들)

        라벨은 계열마다 '모델명'·'모델' 로 갈린다. 그리고 실내기 표는 형번 하나가
        **두 열을 덮는다**(판넬 노출형/매립형). 머리글의 병합 폭으로 열 묶음을 정하고
        값도 같은 묶음으로 읽어야 형번 수와 값 수가 맞는다.
        """
        flat = [text(cell(ri, j, vmerge=False)) for j in range(ncol)]
        if not any(c.startswith("모델") for c in flat[:6]):
            return None
        vs = None
        for j in range(1, ncol):
            if CODE.match(flat[j].replace(" ", "")):
                vs = j
                break
        if vs is None:
            return None
        groups, codes, j = [], [], vs
        while j < ncol:
            c = cell(ri, j, vmerge=False)
            span = max(1, min(c[5], ncol - 1) - max(c[4], vs) + 1)
            groups.append((j, j + span - 1))
            codes.append(text(c))
            j += span
        if not codes or len(set(codes)) < len(codes):
            return None
        return vs, groups, codes

    heads = [ri for ri in range(nrow) if header_at(ri)]
    if not heads:
        return []
    # 한 덩어리에 표가 둘 이상 붙어 있을 수 있다(원문 p30 은 위·아래 표 사이가 좁아
    # 한 덩어리로 잡힌다). 머리글이 나올 때마다 갈라 각각을 표로 만든다.
    bounds = [0] + [h - 1 for h in heads[1:]] + [nrow]
    out = []
    for k, ri0 in enumerate(heads):
        lo_r, hi_r = bounds[k], bounds[k + 1]
        vstart, groups, codes = header_at(ri0)
        uj = vstart - 1        # 단위 열 = 값 대역 바로 왼쪽
        rows, quants, seen = [], [], set()
        for ri in range(lo_r, hi_r):
            if ri == ri0:
                continue
            parts = []
            for j in range(0, uj):
                c = cell(ri, j)
                if c[4] != j:             # 왼쪽 칸에서 이어진 것 — 이미 담았다
                    continue
                t = text(c)
                if t and t not in parts:
                    parts.append(t)
            cu = cell(ri, uj)
            unit = ""
            if cu[4] == uj:               # 병합돼 오지 않았다 = 진짜 단위 칸
                unit = text(cu)
            elif text(cu) and not parts:
                parts.append(text(cu))
            if unit in ("-", "—", "–"):   # 원문이 '단위 없음'을 대시로 적은 것
                unit = ""
            # 대분류가 중분류의 앞머리인 표기가 있다('성능'+'성능 (정격)').
            parts = [p for p in parts if not any(q != p and q.startswith(p) for q in parts)]
            label = " ".join(parts)
            if not label or label.startswith("모델"):
                continue
            vals = []
            for ja, jb in groups:
                sub, j = [], ja
                while j <= jb:
                    c = cell(ri, j, vmerge=False)
                    t = text(c)
                    if t and t not in sub:
                        sub.append(t)
                    j += max(1, min(c[5], jb) - max(c[4], ja) + 1)
                vals.append(" / ".join(sub))
            if not any(vals):
                continue
            name = "%s (%s)" % (label, unit) if unit else label
            if name in seen:
                name = "%s [%d]" % (name, ri)
            seen.add(name)
            rows.append([name] + vals)
            quants.append(quantity(label))
        if not rows:
            continue
        out.append(({
            "title": "형번별 정격 — %s" % (title_of(page, rect) or "p%d %s쪽" % (pno, half)),
            "page": pno,
            "orientation": "row",
            "header": ["항목"] + codes,
            "quantities": quants,
            "kind": "rating",
            "source": DOC,
        }, rows))
    return out


def build(doc):
    out, skipped = [], []
    for pno in range(1, doc.page_count + 1):
        if pno in SKIP_PAGES:
            continue
        page = doc[pno - 1]
        V, H = rules(page)
        if not H:
            continue
        for half, lo, hi in (("좌", 0.0, SPLIT_X), ("우", SPLIT_X, page.rect.x1)):
            hv = [v for v in V if lo <= v[0] <= hi]
            hh = [h for h in H if h[1] >= lo - 2 and h[2] <= hi + 2]
            for ys in blocks(hh):
                got = build_table(page, pno, half, hv, hh, ys)
                if not got:
                    skipped.append((pno, half, round(ys[0])))
                for t, rows in got:
                    t["rows"] = rows
                    out.append(t)
    return out, skipped


def _num(t):
    """검산용 — 원문이 같은 값을 5.2 / 5.20 처럼 자릿수를 달리 적는다."""
    try:
        return float(str(t).replace(",", ""))
    except ValueError:
        return str(t)


def gate(tabs):
    """검산 — 머리글 '용량' 행과 '성능 … 냉방' 행은 같은 값이어야 한다.

    두 값은 표에서 물리적으로 떨어진 자리에 있으므로, 격자가 한 칸이라도 어긋나면 깨진다.
    좌표로 읽은 것을 좌표로 확인하는 게 아니라 **원문 자체의 불변식**으로 확인하는 것이다.
    """
    ok = bad = 0
    for t in tabs:
        cap = nom = None
        for r in t["rows"]:
            # 용량이 kW 로 적힌 표에서만 견준다 — 칠러는 RT, Eco 는 마력으로 적어 단위가 다르다.
            if r[0].startswith("용량 (kW)"):
                cap = r[1:]
            elif re.match(r"^성능.*냉방 \(kW\)", r[0]):
                nom = r[1:]
        if cap and nom and any("/" in x for x in cap + nom):
            continue          # 하위열이 둘인 표(GEO 인증스펙)는 견줄 짝이 아니다
        if cap and nom:
            if [_num(x) for x in cap] == [_num(x) for x in nom]:
                ok += 1
            else:
                bad += 1
                print("   ⚠ 검산 실패 p%d %s" % (t["page"], t["title"][:40]))
                print("     용량 %s" % cap[:5])
                print("     냉방 %s" % nom[:5])
    return ok, bad


def probe(doc, pno):
    page = doc[pno - 1]
    V, H = rules(page)
    for half, lo, hi in (("좌", 0.0, SPLIT_X), ("우", SPLIT_X, page.rect.x1)):
        hv = [v for v in V if lo <= v[0] <= hi]
        hh = [h for h in H if h[1] >= lo - 2 and h[2] <= hi + 2]
        for ys in blocks(hh):
            got = build_table(page, pno, half, hv, hh, ys)
            print("=== p%d %s y=%d ===" % (pno, half, ys[0]))
            if not got:
                print("   (표로 못 읽음)")
                continue
            for t, rows in got:
                print("   ", t["title"])
                print("   ", t["header"])
                for q, r in zip(t["quantities"], rows):
                    print("    %-11s %s" % (q, r))
    return 0


def main(argv):
    import fitz
    doc = fitz.open(os.path.join(DATA, "raw", DOC))
    if "--probe" in argv:
        return probe(doc, int(argv[argv.index("--probe") + 1]))
    run = "--run" in argv
    tabs, skipped = build(doc)
    n = sum(len(t["rows"]) for t in tabs)
    codes = {(t["title"], c) for t in tabs for c in t["header"][1:]}
    print("정격 표 %d개 · %d행 · 형번 %d건(계열까지 합쳐 셈)" % (len(tabs), n, len(codes)))
    print("쪽별 표 수:", dict(sorted(collections.Counter(t["page"] for t in tabs).items())))
    if skipped:
        print("표로 못 읽은 덩어리 %d개:" % len(skipped), skipped[:12])
    ok, bad = gate(tabs)
    print("검산(용량 == 성능·냉방): %d 통과 · %d 실패" % (ok, bad))
    for t in tabs[:1]:
        print("\n  %s  (원문 %d쪽)" % (t["title"], t["page"]))
        print("   ", t["header"])
        for r in t["rows"][:8]:
            print("     ", r)

    mp = os.path.join(DATA, "models", MODEL_ID + ".json")
    m = json.load(io.open(mp, encoding="utf-8"))
    before = len(m.get("specTables") or [])
    keep = [t for t in (m.get("specTables") or []) if t.get("source") != DOC]
    m["specTables"] = keep + tabs
    m["has"] = dict(m.get("has") or {}, spec=bool(m["specTables"]))
    gaps = [g for g in (m.get("gap") or []) if "스펙 가이드" not in g]
    gaps.append(
        "정격은 삼성 SEC 스펙 가이드(2017-03, 국내 60Hz)에서 형번이 열로 오는 표만 담았다. "
        "ERV 환기(원문 p61~63)는 열이 형번이 아니라 풍량 구분이고, DVM AHU(p50)는 라벨이 4단에 "
        "한 열에 표가 둘이며, Hydro Unit(p59)은 한 열에 형번이 둘이라 조판이 달라 담지 않았다. "
        "성능 값의 시험 조건은 원문 p64 각주에 있다(정격 냉방 27℃DB/19℃WB·실외 35/24·배관 50m).")
    m["gap"] = gaps
    print("\n사양 표 %d개 → %d개 (이 문서에서 온 것만 갈아 끼운다)" % (before, len(m["specTables"])))
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
