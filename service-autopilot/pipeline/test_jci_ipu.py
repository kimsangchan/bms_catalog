# -*- coding: utf-8 -*-
"""JCI IOM 본문형 포인트 파서·취입 회귀 시험."""
import io
import json
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

import ingest_jci
import points
import vendor_jci_ipu as IPU


class _Table:
    def __init__(self, rows):
        self._rows = rows

    def extract(self):
        return self._rows


class _Page:
    def __init__(self, rows):
        self._rows = rows

    def find_tables(self):
        return types.SimpleNamespace(tables=[_Table(self._rows)])


class _Document:
    def __init__(self, rows):
        self._page = _Page(rows)
        self.page_count = 1

    def __getitem__(self, _index):
        return self._page

    def close(self):
        pass


class IpuParserTest(unittest.TestCase):
    def test_unlabelled_unit_codes_stay_raw_not_states(self):
        values = ["FAN-ST", "Supply Fan Status", "R", "BI01", "514", "0, 1"]
        cmap = {"objName": 0, "uiName": 1, "rw": 2, "obj": 3,
                "modbus": 4, "unit": 5}

        point, why = IPU.row_to_point(values, cmap, "synthetic.pdf", 1)

        self.assertIsNone(why)
        self.assertNotIn("states", point["common"])
        self.assertEqual(point["provenance"]["sourceColumns"]["ENG UNITS"], "0, 1")

    def test_continuations_follow_the_source_column(self):
        table = [
            ["BACnet NAME", "USER INTERFACE NAME", "READ/WRITE",
             "OBJECT TYPE AND INSTANCE", "MODBUS REGISTER ADDRESS",
             "POINTS LIST DESCRIPTION"],
            ["FAN-ST", "Supply Fan Status", "R", "BI01", "514", "Fan status"],
            ["", "1 - GAS CONFIG NAME", "", "", "", ""],
            ["", "", "", "", "", "1 - Occupied cooling low"],
            ["", "", "", "", "", "FLEXSYS: IF CURRENT MODE IS OCCUPIED"],
        ]
        fake_fitz = types.SimpleNamespace(open=lambda _path: _Document(table))

        with mock.patch.dict(sys.modules, {"fitz": fake_fitz}):
            rows, unknown, _head, skipped = IPU.parse_doc("synthetic.pdf")

        self.assertEqual(len(rows), 1)
        common = rows[0]["common"]
        self.assertEqual(common["altNames"], ["1 - GAS CONFIG NAME"])
        self.assertEqual(
            common["states"],
            [{"code": "1", "label": "Occupied cooling low"}],
        )
        self.assertIn("FLEXSYS: IF CURRENT MODE IS OCCUPIED", common["note"])
        self.assertEqual(unknown, {})
        self.assertEqual(skipped, {"altName": 1, "stateCont": 1, "noteCont": 1})

    def test_interface_csv_preserves_alternate_names(self):
        model = {
            "id": "m", "equipId": "e5", "vendor": "JCI", "model": "YPAL",
            "interfaces": [{
                "id": "ipu", "family": "IPU/Series-100", "revision": {},
                "points": [{
                    "common": {"name": "Heat Status", "altNames": ["Electric", "Gas"],
                               "rangeIP": {"min": 1.0, "max": 2.0}},
                    "blocks": {"bacnet": {"objectType": "BI", "instance": 26,
                                             "objectName": "HEAT-ST"}},
                    "provenance": {"sourceFile": "x.pdf", "sourcePage": 1},
                }],
            }],
        }

        row, _states = next(points.iface_rows(model, {
            "modelId": "m", "equipId": "e5", "vendor": "JCI", "model": "YPAL",
        }))

        self.assertIn("altNames", points.FIELDS)
        self.assertEqual(row["altNames"], "Electric | Gas")
        self.assertEqual(row["bacnetName"], "HEAT-ST")
        self.assertEqual(row["rangeMin"], 1.0)
        self.assertEqual(row["rangeMax"], 2.0)

    def test_state_csv_adds_interface_id_at_the_end(self):
        self.assertEqual(
            points.STATE_FIELDS,
            ["modelId", "type", "inst", "name", "stateCode", "stateLabel", "interfaceId"],
        )


