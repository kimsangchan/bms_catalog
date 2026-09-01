# -*- coding: utf-8 -*-
"""JCI SC-EQ/Config(통신 카드 설정 포인트) 파서 회귀 시험.

여기 있는 시험은 전부 **실제로 밟은 함정**이다. 짐작으로 넣은 것은 없다.
"""
import os
import re
import types
import unittest

import vendor_jci_sceq_config as SC


class _Table:
    def __init__(self, rows):
        self._rows = rows

    def extract(self):
        return self._rows


class _Page:
    """쪽 하나. `get_text()` 가 있어야 한다 — 이 계통은 표 밖(각주·표제)을 읽는다."""

    def __init__(self, tables, text=""):
        self._tables = [_Table(t) for t in tables]
        self._text = text

    def find_tables(self):
        return types.SimpleNamespace(tables=self._tables)

    def get_text(self):
        return self._text


class _Document:
    """⚠ __getitem__ 만 두면 enumerate(doc) 가 끝나지 않는다 — IndexError 를 내야 한다."""

    def __init__(self, pages):
        self._pages = [_Page(t, x) for t, x in pages]
        self.page_count = len(self._pages)

    def __getitem__(self, i):
        return self._pages[i]

    def __len__(self):
        return len(self._pages)

    def close(self):
        pass


HEAD = ["POINT NAME", "BACNET", "MODBUS", "N2", "DESCRIPTION"]
ROWS = [
    ["BACnet Instance ID Mode", "BV65000", "N/A", "N/A", "0 = Auto 1 = Manual"],
    ["BACnet Instance ID", "AV65000", "N/A", "N/A",
     "Write desired value with Mode set to Manual"],
    ["BACnet Encoding Type", "MV65003", "N/A", "N/A", "0 = ISO(UCS-2), 1 = ASCII"],
    ["BACnet Device Name ", "SV65000", "N/A", "N/A", "Write value desired for BAS system"],
    ["Units", "MV65001", "65001", "ADI 201", "0 = Imperial, 1 = Metric"],
    ["Manual Select Chiller Model\n(YT2 only)", "MV65002", "65002", "ADI 202",
     "See Table 1 below"],
]
P1_TEXT = ("POINT NAME BACNET MODBUS N2 DESCRIPTION … "
           "Note: Modbus addresses 65001 and 65002 are Scaled X1 and Unsigned")
# 원문 2쪽 값 표 — **머리글 행이 없고**(함정 1) 같은 표가 두 벌 나란하다(함정 2).
# 가운데 열은 빈 칸이다. 원문 44종 중 앞뒤만 옮겼다.
VALUE_TABLE = [
    ["None (Disables Manual Select)", "0", "", "YLPA (IP)", "233"],
    ["Generic", "200", "", "YLPA (SI)", "234"],
    ["YVAA Micro Channel (IP)", "201", "", "Millenium YT (SI)", "340"],
]
P2_TEXT = "Table 1 - MANUAL SELECT CHILLER MODELS (YORKTALK 2 ONLY)"


def parse(pages):
    import unittest.mock as mock
    fake = types.SimpleNamespace(open=lambda _p: _Document(pages))
    with mock.patch.dict("sys.modules", {"fitz": fake}):
        return SC.parse_doc("synthetic.pdf")


def si0371():
    return parse([([[HEAD] + ROWS], P1_TEXT), ([VALUE_TABLE], P2_TEXT)])


