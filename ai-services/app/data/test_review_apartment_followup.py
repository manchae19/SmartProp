import copy
import unittest
import review_apartment_followup as job
from test_review_apartment_pilot import sample, CATALOG


def prior(row,group='frozen:1',split='collection_holdout'):
    return dict(record_key=row['record_key'],property_candidate_group=group,cohort_split=split,
                review_codes='[]',group_review_codes='[]')


class FollowupGroupsTest(unittest.TestCase):
    def test_cross_source_duplicate_does_not_increase_cohort(self):
        old=sample();new=sample('nhadat24h:9990002',source='nhadat24h')
        out,_=job.evaluate([old],[new],[],{},CATALOG,[prior(old)])
        self.assertEqual(sum(r['cohort_split']=='collection_holdout' for r in out),1)
        bykey={r['record_key']:r for r in out}
        self.assertEqual(bykey[old['record_key']]['cohort_split'],'collection_holdout')
        self.assertEqual(bykey[new['record_key']]['cohort_split'],'suppressed_duplicate')

    def test_new_uncertainty_marks_extended_risk_without_mutating_old_lock(self):
        old=sample();new=sample('nhadat24h:9990002',source='nhadat24h',source_evidence_flags=['missing_jsonld_product_identity'])
        frozen=[prior(old)];before=copy.deepcopy(frozen)
        out,_=job.evaluate([old],[new],[],{},CATALOG,frozen)
        self.assertTrue(all(r['cohort_split']=='needs_evidence' for r in out))
        self.assertEqual(frozen,before);self.assertTrue(all(not r['training_allowed'] for r in out))

    def test_prior_group_is_not_split_to_create_clean_candidates(self):
        a=sample();b=sample('cafeland:9990002',title='Bán căn hộ rộng rãi tại khu phố trung tâm thích hợp gia đình',
            area_sqm=75,description='Căn hộ chung cư diện tích 75m2. Giá bán 2,5 tỷ. Đầy đủ nội thất với không gian sống rộng rãi thoáng mát.')
        out,_=job.evaluate([a,b],[],[],{},CATALOG,[prior(a,split='quarantine'),prior(b,split='quarantine')])
        self.assertTrue(all(r['cohort_split']=='needs_evidence' for r in out))
        self.assertTrue(all('group_area_sqm_conflict' in r['group_review_codes'] for r in out))

    def test_literal_whole_building_is_excluded_only_from_scope(self):
        row=sample(description='Bán tòa căn hộ 7 phòng khép kín. Diện tích đất 55m2, giá bán 2,5 tỷ. Tài sản kinh doanh cho thuê.')
        before=copy.deepcopy(row)
        out,_=job.evaluate([row],[],[],{},CATALOG,[prior(row,split='quarantine')])
        self.assertEqual(out[0]['review_outcome'],'excluded_scope')
        self.assertEqual(row,before)


if __name__=='__main__':unittest.main()
