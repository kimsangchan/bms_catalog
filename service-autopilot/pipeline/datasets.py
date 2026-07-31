# -*- coding: utf-8 -*-
"""목적별 데이터셋 생성.

원본 JSON은 벤더 문서를 최대한 보존한다. 여기서는 BMS 템플릿과 시뮬레이터가 바로
쓰기 쉽도록 같은 정보를 세 등급으로 나눠 생성한다.

  1. equipmentTemplates  장비 종류별 L2 템플릿
  2. modelMappings       모델별 L3 원문 매핑 + L2 후보 + 시뮬레이터 입력
  3. referenceTables     성능표·치수·부속 참고표 목록

실행:
  python datasets.py
  python datasets.py --equip e5
"""
import argparse
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "datasets")


AHU_PROFILE = [
    {"name": "급기온도", "include": r"(?:supply|discharge).*air.*temp|discharge.*temp",
     "exclude": r"setpoint|sp\b|reheat|refrigerant"},
    {"name": "환기온도", "include": r"return.*air.*temp", "exclude": r"setpoint|sp\b"},
    {"name": "외기온도", "include": r"outdoor.*air.*temperature|outside.*air.*temperature|outdoortemp",
     "exclude": r"flow|enthalpy|humidity|setpoint|sp\b|enable|min"},
    {"name": "급기정압", "include": r"(?:supply|discharge).*static.*pressure|duct.*static",
     "exclude": r"setpoint|sp\b"},
    {"name": "급기온도 설정값", "include": r"(?:supply|discharge).*temp.*setpoint|discharge.*cooling.*setpoint"},
    {"name": "급기정압 설정값", "include": r"static.*pressure.*setpoint"},
    {"name": "팬 지령/상태", "include": r"fan.*(?:command|status|speed|frequency)|(?:supply|return).*fan",
     "exclude": r"type|configuration|identifier"},
    {"name": "외기댐퍼", "include": r"outdoor.*air.*damper|outside.*air.*damper",
     "exclude": r"minimum|min|setpoint|sp\b"},
    {"name": "냉수·냉방", "include": r"cool(?:ing)?|chilled.*water|cooling.*capacity",
     "exclude": r"type|configuration|identifier|enable|setpoint|sp\b"},
    {"name": "온수·난방", "include": r"heat(?:ing)?|hot.*water",
     "exclude": r"type|configuration|identifier|enable|setpoint|sp\b"},
    {"name": "필터/차압", "include": r"filter|differential.*pressure"},
    {"name": "경보/고장", "include": r"alarm|fault|emergency|freeze|lockout"},
]

VIEW_PROFILES = {"e5": AHU_PROFILE}

