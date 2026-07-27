# -*- coding: utf-8 -*-
"""교차 대조 — 표 인식과 **완전히 다른 경로**로 한 번 더 읽어 서로 맞는지 본다.

왜 필요한가
  정답 대조셋(known-good.json)은 사람이 원문을 눈으로 보고 4~6쌍을 넣는 방식이다.
  틀린 추출을 실제로 잡아냈지만, 모델이 수백 건이 되면 사람이 따라갈 수 없다.
  그래서 기계가 스스로 두 번 읽는다.

두 경로
  A. extract.py — PyMuPDF find_tables(). 셀 경계를 인식한다.
  B. 이 파일    — 페이지 텍스트를 줄 순서로 읽는다. 표 인식을 전혀 쓰지 않는다.

두 경로가 같은 (타입, 인스턴스, 이름)에 도달하면 그 포인트는 신뢰한다.
어긋나면 검수 큐로 보낸다. '열이 한 칸 밀리는' 종류의 오류는 B에서는 일어날 수
없으므로(줄 순서만 본다), A의 열 밀림을 B가 잡아낸다.

한 문서에 장치·프로파일이 여러 개면 번호가 겹치므로 **구간별로 나눠 비교**한다.

실행
  python crosscheck.py data/raw/<파일>.pdf
  python crosscheck.py --all
"""
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract as E  # noqa: E402
import schema as S  # noqa: E402

LON_NAME = re.compile(r"^(nvi|nvo|nci|vi|vo)[A-Za-z0-9_.]{2,}$")
BAC_ID = re.compile(r"^(AI|AO|AV|BI|BO|BV|MI|MO|MV|MSI|MSO|MSV)\s*-?\s*(\d{1,6})$")
BARE = re.compile(r"^\d{1,6}$")
SKIP = re.compile(r"^(♥|\(a\)|\(b\)|—|-|\*|\d+)$")
NOISE = re.compile(r"^(Symbio|LonTalk|BACnet|Date:|Firmware|Reference|Object Naming|"
                   r"Note:|Table|Page|BAS-PTS)", re.I)
# 표 머리글 자체 — 줄 읽기에서는 이름 자리에 들어와 가짜 불일치를 만든다
HDRWORD = re.compile(r"^(Object (Identifier|Name|States)|Register (Address|Type|Value)|"
                     r"Description|Units?|Configuration|Dependency|Valid Range|"
                     r"Relinquish Default|Read/?Write|Network Variable \w+|NV ?#|"
                     r"nv Index|Profile Index|SNVT\w*|Variable (Type|Description)|"
                     r"Point Name|Diagnostic (Name|Code.*)|Byte Order|Invalid Values|"
                     r"Delta to Send.*|Send HrtBt|Recv HrtBt|Suffix)$", re.I)


def _lines(pdf, head_pt=80):
    """(페이지번호, 줄) 순서대로. 머리글 영역은 **좌표로** 잘라낸다.

    문자열 목록으로 막으려 했더니 문서마다 머리글이 달라 계속 새는데(모델명·프로토콜명이
    포인트 이름 자리에 섞였다), 머리글은 어느 문서나 페이지 맨 위에 있다.
    실측: BAS-PTS 시리즈는 머리글 y≤73, 첫 표 y≈90 → 80pt 로 자른다.
    """
    import fitz
    for i, pg in enumerate(fitz.open(pdf)):
        # 블록 순서는 PDF가 주는 읽기 순서를 그대로 쓴다. y좌표로 다시 정렬했더니
        # 셀 안에서 줄바꿈된 이름의 뒷부분이 앞부분과 떨어져 짝이 어긋났다.
        for b in (b for b in pg.get_text("blocks") if b[3] > head_pt):
            for ln in b[4].split("\n"):
                t = ln.strip()
                if t and not NOISE.match(t) and not HDRWORD.match(t):
                    yield i, t


def raw_lontalk(pdf):
    """줄 순서: 숫자 줄 → 바로 다음의 nv*/nci* 줄. 표 인식을 쓰지 않는다."""
    out, pending = [], None
    for pi, t in _lines(pdf):
        if BARE.match(t):
            pending = (pi, int(t))
            continue
        if pending is None:
            continue
        if LON_NAME.match(t):
            out.append({"page": pending[0], "inst": pending[1], "name": t,
                        "type": "NCI" if t[:3].lower() == "nci" else "NV"})
        pending = None
    return _drop_sparse(out)


def _drop_sparse(rows, minimum=3):
    """짝이 몇 개 안 나온 페이지는 버린다.

    표 페이지는 한 장에 수십 짝이 나오고, 표지·목차는 한두 개뿐이다. 표 인식을 쓰지 않고도
    '여기는 표가 아니다'를 이 숫자로 가른다 — 냉동기 3종에서 표지 목차 제목이
    AI-1 이름으로 잡히던 것을 이 규칙으로 걸렀다.
    """
    n = collections.Counter(r["page"] for r in rows)
    return [r for r in rows if n[r["page"]] >= minimum]


