# -*- coding: utf-8 -*-
"""AYK550 4xxxx 고정 레지스터 창 어댑터 시험.

왜 시험이 필요한가
  레지스터 번호를 그대로 주소로 쓰면 **한 칸 어긋난다.** 원문이 못 박는다 —
  "Holding register 40002 is addressed as 0001 in a Modbus message." 40000 을 빼는
  흔한 실수를 하면 전 포인트가 1 씩 밀린 채로 게이트를 통과한다(주소는 정수라 검사에
  안 걸린다). 그리고 이 표는 자료형을 **일부 구간에만** 밝히는데, 앞선 YKH 표의
  'Signed' 를 베껴 전 레지스터에 붙이면 없는 사실을 지어내는 것이다.

  미끼는 전부 실측이다(JCI_AIR_AYK550-fln.pdf, PDF 162~163쪽).
"""
import unittest

import vendor_jci_ayk_modbus as M


def parse(*rows):
    return M.parse_rows([(162, list(r)) for r in rows], "JCI_AIR_AYK550-fln.pdf")


CTRL = ["40001", "CONTROL WORD", "R/W",
        "Supported only if the drive is configured to use the YORK Drives Profile (5305 = 0)."]
ACT1 = ["40005", "Actual 1 (select using 5310)", "R",
        "By default, stores a copy of 0103 OUTPUT FREQ."]
LSW = ["40031", "AYK550 CONTROL WORD LSW", "R/W", "Maps directly to the LSW."]


class TableSelection(unittest.TestCase):

    def test_this_manuals_modbus_header_is_recognised(self):
        self.assertTrue(M.is_point_table(
            "Modbus Register | AYK550 Standard Profile (YORK DRIVES) | Access | Remarks"))

    def test_the_fln_point_table_in_the_same_manual_is_rejected(self):
        # 같은 문서의 9열 FLN 목록은 다른 어댑터 몫이다
        self.assertFalse(M.is_point_table(
            "Point | | Subpoint Name | Factory Default | Engr. Units | Slope | "
            "Intercept | On Text | Off Text"))

    def test_the_report_table_is_rejected(self):
        self.assertFalse(M.is_point_table("Point | | Subpoint Name | Data"))


class Addressing(unittest.TestCase):

    def test_wire_address_is_register_minus_40001(self):
        # 원문: "Holding register 40002 is addressed as 0001 in a Modbus message."
        pts, _ = parse(["40002", "Reference 1", "R/W", ""])
        self.assertEqual(pts[0]["blocks"]["modbus"]["address"], 1)

    def test_first_register_is_address_zero_not_one(self):
        # 40000 을 빼면 40001 이 1 이 되어 전 포인트가 한 칸 밀린다
        pts, _ = parse(CTRL)
        self.assertEqual(pts[0]["blocks"]["modbus"]["address"], 0)

    def test_address_base_is_declared(self):
        # 사전이 addressBase 동반을 의무화한다 — 없으면 0/1 base 를 알 수 없다
        pts, _ = parse(CTRL)
        self.assertEqual(pts[0]["blocks"]["modbus"]["addressBase"], "0")

    def test_raw_register_number_is_kept(self):
        pts, _ = parse(CTRL)
        self.assertEqual(
            pts[0]["provenance"]["sourceColumns"]["Modbus Register"], "40001")

    def test_holding_register_class_from_function_codes(self):
        # 원문 기능코드 표: "03 Read holding 4xxxx registers"
        pts, _ = parse(CTRL)
        self.assertEqual(pts[0]["blocks"]["modbus"]["refClass"], "holding-register")


class DataType(unittest.TestCase):
    """자료형은 원문이 밝힌 구간에만 붙인다."""

    def test_actual_values_are_signed(self):
        # 40005…40012 만 "a sign bit and a 15-bit integer" 라고 원문이 밝힌다
        pts, _ = parse(ACT1)
        self.assertEqual(pts[0]["blocks"]["modbus"]["dataType"], "Signed")

    def test_other_registers_have_no_declared_type(self):
        # 앞선 YKH 표의 'Signed' 를 베껴 오면 안 된다 — 이 문서는 안 밝힌다
        pts, _ = parse(CTRL)
        self.assertNotIn("dataType", pts[0]["blocks"]["modbus"])
        self.assertIn("blocks.modbus.dataType", pts[0]["provenance"]["gaps"])

    def test_profile_word_registers_are_untyped_too(self):
        pts, _ = parse(LSW)
        self.assertNotIn("dataType", pts[0]["blocks"]["modbus"])


class AccessColumn(unittest.TestCase):
    """이 표는 앞 표들이 못 주던 readWrite 를 준다."""

    def test_read_write_is_captured(self):
        pts, _ = parse(CTRL)
        self.assertEqual(pts[0]["common"]["readWrite"], "R/W")

    def test_read_only_is_captured(self):
        pts, _ = parse(ACT1)
        self.assertEqual(pts[0]["common"]["readWrite"], "R")

    def test_remarks_are_preserved_as_note(self):
        # 프로파일 조건이 여기 들어 있다 — 버리면 언제 유효한 점인지 모른다
        pts, _ = parse(CTRL)
        self.assertIn("YORK Drives Profile", pts[0]["common"]["note"])


class Rows(unittest.TestCase):

    def test_repeated_header_row_is_counted_not_dropped_silently(self):
        pts, skipped = parse(["Modbus Register", "AYK550 Standard Profile", "Access",
                              "Remarks"], CTRL)
        self.assertEqual(len(pts), 1)
        self.assertTrue(skipped)

    def test_page_break_duplicate_is_dropped(self):
        pts, skipped = parse(CTRL, CTRL)
        self.assertEqual(len(pts), 1)
        self.assertIn("쪽 넘김 중복", skipped)

    def test_same_register_different_name_is_surfaced(self):
        other = ["40001", "SOMETHING ELSE", "R", ""]
        pts, skipped = parse(CTRL, other)
        self.assertEqual(len(pts), 1)
        self.assertIn("같은 레지스터 다른 이름", skipped)

    def test_non_register_rows_are_skipped(self):
        pts, skipped = parse(["0103", "OUTPUT FREQ", "R", ""])
        self.assertEqual(pts, [])
        self.assertTrue(skipped)

    def test_points_are_sorted_by_address(self):
        pts, _ = parse(LSW, CTRL, ACT1)
        self.assertEqual([p["blocks"]["modbus"]["address"] for p in pts], [0, 4, 30])

    def test_family_is_recorded(self):
        pts, _ = parse(CTRL)
        self.assertEqual(pts[0]["provenance"]["family"], "Drive/Modbus")


if __name__ == "__main__":
    unittest.main()