POINT_TIER_HELP = {
    "template": "L2 템플릿 후보 — BMS 기본 화면에 먼저 올릴 포인트",
    "control": "제어·설정 — 쓰기/지령/설정값 후보",
    "alarm": "경보·고장 — 알람 화면과 이력에 연결",
    "telemetry": "상태·계측 — 상세 감시값",
    "config": "설정·식별 — 시운전/엔지니어링용",
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_terms():
    return load_json(os.path.join(DATA, "spec-terms.json")).get("terms", [])


def term_of(label, terms):
    text = str(label or "").strip()
    for pattern, ko, desc, sim, cat in terms:
        if re.search(pattern, text, re.I):
            return {"ko": ko, "desc": desc, "sim": sim, "category": cat}
    return None


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def row_cells(row):
    if isinstance(row, list):
        return [clean_text(x) for x in row]
    return [clean_text(row)]


def numbers(values):
    out = []
    for value in values:
        text = clean_text(value).replace(",", "")
        text = re.sub(r"(\d)\s*[-–]\s*(?=\d)", r"\1 ", text)
        for match in re.findall(r"-?\d+(?:\.\d+)?", text):
            try:
                out.append(float(match))
            except ValueError:
                pass
    return out


def fmt_num(value):
    return str(int(value)) if value == int(value) else ("%g" % value)


def template_points(equip):
    rows = []
    for table in equip.get("pointTables") or []:
        for row in table.get("rows") or []:
            cells = row_cells(row)
            if len(cells) < 6:
                continue
            rows.append({
                "name": cells[0],
                "objectType": cells[1],
                "unit": cells[2],
                "role": cells[3],
                "tags": cells[4],
                "grade": cells[5],
                "datasetTier": "template",
            })
    return rows


def simulator_requirements(equip):
    rows = []
    for table in equip.get("specTables") or []:
        for row in table.get("rows") or []:
            cells = row_cells(row)
            if len(cells) < 3:
                continue
            rows.append({
                "name": cells[0],
                "unit": cells[1],
                "condition": cells[2],
                "requiredFor": "simulator",
            })
    return rows


def point_text(point):
    return "%s %s" % (point.get("name") or "", point.get("note") or "")


def find_template_candidates(equip_id, points):
    profile = VIEW_PROFILES.get(equip_id) or []
    picked = []
    seen_names = set()
    for rule in profile:
        include = re.compile(rule["include"], re.I)
        exclude = re.compile(rule.get("exclude", r"$^"), re.I)
        matches = []
        for point in points:
            if point.get("name") in seen_names:
                continue
            text = point_text(point)
            if not include.search(text) or exclude.search(text):
                continue
            score = 0
            low = text.lower()
            typ = clean_text(point.get("type")).upper()
            if "출력(send)" in low or typ in {"AI", "BI"}:
                score += 30
            if re.search(r"\bstatus\b|active|position|temperature|capacity", low):
                score += 10
            if "입력(recv)" in low or typ == "NCI":
                score -= 20
            if re.search(r"setpoint|configuration|type identifier|enable|min", low):
                score -= 15
            matches.append((score, point))
        if not matches:
            continue
        point = sorted(matches, key=lambda item: (-item[0], item[1].get("inst") or 999999))[0][1]
        seen_names.add(point.get("name"))
        picked.append({
            "templateName": rule["name"],
            "sourceName": point.get("name"),
            "type": point.get("type"),
            "instance": point.get("inst"),
            "unit": point.get("unit") or point.get("unitRaw"),
            "note": point.get("note", ""),
        })
    return picked


def template_point_mappings(equip_id, template_rows, points):
    candidates = {
        item["templateName"]: item
        for item in find_template_candidates(equip_id, points)
    }
    out = []
    for row in template_rows:
        candidate = candidates.get(row["name"])
        item = {
            "templateName": row["name"],
            "objectType": row["objectType"],
            "unit": row["unit"],
            "grade": row["grade"],
            "role": row["role"],
            "tags": row["tags"],
            "status": "matched" if candidate else "missing",
            "matchedPoint": None,
        }
        if candidate:
            item["matchedPoint"] = {
                "name": candidate["sourceName"],
                "type": candidate["type"],
                "instance": candidate["instance"],
                "unit": candidate["unit"],
                "note": candidate["note"],
            }
        out.append(item)
    return out


def point_tier(point, template_names):
    name = clean_text(point.get("name"))
    text = ("%s %s" % (name, point.get("note") or "")).lower()
    typ = clean_text(point.get("type")).upper()
    if name in template_names:
        return "template"
    if typ == "NCI" or re.search(r"config|version|build|identifier|location|heartbeat", text):
        return "config"
    if re.search(r"alarm|fault|emergency|lockout|freeze|trip", text):
        return "alarm"
    if typ in {"AO", "BO", "AV", "BV", "MSO", "NVI"} or re.search(
        r"command|setpoint|enable|request|override|cmd", text
    ):
        return "control"
    return "telemetry"


def mapping_points(points, template_candidates):
    template_names = {p["sourceName"] for p in template_candidates}
    out = []
    for point in points:
        tier = point_tier(point, template_names)
        out.append({
            "type": point.get("type"),
            "instance": point.get("inst"),
            "name": point.get("name"),
            "unit": point.get("unit"),
            "unitRaw": point.get("unitRaw"),
            "note": point.get("note", ""),
            "datasetTier": tier,
            "tierDescription": POINT_TIER_HELP[tier],
        })
    return out


def spec_rows_from_flat(spec, terms, source_kind):
    rows = []
    for row in spec or []:
        cells = row_cells(row)
        if len(cells) < 3:
            continue
        term = term_of(cells[0], terms)
        if not term or term["sim"] < 2:
            continue
        rows.append({
            "name": cells[0],
            "label": term["ko"],
            "value": cells[1],
            "unit": cells[2],
            "condition": cells[3] if len(cells) > 3 else "",
            "evidence": cells[4] if len(cells) > 4 else "",
            "simulatorUse": "core" if term["sim"] == 3 else "condition",
            "category": term["category"],
            "sourceKind": source_kind,
        })
    return rows


def summarize_table(table, terms):
    if (table.get("kind") or "etc") not in {"rating", "perf"}:
        return []
    rows = [row_cells(r) for r in table.get("rows") or []]
    header = [clean_text(h) for h in table.get("header") or []]
    out = []
    if table.get("orientation") == "row":
        iterable = [(r[0], r[1:]) for r in rows if r]
    else:
        iterable = []
        for idx, label in enumerate(header):
            vals = [r[idx] for r in rows if idx < len(r)]
            iterable.append((label, vals))
    for label, vals in iterable:
        term = term_of(label, terms)
        if not term or term["sim"] < 2:
            continue
        ns = numbers(vals)
        if not ns:
            continue
        lo, hi = min(ns), max(ns)
        out.append({
            "name": label,
            "label": term["ko"],
            "valueRange": fmt_num(lo) if lo == hi else "%s – %s" % (fmt_num(lo), fmt_num(hi)),
            "unit": "",
            "condition": table.get("title", ""),
            "evidence": "%s p%s" % (table.get("source", ""), table.get("page", "")),
            "simulatorUse": "core" if term["sim"] == 3 else "condition",
            "category": term["category"],
            "sourceKind": table.get("kind") or "etc",
        })
    return out


def simulator_inputs(model, terms):
    rows = []
    rows.extend(spec_rows_from_flat(model.get("spec"), terms, "flat"))
    for variant in model.get("variants") or []:
        for row in spec_rows_from_flat(variant.get("spec"), terms, "variant"):
            rows.append(dict(row, variant=variant.get("code")))
    for table in model.get("specTables") or []:
        if (table.get("kind") or "etc") == "rating":
            rows.extend(summarize_table(table, terms))
    return rows


def value_for_label(rows, pattern, col):
    regex = re.compile(pattern, re.I)
    for row in rows:
        cells = row_cells(row)
        if cells and regex.search(cells[0]):
            return cells[col] if col < len(cells) else ""
    return ""


def clean_model_label(value):
    text = clean_text(value)
    if not text or re.search(r"^(system data|cooling performance|efficiency)$", text, re.I):
        return ""
    return text


def unit_models(model):
    """제품군/통신 프로파일 문서 안의 실제 Unit Model Number 후보.

    Trane 공조기 카탈로그는 행=속성, 열=형번인 General data 표를 쓴다.
    프로파일 모델과 실제 장비 형번을 분리하려면 이 열을 다시 1행=형번 구조로 편다.
    """
    if model.get("equipId") != "e5":
        return []
    out = []
    for table in model.get("specTables") or []:
        if (table.get("kind") or "etc") != "rating":
            continue
        if table.get("orientation") != "row":
            continue
        if not re.search(r"general data", table.get("title") or "", re.I):
            continue
        header = row_cells(table.get("header") or [])
        rows = table.get("rows") or []
        first = row_cells(rows[0]) if rows else []
        for col in range(1, len(header)):
            code = clean_model_label(first[col] if col < len(first) else "")
            if not code:
                continue
            role = "airHandler" if re.search(r"\bTWE", code, re.I) else "condensingUnit"
            out.append({
                "unitModelNumber": code,
                "unitRole": role,
                "capacityClass": header[col] or "—",
                "matchedAirHandler": value_for_label(rows, r"matched air handler$", col) or "—",
                "ratedAirflow": (
                    value_for_label(rows, r"AHRI Rated Airflow", col)
                    or value_for_label(rows, r"^CFM$", col)
                    or value_for_label(rows, r"CFM \(Nominal\)", col)
                    or "—"
                ),
                "grossCoolingCapacity": (
                    value_for_label(rows, r"Gross Cooling Capacity - System", col) or "—"
                ),
                "ahriNetCoolingCapacity": (
                    value_for_label(rows, r"AHRI Net Cooling Capacity", col) or "—"
                ),
                "eer": (
                    value_for_label(rows, r"Matched Air Handler \(EER\)|System \(EER\)", col) or "—"
                ),
                "coilFaceArea": value_for_label(rows, r"Face Area", col) or "—",
                "coilRowsFpi": value_for_label(rows, r"Rows/FPI", col) or "—",
                "fanMotorHp": value_for_label(rows, r"Motor HP", col) or "—",
                "fanMotorRpm": value_for_label(rows, r"Motor RPM", col) or "—",
                "sourceTable": table.get("title") or "",
                "sourcePage": table.get("page"),
                "selectionStatus": "unit_candidate",
            })
    return out


def split_tokens(value):
    text = clean_text(value)
    if not text or text.upper() in {"N/A", "NA"}:
        return []
    return re.findall(r"N/A|[A-Za-z]+\d+[A-Za-z0-9/]*|\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?", text)


def at_token(tokens, index):
    if not tokens:
        return ""
    if index < len(tokens):
        return tokens[index]
    return tokens[-1]


def amp_pair(value, index):
    tokens = split_tokens(value)
    if len(tokens) >= (index + 1) * 2:
        return at_token(tokens, index * 2), at_token(tokens, index * 2 + 1)
    return at_token(tokens, index), ""


def electrical_rows(model):
    """Electrical tables normalized to one row per unit-model/voltage option."""
    if model.get("equipId") != "e5":
        return []
    out = []
    for table in model.get("specTables") or []:
        title = table.get("title") or ""
        if not re.search(r"electrical characteristics", title, re.I):
            continue
        header = row_cells(table.get("header") or [])
        rows = [row_cells(row) for row in table.get("rows") or []]
        source = "%s p%s" % (title, table.get("page", ""))
        if "compressor and condenser fan" in title.lower():
            for row in rows:
                if len(row) < 13 or not re.search(r"\bTTA", row[1], re.I):
                    continue
                models = split_tokens(row[1])
                volts = split_tokens(row[2])
                phases = split_tokens(row[3])
                comp1_rla = split_tokens(row[4])
                comp1_lra = split_tokens(row[5])
                comp2_rla = split_tokens(row[6])
                comp2_lra = split_tokens(row[7])
                fan_count = split_tokens(row[8])
                fan_volts = split_tokens(row[9])
                fan_phase = split_tokens(row[10])
                fan_fla = split_tokens(row[11])
                fan_lra = split_tokens(row[12])
                for idx, code in enumerate(models):
                    out.append({
                        "unitModelNumber": code,
                        "unitRole": "condensingUnit",
                        "capacityClass": row[0],
                        "voltage": at_token(volts, idx),
                        "phase": at_token(phases, idx),
                        "motorSet": "compressorAndCondenserFan",
                        "compressor1Rla": at_token(comp1_rla, idx),
                        "compressor1Lra": at_token(comp1_lra, idx),
                        "compressor2Rla": at_token(comp2_rla, idx),
                        "compressor2Lra": at_token(comp2_lra, idx),
                        "fanCount": at_token(fan_count, idx),
                        "fanVoltage": at_token(fan_volts, idx),
                        "fanPhase": at_token(fan_phase, idx),
                        "fanFla": at_token(fan_fla, idx),
                        "fanLra": at_token(fan_lra, idx),
                        "sourceTable": title,
                        "sourcePage": table.get("page"),
                        "source": source,
                    })
            continue
        for row in rows:
            if len(row) < 10 or not re.search(r"\bTWE", row[1], re.I):
                continue
            models = split_tokens(row[1])
            if not models:
                continue
            combined_air_handler = len(row) >= 16
            standard = {
                "unitModelNumbers": models,
                "motorNo": split_tokens(row[2]),
                "voltage": split_tokens(row[3]),
                "phase": split_tokens(row[4]),
                "hp": split_tokens(row[5]),
                "amps": row[6],
                "lra": "" if combined_air_handler else (row[7] if len(row) > 7 else ""),
                "mca": split_tokens(row[7] if combined_air_handler else (row[8] if len(row) > 8 else "")),
                "mop": split_tokens(row[8] if combined_air_handler else (row[9] if len(row) > 9 else "")),
                "option": "standardEvaporatorFan",
            }
            sets = [standard]
            if combined_air_handler:
                sets.append({
                    "unitModelNumbers": models,
                    "motorNo": split_tokens(row[9]),
                    "voltage": split_tokens(row[10]),
                    "phase": split_tokens(row[11]),
                    "hp": split_tokens(row[12]),
                    "amps": row[13],
                    "lra": "",
                    "mca": split_tokens(row[14]),
                    "mop": split_tokens(row[15]),
                    "option": "oversizedEvaporatorFan",
                })
            for item in sets:
                count = max(len(item["voltage"]), len(item["unitModelNumbers"]))
                for idx in range(count):
                    fla, lra = amp_pair(item["amps"], idx)
                    if item["lra"]:
                        lra = at_token(split_tokens(item["lra"]), idx)
                    code = at_token(item["unitModelNumbers"], idx)
                    if not code or code.upper() == "N/A":
                        continue
                    out.append({
                        "unitModelNumber": code,
                        "unitRole": "airHandler",
                        "capacityClass": row[0],
                        "voltage": at_token(item["voltage"], idx),
                        "phase": at_token(item["phase"], idx),
                        "motorSet": item["option"],
                        "motorNo": at_token(item["motorNo"], idx),
                        "motorHp": at_token(item["hp"], idx),
                        "fanFla": fla,
                        "fanLra": lra,
                        "mca": at_token(item["mca"], idx),
                        "mop": at_token(item["mop"], idx),
                        "sourceTable": title,
                        "sourcePage": table.get("page"),
                        "source": source,
                    })
    return out


SIM_REQUIREMENT_RULES = {
    "급기 풍량": {"field": r"\bCFM\b|air ?flow|풍량"},
    "환기 풍량": {"field": r"\bCFM\b|air ?flow|풍량"},
    "최소 외기량": {"field": r"outdoor air.*flow|minimum.*flow|oa.*flow"},
    "기외정압": {"field": r"static pressure|^esp$|정압"},
    "급기팬 형식·모터출력": {
        "field": r"\b(?:hp|kw|bhp)\b|motor.*power|fan.*motor.*(?:hp|kw)",
        "exclude": r"tons|phase|volts|amps|mca|mop|rpm",
    },
    "환기팬 형식·모터출력": {
        "field": r"\b(?:hp|kw|bhp)\b|motor.*power|fan.*motor.*(?:hp|kw)",
        "exclude": r"tons|phase|volts|amps|mca|mop|rpm",
    },
    "냉수코일 능력": {
        "field": r"cooling capacity|냉방.*능력|능력",
        "context": r"cooling|냉수|냉방",
        "exclude": r"tons|air ?flow|entering water temperature",
    },
    "온수코일 능력": {
        "field": r"heating capacity|난방.*능력|능력",
        "context": r"hot water|heating|온수|난방",
        "exclude": r"tons|air ?flow|entering water temperature|gross cooling|net cooling",
    },
    "냉수·온수 유량": {"field": r"water.*flow|flow.*water|gpm|lpm|유량"},
    "코일 열수·핀피치": {"field": r"rows/fpi|fins per inch|코일 열수"},
    "코일 정면풍속": {"field": r"face area|face velocity|면풍속"},
    "필터 형식·효율·차압": {"field": r"filter|pressure drop|efficiency|필터|차압"},
    "가습 방식·가습량": {"field": r"humid|가습"},
    "열회수 유무·효율": {"field": r"energy recovery|heat recovery|efficiency|열회수"},
    "케이싱·단열": {"field": r"cabinet|casing|insulation|케이싱|단열"},
    "전원": {"field": r"voltage|volts|phase|hz|mca|mop|electrical|전압|상수"},
}


def requirement_match_rank(req_name, item):
    label = clean_text(item.get("label"))
    name = clean_text(item.get("name")).lower()
    if req_name == "전원":
        order = [
            ("전압", r"volt|voltage"),
            ("상수", r"phase"),
            ("전류", r"amp|current"),
            ("최소 회선 용량 (MCA)", r"\bmca\b"),
            ("최대 차단기 용량 (MOP)", r"\bmop\b"),
        ]
        for idx, (ko, pat) in enumerate(order):
            if label == ko or re.search(pat, name):
                return idx
    return 99


def simulator_requirement_mappings(requirements, inputs):
    out = []
    for req in requirements:
        rule = SIM_REQUIREMENT_RULES.get(req["name"], {"field": re.escape(req["name"])})
        field_pattern = re.compile(rule["field"], re.I)
        context_pattern = re.compile(rule["context"], re.I) if rule.get("context") else None
        exclude_pattern = re.compile(rule["exclude"], re.I) if rule.get("exclude") else None
        matches = []
        for item in inputs:
            field_text = "%s %s" % (
                item.get("name", ""),
                item.get("label", ""),
            )
            context_text = "%s %s" % (field_text, item.get("condition", ""))
            if exclude_pattern and exclude_pattern.search(field_text):
                continue
            if not field_pattern.search(field_text):
                continue
            if context_pattern and not context_pattern.search(context_text):
                continue
            matches.append(item)
        matches.sort(key=lambda item: requirement_match_rank(req["name"], item))
        if any((item.get("sourceKind") in {"flat", "variant"}) for item in matches):
            status = "matched"
        elif matches:
            status = "candidate"
        else:
            status = "missing"
        out.append({
            "requirementName": req["name"],
            "unit": req["unit"],
            "condition": req["condition"],
            "status": status,
            "matchedInputs": matches[:8],
        })
    return out


def reference_tables(model):
    out = []
    for table in model.get("specTables") or []:
        kind = table.get("kind") or "etc"
        if kind == "rating":
            continue
        out.append({
            "title": table.get("title"),
            "kind": kind,
            "page": table.get("page"),
            "source": table.get("source"),
            "rows": len(table.get("rows") or []),
            "use": {
                "perf": "조건별 성능 조회",
                "dim": "설치·반입 참고",
                "etc": "부속·배선·호환 참고",
            }.get(kind, "참고"),
        })
    return out


def load_equips():
    equips = {}
    for path in glob.glob(os.path.join(DATA, "equips", "*.json")):
        equip = load_json(path)
        equips[equip["id"]] = equip
    return equips


def load_models(equip_ids=None):
    models = {}
    for path in glob.glob(os.path.join(DATA, "models", "*.json")):
        model = load_json(path)
        if equip_ids and model.get("equipId") not in equip_ids:
            continue
        models[model["id"]] = model
    return models


def build_dataset(equip_ids=None):
    terms = load_terms()
    equips = load_equips()
    if equip_ids:
        equips = {k: v for k, v in equips.items() if k in equip_ids}
    models = load_models(set(equips))

    data = {
        "schemaVersion": 1,
        "datasetTiers": {
            "template": "장비별 BMS 템플릿. 화면/자동 매핑의 기준",
            "simulator": "전력·온도 계산에 쓰는 정격과 조건",
            "mapping": "제조사 통신문서 원문 전체 포인트",
            "reference": "성능표·치수·부속·배선 참고자료",
        },
        "equipmentTemplates": {},
        "modelMappings": {},
    }

    for equip_id, equip in sorted(equips.items(), key=lambda item: item[1].get("no", 999)):
        tpoints = template_points(equip)
        sreqs = simulator_requirements(equip)
        data["equipmentTemplates"][equip_id] = {
            "id": equip_id,
            "title": equip.get("title"),
            "domain": equip.get("domain"),
            "templatePoints": tpoints,
            "simulatorSpecRequirements": sreqs,
        }

    for model_id, model in sorted(models.items()):
        candidates = find_template_candidates(model.get("equipId"), model.get("points") or [])
        mapped = mapping_points(model.get("points") or [], candidates)
        sim = simulator_inputs(model, terms)
        refs = reference_tables(model)
        units = unit_models(model)
        electrical = electrical_rows(model)
        equip_template = data["equipmentTemplates"].get(model.get("equipId"), {})
        template_mappings = template_point_mappings(
            model.get("equipId"),
            equip_template.get("templatePoints", []),
            model.get("points") or [],
        )
        simulator_mappings = simulator_requirement_mappings(
            equip_template.get("simulatorSpecRequirements", []),
            sim,
        )
        data["modelMappings"][model_id] = {
            "id": model_id,
            "equipmentId": model.get("equipId"),
            "vendor": model.get("vendor"),
            "model": model.get("model"),
            "name": model.get("name"),
            "templatePointCandidates": candidates,
            "templatePointMappings": template_mappings,
            "unitModels": units,
            "electricalRows": electrical,
            "simulatorInputs": sim,
            "simulatorRequirementMappings": simulator_mappings,
            "l3MappingPoints": mapped,
            "referenceTables": refs,
            "counts": {
                "templateCandidates": len(candidates),
                "templatePointMappings": len(template_mappings),
                "unitModels": len(units),
                "electricalRows": len(electrical),
                "simulatorInputs": len(sim),
                "simulatorRequirementMappings": len(simulator_mappings),
                "l3MappingPoints": len(mapped),
                "referenceTables": len(refs),
            },
        }
    return data


def write_outputs(data):
    os.makedirs(OUT, exist_ok=True)
    files = {
        "catalog-dataset.json": data,
        "equipment-templates.json": data["equipmentTemplates"],
        "model-mappings.json": data["modelMappings"],
    }
    for name, content in files.items():
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return sorted(files)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--equip", action="append", help="장비 ID(e5 등). 생략하면 전체")
    args = parser.parse_args(argv)
    data = build_dataset(set(args.equip) if args.equip else None)
    files = write_outputs(data)
    print("데이터셋 생성 완료: %s" % ", ".join(files))
    print("  장비 템플릿 %d건 · 모델 매핑 %d건" %
          (len(data["equipmentTemplates"]), len(data["modelMappings"])))


if __name__ == "__main__":
    main()
