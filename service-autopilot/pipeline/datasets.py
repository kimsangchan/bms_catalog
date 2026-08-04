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


def label_unit(label):
    """라벨에 적힌 단위만 뽑는다 — (sq ft)·(%)·CFM·HP·RPM 등. 없는 단위는 지어내지 않는다."""
    text = clean_text(label)
    m = re.search(r"\(([^)]*(?:%|ft|cfm|btu|mbh|hp|rpm|ton|kw|psi|°f|m³|m3|l/s|cmh)[^)]*)\)",
                  text, re.I)
    if m and not re.search(r"nominal|standard|oversiz|fins|t/y", m.group(1), re.I):
        return m.group(1).strip()
    if re.search(r"\bcfm\b", text, re.I):
        return "CFM"
    if re.search(r"\bhp\b", text, re.I):
        return "HP"
    if re.search(r"\brpm\b", text, re.I):
        return "RPM"
    return ""


def value_unit_for_label(rows, pattern, col, unit_col=None):
    """값과 함께 그 값의 단위를 돌려준다 — 라벨 안 단위가 1순위, RAUK식 단위 열이 2순위."""
    regex = re.compile(pattern, re.I)
    for row in rows:
        cells = row_cells(row)
        if cells and regex.search(cells[0]):
            value = cells[col] if col < len(cells) else ""
            unit = label_unit(cells[0])
            if not unit and unit_col is not None and unit_col < len(cells):
                candidate = cells[unit_col]
                if candidate and len(candidate) <= 8 and not re.match(r"^[\d.,/ –-]+$", candidate):
                    unit = candidate
            return value, unit
    return "", ""


# 형번으로 인정하는 토큰 — 문자 계열 + 숫자 2자리 이상 (TTA0724, WHJ150, T/YSC036G3).
# 'Scroll'(압축기 형식)이나 '1/5, 2/7.5'(압축기 구성) 같은 속성값이 형번으로 오인되지 않게 한다.
UNIT_CODE_TOKEN = re.compile(r"[A-Z][A-Za-z/]{1,8}\d{2,}")


def looks_like_unit_code(text):
    return bool(UNIT_CODE_TOKEN.search(text or ""))


def unit_role_for(code, title):
    """TWE=공기측, 표 제목에 condensing=실외/응축, 그 외(옥상형·WSHP)=일체형."""
    if re.search(r"\bTWE", code or "", re.I):
        return "airHandler"
    if re.search(r"condensing", title or "", re.I):
        return "condensingUnit"
    return "packagedUnit"


def unit_family_for(model, title):
    """용량급 표의 제품군 이름 — 표 제목(RAUJ condensing units)이 1순위, 없으면 모델명에서."""
    match = re.search(r"([A-Z]{3,}\d*)\s+condensing units", title or "")
    if match:
        return match.group(1)
    match = re.search(r"[—-]\s*([A-Za-z][A-Za-z0-9]+)", clean_text(model.get("model")))
    if match:
        return re.sub(r"[™®]", "", match.group(1))
    return ""


CAPACITY_FILL_LABELS = {
    "compressorConfig": r"Number/Size \(Nominal\)|Manifolded Compressor sizes",
    "capacitySteps": r"Unit Capacity Steps",
    "refrigerantCircuits": r"Number of Refrigerant Circuits|No\. of Circuits",
    "condenserFans": r"Number/Size/Type",
    "ratedAirflow": r"CFM Range",
    "condenserAirflow": r"Nominal Total Airflow",
}


