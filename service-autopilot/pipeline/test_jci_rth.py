# -*- coding: utf-8 -*-
"""JCI Roomtop RTC/RTH 정격 취입 회귀 시험.

원문 PDF 는 저장소에 없다(D-008). 그래서 두 가지로 나눠 건다.
  · 파서 로직 — 원문에서 뜬 **조각을 그대로 옮긴** 가짜 쪽으로
  · 확정본 값 — 원문 3쪽 명판(Nominal power)을 **여기에 적어 두고** 대조
    (능력표와 다른 쪽에 따로 인쇄된 값이라 같은 표를 두 번 읽는 것이 아니다)
"""
import json
import os
import types
import unittest

import datasets
import vendor_jci_rth as R

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = os.path.join(HERE, "data", "units", R.MID + ".json")

# 원문 3쪽 'Nominal power: Cooling / Heating' — K판·L판 각각에 인쇄된 값 그대로.
# 능력표(7·8쪽)와 **다른 쪽**이라 대조가 성립한다.
NAMEPLATE = {
    "RTH-07K": ("6 900", "8 000"), "RTH-10K": ("9 400", "11 000"),
    "RTH-15K": ("14 000", "14 500"), "RTH-20K": ("18 000", "18 000"),
    "RTH-25K": ("20 200", "20 200"), "RTH-30K": ("27 000", "27 500"),
    "RTH-07L": ("7 400", "7 400"), "RTH-10L": ("9 300", "11 700"),
    "RTH-15L": ("14 100", "13 800"), "RTH-20L": ("19 900", "17 800"),
    "RTH-25L": ("22 200", "20 800"), "RTH-30L": ("26 800", "25 400"),
}


def _span(x0, y, text, font="Helvetica", w=None):
    w = w if w is not None else max(6.0, len(text) * 4.0)
    return {"text": text, "font": font, "bbox": (x0, y - 4, x0 + w, y + 4)}


def _page(spans):
    doc = {"blocks": [{"lines": [{"spans": spans}]}]}
    return types.SimpleNamespace(get_text=lambda *a, **k: doc)


class FontRepairTest(unittest.TestCase):
    """ToUnicode 가 1 밀린 임베드 폰트 (함정 1)."""

    def test_shifted_font_is_restored(self):
        self.assertEqual(R.dec("MPT!DPNQPOFOUFT"), "LOS COMPONENTES")
        self.assertEqual(R.dec("DPNQSFTTPS!2"), "COMPRESSOR 1")
        self.assertEqual(R.dec("249!±D"), "138 °C")

    def test_space_is_left_alone(self):
        """자간 때문에 끼워 넣은 진짜 공백까지 내리면 제어문자가 된다."""
        # '!' 하나만 공백이 되고, 자간 공백은 그대로 남는다
        self.assertEqual(R.dec("J T P ! 2 5 1 1 2"), "I S O   1 4 0 0 1")

    def test_clean_font_is_not_touched(self):
        pg = _page([_span(210, 100, "RTH-07K"), _span(300, 100, "6 900")])
        lines = R.page_lines(pg)
        self.assertEqual(sorted(t for cs in lines.values() for _a, _b, t in cs),
                         ["6 900", "RTH-07K"])

    def test_only_the_broken_font_is_shifted(self):
        pg = _page([_span(210, 100, "BJS!PVUMFU", font="Gen_Helvetica"),
                    _span(300, 100, "0.32")])
        got = sorted(t for cs in R.page_lines(pg).values() for _a, _b, t in cs)
        self.assertEqual(got, ["0.32", "AIR OUTLET"])


class ByModelRowsTest(unittest.TestCase):
    def test_model_code_need_not_be_the_first_cell(self):
        """원문이 2단이라 왼쪽 단의 다른 표와 한 줄에 온다 — 6모델 중 2개를 놓쳤다."""
        pg = _page([_span(20, 100, "Comp. absorbed power"), _span(120, 100, "0.980"),
                    _span(300, 100, "RTH07L"), _span(360, 100, "1 490"),
                    _span(400, 100, "25"), _span(440, 100, "2 420"),
                    _span(480, 100, "50")])
        got = R.by_model_rows(pg, 4)
        self.assertEqual(got, {"RTH-07L": ["1 490", "25", "2 420", "50"]})

    def test_thousands_gap_is_one_value(self):
        pg = _page([_span(20, 100, "RTH-30K"), _span(100, 100, "27"),
                    _span(109, 100, "000"), _span(200, 100, "12"),
                    _span(209, 100, "300"), _span(300, 100, "27"),
                    _span(309, 100, "500"), _span(400, 100, "10"),
                    _span(409, 100, "900")])
        self.assertEqual(R.by_model_rows(pg, 4),
                         {"RTH-30K": ["27000", "12300", "27500", "10900"]})

    def test_y_range_keeps_two_tables_apart(self):
        """한 쪽에 모델=행 표가 둘이면 아래 표가 위 표를 덮어쓴다(실제로 그랬다)."""
        spans = ([_span(20, 100, "RTH-07K"), _span(100, 100, "6"), _span(109, 100, "900"),
                  _span(200, 100, "3"), _span(209, 100, "600"),
                  _span(300, 100, "8"), _span(309, 100, "000"),
                  _span(400, 100, "2"), _span(409, 100, "800")]
                 + [_span(20, 400, "RTH-07K"), _span(100, 400, "1970"),
                    _span(200, 400, "25"), _span(300, 400, "2"), _span(309, 400, "380"),
                    _span(400, 400, "50")])
        pg = _page(spans)
        self.assertEqual(R.by_model_rows(pg, 4, None, 200)["RTH-07K"][0], "6900")
        self.assertEqual(R.by_model_rows(pg, 4, 300, None)["RTH-07K"][0], "1970")


