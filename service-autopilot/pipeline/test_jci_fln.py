# -*- coding: utf-8 -*-
"""APOGEE P1/FLN 어댑터 시험.

왜 시험이 필요한가
  이 매뉴얼 한 권에 우리 표식에 걸리는 표가 **셋** 있다 — 9열 포인트 목록,
  4열 리포트 7종, 그리고 같은 문서의 Modbus 4xxxx 표. 리포트를 포인트로 세면
  같은 것을 두 번 센다(고유 번호 85개가 전부 9열 목록 안에 있다). 그리고 원문이
  Type 코드 풀이도, On/Off Text 의 코드 대응도, slope 변환 방향도 주지 않는다 —
  없는 것을 채우기 시작하면 시뮬레이터가 그대로 믿는다.

  미끼는 전부 실측이다(AYK550-UH 1-400 HP 판, 인쇄 176~183쪽).
"""
import unittest

import vendor_jci_fln as F


def parse(*rows):
    return F.parse_rows([(180, list(r)) for r in rows], "JCI_AIR_AYK550-fln.pdf")


ROW_ANALOG = ["{03}", "LAI", "FREQ OUTPUT", "0", "Hz", "0.1", "0", "-", "-"]
ROW_DIGITAL = ["{21}", "LDI", "FWD.REV", "FWD", "-", "1", "0", "REV", "FWD"]
ROW_PLAIN = ["01", "LAO", "CTLR ADDRESS", "99", "-", "1", "0", "-", "-"]


class TableSelection(unittest.TestCase):

    def test_nine_column_point_table_is_recognised(self):
        self.assertTrue(F.is_point_table(
            "Point | | Subpoint Name | Factory Default | Engr. Units | Slope | "
            "Intercept | On Text | Off Text"))

    def test_four_column_report_table_is_rejected(self):
        # 리포트는 목록의 부분집합이다 — 포인트로 세면 두 번 센다
        self.assertFalse(F.is_point_table("Point | | Subpoint Name | Data"))

    def test_modbus_table_in_the_same_manual_is_rejected(self):
        # 같은 문서 p162~164 는 Modbus 표다 — 계통이 다르다
        self.assertFalse(F.is_point_table(
            "Modbus Register | AYK550 Standard Profile | Access | Remarks"))

    def test_repeated_header_rows_are_counted_not_silently_dropped(self):
        pts, skipped = parse(["#", "Type", "", "", "", "", "", "", ""], ROW_PLAIN)
        self.assertEqual(len(pts), 1)
        self.assertTrue(skipped)


class Addressing(unittest.TestCase):

    def test_point_number_is_the_address(self):
        pts, _ = parse(ROW_PLAIN)
        self.assertEqual(pts[0]["blocks"]["fln"]["address"], 1)

    def test_braces_mean_unbundlable_at_the_field_panel(self):
        # 원문 각주 c: "Point numbers that appear in brackets { } may be unbundled
        # at the field panel." 표기를 bool 로만 보존하고 해석은 섞지 않는다.
        pts, _ = parse(ROW_ANALOG, ROW_PLAIN)
        by = {p["blocks"]["fln"]["address"]: p for p in pts}
        self.assertTrue(by[3]["blocks"]["fln"]["unbundlable"])
        self.assertFalse(by[1]["blocks"]["fln"]["unbundlable"])

    def test_raw_point_number_is_kept(self):
        pts, _ = parse(ROW_ANALOG)
        self.assertEqual(pts[0]["provenance"]["sourceColumns"]["Point #"], "{03}")

    def test_duplicate_point_numbers_from_page_breaks_are_dropped(self):
        pts, skipped = parse(ROW_PLAIN, ROW_PLAIN)
        self.assertEqual(len(pts), 1)
        self.assertIn("쪽 넘김 중복", skipped)

    def test_same_number_different_name_is_surfaced_not_hidden(self):
        other = ["01", "LAO", "SOMETHING ELSE", "0", "-", "1", "0", "-", "-"]
        pts, skipped = parse(ROW_PLAIN, other)
        self.assertEqual(len(pts), 1)
        self.assertIn("같은 번호 다른 이름", skipped)


