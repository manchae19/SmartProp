import unittest

from app.rag.personalization import area_spec, apply_area, format_vnd


class AreaSemanticsTests(unittest.TestCase):
    def test_strict_minimum_excludes_equal_area(self):
        self.assertEqual(area_spec("Tìm nhà trên 80m² tại Cẩm Lệ"), {
            "minAreaSqm": "80", "maxAreaSqm": None,
            "minAreaExclusive": True, "maxAreaExclusive": False,
        })

    def test_inclusive_minimum_from(self):
        self.assertEqual(area_spec("Tìm nhà từ 80m² tại Cẩm Lệ"), {
            "minAreaSqm": "80", "maxAreaSqm": None,
            "minAreaExclusive": False, "maxAreaExclusive": False,
        })

    def test_strict_maximum_below(self):
        self.assertEqual(area_spec("Tìm nhà dưới 80m²"), {
            "minAreaSqm": None, "maxAreaSqm": "80",
            "minAreaExclusive": False, "maxAreaExclusive": True,
        })

    def test_inclusive_maximum_at_most(self):
        self.assertEqual(area_spec("Tìm nhà tối đa 80m²"), {
            "minAreaSqm": None, "maxAreaSqm": "80",
            "minAreaExclusive": False, "maxAreaExclusive": False,
        })

    def test_no_operator_keeps_legacy_inclusive_minimum(self):
        self.assertEqual(area_spec("Tìm nhà 80m² tại Cẩm Lệ"), {
            "minAreaSqm": "80", "maxAreaSqm": None,
            "minAreaExclusive": False, "maxAreaExclusive": False,
        })

    def test_apply_replaces_old_area_constraint(self):
        criteria = {"minAreaSqm": "50", "minAreaExclusive": True}
        self.assertTrue(apply_area(criteria, "Tìm nhà dưới 80m²"))
        self.assertNotIn("minAreaSqm", criteria)
        self.assertEqual(criteria["maxAreaSqm"], "80")
        self.assertTrue(criteria["maxAreaExclusive"])

    def test_vnd_budget_is_grouped_without_rounding(self):
        self.assertEqual(format_vnd("50000000000"), "50.000.000.000 VND")
        self.assertEqual(format_vnd("5500000000"), "5.500.000.000 VND")
        self.assertEqual(format_vnd("5500000000.50"), "5.500.000.000,5 VND")


if __name__ == "__main__":
    unittest.main()
