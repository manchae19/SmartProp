import hashlib
import json
import unittest
from finalize_apartment_review import apply, read, OUT, SOURCE, REVIEW


class FinalizationTests(unittest.TestCase):
    def test_correction_recomputes_unit_and_retains_original(self):
        original=dict(price_million='4300',area_sqm='67',model_split='train',raw_json='original')
        decision=dict(decision='correct',price_million=5700,area_sqm=66.7,note='Evidence',terms='4300+1400')
        result=apply(original,decision)
        self.assertEqual(result['original_price_million'],'4300')
        self.assertAlmostEqual(float(result['price_per_sqm_million']),5700/66.7)
        self.assertEqual(result['raw_json'],'original')
        self.assertEqual(original['price_million'],'4300')

    def test_unresolved_and_nonfinite_never_enter_dataset(self):
        original=dict(price_million='4300',area_sqm='67')
        for decision in ['pending','exclude']:
            self.assertIsNone(apply(original,dict(decision=decision)))
        with self.assertRaises(ValueError):
            apply(original,dict(decision='correct',price_million=float('nan'),area_sqm=None,note='',terms=''))

    def test_all_decisions_reconciled_and_holdouts_frozen(self):
        original={r['record_key']:r for r in read(SOURCE)}
        decisions={r['record_key']:r for r in read(OUT/'review_decisions.csv')}
        included=read(OUT/'baseline_inputs.csv')
        excluded=read(OUT/'quarantined.csv')
        self.assertEqual(len(decisions),64)
        self.assertEqual(len(included)+len(excluded),296)
        self.assertEqual(len({r['record_key'] for r in included+excluded}),296)
        self.assertTrue(all(decisions[r['record_key']]['decision'] in ['pending','exclude'] for r in excluded))
        self.assertTrue(all(r['model_split']==original[r['record_key']]['model_split'] for r in included))
        self.assertTrue(all(r['duplicate_candidate_group']==original[r['record_key']]['duplicate_candidate_group'] for r in included))
        self.assertEqual(len({r['duplicate_candidate_group'] for r in included}),len(included))
        self.assertEqual((OUT/'reviewed_queue.csv').read_bytes(),(REVIEW/'needs_review.csv').read_bytes())
        for r in included:
            if r['record_key'] not in decisions:
                self.assertEqual(r['price_million'],original[r['record_key']]['price_million'])
                self.assertEqual(r['area_sqm'],original[r['record_key']]['area_sqm'])

    def test_protected_inputs_and_backup(self):
        report=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),report['source_input_sha256'])
        self.assertEqual(hashlib.sha256((OUT/'review_queue_before.csv').read_bytes()).hexdigest(),report['review_queue_before_sha256'])
        self.assertEqual(hashlib.sha256((OUT/'baseline_inputs.csv').read_bytes()).hexdigest(),report['dataset_sha256'])


if __name__=='__main__':
    unittest.main()
