# -*- coding: utf-8 -*-
"""JCI YKN2Open(게이트웨이) 파서 회귀 시험.

여기 있는 시험은 전부 **실제로 밟은 함정**이다. 짐작으로 넣은 것은 없다.
"""
import types
import unittest

import vendor_jci_ykn2open as YK


class _Table:
    def __init__(self, rows):
        self._rows = rows

    def extract(self):
        return self._rows


class _Page:
    def __init__(self, tables):
        self._tables = [_Table(t) for t in tables]

    def find_tables(self):
        return types.SimpleNamespace(tables=self._tables)


class _Document:
    """쪽을 여럿 가진 가짜 문서.

    ⚠ __getitem__ 만 두면 enumerate(doc) 가 끝나지 않는다 — 파서가 쪽을 순회하므로
    IndexError 를 내야 한다.
    """

    def __init__(self, pages):
        self._pages = [_Page(p) for p in pages]
        self.page_count = len(self._pages)

    def __getitem__(self, i):
        return self._pages[i]

    def __len__(self):
        return len(self._pages)

    def close(self):
        pass


MB_HEAD = ["N2Open‐\nType", "N2Ad‐\ndress", "Map Descrip‐\n_\ntor Name\n_",
           "Modbus Ad‐\n_\ndress", "Modbus Scale\n_", "Description",
           "Value / Units", "Range"]
BAC_HEAD = ["Object-name", "Object-type", "Object-type-text", "Object-instance",
            "Description", "State-text-refer‐\nence", "Unit-code", "Value/Units", "Range"]
MB_TITLE = ["Modbus variables", "", "", "", "", "", "", ""]
BAC_TITLE = ["Bacnet variables", "", "", "", "", "", "", "", ""]
# 10·13쪽 게이트웨이 설정표 — 포인트가 아니다
CFG = [["Map Descriptor Name\n_ _", "Data Array Name\n_ _", "Data Array Offset\n_ _",
        "Function", "Node Name\n_", "Address", "Length"],
       ["SMDDI01\n_ _", "DAComm OK\n_ _", "1", "Server", "MBPSrv1\n_ _", "10001", "1"],
       ["SMDDI01\n_ _", "DAComm OK\n_ _", "2", "Server", "MBPSrv2\n_ _", "10001", "1"],
       ["SMDDI01\n_ _", "DAComm OK\n_ _", "3", "Server", "MBPSrv3\n_ _", "10001", "1"]]


def _mb(*cells):
    return list(cells)


class CleanTest(unittest.TestCase):
    def test_wrap_hyphen_is_joined_but_real_hyphens_are_not(self):
        """하이픈이 세 종류다 — 하나로 뭉개면 이름이 오염된다(함정 1)."""
        self.assertEqual(YK.clean("Suction Temper‐\nature 1"), "Suction Temperature 1")
        # U+2011 은 열거 구분자, ASCII '-' 는 이름의 일부 — 둘 다 그대로 둔다
        self.assertEqual(YK.clean("0 ‑ OFF\n1 ‑ ON"), "0 ‑ OFF 1 ‑ ON")
        self.assertEqual(YK.clean("Close-Open"), "Close-Open")

    def test_header_underscore_shards_are_squeezed(self):
        """밑줄 조각이 낱말 **가운데** 박힌다 — 공백만 지우면 못 알아본다.

        이걸 놓쳐서 Modbus 표 37행을 통째로 못 읽고도 BACnet 49점이 나와
        멀쩡해 보였다.
        """
        self.assertEqual(YK.squeeze("Modbus Ad‐\n_\ndress"), "ModbusAddress")
        cmap, unknown = YK.header_map(MB_HEAD, YK.COLMAP_MB)
        self.assertEqual(unknown, {})
        self.assertEqual(cmap["mbAddr"], 3)
        self.assertEqual(YK._headname(cmap, "mapDesc"), "Map Descriptor Name")


class RangeColumnTest(unittest.TestCase):
    """'Range' 열이 세 가지를 담는다(함정 2)."""

    def test_numeric_ranges(self):
        self.assertEqual(YK.range_of("-50 min / 160 max"), {"min": -50.0, "max": 160.0})
        self.assertEqual(YK.range_of("0-100"), {"min": 0.0, "max": 100.0})
        self.assertEqual(YK.range_of("10min 32max"), {"min": 10.0, "max": 32.0})

    def test_enum_is_not_a_range(self):
        self.assertIsNone(YK.range_of("0 ‑ OFF\n1 ‑ Cool"))

    def test_enum_items_may_be_run_together(self):
        """9쪽은 항목을 붙여 쓴다 — '(forced)1 ‑ ON'."""
        self.assertEqual(YK.states_of("0 ‑ OFF (forced)1 ‑ ON. Reset"),
                         [{"code": "0", "label": "OFF (forced)"},
                          {"code": "1", "label": "ON. Reset"}])

    def test_enum_label_may_wrap_mid_word(self):
        """12쪽은 라벨 가운데서 줄을 바꾼다 — 줄바꿈을 경계로 삼으면 통째로 샌다."""
        self.assertEqual(YK.states_of("0 ‑ Fan auto\n1 ‑ Fan manual\ncontinuo"),
                         [{"code": "0", "label": "Fan auto"},
                          {"code": "1", "label": "Fan manual continuo"}])

    def test_plain_range_is_never_read_as_enum(self):
        self.assertEqual(YK.states_of("0-100"), [])
        self.assertEqual(YK.states_of("0-50000"), [])


