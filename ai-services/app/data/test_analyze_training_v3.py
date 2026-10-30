"""Critical reconciliation and interpretation guards for v3 diagnostics."""
import unittest
from copy import deepcopy

from analyze_training_v3 import (selected_predictions, diagnostic_row, evidence_state,
                                 price_band, area_band, segment_metrics)


def row(key='one', split='validation', **changes):
    value = dict(record_key=key, model_split=split, category='Nhà ở', source='cafeland',
        location_feature='Hòa Vang', detail_url='https://example.test/one',
        displayed_date='2026-10-01', area_sqm='100', price_million='1000', ward_source='', rooms='')
    value.update(changes)
    return value


def pred(key='one', **changes):
    value = dict(record_key=key, selected='True', category='Nhà ở',
                 actual_million='1000', predicted_million='1200')
    value.update(changes)
    return value


class DiagnosticsTests(unittest.TestCase):
    def test_join_rejects_missing_duplicate_and_label_changes(self):
        selected_predictions([row()], [pred()])
        for predictions in ([], [pred(),pred()], [pred(key='other')], [pred(actual_million='2000')],
                            [pred(category='Đất nền')], [pred(predicted_million='nan')]):
            with self.assertRaises(ValueError):
                selected_predictions([row()], predictions)

    def test_nonselected_predictions_do_not_replace_selected(self):
        result = selected_predictions([row()], [pred(), pred(selected='False', predicted_million='9999')])
        self.assertEqual(result['one']['predicted_million'], '1200')

    def test_tail_flag_does_not_relabel_and_unseen_support_is_zero(self):
        stat = dict(unit_q01=20,unit_q99=100,area_min=20,area_max=500,locations={})
        source = dict(identity_verified=True,structure_verified=True,price_million=1000,area_sqm=100)
        value = diagnostic_row(row(), stat, source)
        self.assertEqual(value['actual_million'],1000)
        self.assertEqual(value['location_support'],'unseen')
        self.assertEqual(value['train_location_n'],0)
        self.assertIn('unit_price_outside_train_q01_q99',value['diagnostic_flags'])
        self.assertTrue(value['label_action'].startswith('none'))
        self.assertEqual(value['evidence_state'],'cached_header_matches_snapshot')

    def test_unverified_cache_cannot_confirm_or_contradict_identity(self):
        state, flags = evidence_state(row(), dict(identity_verified=False,
            structure_verified=True,price_million=99999,area_sqm=1))
        self.assertEqual(state,'cached_identity_or_structure_unverified')
        self.assertEqual(flags,[])

    def test_actual_header_conflict_is_only_a_review_signal(self):
        state, flags = evidence_state(row(), dict(identity_verified=True,
            structure_verified=True,price_million=2000,area_sqm=100))
        self.assertEqual(state,'cached_header_differs_from_snapshot')
        self.assertEqual(flags,['cached_detail_price_million_differs_from_snapshot'])

    def test_bins_keep_boundary_values_once(self):
        self.assertEqual(price_band(1999),'<2 tỷ')
        self.assertEqual(price_band(2000),'2–<5 tỷ')
        self.assertEqual(price_band(20000),'≥20 tỷ')
        self.assertEqual(area_band(50),'50–<100 m²')
        self.assertEqual(area_band(200),'≥200 m²')

    def test_segment_counts_and_metrics_reconcile(self):
        records = [dict(category='Nhà ở',source='cafeland',actual_million=100,
                        predicted_million=110,signed_error_million=10),
                   dict(category='Nhà ở',source='nhadat24h',actual_million=200,
                        predicted_million=160,signed_error_million=-40)]
        groups = segment_metrics(deepcopy(records),'source')
        self.assertEqual(sum(r['n'] for r in groups),len(records))
        self.assertEqual(sum(r['n']*r['mae_million'] for r in groups),50)
        self.assertTrue(all(r['n_below_10'] for r in groups))


if __name__ == '__main__':
    unittest.main()
