"""Guard v3 against holdout leakage, target leakage and mismatched model schemas."""
import json
import unittest

import numpy as np
from training_v3_common import (cohort, model_row, validate_parts, safe_source_features,
                                schema, encode, scores, FIELDS)


def row(key='one', group='g1', split='train', category='Nhà ở', **changes):
    value = dict(record_key=key, source='cafeland', pipeline_group=group,
        pipeline_status='eligible', category=category, reserved_splits=split,
        assigned_split='train' if split == 'train' else 'reserved_holdout',
        training_allowed=str(split == 'train'), protected_holdout=str(split != 'train'),
        price_million='2000', area_sqm='100', location_feature='Sơn Trà',
        displayed_date='2026-10-01', geographic_scope_status='accepted_old',
        raw_json=json.dumps(dict(rooms='3 phòng ngủ', ward='Phường An Hải',
                                 title='giá 2 tỷ', price_million=2000)))
    value.update(changes)
    return value


class V3Tests(unittest.TestCase):
    def test_reservations_have_test_precedence(self):
        self.assertEqual(cohort(row(split='train;validation')), 'validation')
        self.assertEqual(cohort(row(split='test;validation')), 'reserved')
        self.assertEqual(cohort(row(split='test;train')), 'reserved')
        with self.assertRaises(ValueError):
            cohort(row(split='test', training_allowed='True', assigned_split='train'))

    def test_noneligible_never_promoted(self):
        self.assertIsNone(cohort(row(pipeline_status='needs_review')))
        self.assertIsNone(cohort(row(pipeline_status='excluded')))

    def test_duplicate_group_protects_different_ids(self):
        parts = dict(train=[model_row(row(), 'train')], validation=[model_row(
            row(key='another', split='validation'), 'validation')])
        with self.assertRaises(ValueError):
            validate_parts(parts)
        parts['validation'][0]['pipeline_group'] = 'g2'
        validate_parts(parts)
        with self.assertRaises(ValueError):
            validate_parts(parts, {'g1'})

    def test_train_cannot_use_validation_reservation(self):
        parts = dict(train=[model_row(row(split='train;validation'), 'train')], validation=[])
        with self.assertRaises(ValueError):
            validate_parts(parts)

    def test_features_ignore_title_price_and_source(self):
        first = row()
        second = row(price_million='99999', source='other', record_key='different',
            raw_json=json.dumps(dict(rooms='3 phòng ngủ', ward='Phường An Hải',
                                     title='giá 999 tỷ', price_million=999999)))
        self.assertEqual(safe_source_features(first), safe_source_features(second))
        one, two = model_row(first, 'train'), model_row(second, 'train')
        spec = schema([one, one, one])
        np.testing.assert_equal(encode([one], spec), encode([two], spec))
        self.assertNotIn('raw_json', FIELDS)
        self.assertNotIn('title', FIELDS)
        self.assertNotIn('unit_price', FIELDS)

    def test_room_rules_and_land_mask(self):
        self.assertEqual(safe_source_features(row())['rooms'], '3')
        self.assertEqual(safe_source_features(row(category='Đất nền'))['rooms'], '')
        for room in ('0', '31', '3-4', '3.5', 'thỏa thuận'):
            self.assertEqual(safe_source_features(row(raw_json=json.dumps(dict(rooms=room))))['rooms'], '')

    def test_encoder_never_learns_validation_vocab(self):
        tr = model_row(row(), 'train')
        va = model_row(row(split='validation'), 'validation')
        va.update(location_feature='unseen location', ward_source='unseen ward', rooms='')
        spec = schema([tr, tr, tr])
        x = encode([va], spec)[0]
        self.assertNotIn('unseen location', spec['locations'])
        self.assertNotIn('unseen ward', spec['wards'])
        self.assertTrue(np.isnan(x[1]))
        self.assertEqual(x[2:5].tolist(), [1, 0, 1])
        self.assertEqual(float(x[5:].sum()), 0)

    def test_metrics_known_errors(self):
        score = scores([100, 200], [110, 160])
        self.assertEqual(score['mae_million'], 25)
        self.assertAlmostEqual(score['rmse_million'], np.sqrt(850))
        self.assertAlmostEqual(score['mape_pct'], 15)
        self.assertEqual(score['within_20pct'], 100)


if __name__ == '__main__':
    unittest.main()
