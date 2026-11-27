import unittest

import httpx
from decimal import Decimal

from unittest.mock import MagicMock, patch

from app.rag.tools import BackendTools, PublishedPropertyRepository, _public_text
from app.rag.config import GroundingError, Settings


class PublicPropertyProjectionTests(unittest.TestCase):
    def test_public_text_redacts_contact_and_internal_markers(self):
        text = _public_text(
            "<b>Liên hệ 0905 123 456 hoặc a@example.com</b> UNVERIFIED TINIX_AI"
        )
        for forbidden in ("0905", "a@example.com", "UNVERIFIED", "TINIX_AI"):
            self.assertNotIn(forbidden, text)

    def test_public_row_never_exposes_private_columns(self):
        pid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        row = {
            "id": pid, "listingCode": "SP001", "title": "<b>Nhà thử</b>",
            "description": "Liên hệ 0905&#32;123 456 hoặc a&#64;example.com",
            "price": Decimal("2000000000"), "areaSqm": Decimal("80"),
            "status": "PUBLISHED", "bedrooms": 3,
            "owner_id": 1, "contact_phone": "0905123456", "contact_email": "a@example.com",
            "uploaded_by": 2, "storage_key": "private/file", "review_reason": "private", "sha256": "hash",
        }
        tools = BackendTools(Settings())
        self.addCleanup(tools.close)
        with patch.object(tools, "_call", return_value=row):
            public = tools.public_property(pid)
        for forbidden in ("owner_id", "contact_phone", "contact_email", "uploaded_by",
                          "storage_key", "review_reason", "sha256"):
            self.assertNotIn(forbidden, public)
        self.assertEqual(public["listingCode"], "SP001")
        self.assertEqual(public["bedrooms"], 3)
        self.assertEqual(public["title"], "Nhà thử")
        self.assertNotIn("0905", public["description"])
        self.assertNotIn("a@example.com", public["description"])

    def test_public_detail_rejects_unpublished_or_wrong_id(self):
        tools = BackendTools(Settings())
        self.addCleanup(tools.close)
        pid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        for row in ({"id": pid, "status": "DRAFT"}, {"id": "different", "status": "PUBLISHED"},
                    {"id": pid, "status": "PUBLISHED", "deletedAt": "2026-01-01T00:00:00Z"},
                    {"id": pid, "status": "PUBLISHED", "expiresAt": "2026-01-01T00:00:00Z"}):
            with self.subTest(row=row), patch.object(tools, "_call", return_value=row):
                with self.assertRaisesRegex(GroundingError, "INVALID_PUBLIC_PROPERTY"):
                    tools.public_property(pid)

    def test_public_recommendation_excludes_private_fields(self):
        tools = BackendTools(Settings())
        self.addCleanup(tools.close)
        card = {"id": "property:x", "title": "Nhà 0905 123 456", "priceVnd": 2000000000, "areaSqm": 80,
                "owner_id": 99, "source": {"kind": "PROPERTY", "recordKey": "x", "storage_key": "private"},
                "qualityStatus": "PLATFORM_PUBLISHED",
                "scoreBreakdown": {"areaFit": 95, "private_note": "private"},
                "amenityEvidence": {"areaId": "public-area", "private_note": "private",
                                    "poiEvidence": [{"name": "School", "category": "SCHOOL", "owner_id": 99}]}}
        with patch.object(tools, "_call", return_value={
            "method": "HEURISTIC_V1_1", "mode": "SAFE", "topProperties": [card],
            "topAreas": [{"district": "Cẩm Lệ", "owner_id": 99}]
        }):
            response = tools.recommend({"budgetVnd": "3000000000"})
        result = response["topProperties"][0]
        self.assertNotIn("owner_id", response["topAreas"][0])
        self.assertEqual(result["scoreBreakdown"], {"areaFit": 95})
        self.assertEqual(result["amenityEvidence"]["poiEvidence"], [{"name": "School", "category": "SCHOOL"}])
        self.assertNotIn("private_note", result["amenityEvidence"])
        self.assertNotIn("owner_id", result)
        self.assertNotIn("storage_key", result["source"])
        self.assertNotIn("0905", result["title"])

    def test_image_requires_public_matching_listing_and_same_property_path(self):
        tools = BackendTools(Settings())
        self.addCleanup(tools.close)
        pid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        image = f"/api/v1/properties/{pid}/images/cover/content"
        foreign = "/api/v1/properties/other/images/cover/content"
        row = {"id": pid, "status": "PUBLISHED", "images": [{"url": foreign}, {"url": image}]}
        with patch.object(tools, "_call", return_value=row):
            self.assertEqual(tools.property_image(pid), image)
        with patch.object(tools, "_call", return_value=dict(row, status="DRAFT")):
            with self.assertRaisesRegex(GroundingError, "INVALID_PUBLIC_PROPERTY"):
                tools.property_image(pid)

    def test_recommendation_rejects_wrong_property_identity_or_ward(self):
        tools = BackendTools(Settings())
        self.addCleanup(tools.close)
        card = {"id": "property:x", "priceVnd": 2000000000, "areaSqm": 80, "ward": "Hòa Thọ Đông",
                "qualityStatus": "PLATFORM_PUBLISHED", "source": {"kind": "PROPERTY", "recordKey": "x"}}
        body = {"method": "HEURISTIC_V1_1", "mode": "SAFE", "topProperties": [card]}
        with patch.object(tools, "_call", return_value=body):
            with self.assertRaisesRegex(GroundingError, "RECOMMENDATION_OUTSIDE_LOCATION"):
                tools.recommend({"budgetVnd": "3000000000", "ward": "Hòa Thọ Tây"})
            card["source"]["recordKey"] = "other"
            with self.assertRaisesRegex(GroundingError, "INVALID_PROPERTY_REFERENCE"):
                tools.recommend({"budgetVnd": "3000000000"})

    def test_nearby_projection_drops_internal_origin_reference(self):
        tools = BackendTools(Settings())
        tools.close()
        pid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        payload = {"propertyId": pid, "radiusMeters": 1000, "distanceType": "STRAIGHT_LINE",
                   "location": {"accuracy": "EXACT_PROPERTY", "reference": "private"},
                   "items": [{"name": "School", "latitude": 16, "longitude": 108,
                              "distanceMeters": 100, "categoryGroups": ["education"], "owner_id": 99}]}
        def reply(request):
            self.assertIsNone(request.headers.get("Authorization"))
            return httpx.Response(200, json=payload)
        with httpx.Client(base_url="http://127.0.0.1:18080", transport=httpx.MockTransport(reply)) as client:
            tools.client = client
            result = tools.property_nearby(pid)
        self.assertNotIn("reference", result["location"])
        self.assertNotIn("owner_id", result["items"][0])
        self.assertEqual(result["items"][0]["categoryGroups"], ["education"])

    def test_sql_view_cross_check_keeps_projection_bounded(self):
        repository = PublishedPropertyRepository(Settings(
            sql_enabled=True, sql_database="smartprop_staging", sql_use_views=True,
            db_user="fixture", db_password="fixture",
        ))
        with patch("pymysql.connect") as connect:
            connection = connect.return_value.__enter__.return_value
            connection.cursor.return_value = MagicMock()
            cursor = connection.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = {"db": "smartprop_staging", "port": 13306, "read_only": 1}
            cursor.fetchall.return_value = [{"id": "property-1", "price": Decimal("2000000000"),
                                              "area_sqm": Decimal("80"), "owner_id": 1}]
            result = repository.lookup(["property-1"])
        self.assertNotIn("owner_id", result[0])
        self.assertEqual(result[0]["area_sqm"], Decimal("80"))
        self.assertEqual(connect.call_args.kwargs["port"], 13306)
        self.assertEqual(connect.call_args.kwargs["init_command"], "SET SESSION TRANSACTION READ ONLY")
        query, params = cursor.execute.call_args.args
        self.assertIn("FROM rag_public_properties", query)
        self.assertIn("status='PUBLISHED' AND deleted_at IS NULL", query)
        self.assertIn("expires_at>UTC_TIMESTAMP(6)", query)
        self.assertIn("id IN (%s)", query)
        self.assertEqual(params, ("property-1",))


if __name__ == "__main__":
    unittest.main()
