import unittest
from finalize_training_source_review import decide


class SourceReviewTests(unittest.TestCase):
    def row(self,key):return dict(record_key=key,detail_state='identity_verified',detail_flags='')

    def test_payment_percentage_never_multiplied(self):
        decision,p,a,note=decide(self.row('nhadat24h:4396478'))
        self.assertEqual(decision,'pending');self.assertIsNone(p)

    def test_explicit_exact_area_correction(self):
        decision,p,a,note=decide(self.row('nhadat24h:4382452'))
        self.assertEqual((decision,p,a),('correct',None,33.3))

    def test_mixed_areas_and_multiple_prices_stay_pending(self):
        decision,p,a,note=decide(self.row('nhadat24h:4363060'))
        self.assertEqual(decision,'pending');self.assertIsNone(p);self.assertIsNone(a)

    def test_multiple_lots_not_synthetic_single_plot(self):
        decision,p,a,note=decide(self.row('cafeland:3146695'))
        self.assertEqual(decision,'exclude');self.assertIsNone(p);self.assertIsNone(a)

    def test_wrong_identity_prevents_predefined_correction(self):
        row=self.row('nhadat24h:4382452');row['detail_state']='identity_unverified'
        self.assertEqual(decide(row)[0],'pending')


if __name__=='__main__':unittest.main()