class Scaling(unittest.TestCase):

    def test_dual_unit_slope_keeps_si_and_raw(self):
        # 각주 b — 값이 둘이면 영국단위(SI) 병기다
        row = ["{60}", "LAI", "REF SCALE", "77 (25)", "° F (° C)", "0.18 (0.1)", "32 (0)",
               "-", "-"]
        pts, _ = parse(row)
        fln = pts[0]["blocks"]["fln"]
        self.assertEqual(fln["slope"], 0.1)
        self.assertEqual(fln["slopeRaw"], "0.18 (0.1)")
        self.assertEqual(fln["intercept"], 0)

    def test_parentheses_lost_in_extraction_are_still_read(self):
        # 추출본에 괄호가 떨어진 변형이 실제로 온다
        row = ["{61}", "LAI", "REF SCALE 2", "0", "PCT", "0.134 0.1", "32 0", "-", "-"]
        pts, _ = parse(row)
        self.assertEqual(pts[0]["blocks"]["fln"]["slope"], 0.1)

    def test_dual_units_split_into_ip_and_si(self):
        row = ["{62}", "LAI", "TEMP", "0", "° F (° C)", "1", "0", "-", "-"]
        pts, _ = parse(row)
        self.assertEqual(pts[0]["common"]["unitIP"], "° F")
        self.assertEqual(pts[0]["common"]["unitSI"], "° C")

    def test_single_unit_means_same_in_both_systems(self):
        pts, _ = parse(ROW_ANALOG)
        self.assertEqual(pts[0]["common"]["unitIP"], "Hz")
        self.assertEqual(pts[0]["common"]["unitSI"], "Hz")

    def test_empty_intercept_is_left_empty_not_zeroed(self):
        # 원문부터 빈 칸인 포인트가 있다 — 0 으로 채우면 없는 값을 지어내는 것이다
        row = ["02", "LAO", "APPLICATION", "2734", "-", "1", "", "-", "-"]
        pts, _ = parse(row)
        self.assertNotIn("intercept", pts[0]["blocks"]["fln"])
        self.assertIn("blocks.fln.intercept", pts[0]["provenance"]["gaps"])


class UnstatedThings(unittest.TestCase):
    """원문이 안 밝히는 것을 채우지 않는다."""

    def test_on_off_text_is_preserved_but_not_turned_into_states(self):
        # 글자는 주는데 **어느 코드가 ON 인지** 원문이 안 준다
        pts, _ = parse(ROW_DIGITAL)
        fln = pts[0]["blocks"]["fln"]
        self.assertEqual(fln["onText"], "REV")
        self.assertEqual(fln["offText"], "FWD")
        self.assertNotIn("states", pts[0]["common"])
        self.assertIn("common.states", pts[0]["provenance"]["gaps"])

    def test_read_write_is_a_gap(self):
        pts, _ = parse(ROW_ANALOG)
        self.assertIn("common.readWrite", pts[0]["provenance"]["gaps"])

    def test_point_type_code_is_kept_verbatim(self):
        # 'Logical Analog Input' 같은 풀이는 문서에 없다 — 코드만 남긴다
        pts, _ = parse(ROW_ANALOG)
        self.assertEqual(pts[0]["blocks"]["fln"]["pointType"], "LAI")

    def test_unknown_type_codes_are_skipped_not_invented(self):
        row = ["05", "XYZ", "MYSTERY", "0", "-", "1", "0", "-", "-"]
        pts, skipped = parse(row)
        self.assertEqual(pts, [])
        self.assertTrue(skipped)

    def test_dash_cells_do_not_become_values(self):
        pts, _ = parse(ROW_PLAIN)
        fln = pts[0]["blocks"]["fln"]
        self.assertNotIn("onText", fln)
        self.assertNotIn("unitIP", pts[0]["common"])


class Provenance(unittest.TestCase):

    def test_family_and_page_are_recorded(self):
        pts, _ = parse(ROW_ANALOG)
        pv = pts[0]["provenance"]
        self.assertEqual(pv["family"], "APOGEE/FLN")
        self.assertEqual(pv["sourcePage"], 180)
        self.assertEqual(pv["status"], "extracted")

    def test_points_come_out_sorted_by_number(self):
        pts, _ = parse(ROW_DIGITAL, ROW_PLAIN, ROW_ANALOG)
        self.assertEqual([p["blocks"]["fln"]["address"] for p in pts], [1, 3, 21])


if __name__ == "__main__":
    unittest.main()
