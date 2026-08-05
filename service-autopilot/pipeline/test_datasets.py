# -*- coding: utf-8 -*-
import unittest

import datasets
import units as U


class DatasetBuildTest(unittest.TestCase):
    def test_ahu_template_has_template_simulator_and_mapping_layers(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        ahu = data["equipmentTemplates"]["e5"]

        self.assertGreaterEqual(len(ahu["templatePoints"]), 20)
        self.assertGreaterEqual(len(ahu["simulatorSpecRequirements"]), 10)
        self.assertIn("modelMappings", data)
        self.assertTrue(data["modelMappings"])

    def test_model_dataset_separates_l2_candidates_from_l3_mapping(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]

        self.assertGreaterEqual(model["counts"]["l3MappingPoints"], 100)
        self.assertGreater(len(model["templatePointCandidates"]), 0)
        self.assertGreater(model["counts"]["l3MappingPoints"], len(model["templatePointCandidates"]))

    def test_simulator_inputs_exclude_reference_tables(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        kinds = {item["sourceKind"] for item in model["simulatorInputs"]}

        self.assertIn("rating", kinds)
        self.assertNotIn("etc", kinds)

    def test_ahu_template_candidates_prefer_status_points_over_config(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        candidates = {item["templateName"]: item["sourceName"] for item in model["templatePointCandidates"]}

        self.assertEqual(candidates["외기온도"], "nvoOutdoorTemp")
        self.assertEqual(candidates["냉수·냉방"], "nvoCoolPrimary")

    def test_ahu_model_exposes_every_template_point_with_match_status(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        template = data["equipmentTemplates"]["e5"]
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]

        self.assertEqual(
            len(model["templatePointMappings"]),
            len(template["templatePoints"]),
        )
        by_name = {item["templateName"]: item for item in model["templatePointMappings"]}
        self.assertEqual(by_name["외기온도"]["matchedPoint"]["name"], "nvoOutdoorTemp")
        self.assertEqual(by_name["급기온도"]["matchedPoint"]["name"], "nvoDischAirTemp")
        self.assertIn(by_name["급기 정압"]["status"], {"matched", "missing"})

    def test_ahu_model_exposes_every_simulator_requirement_with_match_status(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        template = data["equipmentTemplates"]["e5"]
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]

        self.assertEqual(
            len(model["simulatorRequirementMappings"]),
            len(template["simulatorSpecRequirements"]),
        )
        by_name = {item["requirementName"]: item for item in model["simulatorRequirementMappings"]}
        self.assertEqual(by_name["급기 풍량"]["status"], "candidate")
        self.assertTrue(by_name["급기 풍량"]["matchedInputs"])

    def test_ahu_simulator_requirement_mapping_does_not_force_weak_matches(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        by_name = {item["requirementName"]: item for item in model["simulatorRequirementMappings"]}

        # 문서에 정말 없는 값은 후보를 지어내면 안 된다
        self.assertEqual(by_name["기외정압"]["status"], "missing")
        self.assertEqual(by_name["온수코일 능력"]["status"], "missing")
        # 급기팬 모터출력은 원래 missing 이었지만 용어 사전에 'Motor HP' 를 넣은 뒤
        # TWE 표의 실제 값(2–3 HP)이 후보로 잡힌다 — 사전 보강의 의도된 결과다
        fan = by_name["급기팬 형식·모터출력"]
        self.assertEqual(fan["status"], "candidate")
        self.assertEqual(fan["matchedInputs"][0]["name"], "Motor HP - Standard/Oversized")

    def test_power_requirement_prefers_voltage_over_phase(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        by_name = {item["requirementName"]: item for item in model["simulatorRequirementMappings"]}

        self.assertEqual(by_name["전원"]["matchedInputs"][0]["label"], "전압")

    def test_ahu_profile_exposes_unit_model_numbers_separately(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        units = model["unitModels"]

        self.assertEqual(len(units), 17)
        self.assertEqual(units[0]["unitModelNumber"], "Single Compressor TTA0724*A*")
        self.assertEqual(units[0]["capacityClass"], "6 Tons")
        self.assertEqual(units[0]["ratedAirflow"], "2,400")
        self.assertEqual(units[0]["grossCoolingCapacity"], "78,000")
        self.assertEqual(model["counts"]["unitModels"], 17)

    def test_ahu_column_orientation_general_data_is_not_skipped(self):
        # Table 8 (15-25 tons)은 열 방향으로 인식됐지만 구조는 같다 — 형번이 빠지면 안 된다
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}
        big = units["Manifolded Compressor TTA3004*C*"]

        self.assertEqual(big["unitRole"], "condensingUnit")
        self.assertEqual(big["capacityClass"], "25 Tons")   # 정규화: 'Ton' → 'Tons'
        self.assertEqual(big["matchedAirHandler"], "TWE3004*B*")
        self.assertEqual(big["ratedAirflow"], "8,750")
        self.assertEqual(big["grossCoolingCapacity"], "308,000")

    def test_ahu_air_handler_unit_models_use_air_side_ratings(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}
        twe = units["Dual Circuit TWE07243B*, 4B*, WB*"]

        self.assertEqual(twe["unitRole"], "airHandler")
        self.assertEqual(twe["ratedAirflow"], "2400")
        self.assertEqual(twe["units"]["ratedAirflow"], "CFM")
        self.assertEqual(twe["fanMotorHp"], "2.0/3.0")
        self.assertEqual(twe["units"]["fanMotorHp"], "HP")
        self.assertEqual(twe["coilFaceArea"], "8.1")
        self.assertEqual(twe["coilRowsFpi"], "4/14")
        self.assertEqual(twe["grossCoolingCapacity"], "—")

    def test_ahu_electrical_tables_are_split_by_unit_model_and_voltage(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        rows = model["electricalRows"]

        self.assertGreater(len(rows), 40)
        by_code = {item["unitModelNumber"]: item for item in rows}
        tta = by_code["TTA07243A"]

        self.assertEqual(tta["unitRole"], "condensingUnit")
        self.assertEqual(tta["voltage"], "208-230")
        self.assertEqual(tta["phase"], "3")
        self.assertEqual(tta["compressor1Rla"], "19.6")
        self.assertEqual(tta["compressor1Lra"], "136")
        self.assertEqual(tta["fanFla"], "2.3")
        self.assertEqual(tta["fanLra"], "8.4")
        self.assertEqual(model["counts"]["electricalRows"], len(rows))

    def test_ahu_air_handler_electrical_rows_include_mca_and_mop(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        rows = model["electricalRows"]
        twe = next(item for item in rows if item["unitModelNumber"] == "TWE07243B")

        self.assertEqual(twe["unitRole"], "airHandler")
        self.assertEqual(twe["voltage"], "208-230")
        self.assertEqual(twe["motorHp"], "2")
        self.assertEqual(twe["fanFla"], "6.8")
        self.assertEqual(twe["fanLra"], "54.0")
        self.assertEqual(twe["mca"], "8")
        self.assertEqual(twe["mop"], "15")

    def test_rauk_units_come_from_capacity_columns_not_attribute_values(self):
        # 이전엔 압축기 형식 'Scroll'이 형번으로 오추출됐다 — 톤수 열 9개가 나와야 한다
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-800-intellicore-split-system-rauk-bacnet"]
        units = model["unitModels"]

        self.assertEqual(len(units), 9)
        self.assertNotIn("Scroll", {item["unitModelNumber"] for item in units})
        first = units[0]
        self.assertEqual(first["unitModelNumber"], "RAUJ 20 Ton")
        self.assertEqual(first["unitNumberKind"], "capacityClass")
        self.assertEqual(first["unitRole"], "condensingUnit")
        self.assertEqual(first["capacitySteps"], "100-50")
        self.assertEqual(first["compressorConfig"], "10-10")
        # 단위는 RAUK 표의 전용 단위 열(1번 열)에서 온다
        self.assertEqual(first["units"]["capacitySteps"], "%")
        self.assertEqual(first["units"]["compressorConfig"], "Tons")
        self.assertEqual(first["condenserAirflow"], "14600")
        self.assertEqual(first["units"]["condenserAirflow"], "CFM")   # 철자 통일

    def test_intellipak_units_merge_general_data_and_continued_tables(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-800-intellipak-lontalk-dac"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertEqual(len(units), 9)
        twenty = units["IntelliPak 20 Ton"]
        self.assertEqual(twenty["unitRole"], "packagedUnit")
        self.assertEqual(twenty["compressorConfig"], "1/5, 2/7.5")
        self.assertEqual(twenty["condenserFans"], '2/30"/Prop')
        # 급기 CFM 범위는 (continued) 표에 있다 — 병합이 끊기면 '—'로 퇴행한다
        self.assertEqual(twenty["ratedAirflow"], "4,000 - 9,000")
        self.assertEqual(twenty["units"]["ratedAirflow"], "CFM")
        self.assertEqual(twenty["units"]["capacitySteps"], "%")
        seventy_five = units["IntelliPak 75 Ton"]
        self.assertEqual(seventy_five["ratedAirflow"], "15,000 - 30,000")

    def test_precedent_rooftop_units_are_packaged_not_condensing(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-precedent-and-axiom-rooftop-wshp-lontalk-scc"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        ysc = units["T/YSC036G3,4,W"]
        self.assertEqual(ysc["unitRole"], "packagedUnit")
        self.assertEqual(ysc["ahriNetCoolingCapacity"], "36,000")
        # 풍량은 응축 팬 CFM(3,600)이 아니라 급기 정격('Nominal cfm/AHRI Rated cfm')이어야 한다
        self.assertEqual(ysc["ratedAirflow"], "1,200/1,200")
        self.assertEqual(ysc["units"]["ratedAirflow"], "CFM")
        whj = units["WHJ150"]
        self.assertEqual(whj["unitRole"], "packagedUnit")
        self.assertEqual(whj["grossCoolingCapacity"], "154000")
        self.assertEqual(whj["eer"], "12.3")

    def test_precedent_per_unit_electrical_tables_are_normalized(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-precedent-and-axiom-rooftop-wshp-lontalk-scc"]
        rows = model["electricalRows"]

        self.assertGreater(len(rows), 100)
        comp = next(r for r in rows if r["unitModelNumber"] == "T/YSC036G3"
                    and r["motorSet"] == "compressorAndCondenserFan")
        self.assertEqual(comp["voltage"], "208-230")
        self.assertEqual(comp["compressor1Rla"], "10.4")
        self.assertEqual(comp["compressor1Lra"], "73")
        self.assertEqual(comp["fanFla"], "1.1")
        self.assertEqual(comp["fanLra"], "3")
        fan = next(r for r in rows if r["unitModelNumber"] == "T/YSC036G3"
                   and r["motorSet"] == "standardEvaporatorFan")
        self.assertEqual(fan["fanFla"], "5.7")
        self.assertEqual(fan["motorHp"], "0.75")
        wshp = next(r for r in rows if r["unitModelNumber"] == "W/DHJ150A3"
                    and r["motorSet"] == "compressorAndCondenserFan")
        self.assertEqual(wshp["compressor1Rla"], "28.4/14.1")
        self.assertEqual(wshp["fanFla"], "2.2")
        self.assertEqual(wshp["fanLra"], "7.3")

    def test_york_physical_data_units_come_from_header_codes(self):
        # York 기술 가이드 — 형번이 첫 행이 아니라 머리글('Models ZJ037')에 있다
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "johnson-controls-york-simplicity-se-smart-equipment-york-rooftop-units-modbus"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertGreaterEqual(len(units), 30)
        zj = units["ZJ037"]
        self.assertEqual(zj["unitRole"], "packagedUnit")
        self.assertEqual(zj["capacityClass"], "3.0 Tons")
        self.assertEqual(zj["ratedAirflow"], "1200")
        self.assertEqual(zj["eer"], "12.2")
        self.assertEqual(zj["grossCoolingCapacity"], "36000")

    def test_rebel_size_codes_get_family_prefix_from_title(self):
        # Rebel 물리 데이터 — 첫 행이 '003' 같은 크기 코드뿐이라 제목의 'Model DPS'
        # 제품군을 붙여 형번으로 만든다. EER 은 'EER1, 7' 각주 표기.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "daikin-microtech-iii-4-rebel-roofpak-maverick-ii-rooftop-self-contained-bacnet"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertEqual(len(units), 13)
        dps = units["DPS 003"]
        self.assertEqual(dps["capacityClass"], "3 Tons")
        self.assertEqual(dps["ratedAirflow"], "1125")
        self.assertEqual(dps["units"]["ratedAirflow"], "CFM")   # 철자 통일
        self.assertEqual(dps["eer"], "13.5")

    def test_every_e5_model_has_unit_candidates(self):
        # 재발 방지 게이트 — 공조기 모델은 형번·정격 카드가 반드시 1개 이상이어야 한다.
        # 새 벤더를 넣고 이 테스트가 깨지면 체크리스트 5번(인식 사다리 확장)을 하지
        # 않은 것이다. "조판 탓" 으로 넘기지 말 것 (AAON 실사례 — 텍스트 층 파서로 해결).
        data = datasets.build_dataset(equip_ids={"e5"})
        missing = [mid for mid, m in data["modelMappings"].items()
                   if not m.get("unitModels")]
        self.assertEqual(missing, [])

    def test_aaon_cabinet_text_yields_units_with_iom_tonnage(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["aaon-vccx2-rn-rq-series-rooftop-bacnet"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertGreaterEqual(len(units), 20)
        rn6 = units["RN-006"]
        self.assertEqual(rn6["capacityClass"], "6 Tons")
        self.assertEqual(rn6["ratedAirflow"], "2,000")
        self.assertEqual(rn6["units"]["ratedAirflow"], "CFM")
        self.assertEqual(rn6["eer"], "Up to 13.2")
        self.assertEqual(rn6["ieer"], "Up to 22.5")

    def test_lennox_general_data_text_yields_units(self):
        # Lennox Enlight LGT — EHB 표 인식은 구간 라벨(General Data·Cooling
        # Performance)이 항목 라벨과 눌려 라벨-값 짝이 끊긴다. 텍스트 층 주입
        # (vendor_lennox)으로 4형번을 만들고, 기존 e5 스키마 클래스가 무수정으로
        # 받는지(수집 3규칙 검증)를 본다. IEER 는 문서상 072 3상만 게재된다.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "lennox-core-unit-controller-enlight-model-l-rooftop-bacnet"]
        units = {u["unitModelNumber"]: u for u in model["unitModels"]}

        self.assertEqual(len(units), 4)
        lgt36 = units["LGT036H4E"]
        self.assertEqual(lgt36["capacityClass"], "3 Tons")   # 정규화: 'Ton' → 'Tons'
        self.assertEqual(lgt36["ratedAirflow"], "1200/800")
        self.assertEqual(lgt36["units"]["ratedAirflow"], "CFM high/low")
        self.assertEqual(lgt36["grossCoolingCapacity"], "36,600")
        self.assertEqual(lgt36["ahriNetCoolingCapacity"], "36,000")
        self.assertEqual(lgt36["eer"], "13.3")
        self.assertEqual(lgt36["ieer"], "—")
        self.assertEqual(units["LGT072H4E"]["ieer"], "17.0")

    def test_systemair_geniox_sizes_with_dimensions(self):
        # Systemair Geniox — 퀵가이드 크기표는 그래픽 조판이라 텍스트 층 주입
        # (vendor_systemair). 크기별 풍량은 SystemairCAD 선정 SW 전용이라 없고,
        # 치수(폭·높이·길이 mm)가 문서값이다. 크기 행 사다리의 치수 열 확장 검증.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["systemair-access-geniox-geniox-go-ahu-modbus"]
        units = {u["unitModelNumber"]: u for u in model["unitModels"]}

        self.assertEqual(len(units), 12)
        g10 = units["Geniox 10"]
        self.assertEqual(g10["capacityClass"], "크기 10")
        self.assertEqual(g10["unitWidth"], "1082")
        self.assertEqual(g10["units"]["unitWidth"], "mm")
        self.assertEqual(g10["unitHeight"], "1082")
        self.assertEqual(g10["unitLength"], "2282")
        # 포인트는 Modbus 절대 참조 — 3x/4x 주소 충돌(663건)이 살아남아야 한다
        self.assertGreaterEqual(model["counts"]["l3MappingPoints"], 1800)

    def test_carrier_letter_sizes_become_units_with_nominal_capacity(self):
        # Carrier 48/50N — 크기가 한 글자(N~T)이고 톤수는 'NOMINAL CAPACITY (tons)' 행.
        # 치수·커브 표도 같은 제목 낱말을 쓰므로 이 행이 없으면 형번을 만들면 안 된다.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "carrier-comfortlink-48-50n-weatherexpert-rooftop-75-150-ton-bacnet-co"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertEqual(len(units), 6)
        self.assertEqual(units["48/50N N"]["capacityClass"], "75 Tons")
        self.assertEqual(units["48/50N T"]["capacityClass"], "150 Tons")
        self.assertEqual(units["48/50N N"]["unitRole"], "packagedUnit")
        # 이 표는 PDF 추출 때 응축 팬·코일 블록의 하위 행들이 한 행으로 눌려
        # 모든 열 값이 1열 한 칸에 뭉친다 — 가드가 버려서 '—' 여야 한다
        self.assertEqual(units["48/50N N"]["coilFaceArea"], "—")
        self.assertEqual(units["48/50N N"]["fanMotorHp"], "—")

    def test_unit_fields_reject_collapsed_row_pdf_blobs_everywhere(self):
        # 재발 방지 게이트 — PDF 추출이 하위 행 여러 개를 한 행으로 눌러 모든 열
        # 값이 한 칸에 뭉친 덩어리('MCHX Aluminum … 138.7 173.3 …')가 어떤 모델의
        # 어떤 형번 필드로든 새면 실패한다 (Carrier 48/50N 실사례). 새 벤더를
        # 등록할 때 형번 표 한 행에 스펙이 다 들어가 보이면 이 테스트가 먼저 잡는다.
        skip = {"sourceTable", "sourceFile", "source", "units"}
        for model in datasets.load_models().values():
            for row in datasets.unit_models(model):
                for field, value in row.items():
                    if field in skip or not isinstance(value, str):
                        continue
                    self.assertTrue(
                        datasets.plausible_rating_value(value),
                        "%s %s.%s 에 눌린 다열 덩어리: %r" % (
                            model.get("id"), row.get("unitModelNumber"),
                            field, value[:80]))

    def test_point_units_are_short_tokens_not_prose(self):
        # 오브젝트 목록의 단위 칸에 표 각주 문장('These legacy alarm reporting
        # objects are obsolete …', Lennox 실사례)이나 범위+기본값(Daikin)이 남으면
        # 실패한다 — 추출 가드(extract.unit_or_note)가 비고로 옮겨야 한다.
        import extract
        for mid, model in datasets.load_models().items():
            for p in model.get("points") or []:
                _unit, spill = extract.unit_or_note(p.get("unitRaw") or "")
                self.assertFalse(
                    spill, "%s %s-%s 단위 칸에 문장/범위: %r" % (
                        mid, p.get("type"), p.get("inst"),
                        (p.get("unitRaw") or "")[:60]))

    def test_unit_rows_carry_source_file_for_pdf_page_link(self):
        # 출처 클릭 → 원문 PDF 해당 쪽 열기가 되려면 형번 행마다 원본 파일명이 있어야 한다
        for model in datasets.load_models().values():
            for row in datasets.unit_models(model):
                self.assertIn(
                    ".pdf", (row.get("sourceFile") or "").lower(),
                    "%s %s 에 sourceFile 이 없다: %r" % (
                        model.get("id"), row.get("unitModelNumber"),
                        row.get("sourceFile")))


class CuratedUnitDatasetTest(unittest.TestCase):
    """형번 확정 데이터셋(골든 레코드) 게이트 — 추출은 제안, data/units 가 정본."""

    def test_curated_file_exists_for_every_model_with_extraction(self):
        # 추출이 형번을 내는데 확정본이 없으면 화면에서 형번이 사라진다 —
        # units.py --sync 를 잊으면 여기서 잡힌다.
        schema = U.load_schema()
        for mid, model in datasets.load_models().items():
            if not U.extraction_records(model, schema):
                continue
            stored = U.load_stored(mid)
            self.assertTrue(
                stored and stored.get("units"),
                "%s: 추출 제안은 있는데 확정본(data/units)이 없다 — units.py --sync" % mid)

    def test_class_equip_models_have_units_or_documented_reason(self):
        # 스키마 적용 전수 감사의 상시화 — 클래스 설비(e5·e9)의 모든 모델은
        # ① 확정본 형번이 있거나 ② 없으면 gap 에 문서 한계 사유(형번/정격/카탈로그)가
        # 적혀 있어야 한다. 조용히 스키마 밖에 남는 모델을 금지한다.
        schema = U.load_schema()
        for mid, model in datasets.load_models().items():
            if model.get("equipId") not in schema["classes"]:
                continue
            if U.extraction_records(model, schema):
                continue
            gap = model.get("gap") or ""
            self.assertTrue(
                any(w in gap for w in ("형번", "정격", "카탈로그")),
                "%s: 클래스 설비인데 형번도 없고 gap 사유도 없다" % mid)

    def test_curated_units_conform_to_schema(self):
        # 확정본의 모든 레코드는 속성 사전(features)에 있는 필드만 쓰고,
        # 값 모양 한계(눌린 다열 덩어리 금지)와 원본 PDF 출처를 지켜야 한다.
        import glob, json, os
        schema = U.load_schema()
        ids = set(U.field_ids(schema))
        statuses = set(schema["statuses"])
        for path in glob.glob(os.path.join(U.UNITS_DIR, "*.json")):
            doc = json.load(open(path, encoding="utf-8"))
            for rec in doc.get("units") or []:
                code = "%s %s" % (doc.get("modelId"), rec.get("unitModelNumber"))
                self.assertIn(rec.get("status") or "extracted", statuses, code)
                self.assertIn(".pdf", ((rec.get("source") or {}).get("file") or "").lower(),
                              code + " 출처 파일 없음")
                for fid, entry in (rec.get("fields") or {}).items():
                    self.assertIn(fid, ids, code + " 사전 밖 필드 " + fid)
                    self.assertTrue(
                        datasets.plausible_rating_value((entry or {}).get("value") or ""),
                        code + "." + fid + " 눌린 다열 덩어리")

    def test_schema_classes_reference_defined_features(self):
        # 클래스(설비별 세트)의 table·detail·labels 가 사전에 없는 id 를 가리키면
        # 화면 열이 조용히 비거나 라벨이 원문 id 로 샌다.
        schema = U.load_schema()
        ids = set(schema["features"])
        for cid, cls in schema["classes"].items():
            for fid in (cls.get("table") or []) + (cls.get("detailExtra") or []):
                self.assertIn(fid, ids, "%s.table/detailExtra: %s" % (cid, fid))
            for fid in (cls.get("labels") or {}):
                self.assertIn(fid, ids, "%s.labels: %s" % (cid, fid))
            for role, rd in (cls.get("roles") or {}).items():
                for fid in rd.get("detail") or []:
                    self.assertIn(fid, ids, "%s.%s.detail: %s" % (cid, role, fid))

    def test_every_equip_with_extracted_units_has_schema_class(self):
        # 스키마 우선 규칙 — 형번이 나오는 설비 계열은 클래스(열 구성·라벨·역할)를
        # unit-schema.json classes 에 먼저 정의해야 한다. 새 설비(냉각탑·VAV 등)를
        # 수집하며 스키마 없이 지나가면 여기서 잡힌다 (units.py --propose-class 초안).
        schema = U.load_schema()
        classes = schema.get("classes") or {}
        for mid, model in datasets.load_models().items():
            if U.extraction_records(model, schema):
                self.assertIn(
                    model.get("equipId"), classes,
                    "%s: 설비 %s 클래스 미정의 — units.py --propose-class %s"
                    % (mid, model.get("equipId"), model.get("equipId")))

    def test_extracted_fields_are_all_defined_in_schema_features(self):
        # 사전 우선 규칙 — 추출기에 새 필드(pick)를 더할 때 공유 속성 사전에 먼저
        # 정의하지 않으면 확정본 저장에서 조용히 떨어져 나간다(데이터 유실).
        # 여기서 시끄럽게 잡는다: 추출 행의 모든 사양 키는 features 에 있어야 한다.
        META = {"unitModelNumber", "unitNumberKind", "unitRole", "units",
                "sourceTable", "sourcePage", "sourceFile", "selectionStatus", "status"}
        ids = set(U.field_ids(U.load_schema()))
        for mid, model in datasets.load_models().items():
            for row in datasets.unit_models(model):
                for key in row:
                    if key in META:
                        continue
                    self.assertIn(key, ids,
                                  "%s: 추출 필드 %r 가 속성 사전(features)에 없다 — "
                                  "unit-schema.json 에 먼저 정의" % (mid, key))

    def test_curated_notation_is_unified(self):
        # 표기 통일 게이트 — 정규화 계층(units.normalize_entry)을 지나지 않은
        # 흔들린 표기(단수 Ton·소문자 cfm·Btuh·Mbh·K Btu·sq. ft.·EER 단위/라벨·
        # '-' 자리표시)가 확정본에 남으면 실패한다. 척도가 다른 단위
        # (MBh·Btu/h·kW, CFM·m³/s·m³/h)는 문서 사실이라 허용이다.
        import glob, json, os, re
        bad_units = {"cfm", "cfm-high/low", "m3/s", "m3/h",
                     "sq. ft.", "Sq. Ft.", "Mbh", "K Btu", "Btuh", "Btu"}
        for path in glob.glob(os.path.join(U.UNITS_DIR, "*.json")):
            doc = json.load(open(path, encoding="utf-8"))
            for rec in doc.get("units") or []:
                code = "%s %s" % (doc.get("modelId"), rec.get("unitModelNumber"))
                for fid, entry in (rec.get("fields") or {}).items():
                    value = (entry or {}).get("value") or ""
                    unit = (entry or {}).get("unit") or ""
                    self.assertNotIn(unit, bad_units, code + " 단위 표기 미통일: " + unit)
                    if fid == "capacityClass":
                        self.assertFalse(value.endswith(" Ton"), code + " 단수 Ton")
                    if fid in ("eer", "ieer"):
                        self.assertFalse(unit, code + " EER 단위 표기는 생략이 규칙")
                        self.assertFalse(re.match(r"^\s*I?EER\s*=", value),
                                         code + " EER 라벨 혼입")
                        self.assertFalse(re.match(r"^[-\s]*$", value),
                                         code + " 자리표시 값")

    def test_merge_preserves_verified_and_manual_and_reports_drift(self):
        # 생존 규칙 — 사람 확정본(verified·manual)은 추출이 절대 덮지 않는다.
        verified = {"unitModelNumber": "X-01", "status": "verified",
                    "fields": {"eer": {"value": "12.0"}}, "source": {"page": 1}}
        manual = {"unitModelNumber": "M-01", "status": "manual",
                  "fields": {"eer": {"value": "9.9"}}, "source": {"page": 3}}
        extracted = [{"unitModelNumber": "X-01", "status": "extracted",
                      "fields": {"eer": {"value": "13.5"}}, "source": {"page": 1}}]
        merged, log = U.merge_units([verified, manual], extracted)
        by_code = {r["unitModelNumber"]: r for r in merged}
        self.assertEqual(by_code["X-01"]["fields"]["eer"]["value"], "12.0")
        self.assertEqual(by_code["X-01"]["status"], "verified")
        self.assertEqual(by_code["M-01"]["fields"]["eer"]["value"], "9.9")
        kinds = {kind for kind, _ in log}
        self.assertIn("drift", kinds)   # 확정본과 추출이 달라짐 — 알림만
        self.assertIn("orphan", kinds)  # 추출이 못 만들어도 수기 입력은 남는다

    def test_merge_updates_and_drops_extracted_proposals(self):
        # extracted 상태는 추출이 자유롭게 갱신·삭제한다 (제안이니까).
        old = [{"unitModelNumber": "A-01", "status": "extracted",
                "fields": {"eer": {"value": "10"}}, "source": {"page": 5}},
               {"unitModelNumber": "GONE-01", "status": "extracted",
                "fields": {}, "source": {"page": 6}}]
        new = [{"unitModelNumber": "A-01", "status": "extracted",
                "fields": {"eer": {"value": "11"}}, "source": {"page": 5}}]
        merged, log = U.merge_units(old, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["fields"]["eer"]["value"], "11")
        self.assertEqual({k for k, _ in log}, {"update", "drop"})

    def test_build_reads_curated_only(self):
        # 화면 데이터는 확정본 어댑터를 거친다 — status 필드가 실려 있어야 한다
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["aaon-vccx2-rn-rq-series-rooftop-bacnet"]
        self.assertTrue(model["unitModels"])
        for row in model["unitModels"]:
            self.assertIn(row.get("status"), ("extracted", "verified", "manual"))

    def test_inducer_and_power_exhaust_motors_are_not_electrical_rows(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-precedent-and-axiom-rooftop-wshp-lontalk-scc"]
        sources = {r["sourceTable"] for r in model["electricalRows"]}

        self.assertFalse(any("inducer" in s.lower() or "power exhaust" in s.lower()
                             for s in sources))


if __name__ == "__main__":
    unittest.main()
