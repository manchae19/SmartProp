import unittest

from review_geospatial_candidates import access_claims, street_key


class AccessClaimsTests(unittest.TestCase):
    def test_alley_width_not_area_parcel_frontage_or_alley_number(self):
        result = access_claims('Nhà 2 tầng hẻm 3m đường 2/9, ngang 5m, 50m2')
        self.assertEqual(result['access_type_claim'],'alley_claim')
        self.assertEqual(result['alley_width_claim_m'],[3.0])
        self.assertEqual(result['road_width_claim_m'],[])
        for title in ('Kiệt 266 Trường Chinh, ngang 5m',
                      'Nhà kiệt ô tô, 85m2, ngang 5m',
                      'Nhà kiệt 15m²', 'Nhà kiệt 15m2', 'Nhà kiệt 3m2'):
            self.assertEqual(access_claims(title)['alley_width_claim_m'],[],title)

    def test_road_width_is_separate_from_alley_width(self):
        result = access_claims('Mặt tiền đường 7m5, ngang 6m, nhà 3 tầng')
        self.assertEqual(result['road_width_claim_m'],[7.5])
        self.assertEqual(result['alley_width_claim_m'],[])
        self.assertEqual(result['access_type_claim'],'frontage_claim')

    def test_person_street_names_do_not_create_alley(self):
        for title in ('Bán nhà mặt tiền Võ Văn Kiệt', 'Nhà đường Lý Thường Kiệt'):
            self.assertNotEqual(access_claims(title)['access_type_claim'],'alley_claim')
        self.assertEqual(access_claims('Nhà kiệt Lý Thường Kiệt')['access_type_claim'],'alley_claim')

    def test_near_frontage_is_not_frontage(self):
        self.assertEqual(access_claims('Nhà 2 tầng kiệt Trần Cao Vân, sát mặt tiền')['access_type_claim'],'alley_claim')
        result = access_claims('Bán nhà sát mặt tiền giao Nguyễn Văn Linh')
        self.assertEqual(result['access_type_claim'],'unknown')
        self.assertIn('near_frontage_not_frontage',result['flags'])
        self.assertEqual(access_claims('Nhà mặt tiền trong kiệt')['access_type_claim'],'needs_review')

    def test_car_claims_are_explicit_and_negation_safe(self):
        self.assertEqual(access_claims('Kiệt ôtô trải nhựa Dương Khuê')['car_access_claim'],'access_claim')
        self.assertEqual(access_claims('Nhà kiệt không ô tô vào được')['car_access_claim'],'no_access_claim')
        self.assertEqual(access_claims('Nhà không phải kiệt ô tô')['car_access_claim'],'needs_review')
        self.assertEqual(access_claims('Nhà kiệt rộng 5m')['car_access_claim'],'unknown')
        self.assertEqual(access_claims('Nhà kiệt cách đường ô tô 20m')['car_access_claim'],'unknown')

    def test_missing_abbreviation_and_landmark_are_not_measurements(self):
        result = access_claims('NHÀ 3 TẦNG MT AN HẢI GẦN BỆNH VIỆN')
        self.assertEqual(result['access_type_claim'],'unknown')
        self.assertIn('MT_abbreviation_not_auto_classified',result['flags'])
        self.assertIn('amenity_or_landmark_mention_not_measured',result['flags'])
        self.assertEqual(access_claims('CHÍNH CHỦ')['access_type_claim'],'unknown')
        self.assertEqual(street_key('Đường Điện Biên Phủ'),'dien bien phu')


if __name__ == '__main__':
    unittest.main()