class ValueTableTest(unittest.TestCase):
    """'Table 1' — 이 저장소에서 처음 만난, **머리글이 없는** 표."""

    def test_first_row_is_data_not_a_header(self):
        """0행을 머리글로 버리면 코드 0(=수동 선택 끄기)이 통째로 사라진다(함정 1)."""
        rows, _u, _h, _s = si0371()
        st = rows[-1]["common"]["states"]
        self.assertEqual(st[0], {"code": "0", "label": "None (Disables Manual Select)"})

    def test_two_side_by_side_copies_are_read_column_wise(self):
        """행 순서로 읽으면 두 벌이 엇갈리고, 왼쪽만 읽으면 절반이 사라진다(함정 2)."""
        rows, _u, _h, _s = si0371()
        codes = [s["code"] for s in rows[-1]["common"]["states"]]
        self.assertEqual(codes, ["0", "200", "201", "233", "234", "340"])
        # 행 순서(0, 233, 200, 234 …)로 읽혔다면 이 단정이 깨진다
        self.assertNotEqual(codes, ["0", "233", "200", "234", "201", "340"])

    def test_value_rows_are_counted_not_silently_dropped(self):
        """값 표의 행은 '포인트가 아닌 행'이다 — 세어서 표면화한다."""
        _r, _u, _h, skipped = si0371()
        self.assertEqual(skipped["modelCodeTable"], len(VALUE_TABLE))

    def test_a_shapewise_lookalike_without_the_caption_is_not_a_value_table(self):
        """모양만으로 고르면 남의 숫자 표가 값 표로 둔갑한다 — 표제가 유일한 근거다."""
        rows, _u, _h, skipped = parse([([[HEAD] + ROWS], P1_TEXT),
                                       ([VALUE_TABLE], "Table 3 - Wire colors")])
        self.assertNotIn("states", rows[-1]["common"])
        self.assertEqual(skipped["modelCodeTable"], 0)
        self.assertTrue(any(g.startswith("states —")
                            for g in rows[-1]["provenance"]["gaps"]))


class FootnoteTest(unittest.TestCase):
    """데이터형·배율이 표 **밖**에 있다 (함정 3)."""

    def test_datatype_comes_from_the_note_outside_the_table(self):
        rows, _u, _h, _s = si0371()
        units = next(r for r in rows if r["common"]["name"] == "Units")
        self.assertEqual(units["blocks"]["modbus"]["dataType"], "Unsigned")
        self.assertEqual(units["blocks"]["modbus"]["scaleRaw"], "X1")

    def test_the_note_only_touches_the_addresses_it_names(self):
        """각주가 주소를 지목한다 — 표 전체에 뿌리면 Modbus 없는 넷에도 붙는다."""
        rows, _u, _h, _s = si0371()
        for r in rows:
            if r["common"]["name"].startswith("BACnet"):
                self.assertNotIn("modbus", r["blocks"])

    def test_scale_is_not_numericised(self):
        """곱·나눗 방향을 문서가 밝히지 않는다 — 같은 계통 vendor_jci_sceq 과 같다."""
        rows, _u, _h, _s = si0371()
        units = next(r for r in rows if r["common"]["name"] == "Units")
        self.assertNotIn("scale", units["blocks"]["modbus"])
        self.assertTrue(any(g.startswith("modbus.scale")
                            for g in units["provenance"]["gaps"]))


class AddressTest(unittest.TestCase):
    def test_mv_becomes_msv_and_sv_survives(self):
        """MV 는 BACnet 표준 표기가 아니고 SV 는 흔치 않다 — 둘 다 버리면 안 된다(함정 4)."""
        rows, _u, _h, _s = si0371()
        by = {r["common"]["name"]: r for r in rows}
        self.assertEqual(by["BACnet Encoding Type"]["blocks"]["bacnet"],
                         {"instance": 65003, "objectType": "MSV"})
        self.assertEqual(by["BACnet Device Name"]["blocks"]["bacnet"],
                         {"instance": 65000, "objectType": "SV"})

    def test_unknown_modbus_band_is_a_gap_not_a_guess(self):
        """65001 은 0/1/3/4xxxx 어디에도 없다 — 앞자리로 종류를 지어내지 않는다(함정 5)."""
        rows, _u, _h, _s = si0371()
        units = next(r for r in rows if r["common"]["name"] == "Units")
        self.assertNotIn("refClass", units["blocks"]["modbus"])
        self.assertEqual(units["blocks"]["modbus"]["addressBase"], "unknown")
        self.assertTrue(any(g.startswith("modbus.refClass")
                            for g in units["provenance"]["gaps"]))

    def test_n2_prefix_and_number_are_split(self):
        rows, _u, _h, _s = si0371()
        units = next(r for r in rows if r["common"]["name"] == "Units")
        self.assertEqual(units["blocks"]["n2"], {"pointType": "ADI", "address": 201})


