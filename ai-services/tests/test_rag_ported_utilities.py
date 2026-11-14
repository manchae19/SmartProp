"""Unit tests for the RAG utility modules ported from Backend-Huy.

These modules are not wired into the chat pipeline yet; the tests pin their
behaviour so a later integration cannot change it silently.
"""
import unittest
from decimal import Decimal

from app.rag import money, scope, locality, hybrid, market


class MoneyTests(unittest.TestCase):
    def test_parses_billion_range(self):
        budget = money.parse_budget("tìm nhà từ 2 đến 3 tỷ")
        self.assertEqual(budget.status, "VALID")
        self.assertEqual(budget.minimum, Decimal(2_000_000_000))
        self.assertEqual(budget.maximum, Decimal(3_000_000_000))

    def test_parses_single_maximum(self):
        budget = money.parse_budget("nhà dưới 3 tỷ")
        self.assertEqual(budget.status, "VALID")
        self.assertEqual(budget.maximum, Decimal(3_000_000_000))

    def test_parses_million_unit(self):
        budget = money.parse_budget("khoảng 800 triệu")
        self.assertEqual(budget.status, "VALID")
        self.assertEqual(budget.maximum, Decimal(800_000_000))

    def test_returns_no_budget_when_absent(self):
        budget = money.parse_budget("nhà ở Hải Châu có 3 phòng ngủ")
        self.assertNotEqual(budget.status, "VALID")

    def test_format_vnd_uses_dot_separators(self):
        self.assertEqual(money.format_vnd(3_000_000_000), "3.000.000.000 đồng")


class ScopeTests(unittest.TestCase):
    def test_housing_question_is_in_scope(self):
        self.assertIsNone(scope.domain_reply("nhà ở Hải Châu giá bao nhiêu", {"intent": "SEARCH"}))

    def test_off_topic_question_is_rejected(self):
        reply = scope.domain_reply("dự báo thời tiết ngày mai thế nào", {"intent": "SEARCH"})
        self.assertEqual(reply, scope.OUTSIDE)

    def test_outside_message_is_non_empty(self):
        self.assertTrue(scope.OUTSIDE.strip())


class LocalityTests(unittest.TestCase):
    def test_key_strips_ward_prefix(self):
        self.assertEqual(locality.key("Phường Hòa Cường"), "hoa cuong")

    def test_key_handles_empty(self):
        self.assertEqual(locality.key(""), "")

    def test_resolves_single_ward_from_documents(self):
        documents = [{
            "kind": "AREA_AMENITY",
            "metadata": {"areaLevel": "WARD", "areaName": "Phường Hòa Cường", "district": "Hải Châu", "areaId": "x"},
        }]
        result = locality.amenity_locality("tiện ích ở phường Hòa Cường", documents)
        self.assertEqual(result["ward"], "Phường Hòa Cường")

    def test_returns_none_without_ward_mention(self):
        self.assertIsNone(locality.amenity_locality("nhà ở Đà Nẵng", []))


class HybridTests(unittest.TestCase):
    def test_bm25_ranks_matching_document_first(self):
        documents = [
            {"id": "a", "sourceId": "a", "text": "nha mat tien duong ngo the lieu hai chau"},
            {"id": "b", "sourceId": "b", "text": "can ho chung cu son tra view bien"},
        ]
        ranked = hybrid.bm25("ngo the lieu", documents)
        self.assertTrue(ranked)
        self.assertEqual(documents[ranked[0][0]]["id"], "a")

    def test_bm25_returns_empty_for_no_overlap(self):
        documents = [{"id": "a", "sourceId": "a", "text": "can ho chung cu"}]
        self.assertEqual(hybrid.bm25("zzzzz", documents), [])

    def test_tokens_drops_stopwords(self):
        tokens = hybrid.tokens("nhà ở Hải Châu")
        self.assertNotIn("o", tokens)


class MarketTests(unittest.TestCase):
    def test_district_list_covers_da_nang(self):
        self.assertIn("Hải Châu", market.DISTRICTS)
        self.assertEqual(len(market.DISTRICTS), 7)

    def test_format_money_is_readable(self):
        self.assertIn("đồng", market.format_money(3_000_000_000))


if __name__ == "__main__":
    unittest.main()