def capacity_units_from_table(table, model, merged):
    """형번이 없고 톤수 열로만 유닛을 구분하는 General data 표 (RAUJ·IntelliPak).

    문서가 유닛을 톤수로만 식별하므로 지어내지 않고 '제품군 + 톤수'를 후보 이름으로 쓴다.
    같은 제품군의 (continued) 표는 열이 같으므로 빈 값만 이어서 채운다.
    """
    header = row_cells(table.get("header") or [])
    rows = table.get("rows") or []
    title = table.get("title") or ""
    family = unit_family_for(model, title)
    role = ("chillerUnit" if model.get("equipId") == "e9"
            else "condensingUnit" if re.search(r"condensing", title, re.I)
            else "packagedUnit")
    cap_cols = [col for col in range(1, len(header))
                if re.match(r"^\d{2,3}$", header[col] or "")]
    # RAUK식 표는 값 열이 2번부터라 1번 열이 단위 전용이다 (Tons·%·cfm·ft2)
    unit_col = 1 if cap_cols and min(cap_cols) >= 2 else None
    for col in cap_cols:
        cap = header[col]
        key = "%s|%s" % (family, cap)
        unit = merged.get(key)
        if unit is None:
            unit = merged[key] = {
                "unitModelNumber": ("%s %s Ton" % (family, cap)).strip(),
                "unitNumberKind": "capacityClass",
                "unitRole": role,
                "capacityClass": "%s Tons" % cap,
                "matchedAirHandler": "—",
                "ratedAirflow": "—",
                "grossCoolingCapacity": "—",
                "ahriNetCoolingCapacity": "—",
                "eer": "—",
                "coilFaceArea": "—",
                "coilRowsFpi": "—",
                "fanMotorHp": "—",
                "fanMotorRpm": "—",
                "compressorConfig": "—",
                "capacitySteps": "—",
                "refrigerantCircuits": "—",
                "condenserFans": "—",
                "condenserAirflow": "—",
                "units": {},
                "sourceTable": title,
                "sourcePage": table.get("page"),
                "selectionStatus": "unit_candidate",
            }
        for field, pattern in CAPACITY_FILL_LABELS.items():
            if unit[field] == "—":
                value, measure = value_unit_for_label(rows, pattern, col, unit_col=unit_col)
                if value:
                    unit[field] = value
                    if measure:
                        unit["units"][field] = measure


def size_row_units(table, model, out, seen):
    """행=크기 코드(04~28), 열=풍량·냉방능력인 표 (IV Produkt Envistar).

    표 제목이 각주 조각으로 깨져 시리즈 이름은 남지 않았다 — 제품군은 문서
    이름(Envistar)에서 오고, 같은 크기가 시리즈마다 있으므로 쪽수로 가른다.
    풍량은 Min–Max 범위 그대로 적는다 (사이 값은 SFPv 조건별 선정치).
    """
    header = row_cells(table.get("header") or [])
    rows = [row_cells(r) for r in table.get("rows") or []]
    src = table.get("source") or ""
    family = ("Envistar" if "Envistar" in src
              else unit_family_for(model, table.get("title") or ""))
    af_i = next((i for i, h in enumerate(header)
                 if re.search(r"air ?flow", h or "", re.I)), None)
    cool_i = next((i for i, h in enumerate(header)
                   if re.search(r"cooling power", h or "", re.I)), None)
    if af_i is None:
        return
    # 머리글 다음의 부머리글 행(Min/SFPv/Max)에서 Max 열의 상대 위치를 찾는다
    sub = rows[0] if rows and not (rows[0][0] or "").strip() else []
    af_max = af_i
    for off in range(0, 4):
        if af_i + off < len(sub) and re.search(r"max", sub[af_i + off] or "", re.I):
            af_max = af_i + off
            break
    for cells in rows:
        code = (cells[0] or "").strip()
        if not re.match(r"^\d{2,3}$", code):
            continue
        key = (family, code, table.get("page"))
        if key in seen:
            continue
        seen.add(key)
        lo = cells[af_i] if af_i < len(cells) else ""
        hi = cells[af_max] if af_max < len(cells) else ""
        airflow = (" – ".join(x for x in (lo, hi) if x)) or "—"
        cool = (cells[cool_i] if cool_i is not None and cool_i < len(cells) else "") or "—"
        units = {}
        if airflow != "—" and label_unit(header[af_i]):
            units["ratedAirflow"] = label_unit(header[af_i])
        if cool != "—" and cool_i is not None and label_unit(header[cool_i]):
            units["grossCoolingCapacity"] = label_unit(header[cool_i])
        out.append({
            "unitModelNumber": "%s %s" % (family, code),
            "unitNumberKind": "capacityClass",
            "unitRole": "packagedUnit",
            "capacityClass": "크기 %s" % code,
            "matchedAirHandler": "—", "ratedAirflow": airflow,
            "grossCoolingCapacity": cool, "ahriNetCoolingCapacity": "—",
            "eer": "—", "coilFaceArea": "—", "coilRowsFpi": "—",
            "fanMotorHp": "—", "fanMotorRpm": "—",
            "units": units,
            "sourceTable": table.get("title") or "",
            "sourcePage": table.get("page"),
            "selectionStatus": "unit_candidate",
        })


