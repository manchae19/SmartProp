import json
import unittest

from test_filter_all_collected import CollectionPipelineTests
from review_pending_collection import repair, compatible_category, apply_review_rules, action_for
from filter_all_collected import classify


class PendingReviewTests(unittest.TestCase):
    def row(self, **updates):
        row = CollectionPipelineTests().row()
        row.update(source_listing_id='1', detail_url='https://nhadat.cafeland.vn/ban-nha-1.html',
                   location_basis='historical_district', district_candidates='',
                   age_days='10', prior_review_decision='', status='needs_review',
                   raw_json=json.dumps(dict(price_raw='5 tỷ', area_raw='100m2', source_category='ban-nha-rieng')))
        row.update(updates)
        return row

    def test_fill_missing_full_strings(self):
        r, changes = repair(self.row(price_million='', area_sqm=''))
        self.assertEqual(r['price_million'], 5000)
        self.assertEqual(r['area_sqm'], 100)
        self.assertEqual(len(changes), 2)
        self.assertNotIn('missing_or_invalid_price', r['review_codes'])
        self.assertNotIn('missing_or_invalid_area', r['review_codes'])

    def test_dont_guess_unit_range_or_negotiated_price(self):
        for price in ('Thỏa thuận', '117 triệu / m²', 'Từ 2 tỷ', '2-3 tỷ', 'Trả trước 1 tỷ'):
            with self.subTest(price=price):
                r, changes = repair(self.row(price_million='', raw_json=json.dumps(dict(price_raw=price, area_raw='100m2'))))
                self.assertEqual(r['price_million'], '')
                self.assertFalse(any(c['field']=='price_million' for c in changes))

    def test_do_not_override_existing_label_even_if_raw_disagrees(self):
        r, changes = repair(self.row(price_million='6000'))
        self.assertEqual(r['price_million'], '6000')
        self.assertFalse(changes)
        self.assertIn('price_parse_mismatch', r['review_codes'])

    def test_cross_snapshot_conflicts_survive_row_reparse(self):
        r, _ = repair(self.row(review_codes='snapshot_price_million_conflict'))
        self.assertIn('snapshot_price_million_conflict', r['review_codes'])

    def test_specific_category_rejects_mixed_or_opposing_title(self):
        raw = dict(source_category='Nhà mặt phố')
        self.assertEqual(compatible_category(self.row(), raw), 'Nhà ở')
        self.assertIsNone(compatible_category(self.row(title='Bán đất tặng nhà mặt tiền'), raw))
        self.assertIsNone(compatible_category(self.row(), dict(source_category='Nhà đất thổ cư')))

    def test_saved_pending_cannot_be_overridden(self):
        normalized = self.row()
        r = classify(normalized)
        r.update(review_decision='pending', pipeline_review_codes='source_category_needs_review;saved_source_review_pending')
        after, rule = apply_review_rules(r, normalized)
        self.assertEqual(after['pipeline_status'], 'needs_review')
        self.assertIn('source_category_needs_review', after['pipeline_review_codes'])
        self.assertFalse(rule)

    def test_missing_date_and_old_date_kept_out_of_main(self):
        r = dict(pipeline_status='needs_review', pipeline_review_codes='listing_date_unavailable')
        self.assertEqual(action_for(r, 1)[0], 'undated_candidate')
        self.assertNotEqual(action_for(r, 2)[0], 'undated_candidate')
        r['pipeline_review_codes'] = 'older_than_183_days'
        self.assertEqual(action_for(r, 1)[0], 'historical_candidate')

    def test_source_special_is_excluded_without_deleting(self):
        normalized = self.row(category='Khác', raw_json=json.dumps(dict(source_category='Condotel')))
        r = classify(normalized)
        after, _ = apply_review_rules(r, normalized)
        self.assertEqual(after['pipeline_status'], 'excluded')
        self.assertIn('explicit_special_source_category', after['exclusion_codes'])


if __name__ == '__main__':
    unittest.main()
