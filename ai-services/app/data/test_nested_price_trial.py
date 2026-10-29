import copy
import unittest
import numpy as np

import nested_price_trial as trial
import property_text_features_v6 as feature


def rows(n=90,category=None,prefix='x'):
    category=category or trial.data.CATEGORIES[0]
    return [dict(record_key=f'{prefix}:{i}',pipeline_group=f'group:{prefix}:{i}',category=category,
        source='fixture',area_sqm=str(40+i%50),price_million=str(60*(40+i%50)),rooms='2',ward_source='',
        location_feature='A',model_split='train',reserved_splits='train') for i in range(n)]


def values(sample):
    return {r['record_key']:dict(rooms_completed='2',floors_claim='2',access_claim='frontage',house_subtype_claim='') for r in sample}


class TrialContractTests(unittest.TestCase):
    def test_outer_and_inner_groups_are_separate_with_complete_coverage(self):
        sample=rows();held_keys=[]
        for outer,fit,held in trial.partition(sample,3,trial.PROTOCOL['outer_salt']):
            held_keys += [r['record_key'] for r in held]
            outer_groups={r['pipeline_group'] for r in held};inner_keys=[]
            for _,inner,check in trial.partition(fit,2,trial.PROTOCOL['inner_salt']+str(outer)+'/'):
                inner_groups={r['pipeline_group'] for r in inner};check_groups={r['pipeline_group'] for r in check}
                self.assertFalse(inner_groups&check_groups or (inner_groups|check_groups)&outer_groups)
                inner_keys += [r['record_key'] for r in check]
            self.assertEqual(set(inner_keys),{r['record_key'] for r in fit})
            self.assertEqual(len(inner_keys),len(fit))
        self.assertEqual(len(held_keys),len(set(held_keys)))
        self.assertEqual(set(held_keys),{r['record_key'] for r in sample})

    def test_partition_is_order_and_price_independent(self):
        a=list(trial.partition(rows(),3,'fixed'))
        b=list(trial.partition([dict(r,price_million='999999') for r in reversed(rows())],3,'fixed'))
        for x,y in zip(a,b):
            for index in [1,2]:self.assertEqual([r['record_key'] for r in x[index]],[r['record_key'] for r in y[index]])

    def test_duplicate_key_group_and_too_small_sets_are_rejected(self):
        sample=rows()
        for added in [dict(sample[0]),dict(sample[0],record_key='other')]:
            with self.assertRaisesRegex(ValueError,'Repeated'):list(trial.partition(sample+[added],3,'x'))
        with self.assertRaisesRegex(ValueError,'Too few'):list(trial.partition(rows(2),3,'x'))

    def test_targets_roundtrip_total_and_unit(self):
        sample=rows()
        for arm in trial.ARMS:
            np.testing.assert_allclose(trial.inverse(trial.labels(sample,arm),sample,arm),[float(r['price_million']) for r in sample])
        np.testing.assert_allclose(trial.labels(sample,'log_unit_squared'),np.log(60))

    def test_bad_price_area_arm_or_predictions_fail_closed(self):
        for bad in ['0','-1','nan','inf']:
            with self.assertRaises(ValueError):trial.labels([dict(rows(1)[0],price_million=bad)],trial.CONTROL)
            with self.assertRaises(ValueError):trial.labels([dict(rows(1)[0],area_sqm=bad)],'log_unit_squared')
        with self.assertRaises(ValueError):trial.inverse([np.nan],rows(1),trial.CONTROL)
        with self.assertRaises(ValueError):trial.params('unknown')

    def test_no_target_or_held_vocabulary_enters_feature_matrix(self):
        sample=rows();held=[dict(rows(1)[0],location_feature='held-only',ward_source='held ward')]
        spec=feature.feature_spec(sample,trial.data.CATEGORIES[0],'all');features=values(sample)
        self.assertNotIn('held-only',spec['base_schema']['locations'])
        self.assertFalse(set(spec['feature_names'])&{'price_million','unit_price','title','description','record_key'})
        first=feature.encode(held,features,spec)
        other=feature.encode([dict(held[0],price_million='999999999')],features,spec)
        np.testing.assert_equal(first,other)

    def test_inner_selection_is_weighted_by_prediction_count_and_ties_favor_control(self):
        scores=[]
        for arm in trial.ARMS:
            for n,error in [(1,100),(9,0)]:scores.append(dict(arm=arm,n=n,absolute_error_sum=error))
        selected,maes=trial.choose(scores)
        self.assertEqual(selected,trial.CONTROL);self.assertEqual(set(maes.values()),{10})
        for score in scores:
            if score['arm']=='log_unit_squared':score['absolute_error_sum']/=2
        self.assertEqual(trial.choose(scores)[0],'log_unit_squared')

    def test_missing_arm_invalid_score_or_unequal_coverage_rejected(self):
        valid=[dict(arm=a,n=10,absolute_error_sum=10) for a in trial.ARMS]
        for sample in [valid[:-1],valid+[dict(arm=trial.CONTROL,n=1,absolute_error_sum=1)],
                       [dict(r,absolute_error_sum=float('nan')) for r in valid]]:
            with self.assertRaises(ValueError):trial.choose(sample)

    def test_location_median_threshold_fallback_and_no_held_target_usage(self):
        fit=[dict(r,location_feature='A',price_million=str(100*float(r['area_sqm']))) for r in rows(5)]
        fit += [dict(r,location_feature='B',price_million=str(10*float(r['area_sqm']))) for r in rows(4,prefix='b')]
        held=[dict(rows(1)[0],location_feature='A'),dict(rows(1)[0],location_feature='B')]
        a=trial.median_baseline(fit,held);b=trial.median_baseline(fit,[dict(r,price_million='999999') for r in held])
        np.testing.assert_equal(a,b);np.testing.assert_equal(a,[4000,4000])
        fit.append(dict(rows(1,prefix='last')[0],location_feature='B',price_million='400'))
        self.assertEqual(trial.median_baseline(fit,held)[1],400)

    def test_nomination_gate_requires_all_predeclared_checks(self):
        metric=[];folds=[]
        for category in trial.data.CATEGORIES+['ALL']:
            for method,mae in [('control',100),('selected',90),('median_unit_location',110)]:
                metric.append(dict(category=category,method=method,mae_million=mae,within_20pct=60))
                if category!='ALL':
                    for f in range(3):folds.append(dict(category=category,method=method,outer_fold=f,mae_million=mae))
        self.assertTrue(trial.nomination_gate(metric,folds)['passed'])
        simple_better=copy.deepcopy(metric)
        next(r for r in simple_better if (r['category'],r['method'])==('ALL','median_unit_location'))['mae_million']=80
        self.assertFalse(trial.nomination_gate(simple_better,folds)['passed'])
        for category in trial.data.CATEGORIES:
            altered=copy.deepcopy(metric)
            next(r for r in altered if (r['category'],r['method'])==(category,'selected'))['within_20pct']=54
            self.assertFalse(trial.nomination_gate(altered,folds)['passed'])
        changed=copy.deepcopy(folds)
        for r in changed:
            if r['method']=='selected' and r['outer_fold'] in [0,1]:r['mae_million']=101
        self.assertFalse(trial.nomination_gate(metric,changed)['passed'])


if __name__=='__main__':unittest.main()