class ModbusRowTest(unittest.TestCase):
    def setUp(self):
        self.cmap, _ = YK.header_map(MB_HEAD, YK.COLMAP_MB)

    def test_read_scale_is_numeric_but_ambiguous_scale_is_not(self):
        """'/10' 은 방향이 명시적, 'x /10' 은 아니다(함정 6)."""
        r, _ = YK.row_to_point(
            _mb("AI", "1", "CMDAI001 _ _", "30001", "/10", "Suction Temperature 1",
                "°C", "-50 min / 160 max"), self.cmap, "modbus", "x.pdf", 9)
        self.assertEqual(r["blocks"]["modbus"]["scale"], 0.1)
        self.assertEqual(r["blocks"]["modbus"]["scaleRaw"], "/10")
        self.assertEqual(r["blocks"]["modbus"]["refClass"], "input-register")

        w, _ = YK.row_to_point(
            _mb("AO", "2", "CMDAO002 _ _", "40002", "x /10", "Setpoint occupied cool",
                "°C", "10min 32max"), self.cmap, "modbus", "x.pdf", 9)
        self.assertNotIn("scale", w["blocks"]["modbus"])
        self.assertEqual(w["blocks"]["modbus"]["scaleRaw"], "x /10")
        self.assertTrue(any(g.startswith("modbus.scale")
                            for g in w["provenance"]["gaps"]))

    def test_address_base_is_declared_unknown_not_guessed(self):
        r, _ = YK.row_to_point(
            _mb("DO", "1", "CMDDO001", "00001", "N/A", "Fan Mode", "Auto/Manual",
                "0 ‑ Fan auto\n1-Fan manual continuo"), self.cmap, "modbus", "x.pdf", 9)
        self.assertEqual(r["blocks"]["modbus"]["addressBase"], "unknown")
        self.assertEqual(r["blocks"]["modbus"]["refClass"], "coil")

    def test_n2open_type_is_kept_raw_not_forced_into_the_dictionary(self):
        """'AI/AO/DI/DO' 는 point-schema n2.pointType(ADF·ADI·BD)에 없다."""
        r, _ = YK.row_to_point(
            _mb("AI", "31", "CMDAI031", "30027", "/10", "Error Code", "Integer",
                "Alarm code (11 a 46). See alarm table"), self.cmap, "modbus", "x.pdf", 9)
        self.assertEqual(r["blocks"]["n2"], {"address": 31})
        self.assertNotIn("pointType", r["blocks"]["n2"])
        self.assertEqual(r["provenance"]["sourceColumns"]["N2OpenType"], "AI")
        # 참조 문장은 범위도 열거도 아니다 — 비고로 간다
        self.assertEqual(r["common"]["note"], "Alarm code (11 a 46). See alarm table")


class BacnetRowTest(unittest.TestCase):
    def setUp(self):
        self.cmap, _ = YK.header_map(BAC_HEAD, YK.COLMAP_BAC)

    def test_object_type_comes_from_the_numeric_column(self):
        r, _ = YK.row_to_point(
            _mb("Mode", "2", "Analog Value In/ Out", "8", "Mode", "", "95", "Integer",
                "0 ‑ OFF\n1 ‑ Cool\n2 ‑ Heat"), self.cmap, "bacnet", "x.pdf", 11)
        self.assertEqual(r["blocks"]["bacnet"]["objectType"], "AV")
        self.assertEqual(r["blocks"]["bacnet"]["instance"], 8)
        self.assertEqual(len(r["common"]["states"]), 3)

    def test_units_column_may_not_be_a_unit(self):
        """'Integer'·'Auto/Manual' 은 단위가 아니다 — 단위 자리에 올리지 않는다(함정 3)."""
        r, _ = YK.row_to_point(
            _mb("Fan Mode", "5", "Binary Value", "1", "Fan Mode", "4 Close-Open", "",
                "Auto/Manual", "0 ‑ Fan auto\n1 ‑ Fan manual"), self.cmap, "bacnet",
            "x.pdf", 12)
        self.assertEqual(r["common"]["unitSIRaw"], "Auto/Manual")
        self.assertNotIn("unitSI", r["common"])
        self.assertEqual(r["common"]["statesRef"], "4 Close-Open")

    def test_real_units_are_normalised(self):
        r, _ = YK.row_to_point(
            _mb("Indoor Fan Hours", "0", "Analog Input", "29", "Indoor Fan Hours", "",
                "71", "Hours", "0-50000"), self.cmap, "bacnet", "x.pdf", 11)
        self.assertEqual(r["common"]["unitSI"], "h")
        self.assertEqual(r["common"]["rangeSI"], {"min": 0.0, "max": 50000.0})


