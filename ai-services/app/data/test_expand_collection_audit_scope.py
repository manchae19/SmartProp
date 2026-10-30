import unittest
from expand_collection_audit_scope import geographic_scope, rescreen


class ExpandedScopeTests(unittest.TestCase):
    def row(self, **updates):
        row = dict(address_raw='Hòa Khánh, Đà Nẵng', location_basis='crosses_historical_districts',
                   review_codes='historical_district_unresolved', prior_review_decision='',
                   displayed_date='2026-10-10', status='district_needs_review', district='')
        row.update(updates)
        return row

    def test_new_ward_no_longer_requires_old_district(self):
        row = rescreen(self.row())
        self.assertEqual(row['status'], 'screened_candidate_unverified')
        self.assertEqual(row['district'], '')

    def test_former_quang_nam_accepted(self):
        row = rescreen(self.row(address_raw='Cẩm Châu, Hội An, Quảng Nam',
            location_basis='outside_or_unknown', displayed_date='',
            review_codes='historical_district_unresolved;outside_or_unverified_old_danang;source_region_needs_review;listing_date_unavailable'))
        self.assertEqual(row['status'], 'screened_date_unknown')
        self.assertNotIn('source_region_needs_review', row['review_codes'])

    def test_street_name_does_not_establish_province(self):
        status, _ = geographic_scope(self.row(address_raw='Đường Quảng Nam, Phường Hoà Quý, Quận Ngũ Hành Sơn',
            location_basis='legacy_filename_and_district_unverified'))
        self.assertEqual(status, 'unverified')

    def test_other_province_excluded(self):
        row = rescreen(self.row(address_raw='Quận 8, TP Hồ Chí Minh', location_basis='outside_or_unknown'))
        self.assertEqual(row['status'], 'outside_or_unverified_scope')

    def test_quality_and_prior_decisions_preserved(self):
        row = rescreen(self.row(review_codes='historical_district_unresolved;title_price_conflict'))
        self.assertEqual(row['status'], 'needs_review')
        self.assertIn('title_price_conflict', row['review_codes'])
        for decision in ['exclude', 'pending', 'correct', 'keep']:
            row = rescreen(self.row(prior_review_decision=decision))
            self.assertEqual(row['status'], ('prior_' if decision in ['exclude','pending'] else 'prior_reviewed_') + decision)


if __name__ == '__main__':
    unittest.main()
