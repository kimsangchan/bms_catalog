# -*- coding: utf-8 -*-
"""빌드 — data/ 의 JSON을 읽어 카탈로그 HTML을 굽는다.

이전에는 파이썬 딕셔너리(models.py)를 읽었지만, 이제 데이터는 data/ 아래 JSON이
유일한 원본이다. HTML은 생성물이며 폐쇄망 배포용으로 계속 유지한다.

실행:  python build.py
전체:  python migrate.py && python normalize.py && python validate.py && python build.py
"""
import json, os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(HERE, "data")
OUT = os.path.join(ROOT, "review", "equip-catalog.html")
TPL = os.path.join(ROOT, "evidence", "gen2.py")   # 화면 템플릿은 gen2.py 안의 HTML을 재사용
sys.path.insert(0, HERE)

PUBLIC_MENU_EQUIP_IDS = {
    "e5", "e6", "e7", "e8",
    "e9", "e10", "e11", "e12",
    "e13", "e14", "e15", "e16",
    "e19", "e20",
}
PUBLIC_MODEL_EQUIP_IDS = {"e5"}

DOM_ORDER = ["공기측 설비", "열원·수측 설비", "반송·구동", "계측·제어", "전력 설비",
             "조명·차양", "방재", "승강", "보안·출입", "환경·공기질", "급배수·위생"]


def clean_label(text):
    return " ".join(str(text or "").replace("™", "").replace("®", "").split())


def selector_label(model):
    """모델 선택 버튼용 짧은 이름.

    원본 모델명은 컨트롤러명이 앞에 오는 경우가 많아, 버튼에서는 제조사와 실제
    장비 제품군을 먼저 보이게 한다. 원본 model/name 필드는 그대로 보존한다.
    """
    vendor = clean_label(model.get("vendor"))
    raw = clean_label(model.get("model"))
    raw_no_proto = clean_label(
        raw.replace("(BACnet)", "").replace("(LonTalk)", "").replace("(Modbus)", ""))

    if model.get("id") == "aaon-vccx2-rn-rq-series-rooftop-bacnet":
        return "AAON RN/RQ Rooftop · VCCX2"

    parts = [clean_label(x) for x in raw_no_proto.split("—", 1)]
    if len(parts) == 2:
        controller, product = parts
        product = product.replace(" Series ", " ").replace(" Series", "")
        label = "%s %s · %s" % (vendor, product, controller)
    else:
        label = "%s %s" % (vendor, raw_no_proto)
    return clean_label(label)


def model_subtype(model):
    """공조기 아래에서 서로 다른 장비군을 한 단계 더 구분한다."""
    if model.get("equipId") != "e5":
        return ""
    text = " ".join([
        model.get("id") or "",
        model.get("vendor") or "",
        model.get("model") or "",
        model.get("cat") or "",
        model.get("tag") or "",
    ]).lower()
    if "interface" in text or "comm kit" in text or "pac-if" in text:
        return "AHU 인터페이스 / 외부 공조기 연동"
    if "wshp" in text:
        return "RTU / WSHP"
    if "rooftop" in text or ".rtu" in text:
        return "RTU / Rooftop"
    if "split system" in text or ".split" in text:
        return "Split system / AHU 연동"
    if any(w in text for w in ("gold", "geniox", "iv produkt", "climatix")):
        return "Modular AHU / 전용 컨트롤러"
    if "intellipak" in text:
        return "Packaged AHU"
    return "AHU / 기타"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load():
    equips = []
    for f in sorted(glob.glob(os.path.join(DATA, "equips", "*.json")),
                    key=lambda p: int(os.path.basename(p)[1:-5])):
        e = load_json(f)
        if e["id"] not in PUBLIC_MENU_EQUIP_IDS:
            continue
        equips.append({
            "id": e["id"], "no": e["no"], "title": e["title"], "domain": e["domain"],
            "head": e.get("tagSummary", ""), "notes": e.get("notes", []),
            "spec": e.get("specTables", []), "points": e.get("pointTables", []),
            "np": sum(len(t["rows"]) for t in e.get("pointTables", [])),
            "ns": sum(len(t["rows"]) for t in e.get("specTables", [])),
        })
    models = {}
    docs_by_model = {}
    for d in load_json(os.path.join(DATA, "docs.json")):
        docs_by_model.setdefault(d["modelId"], []).append(
            [d["kind"], d["title"], d["publisher"], d["docNo"], d["issued"], d["url"], d["status"]])
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = load_json(f)
        if m["equipId"] not in PUBLIC_MODEL_EQUIP_IDS:
            continue
        base = m["id"].rsplit("-idu", 1)[0].rsplit("-odu", 1)[0]
        models.setdefault(m["equipId"], []).append({
            "id": m["id"], "equipId": m["equipId"],
            "vendor": m["vendor"], "model": m["model"], "name": m["name"],
            "selectorLabel": selector_label(m),
            "modelSubtype": model_subtype(m),
            "cat": m["cat"], "tag": m["tag"], "status": m.get("status", "active"),
            "summary": m.get("summary", ""), "has": m.get("has", {}),
            "spec": m.get("spec", []), "comm": m.get("comm", []), "io": m.get("io", []),
            "elec": m.get("elec"), "gap": m.get("gap", ""),
            "specTables": m.get("specTables", []),
            "variants": m.get("variants", []),
            "photo": m.get("photo"), "photoSource": m.get("photoSource"),
            "specFrom": m.get("specFrom"),
            "docs": docs_by_model.get(m["id"]) or docs_by_model.get(base) or [],
            "points": [{"inst": p["inst"], "type": p["type"],
                        "unitDisp": p.get("unitRaw") or "—", "name": p["name"],
                        "note": p.get("note", "")} for p in m.get("points", [])],
        })
    # 사양 참조 풀기 — 같은 제품의 다른 프로토콜 판은 사양을 공유한다.
    # 데이터에는 참조만 두고(중복 방지), 화면에 낼 때 실제 값을 채운다.
    by_id = {m["id"]: m for v in models.values() for m in v}
    for v in models.values():
        for m in v:
            src = by_id.get(m.pop("specFrom", None) or "")
            if src:
                m["variants"] = src.get("variants", [])
                m["specTables"] = src.get("specTables", [])
                m["photo"] = m.get("photo") or src.get("photo")
                m["specFromName"] = src["name"]
    for v in models.values():
        v.sort(key=lambda x: (x["vendor"], x["model"]))
    l3 = load_json(os.path.join(DATA, "l3-status.json"))
    # 용어 사전 — 영문 사양 이름을 한글·설명·시뮬레이터 쓰임새로 옮긴다
    terms = load_json(os.path.join(DATA, "spec-terms.json"))["terms"]
    return equips, models, l3, terms


