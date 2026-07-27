# -*- coding: utf-8 -*-
"""1회성 이관 — 흩어진 저장소를 JSON 한 벌로 모은다.

  08-equip-spec-tag-catalog.md   (마크다운 표)   → data/equips/*.json
  evidence/models*.py            (파이썬 딕셔너리) → data/models/*.json
  evidence/*.json                (파서 결과)      → 위 모델 안에 흡수
                                                 → data/docs.json (문서 메타 분리)

실행 후에는 파이썬 파일이 데이터 저장소가 아니게 된다.
"""
import json, os, re, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EV = os.path.join(ROOT, "evidence")
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import schema as S  # noqa: E402

DOMAIN = {
    5: "공기측 설비", 6: "공기측 설비", 7: "공기측 설비", 8: "공기측 설비",
    9: "열원·수측 설비", 10: "열원·수측 설비", 11: "열원·수측 설비", 12: "열원·수측 설비",
    13: "반송·구동", 14: "반송·구동", 15: "반송·구동", 16: "계측·제어",
    19: "전력 설비", 20: "조명·차양", 21: "방재", 22: "승강", 23: "보안·출입",
    24: "환경·공기질", 25: "급배수·위생",
}


def load_py(name):
    p = os.path.join(EV, name)
    spec = importlib.util.spec_from_file_location(name[:-3], p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── 1) 장비 계열 : 마크다운 → JSON
def md_tables(body):
    tables, cur = [], None
    for ln in body:
        if ln.startswith("|") and ln.rstrip().endswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cur is None:
                cur = {"header": cells, "rows": []}
            elif not re.match(r"^[\s:\-|]+$", ln):
                cur["rows"].append(cells)
        else:
            if cur and cur["rows"]:
                tables.append(cur)
            cur = None
    if cur and cur["rows"]:
        tables.append(cur)
    for t in tables:
        t["rows"] = [r for r in t["rows"] if not all(re.match(r"^[:\-\s]*$", c) for c in r)]
    return [t for t in tables if t["rows"]]


def migrate_equips():
    src = os.path.join(ROOT, "08-equip-spec-tag-catalog.md")
    lines = open(src, encoding="utf-8").read().split("\n")
    secs, cur = [], None
    for ln in lines:
        m = re.match(r"^# (\d+)\.\s*(.+)$", ln)
        if m:
            cur = {"no": int(m.group(1)), "title": m.group(2).strip(), "body": []}
            secs.append(cur)
        elif re.match(r"^# ", ln):
            cur = None
        elif cur is not None:
            cur["body"].append(ln)

    os.makedirs(os.path.join(DATA, "equips"), exist_ok=True)
    out = []
    for s in secs:
        if s["no"] not in DOMAIN:
            continue
        head = []
        for ln in s["body"][:14]:
            t = ln.strip()
            if t.startswith("**") or t.startswith("구역 태그"):
                head.append(t)
            elif head and t and not t.startswith(("|", "#", ">")):
                head.append(t)
            elif head and (t.startswith("|") or t.startswith("#")):
                break
        tabs = md_tables(s["body"])
        spec, pts = [], []
        for t in tabs:
            h = " ".join(t["header"])
            (pts if ("종류" in h and "역할" in h) or "태그 조합" in h or "마커셋" in h
             else spec).append(t)
        eid = "e%d" % s["no"]
        rec = {
            "id": eid, "no": s["no"], "title": s["title"], "domain": DOMAIN[s["no"]],
            "tagSummary": " ".join(head),
            "notes": [l.strip().lstrip("> ") for l in s["body"] if l.strip().startswith(">")],
            "specTables": spec, "pointTables": pts,
            "source": {"file": "08-equip-spec-tag-catalog.md", "section": s["no"]},
        }
        json.dump(rec, open(os.path.join(DATA, "equips", eid + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        out.append(rec)
    return out


# ── 2) 모델 : 파이썬 딕셔너리 → JSON
def migrate_models():
    m = load_py("models.py")
    os.makedirs(os.path.join(DATA, "models"), exist_ok=True)
    docs, recs = [], []
    for eno, lst in m.MODELS.items():
        for md in lst:
            mid = S.model_id(md["vendor"], md["model"])
            pts = []
            for p in md.get("points", []):
                if p.get("inst") is None:
                    continue
                pts.append({
                    "type": S.canon_type(p.get("type")),
                    "inst": p.get("inst"),
                    "name": p.get("name", ""),
                    "unitRaw": p.get("unitDisp") or None,
                    "unit": S.canon_unit(p.get("unitDisp")),
                    "note": p.get("note", ""),
                })
            for d in md.get("docs", []):
                docs.append({
                    "modelId": mid, "kind": d[0], "title": d[1], "publisher": d[2],
                    "docNo": d[3], "issued": d[4], "url": d[5], "status": d[6],
                })
            rec = {
                "id": mid, "equipId": "e%d" % eno,
                "vendor": md["vendor"], "model": md["model"], "name": md["name"],
                "cat": md["cat"], "tag": md["tag"], "status": md.get("status", "active"),
                "summary": md.get("summary", ""),
                "has": md.get("has", {}), "ede": bool(md.get("ede")),
                "spec": md.get("spec", []), "comm": md.get("comm", []), "io": md.get("io", []),
                "elec": md.get("elec"), "points": pts, "gap": md.get("gap", ""),
                "extractor": "ede" if md.get("ede") else ("table" if pts else "manual"),
            }
            json.dump(rec, open(os.path.join(DATA, "models", mid + ".json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            recs.append(rec)
    json.dump(docs, open(os.path.join(DATA, "docs.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # L3 확보 현황도 함께
    json.dump({("e%d" % k): v for k, v in m.L3_STATUS.items()},
              open(os.path.join(DATA, "l3-status.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return recs, docs


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    eq = migrate_equips()
    md, dc = migrate_models()
    npts = sum(len(x["points"]) for x in md)
    print("장비 계열 %d건  → data/equips/" % len(eq))
    print("모델     %d건 (포인트 %d점) → data/models/" % (len(md), npts))
    print("문서     %d건 → data/docs.json" % len(dc))
    nu = sum(1 for x in md for p in x["points"] if S.unit_state(p["unitRaw"]) == "unknown")
    print("단위 정규화 실패 %d건 (canon 매핑 필요)" % nu)
