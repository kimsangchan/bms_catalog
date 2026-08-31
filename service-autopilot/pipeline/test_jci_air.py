# -*- coding: utf-8 -*-
"""JCI 공조기 Modbus 레지스터 어댑터 시험.

왜 시험이 필요한가
  이 표는 열이 다섯인데 **둘이 다 주소처럼 생겼다**(PLC register 40001 · Parameter
  number 0). 어느 쪽을 주소로 쓸지 틀리면 통신 설정이 통째로 어긋난다. 그리고
  Range 는 공학값이 아니라 배율이 걸린 raw 다 — 그걸 범위로 올리면 시뮬레이터가
  28ºC 를 280 으로 믿는다. 그 두 가지를 여기서 못 박는다.

  미끼는 전부 실측이다(JCI_AIR_YKL-lowprofile-ahu.pdf p27~35).
"""
import unittest

import vendor_jci_air as A


def parse(*rows):
    pts, skipped = A.parse_doc("JCI_AIR_x.pdf", [(27, list(r)) for r in rows], None)
    return pts, skipped


class Address(unittest.TestCase):

    def test_parameter_number_is_the_address(self):
        # PLC register 는 40001 부터의 표기이고 실제 주소는 0-base 파라미터 번호다
        pts, _ = parse(["40001", "0", "Unit open and close variable", "0, 1", "0: Off 1: On"])
        mb = pts[0]["blocks"]["modbus"]
        self.assertEqual(mb["address"], 0)
        self.assertEqual(mb["addressBase"], "0")

    def test_raw_register_is_kept(self):
        pts, _ = parse(["40009", "8", "Unit supply air temperature value", "-400 to 999", ""])
        src = pts[0]["provenance"]["sourceColumns"]
        self.assertEqual(src["PLC register Address"], "40009")
        self.assertEqual(pts[0]["blocks"]["modbus"]["address"], 8)

    def test_mismatched_columns_are_flagged_not_guessed(self):
        # 40001 ↔ 5 는 어느 쪽이 주소인지 알 수 없다 — 짐작하지 않고 gap 에 남긴다
        pts, _ = parse(["40001", "5", "Something", "", ""])
        self.assertIn("blocks.modbus.address", pts[0]["provenance"]["gaps"])

    def test_document_stated_register_class_and_type(self):
        # 표 위 문장이 "holding register and signed integer 16" 이라고 밝힌다
        pts, _ = parse(["40002", "1", "Unit set temperature", "0 to 999", ""])
        mb = pts[0]["blocks"]["modbus"]
        self.assertEqual(mb["refClass"], "holding-register")
        self.assertEqual(mb["dataType"], "Signed")


class Ranges(unittest.TestCase):

    def test_scaled_range_is_not_promoted_to_engineering_units(self):
        # '0 to 999' 에서 280 이 28ºC 다 — 범위로 올리면 시뮬레이터가 raw 를 믿는다
        pts, _ = parse(["40002", "1", "Unit set temperature", "0 to 999",
                        "The value includes a decimal place."])
        self.assertNotIn("rangeSI", pts[0]["common"])
        self.assertIn("common.rangeSI", pts[0]["provenance"]["gaps"])

    def test_read_write_is_a_gap_because_the_table_omits_it(self):
        pts, _ = parse(["40010", "9", "Outside temperature value", "-400 to 999", ""])
        self.assertNotIn("readWrite", pts[0]["common"])
        self.assertIn("common.readWrite", pts[0]["provenance"]["gaps"])


class States(unittest.TestCase):

    def test_binary_codes_become_states(self):
        pts, _ = parse(["40001", "0", "Unit open and close variable", "0, 1", "0: Off 1: On"])
        self.assertEqual(pts[0]["common"]["states"],
                         [{"code": "0", "label": "Off"}, {"code": "1", "label": "On"}])

    def test_range_codes_also_become_states_when_all_are_explained(self):
        # '0 to 5' 도 코드 목록이다 — 쉼표형만 보면 모드 값을 통째로 놓친다
        pts, _ = parse(["40003", "2", "Unit air conditioning mode", "0 to 5",
                        "0: Fan mode 1: Manual heating 2: Manual cooling "
                        "3: Auto heating 4: Auto cooling 5: Full automatic mode"])
        st = pts[0]["common"]["states"]
        self.assertEqual(len(st), 6)
        self.assertEqual(st[0], {"code": "0", "label": "Fan mode"})
        self.assertEqual(st[5]["label"], "Full automatic mode")

    def test_partly_explained_codes_make_no_states(self):
        # 1 만 풀린 열거는 만들지 않는다 — 반쯤 채운 상태표는 없느니만 못하다
        pts, _ = parse(["40015", "14", "BMS input", "0, 1", "1: The unit is off."])
        self.assertNotIn("states", pts[0]["common"])

    def test_wide_numeric_range_is_never_an_enumeration(self):
        # 온도값 -400~999 를 1,400개 상태로 펼치면 안 된다
        pts, _ = parse(["40010", "9", "Outside temperature value", "-400 to 999", ""])
        self.assertNotIn("states", pts[0]["common"])


class Rows(unittest.TestCase):

    def test_short_rows_are_counted_not_silently_dropped(self):
        pts, skipped = parse(["40001", "0"])
        self.assertEqual(pts, [])
        self.assertTrue(skipped)

    def test_rows_without_a_parameter_number_are_skipped(self):
        pts, skipped = parse(["", "", "Modbus parameter list", "", ""])
        self.assertEqual(pts, [])
        self.assertTrue(skipped)

    def test_provenance_carries_page_and_family(self):
        pts, _ = parse(["40001", "0", "Unit open and close variable", "0, 1", "0: Off 1: On"])
        pv = pts[0]["provenance"]
        self.assertEqual(pv["sourcePage"], 27)
        self.assertEqual(pv["family"], A.FAMILY)
        self.assertEqual(pv["status"], "extracted")


if __name__ == "__main__":
    unittest.main()
