"""Commute destination selection and route-based ranking.

These pin the two decisions that are easy to get wrong: where the workplace comes from
(a saved profile value never reaches the browser), and what "khoảng 25 phút" means
next to "tối đa 25 phút".
"""
import unittest

from app.rag import commute_destination as cd
from app.rag import commute_ranking as cr


class DestinationIntentTests(unittest.TestCase):
    def test_saved_workplace_phrasings(self):
        for text in ("Dùng nơi làm việc đã lưu", "su dung noi lam viec da luu", "lấy chỗ làm đã lưu"):
            self.assertTrue(cd.wants_saved(text), text)

    def test_new_address_phrasings(self):
        for text in ("Nhập địa điểm khác", "nhap dia chi", "điền địa điểm"):
            self.assertTrue(cd.wants_new(text), text)

    def test_skip_phrasings(self):
        for text in ("bỏ qua", "thôi", "không cần", "để sau"):
            self.assertTrue(cd.wants_skip(text), text)

    def test_plain_consent_variants(self):
        for text in ("đồng ý", "duoc", "ok", "OK", "vang"):
            self.assertTrue(cd.is_plain_consent(text), text)
        self.assertFalse(cd.is_plain_consent("đồng ý, 123 Nguyễn Văn Linh"))

    def test_address_is_not_extracted_from_an_option_choice(self):
        self.assertIsNone(cd.address_from("Dùng nơi làm việc đã lưu"))
        self.assertIsNone(cd.address_from("Bỏ qua"))
        self.assertIsNone(cd.address_from("đồng ý"))
        self.assertEqual(cd.address_from("123 Nguyễn Văn Linh, Hải Châu"), "123 Nguyễn Văn Linh, Hải Châu")

    def test_mode_detection_defaults_to_drive(self):
        self.assertEqual(cd.mode_for("đi bộ"), "walk")
        self.assertEqual(cd.mode_for("ô tô"), "drive")
        self.assertEqual(cd.mode_for("căn này đi làm mất bao lâu"), "drive")
        self.assertEqual(cd.mode_for("đi bộ nhé", "drive"), "walk")

    def test_candidate_index_reads_numbers_and_words(self):
        self.assertEqual(cd.candidate_index("2", 3), 2)
        self.assertEqual(cd.candidate_index("số 3", 3), 3)
        self.assertEqual(cd.candidate_index("cái đầu tiên", 3), 1)
        self.assertIsNone(cd.candidate_index("5", 3))
        self.assertIsNone(cd.candidate_index("chỗ nào cũng được", 3))


class LimitTests(unittest.TestCase):
    def test_soft_limits(self):
        for text, minutes in (("đi làm khoảng 25 phút", 25), ("tầm 30 phút", 30),
                              ("đi làm mất bao lâu, tôi muốn 20 phút", 20)):
            self.assertEqual(cr.limit_from(text), (minutes, "SOFT"), text)

    def test_hard_limits(self):
        for text, minutes in (("tối đa 25 phút", 25), ("không quá 15 phút", 15),
                              ("dưới 30 phút đi làm", 30)):
            self.assertEqual(cr.limit_from(text), (minutes, "HARD"), text)

    def test_hard_wins_over_soft_in_the_same_question(self):
        self.assertEqual(cr.limit_from("khoảng 20 phút nhưng tối đa 25 phút"), (25, "HARD"))

    def test_bare_minutes_need_a_commute_context(self):
        self.assertEqual(cr.limit_from("nhà 2 phút ra chợ"), (None, None))
        self.assertEqual(cr.limit_from("đi làm 25 phút"), (25, "SOFT"))

    def test_out_of_range_minutes_are_ignored(self):
        self.assertEqual(cr.limit_from("tối đa 999 phút"), (None, None))
        self.assertEqual(cr.limit_from("tối đa 0 phút"), (None, None))


class RankingTests(unittest.TestCase):
    def entries(self):
        return [
            {"id": "slow", "route": {"durationSeconds": 1800.0}},
            {"id": "fast", "route": {"durationSeconds": 600.0}},
            {"id": "unknown", "route": None},
            {"id": "mid", "route": {"durationSeconds": 1200.0}},
        ]

    def test_soft_orders_by_time_and_keeps_unmeasured_last(self):
        ordered = cr.rank(self.entries(), 25, "SOFT", 3)
        self.assertEqual([e["id"] for e in ordered], ["fast", "mid", "slow"])

    def test_hard_drops_anything_over_the_limit(self):
        ordered = cr.rank(self.entries(), 25, "HARD", 3)
        self.assertEqual([e["id"] for e in ordered], ["fast", "mid"])

    def test_hard_drops_unmeasured_routes(self):
        ordered = cr.rank(self.entries(), 30, "HARD", 3)
        self.assertNotIn("unknown", [e["id"] for e in ordered])

    def test_hard_can_empty_the_list(self):
        self.assertEqual(cr.rank(self.entries(), 5, "HARD", 3), [])

    def test_no_limit_keeps_input_order(self):
        ordered = cr.rank(self.entries(), None, None, 2)
        self.assertEqual([e["id"] for e in ordered], ["slow", "fast"])

    def test_work_proximity_phrasings(self):
        self.assertTrue(cr.wants_work_proximity("tìm nhà gần chỗ làm"))
        self.assertTrue(cr.wants_work_proximity("gần nơi làm việc"))
        self.assertFalse(cr.wants_work_proximity("tìm nhà gần trường"))


if __name__ == "__main__":
    unittest.main()