class DescriptionTest(unittest.TestCase):
    def test_enum_without_a_comma_still_splits(self):
        """SI0371 은 '0 = Auto 1 = Manual' 로 붙여 쓴다 — 쉼표를 경계로 삼으면 못 가른다."""
        self.assertEqual(SC.states_of("0 = Auto 1 = Manual"),
                         [{"code": "0", "label": "Auto"}, {"code": "1", "label": "Manual"}])

    def test_digits_inside_a_label_are_not_boundaries(self):
        """'ISO(UCS-2)' 의 2 를 코드로 읽으면 라벨이 잘린다."""
        self.assertEqual(SC.states_of("0 = ISO(UCS-2), 1 = ASCII"),
                         [{"code": "0", "label": "ISO(UCS-2)"},
                          {"code": "1", "label": "ASCII"}])
        self.assertEqual(SC.states_of("0 = ISO (UCS-2), 1 = ASCII")[0]["label"],
                         "ISO (UCS-2)")

    def test_free_text_never_becomes_states(self):
        self.assertEqual(SC.states_of("Write desired value with Mode set to Manual"), [])
        rows, _u, _h, _s = si0371()
        r = next(x for x in rows if x["common"]["name"] == "BACnet Instance ID")
        self.assertEqual(r["common"]["note"], "Write desired value with Mode set to Manual")
        self.assertNotIn("states", r["common"])

    def test_cell_newline_joins_the_qualifier_not_the_word(self):
        """'Manual Select Chiller Model\\n(YT2 only)' — 붙이면 낱말이 눌러붙는다."""
        rows, _u, _h, _s = si0371()
        self.assertEqual(rows[-1]["common"]["name"],
                         "Manual Select Chiller Model (YT2 only)")


class ReferenceTest(unittest.TestCase):
    """참조를 조용히 비고로 흘리지 않는다 (함정 6·7)."""

    def _other_doc(self):
        # 450.50-N1 46쪽 — 같은 6점인데 값 표가 없고 다른 문서를 가리킨다
        rows = [list(r) for r in ROWS]
        rows[-1][-1] = "Refer to SI0371."
        head = ["Point name", "BACnet", "Modbus", "N2", "Description"]
        return parse([([[head] + rows],
                       "… Note: Modbus addresses 65001 and 65002 are Scaled X1 and "
                       "Unsigned.")])

    def test_unresolvable_cross_document_reference_is_kept_and_flagged(self):
        rows, _u, _h, _s = self._other_doc()
        r = rows[-1]
        self.assertEqual(r["common"]["statesRef"], "Refer to SI0371.")
        self.assertNotIn("states", r["common"])
        self.assertNotIn("note", r["common"])          # 비고로 새면 안 된다
        self.assertTrue(any(g.startswith("states —") for g in r["provenance"]["gaps"]))

    def test_resolved_reference_keeps_the_reference(self):
        rows, _u, _h, _s = si0371()
        self.assertEqual(rows[-1]["common"]["statesRef"], "See Table 1 below")
        self.assertIn("states", rows[-1]["common"])

    def test_msv_offset_is_never_invented(self):
        """SC-EQ 코드표의 'add 1 to number' 노트가 이 문서엔 없다 — 1 로 지어내면
        44종 기종 선택이 통째로 한 칸 밀린다."""
        rows, _u, _h, _s = si0371()
        self.assertNotIn("msvOffset", rows[-1]["blocks"]["bacnet"])
        self.assertTrue(any(g.startswith("bacnet.msvOffset")
                            for g in rows[-1]["provenance"]["gaps"]))

    def test_read_write_is_never_inferred(self):
        rows, _u, _h, _s = si0371()
        for r in rows:
            self.assertNotIn("readWrite", r["common"])
            self.assertTrue(any(g.startswith("readWrite") for g in r["provenance"]["gaps"]))