def raw_bacnet(pdf):
    """줄 순서: 'AI-10101' 같은 ID 줄 → 바로 다음의 이름 줄."""
    out, pending = [], None
    for pi, t in _lines(pdf):
        m = BAC_ID.match(t)
        if m:
            pending = (pi, S.canon_type(m.group(1)), int(m.group(2)))
            continue
        if pending and E.nameish(t):
            out.append({"page": pending[0], "type": pending[1],
                        "inst": pending[2], "name": t})
            pending = None
    return _drop_sparse(out)


def raw_bare(pdf):
    """ID가 숫자만인 문서 — 타입은 페이지 섹션 제목에서 온다 (extract.py와 같은 근거)."""
    types = E.section_types(pdf)
    out, pending = [], None
    for pi, t in _lines(pdf):
        if BARE.match(t):
            pending = (pi, int(t))
            continue
        if pending is None:
            continue
        dt = types.get(pending[0])
        if dt and E.nameish(t) and len(t) >= 3 and not t[0].isdigit():
            out.append({"page": pending[0], "type": S.canon_type(dt),
                        "inst": pending[1], "name": t})
        pending = None
    return _drop_sparse(out)


def _segmap(rows):
    """문서 순서 목록 → [ {(타입,인스턴스): 이름}, ... ] 구간별.

    같은 키가 두 번 나오면 **먼저 읽은 값**을 남긴다. 본문 표가 부록보다 앞에 있으므로,
    부록의 예시·설명 표가 본문 이름을 덮어쓰는 것을 막는다.
    """
    out = []
    for seg in E.split_profiles(rows):
        d = {}
        for r in seg:
            d.setdefault((r["type"], r["inst"]), r["name"])
        out.append(d)
    return out


def compare(pdf, table_rows=None):
    fam = E.classify(pdf)
    if table_rows is None:
        table_rows = (E.extract_lontalk(pdf, keep_order=True) if fam == "lontalk"
                      else E.extract(pdf)[0])
    # 줄 읽기 경로가 여러 개다. '줄이 많이 잡힌 것'이 아니라 **표와 실제로 겹치는 것**을
    # 골라야 한다. 줄 수로 고르다가 냉동기 문서에서 엉뚱한 경로가 뽑혀 겹침 1건이 됐다.
    A = _segmap(table_rows)
    flat = {k for seg in A for k in seg}
    cands = [raw_lontalk(pdf)] if fam == "lontalk" else [raw_bacnet(pdf), raw_bare(pdf)]
    raw = max(cands, key=lambda rs: sum(1 for r in rs if (r["type"], r["inst"]) in flat))
    if len(A) == 1:
        # 표가 '장치 1대'라고 했으면 줄 경로도 쪼갤 이유가 없다. 부록이 본문 번호를
        # 되풀이해 줄 경로가 4조각으로 갈라지고 그 조각과 짝지어져 가짜 불일치가 났다.
        d = {}
        for r in raw:
            d.setdefault((r["type"], r["inst"]), r["name"])
        B = [d]
    else:
        B = _segmap(raw)
    same, diff, both = [], [], 0
    for i, a in enumerate(A):
        # 구간 짝짓기는 순번이 아니라 **겹침 최대**로 한다. 표지의 모델명이 포인트처럼
        # 잡히면 구간이 하나 더 생겨 순번이 밀린다 — 그때도 옳은 짝을 찾아야 한다.
        b = max(B, key=lambda s: len(set(a) & set(s))) if B else {}
        for k in sorted(set(a) & set(b)):
            both += 1
            na, nb = a[k], b[k]
            # 줄 읽기는 셀 안에서 줄바꿈된 이름의 앞부분만 잡을 수 있다 → 접두 일치도 인정
            (same if na == nb or na.startswith(nb) or nb.startswith(na) else diff)\
                .append((i, k, na, nb))
    return {"fam": fam, "segments": len(A), "table": len(table_rows), "raw": len(raw),
            "both": both, "same": len(same), "diff": diff,
            "rate": (len(same) / both) if both else 0.0,
            "verified": {"%s-%d" % k: na for _, k, na, _ in same}}


def main(argv):
    files = sorted(glob.glob(os.path.join(HERE, "data", "raw", "*.pdf"))) \
        if "--all" in argv else [argv[0]]
    bad = 0
    print("%-30s %-8s %3s %5s %5s %5s %7s %s"
          % ("문서", "계열", "구간", "표", "줄", "겹침", "일치율", "불일치"))
    print("─" * 96)
    for f in files:
        r = compare(f)
        weak = r["rate"] < 0.98 or r["both"] < r["table"] * 0.5
        bad += 1 if weak else 0
        print("%-30s %-8s %3d %5d %5d %5d %6.1f%% %4d%s"
              % (os.path.basename(f), r["fam"], r["segments"], r["table"], r["raw"],
                 r["both"], r["rate"] * 100, len(r["diff"]), "  ← 검수" if weak else ""))
        for si, k, na, nb in r["diff"][:3]:
            print("      구간%d %s-%s  표 %r ≠ 줄 %r" % (si + 1, k[0], k[1], na[:38], nb[:38]))
    print("\n검수 필요 %d건 (일치율 98%% 미만 또는 겹침 50%% 미만)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
