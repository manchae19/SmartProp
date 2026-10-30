import copy
import unittest
import analyze_models_v6 as job


class FrozenDiagnosticsTest(unittest.TestCase):
    def fixture(self):
        train=[dict(record_key='t',category='Nhà ở',pipeline_group='train',location_feature='Cẩm Lệ')]
        validation=[dict(record_key='v',category='Nhà ở',source='fixture',pipeline_group='val',location_feature='Cẩm Lệ',
                         area_sqm='80',price_million='1000',ward_source='')]
        features=[dict(record_key='t'),dict(record_key='v',category='Nhà ở',model_split='validation',
                  rooms_completed='',floors_claim='',access_claim='')]
        predictions=[dict(record_key='v',arm=arm,category='Nhà ở',source='fixture',pipeline_group='val',
                          actual_million='1000',predicted_million='1200',absolute_error_million='200') for arm in ['all','control']]
        return train,validation,features,predictions

    def test_metrics_keep_currency_bias_and_percentage_thresholds(self):
        score=job.score([dict(actual_million=1000,predicted_million=1200),dict(actual_million=2000,predicted_million=1000)])
        self.assertEqual(score['mae_million'],600)
        self.assertEqual(score['mape_pct'],35)
        self.assertEqual(score['within_20pct'],50)
        self.assertEqual(score['above_50pct'],0)
        self.assertEqual(score['signed_mean_error_million'],-400)

    def test_cohort_join_is_by_id_not_position_and_preserves_missing(self):
        inputs=self.fixture()
        original=copy.deepcopy(inputs)
        result=job.join_rows(*inputs)
        self.assertEqual(result[0]['record_key'],'v')
        self.assertEqual(result[0]['rooms_status'],'missing')
        self.assertEqual(inputs,original)

    def test_duplicate_missing_and_changed_labels_are_rejected(self):
        for mode in ['duplicate','missing','label','group']:
            train,validation,features,predictions=self.fixture()
            if mode=='duplicate':predictions.append(dict(predictions[0]))
            if mode=='missing':predictions.pop()
            if mode=='label':predictions[0]['actual_million']='999'
            if mode=='group':train[0]['pipeline_group']='val'
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                job.join_rows(train,validation,features,predictions)

    def test_small_groups_are_marked_and_support_does_not_use_errors(self):
        rows=job.join_rows(*self.fixture())
        self.assertTrue(all(r['small_group'] for r in job.segments(rows)))
        train,validation,_,_=self.fixture()
        result=job.coverage(train,validation,{'Cẩm Lệ':'Cẩm Lệ'})
        self.assertEqual(result[0]['planning_gap'],9)
        self.assertEqual(job.coverage(train,validation,{})[0]['action'],'source_review_location')
        self.assertEqual(job.coverage(train,validation,{})[0]['planning_gap'],0)

    def test_nonfinite_and_nonpositive_prices_are_rejected(self):
        for price in [float('nan'),float('inf'),0,-1]:
            with self.subTest(price=price),self.assertRaises(ValueError):
                job.score([dict(actual_million=price,predicted_million=100)])


if __name__=='__main__':unittest.main()
