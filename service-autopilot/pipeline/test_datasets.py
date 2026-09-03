# -*- coding: utf-8 -*-
import glob
import os
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
import unittest
from unittest import mock

import build
import datasets
import extract
import haystack
import requirements as RQ
import units as U

RAW = os.path.join(datasets.DATA, "raw")


class DatasetBuildTest(unittest.TestCase):
    def test_ahu_template_has_template_simulator_and_mapping_layers(self):
        # 전에는 equipmentTemplates['e5'].templatePoints 한 벌(23행)이었다. 그게 RTU 를
        # 냉수코일 AHU 체크리스트로 채점한 원인이라 하위형식 프로파일로 갈랐다.
        data = datasets.build_dataset(equip_ids={"e5"})
        ahu = data["equipmentTemplates"]["e5"]

        self.assertEqual(ahu["templateProfileIds"], ["e5.ahu", "e5.rtu"])
        self.assertNotIn("templatePoints", ahu)   # 계열 한 벌은 더 이상 없다
        self.assertGreaterEqual(len(ahu["simulatorSpecRequirements"]), 10)
        for pid in ("e5.rtu", "e5.ahu"):
            self.assertGreaterEqual(len(data["templateProfiles"][pid]["templatePoints"]), 20)
        self.assertIn("modelMappings", data)
        self.assertTrue(data["modelMappings"])

    def test_template_profile_ids_match_requirement_profile_ids(self):
        """게이트 — 두 파일의 프로파일 id 집합이 같아야 한다.

        매치 규칙(catPrefix)은 equip-requirements.json 에만 있고 결합은
        requirements.profile_for() 하나만 쓴다. id 가 어긋나면 모델이 조용히 템플릿
        없이 흘러가므로 여기서 세운다.
        """
        tpl = set(datasets.load_template_profiles())
        req = set(RQ.profiles())

        self.assertEqual(tpl, req)
        self.assertEqual(tpl, {"e5.rtu", "e5.ahu"})
        for pid, prof in datasets.load_template_profiles().items():
            self.assertNotIn("match", prof, "%s: 매치 규칙을 여기 복제하면 규칙이 두 벌이 된다" % pid)

    def test_datasets_cli_rejects_partial_overwrite(self):
        """공용 산출물을 부분 데이터로 덮어쓰는 --equip 재발 방지."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = datasets.main(["--equip", "e5"])

        self.assertEqual(code, 2)
        self.assertIn("--equip", buf.getvalue())

    def test_extracted_points_carry_pdf_page_source(self):
        """모델별 오브젝트 목록도 행 단위로 원문 PDF 쪽을 들고 있어야 한다."""
        pdf = os.path.join(RAW, "AAON_VCCX2_Technical_Guide.pdf")
        if not os.path.exists(pdf):
            self.skipTest("raw PDF 없음: " + pdf)

        points, _how = extract.extract(pdf)

        self.assertTrue(points)
        self.assertTrue(all(p.get("sourceFile") for p in points[:20]))
        self.assertTrue(all(isinstance(p.get("sourcePage"), int) for p in points[:20]))
        self.assertEqual(points[0]["sourceFile"], "AAON_VCCX2_Technical_Guide.pdf")

    def test_model_and_dataset_points_preserve_pdf_page_source(self):
        model = datasets.load_models()["aaon-vccx2-rn-rq-series-rooftop-bacnet"]
        self.assertTrue(model["points"][0].get("sourceFile"))
        self.assertIsInstance(model["points"][0].get("sourcePage"), int)

        data = datasets.build_dataset(equip_ids={"e5"})
        mapped = data["modelMappings"]["aaon-vccx2-rn-rq-series-rooftop-bacnet"]["l3MappingPoints"]
        self.assertTrue(mapped[0].get("sourceFile"))
        self.assertIsInstance(mapped[0].get("sourcePage"), int)

    def test_haystack_diff_reads_template_profiles_before_legacy_rows(self):
        """haystack --diff e5 가 옛 23행 pointTables 가 아니라 하위형식 프로파일을 본다."""
        rows = haystack.template_rows("e5", haystack.load_equip("e5"))
        names = {r["name"] for r in rows}

        self.assertGreaterEqual(len(rows), 60)
        self.assertIn("e5.rtu/실내온도", names)
        self.assertIn("e5.ahu/냉수밸브 개도", names)

    def test_every_e5_model_resolves_to_a_template_profile(self):
        """프로파일 미해결이 조용히 후보 0 이 되지 않는지 — 전에는 `or []` 로 흘렀다."""
        seen = {}
        for path in glob.glob(os.path.join(datasets.DATA, "models", "*.json")):
            model = datasets.load_json(path)
            if model.get("equipId") != "e5":
                continue
            seen[model["id"]] = datasets.template_profile_for(model)

        # 모델 수는 늘어난다(2026-08-14 JCI 옥상형 2건). 수를 박아 두면 새 모델이
        # 들어올 때마다 이 게이트가 '틀렸다'고 말한다 — 확인해야 할 것은 **미해결이
        # 없다**는 것이다.
        self.assertGreaterEqual(len(seen), 17)
        self.assertFalse([k for k, v in seen.items() if v is None])
        self.assertEqual(
            seen["trane-symbio-800-intellicore-split-system-rauk-bacnet"], "e5.rtu")
        self.assertEqual(
            seen["trane-symbio-700-precedent-and-axiom-rooftop-wshp-lontalk-scc"], "e5.rtu")
        self.assertEqual(seen["swegon-iqlogic-gold-rx-px-cx-sd-ahu-modbus"], "e5.ahu")
        # 자립형은 응축수 배관이 있어도 냉수코일 AHU가 아니다. 냉매 압축기와
        # 응축기를 한 캐비닛에 둔 직팽 패키지라 RTU 계산식을 쓴다.
        self.assertEqual(
            seen["johnson-controls-york-versecon-yswu-yswd-water-cooled-self-contained"],
            "e5.rtu",
        )
        self.assertEqual(
            seen["johnson-controls-york-l-series-lswu-lswd-lswf-self-contained"],
            "e5.rtu",
        )
        with self.assertRaises(ValueError):
            datasets.template_profile_for({"id": "x", "equipId": "e5", "cat": "HVAC.WATER.PUMP"})

    def test_rtu_template_drops_water_valves_from_required_points(self):
        """이번 사고의 회귀 테스트 — RTU 에 없는 부품을 '필수'로 물지 않는다."""
        rows = {r["name"]: r
                for r in datasets.load_template_profiles()["e5.rtu"]["templatePoints"]}

        for name in ("냉수밸브 개도", "온수밸브 개도"):
            self.assertNotEqual(rows[name]["grade"], "필수")
            self.assertTrue(rows[name].get("appliesWhen"),
                            "%s: 삭제가 아니라 적용성 조건으로 남겨야 한다" % name)
        # 그 자리를 대신하는 것 (Haystack 의 cool cmd / heat cmd)
        for name in ("냉방 지령", "난방 지령"):
            self.assertEqual(rows[name]["grade"], "필수")
            self.assertIn("cmd", rows[name]["haystack"])
        # AHU 쪽 밸브는 그대로 필수 — 실제로 있는 부품이다
        ahu = {r["name"]: r
               for r in datasets.load_template_profiles()["e5.ahu"]["templatePoints"]}
        self.assertEqual(ahu["냉수밸브 개도"]["grade"], "필수")
        self.assertEqual(ahu["온수밸브 개도"]["grade"], "필수")

    def test_every_template_point_carries_a_haystack_basis(self):
        for pid, prof in datasets.load_template_profiles().items():
            for row in prof["templatePoints"]:
                self.assertTrue(row.get("haystack") or row.get("handMade"),
                                "%s/%s: Haystack proto 근거가 없다" % (pid, row["name"]))
                self.assertTrue(row.get("match", {}).get("include"),
                                "%s/%s: 매칭 규칙이 없다" % (pid, row["name"]))

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
        # 전 이름은 '냉수·냉방'이었다 — datasets.py 에만 있고 템플릿에는 없던 유령 룰이라
        # 화면에 안 나왔다. 직팽 RTU 의 실제 신호이므로 '냉방 지령'으로 정직하게 고쳤다.
        self.assertEqual(candidates["냉방 지령"], "nvoCoolPrimary")

    def test_ahu_model_exposes_every_template_point_with_match_status(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        # 이 모델은 RTU 다. 계열(e5) 한 벌이 아니라 하위형식 템플릿과 길이가 맞아야 한다.
        self.assertEqual(model["templateProfileId"], "e5.rtu")
        template = data["templateProfiles"]["e5.rtu"]

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
        self.assertEqual(by_name["급기 풍량"]["status"], "matched")
        self.assertTrue(by_name["급기 풍량"]["matchedInputs"])

    def test_ahu_unit_ratings_feed_simulator_requirement_mappings(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "daikin-microtech-iii-4-rebel-roofpak-maverick-ii-rooftop-self-contained-bacnet"]
        by_name = {item["requirementName"]: item for item in model["simulatorRequirementMappings"]}

        airflow = by_name["급기 풍량"]
        self.assertEqual(airflow["status"], "matched")
        self.assertEqual(airflow["matchedInputs"][0]["sourceKind"], "unitModel")
        self.assertEqual(airflow["matchedInputs"][0]["fieldId"], "ratedAirflow")

        fan = by_name["급기팬 형식·모터출력"]
        self.assertEqual(fan["status"], "matched")
        self.assertEqual(fan["matchedInputs"][0]["fieldId"], "fanMotorHp")

        coil = by_name["코일 열수·핀피치"]
        self.assertEqual(coil["status"], "matched")
        self.assertEqual(coil["matchedInputs"][0]["fieldId"], "coilRowsFpi")

    def test_carrier_48_50n_merges_airflow_limits_into_size_cards(self):
        model = datasets.load_models()[
            "carrier-comfortlink-48-50n-weatherexpert-rooftop-75-150-ton-bacnet-co"]
        units = {row["unitModelNumber"]: row for row in datasets.unit_models(model)}

        self.assertEqual(units["48/50N N"]["ratedAirflow"], "15,000 – 37,500")
        self.assertEqual(units["48/50N N"]["units"]["ratedAirflow"], "CFM")
        self.assertIn("airflow limits p10", units["48/50N N"]["sourceTable"])

    def test_mitsubishi_pac_if013_merges_nominal_capacity_with_airflow_cards(self):
        model = datasets.load_models()[
            "mitsubishi-electric-pac-if013b-sif013b-mr-slim-ahu-interface-modbus"]
        units = {row["unitModelNumber"]: row for row in datasets.unit_models(model)}

        self.assertEqual(units["ZRP100"]["ratedAirflow"], "978 – 2016")
        self.assertEqual(units["ZRP100"]["grossCoolingCapacity"], "10.0")
        self.assertEqual(units["ZRP100"]["heatingCapacity"], "11.2")
        self.assertEqual(units["ZRP100"]["units"]["grossCoolingCapacity"], "kW")
        self.assertEqual(units["ZRP100"]["units"]["heatingCapacity"], "kW")

    def test_lg_eev_capacity_range_is_a_compatibility_rating(self):
        model = datasets.load_models()[
            "lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcms000"]
        units = {row["unitModelNumber"]: row for row in datasets.unit_models(model)}

        self.assertEqual(units["PRLK594A0"]["unitRole"], "eevKit")
        self.assertEqual(units["PRLK594A0"]["capacityClass"], "EEV kit")
        self.assertEqual(units["PRLK594A0"]["compatibleCapacityRange"], "112.1 – 168")
        self.assertEqual(units["PRLK594A0"]["units"]["compatibleCapacityRange"], "kW")

    def test_york_zr_large_reheat_cards_merge_base_physical_data(self):
        model = datasets.load_models()[
            "johnson-controls-york-simplicity-se-smart-equipment-york-rooftop-units-modbus"]
        units = {row["unitModelNumber"]: row for row in datasets.unit_models(model)}

        self.assertEqual(units["ZR078"]["ratedAirflow"], "2200")
        self.assertEqual(units["ZR078"]["grossCoolingCapacity"], "80000")
        self.assertEqual(units["ZR078"]["ahriNetCoolingCapacity"], "78000")
        self.assertEqual(units["ZR078"]["systemPower"], "6.96")
        self.assertEqual(units["ZR078"]["coilFaceArea"], "23.8")
        self.assertIn("base physical p21", units["ZR078"]["sourceTable"])

    def test_ahu_electrical_rows_feed_power_requirement(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        by_name = {item["requirementName"]: item for item in model["simulatorRequirementMappings"]}

        power = by_name["전원"]
        self.assertEqual(power["status"], "matched")
        self.assertEqual(power["matchedInputs"][0]["sourceKind"], "electrical")
        self.assertIn(power["matchedInputs"][0]["name"], {"voltage", "phase", "fanFla", "mca", "mop"})

    def test_ahu_table_evidence_fills_clear_candidate_gaps(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        daikin = data["modelMappings"][
            "daikin-microtech-iii-4-rebel-roofpak-maverick-ii-rooftop-self-contained-bacnet"]
        trane = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        carrier = data["modelMappings"][
            "carrier-comfortlink-48-50n-weatherexpert-rooftop-75-150-ton-bacnet-co"]
        aaon = data["modelMappings"]["aaon-vccx2-rn-rq-series-rooftop-bacnet"]
        swegon = data["modelMappings"]["swegon-iqlogic-gold-rx-px-cx-sd-ahu-modbus"]
        intellipak = data["modelMappings"]["trane-symbio-800-intellipak-lontalk-scc"]

        daikin_by_name = {item["requirementName"]: item for item in daikin["simulatorRequirementMappings"]}
        trane_by_name = {item["requirementName"]: item for item in trane["simulatorRequirementMappings"]}
        carrier_by_name = {item["requirementName"]: item for item in carrier["simulatorRequirementMappings"]}
        aaon_by_name = {item["requirementName"]: item for item in aaon["simulatorRequirementMappings"]}
        swegon_by_name = {item["requirementName"]: item for item in swegon["simulatorRequirementMappings"]}
        intellipak_by_name = {item["requirementName"]: item for item in intellipak["simulatorRequirementMappings"]}

        minimum_oa = daikin_by_name["최소 외기량"]
        self.assertEqual(minimum_oa["status"], "candidate")
        self.assertIn(minimum_oa["matchedInputs"][0]["sourceKind"], {"rating", "tableEvidence"})
        self.assertRegex(
            minimum_oa["matchedInputs"][0]["condition"].lower(),
            r"minimum outdoor air|minimum ventilation",
        )

        daikin_power = daikin_by_name["전원"]
        self.assertEqual(daikin_power["status"], "candidate")
        self.assertEqual(daikin_power["matchedInputs"][0]["sourceKind"], "tableEvidence")
        self.assertIn("electrical", daikin_power["matchedInputs"][0]["condition"].lower())

        daikin_filter = daikin_by_name["필터 형식·효율·차압"]
        self.assertNotEqual(
            daikin_filter["matchedInputs"][0]["name"] if daikin_filter["matchedInputs"] else "",
            "Steady state efficiency",
        )

        esp = trane_by_name["기외정압"]
        self.assertEqual(esp["status"], "candidate")
        self.assertEqual(esp["matchedInputs"][0]["sourceKind"], "tableEvidence")
        self.assertIn("external static pressure", esp["matchedInputs"][0]["condition"].lower())

        heat = trane_by_name["온수코일 능력"]
        self.assertEqual(heat["status"], "candidate")
        self.assertEqual(heat["matchedInputs"][0]["sourceKind"], "tableEvidence")
        self.assertIn("heating coil capacity", heat["matchedInputs"][0]["condition"].lower())

        carrier_filter = carrier_by_name["필터 형식·효율·차압"]
        self.assertEqual(carrier_filter["status"], "candidate")
        self.assertEqual(carrier_filter["matchedInputs"][0]["sourceKind"], "tableEvidence")
        self.assertIn("pressure", carrier_filter["matchedInputs"][0]["condition"].lower())

        carrier_fan = carrier_by_name["급기팬 형식·모터출력"]
        self.assertEqual(carrier_fan["status"], "candidate")
        self.assertIn(carrier_fan["matchedInputs"][0]["sourceKind"], {"rating", "tableEvidence"})
        self.assertRegex(carrier_fan["matchedInputs"][0]["condition"].lower(), r"fan motor|fan and drive")

        aaon_heat = aaon_by_name["온수코일 능력"]
        self.assertEqual(aaon_heat["status"], "candidate")
        self.assertIn("heating capacities", aaon_heat["matchedInputs"][0]["condition"].lower())

        swegon_power = swegon_by_name["전원"]
        self.assertEqual(swegon_power["status"], "candidate")
        self.assertEqual(swegon_power["matchedInputs"][0]["sourceTableKind"], "etc")
        self.assertIn("electrical connection", swegon_power["matchedInputs"][0]["condition"].lower())

        cabinet = intellipak_by_name["케이싱·단열"]
        self.assertEqual(cabinet["status"], "candidate")
        self.assertEqual(cabinet["matchedInputs"][0]["sourceTableKind"], "etc")
        self.assertIn("cabinet", cabinet["matchedInputs"][0]["condition"].lower())

    def test_ahu_template_mapping_covers_airside_controls(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "daikin-microtech-iii-4-rebel-roofpak-maverick-ii-rooftop-self-contained-bacnet"]
        by_name = {item["templateName"]: item for item in model["templatePointMappings"]}

        self.assertEqual(by_name["급기 정압"]["matchedPoint"]["name"], "DuctStatPress")
        self.assertEqual(by_name["급기 정압 설정값"]["matchedPoint"]["name"], "DuctStaticSP")
        self.assertEqual(by_name["급기팬 주파수 지령"]["matchedPoint"]["name"], "SupFanCapNetIn")
        self.assertEqual(by_name["외기댐퍼 개도"]["matchedPoint"]["name"], "EconCapacity")
        self.assertEqual(by_name["필터 차압"]["matchedPoint"]["name"], "DirtyFilterSw")
        self.assertEqual(by_name["운전 모드"]["matchedPoint"]["name"], "ApplicCmd")

    def test_ahu_simulator_requirement_mapping_does_not_force_weak_matches(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-odyssey-lontalk-scc"]
        by_name = {item["requirementName"]: item for item in model["simulatorRequirementMappings"]}

        # 표 제목으로 확인되는 값은 후보로만 올리고, 정격값처럼 확정하지 않는다
        self.assertEqual(by_name["기외정압"]["status"], "candidate")
        self.assertEqual(by_name["온수코일 능력"]["status"], "candidate")
        # 급기팬 모터출력은 원래 missing 이었지만 용어 사전에 'Motor HP' 를 넣은 뒤
        # TWE 표의 실제 값(2–3 HP)이 후보로 잡힌다 — 사전 보강의 의도된 결과다
        fan = by_name["급기팬 형식·모터출력"]
        self.assertEqual(fan["status"], "matched")
        self.assertEqual(fan["matchedInputs"][0]["fieldId"], "fanMotorHp")

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

    def test_york_continued_physical_data_merges_into_same_unit_model(self):
        model = datasets.load_models({"e5"})[
            "johnson-controls-york-simplicity-se-smart-equipment-york-rooftop-units-modbus"]
        units = {item["unitModelNumber"]: item for item in datasets.unit_models(model)}

        zj = units["ZJ078"]
        self.assertEqual(zj["ratedAirflow"], "2500")
        self.assertEqual(zj["grossCoolingCapacity"], "76000")
        self.assertEqual(zj["fanMotorHp"], "1/3")
        self.assertEqual(zj["sourcePage"], 17)
        self.assertIn("continued p18", zj["sourceTable"])

        zf = units["ZF102"]
        self.assertEqual(zf["ratedAirflow"], "3300")
        self.assertEqual(zf["grossCoolingCapacity"], "98800")
        self.assertEqual(zf["fanMotorHp"], "3/4")
        self.assertEqual(zf["sourcePage"], 23)
        self.assertIn("continued p24", zf["sourceTable"])

    def test_size_row_catalogs_qualify_repeated_size_codes(self):
        models = datasets.load_models({"e5"})
        mid = "siemens-climatix-pol908-iv-produkt-ahu-application-bacnet"
        rows = datasets.unit_models(models[mid])
        codes = [item["unitModelNumber"] for item in rows]
        self.assertEqual(len(codes), len(set(codes)), mid)
        self.assertTrue(any(" · " in code for code in codes), mid)

    def test_swegon_quickguide_keeps_condition_airflows_in_one_unit_row(self):
        model = datasets.load_models({"e5"})[
            "swegon-iqlogic-gold-rx-px-cx-sd-ahu-modbus"]
        rows = datasets.unit_models(model)
        codes = [item["unitModelNumber"] for item in rows]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertNotIn("GOLD 004", codes)

        rx = {item["unitModelNumber"]: item for item in rows}["GOLD RX 004"]
        self.assertEqual(rx["ratedAirflow"], "290 - 1620")
        self.assertEqual(rx["ecodesignAirflow"], "290 - 1620")
        self.assertEqual(rx["sfp15Airflow"], "1356")
        self.assertEqual(rx["sfp20Airflow"], "1620")
        self.assertEqual(rx["airflowConfiguration"], "GOLD RX")
        self.assertEqual(rx["units"]["ratedAirflow"], "m³/h")
        self.assertEqual(rx["units"]["ecodesignAirflow"], "m³/h")

        self.assertIn("GOLD RX Top 004 Top", codes)
        self.assertIn("GOLD PX 004", codes)
        self.assertIn("GOLD PX Top 004 Top", codes)
        self.assertIn("GOLD CX Sections 035", codes)
        self.assertIn("GOLD CX Longest section 035", codes)

    def test_rebel_size_codes_get_family_prefix_from_title(self):
        # Rebel 물리 데이터 — 첫 행이 '003' 같은 크기 코드뿐이라 제목의 'Model DPS'
        # 제품군을 붙여 형번으로 만든다. EER 은 'EER1, 7' 각주 표기.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "daikin-microtech-iii-4-rebel-roofpak-maverick-ii-rooftop-self-contained-bacnet"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertEqual(len([code for code in units if code.startswith("DPS ")]), 13)
        dps = units["DPS 003"]
        self.assertEqual(dps["capacityClass"], "3 Tons")
        self.assertEqual(dps["ratedAirflow"], "1125")
        self.assertEqual(dps["units"]["ratedAirflow"], "CFM")   # 철자 통일
        self.assertEqual(dps["eer"], "13.5")
        # Rebel 물리 데이터는 캐비닛 병합 셀로 팬 모터 범위를 한 번만 적는다.
        # 같은 캐비닛의 뒤 형번에도 같은 값을 전파해야 한다.
        self.assertEqual(units["DPS 004"]["fanMotorHp"], "1.3 / 2.3 / 4.0")
        self.assertEqual(units["DPS 010"]["fanMotorHp"], "4.0 / 8.0")
        self.assertEqual(units["DPS 025"]["fanMotorHp"], "2.0 / 3.0 / 5.0 / 7.5 / 10.0 / 15.0 / 20.0")

    def test_daikin_microtech_ahu_catalogs_add_non_rebel_unit_families(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "daikin-microtech-iii-4-rebel-roofpak-maverick-ii-rooftop-self-contained-bacnet"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        self.assertGreater(len(units), 13)
        self.assertTrue(any(code.startswith("MPS ") for code in units))
        self.assertTrue(any(code.startswith("SWP-J ") for code in units))

    def test_every_e5_model_has_unit_candidates(self):
        # 재발 방지 게이트 — 공조기 모델은 형번·정격 카드가 반드시 1개 이상이어야 한다.
        # 새 벤더를 넣고 이 테스트가 깨지면 체크리스트 5번(인식 사다리 확장)을 하지
        # 않은 것이다. "조판 탓" 으로 넘기지 말 것 (AAON 실사례 — 텍스트 층 파서로 해결).
        data = datasets.build_dataset(equip_ids={"e5"})
        # 예외는 **정격 문서가 아예 없는 모델**이다. BAS 포인트 리스트나 IOM만
        # 있는 JCI York 제품은 형번을 뽑을 원문 자체가 없다. 사다리를 넓혀서
        # 될 일이 아니라 카탈로그를 더 받아야 하는 일이라, 여기서 막으면 게이트가
        # '고칠 수 없는 실패'로 상주한다. 대신 사유가 gap 에 적혀 있어야 하고
        # validate.py 의 units-none / units-none-undoc 가 그것을 매번 확인한다.
        # ⚠ 면제 판정은 **모델 레코드**로 한다. modelMappings 에는 사양 키가 없어서
        #    거기서 판정하면 조건이 항상 참이 되고 게이트가 통째로 무력해진다
        #    (실제로 그렇게 썼다가 19건 전부 면제되는 것을 확인하고 고쳤다).
        no_rating = set()
        for path in glob.glob(os.path.join(datasets.DATA, "models", "*.json")):
            model = datasets.load_json(path)
            if model.get("equipId") != "e5":
                continue
            if not (model.get("specTables") or model.get("variants") or model.get("spec")):
                no_rating.add(model["id"])
        missing = [mid for mid, m in data["modelMappings"].items()
                   if not m.get("unitModels") and mid not in no_rating]
        self.assertEqual(missing, [])
        # 면제가 늘어나면 게이트가 조용히 헐거워진다 — 승인한 모델 id를 정확히 박는다.
        self.assertEqual(no_rating, {
            "johnson-controls-york-l-series-lswu-lswd-lswf-self-contained",
            "johnson-controls-york-millenium-packaged-rooftop-unit",
            "johnson-controls-york-rooftop-25-30-40-ton-ipu-control",
            "johnson-controls-york-sunline-3000-rooftop",
            "johnson-controls-york-tempmaster-omnielite-packaged-rooftop-unit",
            "johnson-controls-york-versecon-yswu-yswd-water-cooled-self-contained",
            "johnson-controls-york-ypal-packaged-rooftop-unit",
            # ── YKN2Open 게이트웨이와 그것이 덮는 제품 코드 (2026-08-21) ──────
            # 게이트웨이 문서에는 정격이 없다(BAS 포인트만). 덮는 제품 코드는
            # 별칭 레코드라 목록 자체를 갖지 않는다 — 정격은 더 없다.
            # ✓ RTC·RTH 는 여기 있었는데 뺐다 — 기술 가이드 2건에서 정격을 취입해
            #   진짜 제품 모델(형번 12건)이 생겼고, 별칭이 필요 없어져 지워졌다.
            #   VITALITY 4코드는 아직 정격 문서가 없어 별칭으로 남는다.
            "johnson-controls-york-ykn2open-control-board",
            "johnson-controls-york-vac",
            "johnson-controls-york-vah",
            "johnson-controls-york-vch",
            "johnson-controls-york-vir",
            # ── 공조기 포털 (2026-08-31) ───────────────────────────
            # YKL 은 IOM 본문의 Modbus 레지스터 표만 가졌다 — 정격도 형번도 없다.
            # 사다리를 넓혀서 될 일이 아니라 제품 카탈로그를 더 받아야 하는 일이다.
            "johnson-controls-york-ykl-compact-low-profile-ahu",
            # VEC100 은 응용 노트라 정격도 형번도 없다. 더욱이 오브젝트별 **주소도**
            # 없는 메뉴 항목 목록이다(validate 의 points-unaddressed 가 그 수를 드러낸다).
            # 사다리를 넓혀서 될 일이 아니라 제품 카탈로그가 따로 있어야 한다.
            "johnson-controls-verasys-vec100-generic-rtu-controller",
        })

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
        self.assertEqual(rn6["cabinetSize"], "A")
        self.assertEqual(rn6["airflowConfiguration"], "Vertical")

    def test_model_selector_label_keeps_vendor_and_product_family(self):
        _equips, models, _l3, _terms = build.load()
        ahu_models = {m["id"]: m for m in models["e5"]}
        aaon = ahu_models["aaon-vccx2-rn-rq-series-rooftop-bacnet"]

        self.assertEqual(aaon["selectorLabel"], "AAON RN/RQ Rooftop · VCCX2")
        self.assertIn("VCCX2", aaon["selectorLabel"])
        self.assertIn("AAON", aaon["selectorLabel"])
        self.assertIn("RN/RQ", aaon["selectorLabel"])

    def test_lennox_general_data_text_yields_units(self):
        # Lennox Enlight LGT — EHB 표 인식은 구간 라벨(General Data·Cooling
        # Performance)이 항목 라벨과 눌려 라벨-값 짝이 끊긴다. 텍스트 층 주입
        # (vendor_lennox)으로 4형번을 만들고, 기존 e5 스키마 클래스가 무수정으로
        # 받는지(수집 3규칙 검증)를 본다. IEER 는 문서상 072 3상만 게재된다.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "lennox-core-unit-controller-enlight-model-l-rooftop-bacnet"]
        units = {u["unitModelNumber"]: u for u in model["unitModels"]}

        self.assertEqual(len(units), 7)   # LGT 4(3~6톤) + LHT 3(13~20톤 히트펌프)
        lgt36 = units["LGT036H4E"]
        self.assertEqual(lgt36["capacityClass"], "3 Tons")   # 정규화: 'Ton' → 'Tons'
        self.assertEqual(lgt36["ratedAirflow"], "1200/800")
        self.assertEqual(lgt36["units"]["ratedAirflow"], "CFM high/low")
        self.assertEqual(lgt36["grossCoolingCapacity"], "36,600")
        self.assertEqual(lgt36["ahriNetCoolingCapacity"], "36,000")
        self.assertEqual(lgt36["eer"], "13.3")
        self.assertEqual(lgt36["ieer"], "—")
        self.assertEqual(lgt36["seer"], "17.8")
        self.assertEqual(units["LGT072H4E"]["ieer"], "17.0")
        # 히트펌프(LHT)는 난방 성능까지 — 문서 라벨 표기가 LGT 와 달라도(- Btuh)
        # 유연 패턴이 받는다
        lht13 = units["LHT156H4M"]
        self.assertEqual(lht13["capacityClass"], "13 Tons")
        self.assertEqual(lht13["heatingCapacity"], "144,000")
        self.assertEqual(lht13["cop"], "3.40")
        self.assertEqual(lht13["systemPower"], "12.3")

    def test_lg_ahu_kit_split_and_eev_combinations(self):
        # LG AHU 통신 킷 — 환기(PAHCMR000)·급기(PAHCMS000) 맵이 같은 레지스터
        # 번호를 재사용해 구간(sect) 분리로 두 모델이 된다. 형번은 조합 EEV 킷
        # (문서 호환 'O' 인 것만 — 환기 3종·급기 4종).
        data = datasets.build_dataset(equip_ids={"e5"})
        rkit = data["modelMappings"][
            "lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcmr000"]
        skit = data["modelMappings"][
            "lg-ahu-comm-kit-0caa0-02m-multi-v-single-ahu-interface-modbus-pahcms000"]

        self.assertEqual(rkit["counts"]["l3MappingPoints"], 19)
        self.assertEqual(skit["counts"]["l3MappingPoints"], 28)
        r_units = {u["unitModelNumber"]: u for u in rkit["unitModels"]}
        s_units = {u["unitModelNumber"]: u for u in skit["unitModels"]}
        self.assertEqual(len(r_units), 3)
        self.assertEqual(len(s_units), 4)
        self.assertEqual(r_units["PRLK048A0"]["capacityClass"], "EEV kit")
        self.assertEqual(r_units["PRLK048A0"]["compatibleCapacityRange"], "3.6 – 28")
        self.assertEqual(r_units["PRLK048A0"]["unitRole"], "eevKit")
        self.assertIn("PRLK594A0", s_units)     # 168 kW 급은 급기 킷만 지원
        self.assertNotIn("PRLK594A0", r_units)

    def test_mitsubishi_pacif013_outdoor_combinations(self):
        # Mitsubishi PAC-IF013 — 설계 가이드라인의 표준 풍량 표(텍스트 층 주입)에서
        # 조합 실외기 시리즈×용량 22건. 한 글자 계열(P200)도 형번 토큰이어야 한다.
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "mitsubishi-electric-pac-if013b-sif013b-mr-slim-ahu-interface-modbus"]
        units = {u["unitModelNumber"]: u for u in model["unitModels"]}

        self.assertEqual(len(units), 22)
        self.assertEqual(units["ZRP35"]["ratedAirflow"], "372 – 738")
        self.assertEqual(units["ZRP35"]["units"]["ratedAirflow"], "m³/h")
        self.assertIn("P200", units)
        self.assertIn("SHW230", units)
        # 포인트는 Modbus 절대 참조(코일 1·입력 30001~·홀딩 40001~) 20점
        self.assertEqual(model["counts"]["l3MappingPoints"], 20)

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

    def test_pick_patterns_reference_defined_features(self):
        # 사전 우선 규칙의 패턴 층 강제 — 추출 pick(UNIT_FIELD_PICKS·CAPACITY_FILL)이
        # 사전에 없는 필드로 값을 뽑으면 확정본 저장에서 유실된다. 패턴 정의 자체를 잡는다.
        ids = set(U.field_ids(U.load_schema()))
        for fid in list(datasets.UNIT_FIELD_PICKS) + list(datasets.CAPACITY_FILL_LABELS):
            self.assertIn(fid, ids,
                          "pick 필드 %r 가 속성 사전(features)에 없다 — 사전 먼저" % fid)

    def test_schema_extension_features_fill_from_documents(self):
        # --propose-features 발굴로 채택한 확장 필드가 실제 문서값으로 채워지는지 —
        # 스키마가 벤더 공개 수준을 따라 성장할 수 있음을 상시 검증한다.
        data = datasets.build_dataset(equip_ids={"e5"})
        lgt = {u["unitModelNumber"]: u for u in data["modelMappings"][
            "lennox-core-unit-controller-enlight-model-l-rooftop-bacnet"]["unitModels"]}
        self.assertEqual(lgt["LGT036H4E"]["systemPower"], "2.7")
        self.assertEqual(lgt["LGT036H4E"]["units"]["systemPower"], "kW")
        self.assertEqual(lgt["LGT036H4E"]["soundRating"], "75")
        self.assertEqual(lgt["LGT036H4E"]["units"]["soundRating"], "dBA")

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

    def test_jci_simplicity_modbus_mapping_preserves_scale_and_bac_oid(self):
        model = json.loads(Path(
            "data/models/johnson-controls-york-simplicity-se-smart-equipment-york-rooftop-units-modbus.json"
        ).read_text(encoding="utf-8"))
        net_st = next(p for p in model["points"] if p["inst"] == 1)

        # 정본 문서(5177447-UTS-A-1215)에는 오브젝트 타입·단위 열이 없어 한때
        # type='MB' · unit=None 이었다. Premier Start-Up 가이드(5586996-JSG-A-520)의
        # Table 32 를 Object ID 로 이어 타입·단위를 채웠다 — vendor_jci.py 참고.
        # 이름·레지스터는 여전히 정본 문서가 기준이다(보강이 덮지 않는다).
        self.assertEqual(net_st["type"], "AV")
        self.assertEqual(net_st["name"], "Net Override Space Temp")
        self.assertEqual(net_st.get("unit"), "°F")
        self.assertEqual(net_st.get("unitRaw"), "°F")
        self.assertEqual(
            net_st.get("typeSource"),
            "JCI_SunPremier_25-50t_StartUp_5586996-JSG-A-520.pdf")
        self.assertEqual(net_st.get("bacOid"), 29526)
        self.assertEqual(net_st.get("modbusRegister"), 1)
        self.assertEqual(net_st.get("modbusScaleFactor"), "X10")
        self.assertEqual(net_st.get("modbusSignedFlag"), "Signed")
        self.assertEqual(net_st.get("modbusWritableFlag"), 1)
        self.assertEqual(net_st.get("sourcePage"), 15)


class InterfacePointTemplateGateTest(unittest.TestCase):
    """게이트 — 템플릿 매처가 인터페이스형 포인트를 보고 있나.

    포인트는 모델이 아니라 인터페이스에 속하는데(D-016) 매처만 옛 자리
    (model['points'])를 보고 있었다. JCI 취입분은 전부 인터페이스형이라
    5,629점을 가진 e5 모델 8개가 **한 행도 못 채우고 'missing' 으로 보였다** —
    남은 일을 실제보다 많게 보여 주는 쪽으로 틀린 것이다. 조용히 0 이 되는
    부류라 총계만 봐서는 못 알아챈다.
    """

    def _e5_models(self):
        out = []
        for path in glob.glob(os.path.join(datasets.DATA, "models", "*.json")):
            model = datasets.load_json(path)
            if model.get("equipId") == "e5":
                out.append(model)
        return out

    def test_interface_models_are_not_silently_empty(self):
        """인터페이스형 e5의 각 판이 한 행도 못 채우면 운다."""
        empty, seen, points = [], 0, 0
        for model in self._e5_models():
            if not model.get("interfaces"):
                continue
            for scope in datasets.model_mapping_inputs(model):
                if scope["kind"] != "interface":
                    continue
                seen += 1
                points += len(scope["points"])
                picked = datasets.find_template_candidates(
                    datasets.template_profile_for(model), scope["points"])
                if not picked:
                    empty.append("%s/%s" % (model["id"], scope["interfaceId"]))

        # 하한은 시험이 일부 모델/판을 건너뛰며 통과하는 상태를 막는다. 새 판 추가는
        # 통과하고, 기존 판이 통째로 사라지면 아래 L3 전수 게이트가 함께 운다.
        self.assertGreaterEqual(seen, 27)
        self.assertGreaterEqual(points, 5961)
        self.assertEqual(empty, [])

    def test_flat_models_feed_the_matcher_unchanged(self):
        """회귀 — 평면형 모델의 매처 입력은 한 글자도 안 바뀐다."""
        checked = 0
        for model in self._e5_models():
            if model.get("interfaces"):
                continue
            flat = [p for p in (model.get("points") or []) if isinstance(p, dict)]
            if not flat:
                continue
            checked += 1
            self.assertEqual(datasets.model_template_points(model), flat)
        self.assertGreaterEqual(checked, 15)

    def test_interface_point_type_is_copied_only_where_the_vocabulary_matches(self):
        """어휘가 같은 계통만 옮긴다 — 번역하면 매칭이 조용히 틀어진다.

        bacnet.objectType 은 값이 AI·AV·BI·BV·MSV 로 평면 type 과 글자가 같다.
        n2(ADF·BD·ADI) · yorktalk('A. Monitor') · lon(nvo·nvi) 은 다른 어휘라
        옮기지 않고 비운다. 비면 점수 가산만 못 받고 include/exclude 는 그대로 된다.
        """
        bac = datasets.flatten_interface_point({
            "common": {"name": "Discharge Temperature 1"},
            "blocks": {"bacnet": {"objectType": "AI", "instance": 7}},
        })
        self.assertEqual(bac["type"], "AI")
        self.assertEqual(bac["inst"], 7)

        n2 = datasets.flatten_interface_point({
            "common": {"name": "Supply Air Temp"},
            "blocks": {"n2": {"pointType": "ADF", "address": 3},
                       "yorktalk": {"pointType": "A. Monitor"}},
        })
        self.assertIsNone(n2["type"])          # ADF 를 AI 로 옮기지 않는다
        self.assertEqual(n2["name"], "Supply Air Temp")

        # 주소가 0 인 점이 있다 — or 로 쓰면 0 이 사라진다(YKL 40001 이 그 자리다).
        zero = datasets.flatten_interface_point({
            "common": {"name": "Unit open and close variable"},
            "blocks": {"modbus": {"address": 0}},
        })
        self.assertEqual(zero["inst"], 0)

    def test_ykl_air_handling_points_reach_the_screen_template(self):
        """공조기 포털에서 취입한 YKL 157점이 화면 행에 실제로 붙는다."""
        model = datasets.load_json(os.path.join(
            datasets.DATA, "models",
            "johnson-controls-york-ykl-compact-low-profile-ahu.json"))
        pts = datasets.model_template_points(model)
        self.assertEqual(len(pts), 157)
        names = {p["templateName"] for p in
                 datasets.find_template_candidates("e5.ahu", pts)}
        self.assertIn("급기온도", names)
        self.assertIn("필터 차압", names)

    def test_zero_instance_wins_a_score_tie(self):
        """주소 0은 결측값이 아니며 같은 점수에서는 1보다 먼저 선택된다."""
        picked = datasets.find_template_candidates("e5.ahu", [
            {"name": "Supply Air Temperature", "type": "AI", "inst": 1},
            {"name": "Supply Air Temperature", "type": "AI", "inst": 0},
        ])
        supply = next(p for p in picked if p["templateName"] == "급기온도")
        self.assertEqual(supply["instance"], 0)

    def test_interface_models_are_mapped_one_interface_at_a_time(self):
        """서로 다른 판을 합쳐 어느 판에도 없는 가상 매핑을 만들지 않는다."""
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "johnson-controls-york-ypal-packaged-rooftop-unit"]
        source = datasets.load_models()[model["id"]]

        self.assertEqual(model["mappingScope"], "interface")
        self.assertEqual(
            [m["interfaceId"] for m in model["interfaceMappings"]],
            [i["id"] for i in source["interfaces"]],
        )
        # 기존 최상위 필드는 합집합이 아니라 첫 판의 호환 별칭이다.
        self.assertEqual(
            model["templatePointMappings"],
            model["interfaceMappings"][0]["templatePointMappings"],
        )
        self.assertEqual(
            model["templatePointCandidates"],
            model["interfaceMappings"][0]["templatePointCandidates"],
        )
        self.assertLess(
            max(x["counts"]["templateCandidates"] for x in model["interfaceMappings"]),
            25,
        )

    def test_interface_points_are_preserved_in_l3_with_their_interface_id(self):
        """템플릿뿐 아니라 원문 L3 목록도 판 경계와 출처를 보존한다."""
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "johnson-controls-york-ykl-compact-low-profile-ahu"]

        self.assertEqual(model["counts"]["l3MappingPoints"], 157)
        self.assertEqual(len(model["l3MappingPoints"]), 157)
        self.assertEqual(
            {p["interfaceId"] for p in model["l3MappingPoints"]}, {"air-modbus"})
        self.assertTrue(all(p.get("sourceFile") for p in model["l3MappingPoints"]))
        self.assertTrue(all(isinstance(p.get("sourcePage"), int)
                            for p in model["l3MappingPoints"]))

    def test_every_e5_source_point_reaches_l3_once(self):
        """평면과 판별 원문 수의 합이 L3 보존 수와 전 모델에서 정확히 같다."""
        data = datasets.build_dataset(equip_ids={"e5"})
        sources = datasets.load_models()
        for model_id, mapped in data["modelMappings"].items():
            model = sources[model_id]
            expected = len(model.get("points") or []) + sum(
                len(scope.get("points") or []) for scope in model.get("interfaces") or [])
            self.assertEqual(
                mapped["counts"]["l3MappingPoints"], expected, model_id)

    def test_structured_protocol_fields_survive_interface_l3_mapping(self):
        """동시 프로토콜 주소·RW·범위를 얇은 instance 하나로 잃지 않는다."""
        source = {
            "common": {
                "name": "Supply Air Temperature",
                "readWrite": "R",
                "range": {"min": -40, "max": 125},
            },
            "blocks": {
                "bacnet": {"objectType": "AI", "instance": 1},
                "modbus": {
                    "address": 514,
                    "refClass": "holding-register",
                    "dataType": "int16",
                },
            },
            "provenance": {
                "interfaceId": "dual-protocol",
                "sourceFile": "points.pdf",
                "sourcePage": 7,
            },
        }
        flat = datasets.flatten_interface_point(source, {
            "id": "dual-protocol",
            "protocols": ["bacnet", "modbus"],
        })
        mapped = datasets.mapping_points([flat], [])[0]

        self.assertEqual(mapped["common"]["readWrite"], "R")
        self.assertEqual(mapped["common"]["range"]["max"], 125)
        self.assertEqual(mapped["blocks"]["bacnet"]["instance"], 1)
        self.assertEqual(mapped["blocks"]["modbus"]["address"], 514)
        self.assertEqual(mapped["blocks"]["modbus"]["refClass"], "holding-register")
        self.assertEqual(mapped["provenance"]["sourcePage"], 7)
        self.assertIsNot(mapped["blocks"], source["blocks"])

    def test_known_ypal_prose_false_positives_stay_unmatched(self):
        """설명문에 낱말만 나온 상태·설정점·풍량을 제어 포인트로 집지 않는다."""
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"][
            "johnson-controls-york-ypal-packaged-rooftop-unit"]
        forbidden = {
            ("급기팬 주파수 지령", "UNSTABLE SYSTEM"),
            ("급기온도", "ACTIVE SUPPLY AIR TEMP SETP"),
            ("외기댐퍼 개도", "OUTSIDE AIR TOTAL FLOW"),
            ("가습 지령", "Underfloor Air Humidity BAS"),
        }
        actual = {
            (p["templateName"], p["sourceName"])
            for scope in model["interfaceMappings"]
            for p in scope["templatePointCandidates"]
        }
        self.assertFalse(forbidden & actual)

    def test_known_vec100_and_ykl_prose_false_positives_stay_unmatched(self):
        """모델번호·설명문 열거·동결 설명을 운전값으로 집지 않는다."""
        names = [
            "johnson-controls-verasys-vec100-generic-rtu-controller.json",
            "johnson-controls-york-l-series-lswu-lswd-lswf-self-contained.json",
            "johnson-controls-york-tempmaster-omnielite-packaged-rooftop-unit.json",
            "johnson-controls-york-ykl-compact-low-profile-ahu.json",
            "johnson-controls-york-ypal-packaged-rooftop-unit.json",
        ]
        models = [datasets.load_json(os.path.join(datasets.DATA, "models", name))
                  for name in names]
        forbidden = {
            ("운전 모드", "Unit Model Number"),
            ("운전 모드", "VAV RAT Heating Setpoint"),
            ("환기온도", "Control temperature type"),
            ("운전 모드", "Heating coil freeze protection maximum temperature value"),
            ("운전 모드", "Heat exchanger freeze protection maximum temperature value"),
            ("급기팬 주파수 지령", "OA Damper Min Position"),
            ("가습 지령", "Under Floor Humidity BAS"),
            ("급기온도", "Supply Air Tempering Status"),
            ("환기 CO2", "IAQ Offset"),
            ("급기팬 주파수 지령", "Supply Fan Command"),
            ("외기댐퍼 개도", "Demand Ventilation Maximum Economizer Position"),
            ("급기 정압", "Duct Static Press Reset"),
            ("급기 정압 설정값", "Duct Static Press Current"),
            ("환기팬 주파수 지령", "Return Fan Pressure Current"),
            ("운전 모드", "Occupancy Command"),
            ("운전 모드", "Cooling Mode Enabled For Operation"),
            ("냉방 지령", "SAT Limit for Cooling Enable"),
            ("난방 지령", "Night Setback For Heating"),
            ("온수밸브 개도", "Heating Valve Action"),
        }
        actual = {
            (p["templateName"], p["sourceName"])
            for model in models
            for scope in datasets.model_mapping_inputs(model)
            for p in datasets.find_template_candidates(
                datasets.template_profile_for(model), scope["points"])
        }
        self.assertFalse(forbidden & actual)

    def test_flat_models_do_not_publish_a_fake_interface_mapping(self):
        """평면 포인트 호환 매핑을 실제 통신판으로 오인하게 만들지 않는다."""
        source = {
            "id": "flat-fixture",
            "equipId": "e5",
            "vendor": "test",
            "model": "flat",
            "name": "flat",
            "cat": "HVAC.AIR.AHU",
            "points": [{"name": "Supply Air Temperature", "type": "AI", "inst": 0}],
            "interfaces": [],
        }
        with mock.patch.object(datasets, "load_models", return_value={source["id"]: source}):
            data = datasets.build_dataset(equip_ids={"e5"})
        mapped = data["modelMappings"][source["id"]]

        self.assertEqual(mapped["mappingScope"], "legacy-flat")
        self.assertIsNone(mapped["defaultMappingScopeId"])
        self.assertEqual(mapped["interfaceMappings"], [])
        self.assertEqual(mapped["counts"]["interfaceMappings"], 0)

    def test_bms_and_simulator_views_are_reachable_native_button_groups(self):
        """생성기에서 BMS/시뮬레이터 패널을 실제 버튼으로 열 수 있어야 한다."""
        path = os.path.join(os.path.dirname(datasets.HERE), "evidence", "gen2.py")
        with open(path, encoding="utf-8") as stream:
            source = stream.read()

        self.assertIn("views.push({id:'bms'", source)
        self.assertIn("views.push({id:'sim'", source)
        self.assertIn('role="group"', source)
        self.assertIn('aria-pressed="', source)

    def test_catalog_purpose_data_carries_interface_mappings_without_l3_duplication(self):
        """HTML용 축약 데이터도 선택 판의 매핑을 찾을 수 있어야 한다."""
        purpose = build.load_purpose_dataset()
        model = purpose["johnson-controls-york-ypal-packaged-rooftop-unit"]

        self.assertTrue(model["defaultMappingScopeId"].startswith("interface:"))
        self.assertEqual(len(model["interfaceMappings"]), 11)
        self.assertNotIn("l3MappingPoints", model)
        self.assertTrue(all("templatePointMappings" in scope
                            for scope in model["interfaceMappings"]))


if __name__ == "__main__":
    unittest.main()