class HeaderMarkTest(unittest.TestCase):
    """계통 표식은 **표 머리글의 다섯 낱말 전체**다."""

    def _route_pat(self):
        import ingest_jci as G
        return next(p for fam, _m, p in G.ROUTES if fam == "SC-EQ/Config")

    def test_mark_needs_the_whole_sequence(self):
        pat = self._route_pat()
        self.assertTrue(re.search(pat, " | ".join(HEAD), re.I))
        self.assertTrue(re.search(pat, "Point name | BACnet | Modbus | N2 | Description",
                                  re.I))
        # 'Point name' 하나만으로 잡으면 이런 표가 남의 계통에서 걸린다
        self.assertFalse(re.search(pat, "Point name | Description | Notes", re.I))
        self.assertFalse(re.search(pat, "Long Name | Short Name | BACnet | Modbus | N2",
                                   re.I))

    def test_a_table_missing_a_column_is_not_this_family(self):
        self.assertTrue(SC.is_point_head(HEAD))
        self.assertFalse(SC.is_point_head(["Point name", "BACnet", "Description"]))
        self.assertFalse(SC.is_point_head(["Long Name", "BACnet", "Modbus", "N2"]))


HERE = os.path.dirname(os.path.abspath(__file__))
SI0371 = os.path.join(HERE, "data", "raw", "JCI_SC-EQ-Firmware-3.0.0.1114-SI0371.pdf")
# 짝 문서는 대장에 없다(판으로 삼지 않았다) — 전수 스캔본에서만 온다
# ⚠ 스캔 임시 폴더(_scan_jci)를 가리키면 안 된다 — scan_jci 가 안 걸린 원문을
#   지우므로 재훑기 한 번에 사라지고 이 시험이 조용히 skip 이 된다(실제로 그랬다).
#   소스 jci-corroboration 으로 등록했으니 collect.py --run 으로 재현된다.
N1 = os.path.join(HERE, "data", "raw", "JCI_SC-EQ-Card-Install-450.50-N1.pdf")


class RealDocumentTest(unittest.TestCase):
    """원문 두 건이 **정말 같은 6점**인지. 판을 하나만 세운 근거가 이것이다.

    원문은 저장소에 없다(data/raw 는 gitignore) — 없으면 건너뛴다.
    """

    def _key(self, path):
        rows, unk, _h, _s = SC.parse_doc(path)
        self.assertEqual(unk, {}, "못 알아본 열이 있으면 표가 바뀐 것이다")
        return [(r["common"]["name"], r["blocks"].get("bacnet"),
                 (r["blocks"].get("modbus") or {}).get("address"),
                 r["blocks"].get("n2")) for r in rows]

    def test_both_documents_carry_the_same_six_points(self):
        for p in (SI0371, N1):
            if not os.path.exists(p):
                self.skipTest("원문 없음: %s" % os.path.basename(p))
        a, b = self._key(SI0371), self._key(N1)
        self.assertEqual(len(a), 6)
        self.assertEqual(a, b)

    def test_si0371_resolves_all_44_chiller_models(self):
        if not os.path.exists(SI0371):
            self.skipTest("원문 없음")
        rows, _u, _h, _s = SC.parse_doc(SI0371)
        st = rows[-1]["common"]["states"]
        self.assertEqual(len(st), 44)
        self.assertEqual(st[0]["code"], "0")
        self.assertEqual(st[-1], {"code": "340", "label": "Millenium YT (SI)"})
        # 코드가 오름차순이면 두 벌을 세로로 제대로 읽은 것이다(엇갈리면 깨진다)
        self.assertEqual([int(s["code"]) for s in st],
                         sorted(int(s["code"]) for s in st))


if __name__ == "__main__":
    unittest.main()
