# -*- coding: utf-8 -*-
"""검증 게이트 — 자동 추출 결과를 사람이 보기 전에 거른다.

만든 이유: Trane 공조기 추출 때 결과의 90%가 '그럴듯해' 보였지만 이름이 엉뚱한
인스턴스에 붙어 있었다. 알려진 정답과 대조해서 겨우 잡았다. 수백 건을 눈으로 볼 수
없으므로 그 대조를 기계가 한다.

검사 항목
  E  (오류)  — 적재 차단
  W  (경고)  — 적재하되 검수 큐로
  I  (정보)  — 기록만

실행:  python validate.py [--model <id>] [--json]
"""
import json, os, re, sys, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import schema as S  # noqa: E402

# 이름에 섞이면 안 되는 조각 — 표 옆 칸이 흘러들어온 흔적.
# 'Present' 단독은 뺐다. 'Alarm Present'·'Diagnostic Present'는 진짜 포인트 이름이라
# 가짜 경보만 만들었다. 옆 칸이 흘러들면 이름 안에 **문장**이 생기므로 그쪽을 본다.
BLEED = re.compile(
    r"\b(Indicates|Read/Write|All RAUK Units|Type Address|"
    r"Configuration Dependency|Object Name|Object Identifier|mandatory|optional)\b", re.I)
# 이름이 아니라 값·단위만 남은 경우
VALUEONLY = re.compile(r"^[\d\.\-\*/,%°\s]+$")


