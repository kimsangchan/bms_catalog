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
import extract as X  # noqa: E402 — 단위 칸 모양 가드(unit_or_note) 재사용

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

    # 3a) 단위 칸 문장·범위 침입 — 표 각주(Lennox 'These legacy alarm …')나
    #     범위+기본값(Daikin '-40 – 230°F … Default: NA')이 단위로 눌린 것.
    #     추출 가드(extract.unit_or_note)가 비고로 옮기므로 남아 있으면 결함이다.
    prose = [p for p in pts if X.unit_or_note(p.get("unitRaw") or "")[1]]
    if prose:
        add("E", "unit-prose", "단위 칸에 문장/범위 %d건 예: %s = %r"
            % (len(prose), prose[0].get("name", "")[:24], (prose[0].get("unitRaw") or "")[:40]))

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
    if not n_points(m):
        pass          # 포인트가 없는 모델(별칭)은 대조할 것이 아예 없다 — 물을 일이 아니다
    elif xc and xc.get("unverifiable"):
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
    elif not xc and n_points(m):
        add("W", "no-known-good", "정답 대조셋도 교차 대조도 없음 — 정확도를 확인할 방법이 없다")

    # 9) 정격 사양 — 시뮬레이터가 쓰려면 통신 맵만으로는 부족하다
    st = m.get("specTables") or []
    vr = m.get("variants") or []
    # 형번이 하나인 장치는 행렬 표도 형번별 목록도 아니라 '항목/값' 한 벌이다
    # (게이트웨이·계측기). 이걸 안 세다가 사양을 넣어 둔 모델에 '사양 없음' 이 떴다.
    sp = m.get("spec") or []
    if st or vr or sp:
        qs = sorted({q for t in st for q in (t.get("quantities") or []) if q})
        if sp:
            units = {r[2] for r in sp if len(r) > 2 and r[2] and r[2] != "—"}
            qs = sorted((set(qs) | {S.quantity_of_unit(u) for u in units}) - {None})
            add("I", "spec-flat", "사양 항목 %d건 (항목/값)" % len(sp))
        if vr:
            # 형번별 사양은 항목/값 목록이라 물리량을 단위에서 읽는다
            units = {r[2] for v in vr for r in v.get("spec", []) if r[2] and r[2] != "—"}
            qs = sorted(set(qs) | {S.quantity_of_unit(u) for u in units} - {None})
            add("I", "spec-variants", "형번 %d개 · 항목 %d건"
                % (len(vr), sum(len(v.get("spec", [])) for v in vr)))
        if st:
            add("I", "spec-ok", "사양 표 %d개 (%d행)"
                % (len(st), sum(len(t.get("rows", [])) for t in st)))
        core = {"power", "current", "voltage", "capacity"}
        if not (core & set(qs)):
            add("W", "spec-nocore", "전력·전류·전압·용량이 없다 — 시뮬레이터에 쓸 값이 아니다")
        else:
            add("I", "spec-core", "시뮬레이터용 물리량 확보: %s"
                % ", ".join(sorted(core & set(qs))))
    elif pts:
        add("W", "no-spec", "정격 사양 없음 — 통신 맵만 있다 (카탈로그·데이터시트 필요)")

    # 10) 근거 문서
    if not m.get("gap") and not m.get("has", {}).get("spec"):
        add("I", "no-gap-note", "미확보 항목 설명(gap) 없음")
    if pts and m.get("extractor") == "manual":
        add("I", "manual", "수기 입력 — 재현 불가")

    # 11) 형번 확정 데이터셋 — 추출은 제안, data/units/ 골든 레코드가 정본.
    #     화면은 확정본만 읽으므로 누락·스키마 위반은 오류(E), 미동기는 경고(W)다.
    check_curated_units(m, add)
    # 12) 인터페이스(포인트 리스트 리비전) — point-schema.json 이 정본
    check_interfaces(m, add)
    return out


PSCHEMA = None


