# -*- coding: utf-8 -*-
"""등록 — 수집한 문서를 모델로 만든다.

문서 1건 → 모델 1건이 아니다. 한 문서에 장치가 여러 대 실려 있으면 나눠야 하고
(LonMark 프로파일, 실내기/실외기), 프로토콜이 섞여 있으면 그대로 한 모델에 담는다.

수동으로 정하는 것은 **장비 계열·이름·분류 태그**뿐이다. 나머지(포인트·프로토콜·
교차 대조 결과·근거 문서)는 문서에서 나온다.

실행
  python register.py --plan            등록 계획만 출력
  python register.py --run             data/models/*.json 생성
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
sys.path.insert(0, HERE)
import crosscheck as C  # noqa: E402
import extract as E  # noqa: E402
import schema as S  # noqa: E402

# 문서 → 장비 판정. 표지에서 읽은 제품명을 근거로 사람이 정한 부분이다.
#   equipId  data/equips/ 의 계열
#   split    한 문서 안 장치가 여러 대일 때 구간별 접미사·이름 (없으면 통째로 1건)
PLAN = {
    "BAS-PTS002A-EN_11082024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 700 — Precedent/Axiom Rooftop WSHP (LonTalk)",
        "name": "Symbio™ 700 지붕형 수열원 히트펌프 — LonTalk",
        "equipId": "e5", "cat": "HVAC.AIR.RTU.WSHP", "tag": "rooftop",
        "split": [("scc", "SCC 프로파일 (실내 쾌적 제어)"), ("dac", "DAC 프로파일 (급기 제어)")],
    },
    "BAS-PTS004A-EN_09182024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 800 — IntelliPak (LonTalk)",
        "name": "Symbio™ 800 대형 공조기 IntelliPak — LonTalk",
        "equipId": "e5", "cat": "HVAC.AIR.AHU", "tag": "ahu",
        "split": [("scc", "SCC 프로파일 (실내 쾌적 제어)"), ("dac", "DAC 프로파일 (급기 제어)")],
    },
    "BAS-PTS006A-EN_11152024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 700 — Odyssey (LonTalk)",
        "name": "Symbio™ 700 Odyssey 실외 공조기 — LonTalk",
        "equipId": "e5", "cat": "HVAC.AIR.AHU", "tag": "ahu",
    },
    "BAS-PTS008A-EN_11152024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 800 — Agility Water-cooled (LonTalk)",
        "name": "Symbio™ 800 Agility 수랭식 원심 냉동기 — LonTalk",
        "equipId": "e9", "cat": "HVAC.PLANT.CHILLER", "tag": "chiller",
    },
    "BAS-PTS010A-EN_11152024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 800 — CenTraVac (LonTalk)",
        "name": "Symbio™ 800 CenTraVac 원심 냉동기 — LonTalk",
        "equipId": "e9", "cat": "HVAC.PLANT.CHILLER", "tag": "chiller",
    },
    "BAS-PTS011A-EN_11152024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 800 (ACS/ACX) — Ascend",
        "name": "Symbio™ 800 Ascend 공랭 냉동기 — BACnet · Modbus",
        "equipId": "e9", "cat": "HVAC.PLANT.CHILLER", "tag": "chiller",
    },
    "BAS-PTS012A-EN_11152024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 800 — Ascend ACS/ACX (LonTalk)",
        "name": "Symbio™ 800 Ascend 공랭 냉동기 — LonTalk",
        "equipId": "e9", "cat": "HVAC.PLANT.CHILLER", "tag": "chiller",
    },
    "BAS-PTS014A-EN_11152024.pdf": {
        "vendor": "Trane", "model": "Symbio™ 800 — Sintesis RTAF (LonTalk)",
        "name": "Symbio™ 800 Sintesis RTAF 공랭 스크류 냉동기 — LonTalk",
        "equipId": "e9", "cat": "HVAC.PLANT.CHILLER", "tag": "chiller",
    },
}


def read(pdf):
    """문서 1건 → (구간별 포인트, 교차 대조 결과)"""
    fam = E.classify(pdf)
    rows = (E.extract_lontalk(pdf, keep_order=True) if fam == "lontalk"
            else E.extract(pdf)[0])
    xc = C.compare(pdf, table_rows=rows)
    return E.split_profiles(rows), xc, fam


def build(fname, spec):
    pdf = os.path.join(RAW, fname)
    segs, xc, fam = read(pdf)
    split = spec.get("split")
    if split and len(segs) != len(split):
        print("  ⚠ %s: 구간 %d개인데 계획은 %d개 — 통째로 등록한다"
              % (fname, len(segs), len(split)))
        split = None
    parts = list(zip(split, segs)) if split else [((None, None), [p for s in segs for p in s])]

    out = []
    for (suffix, subname), pts in parts:
        mid = S.model_id(spec["vendor"], spec["model"]) + ("-" + suffix if suffix else "")
        proto = collections.Counter(S.protocol_of(p["type"]) for p in pts)
        out.append({
            "id": mid, "equipId": spec["equipId"], "vendor": spec["vendor"],
            "model": spec["model"] + (" · " + subname if subname else ""),
            "name": spec["name"] + (" · " + subname if subname else ""),
            "cat": spec["cat"], "tag": spec["tag"], "status": "active",
            "summary": "공개 통합 포인트 리스트에서 자동 추출했다. "
                       + " · ".join("%s %d점" % (k, v) for k, v in proto.most_common())
                       + (" · %s" % subname if subname else ""),
            "has": {"spec": False, "points": True},
            "ede": False, "spec": [], "io": [], "elec": None,
            "comm": [[k, "통합 포인트 리스트 공개", "—", "Points List"]
                     for k in proto],
            "points": [{k: p[k] for k in ("type", "inst", "name", "unitRaw", "unit", "note")}
                       for p in pts],
            "gap": "정격 성능(용량·COP·소비전력)은 이 문서에 없다 — 제품 카탈로그가 따로 필요하다."
                   + (" LonTalk 프로파일이라 BACnet 오브젝트 번호는 별도 문서를 봐야 한다."
                      if fam == "lontalk" else ""),
            "extractor": "table",
            "sourceDoc": fname,
            "crosscheck": {"rate": xc["rate"], "both": xc["both"],
                           "diff": [[str(k[0]), k[1], a, b] for _, k, a, b in xc["diff"][:20]]},
        })
    return out, xc


def main(argv):
    run = "--run" in argv
    led = json.load(open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    url_by_file = {v.get("file"): u for u, v in led.items() if v.get("file")}
    docs = json.load(open(os.path.join(DATA, "docs.json"), encoding="utf-8"))
    have = {d.get("docNo") for d in docs}
    made, newdocs = 0, 0
    print("%-46s %-5s %6s  %s" % ("모델 ID", "계열", "포인트", "교차대조"))
    print("─" * 84)
    for fname, spec in sorted(PLAN.items()):
        if not os.path.exists(os.path.join(RAW, fname)):
            print("  · %s 없음 — 건너뜀" % fname)
            continue
        models, xc = build(fname, spec)
        for m in models:
            print("%-46s %-5s %6d  %5.1f%% (%d점 대조)"
                  % (m["id"], m["equipId"], len(m["points"]), xc["rate"] * 100, xc["both"]))
            if run:
                json.dump(m, open(os.path.join(DATA, "models", m["id"] + ".json"), "w",
                                  encoding="utf-8"), ensure_ascii=False, indent=1)
                made += 1
        docno = fname.rsplit("-EN", 1)[0]
        if run and docno not in have:
            docs.append({"modelId": models[0]["id"], "kind": "포인트리스트",
                         "title": spec["name"], "publisher": spec["vendor"],
                         "docNo": docno, "issued": "2024",
                         "url": url_by_file.get(fname, ""), "status": "취입 완료"})
            newdocs += 1
    if run:
        json.dump(docs, open(os.path.join(DATA, "docs.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n모델 %d건 기록 · 문서 메타 %d건 추가" % (made, newdocs))
    else:
        print("\n(--run 을 주면 실제로 기록한다)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
