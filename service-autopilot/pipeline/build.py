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

DOM_ORDER = ["공기측 설비", "열원·수측 설비", "반송·구동", "계측·제어", "전력 설비",
             "조명·차양", "방재", "승강", "보안·출입", "환경·공기질", "급배수·위생"]


def load():
    equips = []
    for f in sorted(glob.glob(os.path.join(DATA, "equips", "*.json")),
                    key=lambda p: int(os.path.basename(p)[1:-5])):
        e = json.load(open(f, encoding="utf-8"))
        equips.append({
            "id": e["id"], "no": e["no"], "title": e["title"], "domain": e["domain"],
            "head": e.get("tagSummary", ""), "notes": e.get("notes", []),
            "spec": e.get("specTables", []), "points": e.get("pointTables", []),
            "np": sum(len(t["rows"]) for t in e.get("pointTables", [])),
            "ns": sum(len(t["rows"]) for t in e.get("specTables", [])),
        })
    models = {}
    docs_by_model = {}
    for d in json.load(open(os.path.join(DATA, "docs.json"), encoding="utf-8")):
        docs_by_model.setdefault(d["modelId"], []).append(
            [d["kind"], d["title"], d["publisher"], d["docNo"], d["issued"], d["url"], d["status"]])
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = json.load(open(f, encoding="utf-8"))
        base = m["id"].rsplit("-idu", 1)[0].rsplit("-odu", 1)[0]
        models.setdefault(m["equipId"], []).append({
            "vendor": m["vendor"], "model": m["model"], "name": m["name"],
            "cat": m["cat"], "tag": m["tag"], "status": m.get("status", "active"),
            "summary": m.get("summary", ""), "has": m.get("has", {}),
            "spec": m.get("spec", []), "comm": m.get("comm", []), "io": m.get("io", []),
            "elec": m.get("elec"), "gap": m.get("gap", ""),
            "docs": docs_by_model.get(m["id"]) or docs_by_model.get(base) or [],
            "points": [{"inst": p["inst"], "type": p["type"],
                        "unitDisp": p.get("unitRaw") or "—", "name": p["name"],
                        "note": p.get("note", "")} for p in m.get("points", [])],
        })
    for v in models.values():
        v.sort(key=lambda x: (x["vendor"], x["model"]))
    l3 = json.load(open(os.path.join(DATA, "l3-status.json"), encoding="utf-8"))
    return equips, models, l3


def main():
    equips, models, l3 = load()
    src = open(TPL, encoding="utf-8").read()
    html = src[src.index('HTML = r"""') + len('HTML = r"""'):src.rindex('"""')]
    data = {"equips": equips, "models": models, "l3": l3, "domOrder": DOM_ORDER}
    totp = sum(e["np"] for e in equips)
    tots = sum(e["ns"] for e in equips)
    nmodel = sum(len(v) for v in models.values())
    nmpts = sum(len(m["points"]) for v in models.values() for m in v)
    out = (html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
               .replace("__NEQ__", str(len(equips))).replace("__TOTP__", str(totp))
               .replace("__NMODEL__", str(nmodel)).replace("__NMPTS__", str(nmpts)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(out)
    print("빌드 완료 → %s  (%.0f KB)" % (os.path.relpath(OUT, ROOT), len(out.encode()) / 1024))
    print("  장비 %d계열 · 공통 포인트 %d · 사양 %d · 모델 %d건 · 모델 포인트 %d점"
          % (len(equips), totp, tots, nmodel, nmpts))


if __name__ == "__main__":
    main()
