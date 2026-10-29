import unittest
import numpy as np
import measure_training_learning_curve as job


def rows(n=90):
    return [dict(record_key='test:'+str(i), pipeline_group='group:'+str(i), category=job.data.CATEGORIES[2],
                 price_million=str(1000+i*10), area_sqm=str(40+i%10), rooms='2', ward_source='', location_feature='known')
            for i in range(n)]


class LearningCurveTests(unittest.TestCase):
    def test_group_separation_fixed_outerfold_and_nested_subsets(self):
        byfold = {}
        all_outer = []
        for fold, fraction, subset, outer in job.partitions(rows()):
            train_keys = {r['record_key'] for r in subset}
            outer_keys = {r['record_key'] for r in outer}
            self.assertFalse({r['pipeline_group'] for r in subset} & {r['pipeline_group'] for r in outer})
            if fold in byfold:
                self.assertTrue(byfold[fold][0] <= train_keys)
                self.assertEqual(byfold[fold][1], outer_keys)
            else:
                all_outer.extend(outer_keys)
            byfold[fold] = train_keys, outer_keys
        self.assertEqual(len(all_outer), 90)
        self.assertEqual(len(set(all_outer)), 90)

    def test_price_values_do_not_choose_fold_or_subset(self):
        original = list(job.partitions(rows()))
        altered = list(job.partitions([dict(r, price_million='999999') for r in reversed(rows())]))
        for a,b in zip(original,altered):
            self.assertEqual([r['record_key'] for r in a[2]], [r['record_key'] for r in b[2]])
            self.assertEqual({r['record_key'] for r in a[3]}, {r['record_key'] for r in b[3]})

    def test_duplicate_groups_and_tiny_sets_are_refused(self):
        sample = rows()
        with self.assertRaises(ValueError):
            list(job.partitions(sample + [dict(sample[0], record_key='another')]))
        with self.assertRaises(ValueError):
            list(job.partitions(rows(2)))

    def test_unseen_outer_location_never_enters_vocab_and_target_not_in_features(self):
        subset = rows(30)
        outer = [dict(rows(1)[0], location_feature='outer_only', price_million='100000')]
        spec = job.feature.feature_spec(subset, job.data.CATEGORIES[2], 'all')
        self.assertEqual(spec['base_schema']['locations'], ['known'])
        self.assertNotIn('outer_only', spec['base_schema']['locations'])
        self.assertNotIn('price_million', spec['feature_names'])
        values = {r['record_key']:dict(rooms_completed='2', floors_claim='', access_claim='',house_subtype_claim='') for r in subset}
        encoded = job.feature.encode(outer,values,spec)
        self.assertEqual(encoded.shape[1], len(spec['feature_names']))
        self.assertTrue(np.isfinite(encoded[:,0]).all())


if __name__ == '__main__':unittest.main()
