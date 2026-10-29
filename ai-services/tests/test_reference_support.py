import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SERVICE=Path(__file__).resolve().parents[1]
if str(SERVICE) not in sys.path:sys.path.insert(0,str(SERVICE))
from app.core import reference_support as support
from fastapi.testclient import TestClient
from main import create_app


def fixture():
    return dict(version=support.PROFILE_VERSION,model_run=support.V6_RUN,
        model_manifest_sha256=support.V6_MANIFEST_SHA256,reference_groups=24,
        policy=dict(low_reference_groups_below=10,area_percentiles=[.05,.95],minimum_groups_for_area_range=10),
        categories={'Nhà ở':{'thin':dict(reference_groups=4,area_percentiles_sqm=None),
                             'covered':dict(reference_groups=20,area_percentiles_sqm=dict(p05=40,p95=100))},
                    'Đất nền':{},'Căn hộ chung cư':{}})


class SupportProfileTests(unittest.TestCase):
    def load(self,value,**options):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'profile.json';raw=json.dumps(value,ensure_ascii=False).encode('utf8');path.write_bytes(raw)
            return support.ReferenceSupport(path=path,expected_sha=hashlib.sha256(raw).hexdigest(),**options)

    def test_sparse_unknown_and_covered_area_boundaries(self):
        profile=self.load(fixture())
        self.assertIn('4 nhóm',profile.warnings('Nhà ở','thin',80)[0])
        self.assertEqual(profile.warnings('Nhà ở','not-known',80),[support.UNAVAILABLE])
        for area in [40,80,100]:self.assertEqual(profile.warnings('Nhà ở','covered',area),[])
        for area in [39.99,100.01]:self.assertIn('khoảng phổ biến',profile.warnings('Nhà ở','covered',area)[0])

    def test_missing_bad_hash_or_other_release_has_no_claimed_support(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'absent.json'
            self.assertEqual(support.ReferenceSupport(path=path).warnings('Nhà ở','thin',80),[support.UNAVAILABLE])
            path.write_text('{}',encoding='utf8')
            self.assertIsNone(support.ReferenceSupport(path=path,expected_sha='wrong').profile)
        self.assertIsNone(self.load(fixture(),model_run='another').profile)
        self.assertIsNone(self.load(fixture(),model_manifest_sha='another').profile)

    def test_invalid_counts_ranges_policy_or_structure_fail_closed(self):
        samples=[]
        for count in [True,0,-1,'4']:
            value=fixture();value['categories']['Nhà ở']['thin']['reference_groups']=count;samples.append(value)
        for area in [dict(p05=101,p95=100),dict(p05=float('nan'),p95=100),dict(p05=True,p95=100),None]:
            value=fixture();value['categories']['Nhà ở']['covered']['area_percentiles_sqm']=area;samples.append(value)
        value=fixture();value['reference_groups']=25;samples.append(value)
        value=fixture();value['policy']['low_reference_groups_below']=1;samples.append(value)
        samples += [[],{'version':support.PROFILE_VERSION}]
        for value in samples:
            with self.subTest(value=value):self.assertIsNone(self.load(value).profile)

    def test_shipped_reference_is_bound_to_release_and_clean_cohort(self):
        profile=support.ReferenceSupport().profile
        self.assertIsNotNone(profile)
        self.assertEqual(profile['reference_groups'],2213)
        self.assertIn('not the exact complete',profile['reference_semantics'])
        self.assertEqual(sum(len(v) for v in profile['categories'].values()),56)


class ApiSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=create_app();cls.client=TestClient(cls.app);cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):cls.client.__exit__(None,None,None)

    def test_thin_location_warns_without_changing_price_or_api_keys(self):
        payload=dict(category='Căn hộ chung cư',location_feature='Liên Chiểu',area_sqm=80)
        response=self.client.post('/predict',json=payload);self.assertEqual(response.status_code,200)
        result=response.json();self.assertTrue(any('4 nhóm' in value for value in result['warnings']))
        predictor=self.app.state.predictor
        with patch.object(predictor.reference_support,'warnings',return_value=[]):
            without=self.client.post('/predict',json=payload).json()
        self.assertEqual(result.keys(),without.keys())
        for field in ['predicted_asking_price_vnd','predicted_asking_price_million','features_used','missing_features','model_run']:
            self.assertEqual(result[field],without[field])

    def test_unavailable_profile_keeps_api_working_with_warning(self):
        predictor=self.app.state.predictor
        with patch.object(predictor.reference_support,'profile',None):
            response=self.client.post('/predict',json=dict(category='Nhà ở',location_feature='Cẩm Lệ',area_sqm=80))
        self.assertEqual(response.status_code,200)
        self.assertIn(support.UNAVAILABLE,response.json()['warnings'])


if __name__=='__main__':unittest.main()
