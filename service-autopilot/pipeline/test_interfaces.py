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


class SubscriptSplit(unittest.TestCase):
    """아래첨자가 떨어진 글자를 인터페이스 포인트에서도 잡는가.

    왜 여기 있나
      67fd3b6 이 데이터 113건을 고치고 가드를 넣었지만 그 가드는 **평면 points 만**
      읽었다. 인터페이스형 모델은 평면이 0점이라 아무것도 못 봤고, 2026-08-31
      `--apply-iom` 재실행이 YPAL 40건을 다시 깨뜨렸을 때도 경고 수가 그대로였다.
      파서는 아직 CO₂ 를 흩으므로 재파싱 때마다 되살아난다 — 이 시험이 그 자리를 지킨다.
      미끼 글자는 실제로 파서가 뱉은 것이다(JCI_IOM_100.50-NOM10.pdf).
    """

    def fires(self, **common):
        p = point()
        p["common"].update(common)
        return ("W", "subscript-split") in codes(model(interfaces=[iface(points=[p])]))

    def test_broken_name_fires(self):
        self.assertTrue(self.fires(name="CO Level Of The 2 Outside Air"))

    def test_broken_trailing_digit_fires(self):
        self.assertTrue(self.fires(name="CO Offset SP 2"))

    def test_broken_note_fires(self):
        self.assertTrue(self.fires(note="Displays the actual OA air CO (PPM) 2"))

    def test_broken_short_name_fires(self):
        self.assertTrue(self.fires(shortName="CO 1 OUT 2_"))

    def test_broken_state_label_fires(self):
        self.assertTrue(self.fires(
            states=[{"code": "1", "label": "1=CO 2=CO and air flow boost 2, 2"}]))

    def test_broken_alt_name_fires(self):
        self.assertTrue(self.fires(altNames=["CO LVL Inside 2 Value BAS"]))

    def test_intact_subscript_is_quiet(self):
        # 파서가 제대로 뽑은 것들 — 여기서 울리면 가드가 못 쓰게 된다
        self.assertFalse(self.fires(name="CO2 Level Of The Outside Air"))
        self.assertFalse(self.fires(shortName="CO2 1 OUT"))
        self.assertFalse(self.fires(note="Actual indoor CO2 value (PPM)"))

    def test_ordinary_trailing_numbers_are_quiet(self):
        # 각주가 아니라 진짜 일련번호인 이름들 — 실제 카탈로그에 있다
        self.assertFalse(self.fires(name="Circuit 2"))
        self.assertFalse(self.fires(name="Comp VFD Alarms 1"))
        self.assertFalse(self.fires(name="Configuration of I/O 1"))

    def test_colorado_and_cutout_are_quiet(self):
        # 67fd3b6 이 오탐으로 확인한 2건 — CO 가 Cutout·콜로라도주다
        self.assertFalse(self.fires(name="COND REFRIG HI PRESS CO"))
        self.assertFalse(self.fires(note="3=Pueblo, CO, USA"))


if __name__ == "__main__":
    unittest.main()
