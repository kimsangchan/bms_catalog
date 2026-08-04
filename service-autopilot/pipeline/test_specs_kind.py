# -*- coding: utf-8 -*-
import unittest

import specs


def table(title, header, quantities=None, orientation="column"):
    return {
        "title": title,
        "header": header,
        "quantities": quantities or [specs.quantity_of(h) for h in header],
        "orientation": orientation,
        "rows": [["x", "1"]],
    }


class SpecTableKindTest(unittest.TestCase):
    def test_ahu_accessory_compatibility_is_reference_not_rating(self):
        t = table(
            "Table 4. TWE Accessories",
            ["Model Base (Subbase)", "Used With"],
        )

        self.assertEqual(specs.table_kind(t), "etc")

    def test_ahu_unit_wiring_is_reference_not_rating(self):
        t = table(
            "Table 77. Unit wiring with electric heat (single point connection)",
            [
                "Used With",
                "Heater Model Number",
                "Heater kW Rating",
                "Unit Power Supply",
                "Control Stages",
                "MCA",
                "MOP",
            ],
        )

        self.assertEqual(specs.table_kind(t), "etc")

    def test_ahu_throw_distance_is_performance_not_rating(self):
        t = table(
            "Table 64. Discharge plenum and grille assembly throw distance (ft)",
            ["Tons", "Model No.", "CFM", "Louver Angle Deflection Position Straight 20 40 55"],
        )

        self.assertEqual(specs.table_kind(t), "perf")

    def test_ahu_electrical_characteristics_remain_rating(self):
        t = table(
            "Table 76. Electrical characteristics — standard motors",
            ["Tons", "Unit Model Number", "Volts", "Phase", "HP", "Amps", "MCA", "MOP"],
        )

        self.assertEqual(specs.table_kind(t), "rating")

    def test_korean_condition_performance_title_is_performance(self):
        t = table(
            "성능표 (조건별 조회) — SS-PRC028AA-EN_06262022.pdf p65",
            ["", "", "", "", "", "1.5 HP Standard Motor"],
            quantities=[None, None, None, None, None, "power"],
        )

        self.assertEqual(specs.table_kind(t), "perf")

    def test_heating_coil_capacity_is_performance_not_rating(self):
        t = table(
            "Table 69. Hot water heating coil capacity - air handler (60Hz)",
            ["Tons", "Unit Model No.", "Airflow (CFM)", "Enter Air Temp", "Entering Water Temperature"],
        )

        self.assertEqual(specs.table_kind(t), "perf")

    def test_roof_curb_dimensions_are_dimension_not_rating(self):
        t = table(
            "Table 50. Roof curb dimensional data (inches)",
            ["Description", "A", "B", "C", "Voltage"],
            quantities=[None, "current", None, None, "voltage"],
        )

        self.assertEqual(specs.table_kind(t), "dim")

    def test_physical_data_title_beats_cabinet_header_word(self):
        # Rebel 카탈로그 — 머리글의 'Small cabinet' 낱말로 참고 처리되면 안 된다
        t = table(
            "Rebel® Physical Data — Model DPS 003 – 028",
            ["Model", "Small cabinet", "", "Medium cabinet", "", "Large cabinet"],
        )

        self.assertEqual(specs.table_kind(t), "rating")

    def test_envistar_capacity_table_beats_fuse_reference_word(self):
        # Envistar — 퓨즈 열이 있어도 풍량·냉방능력 표는 정격이다
        t = table(
            "기타 — IVProdukt_Envistar_Catalog_2024-3_en.pdf p30",
            ["Size", "Dimensions (mm)", "Air flow (m3/s) a", "", "",
             "Cooling power (kW)", "External fuse protection c", "Weight d (kg)"],
        )

        self.assertEqual(specs.table_kind(t), "rating")

    def test_cabinet_feature_text_is_reference_not_rating(self):
        t = table(
            "Cabinet",
            ["Features", "Benefits"],
            quantities=[None, "current"],
        )

        self.assertEqual(specs.table_kind(t), "etc")


if __name__ == "__main__":
    unittest.main()
