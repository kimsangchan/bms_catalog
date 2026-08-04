# -*- coding: utf-8 -*-
"""형번 확정 데이터셋(골든 레코드) 동기화 — 추출은 제안, data/units/ 가 정본.

만든 이유: PDF 표 추출(인식 사다리)이 화면에 직결돼 있어 벤더마다 새 표 모양이
나올 때마다 화면 사고가 그대로 노출됐다 (Carrier 눌린 행 등 반복). 현업(PIM/MDM)
방식대로 뒤집는다 — 속성 사전(data/unit-schema.json)에 맞춘 확정 데이터셋을 두고,
추출기는 거기에 '제안'만 쓰며, 화면·데이터셋 빌드는 확정본만 읽는다.

생존 규칙 (골든 레코드 survivorship):
  extracted  자동 추출 제안 — --sync 가 자유롭게 갱신·삭제한다
  verified   사람 확인 — 동기화가 절대 덮지 않는다. 추출이 달라지면 드리프트 보고만
  manual     수기 입력 — 추출이 못 만드는 값(문서 한계). 동기화가 건드리지 않는다

실행:
  python units.py --sync [--only <모델ID>]     추출 제안을 확정본에 반영
  python units.py --diff [--only <모델ID>]     쓰지 않고 바뀔 내용만 보고
  python units.py --verify <모델ID> [형번...]   extracted → verified 승격 (생략=전체)
  python units.py --status                     모델별 확정본 현황
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UNITS_DIR = os.path.join(DATA, "units")
SCHEMA_PATH = os.path.join(DATA, "unit-schema.json")
sys.path.insert(0, HERE)
import datasets  # noqa: E402


def load_schema():
    return json.load(open(SCHEMA_PATH, encoding="utf-8"))


def field_ids(schema):
    """공유 속성 사전(features)의 전 필드 id — 클래스(설비)별 세트는 화면 구성용이고
    저장·검증은 사전 전체를 기준으로 한다."""
    return list(schema["features"].keys())


def unit_path(model_id):
    return os.path.join(UNITS_DIR, "%s.json" % model_id)


def unit_key(rec):
    """레코드 식별 키 — 같은 크기 코드가 시리즈(쪽)마다 있는 문서(Envistar)가 있어
    형번만으로는 안 되고 쪽수까지 본다."""
    page = (rec.get("source") or {}).get("page")
    return "%s@p%s" % (rec.get("unitModelNumber"), page)


def extraction_records(model, schema):
    """datasets.unit_models 의 평평한 제안 행 → 확정본 레코드 모양.

    값이 없는 필드('—')는 저장하지 않는다 — 확정본에는 사실만 두고
    빈칸 채우기는 화면 어댑터가 한다.
    """
    ids = field_ids(schema)
    out = []
    for row in datasets.unit_models(model):
        fields = {}
        for fid in ids:
            value = row.get(fid)
            if not value or value == "—":
                continue
            entry = {"value": value}
            unit = (row.get("units") or {}).get(fid)
            if unit:
                entry["unit"] = unit
            fields[fid] = entry
        out.append({
            "unitModelNumber": row.get("unitModelNumber"),
            "unitNumberKind": row.get("unitNumberKind"),
            "unitRole": row.get("unitRole"),
            "status": "extracted",
            "fields": fields,
            "source": {
                "file": row.get("sourceFile"),
                "page": row.get("sourcePage"),
                "table": row.get("sourceTable"),
            },
        })
    return out


def merge_units(stored, extracted):
    """생존 규칙 적용 병합. 반환 (병합 목록, 변경 로그).

    로그 항목: (kind, key) — add 신규 / update 제안 갱신 / drift 확정본과 추출이
    달라짐(덮지 않음) / orphan 추출이 더는 못 만드는 확정본(남김) / drop 사라진 제안.
    """
    by_key = {unit_key(r): r for r in stored}
    seen = set()
    merged, log = [], []
    for rec in extracted:
        key = unit_key(rec)
        seen.add(key)
        old = by_key.get(key)
        if old is None:
            merged.append(rec)
            log.append(("add", key))
        elif old.get("status") in ("verified", "manual"):
            merged.append(old)
            if old.get("fields") != rec["fields"]:
                log.append(("drift", key))
        else:
            if old.get("fields") != rec["fields"] or old.get("source") != rec["source"]:
                log.append(("update", key))
            merged.append(rec)
    for key, old in by_key.items():
        if key in seen:
            continue
        if old.get("status") in ("verified", "manual"):
            merged.append(old)
            log.append(("orphan", key))
        else:
            log.append(("drop", key))
    return merged, log


def load_stored(model_id):
    path = unit_path(model_id)
    if not os.path.exists(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def sync(only=None, write=True):
    schema = load_schema()
    os.makedirs(UNITS_DIR, exist_ok=True)
    models = datasets.load_models()
    changed = 0
    for mid, model in sorted(models.items()):
        if only and mid != only:
            continue
        extracted = extraction_records(model, schema)
        stored_doc = load_stored(mid)
        stored = (stored_doc or {}).get("units") or []
        if not extracted and not stored:
            continue
        merged, log = merge_units(stored, extracted)
        if not log and stored_doc is not None:
            continue
        changed += 1
        kinds = {}
        for kind, _key in log:
            kinds[kind] = kinds.get(kind, 0) + 1
        print("%s%s: %d건 — %s" % (
            "" if write else "[diff] ", mid, len(merged),
            ", ".join("%s %d" % (k, n) for k, n in sorted(kinds.items())) or "신규 파일"))
        for kind, key in log:
            if kind in ("drift", "orphan"):
                print("   ⚠ %s: %s — 사람 확정본이라 덮지 않음. 원문 재확인 필요" % (kind, key))
        if write:
            doc = {
                "modelId": mid,
                "equipId": model.get("equipId"),
                "schemaVersion": schema.get("version", 1),
                "units": merged,
            }
            with open(unit_path(mid), "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=1)
                f.write("\n")
    if not changed:
        print("변경 없음 — 확정본이 추출 제안과 일치한다.")
    return changed


def verify(model_id, codes):
    doc = load_stored(model_id)
    if doc is None:
        print("확정본 없음: %s — 먼저 units.py --sync" % model_id)
        return 1
    want = set(codes)
    hit = 0
    for rec in doc.get("units") or []:
        if want and rec.get("unitModelNumber") not in want:
            continue
        if rec.get("status") == "extracted":
            rec["status"] = "verified"
            hit += 1
    with open(unit_path(model_id), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("%s: %d건 verified 승격" % (model_id, hit))
    return 0


def status():
    import glob
    total = {"extracted": 0, "verified": 0, "manual": 0}
    for path in sorted(glob.glob(os.path.join(UNITS_DIR, "*.json"))):
        doc = json.load(open(path, encoding="utf-8"))
        tally = {}
        for rec in doc.get("units") or []:
            st = rec.get("status") or "extracted"
            tally[st] = tally.get(st, 0) + 1
            total[st] = total.get(st, 0) + 1
        print("%-64s %s" % (doc.get("modelId"),
                            " ".join("%s %d" % (k, n) for k, n in sorted(tally.items()))))
    print("─" * 72)
    print("계: " + " ".join("%s %d" % (k, n) for k, n in sorted(total.items()) if n))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--verify", metavar="MODEL_ID")
    parser.add_argument("codes", nargs="*", help="--verify 대상 형번 (생략=전체)")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--only", metavar="MODEL_ID")
    args = parser.parse_args(argv)
    if args.sync:
        sync(only=args.only, write=True)
    elif args.diff:
        sync(only=args.only, write=False)
    elif args.verify:
        return verify(args.verify, args.codes)
    elif args.status:
        status()
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
