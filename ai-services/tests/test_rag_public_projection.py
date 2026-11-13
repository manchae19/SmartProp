import unittest
from decimal import Decimal

from app.rag.tools import PublishedPropertyRepository, _public_text
from app.rag.config import Settings


class PublicPropertyProjectionTests(unittest.TestCase):
    def test_public_text_redacts_contact_and_internal_markers(self):
        text = _public_text(
            "<b>Liên hệ 0905 123 456 hoặc a@example.com</b> UNVERIFIED TINIX_AI"
        )
        for forbidden in ("0905", "a@example.com", "UNVERIFIED", "TINIX_AI"):
            self.assertNotIn(forbidden, text)

    def test_public_row_never_exposes_private_columns(self):
        repository = PublishedPropertyRepository(Settings())
        row = {
            "id": "property-1", "listing_code": "SP001", "title": "Nhà thử",
            "description": "Mô tả", "price": Decimal("2000000000"), "area_sqm": Decimal("80"),
            "property_type": "HOUSE", "transaction_type": "SALE", "district": "Hải Châu",
            "ward": "Hải Châu 1", "address": "Địa chỉ", "city": "Đà Nẵng",
            "bedrooms": 3, "bathrooms": 2, "floor": "2", "direction": "Đông",
            "declared_amenities": "[]", "coordinate_srid": 4326,
            "latitude": 16.0, "longitude": 108.0, "project_name": None,
        }
        public = repository._public_row(row, [], None)
        for forbidden in ("owner_id", "contact_phone", "contact_email", "uploaded_by",
                          "storage_key", "review_reason", "sha256"):
            self.assertNotIn(forbidden, public)
        self.assertEqual(public["listing_code"], "SP001")
        self.assertEqual(public["bedrooms"], 3)


if __name__ == "__main__":
    unittest.main()
