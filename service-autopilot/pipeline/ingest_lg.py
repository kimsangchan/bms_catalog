# -*- coding: utf-8 -*-
"""LG AC Smart BACnet 게이트웨이 오브젝트 목록 취입 — 165점.

  PYTHONIOENCODING=utf-8 python ingest_lg.py            바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_lg.py --run      실제로 기록한다

무엇을 세우나
  문서는 **게이트웨이 매뉴얼**이다. 포인트는 모델이 아니라 인터페이스에 속하므로
  (D-016) 제품 = AC Smart BACnet 게이트웨이 하나, 판 = 기기군 여섯
  (실내기·환기·공조기·실외기·AWHP·게이트웨이 공통)으로 세운다.
  JCI SC-EQ 통신카드를 제품으로 세운 것과 같은 자리다.

⚠ 인스턴스 번호를 **채우지 않는다.**
  원문 50쪽이 규칙을 준다:
    "(XXX : Unit address)"
    "Product Type(Indoor:0, Vent:1, AHU:2, ODU:3, AWHP:4, GENERAL:5)"
    "Device : Group of Product units(16EA)"
    → instance = 유형×0x10000 + Device×0x1000 + Product×0x100 + Point
    → XXX(유닛 주소) = Device×16 + Product
  즉 인스턴스는 **유닛 주소가 정해져야** 정해진다. 주소는 문서의 결손이 아니라
  **현장 설정값**이다(Modbus 슬레이브 ID 와 같은 성격). 주소 0 일 때의 값을 넣으면
  다른 주소에서 전부 틀리므로, blocks.bacnet.instance 는 비우고 규칙을 판의 note 와
  gaps 에 적는다. 스키마에 공식·포인트번호를 담을 필드가 없어 **지어내지 않는다** —
  포인트 번호는 provenance.sourceColumns 에 원문 그대로 남긴다.
  ⚠ VEC100 과는 다르다. VEC100 은 주소를 만들 규칙 자체가 없다. 여기는 규칙이 있다.

⚠ 표가 전치돼 있다 — 행이 속성(Object Type·Object Name·Point No.)이고 열이 포인트다.
  추출은 verify_lg.extract() 를 그대로 쓴다(대조 화면과 같은 판독을 쓴다).
  **교차 대조는 다른 경로로 한다** — 표 인식이 아니라 쪽 글자 흐름에서 이름을 다시 읽는다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import verify_lg as V  # noqa: E402  — 추출은 대조 화면과 같은 것을 쓴다

MODEL_ID = "lg-ac-smart-bacnet-gateway"
FAMILY = "LG/ACSmart-BACnet"

# 기기군 → (판 id, 그 판이 덮는 장치, 그 판만의 제약)
#
# ⚠ appliesTo 는 **원문이 부르는 이름만** 쓴다. 원문 5쪽이 붙는 장치를 직접 열거한다:
#     "* Devices : Indoor units, ERV, DI/DOs, DOKITs, AWHPs, AHUs"
#     "with devices like the indoor unit, ERV, DI/DO, DOKIT, AWHP, AHU and I/O Module"
#   전부 LG 485 망에 붙는 LG 장치다 — 타사 프로토콜을 받는 자리가 아니다.
#   (처음에 'Multi V 실내기'·'전열교환기(HRV)' 라고 적었다가 지웠다. 원문에 없는 말이다 —
#    원문은 HRV 가 아니라 **ERV** 라고 쓰고, Multi V 라는 말은 이 목록에 쓰지 않는다.)
IFACE = {
    "실내기": ("indoor-unit", ["Indoor unit"], None),
    "환기(ERV)": ("ventilation", ["ERV"], None),
    "공조기(AHU)": ("ahu", ["AHU"],
                 "⚠ 원문 제약: 'BACnet protocol is not supported for Modular AHU and "
                 "I/O module.' — 모듈러 AHU 는 이 목록으로 못 읽는다. 또 485 포트가 "
                 "채널 둘로 갈려 있고 'CH1: AHU, CH2: devices other than AHU' 다."),
    "실외기(ODU)": ("odu", ["ODU"],
                 "⚠ 원문 제약: 'ODU Point List may not be supported depending on the "
                 "product.' — 제품에 따라 안 될 수 있다."),
    "AWHP": ("awhp", ["AWHP"], None),
    "게이트웨이 공통": ("gateway-general", ["AC Smart BACnet"],
                  "⚠ 원문 제약: 'Some of GENERAL Points may not be supported depending "
                  "on the product.'"),
}

RULE = ("instance = 제품유형×0x10000 + Device×0x1000 + Product×0x100 + Point 이고 "
        "유닛 주소 XXX = Device×16 + Product 다. 제품유형은 Indoor:0 Vent:1 AHU:2 "
        "ODU:3 AWHP:4 GENERAL:5 (원문 50쪽). 원문 예시 42행에 42/42 일치를 확인했다.")


def crosscheck(doc, tables):
    """표 인식이 아닌 **쪽 글자 흐름**에서 오브젝트 이름을 다시 읽어 맞춘다.

    같은 판독기로 두 번 읽으면 같은 맹점을 그대로 통과한다. 여기서는 find_tables 를
    쓰지 않고 get_text 의 낱말을 훑어 '..._XXX' 꼴 이름을 모은다.
    """
    # ⚠ 정규식으로 이름을 다시 뽑지 않는다. 전치 표라 이름이 줄바꿈으로 갈려 있어
    #    '낱말(공백?낱말)*_XXX' 같은 패턴을 쓰게 되는데, 중첩 수량자라 _XXX 가 없는
    #    쪽에서 파국적 백트래킹으로 멈춘다(실제로 10분을 넘겼다).
    #    공백을 전부 지운 뒤 **부분문자열 포함**으로 맞춘다 — 표 인식을 거치지 않는
    #    다른 경로라는 점은 그대로다.
    flat = {t["page"]: re.sub(r"\s+", "", doc[t["page"] - 1].get_text()) for t in tables}

    same = miss = 0
    diff = []
    for t in tables:
        pg = t["page"]
        for p in t["points"]:
            if re.sub(r"\s+", "", p["name"]) in flat[pg]:
                same += 1
            else:
                miss += 1
                if len(diff) < 8:
                    diff.append("%d쪽 %s" % (t["printed"], p["name"]))
    total = same + miss
    return {"method": "쪽 글자 흐름에서 이름을 다시 읽어 맞췄다(표 인식 경로가 아니다)",
            "total": total, "both": same, "rate": round(same / total, 4) if total else 0.0,
            "diff": diff}


def build(meta, url, tables, cc):
    # ⚠ 기기군 이름이 IFACE 열쇠와 어긋나면 그 판이 **통째로 조용히 빠진다.**
    #    실제로 '환기(HRV)'→'환기(Ventilation)' 로 한쪽만 고쳤다가 20점을 잃었다
    #    (165 → 145). 총계만 보면 알아채기 어려워 여기서 세운다.
    unknown = sorted({t["group"] for t in tables} - set(IFACE))
    if unknown:
        raise SystemExit("IFACE 에 없는 기기군: %s — verify_lg.KO 와 이름을 맞춰라" % unknown)

    ifaces, total = [], 0
    for group, (iid, applies, limit) in IFACE.items():
        ts = [t for t in tables if t["group"] == group]
        if not ts:
            continue
        pts, pages = [], []
        for t in ts:
            pages.append(t["printed"])
            for p in t["points"]:
                common = {"name": p["name"]}
                if p["desc"]:
                    common["note"] = p["desc"]
                pgaps = ["blocks.bacnet.instance"]
                if p["states"]:
                    common["states"] = [
                        {"code": s.split("=", 1)[0], "label": s.split("=", 1)[1]}
                        for s in p["states"].split(", ") if "=" in s]
                # ⚠ 단위 칸에는 단위·범위·비고가 섞여 있다. **값을 보고 가른다** —
                #    숫자가 없고 짧은 것만 단위로 올리고(°C·℃·%·Minute), 범위('0~90')와
                #    비고('Reference LG Original Error Code')는 원문 칸에만 남긴다.
                #    포인트 스키마에 단위중립 범위 자리가 없다(rangeIP·rangeSI 는
                #    야드파운드/SI 쌍을 주는 계통 전용).
                u = p.get("unit") or ""
                if u and not re.search(r"\d", u) and len(u) <= 12:
                    common["unitSIRaw"] = u
                    common["unitSI"] = u.replace("℃", "°C")
                elif u:
                    pgaps.append("common.unitSI — 원문 Unit 칸이 단위가 아니라 "
                                 "범위·비고다(%r). sourceColumns 에 원문 그대로 남겼다." % u)
                blocks = {}
                if p["type"]:
                    blocks["bacnet"] = {"objectType": p["type"]}
                    # Text-N 의 N 이 곧 present-value 다 — 보정이 필요 없다.
                    # 근거: 원문 비고가 ModeCommand 를 "1: Cool", FanSpeedStatus 를
                    # "1:Low" 라 적었고 표의 슬롯 1 이 각각 Cool·Low 다(둘 다 일치).
                    if p["type"] in ("MI", "MO", "MV") and p["states"]:
                        blocks["bacnet"]["msvOffset"] = 0
                pts.append({
                    "common": common,
                    "blocks": blocks,
                    "provenance": {
                        "sourceFile": meta["file"],
                        "sourcePage": t["printed"],
                        "family": FAMILY,
                        "sourceColumns": {
                            "Point No.": str(p["no"]),
                            "Object Type": p["type"] or "",
                            # 조판 아티팩트를 지우기 전 원문 그대로(artifactCleanupFirst).
                            # 이름의 '_ XXX' 빈칸은 원문에 없다 — verify_lg.ident 참고.
                            "Object Name": p.get("nameRaw") or p["name"],
                            "Control/monitoring": p["desc"] or "",
                            **({"Unit": p["unit"]} if p.get("unit") else {}),
                            **({"Text-%s" % s.split("=", 1)[0]: s.split("=", 1)[1]
                                for s in p["states"].split(", ") if "=" in s}
                               if p.get("states") else {}),
                        },
                        "gaps": pgaps,
                        "status": "extracted",
                        "interfaceId": iid,
                    },
                })
        total += len(pts)
        ifaces.append({
            "id": iid,
            "label": "BACnet Point List : %s" % group,
            "family": FAMILY,
            "protocols": ["bacnet"],
            "sourceFile": meta["file"],
            "sourcePages": sorted(set(pages)),
            "pointCount": len(pts),
            "appliesTo": applies,
            "status": "extracted",
            "note": ("게이트웨이가 이 기기군에 대해 내보내는 오브젝트 목록. "
                     "⚠ 인스턴스 번호는 표에 없고 **유닛 주소가 정해져야** 정해진다 — " + RULE),
            "gaps": (["blocks.bacnet.instance — 유닛 주소(현장 설정값)가 있어야 정해진다. "
                      "규칙은 note 에 있다. 주소 0 일 때의 값을 넣으면 다른 주소에서 전부 틀린다."]
                     + ([limit] if limit else [])),
            "points": pts,
        })

    return {
        "id": MODEL_ID,
        "equipId": "e5",
        "vendor": "LG",
        "model": "AC Smart BACnet",
        "name": "AC Smart BACnet Gateway",
        "cat": "HVAC.AIR.VRF",
        "tag": "vrf",
        "tags": ["vrf"],
        "status": "active",
        "coversDevices": ("원문 5쪽이 붙는 장치를 직접 열거한다 — Indoor units · ERV · "
                          "DI/DOs · DOKITs · AWHPs · AHUs · I/O Module. 전부 LG 485 망의 "
                          "LG 장치다(2CH: CH1 이 AHU, CH2 가 그 밖). 타사 벤더 것을 섞지 않았다 — "
                          "165점 전부 이 문서 하나에서 나왔다. "
                          "⚠ DI/DO · DOKIT · I/O Module 은 이 문서에 포인트 표가 없어 취입하지 않았다."),
        "classifiedBy": ("게이트웨이지만 덮는 기기군의 주력이 VRF(실내기·실외기)라 "
                         "cat 을 HVAC.AIR.VRF 로 둔다. JCI YKN2Open 게이트웨이를 그것이 "
                         "덮는 옥상형(HVAC.AIR.RTU)으로 둔 것과 같은 방식이다."),
        "summary": "BACnet 게이트웨이 매뉴얼 1건 · 판 %d개에서 취입 — 오브젝트 %d점" % (len(ifaces), total),
        "has": {"spec": False, "points": True},
        "ede": False,
        "spec": [], "io": [], "elec": None, "points": [],
        "gap": ("정격·형번이 없다 — 게이트웨이 매뉴얼이라 제품 카탈로그가 따로 필요하다. "
                "그리고 오브젝트의 BACnet 인스턴스 번호가 비어 있다: 원문이 규칙은 주지만"
                "(50쪽) 실제 번호는 **유닛 주소가 정해져야** 나온다. " + RULE),
        "extractor": "ingest_lg",
        "sourceDoc": meta["file"],
        "interfaces": ifaces,
        "crosscheck": cc,
    }


def main(argv):
    import fitz
    run = "--run" in argv
    url, meta = V.ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, V.SRC_ID))
    doc = fitz.open(path)

    tables = V.extract(doc)
    cc = crosscheck(doc, tables)
    model = build(meta, url, tables, cc)

    print("모델 %s" % model["id"])
    for i in model["interfaces"]:
        print("   %-16s %2d점  원문 %s쪽" % (i["id"], i["pointCount"], i["sourcePages"]))
    n = sum(i["pointCount"] for i in model["interfaces"])
    print("   합계 %d점 · 교차 대조 %d/%d = %.1f%% (%s)"
          % (n, cc["both"], cc["total"], 100 * cc["rate"], cc["method"]))
    if cc["diff"]:
        print("   ⚠ 안 맞은 것:", " · ".join(cc["diff"]))

    out = os.path.join(DATA, "models", MODEL_ID + ".json")
    if not run:
        print("\n(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n→ %s" % os.path.relpath(out, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
