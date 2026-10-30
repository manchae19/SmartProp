import json
import unittest
import numpy as np
from analyze_xgboost_validation import source_features, content_flags
from experiment_xgboost_features import schema, encode


class ValidationFeatureTests(unittest.TestCase):
    def row(self,**raw):
        return dict(raw_json=json.dumps(raw),title='',category='Nhà ở',area_sqm='100',price_million='5000',location_feature='Hải Châu')

    def test_missing_invalid_rooms_not_zero(self):
        for value in ['',0,'100','3 tỷ']:
            self.assertIsNone(source_features(self.row(rooms=value))['rooms'])
        self.assertEqual(source_features(self.row(rooms='3 Phòng ngủ'))['rooms'],3)

    def test_encoder_train_only_unseen_and_land_rooms(self):
        train=[self.row(ward='Phường Bình Hiên',rooms='3') for _ in range(3)]
        spec=schema(train)
        val=self.row(ward='Phường Mới',rooms='5');val['category']='Đất nền'
        features=encode([val],spec)[0]
        self.assertEqual(len(features),len(spec['feature_names']))
        self.assertTrue(np.isnan(features[1]))
        self.assertEqual(features[2],1)
        self.assertEqual(features[4],1)
        self.assertNotIn('Hải Châu|moi',spec['wards'])

    def test_payment_schedule_is_review_cue_not_label_correction(self):
        row=self.row();row['title']='Chỉ 2 tỷ/căn đóng 50% đến 2027'
        self.assertIn('payment_schedule_total_price_needs_source_check',content_flags(row))
        self.assertEqual(row['price_million'],'5000')


if __name__=='__main__':unittest.main()
