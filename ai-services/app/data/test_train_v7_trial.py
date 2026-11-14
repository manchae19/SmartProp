import json
import unittest
import numpy as np
import train_v7_trial as job


class HoldoutFeaturesTest(unittest.TestCase):
    def test_asking_price_is_not_a_feature_and_ward_is_not_guessed(self):
        raw=dict(record_key='cafeland:trial',source='cafeland',category='Căn hộ chung cư',
            source_location_parts=json.dumps(['Sơn Trà','Đà Nẵng']),location_feature='Sơn Trà',area_sqm='55',
            rooms='2',price_million='2500',title='Bán căn hộ 2PN',source_category='ban-can-ho-chung-cu',
            description='Căn hộ 55m2 hai phòng ngủ giá bán 2,5 tỷ.',response_sha256='source-sha')
        a,fa,_=job.holdout_features([raw]);b,fb,_=job.holdout_features([dict(raw,price_million='9000')])
        self.assertEqual(a[0]['ward_source'],'')
        spec=job.features.feature_spec(a,'Căn hộ chung cư','all')
        np.testing.assert_equal(job.features.encode(a,fa,spec),job.features.encode(b,fb,spec))


if __name__=='__main__':unittest.main()