class PhysicalDataTest(unittest.TestCase):
    def _pg(self):
        # 머리글(y=100) 위에 그림 글자(y=40), 아래에 값 행 둘.
        # 'Power supply' 는 둘째 줄이 라벨 줄 **위**에 온다 — 원문 배치 그대로다.
        return _page([
            _span(210, 40, "AUTO"), _span(260, 40, "0h 2 4 6 8"),
            _span(207, 100, "RTH-07K"), _span(267, 100, "RTH-10K"),
            _span(324, 100, "RTH-15K"),
            _span(25, 130, "Compressor"), _span(81, 130, "Nominal power"),
            _span(176, 130, "kW"), _span(220, 130, "2.7"), _span(277, 130, "3.2"),
            _span(338, 130, "4.7"),
            _span(269, 145, "230.3.50"), _span(329, 145, "230.3.50"),
            _span(391, 145, "230.3.50"),
            _span(81, 149, "Power supply"), _span(158, 149, "V.ph.Hz."),
            _span(210, 149, "230.1.50"),
        ])

    def test_values_land_in_the_right_model_column(self):
        cols = R.model_columns(R.page_lines(self._pg()))
        rows = dict(R.physical_data(self._pg(), cols))
        self.assertEqual(rows["Nominal power kW"], ["2.7", "3.2", "4.7"])

    def test_drawing_text_above_the_header_is_not_read(self):
        cols = R.model_columns(R.page_lines(self._pg()))
        joined = " ".join(v for _l, vs in R.physical_data(self._pg(), cols) for v in vs)
        self.assertNotIn("AUTO", joined)
        self.assertNotIn("0h", joined)

    def test_labelless_line_goes_to_the_nearer_row(self):
        """앞 행이라고 단정하면 전원이 'Nominal power' 에 붙는다."""
        cols = R.model_columns(R.page_lines(self._pg()))
        rows = dict(R.physical_data(self._pg(), cols))
        self.assertNotIn("230.3.50", " ".join(rows["Nominal power kW"]))
        self.assertIn("230.3.50", rows["Power supply V.ph.Hz."][1])

    def test_margin_group_words_are_dropped_not_used(self):
        """묶음 이름은 블록 경계와 y 가 어긋나 쓸 수 없다 — 라벨을 오염시키면 안 된다."""
        cols = R.model_columns(R.page_lines(self._pg()))
        labels = [lab for lab, _v in R.physical_data(self._pg(), cols)]
        self.assertNotIn("Compressor", " ".join(labels))


class UnitLabelTest(unittest.TestCase):
    def test_bare_unit_in_parens_is_recognised(self):
        """일반 어휘에 W·Pa 가 없어 값이 단위 없이 저장됐다."""
        self.assertEqual(datasets.label_unit("Cooling capacity (W)"), "W")
        self.assertEqual(datasets.label_unit("Indoor available pressure (Pa)"), "Pa")

    def test_lookalike_parens_are_not_units(self):
        self.assertFalse(datasets.label_unit("Dimensions with packing"))


class GoldenRecordTest(unittest.TestCase):
    """확정본이 원문 명판과 맞는가 — 다른 쪽에 인쇄된 값과의 대조다(규칙 4)."""

    def setUp(self):
        with open(UNITS, encoding="utf-8") as f:
            self.doc = json.load(f)
        self.by = {u["unitModelNumber"]: u for u in self.doc["units"]}

    def test_twelve_units(self):
        self.assertEqual(len(self.doc["units"]), 12)
        self.assertEqual(set(self.by), set(NAMEPLATE))

    def test_capacities_match_the_nameplate_page(self):
        for code, (cool, heat) in NAMEPLATE.items():
            f = self.by[code]["fields"]
            self.assertEqual(f["grossCoolingCapacity"]["value"], cool, code)
            self.assertEqual(f["heatingCapacity"]["value"], heat, code)

    def test_power_is_stored_in_watts_not_bare(self):
        """단위가 없으면 W 인지 Btu/h 인지 모른다 — 시뮬레이터가 그대로 믿는다."""
        for code in NAMEPLATE:
            f = self.by[code]["fields"]
            for fid in ("grossCoolingCapacity", "heatingCapacity",
                        "systemPower", "heatingInput"):
                self.assertEqual(f[fid]["unit"], "W", "%s.%s" % (code, fid))

    def test_consumption_is_below_capacity(self):
        """히트펌프라 소비전력은 능력보다 작다 — 열이 뒤바뀌면 여기서 걸린다."""
        for code in NAMEPLATE:
            f = self.by[code]["fields"]
            for cap, pwr in (("grossCoolingCapacity", "systemPower"),
                             ("heatingCapacity", "heatingInput")):
                c = float(f[cap]["value"].replace(" ", ""))
                p = float(f[pwr]["value"].replace(" ", ""))
                self.assertLess(p, c, "%s %s" % (code, pwr))


if __name__ == "__main__":
    unittest.main()