class ParseDocTest(unittest.TestCase):
    def _doc(self):
        return _Document([
            [CFG],                                   # 1쪽 — 게이트웨이 설정표
            [[MB_TITLE, MB_HEAD,
              _mb("AI", "1", "CMDAI001 _ _", "30001", "/10", "Suction Temper‐\nature 1",
                  "°C", "-50 min / 160 max"),
              _mb("AO", "8", "CMDAO004 _ _", "40004", "x /10", "Mode", "Integer",
                  "0 ‑ OFF\n1 ‑ Cool"),
              _mb("AI", "31", "CMDAI031 _ _", "30027", "/10", "Error Code", "Integer",
                  "Alarm code (11 a 46). See alarm table")]],
            [[BAC_TITLE, BAC_HEAD,
              _mb("Suction Temper‐\nature 1", "0", "Analog Input", "1",
                  "Suction Temper‐\nature 1", "", "62", "°C", "-50 min / 160 max"),
              _mb("Mode", "2", "Analog Value In/ Out", "8", "Mode", "", "95", "Integer",
                  "0 ‑ OFF\n1 ‑ Cool"),
              _mb("Error Code", "0", "Analog Input", "31", "Error Code", "", "95",
                  "Integer", "Alarm code (11 a 46). See alarm table"),
              _mb("Override Mode", "5", "Binary Value", "104", "Override Mode",
                  "6 Open-Close", "", "", "")]],
            [[["Alarms", "", ""], ["Number", "Alarm", "Location"],
              ["11", "Dicharge Temperature 1", "YKN2Open"],
              ["91", "Ambient probe open or short circuited", "Thermostat/Probe"]]],
        ])

    def _parse(self):
        import unittest.mock as mock
        fake = types.SimpleNamespace(open=lambda _p: self._doc())
        with mock.patch.dict("sys.modules", {"fitz": fake}):
            return YK.parse_doc("synthetic.pdf")

    def test_gateway_config_tables_never_become_points(self):
        rows, unknown, _head, skipped = self._parse()
        self.assertEqual(unknown, {})
        self.assertTrue(skipped["gatewayConfig"] >= len(CFG) - 1)
        self.assertNotIn("SMDDI01", [r["common"].get("shortName") for r in rows])

    def test_two_tables_merge_only_when_name_and_number_agree(self):
        """타입 대응표('AO 는 AV 다')를 지어내지 않는다(함정 5)."""
        rows, _u, _h, _s = self._parse()
        by = {r["common"]["name"]: r for r in rows}
        self.assertEqual(len(rows), 4)          # 3 + 4 행이 아니라 합쳐서 4점
        self.assertEqual(sorted(by["Suction Temperature 1"]["blocks"]),
                         ["bacnet", "modbus", "n2"])
        self.assertEqual(sorted(by["Mode"]["blocks"]), ["bacnet", "modbus", "n2"])
        # BACnet 표에만 있는 것은 그대로 BACnet 전용으로 남는다
        self.assertEqual(sorted(by["Override Mode"]["blocks"]), ["bacnet"])

    def test_unpaired_modbus_row_is_flagged_not_silently_merged(self):
        doc = _Document([
            [[MB_TITLE, MB_HEAD,
              _mb("AI", "7", "CMDAI007", "30007", "/10", "Discharge Temperature 2",
                  "°C", "-50 min / 160 max")]],
            [[BAC_TITLE, BAC_HEAD,
              _mb("Discharge Temperature 2", "0", "Analog Input", "99",
                  "Discharge Temperature 2", "", "62", "°C", "-50 min / 160 max")]],
        ])
        import unittest.mock as mock
        fake = types.SimpleNamespace(open=lambda _p: doc)
        with mock.patch.dict("sys.modules", {"fitz": fake}):
            rows, _u, _h, _s = YK.parse_doc("synthetic.pdf")
        self.assertEqual(len(rows), 2)          # 번호가 달라 합치지 않는다
        mb = next(r for r in rows if "modbus" in r["blocks"])
        self.assertTrue(any("짝" in g for g in mb["provenance"]["gaps"]))

    def test_alarm_table_resolves_the_error_code_states(self):
        """'See alarm table' 참조를 풀되 참조 자체는 지우지 않는다(함정 4)."""
        rows, _u, _h, _s = self._parse()
        err = next(r for r in rows if r["common"]["name"] == "Error Code")
        self.assertEqual([s["code"] for s in err["common"]["states"]], ["11", "91"])
        self.assertIn("See alarm table", err["common"]["statesRef"])
        self.assertNotIn("note", err["common"])
        self.assertTrue(any("91~99" in g or "밖의 코드" in g
                            for g in err["provenance"]["gaps"]))

    def test_read_write_is_never_inferred(self):
        rows, _u, _h, _s = self._parse()
        for r in rows:
            self.assertNotIn("readWrite", r["common"])
            self.assertTrue(any(g.startswith("readWrite")
                                for g in r["provenance"]["gaps"]))


if __name__ == "__main__":
    unittest.main()