class IpuIngestTest(unittest.TestCase):
    def test_changed_existing_source_is_replaced_without_counting_new_points(self):
        incoming = {
            "id": "ipu", "label": "IPU", "family": IPU.FAMILY,
            "protocols": ["bacnet"], "sourceFile": "same.pdf", "pointCount": 1,
            "points": [{"version": "new"}],
        }
        stored = dict(incoming, points=[{"version": "old"}],
                      note="파서 vendor_jci_ipu · 원문 IOM 본문")
        record = {
            "id": "johnson-controls-ypal", "vendor": ingest_jci.VENDOR,
            "model": "YPAL Packaged Rooftop Unit", "interfaces": [stored],
        }
        doc = ({"id": "doc", "title": "YPAL", "prod": "YPAL"}, "same.pdf")

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "models"))
            path = os.path.join(tmp, "models", "johnson-controls-ypal.json")
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(record, fp)
            out = io.StringIO()
            with mock.patch.object(IPU, "docs", return_value=[doc]), \
                 mock.patch.object(IPU, "parse_doc", return_value=([{}], {}, [], {})), \
                 mock.patch.object(ingest_jci, "catalog", return_value={
                     "doc": {"prod": "YPAL", "category": "Applied Packaged Rooftop Units"}
                 }), \
                 mock.patch.object(ingest_jci, "build_interfaces", return_value=[incoming]), \
                 mock.patch.object(ingest_jci, "comm_rows", return_value=[]), \
                 mock.patch.object(ingest_jci.S, "model_id", return_value="johnson-controls-ypal"), \
                 mock.patch.object(ingest_jci, "DATA", tmp), \
                 redirect_stdout(out):
                ingest_jci.apply_iom()

            with open(path, encoding="utf-8") as fp:
                saved = json.load(fp)
        self.assertEqual(saved["interfaces"][0]["points"], [{"version": "new"}])
        self.assertIn("모델 1건 · 새 오브젝트 0점", out.getvalue())

    def test_scan_metadata_supports_fresh_checkout_without_catalog_snapshot(self):
        iface = {
            "id": "ipu", "label": "IPU", "family": IPU.FAMILY,
            "protocols": ["bacnet"], "sourceFile": "fresh.pdf", "pointCount": 1,
            "points": [], "note": "주소 대역이 이어져 같은 판",
        }
        doc = ({"id": "doc", "title": "YPAL", "prod": "YPAL",
                "cat": "Applied Packaged Rooftop Units"}, "fresh.pdf")

        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(IPU, "docs", return_value=[doc]), \
             mock.patch.object(IPU, "parse_doc", return_value=([{}], {}, [], {})), \
             mock.patch.object(ingest_jci, "catalog", side_effect=FileNotFoundError), \
             mock.patch.object(ingest_jci, "build_interfaces", return_value=[iface]), \
             mock.patch.object(ingest_jci, "comm_rows", return_value=[]), \
             mock.patch.object(ingest_jci.S, "model_id", return_value="johnson-controls-ypal"), \
             mock.patch.object(ingest_jci, "DATA", tmp):
            out = io.StringIO()
            with redirect_stdout(out):
                ingest_jci.apply_iom(dry=True)

        self.assertIn("(dry) johnson-controls-ypal", out.getvalue())
        self.assertIn("주소 대역이 이어져 같은 판", iface["note"])

    def test_unknown_columns_abort_before_silent_ingest(self):
        doc = ({"id": "doc", "title": "YPAL", "prod": "YPAL",
                "cat": "Applied Packaged Rooftop Units"}, "changed.pdf")

        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(IPU, "docs", return_value=[doc]), \
             mock.patch.object(IPU, "parse_doc",
                               return_value=([{}], {"NEW COLUMN": 1}, [], {})), \
             mock.patch.object(ingest_jci, "catalog", return_value={}):
            with self.assertRaisesRegex(ValueError, "NEW COLUMN"):
                ingest_jci.apply_iom(dry=True)

    def test_existing_source_is_not_reported_as_new_on_repeat(self):
        iface = {
            "id": "ipu", "label": "IPU", "family": IPU.FAMILY,
            "protocols": ["bacnet"], "sourceFile": "same.pdf", "pointCount": 1,
            "points": [],
        }
        stored_iface = dict(iface, note="파서 vendor_jci_ipu · 원문 IOM 본문")
        record = {
            "id": "johnson-controls-ypal", "vendor": ingest_jci.VENDOR,
            "model": "YPAL Packaged Rooftop Unit", "interfaces": [stored_iface],
        }
        doc = ({"id": "doc", "title": "YPAL", "prod": "YPAL"}, "same.pdf")

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "models"))
            path = os.path.join(tmp, "models", "johnson-controls-ypal.json")
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(record, fp)
            out = io.StringIO()
            with mock.patch.object(IPU, "docs", return_value=[doc]), \
                 mock.patch.object(IPU, "parse_doc", return_value=([{}], {}, [], {})), \
                 mock.patch.object(ingest_jci, "catalog", return_value={
                     "doc": {"prod": "YPAL", "category": "Applied Packaged Rooftop Units"}
                 }), \
                 mock.patch.object(ingest_jci, "build_interfaces", return_value=[iface]), \
                 mock.patch.object(ingest_jci, "comm_rows", return_value=[]), \
                 mock.patch.object(ingest_jci.S, "model_id", return_value="johnson-controls-ypal"), \
                 mock.patch.object(ingest_jci, "DATA", tmp), \
                 redirect_stdout(out):
                ingest_jci.apply_iom()

            with open(path, encoding="utf-8") as fp:
                saved = json.load(fp)
            self.assertEqual([i["sourceFile"] for i in saved["interfaces"]], ["same.pdf"])
            self.assertIn("모델 0건 · 새 오브젝트 0점", out.getvalue())


if __name__ == "__main__":
    unittest.main()
