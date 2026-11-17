"""Nearby search must read every page, because the list API sorts by time, not distance.

The nearest listing can sit on any page. These tests pin that the page walk happens,
that duplicates across pages are dropped, and that an incomplete read is never reported
as "the three nearest".
"""
import unittest
from unittest.mock import Mock

import test_rag_multiturn as fixtures
from app.rag import tools as tools_module
from app.rag.config import Settings
from app.rag.geo import haversine_meters
from app.rag.schemas import ChatRequest
from app.rag.tools import BackendTools

ORIGIN = {"latitude": 16.06, "longitude": 108.22}


def listing(pid, meters, price=2000000000, status="PUBLISHED"):
    item = fixtures.prop(pid, price, 80)
    # The list API names the field "price"; the recommendation payload uses "priceVnd".
    item["price"] = price
    item["latitude"] = ORIGIN["latitude"] + meters / 111_194.9
    item["longitude"] = ORIGIN["longitude"]
    item["status"] = status
    return item


def page(items, total_pages, page_number):
    return {"items": items, "page": page_number, "size": 50,
            "totalElements": total_pages * 50, "totalPages": total_pages}


class PaginationTests(unittest.TestCase):
    def tools(self, pages):
        tools = BackendTools(Settings.from_env())
        responses = []
        for body in pages:
            response = Mock()
            response.status_code = 200
            response.content = __import__("json").dumps(body).encode()
            responses.append(response)
        tools.client = Mock()
        tools.client.get.side_effect = responses
        return tools

    def test_every_page_is_read(self):
        tools = self.tools([page([listing("property:a", 100)], 3, 0),
                            page([listing("property:b", 200)], 3, 1),
                            page([listing("property:c", 300)], 3, 2)])
        result = tools.search_nearby(ORIGIN["latitude"], ORIGIN["longitude"], 1000)
        self.assertEqual([i["id"] for i in result["items"]],
                         ["property:a", "property:b", "property:c"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["pagesRead"], 3)

    def test_a_duplicate_across_pages_is_kept_once(self):
        tools = self.tools([page([listing("property:a", 100), listing("property:b", 200)], 2, 0),
                            page([listing("property:b", 200), listing("property:c", 300)], 2, 1)])
        result = tools.search_nearby(ORIGIN["latitude"], ORIGIN["longitude"], 1000)
        self.assertEqual([i["id"] for i in result["items"]],
                         ["property:a", "property:b", "property:c"])

    def test_the_walk_is_bounded(self):
        pages = [page([listing(f"property:{i}", 100 + i)], 999, i)
                 for i in range(tools_module.NEARBY_MAX_PAGES + 5)]
        tools = self.tools(pages)
        result = tools.search_nearby(ORIGIN["latitude"], ORIGIN["longitude"], 1000)
        self.assertFalse(result["complete"])
        self.assertEqual(result["pagesRead"], tools_module.NEARBY_MAX_PAGES)

    def test_a_listing_without_coordinates_is_skipped(self):
        broken = listing("property:broken", 100)
        broken["latitude"] = None
        tools = self.tools([page([broken, listing("property:ok", 200)], 1, 0)])
        result = tools.search_nearby(ORIGIN["latitude"], ORIGIN["longitude"], 1000)
        self.assertEqual([i["id"] for i in result["items"]], ["property:ok"])

    def test_a_draft_is_skipped(self):
        tools = self.tools([page([listing("property:draft", 100, status="DRAFT"),
                                  listing("property:ok", 200)], 1, 0)])
        result = tools.search_nearby(ORIGIN["latitude"], ORIGIN["longitude"], 1000)
        self.assertEqual([i["id"] for i in result["items"]], ["property:ok"])


class NearestAcrossPagesTests(unittest.TestCase):
    """The nearest listing is on page 2; it must still come first."""

    def service(self, pages):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[fixtures.prop("property:a", 2000000000, 90)])
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "300 Dũng Sĩ Thanh Khê", "latitude": ORIGIN["latitude"],
             "longitude": ORIGIN["longitude"], "approximate": False}]
        # The tool is exercised for real; only the HTTP client is faked.
        tools = BackendTools(Settings.from_env())
        responses = []
        for body in pages:
            response = Mock()
            response.status_code = 200
            response.content = __import__("json").dumps(body).encode()
            responses.append(response)
        tools.client = Mock()
        tools.client.get.side_effect = responses
        b.search_nearby.side_effect = lambda *a, **k: tools.search_nearby(*a, **k)
        return s, b

    def ask(self, s, q, sid=None):
        return s.chat(ChatRequest(question=q, sessionId=sid, requireGeneration=False))

    def test_nearest_on_a_later_page_wins(self):
        far = [listing(f"property:far{i}", 800 + i) for i in range(50)]
        s, b = self.service([page(far, 2, 0),
                             page([listing("property:nearest", 120),
                                   listing("property:second", 400)], 2, 1)])
        reply = self.ask(s, "Tìm nhà gần 300 Dũng Sĩ Thanh Khê")
        ids = [p["id"] for p in reply.recommendedProperties]
        self.assertEqual(ids, ["property:nearest", "property:second", "property:far0"])

    def test_a_listing_outside_the_radius_is_dropped_even_if_it_is_on_page_one(self):
        s, b = self.service([page([listing("property:outside", 1500),
                                   listing("property:inside", 900)], 1, 0)])
        reply = self.ask(s, "Tìm nhà gần 300 Dũng Sĩ Thanh Khê")
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:inside"])

    def test_an_incomplete_read_is_not_called_the_nearest(self):
        pages = [page([listing(f"property:{i}", 100 + i)], 999, i)
                 for i in range(tools_module.NEARBY_MAX_PAGES)]
        s, b = self.service(pages)
        reply = self.ask(s, "Tìm nhà gần 300 Dũng Sĩ Thanh Khê")
        notes = " ".join(reply.dataLimitations)
        self.assertIn("Chưa đọc hết danh sách tin", notes)
        self.assertIn("chưa phải toàn bộ khu vực", notes)

    def test_equal_distances_are_ordered_stably(self):
        s, b = self.service([page([listing("property:z", 500),
                                   listing("property:a", 500),
                                   listing("property:m", 500)], 1, 0)])
        first = self.ask(s, "Tìm nhà gần 300 Dũng Sĩ Thanh Khê")
        ids = [p["id"] for p in first.recommendedProperties]
        self.assertEqual(ids, sorted(ids))


if __name__ == "__main__":
    unittest.main()
