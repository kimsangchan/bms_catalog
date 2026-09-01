# -*- coding: utf-8 -*-
"""Verasys VEC100 SBH 메뉴 항목 어댑터 시험.

왜 시험이 필요한가
  이 표는 앞선 계통들과 성격이 다르다 — **주소 열이 없다.** 그리고 표가 메뉴별 소표
  43~47개로 쪼개져 실려서 **캡션의 메뉴 경로가 행 정체성의 절반**이다. 이름만으로
  합치면 서로 다른 오브젝트가 뭉개진다(PID 파라미터가 세 메뉴에 설명 글자까지 같게
  실린다). 마지막으로 'Enum set or range' 한 열에 상태표·범위·단위 세 가지가 섞여
  있어 통째로 states 로 밀면 범위가 상태로 둔갑한다.

  미끼는 전부 실측이다(JCI_VEC100_*.pdf).
"""
import unittest

import vendor_jci_vec100 as V


def parse(*rows, menu="Status"):
    return V.parse_rows([(23, menu, list(r)) for r in rows], "JCI_VEC100_x.pdf")


STATUS = ["Unit Status", "Shows the status of the unit.", "Read Only", "",
          "0 = Idle 1 = SD Alarm 2 = Purge Command"]
SETPT = ["Occupied Cooling Setpoint", "Sets the cooling setpoint.", "Adjustable",
         "74°F (23°C)", "40°F to 80°F (4°C to 27°C)"]
ANALOG = ["Supply Air Temperature", "Shows the supply air temperature.", "Read Only",
          "", "°F (°C)"]


class TableSelection(unittest.TestCase):

    def test_menu_table_is_recognised(self):
        self.assertTrue(V.is_point_table(
            "Object or parameter | Description | Adjustable | Defaults | "
            "Enum set or range"))

    def test_other_families_are_rejected(self):
        self.assertFalse(V.is_point_table(
            "PLC register Address | Parameter number | Name | Range | Details"))
        self.assertFalse(V.is_point_table("Modbus Register | Access | Remarks"))


class MenuPath(unittest.TestCase):
    """메뉴 경로가 행 정체성의 절반이다."""

    def test_caption_becomes_the_menu_path(self):
        self.assertEqual(V.menu_of("Table 27: Details : Setup menu"), "Details : Setup")
        self.assertEqual(V.menu_of("Table 13: Status menu"), "Status")

    def test_caption_without_a_path_is_empty(self):
        self.assertEqual(V.menu_of("표가 아닌 줄"), "")

    def test_menu_path_is_stored_on_the_point(self):
        pts, _ = parse(STATUS, menu="Details : Setup")
        self.assertEqual(pts[0]["common"]["group"], "Details : Setup")

    def test_same_name_in_two_menus_is_two_points(self):
        # PID 파라미터가 세 메뉴에 설명까지 같게 실린다 — 이름으로 합치면 뭉개진다
        a, _ = V.parse_rows([(1, "Heating PID Data", list(SETPT)),
                             (2, "Cooling PID Data", list(SETPT))], "x.pdf")
        self.assertEqual(len(a), 2)

    def test_same_name_same_menu_is_a_page_break_duplicate(self):
        pts, skipped = parse(STATUS, STATUS)
        self.assertEqual(len(pts), 1)
        self.assertIn("쪽 넘김 중복", skipped)


class NoAddress(unittest.TestCase):
    """주소가 없다 — 없는 것을 만들지 않는다."""

    def test_no_protocol_block_is_invented(self):
        pts, _ = parse(STATUS)
        self.assertEqual(pts[0]["blocks"], {})

    def test_absence_is_recorded_as_a_gap(self):
        pts, _ = parse(STATUS)
        self.assertIn("blocks", pts[0]["provenance"]["gaps"])


class EnumRangeUnit(unittest.TestCase):
    """한 열에 섞인 세 가지를 갈라 담는다."""

    def test_state_table_becomes_states(self):
        pts, _ = parse(STATUS)
        st = pts[0]["common"]["states"]
        self.assertEqual(st[0], {"code": "0", "label": "Idle"})
        self.assertEqual(len(st), 3)

    def test_enum_not_starting_at_zero_is_read(self):
        # '3 = Nickel 4 = Platinum' 같은 것이 실제로 있다
        row = ["Sensor Type", "Sets the sensor type.", "Adjustable", "Nickel",
               "3 = Nickel 4 = Platinum"]
        pts, _ = parse(row)
        self.assertEqual([s["label"] for s in pts[0]["common"]["states"]],
                         ["Nickel", "Platinum"])

    def test_range_becomes_a_range_not_states(self):
        pts, _ = parse(SETPT)
        c = pts[0]["common"]
        self.assertNotIn("states", c)
        self.assertEqual(c["rangeSI"], {"min": 40.0, "max": 80.0})

    def test_unit_only_cell_becomes_a_unit(self):
        pts, _ = parse(ANALOG)
        c = pts[0]["common"]
        self.assertNotIn("states", c)
        self.assertEqual(c["unitSI"], "°F (°C)")

    def test_blank_cell_makes_nothing(self):
        row = ["Something", "desc", "Adjustable", "", ""]
        pts, _ = parse(row)
        c = pts[0]["common"]
        self.assertNotIn("states", c)
        self.assertNotIn("rangeSI", c)
        self.assertNotIn("unitSI", c)


class Rows(unittest.TestCase):

    def test_adjustable_and_read_only_map_to_read_write(self):
        pts, _ = parse(SETPT, STATUS)
        by = {p["common"]["name"]: p["common"]["readWrite"] for p in pts}
        self.assertEqual(by["Occupied Cooling Setpoint"], "R/W")
        self.assertEqual(by["Unit Status"], "R")

    def test_header_rows_are_counted_not_dropped_silently(self):
        head = ["Object or parameter", "Description", "Adjustable", "Defaults",
                "Enum set or range"]
        pts, skipped = parse(head, STATUS)
        self.assertEqual(len(pts), 1)
        self.assertTrue(skipped)

    def test_a_point_really_named_description_survives(self):
        # 이름이 'Description' 인 **진짜 포인트**가 있다 — Controller : Network 메뉴의
        # 장치 설명 필드다. 이름 하나로 머리글을 걸러내면 이것까지 버린다.
        row = ["Description",
               "The description of the device. This description appears on the "
               "device list.", "Adjustable", "", "30 characters maximum"]
        pts, _ = parse(row, menu="Controller : Network")
        self.assertEqual(len(pts), 1)
        self.assertEqual(pts[0]["common"]["name"], "Description")

    def test_rows_without_a_readwrite_cell_are_skipped(self):
        pts, skipped = parse(["Note", "이건 설명 문단이다", "", "", ""])
        self.assertEqual(pts, [])
        self.assertTrue(skipped)

    def test_raw_columns_are_preserved(self):
        pts, _ = parse(SETPT)
        src = pts[0]["provenance"]["sourceColumns"]
        self.assertEqual(src["Defaults"], "74°F (23°C)")
        self.assertEqual(src["Adjustable"], "Adjustable")

    def test_family_is_recorded(self):
        pts, _ = parse(STATUS)
        self.assertEqual(pts[0]["provenance"]["family"], "Verasys/Menu")


if __name__ == "__main__":
    unittest.main()
