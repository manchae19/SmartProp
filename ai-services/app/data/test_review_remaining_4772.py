import unittest
from review_remaining_4772 import reconsider, primary_issue, validate_optional_dates


class RemainingReviewTests(unittest.TestCase):
    def row(self,key='one',flags='older_than_183_days',**overrides):
        row=dict(record_key=key,pipeline_status='needs_review',pipeline_review_codes=flags,
            price_million='2000',area_sqm='60',category='Nhà ở',district='Hải Châu',
            pipeline_group=key,displayed_date='2025-01-01',review_decision='',detail_fetched='False',
            collected_at='2026-10-11',exclusion_codes='',protected_holdout='False',
            assigned_split='train',reserved_splits='train',training_allowed='False',representative_key='')
        row.update(overrides)
        return row

    def test_old_and_missing_dates_are_optional(self):
        a,b=reconsider([self.row(),self.row('two','listing_date_unavailable',displayed_date='')])
        self.assertEqual([a['pipeline_status'],b['pipeline_status']],['eligible','eligible'])
        self.assertEqual(b['displayed_date'],'')
        self.assertTrue(b['date_missing'])

    def test_date_policy_cannot_clear_unresolved_content(self):
        r=reconsider([self.row(flags='older_than_183_days;saved_source_review_pending')])[0]
        self.assertEqual(r['pipeline_status'],'needs_review')
        self.assertEqual(r['pipeline_review_codes'],'saved_source_review_pending')

    def test_invalid_target_stays_pending_even_when_date_only(self):
        for price in ['','nan','inf','0','-1']:
            r=reconsider([self.row(price_million=price)])[0]
            self.assertEqual(r['pipeline_status'],'needs_review')

    def test_matching_duplicate_group_keeps_one_representative(self):
        rows=reconsider([self.row('one',pipeline_group='g'),self.row('two',pipeline_group='g')])
        self.assertEqual(sorted(r['pipeline_status'] for r in rows),['eligible','excluded'])

    def test_date_only_group_numeric_conflict_not_promoted(self):
        rows=reconsider([self.row('one',pipeline_group='g'),self.row('two',pipeline_group='g',price_million='5000')])
        self.assertTrue(all(r['pipeline_status']=='needs_review' for r in rows))
        self.assertTrue(all('group_price_million_conflict' in r['pipeline_review_codes'] for r in rows))

    def test_linked_member_cannot_escape_unresolved_sibling(self):
        rows=reconsider([self.row('one','linked_group_member_not_eligible',pipeline_group='g'),
            self.row('two','saved_source_review_pending',pipeline_group='g')])
        self.assertTrue(all(r['pipeline_status']=='needs_review' for r in rows))

    def test_holdout_never_becomes_train(self):
        r=reconsider([self.row(protected_holdout='True',assigned_split='reserved_holdout',reserved_splits='test')])[0]
        self.assertEqual(r['pipeline_status'],'eligible')
        self.assertEqual(r['training_allowed'],'False')
        self.assertEqual(r['reserved_splits'],'test')

    def test_already_suppressed_duplicate_does_not_block_clean_member(self):
        rows=reconsider([self.row('one',pipeline_group='g'),self.row('two',pipeline_group='g',
            pipeline_status='excluded',exclusion_codes='suspected_duplicate_suppressed')])
        self.assertEqual(rows[0]['pipeline_status'],'eligible')
        self.assertEqual(rows[1]['pipeline_status'],'excluded')

    def test_blocked_unrequested_is_not_individual_http_failure(self):
        row=self.row()
        self.assertEqual(primary_issue(row,{},dict(state='not_requested_source_access_blocked'),{}),
                         'source_blocked_not_individually_requested')

    def test_new_input_validator_allows_missing_date_but_preserves_geography_gate(self):
        row=self.row(displayed_date='',model_split='train',geographic_scope_status='accepted_address',location_feature='Hải Châu')
        validate_optional_dates({'train':[row],'validation':[]},set())
        row['geographic_scope_status']='unverified'
        with self.assertRaises(ValueError):
            validate_optional_dates({'train':[row],'validation':[]},set())


if __name__=='__main__':
    unittest.main()