def point_schema():
    global PSCHEMA
    if PSCHEMA is None:
        with open(os.path.join(DATA, "point-schema.json"), encoding="utf-8") as f:
            PSCHEMA = json.load(f)
    return PSCHEMA


def n_points(m):
    """모델의 포인트 수 — 옛 평면과 새 인터페이스 양쪽을 센다."""
    return (len(m.get("points") or [])
            + sum(len(i.get("points") or []) for i in (m.get("interfaces") or [])))


def check_interfaces(m, add):
    """인터페이스(포인트 리스트 리비전) 검사 — point-schema.json 이 정본이다.

    왜 옛 포인트와 따로 보나
      평면 points[] 는 사전이 없던 시절의 추출본이다(24,423점). 사전 게이트를
      거기까지 소급하면 전 모델이 오류로 뒤덮여 게이트가 쓸모없어진다. 그래서
      **새로 취입하는 interfaces[].points[] 에만** 사전 우선 규칙을 강제하고,
      옛 것은 '아직 안 옮겼다'를 정보로 남겨 보이게만 한다. 옛 데이터를 조용히
      통과시키는 것이 아니라 세어서 표면화한다 — 남은 이관 분량이 곧 그 숫자다.
    """
    sch = point_schema()
    ifs = m.get("interfaces") or []
    legacy = m.get("points") or []
    if not ifs:
        if legacy:
            add("I", "points-legacy",
                "평면 %d점 — 인터페이스로 아직 안 갈랐다(옛 추출본)" % len(legacy))
        return
    if legacy:
        # 두 모양이 한 모델에 있으면 어느 쪽이 정본인지 알 수 없다
        add("E", "iface-mixed",
            "평면 points[] %d점과 interfaces[] 가 함께 있다 — 한 모양으로 모아야 한다"
            % len(legacy))

    fields = sch["interfaces"]["fields"]
    families = set(sch["provenance"]["family"]["values"])
    blocks = set(sch["blocks"])
    common_ok = set(sch["common"])
    prov_ok = set(sch["provenance"])
    statuses = set(sch.get("statuses") or ())
    vs = sch["rules"]["valueShape"]

    seen = set()
    for it in ifs:
        iid = it.get("id") or "?"
        for k in ("id", "label", "sourceFile"):
            if not it.get(k):
                add("E", "iface-required", "%s: 인터페이스 필수 항목 없음 — %s" % (iid, k))
        if iid in seen:
            add("E", "iface-dup-id", "인터페이스 ID 중복: %s" % iid)
        seen.add(iid)
        for k in it:
            if k not in fields and k != "points":
                add("E", "iface-field", "%s: 사전에 없는 인터페이스 필드 %r" % (iid, k))
        if it.get("family") and it["family"] not in families:
            add("E", "iface-family", "%s: 정의 밖 문서 계통 %r" % (iid, it["family"]))
        badp = [p for p in (it.get("protocols") or []) if p not in blocks]
        if badp:
            add("E", "iface-protocol", "%s: 사전에 없는 프로토콜 블록 %s" % (iid, ", ".join(badp)))
        if it.get("status") and it["status"] not in statuses:
            add("E", "iface-status", "%s: 정의 밖 상태 %r" % (iid, it["status"]))

        pts = it.get("points") or []
        if it.get("pointCount") is not None and it["pointCount"] != len(pts):
            add("E", "iface-count", "%s: pointCount %s ≠ 실제 %d점"
                % (iid, it["pointCount"], len(pts)))
        if not pts:
            add("W", "iface-empty", "%s: 포인트가 없다" % iid)

        # 사전 우선 — 레코드의 모든 키가 사전에 정의된 경로여야 한다
        bad, shape_bad, orphan, blkuse = (collections.Counter(), collections.Counter(),
                                          0, collections.Counter())
        longname, outrange = [], []
        for p in pts:
            for top in p:
                if top not in ("common", "blocks", "provenance"):
                    bad["최상위 %s" % top] += 1
            common = p.get("common") or {}
            for k in common:
                if k not in common_ok:
                    bad["common.%s" % k] += 1
            alt_names = common.get("altNames")
            if alt_names is not None and (not isinstance(alt_names, list) or
                                          not all(isinstance(x, str) and x for x in alt_names)):
                shape_bad["common.altNames"] += 1
            states = common.get("states")
            if states is not None and (not isinstance(states, list) or not all(
                    isinstance(x, dict) and isinstance(x.get("code"), str) and
                    isinstance(x.get("label"), str) and bool(x.get("label")) for x in states)):
                shape_bad["common.states"] += 1
            for k in (p.get("provenance") or {}):
                if k not in prov_ok:
                    bad["provenance.%s" % k] += 1
            for b, f in (p.get("blocks") or {}).items():
                blkuse[b] += 1
                if b not in blocks:
                    bad["blocks.%s" % b] += 1
                    continue
                known = set((sch["blocks"][b].get("fields") or {}))
                for k in f:
                    if k not in known:
                        bad["%s.%s" % (b, k)] += 1
            pv = p.get("provenance") or {}
            if pv.get("interfaceId") not in (None, iid):
                orphan += 1
            nm = (p.get("common") or {}).get("name") or ""
            if len(nm) > vs["nameMaxLen"]:
                longname.append(nm)
            inst = ((p.get("blocks") or {}).get("bacnet") or {}).get("instance")
            lo, hi = vs["bacnetInstanceRange"]
            if isinstance(inst, int) and not (lo <= inst <= hi):
                outrange.append(inst)
        if bad:
            add("E", "point-field", "%s: 사전 밖 필드 %d종 — %s"
                % (iid, len(bad), ", ".join("%s×%d" % kv for kv in bad.most_common(3))))
        if shape_bad:
            add("E", "point-shape", "%s: 값 모양이 사전과 다른 필드 — %s"
                % (iid, ", ".join("%s×%d" % kv for kv in shape_bad.most_common())))
        if orphan:
            add("E", "point-orphan", "%s: 다른 인터페이스를 가리키는 포인트 %d점" % (iid, orphan))
        if outrange:
            add("E", "point-instance", "%s: BACnet 인스턴스 범위 밖 %d점 예: %s"
                % (iid, len(outrange), outrange[0]))
        if longname:
            add("W", "point-longname", "%s: 이름 %d자 초과 %d점 — 설명 문단이 눌러붙었는지 확인: %r"
                % (iid, vs["nameMaxLen"], len(longname), longname[0][:48]))
        # 문서가 준 프로토콜과 실제로 값이 있는 블록이 어긋나면 둘 중 하나가 틀렸다
        declared = set(it.get("protocols") or [])
        if declared and set(blkuse) - declared:
            add("W", "iface-protocol-undeclared", "%s: 선언에 없는 블록에 값이 있다 — %s"
                % (iid, ", ".join(sorted(set(blkuse) - declared))))
        # 제외 행은 조용히 빼지 않는다 — 사유와 함께 남긴다
        ex = it.get("excluded") or {}
        if ex:
            add("I", "iface-excluded", "%s: 포인트로 세지 않은 행 %s"
                % (iid, ", ".join("%s %d행" % (k, v) for k, v in ex.items())))
        add("I", "iface-ok", "%s: %s · %d점 (%s)"
            % (iid, it.get("family") or "계통 미상", len(pts),
               ", ".join(it.get("protocols") or ["프로토콜 미상"])))