def load_all():
    eq = {}
    for f in glob.glob(os.path.join(DATA, "equips", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        eq[d["id"]] = d
    md = []
    for f in glob.glob(os.path.join(DATA, "models", "*.json")):
        md.append(json.load(open(f, encoding="utf-8")))
    docs = json.load(open(os.path.join(DATA, "docs.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(DATA, "docs.json")) else []
    kg_path = os.path.join(DATA, "known-good.json")
    kg = json.load(open(kg_path, encoding="utf-8")) if os.path.exists(kg_path) else {}
    return eq, md, docs, kg


def check_model(m, eq, kg):
    """모델 1건 검사 → [(등급, 코드, 메시지)]"""
    out = []
    add = lambda lv, code, msg: out.append((lv, code, msg))

    for k in S.REQUIRED_MODEL:
        if not m.get(k):
            add("E", "required", "필수 항목 없음: %s" % k)
    if m.get("equipId") not in eq:
        add("E", "orphan", "장비 계열 %s 이 존재하지 않음" % m.get("equipId"))

    pts = m.get("points", [])
    # 1) 인스턴스 중복 — 같은 (타입, 인스턴스)가 두 번
    dup = [k for k, n in collections.Counter(
        (p["type"], p.get("inst")) for p in pts).items() if n > 1]
    if dup:
        add("E", "dup-instance", "인스턴스 중복 %d건 예: %s" % (len(dup), dup[:3]))

    # 2) 오브젝트 타입이 표준 밖
    bad = sorted({p["type"] for p in pts if p["type"] not in S.OBJ_TYPES})
    if bad:
        add("E", "bad-type", "표준 밖 오브젝트 타입: %s" % ", ".join(bad))

    # 3) 단위 정규화 실패
    unk = collections.Counter(p["unitRaw"] for p in pts
                              if S.unit_state(p.get("unitRaw")) == "unknown")
    if unk:
        add("W", "unit-unknown", "정규화 안 된 단위 %d종: %s"
            % (len(unk), ", ".join("%s×%d" % (u, n) for u, n in unk.most_common(5))))
    grp = sum(1 for p in pts if S.unit_state(p.get("unitRaw")) == "group")
    if grp:
        add("I", "unit-group", "%d점은 문서가 단위 그룹명만 적었다 — 실제 단위는 미상" % grp)

    # 4) 이름에 옆 칸이 흘러든 흔적 (추출 오류의 대표 징후)
    bleed = [p for p in pts if BLEED.search(p.get("name", ""))]
    if bleed:
        lv = "E" if len(bleed) > len(pts) * 0.1 else "W"
        add(lv, "name-bleed", "이름에 설명·머리글 조각 섞임 %d/%d건 예: %r"
            % (len(bleed), len(pts), bleed[0]["name"][:50]))

    # 5) 이름이 값만 남았거나 너무 짧음
    junk = [p for p in pts if VALUEONLY.match(p.get("name", "")) or len(p.get("name", "")) < 3]
    if junk:
        add("W", "name-junk", "이름이 비정상 %d건 예: %r" % (len(junk), junk[0].get("name")))

    # 5b) 이름이 오브젝트 ID 를 되풀이한 것뿐 — 문서가 이름을 안 준 경우다
    idonly = [p for p in pts if re.fullmatch(
        r"%s[\s:_-]*%s" % (p["type"], p.get("inst")), (p.get("name") or "").strip(), re.I)]
    if idonly:
        add("I", "name-is-id", "%d점은 이름이 ID 반복 — 문서가 이름을 주지 않았다" % len(idonly))

    # 6) 이름 중복 과다 — 같은 이름이 여러 인스턴스에 (열 밀림의 징후)
    nm = collections.Counter(p.get("name", "").strip().lower() for p in pts if p.get("name"))
    rep = [(n, c) for n, c in nm.most_common(3) if c >= 3]
    if rep:
        add("W", "name-repeat", "같은 이름이 여러 인스턴스에: %s"
            % ", ".join("%r×%d" % (n[:28], c) for n, c in rep))

    # 7) 교차 대조 ★ 정답셋을 사람이 못 따라갈 때의 자동 방어선
    #    표 인식과 다른 경로(줄 읽기)로 원문을 한 번 더 읽어 비교한 결과를 쓴다.
    xc = m.get("crosscheck")
    if xc and xc.get("unverifiable"):
        add("W", "crosscheck-unverifiable", xc["unverifiable"])
    elif xc:
        rate, n = xc.get("rate", 0), xc.get("both", 0)
        if n < len(pts) * 0.5:
            add("W", "crosscheck-thin", "교차 대조가 %d/%d점만 덮음 — 나머지는 한 경로로만 읽었다"
                % (n, len(pts)))
        if n == 0:
            # 대조된 포인트가 0건이면 '틀렸다'가 아니라 '확인 못 했다'이다.
            add("W", "crosscheck-none", "교차 대조가 한 점도 못 덮었다 — 다른 경로로 읽히지 않는 문서")
        elif rate < 0.98:
            add("E", "crosscheck", "교차 대조 일치율 %.1f%% (%d점 불일치) — 예: %s"
                % (rate * 100, len(xc.get("diff", [])),
                   (xc.get("diff") or [["", "", "", ""]])[0][-2:]))
        elif n:
            add("I", "crosscheck-ok", "교차 대조 %d점 일치율 %.1f%%" % (n, rate * 100))
    elif pts and m.get("extractor") != "manual":
        add("W", "no-crosscheck", "교차 대조 없음 — 원문을 한 경로로만 읽었다")

    # 8) 알려진 정답 대조 ★ 사람이 확인한 표본
    exp = kg.get(m["id"])
    if exp:
        idx = {(p["type"], p.get("inst")): p.get("name", "") for p in pts}
        miss, wrong = [], []
        for key, want in exp.items():
            t, i = key.split("-")
            got = idx.get((t, int(i)))
            if got is None:
                miss.append(key)
            elif want.lower() not in got.lower():
                wrong.append("%s: 기대 %r ≠ 실제 %r" % (key, want[:34], got[:34]))
        if wrong:
            add("E", "known-good", "정답 대조 불일치 %d건 — %s" % (len(wrong), wrong[0]))
        if miss:
            add("W", "known-good-missing", "정답에 있는 포인트 없음: %s" % ", ".join(miss[:4]))
        if not wrong and not miss:
            add("I", "known-good-ok", "정답 대조 %d건 전부 일치" % len(exp))
    elif not xc:
        add("W", "no-known-good", "정답 대조셋도 교차 대조도 없음 — 정확도를 확인할 방법이 없다")

    # 9) 근거 문서
    if not m.get("gap") and not m.get("has", {}).get("spec"):
        add("I", "no-gap-note", "미확보 항목 설명(gap) 없음")
    if pts and m.get("extractor") == "manual":
        add("I", "manual", "수기 입력 — 재현 불가")
    return out


def main(argv):
    eq, md, docs, kg = load_all()
    only = None
    if "--model" in argv:
        only = argv[argv.index("--model") + 1]
    rows, tally = [], collections.Counter()
    for m in sorted(md, key=lambda x: x["id"]):
        if only and m["id"] != only:
            continue
        res = check_model(m, eq, kg)
        for lv, code, msg in res:
            tally[lv] += 1
            rows.append({"model": m["id"], "level": lv, "code": code, "message": msg})

    if "--json" in argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 1 if tally["E"] else 0

    cur = None
    for r in rows:
        if r["model"] != cur:
            cur = r["model"]
            m = [x for x in md if x["id"] == cur][0]
            print("\n■ %s  (%s · 포인트 %d)" % (cur, m["vendor"], len(m["points"])))
        mark = {"E": "✗ 오류", "W": "△ 경고", "I": "· 정보"}[r["level"]]
        print("   %s [%s] %s" % (mark, r["code"], r["message"]))
    print("\n" + "─" * 72)
    print("모델 %d건 검사 — 오류 %d · 경고 %d · 정보 %d"
          % (len(md) if not only else 1, tally["E"], tally["W"], tally["I"]))
    if tally["E"]:
        print("→ 오류가 있는 모델은 적재하지 않는다.")
    return 1 if tally["E"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
