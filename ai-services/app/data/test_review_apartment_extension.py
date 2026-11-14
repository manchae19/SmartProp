import unittest
import review_apartment_extension as job
from test_review_apartment_pilot import sample, CATALOG


class CorrectedDedupTest(unittest.TestCase):
    def test_recovered_body_also_participates_in_history_dedup(self):
        body='Bán căn hộ chung cư diện tích 55m2. Giá bán 2,5 tỷ. '+' '.join('tuvung'+str(i) for i in range(120))+' Liên hệ để nhận thông tin chi tiết.'
        new=sample(description=body)
        history=sample('old:1',title='Căn góc hướng đông tại tòa nhà trung tâm giao dịch trực tiếp chính chủ')
        evidence={'old:1':{'identity_verified':True,'description':body}}
        decisions,links=job.evaluate([new],[],[history],evidence,CATALOG,[])
        self.assertEqual(decisions[0]['review_codes'],[])
        self.assertEqual(decisions[0]['cohort_split'],'needs_evidence')
        self.assertIn('linked_to_historical_collection',decisions[0]['group_review_codes'])
        self.assertTrue(any(p['left']=='old:1' or p['right']=='old:1' for p in links))
        self.assertEqual(decisions[0]['description'],body)


if __name__=='__main__':unittest.main()
