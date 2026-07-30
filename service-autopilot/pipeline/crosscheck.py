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
HDRWORD = re.compile(r"^(Object (Identifier|Name|States|Status|Data Points.*)|Property Values|"
                     r"Register (Address|Type|Value)|"
                     r"Description|Units?|Configuration|Dependency|Valid Range|"
                     r"Relinquish Default|Read/?Write|Network Variable \w+|NV ?#|"
                     r"nv Index|Profile Index|SNVT\w*|Variable (Type|Description)|"
                     r"Point Name|Diagnostic (Name|Code.*)|Byte Order|Invalid Values|"
                     r"Delta to Send.*|Send HrtBt|Recv HrtBt|Suffix|"
                     r"(Analog|Binary|Multi-?State) (Input|Output|Value)s?( \w+)?)$", re.I)


def _lines(pdf, head_pt=80, with_y=False):
    """(페이지번호, 줄) 순서대로. 머리글 영역은 **좌표로** 잘라낸다.
    with_y=True 면 (페이지, 블록 하단 y, 줄) 을 준다 — 표 제목보다 아래인지 볼 때 쓴다.

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
                    yield (i, b[3], t) if with_y else (i, t)


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
        pid = E.parse_objid(t)
        if pid:
            pending = (pi, S.canon_type(pid[0]), pid[1])
            continue
        if pending and E.nameish(t):
            out.append({"page": pending[0], "type": pending[1],
                        "inst": pending[2], "name": t})
            pending = None
    return _drop_sparse(out)


def raw_bacnet_rev(pdf):
    """이름이 ID보다 **앞에** 오는 문서 — Belimo 는 'RelPos' 다음 줄이 'AI[1]' 이다.

    같은 줄 읽기지만 짝짓는 방향이 반대다. 방향을 잘못 잡으면 겹침이 거의 0이 되므로
    두 방향을 모두 만들어 두고 겹침이 큰 쪽을 쓴다.
    """
    out, prev = [], None
    for pi, t in _lines(pdf):
        pid = E.parse_objid(t)
        if pid and prev and E.nameish(prev):
            out.append({"page": pi, "type": S.canon_type(pid[0]),
                        "inst": pid[1], "name": prev})
            prev = None
            continue
        prev = t
    return _drop_sparse(out)


TYPETOK = re.compile(r"^(AI|AO|AV|BI|BO|BV|MI|MO|MV|MSI|MSO|MSV)$")
# 한 문서 안에 장치가 둘이고 **번호를 다시 쓰는** 경우가 있다 — JCI VRF 게이트웨이는
# 실내기 표와 실외기 표가 AI-16 을 각각 다른 뜻으로 쓴다. 표 제목으로 갈라야 한다.
CAPTION = re.compile(r"points for (indoor|outdoor) units", re.I)


def _captions(pdf):
    """표 제목만 따로 줍는다 — 페이지 맨 위에 있어 _lines 의 머리글 자르기에 걸린다.
    돌려주는 것은 [(페이지, 제목 하단 y, 'indoor'|'outdoor')] 이다."""
    import fitz
    out = []
    for i, pg in enumerate(fitz.open(pdf)):
        for b in pg.get_text("blocks"):
            m = CAPTION.search(re.sub(r"\s+", " ", b[4]))
            if m:
                out.append((i, b[3], m.group(1).lower()))
    return out


def _sect_at(caps, page, y):
    """이 줄을 덮는 표 제목 — 같은 쪽에서 위쪽, 없으면 앞 쪽의 마지막 제목."""
    best = None
    for cp, cy, s in caps:
        if cp < page or (cp == page and cy <= y):
            best = s
    return best


def raw_typefirst(pdf):
    """타입이 제 줄에 혼자 오고 번호가 맨 뒤인 문서 — JCI 는 열을 이렇게 갈라 적는다.

        AI / Indoor Unit Capacity Code / UNIT-CAP / 4

    타입 줄에서 시작해 숫자만 있는 줄을 만나면 그 직전 줄이 오브젝트 이름이다.
    표 인식을 쓰지 않으므로 extract.py 와 독립된 경로다.
    """
    caps = _captions(pdf)
    out, pend, buf = [], None, []
    for pi, y, t in _lines(pdf, with_y=True):
        sect = _sect_at(caps, pi, y)
        if TYPETOK.match(t):
            pend, buf = (pi, S.canon_type(t)), []
            continue
        if pend is None:
            continue
        if BARE.match(t):
            name = buf[-1] if buf else ""
            if E.nameish(name) and len(name) >= 3:
                out.append({"page": pend[0], "type": pend[1], "inst": int(t),
                            "name": name, "sect": sect})
            pend, buf = None, []
            continue
        buf.append(t)
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


def raw_modbus_wide(pdf):
    """주소가 작은 레지스터 표(0·1·2…) — 오름차순 성질로 잡음을 거른다."""
    out, pending, last, page = [], None, -1, -1
    for pi, t in _lines(pdf):
        if pi != page:
            page, last = pi, -1
        if re.match(r"^\d{1,5}$", t):
            v = int(t)
            pending = (pi, v) if v > last else None
            continue
        if pending is None:
            continue
        if E.nameish(t) and len(t) >= 3:
            out.append({"page": pending[0], "type": "MB", "inst": pending[1], "name": t})
            last = pending[1]
        pending = None
    return _drop_sparse(out)


def raw_modbus(pdf):
    """Modbus 레지스터 표 — 레지스터 번호 줄 → 바로 다음 이름 줄.

    BACnet 오브젝트 ID 가 없는 문서는 이 경로로 대조한다. 없으면 교차 대조가
    아예 안 돼 '확인할 방법 없음' 상태로 남는다.

    레지스터 주소는 0·1·2 처럼 작을 수 있어 '숫자 줄'만으로는 쪽번호·표 안 값과
    구분되지 않는다. **표 안에서 주소는 오름차순**이라는 성질을 함께 써서 거른다.
    """
    out, pending = [], None
    for pi, t in _lines(pdf):
        if re.match(r"^[1-4]\d{4}$", t):
            pending = (pi, int(t))
            continue
        if pending is None:
            continue
        if E.nameish(t) and len(t) >= 3:
            out.append({"page": pending[0], "type": "MB", "inst": pending[1], "name": t})
        pending = None
    return _drop_sparse(out)


def raw_hexreg(pdf):
    """'D000' 형식 레지스터 — ebm-papst 가 문자+16진으로 쓴다. 번호 줄 → 다음 이름 줄."""
    out, pending = [], None
    for pi, t in _lines(pdf):
        m = E.HEX_REG.match(t)
        if m:
            pending = (pi, int(m.group(2), 16))
            continue
        if pending is None:
            continue
        if E.nameish(t) and len(t) >= 3:
            out.append({"page": pending[0], "type": "MB", "inst": pending[1], "name": t})
        pending = None
    return _drop_sparse(out)


def drop_repeats(rows, limit=3):
    """줄 경로에서 같은 이름이 여러 인스턴스에 반복되면 그건 포인트 이름이 아니다.

    쪽 제목·표 제목이 숫자 줄 뒤에 와서 이름으로 잡히는 일이 있다
    ('VAV-Compact', 'Modbus Register Overview'). 이걸 그대로 두면 표가 맞는데도
    불일치로 세어 진짜 오류가 묻힌다. 대조 대상에서 빼면 그 포인트는
    '확인 못 함'으로 남고, 검증이 커버리지 부족으로 알려 준다.
    """
    n = collections.Counter(r["name"] for r in rows)
    return [r for r in rows if n[r["name"]] < limit]


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


def _key(s):
    """비교용 정규화 — 공백·밑줄·하이픈을 지우고 소문자로.

    셀 안에서 줄바꿈된 이름을 표 인식이 흩뜨리는 일이 있다
    ('Sens1Active_Volt' → 'Sens1Active Volt _'). 구분자 차이는 추출 오류가 아니다.
    """
    return re.sub(r"[\s_\-]+", "", s).lower()


def _same(a, b):
    """두 읽기가 같은 이름을 가리키는가.

    한쪽이 줄바꿈에서 잘려 머리나 꼬리만 남는 경우가 있어 포함 관계도 인정한다.
    열이 통째로 밀리면 글자가 전혀 겹치지 않으므로, 이 완화로 진짜 오류를 놓치지 않는다.
    """
    x, y = _key(a), _key(b)
    if not x or not y:
        return False
    return x == y or (len(min(x, y, key=len)) >= 4 and (x in y or y in x))


def compare(pdf, table_rows=None, sect=None):
    """sect 를 주면 그 표 제목 아래 줄만 대조에 쓴다.

    한 문서가 장치 둘을 담고 번호를 다시 쓰면(JCI 실내기·실외기) 걸러내지 않은
    줄 경로는 두 장치를 뒤섞어 가짜 불일치를 만든다.
    """
    fam = E.classify(pdf)
    if table_rows is None:
        table_rows = (E.extract_lontalk(pdf, keep_order=True) if fam == "lontalk"
                      else E.extract(pdf)[0])
    if sect:
        table_rows = [r for r in table_rows if r.get("sect") == sect]
    # 줄 읽기 경로가 여러 개다. '줄이 많이 잡힌 것'이 아니라 **표와 실제로 겹치는 것**을
    # 골라야 한다. 줄 수로 고르다가 냉동기 문서에서 엉뚱한 경로가 뽑혀 겹침 1건이 됐다.
    A = _segmap(table_rows)
    flat = {k for seg in A for k in seg}
    cands = ([raw_lontalk(pdf)] if fam == "lontalk"
             else [raw_bacnet(pdf), raw_bacnet_rev(pdf), raw_bare(pdf),
                   raw_typefirst(pdf), raw_modbus(pdf), raw_modbus_wide(pdf),
                   raw_hexreg(pdf)])
    if sect:
        cands = [[r for r in rs if r.get("sect") == sect] for rs in cands]
    tbl = {}
    for seg in A:
        tbl.update(seg)

    def agree(rs):
        """표와 겹치는 지점에서 **맞은 수 − 틀린 수**.

        맞은 수만 세면 잡음이 많아도 덩치가 큰 경로가 이긴다 — 실제로 Modbus 완화
        경로가 그래서 뽑혀 일치율이 100%에서 79%로 떨어졌다. 틀린 것을 빼야
        '이 문서를 가장 바르게 읽는 경로'가 뽑힌다.
        """
        ok = bad = 0
        for r in rs:
            t = tbl.get((r["type"], r["inst"]))
            if not t:
                continue
            if _same(t, r["name"]):
                ok += 1
            else:
                bad += 1
        return ok - bad
    raw = drop_repeats(max(cands, key=lambda rs: (
        agree(rs), sum(1 for r in rs if (r["type"], r["inst"]) in flat))))
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
            # 이름이 오브젝트 ID 를 되풀이한 것뿐이면 대조할 정보가 없다.
            # (Danfoss 알림 오브젝트는 이름 칸이 'NC 100' 처럼 ID 그대로다)
            if re.fullmatch(r"%s[\s:_-]*%d" % (k[0], k[1]), a[k].strip(), re.I):
                continue
            # 한쪽이 줄바꿈에서 꼬리만 남아 서너 글자뿐이면 대조 근거가 못 된다
            # ('Sens1Passive_Ohm' 이 'Ohm' 으로 잘린 경우). 틀렸다고 세는 대신
            # 확인 못 한 것으로 두고, 커버리지 경고가 알려 준다.
            if min(len(_key(a[k])), len(_key(b[k]))) < 4:
                continue
            both += 1
            # 비교 전 공백을 고른다 — 'Circuit 1  Available'(이중 공백) 같은
            # 표기 차이는 추출 오류가 아니다.
            na, nb = re.sub(r"\s+", " ", a[k]), re.sub(r"\s+", " ", b[k])
            (same if _same(na, nb) else diff).append((i, k, na, nb))
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
