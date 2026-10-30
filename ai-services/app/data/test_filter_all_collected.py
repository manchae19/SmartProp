import json
import unittest

from filter_all_collected import classify, finish_groups


class CollectionPipelineTests(unittest.TestCase):
    def row(self, key='cafeland:1', **updates):
        row = dict(record_key=key, source='cafeland', title='Bán nhà đẹp trung tâm phố',
                   category='Nhà ở', category_basis='source_category', price_million='5000',
                   area_sqm='100', raw_json='{}', transaction_verified='True',
                   geographic_scope_status='accepted_address', title_money_evidence='[]',
                   date_basis='source_update_not_first_post', displayed_date='2026-10-01',
                   review_codes='', address_raw='Hải Châu, Đà Nẵng', district='Hải Châu',
                   detail_fetched='True', collected_at='2026-10-11')
        row.update(updates)
        return row

    def review(self, **updates):
        r = dict(decision='correct', cache_valid=True, decision_file='review.csv',
                 original_price_million='5000', original_area_sqm='100',
                 price_million='4900', area_sqm='101', detail_sha256='abc')
        r.update(updates)
        return r

    def test_correct_labels_without_waiving_geography_or_date(self):
        r = classify(self.row(review_codes='title_price_conflict;listing_date_unavailable',
                              displayed_date=''), self.review())
        self.assertEqual(r['price_million'], 4900)
        self.assertEqual(r['area_sqm'], 101)
        self.assertEqual(r['pipeline_status'], 'needs_review')
        self.assertIn('listing_date_unavailable', r['pipeline_review_codes'])
        self.assertIn('title_price_conflict', r['resolved_review_codes'])

    def test_stale_review_never_changes_labels_or_excludes(self):
        for review in (self.review(cache_valid=False),
                       self.review(original_price_million='6000'),
                       self.review(decision='exclude', cache_valid=False)):
            with self.subTest(review=review):
                r = classify(self.row(), review)
                self.assertEqual(r['price_million'], '5000')
                self.assertEqual(r['pipeline_status'], 'needs_review')

    def test_unknown_province_not_treated_as_explicitly_outside(self):
        r = classify(self.row(address_raw='Đường chưa biết', geographic_scope_status='unverified'))
        self.assertEqual(r['pipeline_status'], 'needs_review')
        r = classify(self.row(address_raw='Quận 1, Hồ Chí Minh',
                              geographic_scope_status='outside_or_unverified'))
        self.assertEqual(r['pipeline_status'], 'excluded')

    def test_holdout_bridge_cannot_become_train(self):
        a, b = classify(self.row()), classify(self.row('cafeland:2', title='Tin riêng khác'))
        pairs = [dict(left=a['record_key'], right=b['record_key'], rule='bridge', title_similarity=1)]
        finish_groups([a, b], pairs, {a['record_key']: {'train'}, b['record_key']: {'test'}})
        self.assertTrue(a['protected_holdout'] and b['protected_holdout'])
        self.assertFalse(a['training_allowed'] or b['training_allowed'])
        self.assertEqual(sum(r['pipeline_status']=='eligible' for r in (a, b)), 1)

    def test_conflicting_group_quarantined_instead_of_selecting_cheaper(self):
        a, b = classify(self.row()), classify(self.row('cafeland:2', price_million='8000'))
        pairs = [dict(left=a['record_key'], right=b['record_key'], rule='bridge', title_similarity=1)]
        finish_groups([a, b], pairs, {})
        self.assertTrue(all(r['pipeline_status']=='needs_review' for r in (a, b)))

    def test_category_rule_cannot_clear_price_issue(self):
        r = classify(self.row(title='Bán nhà 2 tầng mặt phố',
                     raw_json=json.dumps({'category_needs_review': True, 'source_category': 'Nhà mặt phố'}),
                     review_codes='title_price_conflict'))
        self.assertEqual(r['category_review_decision'], 'keep')
        self.assertEqual(r['pipeline_status'], 'needs_review')
        self.assertIn('title_price_conflict', r['pipeline_review_codes'])


if __name__ == '__main__':
    unittest.main()
