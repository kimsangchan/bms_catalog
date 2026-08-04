# -*- coding: utf-8 -*-
"""등록 — 수집한 문서를 모델로 만든다.

문서 1건 → 모델 1건이 아니다. 한 문서에 장치·프로파일이 여러 개면 나누고,
프로토콜이 섞여 있으면 한 모델에 함께 담는다.

**판정은 문서에서 자동으로 한다** (classify.py):
  · 장비 계열 — 포인트 이름에 나타나는 부속의 증거
  · 구간 이름 — PDF 목차의 프로파일 표제
  · 제품·컨트롤러 — 표지

자동 판정이 안 되거나 틀린 문서만 OVERRIDE 에 적는다. 손으로 적는 양이
문서 수에 비례하지 않아야 수백 벤더로 늘릴 수 있다.

실행
  python register.py            등록 계획만 (기존 모델은 건너뜀)
  python register.py --run      실제로 기록
  python register.py --all      이미 등록된 문서도 다시 계산해 보여준다
  python register.py --only ebm --run   파일 이름에 'ebm' 이 든 문서만

큰 문서(10MB 이상)는 표 인식이 느려 전체 훑기가 몇 분 걸린다. 그럴 때 --only 로
필요한 것만 돌린다.
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
sys.path.insert(0, HERE)
import classify as CL  # noqa: E402
import crosscheck as C  # noqa: E402
import extract as E  # noqa: E402
import schema as S  # noqa: E402

# 모델로 받아들일 최소 기준. 이보다 적으면 '오브젝트 목록이 있는 문서'가 아니라
# 추출이 표 조각을 몇 개 주운 것이다 — 152쪽짜리 설계 가이드에서 9점이 나온 적이 있다.
MIN_POINTS = 12

# 자동 판정이 틀리거나 부족한 문서만 여기 적는다.
OVERRIDE = {
    # 지붕형 패키지·스플릿은 포인트 구성이 공조기와 같아 e5 로 잡히는데,
    # 실제로 공조기 계열이 맞다. 이름만 제품에 맞춰 준다.
    "BAS-PTS002A-EN_11082024.pdf": {"cat": "HVAC.AIR.RTU.WSHP", "tag": "rooftop"},
    "BAS-PTS006A-EN_11152024.pdf": {"cat": "HVAC.AIR.RTU", "tag": "rooftop"},
    "BAS-PTS036A-EN_12042024.pdf": {"cat": "HVAC.AIR.SPLIT", "tag": "ahu"},
    # Daikin ED 문서는 표지 제목이 'Protocol Information' 뿐이라 제품명이 안 잡힌다.
    # 제품·컨트롤러는 각 문서 1쪽 적용 모델 목록에서 옮겨 적었다.
    "Daikin_ED-15112-21_MicroTech_Rooftop-AHU_Protocol.pdf": {
        "cat": "HVAC.AIR.RTU", "tag": "rooftop",
        "controller": "MicroTech III/4",
        "product": "Rebel·RoofPak·Maverick II Rooftop & Self-Contained",
    },
    "Daikin_ED-15120-12_MicroTech_Chiller_Protocol.pdf": {
        "controller": "MicroTech III/4",
        "product": "AGZ·AMZ·ADS·AWV·WME·WWV Chillers",
    },
    "Daikin_ED-19131-1_MicroTech_AGZ-F-WMT_Protocol.pdf": {
        "controller": "MicroTech",
        "product": "AGZ-F & WMT Chillers",
    },
    "Daikin_ED-19111-3_MicroTech_WME-CD_Protocol.pdf": {
        "controller": "MicroTech",
        "product": "WME-C/D Magnitude Chiller",
    },
    "JCI_Simplicity-SE_Point-Mapping_5177447-uts-a-1215.pdf": {
        "cat": "HVAC.AIR.RTU", "tag": "rooftop",
        "controller": "Simplicity SE (Smart Equipment)",
        "product": "York Rooftop Units",
    },
    "IVProdukt_Siemens-Climatix-POL908_AHU_BACnet_Objects_V1.pdf": {
        "cat": "HVAC.AIR.AHU", "tag": "ahu",
        "controller": "Climatix POL908",
        "product": "IV Produkt AHU Application",
    },
    # 표지가 'Controls, Start-Up…' 매뉴얼이라 제품명 대신 Form 번호가 잡힌다
    "Carrier_48-50N-7T_WeatherExpert_Controls.pdf": {
        "cat": "HVAC.AIR.RTU", "tag": "rooftop",
        "controller": "ComfortLink",
        "product": "48/50N WeatherExpert Rooftop 75-150 Ton",
    },
    # 표지가 컨트롤러 기술 가이드라 ASM 번호 조각이 잡힌다
    "AAON_VCCX2_Technical_Guide.pdf": {
        "cat": "HVAC.AIR.RTU", "tag": "rooftop",
        "controller": "VCCX2",
        "product": "RN/RQ Series Rooftop",
    },
    # 표지 제목이 개요 문장이라 조각이 잡힌다
    "Swegon_GOLD-EF_Modbus_RTU-TCP.pdf": {
        "cat": "HVAC.AIR.AHU", "tag": "ahu",
        "controller": "IQlogic",
        "product": "GOLD RX/PX/CX/SD AHU",
    },
}

# 구간 이름을 사람 말로 — 목차에서 딴 약어를 풀어 쓴다 (LonMark 표준 프로파일)
SEGWORD = {
    "scc": "SCC 프로파일 (실내 쾌적 제어)",
    "dac": "DAC 프로파일 (급기 제어)",
    "simplex": "단식(Simplex)",
    "duplex": "복식(Duplex)",
    "idu": "실내기(IDU)",
    "odu": "실외기(ODU)",
}


def read(pdf):
    fam = E.classify(pdf)
    rows = E.extract_lontalk(pdf, keep_order=True) if fam == "lontalk" else []
    # 'network variable' 라는 말만으로 lontalk 판정된 BACnet 문서(Daikin ED)가 있다 —
    # SNVT 가 이만큼 안 나오면 일반 추출로 다시 읽는다 (extract.extract 와 같은 기준).
    if len(rows) < 20:
        rows = E.extract(pdf)[0]
    return rows, C.compare(pdf, table_rows=rows), fam


def unreliable_reason(fname):
    """이 문서는 교차 대조로 검증할 수 없다고 소스가 밝혔는가 → 사유"""
    import re as _re
    from sources import SOURCES
    for src in SOURCES:
        pat = src.get("crosscheck_unreliable")
        if pat and _re.search(pat, fname):
            return "%s 소스가 교차 대조 불가로 표시 — 개요표와 상세표가 서로 다른 열이다"                    % src["vendor"]
    return None


def plan_one(fname, vendor="Trane"):
    """문서 1건 → 만들 모델 목록 (아직 기록하지 않는다)"""
    pdf = os.path.join(RAW, fname)
    rows, xc, fam = read(pdf)
    segs = E.split_profiles(rows)
    ti = CL.title_info(pdf)
    doctext = " ".join(str(v) for v in ti.values()) + " " + CL.front_text(pdf)
    eq, cat, tag, why = CL.classify_equip(rows, doctext)
    ov = OVERRIDE.get(fname, {})
    eq, cat, tag = ov.get("equipId", eq), ov.get("cat", cat), ov.get("tag", tag)
    # 표지 자동 인식이 제품·컨트롤러 이름을 못 뽑는 문서(제목이 'Protocol Information'
    # 뿐인 Daikin ED 등)는 모델 ID 가 문장 조각이 된다 — 이름만 손으로 준다.
    if ov.get("product"):
        ti["product"] = ov["product"]
    if "controller" in ov:
        ti["controller"] = ov["controller"]

    names = CL.segment_names(pdf)
    labels = names if len(names) == len(segs) else []
    # 구간 라벨은 'scc'·'idu' 같은 짧은 식별자여야 한다 — 목차 조각('Table 1:…')이
    # 들어오면 모델 ID 가 오염되고, Windows 에서는 콜론 때문에 파일까지 깨진다(AAON 실측).
    labels = [(l if l and len(l) <= 24 and ":" not in l and "\t" not in l else None)
              for l in labels]
    if all(l is None for l in labels):
        labels = []
    # 프로토콜 이름은 실제 오브젝트 타입에서 딴다 — Modbus 전용 문서를 'BACnet'
    # 이라고 부르면 안 된다.
    allproto = collections.Counter(S.protocol_of(p["type"]) for p in rows)
    proto_name = "·".join(k for k, _ in allproto.most_common()) or "미상"
    prod = ti["product"] or os.path.splitext(fname)[0]
    ctl = ti["controller"]
    # 컨트롤러가 없으면 제품명만 쓴다. 벤더를 채워 넣으면 모델 ID 가
    # 'danfoss-danfoss-…' 처럼 벤더를 두 번 달게 된다.
    base_model = ("%s — %s (%s)" % (ctl, prod, proto_name)
                  if ctl and ctl != prod else "%s (%s)" % (prod, proto_name))

    out = []
    for i, pts in enumerate(segs):
        lab = labels[i] if labels else None
        sub = SEGWORD.get((lab or "").lower(), lab)
        mid = S.model_id(vendor, base_model) + ("-" + lab.lower() if lab else "")
        proto = collections.Counter(S.protocol_of(p["type"]) for p in pts)
        out.append({
            "id": mid, "equipId": eq, "vendor": vendor,
            "model": base_model + (" · " + sub if sub else ""),
            "name": ("%s %s" % (ctl, prod) if ctl else prod)
                    + (" · " + sub if sub else ""),
            "cat": cat, "tag": tag, "status": "active",
            "summary": "공개 통합 포인트 리스트에서 자동 추출했다. "
                       + " · ".join("%s %d점" % (k, v) for k, v in proto.most_common())
                       + (" · 펌웨어 %s" % ti["firmware"] if ti["firmware"] else ""),
            "has": {"spec": False, "points": True},
            "ede": False, "spec": [], "io": [], "elec": None,
            "comm": [[k, "통합 포인트 리스트 공개", "—", "Points List"] for k in proto],
            "points": [{k: p.get(k) for k in
                        ("type", "inst", "name", "unitRaw", "unit", "note")} for p in pts],
            "gap": "정격 성능(용량·소비전력·효율)은 이 문서에 없다 — 제품 카탈로그가 따로 필요하다.",
            "extractor": "table", "sourceDoc": fname,
            "classifiedBy": why,
            "crosscheck": ({"unverifiable": unreliable_reason(fname)}
                           if unreliable_reason(fname) else
                           {"rate": xc["rate"], "both": xc["both"],
                            "diff": [[str(k[0]), k[1], a, b]
                                     for _, k, a, b in xc["diff"][:20]]}),
        })
    return out, xc, ti


def main(argv):
    run, show_all = "--run" in argv, "--all" in argv
    only = argv[argv.index("--only") + 1].lower() if "--only" in argv else None
    known = {}
    for f in glob.glob(os.path.join(DATA, "models", "*.json")):
        m = json.load(open(f, encoding="utf-8"))
        if m.get("sourceDoc"):
            known.setdefault(m["sourceDoc"], []).append(m["id"])
    led = json.load(open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    url_by_file = {v.get("file"): u for u, v in led.items() if v.get("file")}
    vendor_by_file = {v.get("file"): v.get("vendor", "?") for v in led.values() if v.get("file")}
    docs = json.load(open(os.path.join(DATA, "docs.json"), encoding="utf-8"))
    have = {d.get("docNo") for d in docs}

    made, newdocs, skipped = 0, 0, 0
    print("%-52s %-4s %6s  %s" % ("모델 ID", "계열", "포인트", "교차대조"))
    print("─" * 92)
    for pdf in sorted(glob.glob(os.path.join(RAW, "*.pdf"))):
        fname = os.path.basename(pdf)
        if only and only not in fname.lower():
            continue
        # 이미 이 문서로 만든 모델이 있으면 건너뛴다. --run 일 때도 마찬가지다 —
        # 예전에 --run 에서만 이 검사를 빼놨다가 같은 문서가 옛 이름·새 이름으로
        # 두 번 등록돼 모델 11건이 중복됐다.
        if fname in known and not show_all:
            skipped += 1
            continue
        vendor = vendor_by_file.get(fname, "?")
        models, xc, ti = plan_one(fname, vendor)
        npts = sum(len(m["points"]) for m in models)
        if npts < MIN_POINTS:
            print("  · %-42s 포인트 %d건 — 오브젝트 목록 문서가 아니다 (건너뜀)"
                  % (fname, npts))
            continue
        if not models[0]["equipId"]:
            print("  ⚠ %s — 장비 판정 실패, OVERRIDE 에 적어야 한다" % fname)
            continue
        for m in models:
            exists = m["id"] in sum(known.values(), [])
            print("%-52s %-4s %6d  %5.1f%%%s"
                  % (m["id"][:52], m["equipId"], len(m["points"]),
                     xc["rate"] * 100, "  (기존)" if exists else ""))
            if run and not exists:
                json.dump(m, open(os.path.join(DATA, "models", m["id"] + ".json"), "w",
                                  encoding="utf-8"), ensure_ascii=False, indent=1)
                made += 1
        docno = fname.rsplit("-EN", 1)[0] if "-EN" in fname else os.path.splitext(fname)[0]
        if run and docno not in have:
            docs.append({"modelId": models[0]["id"], "kind": "포인트리스트",
                         "title": "%s %s" % (ti["controller"], ti["product"]),
                         "publisher": vendor, "docNo": docno, "issued": "2024",
                         "url": url_by_file.get(fname, ""), "status": "취입 완료"})
            have.add(docno)
            newdocs += 1
    if run:
        json.dump(docs, open(os.path.join(DATA, "docs.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n모델 %d건 기록 · 문서 메타 %d건 추가" % (made, newdocs))
    else:
        print("\n등록된 문서 %d건 건너뜀 (--all 로 전부 보기) · --run 으로 기록" % skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
