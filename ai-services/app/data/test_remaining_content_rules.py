import unittest
import remaining_content_rules as rules


class ContentReviewTests(unittest.TestCase):
    def sample(self,description,price=4800,area=60):
        row=dict(source='cafeland',title='Bán nhà 3 tầng',category='Nhà ở',price_million=str(price),
                 area_sqm=str(area),district='',pipeline_review_codes='',review_decision='')
        evidence=dict(identity_verified=True,structure_verified=True,sale_verified=True,
            source_category='ban-nha-rieng',category='Nhà ở',price_million=price,area_sqm=area,
            address_raw='Đà Nẵng',description=description,flags=[])
        return row,evidence

    def test_compound_price_not_false_conflict(self):
        row,evidence=self.sample('Bán nhà 3 tầng. DT: 60m2. Giá bán: 4 tỷ 800 có thương lượng.')
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'keep')

    def test_land_and_floor_areas_are_distinct(self):
        row,evidence=self.sample('Bán nhà 3 tầng. Diện tích: Đất 100m2. Diện tích sử dụng: 270m2. Giá: 4,8 tỷ.',area=100)
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'keep')

    def test_real_unqualified_area_conflict_stays_pending(self):
        row,evidence=self.sample('Bán nhà. Diện tích: 93,6m2. Giá 4,8 tỷ.',area=96.3)
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'pending')

    def test_partial_price_stays_pending(self):
        row,evidence=self.sample('Bán nhà. Giá từ 4,8 tỷ. Trả trước 800 triệu.')
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'pending')

    def test_unverified_identity_never_approved(self):
        row,evidence=self.sample('Bán nhà 3 tầng. Giá 4,8 tỷ.')
        evidence['identity_verified']=False
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'pending')

    def test_broker_footer_not_category_proof(self):
        row,evidence=self.sample('Thông tin liên hệ: Tư vấn bất động sản nhà phố. Hãy nói nhu cầu của bạn.')
        self.assertIsNone(rules.actual_asset_proof(row,evidence))

    def test_future_house_construction_not_existing_house(self):
        row,evidence=self.sample('Lô đất thích hợp xây nhà đẹp, giá 4,8 tỷ.')
        self.assertIsNone(rules.actual_asset_proof(row,evidence))
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'pending')

    def test_compound_price_does_not_capture_area_as_million(self):
        text,fixes=rules.price_text('Giá 4 tỷ 800 m2 đất.')
        self.assertEqual(fixes,[])

    def test_dtsd_not_land_area(self):
        row,evidence=self.sample('Bán nhà. Diện tích đất: 60m2. DTSD: 180m2. Giá 4,8 tỷ.')
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'keep')

    def test_future_rental_configuration_not_current_building(self):
        row,evidence=self.sample('Bán nhà 3 tầng. Phương án xây mới: Quy mô: 6 tầng. Công năng: 11 phòng căn hộ khép kín. Giá 4,8 tỷ.')
        self.assertNotEqual(rules.evaluate(row,evidence)['decision'],'exclude')

    def test_existing_whole_rental_building_outside_scope(self):
        row,evidence=self.sample('Quy mô: 6 tầng kiên cố. Công năng: 11 phòng căn hộ khép kín. Giá bán 4,8 tỷ.')
        self.assertEqual(rules.evaluate(row,evidence)['decision'],'exclude')

    def test_listing_locality_must_reconcile_with_source_address(self):
        row,evidence=self.sample('BÁN NHÀ PHỐ TRUNG TÂM TAM QUAN. Giá: 4 tỷ 800.')
        result=rules.evaluate(row,evidence)
        self.assertEqual(result['decision'],'pending')
        self.assertIn('content_location_not_reconciled',result['remaining_codes'])

    def test_real_cached_source_cases(self):
        import json
        from training_v3_common import BASE,read
        source={r['record_key']:r for r in read(BASE/'processed/remaining_4772_review/runs/6bbaf88bdc2149d5/needs_review.csv')}
        evidence=json.loads((BASE/'processed/collection_source_review/parsed_evidence.json').read_text(encoding='utf-8'))
        for key in ['cafeland:3145191','cafeland:3145216','cafeland:3146698']:
            with self.subTest(key=key):
                self.assertEqual(rules.previous.decide(source[key],evidence[key])[0],'pending')
                self.assertEqual(rules.evaluate(source[key],evidence[key])['decision'],'keep')


if __name__=='__main__':
    unittest.main()
