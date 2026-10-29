import json
import unittest

import build_reference_support_v6 as job


def rows(n):
    return [dict(record_key='private:'+str(i),pipeline_group='group:'+str(i),model_split='train',reserved_splits='train',
        category='Nhà ở',location_feature='Sơn Trà',area_sqm=str(40+i),price_million='PRIVATE_PRICE',
        detail_url='PRIVATE_URL',description='PRIVATE_PERSON') for i in range(n)]


class ProfileBuilderTests(unittest.TestCase):
    def test_aggregate_contains_no_listing_or_price_fields_and_hides_sparse_area(self):
        result=job.profile(rows(4),reference_manifest_sha256='manifest')
        self.assertEqual(result['reference_groups'],4)
        cell=result['categories']['Nhà ở']['Sơn Trà']
        self.assertIsNone(cell['area_percentiles_sqm'])
        serialized=json.dumps(result,ensure_ascii=False)
        for value in ['private:','PRIVATE_PRICE','PRIVATE_URL','PRIVATE_PERSON','record_key','price_million']:
            self.assertNotIn(value,serialized)

    def test_ten_samples_get_linear_descriptive_area_percentiles(self):
        result=job.profile(rows(10),reference_manifest_sha256='manifest')
        self.assertEqual(result['categories']['Nhà ở']['Sơn Trà']['area_percentiles_sqm'],dict(p05=40.45,p95=48.55))

    def test_duplicate_or_reserved_group_and_invalid_area_rejected(self):
        sample=rows(4)
        for altered in [sample+[dict(sample[0],record_key='other')],
                        sample+[dict(sample[0],pipeline_group='other')],
                        [dict(r,reserved_splits='test') for r in sample],
                        [dict(r,area_sqm='nan') for r in sample]]:
            with self.assertRaises(ValueError):job.profile(altered,reference_manifest_sha256='manifest')


if __name__=='__main__':unittest.main()
