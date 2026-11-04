"""Recovery regression cases are isolated fixtures, never persisted as listings."""
import copy
import unittest
from decimal import Decimal
from unittest.mock import patch
import recovery_source_rules as r
import recover_manual_candidates as batch

class MoneyScopeTest(unittest.TestCase):
    def test_vietnamese_remainder_is_not_lost(self):
        for text,expected in [('Giá bán: 1 tỷ 850',1850),('Giá: 3 tỷ 450',3450),('Giá: 4 tỷ 750',4750),('3 tỷ 5',3500),('3 tỷ 500 triệu',3500),('3 tỷ 450tr',3450)]:
            self.assertEqual(Decimal(expected),r.money_mentions(text)[0]['amount_million'])

    def test_area_rooms_phones_or_ambiguous_suffix_are_not_money_remainders(self):
        for text in ['Giá 3 tỷ 100m2','Giá 3 tỷ 5 phòng','Giá 3 tỷ 3 tầng','Giá 3 tỷ 0123456789','Giá 3 tỷ 12']:
            self.assertEqual(Decimal(3000),r.money_mentions(text)[0]['amount_million'])

    def test_bound_downpayment_rental_and_unit_are_distinct(self):
        cases=[('Phân khúc giá tầm 1 tỷ','approximate_or_bound'),('Chỉ cần 400tr có nhà','partial_or_starting'),('30 triệu/1 tháng','rental_income'),('Giá 80 triệu/m²','unit_price')]
        for text,kind in cases:self.assertEqual(kind,r.money_mentions(text)[0]['kind'])

class SourceRecoveryTest(unittest.TestCase):
    def fixture(self,description,area='57',price='12500'):
        row=dict(source='cafeland',title='Bán nhà Lý Thường Kiệt',category='Nhà ở',district='Hải Châu',price_million=price,area_sqm=area,review_decision='pending',pipeline_review_codes='')
        evidence=dict(title=row['title'],description=description,address_raw='Hải Châu, Đà Nẵng',category='Nhà ở',source_category='ban-nha-rieng',price_raw='12 tỷ 500 triệu',area_raw=area+'m2',price_million=float(price),area_sqm=float(area),sale_verified=True,structure_verified=True,identity_verified=True,flags=[])
        return row,evidence

    def test_precise_land_area_and_floor_area_stay_separate(self):
        row,e=self.fixture('Bán nhà Hải Châu Đà Nẵng. Diện tích đất:57,1m²; DTSD:250m²; DT xây dựng:199,5m². Giá bán:12,5 tỷ.')
        old=copy.deepcopy((row,e));x=r.resolve_source(row,e)
        self.assertEqual('57.1',x['values']['area_sqm'])
        self.assertNotIn('description_area_needs_review',x['remaining_flags'])
        self.assertNotIn('prior_pending_requires_explicit_resolution',x['remaining_flags'])
        self.assertEqual((row,e),old)
        self.assertIn('LAND',{a['basis'] for a in x['area_facts']});self.assertIn('FLOOR',{a['basis'] for a in x['area_facts']})

    def test_large_area_conflict_multiple_assets_and_uncorroborated_location_stay_open(self):
        row,e=self.fixture('Diện tích đất:80m². Giá bán:12,5 tỷ. Hải Châu, Đà Nẵng.')
        x=r.resolve_source(row,e);self.assertEqual('57',x['values']['area_sqm']);self.assertIn('description_area_needs_review',x['remaining_flags'])
        row,e=self.fixture('Bán 2 căn nhà. Diện tích:57,1m². Giá:12,5 tỷ. Hải Châu, Đà Nẵng.')
        x=r.resolve_source(row,e);self.assertFalse(x['changes']);self.assertIn('multiple_assets_or_inventory_context',x['remaining_flags'])
        row,e=self.fixture('Diện tích:57,1m². Giá:12,5 tỷ. Trung tâm một địa bàn khác.')
        x=r.resolve_source(row,e);self.assertIn('SOURCE_LOCATION_CORROBORATION_MISSING',x['remaining_flags'])

    def test_title_only_unit_price_never_generates_a_total(self):
        row,e=self.fixture('Thông tin dự án, liên hệ nhận chính sách.',area='67',price='80')
        row['title']='Căn hộ80 triệu/m²';e['title']=row['title'];row['category']=e['category']='Căn hộ chung cư'
        x=r.resolve_source(row,e)
        self.assertEqual('80',x['values']['price_million']);self.assertFalse(x['changes'])

    def test_all_constraints_must_clear_before_pending_is_resolved(self):
        row,e=self.fixture('Diện tích đất57,1m². Giá bán12,5 tỷ. Có giỏ hàng nhiều căn, thanh toán trước. Hải Châu Đà Nẵng.')
        x=r.resolve_source(row,e)
        self.assertIn('prior_pending_requires_explicit_resolution',x['remaining_flags'])
        self.assertIn('partial_or_starting_price_context',x['remaining_flags'])

    def test_explicit_outside_asset_scope_is_never_ready(self):
        row,e=self.fixture('Nhà phố tại Eco Retreat Long An, Tây Ninh. Diện tích57m². Giá12,5 tỷ.')
        self.assertIn('EXPLICIT_ASSET_OUTSIDE_SUPPORTED_SCOPE',r.resolve_source(row,e)['remaining_flags'])

    def test_pending_is_not_cleared_merely_because_it_is_the_only_flag(self):
        row,e=self.fixture('Bán nhà, diện tích57m². Hải Châu Đà Nẵng.')
        self.assertIn('prior_pending_requires_explicit_resolution',r.resolve_source(row,e)['remaining_flags'])

    def test_unhandled_area_qualifier_is_not_mistaken_for_agreement(self):
        row,e=self.fixture('Đà Nẵng, Hải Châu. DT khủng:211m2. Diện tích:221m2. Giá bán:12,5 tỷ.',area='221')
        x=r.resolve_source(row,e)
        self.assertIn('description_area_needs_review',x['remaining_flags'])
        self.assertFalse(x['changes'])

class DistributionTest(unittest.TestCase):
    def test_one_issue_may_map_to_two_categories_without_duplicating_records(self):
        self.assertEqual({'PRICE_CONFLICT','AREA_CONFLICT'},batch.issue_categories('MULTIPLE_ASSETS_OR_INVENTORY_CONTEXT'))
        self.assertIn('HOLDOUT_RISK',batch.issue_categories('HOLDOUT_RISK_IN_FINAL_CLUSTER'))
        self.assertIn('LOCATION_CONFLICT',batch.issue_categories('SOURCE_LOCATION_CORROBORATION_MISSING'))

if __name__=='__main__':unittest.main()