def unit_models(model):
    """제품군/통신 프로파일 문서 안의 실제 Unit Model Number 후보.

    Trane 공조기 카탈로그의 General data 표는 두 갈래다.
    ① 첫 행에 형번이 있는 표 (Odyssey TTA/TWE·Precedent T/YSC·WHJ) — 행/열 방향과
       무관하게 같은 구조라 orientation으로 거르지 않는다.
    ② 형번 없이 톤수 열로만 구분하는 표 (RAUJ·IntelliPak) — 용량급 후보로 편다.

    냉동기(e9)도 같은 구조다 — Daikin AGZ 'Physical Data' 는 첫 행 형번(AGZ031E),
    Trane CGAM 'General data' 는 톤수 열 + 단위 열. 사용자가 냉동기에서 형번·정격이
    안 보인다고 해서 확장했다.
    """
    if model.get("equipId") not in ("e5", "e9"):
        return []
    out, seen, capacity_units = [], set(), {}
    for table in model.get("specTables") or []:
        if (table.get("kind") or "etc") != "rating":
            continue
        title = table.get("title") or ""
        # York·Daikin 카탈로그는 같은 구조의 표를 'Physical Data' 라고 부른다
        if not re.search(r"general data|physical data", title, re.I):
            # Envistar 는 표 제목이 각주 조각이라 제목으로 못 거른다 — 대신
            # '1행=크기(04~28), 열=풍량·냉방능력' 구조를 모양으로 알아본다
            header0 = row_cells(table.get("header") or [])
            if (header0 and re.match(r"^siz", header0[0] or "", re.I)
                    and any(re.search(r"air ?flow", h or "", re.I) for h in header0)):
                size_row_units(table, model, out, seen)
            continue
        header = row_cells(table.get("header") or [])
        rows = table.get("rows") or []
        first = row_cells(rows[0]) if rows else []
        # 형번이 어디 적혔는가 — ① 첫 행(Trane·York ZJ078형) ② 머리글(York ZJ037형:
        # 'Models ZJ037'처럼 머리글 칸에 형번) ③ 첫 행이 숫자 크기 코드뿐이고 제목이
        # 'Model DPS 003 – 028' 꼴이면 제품군+코드로 조합(Rebel형)
        code_cols = []
        for col in range(1, len(header)):
            code = clean_model_label(first[col] if col < len(first) else "")
            if code and looks_like_unit_code(code):
                code_cols.append((col, code))
        if not code_cols:
            for col in range(1, len(header)):
                cell = re.sub(r"^models?\s+", "", header[col] or "", flags=re.I)
                code = clean_model_label(cell)
                if code and looks_like_unit_code(code):
                    # 머리글 칸에 제품군 설명이 같이 든 경우('AGZ-E (Microchannel
                    # Packaged Chiller) AGZ170E')는 형번 토큰만 꺼낸다
                    if len(code) > 24:
                        m2 = re.search(r"[A-Z][A-Za-z/]*\d+[A-Za-z0-9*\-]*", code)
                        if not m2:
                            continue
                        code = m2.group(0)
                    code_cols.append((col, code))
        if not code_cols:
            fam = re.search(r"model\s+([A-Z]{2,6})\b\s*\d", title, re.I)
            if fam:
                for col in range(1, len(header)):
                    cell = first[col] if col < len(first) else ""
                    if re.match(r"^\d{2,3}$", cell or ""):
                        code_cols.append((col, "%s %s" % (fam.group(1).upper(), cell)))
        if not code_cols:
            capacity_units_from_table(table, model, capacity_units)
            continue
        for col, code in code_cols:
            if code in seen:
                continue
            seen.add(code)
            fields, units = {}, {}

            def pick(field, *patterns):
                for pattern in patterns:
                    value, unit = value_unit_for_label(rows, pattern, col)
                    if value:
                        fields[field] = value
                        if unit:
                            units[field] = unit
                        return
                fields[field] = "—"

            pick("matchedAirHandler", r"matched air handler$")
            # 풍량 우선순위: AHRI 정격 → 급기 공칭('Nominal cfm') → 팬 공칭.
            # 맨 뒤 '^CFM$'는 Precedent 패키지 유닛에서 응축 팬 풍량이라 급기 라벨보다 뒤에 둔다.
            pick("ratedAirflow", r"AHRI Rated Airflow", r"Nominal cfm/AHRI Rated cfm",
                 r"^Nominal airflow", r"^Nominal CFM$", r"CFM \(Nominal\)", r"^CFM$")
            pick("grossCoolingCapacity", r"Gross Cooling Capacity - System",
                 r"^Gross Cooling Capacity$", r"^Gross Capacity @ (ARI|AHRI)")
            pick("ahriNetCoolingCapacity", r"AHRI Net Cooling Capacity",
                 r"^(ARI|AHRI) net capacity")
            # 'EER1, 7' 처럼 각주 번호가 붙는 표기(Rebel)까지 받는다
            pick("eer", r"Matched Air Handler \(EER\)", r"System \(EER\)",
                 r"^EER(?![A-Za-z])")
            pick("coilFaceArea", r"Face Area")
            pick("coilRowsFpi", r"Rows/FPI", r"Rows Deep/Fins")
            pick("fanMotorHp", r"Motor HP")
            pick("fanMotorRpm", r"Motor RPM")
            # 'Staging, 4 Stages …' 는 Daikin 냉동기의 용량 단계 표기다
            pick("capacitySteps", r"Unit Capacity Steps", r"^Staging")
            # 용량대 — Trane 은 머리글이 '6 Tons' 지만 York·Rebel 머리글은
            # 'Models'·'Small cabinet' 같은 묶음 이름이라, 숫자가 없으면 표의
            # 공칭 톤수 행에서 가져온다
            capacity = header[col] or "—"
            # 머리글이 용량('6 Tons')이 아니라 형번('Models ZJ037')이거나 묶음
            # 이름('Small cabinet')이면 표의 공칭 톤수 행에서 가져온다
            if not re.search(r"\d", capacity) or looks_like_unit_code(capacity):
                tons, _u = value_unit_for_label(
                    rows, r"^Nominal Tonnage$|^Gross cooling capacity \(tons\)", col)
                capacity = ("%s Tons" % tons) if tons else "—"
            out.append(dict(fields,
                            unitModelNumber=code,
                            unitNumberKind="modelNumber",
                            unitRole=("chillerUnit" if model.get("equipId") == "e9"
                                      else unit_role_for(code, title)),
                            capacityClass=capacity,
                            units=units,
                            sourceTable=table.get("title") or "",
                            sourcePage=table.get("page"),
                            selectionStatus="unit_candidate"))
    out.extend(capacity_units.values())
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


