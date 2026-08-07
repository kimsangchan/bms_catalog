# -*- coding: utf-8 -*-
"""형번 정격 CSV 내보내기.

HTML은 검토용이고, 시뮬레이터·BMS 매핑은 표 형태 입력이 필요하다. 정본은
data/units/<모델>.json 이므로 그 골든 레코드를 long/wide CSV 두 가지로 편다.

실행:
  python export_units.py
"""
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "datasets")
UNITS = os.path.join(DATA, "units")
PUBLIC_EQUIP_IDS = {"e5"}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def model_meta():
    out = {}
    for path in glob.glob(os.path.join(DATA, "models", "*.json")):
        m = load_json(path)
        out[m["id"]] = {
            "equipId": m.get("equipId") or "",
            "vendor": m.get("vendor") or "",
            "model": m.get("model") or "",
            "name": m.get("name") or "",
        }
    return out


def feature_meta():
    schema = load_json(os.path.join(DATA, "unit-schema.json"))
    return schema.get("features") or {}, schema.get("classes") or {}


def unit_docs():
    for path in sorted(glob.glob(os.path.join(UNITS, "*.json"))):
        doc = load_json(path)
        if (doc.get("equipId") or "") not in PUBLIC_EQUIP_IDS:
            continue
        yield doc


def long_rows(models, features):
    for doc in unit_docs():
        meta = models.get(doc.get("modelId"), {})
        for unit in doc.get("units") or []:
            source = unit.get("source") or {}
            base = {
                "modelId": doc.get("modelId") or "",
                "equipId": doc.get("equipId") or meta.get("equipId") or "",
                "vendor": meta.get("vendor") or "",
                "model": meta.get("model") or "",
                "unitModelNumber": unit.get("unitModelNumber") or "",
                "unitNumberKind": unit.get("unitNumberKind") or "",
                "unitRole": unit.get("unitRole") or "",
                "status": unit.get("status") or "",
                "sourceFile": source.get("file") or "",
                "sourcePage": source.get("page") or "",
                "sourceTable": source.get("table") or "",
            }
            for fid, entry in sorted((unit.get("fields") or {}).items()):
                fmeta = features.get(fid) or {}
                row = dict(base)
                row.update({
                    "fieldId": fid,
                    "fieldKo": fmeta.get("ko") or "",
                    "value": (entry or {}).get("value") or "",
                    "unit": (entry or {}).get("unit") or fmeta.get("convUnit") or "",
                })
                yield row


def wide_rows(models, features, classes):
    feature_ids = list(features)
    for doc in unit_docs():
        meta = models.get(doc.get("modelId"), {})
        equip_id = doc.get("equipId") or meta.get("equipId") or ""
        ordered = []
        cls = classes.get(equip_id) or {}
        for fid in (cls.get("table") or []) + (cls.get("detailExtra") or []) + feature_ids:
            if fid in features and fid not in ordered:
                ordered.append(fid)
        for unit in doc.get("units") or []:
            source = unit.get("source") or {}
            row = {
                "modelId": doc.get("modelId") or "",
                "equipId": equip_id,
                "vendor": meta.get("vendor") or "",
                "model": meta.get("model") or "",
                "unitModelNumber": unit.get("unitModelNumber") or "",
                "unitNumberKind": unit.get("unitNumberKind") or "",
                "unitRole": unit.get("unitRole") or "",
                "status": unit.get("status") or "",
                "sourceFile": source.get("file") or "",
                "sourcePage": source.get("page") or "",
                "sourceTable": source.get("table") or "",
            }
            fields = unit.get("fields") or {}
            for fid in ordered:
                entry = fields.get(fid) or {}
                row[fid] = entry.get("value") or ""
                row[fid + "Unit"] = entry.get("unit") or ""
            yield row


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        count = 0
        for row in rows:
            w.writerow(row)
            count += 1
    return count


def main():
    models = model_meta()
    features, classes = feature_meta()
    base_cols = [
        "modelId", "equipId", "vendor", "model", "unitModelNumber",
        "unitNumberKind", "unitRole", "status", "sourceFile", "sourcePage", "sourceTable",
    ]
    long_cols = base_cols + ["fieldId", "fieldKo", "value", "unit"]
    n_long = write_csv(os.path.join(OUT, "unit-models-long.csv"),
                       long_rows(models, features), long_cols)

    wide_feature_cols = []
    for fid in features:
        wide_feature_cols.extend([fid, fid + "Unit"])
    n_wide = write_csv(os.path.join(OUT, "unit-models-wide.csv"),
                       wide_rows(models, features, classes), base_cols + wide_feature_cols)
    print("CSV 내보내기 완료")
    print("  data/datasets/unit-models-long.csv  %d행" % n_long)
    print("  data/datasets/unit-models-wide.csv  %d행" % n_wide)


if __name__ == "__main__":
    main()
