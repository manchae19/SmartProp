"""Unit tests for TiniX Location Resolution & Address Confidence Audit (Step 19.4.1A)."""
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from tinix_location_resolution import TinixLocationResolver, assert_readonly_sql, normalize_nfc


class TinixLocationResolutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.resolver = TinixLocationResolver()

    def _base_row(self, **overrides):
        base = {
            "internal_id": "0" * 64,
            "name": "",
            "description": "",
            "province_name": "Đà Nẵng",
            "district_name": None,
            "ward_name": None,
            "street_name": None,
            "project_name": None,
            "normalized_type": "HOUSE",
            "district": None,
            "ward": None,
            "floor_count": 3.0,
            "road_width": None,
            "quality_status": "HYBRID_ELIGIBLE_RESEARCH",
            "quality_rule_version": "TINIX_RESEARCH_V1",
        }
        base.update(overrides)
        return base

    # 1. House number + street
    def test_01_house_number_and_street(self) -> None:
        row = self._base_row(
            name="Bán nhà mặt tiền số 72 Hàm Nghi, Phường Thạc Gián, Quận Thanh Khê",
            description="Nhà 3 tầng kiên cố tại 72 Hàm Nghi, trung tâm Thanh Khê, Đà Nẵng.",
            district_name="Thanh Khê",
            ward_name="Thạc Gián",
            street_name="Hàm Nghi",
        )
        res = self.resolver.resolve_record(row)
        self.assertEqual(res["locationPrecision"], "STREET")
        self.assertEqual(res["normalizedStreet"], "Hàm Nghi")
        self.assertEqual(res["houseNumber"], "72")
        self.assertTrue(res["isAddressGeocodeCandidate"])
        self.assertFalse(res["canCalculatePropertyDistance"])
        self.assertIsNone(res["resolvedLatitude"])
        self.assertIsNone(res["resolvedLongitude"])
        self.assertGreaterEqual(res["locationConfidence"], 0.85)
        self.assertLessEqual(res["locationConfidence"], 0.95)
        # Preserve original fields
        self.assertEqual(res["originalStreet"], "Hàm Nghi")
        self.assertEqual(res["qualityStatus"], "HYBRID_ELIGIBLE_RESEARCH")

    def test_01b_alley_slash_house_number(self) -> None:
        row = self._base_row(
            name="Bán nhà K146/12 Lê Đình Dương, Phường Phước Ninh, Hải Châu",
            description="Nhà đẹp kiệt ô tô K146/12 Lê Đình Dương, gần cầu Rồng.",
            district_name="Hải Châu",
            ward_name="Phước Ninh",
            street_name="Lê Đình Dương",
        )
        res = self.resolver.resolve_record(row)
        self.assertEqual(res["locationPrecision"], "STREET")
        self.assertEqual(res["normalizedStreet"], "Lê Đình Dương")
        self.assertEqual(res["alleyNumber"], "K146")
        self.assertEqual(res["houseNumber"], "K146/12")
        self.assertTrue(res["isAddressGeocodeCandidate"])

    # 2. Street without house number (including numbered streets & alley-only without house number)
    def test_02_street_without_house_number(self) -> None:
        row = self._base_row(
            name="Bán đất mặt tiền đường Hòa Minh 21, Liên Chiểu, Đà Nẵng",
            description="Đất sạch đẹp mặt tiền Hòa Minh 21, kiệt 146 Tôn Đức Thắng đi vào.",
            district_name="Liên Chiểu",
            ward_name="Hòa Minh",
            street_name="Hòa Minh 21",
            normalized_type="LAND",
        )
        res = self.resolver.resolve_record(row)
        self.assertEqual(res["locationPrecision"], "STREET")
        self.assertEqual(res["normalizedStreet"], "Hòa Minh 21")
        self.assertIsNone(res["houseNumber"])  # "21" is part of street name, NOT house number!
        self.assertFalse(res["isAddressGeocodeCandidate"])

        row_alley = self._base_row(
            name="Bán nhà kiệt 146 Lê Đình Dương, Hải Châu",
            description="Kiệt rộng 4m thông thoáng.",
            district_name="Hải Châu",
            ward_name="Phước Ninh",
            street_name="Lê Đình Dương",
        )
        res_alley = self.resolver.resolve_record(row_alley)
        self.assertEqual(res_alley["locationPrecision"], "STREET")
        self.assertEqual(res_alley["alleyNumber"], "K146")
        self.assertIsNone(res_alley["houseNumber"])
        self.assertFalse(res_alley["isAddressGeocodeCandidate"])

    # 3. Ward only
    def test_03_ward_only(self) -> None:
        row = self._base_row(
            name="Bán nhà 3 tầng tại Phường An Hải Bắc, Quận Sơn Trà, Đà Nẵng",
            description="Khu dân cư an ninh, dân trí cao, sổ hồng chính chủ.",
            district_name="Sơn Trà",
            ward_name="An Hải Bắc",
            street_name=None,
        )
        res = self.resolver.resolve_record(row)
        self.assertEqual(res["locationPrecision"], "WARD")
        self.assertEqual(res["resolvedDistrictHistorical"], "Sơn Trà")
        self.assertEqual(res["resolvedWardHistorical"], "An Hải Bắc")
        self.assertEqual(res["resolvedUnitNq1659"], "Phường An Hải")
        self.assertIsNone(res["normalizedStreet"])
        self.assertIsNone(res["resolvedLatitude"])
        self.assertFalse(res["canCalculatePropertyDistance"])
        self.assertTrue(res["canAnalyzeAreaAmenities"])
        self.assertEqual(res["amenityCapability"], "AREA_LEVEL")

    # 4. District only
    def test_04_district_only(self) -> None:
        row = self._base_row(
            name="Bán lô đất đẹp tại Quận Ngũ Hành Sơn, TP Đà Nẵng",
            description="Đất vuông vức 100m2, pháp lý sổ đỏ đầy đủ.",
            district_name="Ngũ Hành Sơn",
            ward_name="",
            street_name="",
            normalized_type="LAND",
        )
        res = self.resolver.resolve_record(row)
        self.assertEqual(res["locationPrecision"], "DISTRICT")
        self.assertEqual(res["resolvedDistrictHistorical"], "Ngũ Hành Sơn")
        self.assertIsNone(res["resolvedWardHistorical"])
        self.assertEqual(res["resolvedUnitNq1659"], "Phường Ngũ Hành Sơn")
        self.assertIsNone(res["resolvedLatitude"])
        self.assertEqual(res["amenityCapability"], "AREA_LEVEL")
        self.assertEqual(res["amenityGranularity"], "DISTRICT_MACRO_ONLY")

    # 5. Historical / 2025 administrative toponyms & split boundary NEEDS_MAPPING
    def test_05_historical_and_2025_toponyms(self) -> None:
        # Pre-2025 "Phường An Hải Đông" inside NQ 1251 "An Hải Nam" -> consistent, disambiguates historical ward!
        row_pre = self._base_row(
            name="Bán nhà Phường An Hải Đông, Quận Sơn Trà",
            description="Nhà đẹp trung tâm Phường An Hải Đông cũ.",
            district_name="Sơn Trà",
            ward_name="An Hải Nam",
        )
        res_pre = self.resolver.resolve_record(row_pre)
        self.assertEqual(res_pre["locationPrecision"], "WARD")
        self.assertEqual(res_pre["resolvedWardHistorical"], "An Hải Đông")
        self.assertEqual(res_pre["resolvedWardNq1251"], "An Hải Nam")
        self.assertEqual(res_pre["resolvedUnitNq1659"], "Phường An Hải")
        self.assertNotIn("ADDRESS_CONFLICT", res_pre["locationIssues"])
        self.assertNotIn("NEEDS_MAPPING", res_pre["locationIssues"])

        # Post-07/2025 NQ 1659 "Xã Hòa Vang" with structured "Hòa Phú" -> consistent, NOT conflict!
        row_1659 = self._base_row(
            name="Bán đất nền Xã Hòa Vang, TP Đà Nẵng",
            description="Đất thổ cư tại Hòa Phú, Hòa Vang.",
            district_name="Hòa Vang",
            ward_name="Hòa Phú",
            normalized_type="LAND",
        )
        res_1659 = self.resolver.resolve_record(row_1659)
        self.assertEqual(res_1659["locationPrecision"], "WARD")
        self.assertEqual(res_1659["resolvedUnitNq1659"], "Xã Hòa Vang")
        self.assertNotIn("ADDRESS_CONFLICT", res_1659["locationIssues"])

        # Split commune "Hòa Liên" under NQ 1659 -> NEEDS_MAPPING, never force 1:1 post-2025 ward!
        row_split = self._base_row(
            name="Bán đất Xã Hòa Liên, Huyện Hòa Vang",
            description="Đất sạch sổ đỏ chính chủ.",
            district_name="Hòa Vang",
            ward_name="Hòa Liên",
            normalized_type="LAND",
        )
        res_split = self.resolver.resolve_record(row_split)
        self.assertEqual(res_split["locationPrecision"], "WARD")
        self.assertIsNone(res_split["resolvedUnitNq1659"])
        self.assertIn("NEEDS_MAPPING", res_split["locationIssues"])

    # 6. Marketing / nearby amenity addresses (Category B & Category D)
    def test_06_marketing_and_nearby_landmarks_rejected(self) -> None:
        # "Bán nhà gần biển Mỹ Khê", "Nhà cách cầu Rồng 1 km" -> must NOT become street/exact location
        row_mkt = self._base_row(
            name="Bán nhà gần biển Mỹ Khê, Quận Sơn Trà",
            description="Nhà cách cầu Rồng 1 km, cách đường Võ Văn Kiệt 200m, đi bộ ra biển.",
            district_name="Sơn Trà",
            ward_name="Phước Mỹ",
            street_name=None,
        )
        res_mkt = self.resolver.resolve_record(row_mkt)
        self.assertEqual(res_mkt["locationPrecision"], "WARD")
        self.assertIsNone(res_mkt["normalizedStreet"])
        self.assertIn("LOCATION_FROM_MARKETING_TEXT", res_mkt["locationIssues"])

        # Real TiniX trap: structured street_name="Vành Đai" extracted from "Gần Đường Vành Đai"
        row_vanh_dai = self._base_row(
            name="Bán đất Hòa Phước, Gần Đường Vành Đai",
            description="Cách đường Vành Đai Nam Kỳ Khởi Nghĩa chỉ 200m.",
            district_name="Hòa Vang",
            ward_name="Hòa Phước",
            street_name="Vành Đai",
            normalized_type="LAND",
        )
        res_vd = self.resolver.resolve_record(row_vanh_dai)
        self.assertEqual(res_vd["locationPrecision"], "WARD")
        self.assertIsNone(res_vd["normalizedStreet"])
        self.assertIn("LOCATION_FROM_MARKETING_TEXT", res_vd["locationIssues"])

        # Category D: other project used for marketing ("gần FPT City")
        row_proj_d = self._base_row(
            name="Bán đất dân cư Hòa Hải gần FPT City Đà Nẵng",
            description="Lô đất sát FPT City Đà Nẵng, tiện ích đầy đủ.",
            district_name="Ngũ Hành Sơn",
            ward_name="Hòa Hải",
            project_name="FPT City Đà Nẵng",
            normalized_type="LAND",
        )
        res_pd = self.resolver.resolve_record(row_proj_d)
        self.assertIsNone(res_pd["matchedProject"])
        self.assertIn("LOCATION_FROM_MARKETING_TEXT", res_pd["locationIssues"])

    # 7. Broker office contact address (Category C)
    def test_07_broker_contact_address_ignored(self) -> None:
        row_broker = self._base_row(
            name="Bán đất Phường Hòa Hải, Quận Ngũ Hành Sơn",
            description="Đất đẹp vuông vức. Liên hệ văn phòng tại Quận Hải Châu, số 120 Nguyễn Văn Linh để xem sổ.",
            district_name="Ngũ Hành Sơn",
            ward_name="Hòa Hải",
            street_name=None,
            normalized_type="LAND",
        )
        res = self.resolver.resolve_record(row_broker)
        self.assertEqual(res["locationPrecision"], "WARD")
        self.assertEqual(res["resolvedDistrictHistorical"], "Ngũ Hành Sơn")
        self.assertIsNone(res["normalizedStreet"])
        self.assertNotIn("ADDRESS_CONFLICT", res["locationIssues"])

    # 8. Conflicting addresses vs legitimate 2-frontage corner lots
    def test_08_conflicting_addresses_and_corner_lots(self) -> None:
        # True district conflict -> UNKNOWN + ADDRESS_CONFLICT
        row_dist_conf = self._base_row(
            name="Bán nhà mặt tiền tại Phường Hòa Minh, Quận Liên Chiểu, Đà Nẵng",
            description="Nhà 3 tầng tại Phường Hòa Minh, Quận Liên Chiểu.",
            district_name="Hải Châu",
            ward_name="Thạch Thang",
            street_name=None,
        )
        res_dc = self.resolver.resolve_record(row_dist_conf)
        self.assertEqual(res_dc["locationPrecision"], "UNKNOWN")
        self.assertIn("ADDRESS_CONFLICT", res_dc["locationIssues"])
        self.assertFalse(res_dc["canAnalyzeAreaAmenities"])
        self.assertEqual(res_dc["amenityCapability"], "INSUFFICIENT_DATA")

        # True ward conflict inside same district -> downgraded to DISTRICT + ADDRESS_CONFLICT
        row_ward_conf = self._base_row(
            name="Bán nhà Phường Mân Thái, Quận Sơn Trà",
            description="Nhà chính chủ tại Phường Mân Thái, Quận Sơn Trà.",
            district_name="Sơn Trà",
            ward_name="Phước Mỹ",
        )
        res_wc = self.resolver.resolve_record(row_ward_conf)
        self.assertEqual(res_wc["locationPrecision"], "DISTRICT")
        self.assertIn("ADDRESS_CONFLICT", res_wc["locationIssues"])

        # Legitimate corner lot (2 mặt tiền) -> NOT conflict!
        row_corner = self._base_row(
            name="Bán nhà lô góc 2 mặt tiền Võ Văn Kiệt và Hồ Nghinh, Sơn Trà",
            description="Siêu phẩm góc 2MT kinh doanh sầm uất.",
            district_name="Sơn Trà",
            ward_name="Phước Mỹ",
            street_name="Võ Văn Kiệt",
        )
        res_corner = self.resolver.resolve_record(row_corner)
        self.assertEqual(res_corner["locationPrecision"], "STREET")
        self.assertEqual(res_corner["normalizedStreet"], "Võ Văn Kiệt")
        self.assertNotIn("ADDRESS_CONFLICT", res_corner["locationIssues"])

    # 9. Non-existent / insufficient / special territory (Hoàng Sa, bare road-width "5", unverified geocode)
    def test_09_hoang_sa_corrupted_street_and_unverified_geocode(self) -> None:
        # Exact forensic reproduction of TiniX Hoàng Sa record 39d31d34...
        row_hs = self._base_row(
            internal_id="39d31d348d37ba9911f506dce085c896f687ecf1b93f1e61ad2904d7845a0cdf",
            name="Bán đất mặt tiền đường Hoàng Sa, cách biển Thuận An 100m, giá 14 triệu/m2",
            description="Đất biển diện tích 115m2 mặt tiền đường Hoàng Sa, cách biển Thuận An 100m.",
            district_name="Hoàng Sa",
            ward_name=None,
            street_name=None,
            normalized_type="LAND",
        )
        res_hs = self.resolver.resolve_record(row_hs)
        self.assertEqual(res_hs["locationPrecision"], "UNKNOWN")
        self.assertIn("NON_RESIDENTIAL_SPECIAL_TERRITORY", res_hs["locationIssues"])
        self.assertIn("SOURCE_LOCATION_INCONSISTENT", res_hs["locationIssues"])
        self.assertFalse(res_hs["canAnalyzeAreaAmenities"])
        self.assertEqual(res_hs["amenityCapability"], "INSUFFICIENT_DATA")

        # Corrupted bare integer street_name="5" from road width "đường 5,5m" -> rejected to WARD
        row_bare5 = self._base_row(
            name="Bán nhà đường 5,5m Phường Hòa Minh, Liên Chiểu",
            description="Nhà đẹp đường 5,5m lề 3m.",
            district_name="Liên Chiểu",
            ward_name="Hòa Minh",
            street_name="5",
        )
        res_b5 = self.resolver.resolve_record(row_bare5)
        self.assertEqual(res_b5["locationPrecision"], "WARD")
        self.assertIsNone(res_b5["normalizedStreet"])
        self.assertIn("SOURCE_LOCATION_INCONSISTENT", res_b5["locationIssues"])

        # Unverified geocode must NOT upgrade to HIGH or EXACT
        row_ungeo = self._base_row(
            name="Bán nhà số 72 Hàm Nghi, Thanh Khê",
            district_name="Thanh Khê",
            ward_name="Thạc Gián",
            street_name="Hàm Nghi",
            verified_latitude=16.061,
            verified_longitude=108.211,
            verified_geocode_level="UNVERIFIED_GEOCODE",
        )
        res_ungeo = self.resolver.resolve_record(row_ungeo)
        self.assertEqual(res_ungeo["locationPrecision"], "STREET")
        self.assertIsNone(res_ungeo["resolvedLatitude"])
        self.assertIn("UNVERIFIED_GEOCODE", res_ungeo["locationIssues"])

    def test_10_unicode_and_readonly_sql_guard(self) -> None:
        # NFD decomposed street -> NFC normalized while preserving originalStreet
        nfd_street = "Trương Chi\u0301 Cương"
        self.assertEqual(normalize_nfc(nfd_street), "Trương Chí Cương")
        # Regression: Huỳnh, Thoại, Quý must NOT be corrupted by tone normalization
        self.assertEqual(normalize_nfc("Huỳnh Tịnh Của"), "Huỳnh Tịnh Của")
        self.assertEqual(normalize_nfc("Thoại Ngọc Hầu"), "Thoại Ngọc Hầu")
        self.assertEqual(normalize_nfc("Hòa Quý"), "Hòa Quý")
        self.assertEqual(normalize_nfc("Hoà Quý"), "Hòa Quý")
        assert_readonly_sql("SET SESSION TRANSACTION READ ONLY")
        assert_readonly_sql("SELECT COUNT(*) FROM tinix_dataset_records")
        with self.assertRaises(PermissionError):
            assert_readonly_sql("UPDATE tinix_dataset_records SET ward='X'")
        with self.assertRaises(PermissionError):
            assert_readonly_sql("DELETE FROM tinix_dataset_records")

    def test_11_pilot_false_positive_regressions(self) -> None:
        # 1. Multi-sentence broker signature block at end of description (Category C across periods)
        row_footer = self._base_row(
            name="Bán nhà 3 tầng đường Đô Đốc Lân, Hòa Xuân, Cẩm Lệ",
            description=(
                "Nhà đẹp thiết kế hiện đại tại Đô Đốc Lân, Hòa Xuân. "
                "--- Liên hệ ngay SĐT: [phone_number] gặp em Minh. "
                "Công ty BĐS Hàng Hiệu Hoàng Phương. Địa chỉ: 383 Trần Hưng Đạo, An Hải Trung, Sơn Trà."
            ),
            district_name="Cẩm Lệ",
            ward_name="Hòa Xuân",
            street_name="Đô Đốc Lân",
        )
        res_footer = self.resolver.resolve_record(row_footer)
        self.assertEqual(res_footer["locationPrecision"], "STREET")
        self.assertEqual(res_footer["resolvedDistrictHistorical"], "Cẩm Lệ")
        self.assertEqual(res_footer["normalizedStreet"], "Đô Đốc Lân")
        self.assertIsNone(res_footer["houseNumber"])  # Broker office "383" must NOT leak!
        self.assertNotIn("ADDRESS_CONFLICT", res_footer["locationIssues"])

        # 2. Comma-separated connectivity list ("dễ dàng kết nối Liên Chiểu, Hải Châu") -> Category B
        row_conn = self._base_row(
            name="Bán đất Hòa Sơn, Hòa Vang giá đầu tư",
            description="Vị trí đẹp, giao thông thuận tiện dễ dàng kết nối Liên Chiểu, Hải Châu, sân bay.",
            district_name="Hòa Vang",
            ward_name="Hòa Sơn",
            normalized_type="LAND",
        )
        res_conn = self.resolver.resolve_record(row_conn)
        self.assertEqual(res_conn["locationPrecision"], "WARD")
        self.assertEqual(res_conn["resolvedDistrictHistorical"], "Hòa Vang")
        self.assertNotIn("ADDRESS_CONFLICT", res_conn["locationIssues"])

        # 3. English project name containing "Lake View" ("Hoàng Anh Gia Lai Lake View 72 Hàm Nghi")
        row_lv = self._base_row(
            name="Bán căn hộ 93,5m2 Hoàng Anh Gia Lai Lake View 72 Hàm Nghi, Thanh Khê",
            description="Căn hộ tầng trung thoáng mát tại chung cư Hoàng Anh Gia Lai Lake View 72 Hàm Nghi.",
            district_name="Thanh Khê",
            ward_name="Thạc Gián",
            street_name="Hàm Nghi",
            normalized_type="APARTMENT",
        )
        res_lv = self.resolver.resolve_record(row_lv)
        self.assertEqual(res_lv["locationPrecision"], "STREET")
        self.assertEqual(res_lv["normalizedStreet"], "Hàm Nghi")
        self.assertEqual(res_lv["houseNumber"], "72")
        self.assertTrue(res_lv["isAddressGeocodeCandidate"])
        self.assertNotIn("LOCATION_FROM_MARKETING_TEXT", res_lv["locationIssues"])

        # 4. Alley width in meters ("kiệt 3m", "Kiệt 5m") must NOT become alleyNumber="K3M"/"K5M"
        row_width = self._base_row(
            name="Bán nhà kiệt 3m đường Hải Phòng, Thanh Khê",
            description="Kiệt 5m Hồ Xuân Hương gần đó, nhà hiện tại kiệt 3m đường Hải Phòng sạch đẹp.",
            district_name="Thanh Khê",
            ward_name="Tân Chính",
            street_name="Hải Phòng",
        )
        res_width = self.resolver.resolve_record(row_width)
        self.assertEqual(res_width["locationPrecision"], "STREET")
        self.assertIsNone(res_width["alleyNumber"])
        self.assertIsNone(res_width["houseNumber"])

        # 5. Đà Nẵng streets sharing names with Quảng Nam districts/wards ("Núi Thành", "Cẩm Nam 1")
        row_nt = self._base_row(
            name="Nhà mặt phố tại Núi Thành, Phường Hòa Cường Bắc, Hải Châu",
            description="Nhà 4 tầng kinh doanh tốt mặt tiền Núi Thành.",
            district_name="Hải Châu",
            ward_name="Hòa Cường Bắc",
            street_name="Núi Thành",
        )
        res_nt = self.resolver.resolve_record(row_nt)
        self.assertEqual(res_nt["locationPrecision"], "STREET")
        self.assertEqual(res_nt["normalizedStreet"], "Núi Thành")
        self.assertNotIn("ADDRESS_CONFLICT", res_nt["locationIssues"])

        # 6. Attested numbered street stem ("MT Giáng Hương 6", "đường Hói Kiểng 26")
        row_num_stem = self._base_row(
            name="Bán đất MT Giáng Hương 6, Hòa Quý, Ngũ Hành Sơn",
            description="Lô đất sạch mặt tiền đường Giáng Hương 6, khu đô thị Nam Hòa Xuân.",
            district_name="Ngũ Hành Sơn",
            ward_name="Hòa Quý",
            street_name=None,
            normalized_type="LAND",
        )
        res_num_stem = self.resolver.resolve_record(row_num_stem)
        self.assertEqual(res_num_stem["locationPrecision"], "STREET")
        self.assertEqual(res_num_stem["normalizedStreet"], "Giáng Hương 6")
        self.assertIsNone(res_num_stem["houseNumber"])

        # 7. "tại <house_number> <Street>" without "đường/số" & post-07/2025 "Hòa Liên - Liên Chiểu" NQ 1659 merge
        row_ton_dan = self._base_row(
            name="Chào đón bạn đến với ngôi nhà tuyệt vời tại 1014 Tôn Đản",
            description="Ngôi nhà tuyệt vời tại 1014 Tôn Đản, Cẩm Lệ, Đà Nẵng!",
            district_name="Cẩm Lệ",
            ward_name=None,
            street_name=None,
        )
        res_td = self.resolver.resolve_record(row_ton_dan)
        self.assertEqual(res_td["locationPrecision"], "STREET")
        self.assertEqual(res_td["normalizedStreet"], "Tôn Đản")
        self.assertEqual(res_td["houseNumber"], "1014")

        row_hl_lc = self._base_row(
            name="Chính chủ gửi bán lô Đất Tdc Hoà Liên 5- Liên Chiểu - Đà Nẵng",
            description="Chính chủ gửi bán lô Đất Tdc Hoà Liên 5- Liên Chiểu - Đà Nẵng. Vị trí đối diện công viên.",
            district_name="Hòa Vang",
            ward_name="Hòa Liên",
            street_name=None,
            normalized_type="LAND",
        )
        res_hl = self.resolver.resolve_record(row_hl_lc)
        self.assertEqual(res_hl["locationPrecision"], "STREET")
        self.assertEqual(res_hl["normalizedStreet"], "Hòa Liên 5")
        self.assertEqual(res_hl["resolvedDistrictHistorical"], "Hòa Vang")
        self.assertEqual(res_hl["resolvedWardHistorical"], "Hòa Liên")
        self.assertEqual(res_hl["resolvedUnitNq1659"], "Phường Liên Chiểu")
        self.assertNotIn("ADDRESS_CONFLICT", res_hl["locationIssues"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
