import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import review_property_expansion as job


class SnapshotReviewTests(unittest.TestCase):
    def test_current_price_is_parsed_not_copied_from_frozen_expected_value(self):
        from test_collect_apartment_pilot import fixture
        body, card = fixture()
        record = dict(card, observed_at='2026-10-29T12:00:00Z',
            response_sha256=job.collect.digest(body), fetch=dict(http_status=200,response_url=card['detail_url']))
        original = dict(title=card['listing_title'], raw_json='{"price_raw":"9 tỷ","area_raw":"55m2"}')
        parsed = job.parse_snapshot(record,body,original)
        self.assertEqual(parsed['price_million'],2500)
        self.assertEqual(parsed['area_sqm'],55)
        self.assertFalse(parsed['training_allowed'])
        self.assertFalse(any(x.startswith('listing_detail_') for x in parsed['source_evidence_flags']))

    def test_http_failure_never_reuses_old_price(self):
        record=dict(record_key='cafeland:1',fetch=dict(http_status=404,response_url='https://nhadat.cafeland.vn/test-1.html'),
                    observed_at='2026-10-29T12:00:00Z',expected_price_million=9999)
        with self.assertRaisesRegex(ValueError,'not available'):job.parse_snapshot(record,b'gone',{})

    def test_exact_duplicate_link_to_reserved_history_blocks_candidate(self):
        def row(key):
            return dict(record_key=key,title='Can ho chung cu tang muoi hai Son Tra view bien',category=job.claims.APARTMENT,
                        price_million=2500,area_sqm=55,description='seller body')
        old=dict(row('old:1'),pipeline_group='frozen:1',protected_holdout='True',reserved_splits='test')
        new=row('new:1');snapshot=copy.deepcopy(old)
        clean=dict(review_codes=[],location_feature='Sơn Trà')
        with patch.object(job.quality,'quality',return_value=clean), patch.object(job.quality,'scope_exclusions',return_value=([],[])), \
                patch.object(job.grouping.previous.old,'extra_pairs',return_value=[]):
            decisions,_=job.classify_groups([new],[old],[],{}, {},set())
        self.assertEqual(decisions[0]['candidate_role'],'needs_source_review')
        self.assertIn('linked_to_protected_or_prior_batch',decisions[0]['group_review_codes'])
        self.assertEqual(old,snapshot)

    def test_preserved_old_bridge_links_cannot_be_lost_when_titles_change(self):
        old=dict(record_key='old:1',title='reserved listing changed title',category=job.claims.APARTMENT,price_million=2500,
                 area_sqm=55,pipeline_group='g1',protected_holdout='True',reserved_splits='test')
        new=dict(record_key='new:1',title='entirely different subject',category=job.claims.APARTMENT,price_million=2500,
                 area_sqm=55,description='body')
        link=dict(left='old:1',right='new:1',rule='prior_verified_link',title_similarity=.99)
        with patch.object(job.quality,'quality',return_value=dict(review_codes=[],location_feature='Sơn Trà')), \
             patch.object(job.quality,'scope_exclusions',return_value=([],[])), \
             patch.object(job.grouping.previous.old,'extra_pairs',return_value=[]):
            decisions,_=job.classify_groups([new],[old],[],{}, {},set(),[link])
        self.assertIn('linked_to_protected_or_prior_batch',decisions[0]['group_review_codes'])


if __name__=='__main__':unittest.main()
