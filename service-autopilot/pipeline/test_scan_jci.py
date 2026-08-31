# -*- coding: utf-8 -*-
"""본문 스캔 문턱 시험 — 표를 버리지 않으면서 낱말만 스친 것은 거르는가.

왜 시험이 필요한가
  2026-08-31 에 airhandling 236건이 통째로 **적중 0** 이었다. 표가 없어서가 아니라
  문턱이 '한 쪽에 표식 2종 이상'이었기 때문이다 — Modbus 레지스터 표는 우리가 아는
  열 이름이 'REGISTER ADDRESS' 하나뿐이라 그 문턱을 영영 못 넘는다. YKH·YKL 은
  9쪽 연속으로 걸리는데도 빠져 있었고, 문턱을 낮추고서야 진짜 표 5건 741행이 나왔다.
  그런 0 은 "확인했다"처럼 보여서 분모에 그대로 들어간다 — 그래서 게이트를 건다.

  아래 미끼는 전부 실측이다(data/_air_perpage.json).
"""
import unittest

import scan_jci as S


def pages(spec):
    """{쪽번호: [표식…]} → 0쪽부터의 집합 목록"""
    n = max(spec) if spec else 0
    return [set(spec.get(i + 1, ())) for i in range(n)]


def hits(spec):
    per = pages(spec)
    return [i + 1 for i in range(len(per)) if S.page_is_table(per, i)]


class Threshold(unittest.TestCase):

    def test_two_kinds_on_one_page_still_hits(self):
        # 예전 규칙 — 이것을 깨뜨리면 이미 낸 분모가 줄어든다
        self.assertEqual(hits({3: ["BACNET NAME", "OBJECT TYPE AND INSTANCE"]}), [3])

    def test_single_kind_running_across_pages_hits(self):
        # YKH p28~36 · YKL p27~35 — 레지스터 표는 아는 열 이름이 하나뿐이다
        spec = {p: ["REGISTER ADDRESS"] for p in range(28, 37)}
        self.assertEqual(hits(spec), list(range(28, 37)))

    def test_two_page_run_hits(self):
        # 에너지회수 응용 가이드 p27~28 — 짧아도 이어지면 표다
        self.assertEqual(hits({27: ["POINT NAME"], 28: ["POINT NAME"]}), [27, 28])

    def test_lone_page_single_kind_is_filtered(self):
        # 팬코일 p34 는 점퍼 설명표 · CurbPak p9 는 본문 문장이다
        self.assertEqual(hits({34: ["POINT NAME"]}), [])
        self.assertEqual(hits({9: ["AVAILABLE TO CUSTOMER"]}), [])

    def test_different_kinds_on_neighbours_do_not_pair(self):
        # 서로 다른 낱말이 옆 쪽에 있는 것은 이어진 표가 아니다 — 같은 표식만 짝짓는다
        self.assertEqual(hits({10: ["POINT NAME"], 11: ["SNVT TYPE"]}), [])

    def test_gap_between_pages_does_not_pair(self):
        # 한 쪽 건너뛴 것은 이어진 표로 보지 않는다
        self.assertEqual(hits({10: ["POINT NAME"], 12: ["POINT NAME"]}), [])

    def test_empty_pages_never_hit(self):
        self.assertEqual(hits({1: [], 2: [], 3: []}), [])

    def test_run_at_document_edges(self):
        # 첫 쪽·끝 쪽에서도 이웃을 본다 (인덱스 경계)
        self.assertEqual(hits({1: ["POINT NAME"], 2: ["POINT NAME"]}), [1, 2])


class RealDocuments(unittest.TestCase):
    """실측 쪽별 표식으로 판정이 뒤집히지 않는지 — 진짜 5건 · 스친 2건."""

    AYK550 = {**{p: ["REGISTER ADDRESS"] for p in (162, 163, 164)},
              **{p: ["POINT NAME"] for p in (181, 182, 183, 184, 186, 187, 188)}}

    def test_ayk550_hits(self):
        self.assertEqual(len(hits(self.AYK550)), 10)

    def test_ykh_hits(self):
        self.assertEqual(len(hits({p: ["REGISTER ADDRESS"] for p in range(28, 37)})), 9)


class TableHeader(unittest.TestCase):
    """머리글이 두 줄이거나 열 이름이 세로로 쪼개져도 표를 찾는가.

    YKH 의 157행짜리 Modbus 표가 **0행**으로 세어져 있었다. 0행만 머리글로 봤고,
    그 표의 1열은 0행 'PLC register' + 1행 'Address' 로 **세로로** 쪼개져 있었다.
    쪽 글자에서는 'register\nAddress' 가 걸리는데 표 인식에서는 안 걸린다 —
    경로가 다르면 결과가 다르다는 것이 여기서도 나왔다.
    """

    YKH = [["PLC register", "", "", "", ""],
           ["Address", "Parameter number", "Name", "Range", "Details"],
           ["40001", "0", "Unit open and close variable", "0, 1", "0: Off"],
           ["40002", "1", "Unit set temperature", "0 to 999", ""]]
    ONE_LINE = [["BACNET NAME", "OBJECT TYPE AND INSTANCE"],
                ["A", "AI 1"], ["B", "AI 2"], ["C", "AI 3"]]
    UNRELATED = [["Jumper Name", "Description"],
                 ["JP1", "x"], ["JP2", "y"], ["JP3", "z"]]

    def test_two_row_header_is_joined_columnwise(self):
        head, start = S.table_header(self.YKH)
        self.assertIn("PLC register Address", head)
        self.assertEqual(start, 2)             # 본문은 2행부터

    def test_one_row_header_does_not_eat_a_data_row(self):
        # 두 줄을 먼저 대면 'BACNET NAME A | ...' 가 되어 행이 하나씩 준다
        head, start = S.table_header(self.ONE_LINE)
        self.assertEqual(head, "BACNET NAME | OBJECT TYPE AND INSTANCE")
        self.assertEqual(start, 1)

    def test_table_without_marks_is_not_a_point_table(self):
        self.assertIsNone(S.table_header(self.UNRELATED))

    def test_ragged_rows_do_not_crash(self):
        # 열 수가 들쭉날쭉한 표가 실제로 온다
        ragged = [["PLC register"], ["Address", "Name", "Range"],
                  ["40001", "x", "0, 1"], ["40002", "y", "0 to 9"]]
        self.assertIsNotNone(S.table_header(ragged))


if __name__ == "__main__":
    unittest.main()
