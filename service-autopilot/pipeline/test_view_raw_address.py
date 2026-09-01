# -*- coding: utf-8 -*-
"""화면이 주소 원문 표기를 잃지 않는가 + 화면이 데이터보다 낡지 않았나.

왜 시험이 필요한가
  화면은 정규화한 주소만 실었다. 그래서 매뉴얼에 40001 로 적힌 점이 화면엔 0 으로만
  보였고, 사용자가 "이게 뭐냐" 고 물어서야 드러났다. 재 보니 252점이 그 상태였다:
    YKL 공조기        40001  → 0     (157점)
    AYK550 FLN        '{03}' → 3     (79점)
    AYK550 Modbus     40001  → 0     (16점)
  '{03}' 은 더 나쁘다 — 중괄호가 "필드 패널에서 unbundle 가능" 이라는 뜻이라
  표기가 사라지면 그 정보 자체가 없어진다(원문 각주 c).

  이 함정은 **원문 표기와 정규화 값이 갈리는 계통을 넣을 때마다** 재현된다.
  앞선 계통들은 둘이 같아서 안 드러났을 뿐이다. 그래서 게이트로 건다.
"""
import glob
import io
import json
import os
import unittest

import ingest_jci as I
import validate as V

DATA = I.DATA


def models():
    for f in glob.glob(os.path.join(DATA, "models", "*.json")):
        yield json.load(io.open(f, encoding="utf-8"))


class RawAddressReachesTheScreen(unittest.TestCase):

    def test_normalised_only_view_is_flagged(self):
        # 미끼 — 원문 40001, 정규화 0. 화면이 0 만 실으면 대조를 못 한다.
        p = {"common": {"name": "CONTROL WORD"},
             "blocks": {"modbus": {"address": 0}},
             "provenance": {"sourceColumns": {"Modbus Register": "40001"}}}
        self.assertEqual(I.raw_addr(p), "40001")
        self.assertEqual(I.view_point(p)["mr"], "40001")
        self.assertEqual(I.view_point(p)["m"], 0)

    def test_braces_survive_to_the_screen(self):
        # 중괄호는 뜻이 있는 표기다 — 숫자만 남기면 정보가 사라진다
        p = {"common": {"name": "FREQ OUTPUT"},
             "blocks": {"fln": {"address": 3}},
             "provenance": {"sourceColumns": {"Point #": "{03}"}}}
        self.assertEqual(I.view_point(p)["mr"], "{03}")

    def test_identical_raw_adds_no_noise(self):
        # 원문과 정규화가 같으면 굳이 두 번 적지 않는다
        p = {"common": {"name": "X"},
             "blocks": {"modbus": {"address": 7}},
             "provenance": {"sourceColumns": {"Modbus Register": "7"}}}
        self.assertIsNone(I.raw_addr(p))
        # view_point 는 값 없는 열쇠를 아예 안 담는다 — 화면에 빈 칸이 안 생긴다
        self.assertIsNone(I.view_point(p).get("mr"))

    def test_no_source_column_is_not_an_error(self):
        p = {"common": {"name": "X"}, "blocks": {"bacnet": {"objectType": "AI",
                                                            "instance": 3}},
             "provenance": {}}
        self.assertIsNone(I.raw_addr(p))

    def test_every_stored_point_with_a_differing_raw_reaches_the_screen(self):
        # 실제 카탈로그 전수 — 새 계통을 넣고 이 시험이 깨지면 화면 쪽을 안 넓힌 것이다
        hidden = []
        for m in models():
            for it in (m.get("interfaces") or []):
                for p in (it.get("points") or []):
                    if I.raw_addr(p) and I.view_point(p).get("mr") is None:
                        hidden.append(m["id"])
        self.assertEqual(hidden, [])

    def test_the_known_252_are_actually_carried(self):
        # 0 이 나오면 시험이 아무것도 안 지키고 있다는 뜻이다
        n = sum(1 for m in models() for it in (m.get("interfaces") or [])
                for p in (it.get("points") or []) if I.raw_addr(p))
        self.assertGreaterEqual(n, 200)


class ReviewPagesFreshness(unittest.TestCase):

    def test_gate_reports_nothing_when_pages_are_current(self):
        # 지금 상태에서 우는지가 아니라, **판정 함수가 돈다**는 것만 본다
        out = V.check_review_pages()
        self.assertIsInstance(out, list)
        for lv, code, msg in out:
            self.assertIn(lv, ("E", "W", "I"))
            self.assertTrue(msg)

    def test_gate_fires_when_a_model_is_newer_than_a_page(self):
        import time

        f = sorted(glob.glob(os.path.join(DATA, "models", "*.json")))[0]
        st = os.stat(f)
        os.utime(f, (st.st_atime, time.time() + 3600))
        try:
            codes = [c for _lv, c, _m in V.check_review_pages()]
            self.assertIn("review-stale", codes)
        finally:
            os.utime(f, (st.st_atime, st.st_mtime))


class ConditionalNotes(unittest.TestCase):
    """운전 조건이 비고에만 있는 것을 드러내는가 — 지어내지는 않는다."""

    def test_conditional_note_is_surfaced(self):
        m = {"interfaces": [{"points": [{"common": {
            "name": "CONTROL WORD",
            "note": "Supported only if the drive is configured to use the "
                    "YORK Drives Profile (5305 = 0)."}}]}]}
        out = []
        V.check_conditional_notes(m, lambda lv, c, msg: out.append(c))
        self.assertIn("condition-in-note", out)

    def test_plain_note_is_not_flagged(self):
        m = {"interfaces": [{"points": [{"common": {
            "name": "X", "note": "Displays the actual OA air CO2 (PPM)"}}]}]}
        out = []
        V.check_conditional_notes(m, lambda lv, c, msg: out.append(c))
        self.assertEqual(out, [])

    def test_structured_availability_is_not_double_counted(self):
        m = {"interfaces": [{"points": [{"common": {
            "name": "X", "availability": {"code": "S", "raw": "S"},
            "note": "Only if option installed"}}]}]}
        out = []
        V.check_conditional_notes(m, lambda lv, c, msg: out.append(c))
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
