import unittest
import review_source_features_75 as job


class NewSourceReviewTests(unittest.TestCase):
    def row(self, description):
        return dict(record_key='cafeland:new', title='Bán nhà 80m2 giá 3 tỷ', category='Nhà ở',
            source_evidence_flags=[], address_raw='Sơn Trà, Đà Nẵng', source_location_parts=['Sơn Trà', 'Đà Nẵng'],
            currency='VND', transaction_type='sale', price_million=3000, area_sqm=80,
            collected_at='2026-10-29T00:00:00Z', source_published_date='2026-10-28', description=description)

    def catalog(self):
        return dict(legacy=['Sơn Trà'], expanded={})

    def test_source_header_echo_does_not_corroborate_price_and_area(self):
        description = 'Thông tin mô tả Bán nhà riêng Sơn Trà, Đà Nẵng Nhà ở có vị trí thuận tiện để sinh sống lâu dài cùng gia đình. Giá: 3.000.000.000 VND Diện tích: 80m2'
        result, _ = job.quality(self.row(description), self.catalog())
        self.assertIn('seller_total_price_not_corroborated', result['review_codes'])
        self.assertIn('seller_property_area_not_corroborated', result['review_codes'])

    def test_full_post_contact_price_conflict_is_kept(self):
        description = 'Bán nhà ở hiện trạng hai tầng tại quận Sơn Trà. Diện tích 80m2. Giá bán 3 tỷ. Liên hệ người bán. Giá bán 4 tỷ.'
        result, _ = job.quality(self.row(description), self.catalog())
        self.assertIn('seller_total_price_conflict', result['review_codes'])

    def test_single_source_snapshot_with_literal_values_can_be_reserved(self):
        description = 'Bán nhà ở hiện trạng hai tầng tại quận Sơn Trà với không gian sinh hoạt riêng. Diện tích 80m2. Giá bán 3 tỷ.'
        result, _ = job.quality(self.row(description), self.catalog())
        self.assertEqual(result['review_codes'], [])

    def test_excluded_historical_bridge_keeps_current_group_protected(self):
        old = [dict(record_key=k, title='old '+k, category='Nhà ở', area_sqm=80, price_million=3000,
                    pipeline_group=k) for k in ['old:a', 'old:bridge']]
        new = dict(self.row('Nhà ở 80m2 giá 3 tỷ'), review_codes=[], location_feature='Sơn Trà')
        links = [dict(left='old:a', right='old:bridge', rule='old_preserved', title_similarity=1),
                 dict(left='old:bridge', right=new['record_key'], rule='known_link', title_similarity=1)]
        decisions, preserved = job.grouped_decisions([new], old, [], links, {})
        self.assertEqual(decisions[0]['dataset_role'], 'quarantine')
        self.assertIn('linked_to_historical_or_reserved_group', decisions[0]['group_review_codes'])
        self.assertEqual(preserved[:2], links)

    def test_whole_rental_apartment_building_is_not_plain_house(self):
        row = self.row('TÒA CĂN HỘ MẶT TIỀN, nhà 3 tầng 7 phòng cho thuê thu nhập ổn định. Diện tích 80m2. Giá bán 3 tỷ.')
        result, _ = job.quality(row, self.catalog())
        self.assertIn('nonstandard_asset_requires_review', result['review_codes'])


if __name__=='__main__': unittest.main()