def header_idx(header, pattern, start=0):
    regex = re.compile(pattern, re.I)
    for idx in range(start, len(header)):
        if regex.search(header[idx]):
            return idx
    return None


def per_unit_electrical_rows(table):
    """헤더에 'Unit Model Number' 열이 있는 1행=1형번 전기 특성표 (Precedent·WSHP).

    Odyssey처럼 한 칸에 형번 여러 개를 욱여넣지 않고 행마다 형번·전압이 하나라
    헤더 이름으로 열을 찾아 그대로 편다. 두 갈래다.
    ① 압축기+응축팬 표 — 고정 배치 14~15열 (RLA·LRA 열은 헤더가 'Amps'+빈칸으로 병합)
    ② 공기측(증발기/실내) 팬 표 — Volts·Phase·hp·FLA(·LRA) 열을 이름으로 찾는다
    """
    title = table.get("title") or ""
    if (table.get("kind") or "etc") != "rating":
        return []
    # 급배기 보조 모터는 형번 선정 정보가 아니라서 싣지 않는다
    if re.search(r"inducer|power exhaust", title, re.I):
        return []
    header = row_cells(table.get("header") or [])
    umn_i = header_idx(header, r"unit model number")
    if umn_i is None:
        return []
    rows = [row_cells(row) for row in table.get("rows") or []]
    source = "%s p%s" % (title, table.get("page", ""))
    out = []
    is_compressor = bool(re.search(r"compressor", title, re.I))
    if is_compressor and len(header) not in (14, 15):
        return []
    if not is_compressor:
        volts_i = header_idx(header, r"volts", umn_i + 1)
        phase_i = header_idx(header, r"phase", umn_i + 1)
        hp_i = header_idx(header, r"\bhp", umn_i + 1)
        fla_i = header_idx(header, r"\bfla\b", umn_i + 1)
        lra_i = header_idx(header, r"^lra$", umn_i + 1)
        if volts_i is None or fla_i is None:
            return []
    motor_set = ("compressorAndCondenserFan" if is_compressor
                 else "oversizedEvaporatorFan" if re.search(r"oversiz", title, re.I)
                 else "standardEvaporatorFan")
    tons = ""
    for row in rows:
        if umn_i >= len(row):
            continue
        code = row[umn_i]
        if not looks_like_unit_code(code):
            continue
        tons = row[0] or tons
        base = {
            "unitModelNumber": code,
            "unitRole": "packagedUnit",
            "capacityClass": tons,
            "motorSet": motor_set,
            "sourceTable": title,
            "sourcePage": table.get("page"),
            "source": source,
        }
        if is_compressor:
            fan_fla, fan_lra = ((row[13], row[14]) if len(row) >= 15
                                else amp_pair(row[13] if len(row) > 13 else "", 0))
            out.append(dict(base,
                            voltage=row[3] if len(row) > 3 else "",
                            phase=row[4] if len(row) > 4 else "",
                            compressor1Rla=row[7] if len(row) > 7 else "",
                            compressor1Lra=row[8] if len(row) > 8 else "",
                            fanCount=row[9] if len(row) > 9 else "",
                            fanVoltage=row[10] if len(row) > 10 else "",
                            fanPhase=row[11] if len(row) > 11 else "",
                            fanFla=fan_fla, fanLra=fan_lra))
        else:
            out.append(dict(base,
                            voltage=row[volts_i] if volts_i < len(row) else "",
                            phase=row[phase_i] if phase_i is not None and phase_i < len(row) else "",
                            motorHp=row[hp_i] if hp_i is not None and hp_i < len(row) else "",
                            fanFla=row[fla_i] if fla_i < len(row) else "",
                            fanLra=row[lra_i] if lra_i is not None and lra_i < len(row) else ""))
    return out


def electrical_rows(model):
    """Electrical tables normalized to one row per unit-model/voltage option."""
    if model.get("equipId") not in ("e5", "e9"):
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
        handled_before = len(out)
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
        if len(out) == handled_before:
            # Odyssey식(한 칸 여러 형번) 표가 아니면 1행=1형번 표로 다시 읽는다
            out.extend(per_unit_electrical_rows(table))
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
