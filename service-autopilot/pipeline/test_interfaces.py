# -*- coding: utf-8 -*-
"""인터페이스(포인트 리스트 리비전) 게이트 시험.

왜 시험이 필요한가
  사전(point-schema.json)만 있고 강제하는 코드가 없으면 규칙은 지켜지지 않는다 —
  정격 쪽에서 이미 겪었다(사전 밖 필드가 자라 평면 18종이 됐다). 여기서는
  게이트가 **실제로 막는지**를 미끼 레코드로 확인한다. 게이트가 조용히 통과하면
  다음 사람은 게이트가 있다고 믿고 넣는다.
"""
import unittest

import validate as V


def model(**kw):
    m = {"id": "t", "vendor": "v", "model": "m", "name": "n",
         "equipId": "e5", "cat": "HVAC.AIR.RTU", "tag": "rooftop"}
    m.update(kw)
    return m


def codes(m):
    out = []
    V.check_interfaces(m, lambda lv, code, msg: out.append((lv, code)))
    return out


def point():
    return {"common": {"name": "Supply Air Temperature"},
            "blocks": {"bacnet": {"objectType": "AI", "instance": 3}},
            "provenance": {"sourceFile": "x.pdf", "sourcePage": 2,
                           "family": "SC-EQ", "interfaceId": "sceq"}}


def iface(**kw):
    it = {"id": "sceq", "label": "SC-EQ 포인트 리스트", "family": "SC-EQ",
          "protocols": ["bacnet"], "sourceFile": "x.pdf", "points": [point()]}
    it.update(kw)
    return it


class InterfaceGateTest(unittest.TestCase):
    def test_valid_interface_passes(self):
        lv = [x for x in codes(model(interfaces=[iface()])) if x[0] == "E"]
        self.assertEqual(lv, [])

    def test_legacy_flat_points_are_reported_not_errored(self):
        # 옛 추출본 24,423점은 오류가 아니다. 다만 남은 이관 분량으로 보여야 한다.
        got = codes(model(points=[{"type": "AI", "inst": 1, "name": "x"}]))
        self.assertIn(("I", "points-legacy"), got)
        self.assertFalse([x for x in got if x[0] == "E"])

    def test_mixed_shapes_are_an_error(self):
        got = codes(model(points=[{"type": "AI", "inst": 1}], interfaces=[iface()]))
        self.assertIn(("E", "iface-mixed"), got)

    def test_field_outside_dictionary_is_an_error(self):
        # 사전 우선(rules.dictionaryFirst) — 새 열은 sourceColumns 에 담고 등재부터.
        p = point()
        p["common"]["scaleFactor"] = "X10"
        self.assertIn(("E", "point-field"), codes(model(interfaces=[iface(points=[p])])))

    def test_unknown_protocol_block_is_an_error(self):
        p = point()
        p["blocks"]["knx"] = {"address": 1}
        got = codes(model(interfaces=[iface(protocols=["bacnet", "knx"], points=[p])]))
        self.assertIn(("E", "iface-protocol"), got)

    def test_point_pointing_at_another_interface_is_an_error(self):
        p = point()
        p["provenance"]["interfaceId"] = "elink-gpic"
        self.assertIn(("E", "point-orphan"), codes(model(interfaces=[iface(points=[p])])))

    def test_duplicate_interface_id_is_an_error(self):
        got = codes(model(interfaces=[iface(), iface()]))
        self.assertIn(("E", "iface-dup-id"), got)

    def test_point_count_mismatch_is_an_error(self):
        got = codes(model(interfaces=[iface(pointCount=99)]))
        self.assertIn(("E", "iface-count"), got)

    def test_family_outside_enum_is_an_error(self):
        got = codes(model(interfaces=[iface(family="SC-EQ v2")]))
        self.assertIn(("E", "iface-family"), got)

    def test_excluded_rows_stay_visible(self):
        # 예약 슬롯 745행(29%)을 조용히 빼면 화면은 '문서에 그것뿐'으로 읽힌다.
        got = codes(model(interfaces=[iface(excluded={"예약 슬롯": 745})]))
        self.assertIn(("I", "iface-excluded"), got)

    def test_undeclared_block_with_values_warns(self):
        p = point()
        p["blocks"]["modbus"] = {"address": 7}
        got = codes(model(interfaces=[iface(points=[p])]))
        self.assertIn(("W", "iface-protocol-undeclared"), got)

    def test_alt_names_must_be_a_nonempty_string_array(self):
        p = point()
        p["common"]["altNames"] = "Gas heat status"
        self.assertIn(("E", "point-shape"), codes(model(interfaces=[iface(points=[p])])))

    def test_states_must_have_string_code_and_label(self):
        p = point()
        p["common"]["states"] = [{"code": 1, "label": "On"}]
        self.assertIn(("E", "point-shape"), codes(model(interfaces=[iface(points=[p])])))

    def test_states_reject_empty_labels(self):
        p = point()
        p["common"]["states"] = [{"code": "1", "label": ""}]
        self.assertIn(("E", "point-shape"), codes(model(interfaces=[iface(points=[p])])))


if __name__ == "__main__":
    unittest.main()