def check_curated_units(m, add):
    import datasets as DS
    import units as U

    schema = U.load_schema()
    ids = set(U.field_ids(schema))
    statuses = set(schema.get("statuses") or ())
    classes = schema.get("classes") or {}
    proposals = U.extraction_records(m, schema)
    # 스키마 우선 규칙 — 형번이 나오는 설비는 클래스(열 구성·라벨·역할)가 사전에
    # 정의돼 있어야 한다. 없으면 sync 가 거부하므로 여기서 원인을 알려 준다.
    if proposals and m.get("equipId") not in classes:
        add("E", "units-class",
            "설비 %s 의 스키마 클래스 미정의 — units.py --propose-class %s 초안으로 "
            "unit-schema.json classes 에 먼저 정의" % (m.get("equipId"), m.get("equipId")))
        return
    if m.get("equipId") not in classes:
        # 클래스 밖 설비 — 정격표·형번별 사양(variants)이 있으면 편입 후보로 표면화
        rating = sum(1 for t in m.get("specTables") or []
                     if (t.get("kind") or "") == "rating")
        if rating or m.get("variants"):
            add("I", "units-unclassed",
                "클래스 밖 설비(%s)에 정격표 %d개·variants %d개 — 형번 편입 후보"
                % (m.get("equipId"), rating, len(m.get("variants") or [])))
        return
    path = U.unit_path(m["id"])
    if not os.path.exists(path):
        if proposals:
            add("E", "units-missing",
                "형번 추출 제안 %d건인데 확정 데이터셋(data/units)이 없다 — units.py --sync"
                % len(proposals))
        else:
            # 클래스 설비인데 문서에서 형번이 안 나온다 — 사유(gap)가 적혀 있어야 한다
            gap = m.get("gap") or ""
            if any(w in gap for w in ("형번", "정격", "카탈로그")):
                add("I", "units-none", "형번 없음 — 문서 한계가 gap 에 기록돼 있다")
            else:
                add("W", "units-none-undoc",
                    "클래스 설비인데 형번이 없고 gap 에 사유도 없다 — 문서 한계인지 확인")
        return
    doc = json.load(open(path, encoding="utf-8"))
    curated = doc.get("units") or []
    bad_field, blob, no_src = [], [], []
    for rec in curated:
        code = rec.get("unitModelNumber") or "?"
        if (rec.get("status") or "extracted") not in statuses:
            add("E", "units-status", "%s: 정의 밖 상태 %r" % (code, rec.get("status")))
        for fid, entry in (rec.get("fields") or {}).items():
            if fid not in ids:
                bad_field.append("%s.%s" % (code, fid))
            value = (entry or {}).get("value") or ""
            if not DS.plausible_rating_value(value):
                blob.append("%s.%s" % (code, fid))
        if ".pdf" not in ((rec.get("source") or {}).get("file") or "").lower():
            no_src.append(code)
    if bad_field:
        add("E", "units-field", "속성 사전에 없는 필드 %d건: %s" % (len(bad_field), bad_field[0]))
    if blob:
        add("E", "units-blob", "눌린 다열 덩어리 %d건: %s" % (len(blob), blob[0]))
    if no_src:
        add("E", "units-source", "원본 PDF 출처 없는 형번 %d건: %s" % (len(no_src), no_src[0]))
    # 드리프트 — 추출 제안과 확정본의 어긋남. extracted 는 --sync 로 풀리고(W),
    # verified/manual 은 사람 확정이 이기므로 알림만(I) 한다.
    merged, log = U.merge_units(curated, proposals)
    stale = [k for kind, k in log if kind in ("add", "update", "drop")]
    kept = [k for kind, k in log if kind in ("drift", "orphan")]
    if stale:
        add("W", "units-stale", "추출 제안과 어긋난 %d건 (%s …) — units.py --sync"
            % (len(stale), stale[0]))
    if kept:
        add("I", "units-drift", "사람 확정본과 추출이 다른 %d건 — 원문 재확인 권장" % len(kept))
    if curated and not stale:
        n_ver = sum(1 for r in curated if r.get("status") in ("verified", "manual"))
        add("I", "units-ok", "형번 확정본 %d건 (사람 확인 %d)" % (len(curated), n_ver))


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
            print("\n■ %s  (%s · 포인트 %d)" % (cur, m["vendor"], n_points(m)))
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
