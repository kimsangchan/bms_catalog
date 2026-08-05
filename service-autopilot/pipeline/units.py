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

스키마 우선 규칙: 설비 클래스(unit-schema.json classes)가 정의되지 않은 설비는
--sync 가 확정본을 만들지 않는다. 새 설비 계열의 첫 수집은
--propose-class 로 초안을 떠서 사전에 먼저 정의한다.

실행:
  python units.py --sync [--only <모델ID>]     추출 제안을 확정본에 반영
  python units.py --diff [--only <모델ID>]     쓰지 않고 바뀔 내용만 보고
  python units.py --verify <모델ID> [형번...]   extracted → verified 승격 (생략=전체)
  python units.py --status                     모델별 확정본 현황
  python units.py --propose-class <설비ID>     새 설비 계열의 classes 블록 초안
"""
import argparse
import json
import os
import re
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


def normalize_entry(fid, value, unit, schema):
    """표기 정규화 계층 — 값의 의미는 절대 바꾸지 않고 표기 흔들림만 통일한다.

    규칙의 정본은 unit-schema.json 의 normalize 블록이다 (PIM 의
    취입→정규화→확정 순서). 척도가 다른 단위는 섞지 않는다.
    """
    rules = schema.get("normalize") or {}
    value = (value or "").strip()
    if fid == "capacityClass":
        value = re.sub(r"^(\d+(?:\.\d+)?)\s*Ton$", r"\1 Tons", value)
    if fid in ("eer", "ieer"):
        unit = ""  # 정의 단위(Btu/h per W) — 표기 생략 통일
        value = re.sub(r"^\s*I?EER\s*=\s*", "", value)
        value = re.sub(r",\s*I?EER\s*=\s*", ", ", value)
        if re.match(r"^[-\s]+$", value):
            value = ""  # '-' 자리표시 = 값 없음
    if unit:
        unit = (rules.get("unitSpelling") or {}).get(unit, unit)
    return value, unit


def extraction_records(model, schema):
    """datasets.unit_models 의 평평한 제안 행 → 확정본 레코드 모양.

    값이 없는 필드('—')는 저장하지 않는다 — 확정본에는 사실만 두고
    빈칸 채우기는 화면 어댑터가 한다. 표기는 normalize_entry 로 통일한다.
    """
    ids = field_ids(schema)
    out = []
    for row in datasets.unit_models(model):
        fields = {}
        for fid in ids:
            value = row.get(fid)
            if not value or value == "—":
                continue
            value, unit = normalize_entry(
                fid, value, (row.get("units") or {}).get(fid), schema)
            if not value:
                continue
            entry = {"value": value}
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
    classes = schema.get("classes") or {}
    os.makedirs(UNITS_DIR, exist_ok=True)
    models = datasets.load_models()
    changed = 0
    missing_class = {}
    for mid, model in sorted(models.items()):
        if only and mid != only:
            continue
        extracted = extraction_records(model, schema)
        # 스키마 우선 규칙 — 설비 클래스가 사전에 정의되기 전에는 확정본을 만들지
        # 않는다. 새 설비 계열의 첫 수집은 units.py --propose-class 로 초안을 떠서
        # unit-schema.json classes 에 먼저 넣는다 (열 구성·라벨·역할이 설비마다 다르다).
        if extracted and model.get("equipId") not in classes:
            missing_class.setdefault(model.get("equipId"), []).append(mid)
            continue
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
    if missing_class:
        print("✗ 스키마 클래스 미정의 설비 — 확정본을 만들지 않았다.")
        for eq, mids in sorted(missing_class.items()):
            print("   %s (%d모델): python units.py --propose-class %s 로 초안을 떠서"
                  " unit-schema.json classes 에 먼저 정의" % (eq, len(mids), eq))
        return -1
    if not changed:
        print("변경 없음 — 확정본이 추출 제안과 일치한다.")
    return changed


def propose_class(equip_id):
    """새 설비 계열의 클래스 초안 — 그 설비 모델들의 추출 제안에서 필드·역할
    사용 빈도를 세어 unit-schema.json classes 에 붙여 넣을 블록을 만들어 준다.

    어디까지나 초안이다 — 한글 이름, 설비 관점에서 뜻이 달라지는 라벨
    (labels 오버라이드, 예: 냉동기의 코일·팬 = 응축기 쪽), 역할별 상세 순서는
    사람이 원문을 보고 다듬는다. 제조사가 달라도 필드는 공유 사전(features)의
    id 만 쓰므로 클래스는 벤더 중립으로 유지된다.
    """
    schema = load_schema()
    fields, roles = {}, {}
    for model in datasets.load_models().values():
        if model.get("equipId") != equip_id:
            continue
        for rec in extraction_records(model, schema):
            roles[rec.get("unitRole") or "?"] = roles.get(rec.get("unitRole") or "?", 0) + 1
            for fid in rec["fields"]:
                fields[fid] = fields.get(fid, 0) + 1
    if not fields:
        print("%s: 추출 제안이 없다 — 인식 사다리(datasets.unit_models)부터 확인" % equip_id)
        return 1
    order = [fid for fid, _n in sorted(fields.items(), key=lambda x: (-x[1], x[0]))
             if fid != "capacityClass"]
    block = {equip_id: {
        "ko": "<설비 이름 — 사람이 채운다>",
        "table": ["capacityClass"] + order,
        "detailExtra": [],
        "roles": {role: {"ko": "<역할 이름 — 사람이 채운다>", "detail": order[:5]}
                  for role in sorted(roles)},
    }}
    print("# 필드 사용 빈도: " + ", ".join(
        "%s %d" % (fid, n) for fid, n in sorted(fields.items(), key=lambda x: -x[1])))
    print("# unit-schema.json 의 classes 에 붙여 넣고 한글 이름·라벨 오버라이드를 다듬는다:")
    print(json.dumps(block, ensure_ascii=False, indent=1))
    return 0


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
    parser.add_argument("--propose-class", metavar="EQUIP_ID",
                        help="새 설비 계열의 classes 블록 초안 생성 (스키마 우선 규칙)")
    args = parser.parse_args(argv)
    if args.propose_class:
        return propose_class(args.propose_class)
    if args.sync:
        return 1 if sync(only=args.only, write=True) < 0 else 0
    elif args.diff:
        return 1 if sync(only=args.only, write=False) < 0 else 0
    elif args.verify:
        return verify(args.verify, args.codes)
    elif args.status:
        status()
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
