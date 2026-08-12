# -*- coding: utf-8 -*-
"""Haystack 원본 defs 를 읽어 설비의 protos(예시 구성)를 전개하고 우리 템플릿과 대조한다.

왜 만들었나
  `data/equips/*.json` 의 pointTables(요구 포인트 템플릿)는 **손으로 쓴 것**이다.
  근거가 사람 머릿속에만 있으니 다음 사고가 났다 —

    e5(공조기) 템플릿이 '냉수밸브 개도'·'온수밸브 개도'를 **필수**로 박아 두었는데
    RTU(직팽식 옥상형)에는 그 밸브가 아예 없다. Trane Precedent(228p)·York ZF/ZJ/ZR·
    Lennox Enlight 원문에 "chilled" 가 0회다. 실측으로도 RTU 9모델 중 매칭 0건인데
    '필수' 라서 영원히 미충족이었다. 정격 쪽에서 'RTU 를 냉수코일 AHU 체크리스트로
    채점' 하던 것과 **같은 구조의 오류**다.

  그래서 "우리가 그렇게 정했다" 대신 **표준이 정한 것**을 근거로 삼는다.
  Haystack def 의 `children`(=protos)은 그 설비가 가질 수 있는 포인트 구성을 태그로
  적어 둔 것이므로, 우리 템플릿과 대조하면 (a) 표준에 있는데 우리가 빠뜨린 것,
  (b) 우리에만 있어 근거를 따로 대야 하는 것이 기계적으로 갈린다.

  ⚠ 다만 이 도구가 답을 다 주지는 않는다. 두 가지를 분명히 한다.
    · **Haystack 은 RTU 와 AHU 를 구분하지 않는다.** `rtu.children` 은 `ahu.children`
      21개와 키 단위로 완전히 같고 차이는 doc 문구와 `is: ahu` 뿐이다.
      → RTU/AHU 분리의 근거는 여기서 못 찾는다. 벤더 원문·실측에서 대야 한다.
      (표준이 그 구분을 담는 곳은 coil 하위 proto 다 — `coolingCoil` 아래에
       `chilled water valve cool cmd` 와 `cool run stage cmd` 가 형제로 있다.)
    · **필수/권장/선택 등급의 근거도 없다.** `mandatory` 마커는 13개 def 에만 있고
      doc 원문이 "Requires that the marker be applied to dicts which use the
      marker's subtypes" — 즉 '하위타입을 쓰면 상위 마커도 같이 달아라' 는 **태그
      공존 규칙**이지 포인트 필수 표시가 아니다. 게다가 `notInherited` 라 하위형에
      내려가지도 않는다. protos 에는 우선순위 표시가 아예 존재하지 않는다.

  즉 이 도구는 **등급을 매기지 않는다. 있다/없다만 본다.**
  그리고 전개 결과는 템플릿이 아니라 **누락 점검용 체크리스트**다 — protos 는
  '가질 수 있는 것'의 조합적 완전열거라서 그대로 행으로 만들면 실물에 없는 포인트가
  대량으로 들어온다(economizer 덕트 밑의 냉수코일, exhaust 덕트 밑의 온수코일 등).

전개 규칙 여섯 줄 (하나라도 빠지면 결과가 조용히 무의미해진다)
  ① `is` 는 반드시 순회한다. 단 두 경우를 헷갈리면 안 된다.
     · children 칸이 **채워진** def 는 원본이 상속을 이미 누적해 보냈다. children def
       자체에 `accumulate` 마커가 있고, 실제로 `children(하위형) ⊇ children(상위형)`
       반례가 0건이다. 그래서 이런 def 에서는 순회해도 늘어나는 것이 없다(ahu 상속+ 0).
     · children 칸이 **아예 빈** def 가 6개 있다 — chiller-absorption·chiller-centrifugal
       ·chiller-reciprocal·chiller-rotaryScrew·vav-parallel·vav-series. 이들은 순회를
       빼면 전개 결과가 **0점**이 된다(chiller 계열 22점, vav 계열 7점이 통째로 사라진다).
     즉 "이미 누적돼 있으니 순회는 필요 없다" 는 절반만 맞는 말이고, 그 절반을 믿고
     순회를 지우면 6개 설비가 빈껍데기가 된다. --equips 의 '상속+' 열로 확인한다.
  ② 태그집합이 정확히 {equip} 또는 {point} 인 proto 는 버린다. '아무 equip/아무
     point 를 가질 수 있다' 는 와일드카드이지 구체 포인트가 아니다. accumulate 때문에
     children 을 가진 113 def 전부에 붙어 있다.
  ③ proto 태그집합 → def 되찾기: 이름에 '-' 가 있는 결합 def(162개)를 조각으로
     분해해 '조각이 전부 태그집합에 들어 있는' 후보를 잡고, 다른 후보의 상위형인 것을
     버린 뒤 조각 수 많은 쪽을 고른다. 이 '조각 수 우선' 이 없으면 `vfd-speed`(%)를
     형제 def `speed`(km/h)로 잘못 잡는다.
  ④ childrenFlatten aspect 는 **경로 누적(전이적)** 으로 물려준다. 한 단계만 물려주면
     ahu→duct→fan-motor 손자 단계가 뭉개져 급기팬·환기팬·배기팬이 전부 같은
     `cmd fan point run` 한 점이 된다(고유 태그조합 241 → 145).
     그리고 물려줄 것을 고를 때 ③의 결합 분해를 함께 쓴다. proto 태그는 마커가 낱개로
     흩어져 있어서 `{chilled, water}` 에서 `water`(is fluid)만 걸리고 `chilled`(is
     marker)가 떨어지는데, 그러면 chiller 의 냉수배관과 냉각수배관이 둘 다
     'entering water' 가 돼 뭉갠다(실측 고유 86 → 52). `chilled-water` 는 defs 에
     실재하고 `is fluid` 이므로 조각째 물려준다.
  ⑤ 재귀 가드는 **경로 chain visited** + 깊이 제한이다. 전역 visited 로 막으면 duct 가
     첫 부모에서만 펼쳐져 나머지 6개 덕트가 통째로 사라진다(README 4항의 '550점 실종').
  ⑥ 못 정한 값은 채우지 않는다. gap 으로 남긴다.

  회귀 지표 (고치고 나면 이 수치부터 확인한다)
    ahu = 노드 278 / leaf 241 / 고유 241 / 장비노드 37 / 깊이 2   (rtu·fcu·doas·mau 동일)
    vav = 노드  94 / leaf  83 / 고유  83                chiller = leaf 86 / 고유 86
    protos 를 가진 71개 root 를 전부 전개하면 leaf 합계 4,689 · gap 0 · 최대 깊이 3.
  고유가 241 아래로 떨어지면 ④가 깨진 것이고, leaf 가 급감하면 ⑤가 깨진 것이다.
  단 chilled-water-plant 처럼 계통 안에 같은 배관이 중첩되는 root 는 태그조합이 겹치는
  것이 정상이다(계통 자신의 냉수배관 vs 그 안 chiller 의 냉수배관 — 태그가 같고
  equipRef 만 다르다). --protos 가 '깊이 다름/깊이 같음' 으로 갈라 찍는다.

실행
  PYTHONIOENCODING=utf-8 python haystack.py --equips
  PYTHONIOENCODING=utf-8 python haystack.py --protos ahu
  PYTHONIOENCODING=utf-8 python haystack.py --protos rtu --flat
  PYTHONIOENCODING=utf-8 python haystack.py --diff e5
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DEFS = os.path.join(DATA, "haystack", "defs.json")
EQUIPS = os.path.join(DATA, "equips")
EQUIP_TEMPLATES = os.path.join(DATA, "equip-templates.json")

# 와일드카드 proto — '아무 equip/아무 point' 라는 뜻이라 구체 포인트가 아니다
WILDCARD = (frozenset({"equip"}), frozenset({"point"}))
MAX_DEPTH = 6          # 실측 최대 3(chilled-water-plant). 스냅샷 대비 여유
ROLES = ("sensor", "cmd", "sp")

# --diff 판정 문턱. 겹침 = Jaccard = |질의∩전개| / |질의∪전개|
# 이름으로는 못 맞춘다(한글 '급기온도' vs 태그 'discharge air temp sensor'). 태그 겹침만 본다.
# 문턱을 낮게 잡으면 조용히 틀린 짝이 '일치' 로 계상된다 — 실제로 0.6 에서
# '외기냉방 모드' 가 `cmd economizing point` 대신 `cmd damper economizer point`(외기댐퍼)
# 로 붙었다. 그래서 0.75 미만은 채택하지 않고 애매로 넘긴다.
HIT_EXACT = 0.999      # 태그집합이 완전히 같다      → 일치
HIT_TAKE = 0.75        # 단독 1등이면 채택           → 추정
HIT_WEAK = 0.6         # 여기까지만 후보로 보여 준다 → 애매(사람이 정한다)


# ── 원본 읽기 ────────────────────────────────────────────────────────────────

def sval(v):
    """Zinc 스칼라 → 문자열. {'_kind':'symbol','val':'ahu'} → 'ahu'"""
    return v["val"] if isinstance(v, dict) and "val" in v else v


def slist(v):
    """리스트로 오는 칸(is·children·childrenFlatten…)을 문자열 리스트로"""
    if v is None:
        return []
    if isinstance(v, list):
        return [sval(x) for x in v]
    return [sval(v)]


class Defs(object):
    """defs.json(Haystack Zinc grid 의 JSON 직렬화) 한 벌."""

    def __init__(self, grid):
        self.ver = (grid.get("meta") or {}).get("ver")
        self.by = {}
        for row in grid.get("rows") or []:
            self.by[sval(row.get("def"))] = row
        self._closure = {}
        self._children = {}

    def has(self, name):
        return name in self.by

    def doc(self, name, width=0):
        """def 설명 한 줄. 원문은 여러 줄이라 공백으로 접는다."""
        text = " ".join(((self.by.get(name) or {}).get("doc") or "").split())
        return text[:width] if width else text

    def parts(self, name):
        """결합 def 분해. 'fan-motor' → {fan, motor}. 조각이 전부 def 일 때만."""
        if "-" in name:
            bits = name.split("-")
            if all(b in self.by for b in bits):
                return set(bits)
        return {name}

    def closure(self, name):
        """상위형 전체(is 를 전이적으로 따라간다 — rtu → ahu → airHandlingEquip …).

        결합 def 는 조각도 상위형이다(fan-motor 는 fan 이면서 motor 다).
        defs.json 의 `is` 칸에는 조각 중 하나만 적히므로 여기서 보충한다.
        """
        if name in self._closure:
            return self._closure[name]
        # 재진입 가드. is 그래프에 순환은 실측 0건이지만, 스냅샷이 바뀌어 순환이
        # 생기면 무한재귀로 죽는 대신 여기서 끊는다.
        self._closure[name] = set()
        out = set()
        for sup in slist((self.by.get(name) or {}).get("is")):
            out.add(sup)
            out |= self.closure(sup)
        for part in self.parts(name):
            if part != name:
                out.add(part)
                out |= self.closure(part)
        self._closure[name] = out
        return out

    def isa(self, name, other):
        return name == other or other in self.closure(name)

    def own_protos(self, name):
        """그 def 에 직접 적힌 children (와일드카드 제외 전, 정렬만)"""
        row = self.by.get(name) or {}
        return [frozenset(c.keys()) for c in (row.get("children") or [])]

    def protos(self, name):
        """is 를 따라 children 합집합 (규칙 ①).

        ★ children 칸이 채워진 def 에서는 이 순회로 늘어나는 것이 없다(원본이 이미
          누적). 하지만 children 칸이 빈 def 6개(chiller-absorption·centrifugal·
          reciprocal·rotaryScrew, vav-parallel·vav-series)는 순회가 유일한 공급원이라
          빼면 전개가 0점이 된다. `inherited_extra()` 로 어느 쪽인지 본다.
        """
        if name in self._children:
            return self._children[name]
        seen, keys, out = set(), set(), []
        stack = [name]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            row = self.by.get(cur) or {}
            for tags in self.own_protos(cur):
                if tags in keys:
                    continue
                keys.add(tags)
                out.append(tags)
            stack.extend(slist(row.get("is")))
            stack.extend(p for p in self.parts(cur) if p != cur)
        out.sort(key=lambda t: tuple(sorted(t)))
        self._children[name] = out
        return out

    def inherited_extra(self, name):
        """is 순회로 **추가로** 얻은 proto 수.

        0 = 자기 children 칸에 상속이 이미 누적돼 있다(대부분). 0 이 아니면 자기 칸이
        비어 상위형에서 통째로 빌려온 것이다 — 순회를 지우면 그 def 는 0점이 된다.
        """
        own = set(self.own_protos(name))
        return len([t for t in self.protos(name) if t not in own])

    def carry(self, src, flat):
        """물려줄 aspect 마커를 고른다 (규칙 ④).

        1차: src 태그 중 flatten 목록의 choice 하위형인 것.
        2차: **결합 def 도 본다.** proto 태그는 마커가 낱개로 흩어져 있어서
             `{chilled, water}` 가 1차에서 `water`(is fluid)만 걸리고 `chilled`(is
             marker)는 떨어진다. 그러면 chiller 의 냉수배관과 냉각수배관이 둘 다
             'entering water' 가 돼 **한 점으로 뭉갠다**(실측: 고유 86→52).
             `chilled-water`·`condenser-water` 는 defs 에 실재하고 `is fluid` 이므로,
             조각이 전부 src 에 있으면 조각째 물려준다. 규칙 ③과 같은 분해다.

        ⚠ 2차에서 **장비형 결합 def 는 제외**한다. 안 그러면 `fan-motor`(parts
          {fan,motor}, is fan)가 걸려 `motor` 까지 자식에 밀려 들어가
          급기팬 포인트가 `discharge fan motor …` 이 된다. aspect 는 그 장비가 '어디에
          붙어 있나'를 나타내는 마커·현상이지 장비 자신이 아니다. 1차만으로 이미
          `fan` 은 걸리므로 2차에서 장비를 빼도 잃는 것이 없다.
        """
        out = set(t for t in src if any(self.isa(t, c) for c in flat))
        for name in self.by:
            bits = self.parts(name)
            if len(bits) <= 1 or not bits <= src or self.isa(name, "equip"):
                continue
            if any(self.isa(name, c) for c in flat):
                out |= bits
        return out

    def resolve(self, tags):
        """proto 태그집합 → def 이름. 못 찾으면 None.

        규칙 ③. 결합 def 를 조각으로 분해해 '조각이 전부 tags 에 들어 있는' 후보를
        모으고, 다른 후보의 상위형인 것을 버린 뒤(=최대 구체성) 조각 수 많은 쪽.
        """
        cand = [n for n in self.by if self.parts(n) <= tags]
        if "equip" in tags:
            # 장비 노드다 — 총칭 `equip` 자신은 답이 아니고, 장비형만 후보다
            cand = [n for n in cand if n != "equip" and self.isa(n, "equip")]
        else:
            cand = [n for n in cand if n != "point"]
        cand = [n for n in cand
                if not any(m != n and self.isa(m, n) for m in cand)]
        if not cand:
            return None
        cand.sort(key=lambda n: (-len(self.parts(n)), n))
        return cand[0]


def load_defs(path=DEFS):
    if not os.path.exists(path):
        raise SystemExit("defs.json 이 없다: %s" % path)
    with open(path, encoding="utf-8") as f:
        return Defs(json.load(f))


# ── 전개 ─────────────────────────────────────────────────────────────────────

class Node(object):
    """전개 트리의 한 칸. equip 이면 kids 를 갖고, point 면 leaf 다."""

    def __init__(self, kind, proto, carried, path, target=None, gap=None):
        self.kind = kind                       # 'equip' | 'point'
        self.proto = frozenset(proto)          # 원문 proto 태그 (그대로)
        self.carried = frozenset(carried)      # flatten 으로 물려받은 aspect
        self.tags = self.proto | self.carried  # 유효 태그
        self.path = list(path)                 # 조상 proto 표기들
        self.target = target                   # equip 일 때 되찾은 def 이름
        self.gap = gap                         # 못 정한 것의 사유
        self.kids = []

    @property
    def label(self):
        return " ".join(sorted(self.proto))

    @property
    def role(self):
        for r in ROLES:
            if r in self.tags:
                return r
        return ""


def _ident(root, path, tags):
    """경로 기반 안정키. ahu/discharge.duct.equip/air.point.sensor.temp"""
    segs = [root] + [".".join(sorted(p.split())) for p in path]
    segs.append(".".join(sorted(tags)))
    return "/".join(segs)


def expand(defs, root, max_depth=MAX_DEPTH):
    """root def 의 protos 를 재귀 전개해 트리(Node 리스트)를 만든다.

    반환: (kids, stats). stats 에 회귀 지표와 gap 이 들어간다.
    """
    stats = {"nodes": 0, "leaf": 0, "equipNodes": 0, "maxDepth": 0,
             "gaps": [], "inheritedExtra": 0}

    def walk(name, ctx, chain, path, depth):
        stats["maxDepth"] = max(stats["maxDepth"], depth)
        stats["inheritedExtra"] += defs.inherited_extra(name)
        out = []
        for tags in defs.protos(name):
            if tags in WILDCARD:              # 규칙 ②
                continue
            stats["nodes"] += 1
            if "equip" not in tags:
                stats["leaf"] += 1
                out.append(Node("point", tags, ctx, path))
                continue
            target = defs.resolve(tags)       # 규칙 ③
            if target is None:
                gap = "proto 태그집합에 맞는 def 를 못 찾음 — 전개 중단"
                out.append(Node("equip", tags, ctx, path, gap=gap))
                stats["gaps"].append((" ".join(sorted(tags)), gap))
                continue
            if target in chain or depth >= max_depth:   # 규칙 ⑤
                gap = ("순환(%s 가 경로에 이미 있다)" % target if target in chain
                       else "깊이 %d 초과" % max_depth)
                out.append(Node("equip", tags, ctx, path, target, gap))
                stats["gaps"].append((" ".join(sorted(tags)), gap))
                continue
            stats["equipNodes"] += 1
            node = Node("equip", tags, ctx, path, target)
            # 규칙 ④ — ctx 를 함께 넣어 전이적으로 물려준다
            flat = slist((defs.by.get(target) or {}).get("childrenFlatten"))
            carried = defs.carry(set(tags) | set(ctx), flat)
            node.kids = walk(target, carried, chain | {target},
                             path + [node.label], depth + 1)
            out.append(node)
        return out

    if not defs.has(root):
        raise SystemExit("defs 에 없는 def: %s" % root)
    kids = walk(root, set(), {root}, [], 0)
    return kids, stats


def leaves_of(kids):
    """전개 트리에서 leaf(point) 만 뽑는다."""
    out = []
    for n in kids:
        if n.kind == "point":
            out.append(n)
        else:
            out.extend(leaves_of(n.kids))
    return out


# ── 출력: --equips ───────────────────────────────────────────────────────────

def cmd_equips(defs):
    """protos 를 가진 def 목록. 와일드카드 2개를 뺀 '실질' 개수로 센다."""
    rows = []
    for name in defs.by:
        protos = defs.protos(name)
        if not protos:
            continue
        real = [t for t in protos if t not in WILDCARD]
        eq = len([t for t in real if "equip" in t])
        rows.append((name, len(protos), len(real), eq, len(real) - eq,
                     defs.inherited_extra(name)))
    rows.sort(key=lambda r: (-r[2], r[0]))
    empty = [r for r in rows if r[2] == 0]

    print("Haystack defs %d개 (ver %s) — protos 보유 def %d개"
          % (len(defs.by), defs.ver, len(rows)))
    print("  실질 protos 0개인 def %d개는 children 이 와일드카드 {equip}·{point} 뿐이다"
          % len(empty))
    print()
    print("  %-26s %6s %6s %6s %6s %6s" %
          ("def", "children", "실질", "장비", "포인트", "상속+"))
    print("  " + "-" * 62)
    for name, tot, real, eq, pt, extra in rows:
        if real == 0:
            continue
        print("  %-26s %6d %6d %6d %6d %6d" % (name, tot, real, eq, pt, extra))
    print()
    print("  '상속+' = is 를 따라가서 **추가로** 얻은 proto 수.")
    borrowed = [r for r in rows if r[5] and r[5] == r[1]]
    print("  0 = 자기 children 칸에 이미 상속이 누적돼 있다 (대부분이 이 경우다).")
    print("  children 칸이 통째로 비어 상위형에서 전부 빌려온 def %d개: %s"
          % (len(borrowed), ", ".join(r[0] for r in borrowed)))
    print("  → is 순회를 빼면 이 %d개는 전개 결과가 0점이 된다. 규칙 ① 참고." % len(borrowed))
    return 0


# ── 출력: --protos ───────────────────────────────────────────────────────────

def cmd_protos(defs, root, flat=False):
    kids, st = expand(defs, root)
    leaves = leaves_of(kids)
    uniq = len(set(n.tags for n in leaves))

    print("[%s] %s" % (root, defs.doc(root, 96)))
    sup = sorted(defs.closure(root))
    if sup:
        print("  상위형(is): %s   (전이 폐포 %d개)"
              % (" · ".join(slist(defs.by[root].get("is"))), len(sup)))
    print("  노드 %d · 포인트 leaf %d · 고유 태그조합 %d · 장비노드 %d · 깊이 %d"
          % (st["nodes"], st["leaf"], uniq, st["equipNodes"], st["maxDepth"]))
    if uniq < st["leaf"]:
        _collisions(leaves, st["leaf"] - uniq)
    print()

    if flat:
        print("  %-4s %-7s %-44s %s" % ("#", "역할", "태그(원문+물려받은 것)", "경로"))
        print("  " + "-" * 100)
        for i, n in enumerate(leaves, 1):
            print("  %-4d %-7s %-44s %s"
                  % (i, n.role or "—", " ".join(sorted(n.tags)),
                     " ▸ ".join(n.path) if n.path else "(설비 직속)"))
    else:
        _tree(kids, "  ")

    if st["gaps"]:
        print()
        print("  gap %d건 — 채우지 않고 남긴다" % len(st["gaps"]))
        for tags, why in st["gaps"]:
            print("    %-40s %s" % (tags, why))
    print()
    print("  자체 점검: is 순회로 추가된 proto %d개 %s"
          % (st["inheritedExtra"],
             "(자기 children 칸에 이미 누적돼 있다)" if not st["inheritedExtra"]
             else "(children 칸이 비어 상위형에서 빌려왔다 — 순회를 빼면 0점이 된다)"))
    print("  ⚠ 이 목록은 '가질 수 있는 것'의 완전열거다. 템플릿이 아니라 누락 점검용이다.")
    if defs.isa(root, "ahu") or root == "ahu":
        print("  ⚠ rtu·doas·mau·fcu 의 protos 는 ahu 와 글자 하나 다르지 않다."
              " RTU/AHU 구분 근거는 여기 없다.")
    return 0


def _collisions(leaves, dup):
    """태그조합이 겹치는 leaf 를 짚는다 — 원인이 둘이라 구별해야 한다.

    ① 규칙 ④(aspect 전이 누적)가 깨진 경우 — 급기/환기/배기 팬이 한 점으로 뭉갠다.
       ahu 는 leaf 241 = 고유 241 이 정상이므로 여기서 어긋나면 이쪽을 의심한다.
    ② 계층이 진짜 겹치는 경우 — chilled-water-plant 는 계통 자신의 `chilled entering
       pipe` 와 그 안 chiller 의 `chilled entering pipe` 가 **태그가 같다**.
       Haystack 에서 이 둘을 가르는 것은 태그가 아니라 equipRef(경로)다.
       → 전개물을 평면 리스트로 승격하면 이 구분이 사라진다. 경로를 함께 들고 가야 한다.
    """
    seen = {}
    same_tail, nested = 0, 0
    sample = []
    for n in leaves:
        prev = seen.get(n.tags)
        if prev is None:
            seen[n.tags] = n
            continue
        if len(prev.path) != len(n.path):
            nested += 1
        else:
            same_tail += 1
        if len(sample) < 2:
            sample.append((prev, n))
    print("  ⚠ 태그조합이 겹치는 leaf %d건 (깊이 다름 %d · 깊이 같음 %d)"
          % (dup, nested, same_tail))
    for a, b in sample:
        print("      %s" % " ".join(sorted(a.tags)))
        print("        ▸ %s" % (" ▸ ".join(a.path) or "(직속)"))
        print("        ▸ %s" % (" ▸ ".join(b.path) or "(직속)"))
    if same_tail:
        print("      ↑ '깊이 같음' 이 있으면 aspect 전이 누적(규칙 ④)을 먼저 의심하라."
              " ahu 는 leaf 241 = 고유 241 이 정상이다.")
    if nested:
        print("      ↑ '깊이 다름' 은 계층이 겹치는 것이다 — 태그로는 못 가른다."
              " 평면 목록으로 쓰면 구분이 사라지니 경로를 같이 들고 가야 한다.")


def _tree(kids, pad):
    last = len(kids) - 1
    for i, n in enumerate(kids):
        mark = "└─" if i == last else "├─"
        extra = ""
        if n.carried:
            extra = "   ← %s" % " ".join(sorted(n.carried))
        if n.kind == "equip":
            head = "%s%s %s  ⇒ %s%s" % (pad, mark, n.label, n.target or "?", extra)
            if n.gap:
                head += "   [gap: %s]" % n.gap
            print(head)
            _tree(n.kids, pad + ("   " if i == last else "│  "))
        else:
            print("%s%s %-38s %-7s %s" % (pad, mark, n.label, n.role or "—",
                                          extra.strip()))


# ── 출력: --diff ─────────────────────────────────────────────────────────────

TOKEN = re.compile(r"`([^`]+)`")
HEADER = ["포인트", "종류", "단위", "역할", "태그 조합", "등급"]


def load_equip(equip_id):
    path = os.path.join(EQUIPS, "%s.json" % equip_id)
    if not os.path.exists(path):
        raise SystemExit("설비 정의가 없다: %s" % path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def equip_root(defs, equip):
    """tagSummary 의 첫 백틱 토큰 중 protos 를 가진 def 를 root 로 본다.

    하드코딩하지 않는 이유: e5 → ahu 를 코드에 박으면 다른 계열에서 또 손으로 정해야
    한다. tagSummary 는 이미 대표 태그를 맨 앞에 적고 있다(e5 = '`ahu` ✓ ← 부모 …').
    """
    for tok in TOKEN.findall(equip.get("tagSummary") or ""):
        name = tok.strip()
        if defs.has(name) and [t for t in defs.protos(name) if t not in WILDCARD]:
            return name
    return None


def load_template_profiles():
    if not os.path.exists(EQUIP_TEMPLATES):
        return {}
    with open(EQUIP_TEMPLATES, encoding="utf-8") as f:
        return (json.load(f).get("profiles") or {})


def template_rows(equip_id, equip):
    """대조할 템플릿 행.

    하위형식 프로파일(data/equip-templates.json)이 있으면 그것이 정본이다. 없을 때만
    옛 data/equips/*.json pointTables 를 읽는다.
    """
    profiles = load_template_profiles()
    prof_rows = []
    for pid, prof in sorted(profiles.items()):
        if prof.get("equipId") != equip_id:
            continue
        for row in prof.get("templatePoints") or []:
            prof_rows.append({
                "name": "%s/%s" % (pid, row.get("name")),
                "objectType": row.get("objectType"),
                "unit": row.get("unit"),
                "role": row.get("role"),
                "tagCell": row.get("tags") or "",
                "grade": row.get("grade"),
            })
    if prof_rows:
        return prof_rows

    # pointTables 6열 → dict. 열 구성이 다르면 그대로 알린다(억지로 맞추지 않는다).
    out = []
    for table in equip.get("pointTables") or []:
        head = table.get("header") or []
        if head[:6] != HEADER:
            print("  ⚠ 6열 계약과 다른 표를 건너뛴다: %s" % head)
            continue
        for row in table.get("rows") or []:
            out.append({"name": row[0], "objectType": row[1], "unit": row[2],
                        "role": row[3], "tagCell": row[4], "grade": row[5]})
    return out


def query_tags(defs, row):
    """템플릿 한 행 → (질의 태그집합, 미지 토큰 리스트).

    백틱 토큰에서 ✓/★ 를 떼고, 결합 표기는 '-' 로 분해해 def 인 조각만 쓴다.
    분해해도 def 가 아닌 것은 **채우지 않고** 미지로 남긴다(예: `position` — Haystack
    에 position 이라는 def 는 없다. 개도 % 는 우리 관행이다).
    """
    known, unknown = set(), []
    for tok in TOKEN.findall(row["tagCell"] or ""):
        name = tok.strip().strip("✓★").strip()
        if not name:
            continue
        if defs.has(name):
            known |= set(defs.parts(name))
            continue
        bits = [b for b in name.split("-") if b]
        good = [b for b in bits if defs.has(b)]
        if good:
            known |= set(good)
        unknown.append((name, good, [b for b in bits if not defs.has(b)]))
    # `equip` 은 상위 장비를 가리키는 마커라 leaf 태그에 없다 — 질의에서 뺀다
    known.discard("equip")
    if row["role"] in ROLES:
        known.add(row["role"])
    known.add("point")
    return known, unknown


def score(query, tags):
    if not query or not tags:
        return 0.0
    return len(query & tags) / float(len(query | tags))


def cmd_diff(defs, equip_id, limit=24):
    equip = load_equip(equip_id)
    root = equip_root(defs, equip)
    if root is None:
        raise SystemExit("tagSummary 에서 protos 를 가진 def 를 못 찾았다 — root 미상")
    kids, st = expand(defs, root)
    leaves = leaves_of(kids)
    rows = template_rows(equip_id, equip)

    print("[대조] %s %s  ←  Haystack root `%s`" % (equip_id, equip.get("title"), root))
    print("  전개 leaf %d개 (고유 %d) · 템플릿 %d행"
          % (len(leaves), len(set(n.tags for n in leaves)), len(rows)))
    print("  등급(필수/권장/선택)은 대조하지 않는다 — Haystack 에 근거가 없다.")
    print()

    hits, vague, only_ours = [], [], []
    claimed = set()
    for row in rows:
        query, unknown = query_tags(defs, row)
        if len(query - {"point"} - set(ROLES)) == 0:
            only_ours.append((row, unknown,
                              "태그 조합 칸에 Haystack 태그가 없다 — 대조 불가", None, 0))
            continue
        ranked = sorted(((score(query, n.tags), n) for n in leaves),
                        key=lambda x: (-x[0], sorted(x[1].tags)))
        best = ranked[0][0]
        tied = [n for s, n in ranked if s >= best - 1e-9]
        if best < HIT_WEAK:
            only_ours.append((row, unknown,
                              "태그 겹침 최대 %.2f — 표준에서 짝을 못 찾았다" % best,
                              ranked[0][1], best))
            continue
        if best < HIT_TAKE or len(tied) > 1:
            vague.append((row, unknown, best, tied))
            continue
        node = tied[0]
        claimed.add(node.tags)
        hits.append((row, unknown, best, node))

    print("■ 표준에도 있음 — %d행" % len(hits))
    for row, unknown, s, node in hits:
        print("  %-16s %s %.2f  %s"
              % (row["name"], "일치" if s >= HIT_EXACT else "추정", s,
                 _ident(root, node.path, node.tags)))
    if not hits:
        print("  (없음)")

    print()
    print("■ 애매 — 사람이 정해야 한다 — %d행" % len(vague))
    print("  억지로 붙이지 않는다. 후보를 그대로 보여 주고 판단을 넘긴다.")
    for row, unknown, s, tied in vague:
        why = "동점 %d개" % len(tied) if len(tied) > 1 else "겹침이 약하다"
        print("  %-16s %s (겹침 %.2f)" % (row["name"], why, s))
        for node in tied[:4]:
            print("      %s%s" % (" ".join(sorted(node.tags)),
                                  "   ▸ " + " ▸ ".join(node.path) if node.path else ""))
        if len(tied) > 4:
            print("      … 외 %d개" % (len(tied) - 4))
        if len(tied) > 1 and len(set(n.proto for n in tied)) == 1:
            print("      ↑ proto 는 하나인데 붙는 위치(덕트)가 여럿이다."
                  " 템플릿에 위치 태그가 없어서 못 고른다.")
        _blame(unknown)
    if not vague:
        print("  (없음)")

    print()
    print("■ 우리에만 있음 — 표준 근거를 따로 대야 한다 — %d행" % len(only_ours))
    for row, unknown, why, near, s in only_ours:
        print("  %-16s %s" % (row["name"], why))
        if near is not None:
            print("      가장 가까운 것(채택 안 함): %s   겹침 %.2f"
                  % (" ".join(sorted(near.tags)), s))
        _blame(unknown)
    if not only_ours:
        print("  (없음)")

    rest = [n for n in leaves if n.tags not in claimed]
    print()
    print("■ 표준에만 있음 — 누락 점검 후보 — %d개 (상위 %d개만 표시)"
          % (len(rest), min(limit, len(rest))))
    print("  ⚠ 이건 '추가하라'는 목록이 아니다. protos 는 조합적 완전열거라서"
          " 실물에 없는 것이 섞여 있다(economizer 덕트의 냉수코일 등).")
    direct = [n for n in rest if not n.path]
    if direct:
        print("  · 설비 직속 %d개 — 여기부터 본다" % len(direct))
        for n in direct:
            print("      %-40s %-7s %s" % (" ".join(sorted(n.proto)), n.role or "—",
                                           defs_doc_for(defs, n)))
    others = [n for n in rest if n.path]
    shown = 0
    for n in others:
        if shown >= limit:
            break
        print("      %-40s %-7s ▸ %s" % (" ".join(sorted(n.tags)), n.role or "—",
                                         " ▸ ".join(n.path)))
        shown += 1
    if len(others) > shown:
        print("      … 하위 장비 경유 %d개 더 있다 (--limit 로 늘린다)"
              % (len(others) - shown))

    bad = {}
    for row in rows:
        _, unknown = query_tags(defs, row)
        for name, good, missing in unknown:
            bad.setdefault(name, (good, missing))
    print()
    print("■ defs 에 없는 태그 토큰 — %d종" % len(bad))
    print("  템플릿에 ✓ 가 붙어 있어도 Haystack def 가 아니다. 표기 교정 대상.")
    for name in sorted(bad):
        good, missing = bad[name]
        if good and not missing:
            note = "→ `%s` 로 나눠 적으면 전부 def 다" % "` `".join(good)
        elif good:
            note = "→ %s 는 def, %s 는 def 아님" % ("·".join(good), "·".join(missing))
        else:
            note = "→ def 없음. 우리 관행이면 gap 에 사유를 적어야 한다"
        print("  %-22s %s" % (name, note))
    if not bad:
        print("  (없음)")

    print()
    print("  ⚠ RTU/AHU 를 이 결과로 가를 수 없다 — rtu.children 은 ahu.children 과 동일하다.")
    print("  ⚠ 등급은 여기서 나오지 않는다 — Haystack `mandatory` 는 태그 공존 규칙이다.")
    return 0


def _blame(unknown):
    """짝을 못 찾은 이유가 대개 '태그 표기가 Haystack 이 아니라서' 다 — 그걸 짚어 준다."""
    if not unknown:
        return
    print("      원인 후보: defs 에 없는 토큰 %s"
          % ", ".join("`%s`" % n for n, _, _ in unknown))


def defs_doc_for(defs, node):
    """leaf 를 대표하는 def 의 doc 한 줄. 못 찾으면 빈 문자열.

    `point`·역할(sensor/cmd/sp)을 빼고 고른다. 안 빼면 `cmd cool point` 가 전부
    cmd 의 doc("Point is a command, actuator, AO/BO")로 나와 아무 정보가 없다.
    """
    name = defs.resolve(node.proto - {"point"} - set(ROLES))
    return defs.doc(name, 54) if name else ""


# ── 진입점 ───────────────────────────────────────────────────────────────────

def main(argv):
    ap = argparse.ArgumentParser(description="Haystack protos 전개·대조")
    ap.add_argument("--equips", action="store_true",
                    help="protos 를 가진 def 목록")
    ap.add_argument("--protos", metavar="DEF",
                    help="한 설비의 protos 를 전개해 트리로 출력")
    ap.add_argument("--flat", action="store_true",
                    help="--protos 결과를 평면 목록으로")
    ap.add_argument("--diff", metavar="EQUIP",
                    help="우리 templatePoints 와 대조 (예: e5)")
    ap.add_argument("--limit", type=int, default=24,
                    help="--diff 의 '표준에만 있음' 표시 개수 (기본 24)")
    a = ap.parse_args(argv)

    defs = load_defs()
    if a.equips:
        return cmd_equips(defs)
    if a.protos:
        return cmd_protos(defs, a.protos, a.flat)
    if a.diff:
        return cmd_diff(defs, a.diff, a.limit)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
