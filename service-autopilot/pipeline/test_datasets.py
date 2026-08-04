# -*- coding: utf-8 -*-
import unittest

import datasets


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

        self.assertEqual(by_name["기외정압"]["status"], "missing")
        self.assertEqual(by_name["급기팬 형식·모터출력"]["status"], "missing")
        self.assertEqual(by_name["온수코일 능력"]["status"], "missing")

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
        self.assertEqual(big["capacityClass"], "25 Ton")
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
        self.assertEqual(twe["fanMotorHp"], "2.0/3.0")
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
        seventy_five = units["IntelliPak 75 Ton"]
        self.assertEqual(seventy_five["ratedAirflow"], "15,000 - 30,000")

    def test_precedent_rooftop_units_are_packaged_not_condensing(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-precedent-and-axiom-rooftop-wshp-lontalk-scc"]
        units = {item["unitModelNumber"]: item for item in model["unitModels"]}

        ysc = units["T/YSC036G3,4,W"]
        self.assertEqual(ysc["unitRole"], "packagedUnit")
        self.assertEqual(ysc["ahriNetCoolingCapacity"], "36,000")
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

    def test_inducer_and_power_exhaust_motors_are_not_electrical_rows(self):
        data = datasets.build_dataset(equip_ids={"e5"})
        model = data["modelMappings"]["trane-symbio-700-precedent-and-axiom-rooftop-wshp-lontalk-scc"]
        sources = {r["sourceTable"] for r in model["electricalRows"]}

        self.assertFalse(any("inducer" in s.lower() or "power exhaust" in s.lower()
                             for s in sources))


if __name__ == "__main__":
    unittest.main()
