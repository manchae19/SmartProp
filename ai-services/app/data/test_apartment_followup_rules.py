import unittest
import apartment_followup_rules as rules
from test_review_apartment_pilot import sample, CATALOG


class FollowupRulesTest(unittest.TestCase):
    def test_footer_request_does_not_erase_the_actual_description(self):
        row=sample(description=sample()['description']+' Liên hệ để nhận thông tin chi tiết và hẹn xem căn.')
        self.assertIn('55m2',rules.subject(row['description']))
        self.assertFalse(rules.quality(row,CATALOG)['review_codes'])

    def test_block_number_is_not_a_loss_or_discount(self):
        mention=rules.money_mentions('Căn góc tầng 4 block 407. Giá bán: 1,3 tỷ.')[0]
        self.assertEqual(mention['kind'],'total_candidate')
        row=sample(price_million=1300,description='Căn hộ chung cư 55m2 tầng 4 block 407. Giá bán: 1,3 tỷ. Có hai phòng ngủ đầy đủ nội thất.')
        self.assertFalse(rules.quality(row,CATALOG)['review_codes'])

    def test_explicit_sale_price_after_rental_use_is_still_sale_total(self):
        found=rules.money_mentions('Phù hợp để ở hoặc đầu tư cho thuê. Giá bán: 2,5 tỷ.')
        self.assertEqual(found[0]['kind'],'total_candidate')
        self.assertEqual(rules.money_mentions('Giá cho thuê 20 triệu/tháng')[0]['kind'],'rental_income')

    def test_approximate_teaser_does_not_conflict_with_exact_matching_total(self):
        row=sample(price_million=3080,description='Căn hộ chung cư 55m2 giá chỉ 3 tỷ nhỉnh nhẹ. Có hai phòng ngủ và nội thất đầy đủ. Giá bán: 3.08 tỷ.')
        self.assertFalse(rules.quality(row,CATALOG)['review_codes'])
        row['description']=row['description'].replace('nhỉnh nhẹ','')
        self.assertIn('description_total_price_conflict',rules.quality(row,CATALOG)['review_codes'])

    def test_actual_conflicts_missing_labels_partial_and_inventory_stay_review(self):
        for field,value,code in [('source_evidence_flags',['missing_structured_area'],'missing_structured_area'),
                                 ('description',sample()['description']+' Giá bán: 1,2 tỷ.','description_total_price_conflict'),
                                 ('description',sample()['description']+' Thanh toán 70% chỉ 1,75 tỷ.','partial_starting_or_booking_price'),
                                 ('description',sample()['description']+' Giỏ hàng nhiều căn.','multiple_units_or_inventory')]:
            with self.subTest(code=code):self.assertIn(code,rules.quality(sample(**{field:value}),CATALOG)['review_codes'])

    def test_header_echo_is_not_seller_corroboration(self):
        row=sample(description='Căn hộ tại trung tâm có đầy đủ tiện ích cho gia đình và không gian xanh thoáng mát. Giá : 2500000000 VND Diện tích: 55.00 m2')
        self.assertIn('single_unit_price_area_not_corroborated_in_seller_description',rules.quality(row,CATALOG)['review_codes'])

    def test_nearby_building_does_not_exclude_single_unit(self):
        row=sample(description=sample()['description']+' Xung quanh là tòa căn hộ và khách sạn.')
        self.assertEqual(rules.scope_exclusions(row)[0],[])
        row['description']='Bán tòa căn hộ 7 phòng khép kín. Diện tích đất 55m2 giá 2,5 tỷ.'
        self.assertIn('whole_building_not_single_apartment',rules.scope_exclusions(row)[0])


if __name__=='__main__':unittest.main()