def load_purpose_dataset():
    """화면 설명용으로 목적별 데이터셋을 작게 싣는다.

    전체 dataset에는 L3 전체 포인트가 다시 들어 있어 HTML이 불필요하게 커진다.
    여기서는 모델 상세에서 바로 보여 줄 matched/missing 판정만 남긴다.
    """
    import datasets

    raw = datasets.build_dataset(PUBLIC_MODEL_EQUIP_IDS)
    out = {}
    for mid, m in raw["modelMappings"].items():
        out[mid] = {
            "counts": m["counts"],
            "unitModels": m.get("unitModels", []),
            "electricalRows": m.get("electricalRows", []),
            "templatePointMappings": m["templatePointMappings"],
            "simulatorRequirementMappings": [{
                "requirementName": r["requirementName"],
                "unit": r["unit"],
                "condition": r["condition"],
                "status": r["status"],
                "matchedInputs": [{
                    "name": x.get("name"),
                    "label": x.get("label"),
                    "value": x.get("value") or x.get("valueRange"),
                    "unit": x.get("unit"),
                    "condition": x.get("condition"),
                    "simulatorUse": x.get("simulatorUse"),
                    "sourceKind": x.get("sourceKind"),
                } for x in (r.get("matchedInputs") or [])[:3]],
            } for r in m["simulatorRequirementMappings"]],
        }
    return out


def main():
    equips, models, l3, terms = load()
    purpose = load_purpose_dataset()
    src = open(TPL, encoding="utf-8").read()
    html = src[src.index('HTML = r"""') + len('HTML = r"""'):src.rindex('"""')]
    # 형번 속성 사전 — 화면 열·라벨·역할 구성의 정본 (설비 클래스별)
    unit_schema = load_json(os.path.join(DATA, "unit-schema.json"))
    data = {"equips": equips, "models": models, "l3": l3,
            "domOrder": DOM_ORDER, "terms": terms, "purpose": purpose,
            "unitSchema": unit_schema}
    totp = sum(e["np"] for e in equips)
    tots = sum(e["ns"] for e in equips)
    nmodel = sum(len(v) for v in models.values())
    nmpts = sum(len(m["points"]) for v in models.values() for m in v)
    # 사양이 있는 모델 수 — 어느 모델을 눌러야 정격이 나오는지 화면에서 알려면 필요하다
    nspec = sum(1 for v in models.values() for m in v
                if m.get("specTables") or m.get("variants") or m.get("spec"))
    out = (html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
               .replace("__NEQ__", str(len(equips))).replace("__TOTP__", str(totp))
               .replace("__NMODEL__", str(nmodel)).replace("__NMPTS__", str(nmpts))
               .replace("__NSPEC__", str(nspec)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(out)
    print("빌드 완료 → %s  (%.0f KB)" % (os.path.relpath(OUT, ROOT), len(out.encode()) / 1024))
    print("  장비 %d계열 · 공통 포인트 %d · 모델 %d건 · 모델 포인트 %d점 · 정격 사양 %d모델"
          % (len(equips), totp, nmodel, nmpts, nspec))


if __name__ == "__main__":
    main()
