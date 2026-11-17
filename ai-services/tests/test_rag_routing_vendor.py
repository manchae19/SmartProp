"""The routing vendors: provider selection, matrix shape, and rate-limit wording."""
import unittest
from unittest.mock import Mock

from app.rag import focused_property as fp
from app.rag import commute_ranking as cr
from app.rag.tools import BackendTools, OutboundRateLimited, GroundingError
from app.rag.config import Settings


def settings():
    return Settings.from_env()


class MatrixToolTests(unittest.TestCase):
    def tools(self, status, body):
        tools = BackendTools(settings())
        response = Mock()
        response.status_code = status
        response.content = body.encode()
        tools.client = Mock()
        tools.client.post.return_value = response
        return tools

    def test_parses_cells_in_order(self):
        body = ('{"provider":"OPENROUTESERVICE","mode":"drive","cells":['
                '{"propertyId":"11111111-1111-1111-1111-111111111111","status":"OK","distanceMeters":1500.0,"durationSeconds":300.0},'
                '{"propertyId":"22222222-2222-2222-2222-222222222222","status":"NO_ROUTE","distanceMeters":null,"durationSeconds":null}]}')
        result = self.tools(200, body).commute_matrix(["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"], 16.07, 108.24, "Cty", "drive")
        self.assertEqual(result["provider"], "OPENROUTESERVICE")
        self.assertEqual([c["propertyId"] for c in result["cells"]], ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"])
        self.assertEqual(result["cells"][0]["durationSeconds"], 300.0)
        self.assertIsNone(result["cells"][1]["durationSeconds"])

    def test_our_own_rate_limit_is_its_own_error(self):
        with self.assertRaises(OutboundRateLimited):
            self.tools(429, "{}").commute_matrix(["11111111-1111-1111-1111-111111111111"], 16.07, 108.24, "", "drive")

    def test_unconfigured_routing_is_reported(self):
        with self.assertRaises(GroundingError) as caught:
            self.tools(503, "{}").commute_matrix(["11111111-1111-1111-1111-111111111111"], 16.07, 108.24, "", "drive")
        self.assertIn("ROUTE_NOT_CONFIGURED", str(caught.exception))

    def test_rejects_too_many_ids(self):
        with self.assertRaises(GroundingError):
            self.tools(200, "{}").commute_matrix([f"1111111{i}-1111-1111-1111-111111111111" for i in range(7)], 16.07, 108.24, "", "drive")

    def test_rejects_a_bad_id(self):
        with self.assertRaises(GroundingError):
            self.tools(200, "{}").commute_matrix(["not-a-uuid"], 16.07, 108.24, "", "drive")


class VendorLabelTests(unittest.TestCase):
    def test_answer_names_the_actual_vendor(self):
        commute = {"distanceMeters": 4200.0, "durationSeconds": 900.0, "provider": "OPENROUTESERVICE"}
        self.assertIn("openrouteservice", fp.commute_answer({}, commute, "drive"))

    def test_geapify_result_is_not_labelled_openrouteservice(self):
        commute = {"distanceMeters": 4200.0, "durationSeconds": 900.0, "provider": "GEOAPIFY"}
        answer = fp.commute_answer({}, commute, "drive")
        self.assertIn("Geoapify", answer)
        self.assertNotIn("openrouteservice", answer)

    def test_unknown_vendor_falls_back_to_a_neutral_phrase(self):
        commute = {"distanceMeters": 4200.0, "durationSeconds": 900.0, "provider": ""}
        self.assertIn("dịch vụ tính tuyến", fp.commute_answer({}, commute, "drive"))

    def test_answer_says_estimated_travel_time_not_a_measured_route(self):
        commute = {"distanceMeters": 4200.0, "durationSeconds": 900.0, "provider": "OPENROUTESERVICE"}
        answer = fp.commute_answer({}, commute, "drive")
        self.assertIn("thời gian di chuyển ước tính theo", answer)
        self.assertNotIn("tuyến thật", answer)


class HardLimitTests(unittest.TestCase):
    def entries(self):
        return [
            {"id": "over", "route": {"durationSeconds": 1800.0}},
            {"id": "inside", "route": {"durationSeconds": 600.0}},
            {"id": "unknown", "route": None},
        ]

    def test_hard_drops_over_and_unknown(self):
        ordered = cr.rank(self.entries(), 25, "HARD", 3)
        self.assertEqual([e["id"] for e in ordered], ["inside"])

    def test_soft_keeps_unknown_but_last(self):
        ordered = cr.rank(self.entries(), 25, "SOFT", 3)
        self.assertEqual([e["id"] for e in ordered], ["inside", "over", "unknown"])


if __name__ == "__main__":
    unittest.main()
