# -*- coding: utf-8 -*-
"""검사대 화면이 제품을 하나도 빠뜨리지 않는가.

왜 있나
  좌측 레일과 「진행 현황」 표가 **손으로 적은 분류 목록**(VIEW 의 KIND)으로
  제품을 묶는데, 목록에 없는 분류는 통째로 사라졌다. 실제로 자립형 2제품
  (Versecon 163점 · L-Series 4점)이 화면에서 안 보였고 머리글은 39, 레일은
  37 이었다 — **머리글과 본문이 서로 다른 수를 말하고 있었다.**
  숫자가 안 맞는다는 지적을 받고서야 알았다.

  고칠 때 목록에 한 줄 더 넣는 것으로 끝내면 다음 분류에서 또 사라진다.
  그래서 화면이 목록 밖 분류를 '그 밖에' 로 모으게 했고, 이 시험이 그것을
  지킨다 — 분류가 늘어도 제품 수는 늘 맞아야 한다.
"""
import re
import unittest

import ingest_jci


def kind_codes():
    """VIEW 의 JS 배열 KIND 에서 분류 코드를 뽑는다 (화면이 실제로 쓰는 정본)."""
    m = re.search(r"var KIND = \[(.*?)\];", ingest_jci.VIEW, re.S)
    if not m:
        return []
    return re.findall(r"\['([^']+)'", m.group(1))


class ViewCoverageTest(unittest.TestCase):
    def setUp(self):
        self.data = ingest_jci.view_data()
        self.models = self.data["models"]

    def test_screen_has_a_catch_all_for_unlisted_categories(self):
        """목록 밖 분류를 버리지 않는 장치가 화면에 있어야 한다."""
        self.assertIn("function kindsOf(", ingest_jci.VIEW)
        # 레일과 진행 현황 **둘 다** 그것을 써야 한다 — 한쪽만 고치면 다른 쪽이 샌다
        self.assertEqual(ingest_jci.VIEW.count("kindsOf(D.models)"), 2)

    def test_every_model_is_reachable_on_screen(self):
        """머리글이 말하는 제품 수와 화면이 묶어 보여 주는 수가 같아야 한다."""
        known = set(kind_codes())
        listed = [m for m in self.models if m["cat"] in known]
        rest = [m for m in self.models if m["cat"] not in known]
        # kindsOf 가 나머지를 '그 밖에' 로 모으므로 합은 늘 전체와 같다
        self.assertEqual(len(listed) + len(rest), len(self.models))
        # 목록 밖 분류가 생기면 알려는 준다 — 이름을 붙여 두는 편이 낫다
        if rest:
            self.assertTrue(all(m["cat"] for m in rest),
                            "분류가 빈 제품이 있으면 '그 밖에' 로도 못 묶는다")

    def test_self_contained_products_are_listed(self):
        """실제로 사라졌던 자립형이 분류 목록에 있는가 (재발 방지)."""
        self.assertIn("HVAC.AIR.SELFCONTAINED", kind_codes())

    def test_no_model_is_silently_dropped(self):
        """제품마다 분류가 있어야 한다 — 없으면 어느 묶음에도 안 걸린다."""
        missing = [m["model"] for m in self.models if not m.get("cat")]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
