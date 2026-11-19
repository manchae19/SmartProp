import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.rag.planning_data import *

class PlanningTests(unittest.TestCase):
    def setUp(self):
        now=datetime.now(timezone.utc)
        self.source={"id":"s1","url":"https://hoaxuan.danang.gov.vn/test","title":"Fixture public notice","sha256":"a"*64,"checked_at":(now-timedelta(days=1)).isoformat(),"document_date":"2025-01-01","publication_date":None}
        self.r={"id":"HX-LAND-001","revision":1,"kind":"AUCTION_LAND_CATALOG","parent_ids":[],"source_ids":["s1"],"input_sha256":"b"*64,"facts":{k:{"value":v,"source_ids":["s1"],"basis":"FIXTURE","scope":"PROJECT_PHASE_LOT"} for k,v in {"name":"Fixture Project","phase":"1B","lot_code":"A2-1","area_sqm":None,"legal_event_status":"AUCTION_2026_CATALOG_NOT_AUCTION_OPENING"}.items()}}
        self.b={"format":"SMARTPROP_PLANNING_REVIEW_V1","records":[self.r],"sources":[self.source]}
    def approve(self,b):
        m=initial_review(b);now=datetime.now(timezone.utc)
        for d in list(m['sources'].values())+[d for r in m['records'].values() for d in [r['record'],*r['fields'].values()]]:
            d.update(approval="APPROVED",permission="PERMITTED",permission_basis="TEST FIXTURE ONLY",verification="SOURCE_CHECKED",reviewer="test",reviewed_at=(now-timedelta(hours=1)).isoformat(),review_due_at=(now+timedelta(days=1)).isoformat())
        return m
    def test_pending_has_no_snapshot(self):
        s,r=build_snapshot(self.b,initial_review(self.b));self.assertIsNone(s);self.assertFalse(r['feature_enabled'])
    def test_unknown_permission_stays_blocked(self):
        m=self.approve(self.b);m['records'][self.r['id']]['record']['permission']='UNKNOWN';self.assertIsNone(build_snapshot(self.b,m)[0])
    def test_source_permission_required(self):
        m=self.approve(self.b);m['sources']['s1']['permission']='UNKNOWN';self.assertIsNone(build_snapshot(self.b,m)[0])
    def test_only_reviewed_fields_exported(self):
        m=self.approve(self.b);m['records'][self.r['id']]['fields']['area_sqm']['approval']='PENDING';s,_=build_snapshot(self.b,m);self.assertNotIn('area_sqm',s['records'][0]['facts'])
    def test_changed_bundle_rejects_review(self):
        m=self.approve(self.b);self.b['sources'][0]['title']='Changed'
        with self.assertRaises(ValueError):build_snapshot(self.b,m)
    def test_changed_field_hash_rejected(self):
        m=self.approve(self.b);m['records'][self.r['id']]['fields']['lot_code']['value_hash']='c'*64
        with self.assertRaises(ValueError):build_snapshot(self.b,m)
    def test_bad_area_and_legal_state(self):
        for key,value in [('area_sqm',-1),('area_sqm',float('nan')),('legal_event_status','FULLY_LEGAL')]:
            b=copy.deepcopy(self.b);b['records'][0]['facts'][key]['value']=value
            with self.assertRaises(ValueError):validate_bundle(b)
    def test_source_url_hash_dates(self):
        for key,value in [('url','http://localhost/'),('sha256','bad'),('checked_at','2026-01-01'),('document_date','2099-01-01')]:
            b=copy.deepcopy(self.b);b['sources'][0][key]=value
            with self.assertRaises(ValueError):validate_bundle(b)
    def test_relationships(self):
        self.b['records'][0]['parent_ids']=['HX-RE-999']
        with self.assertRaises(ValueError):validate_bundle(self.b)
    def test_lookup_operations_and_ambiguous_phase(self):
        row=copy.deepcopy(self.r);row['id']='HX-LAND-002';row['facts']['phase']['value']='2';self.b['records'].append(row)
        s,_=build_snapshot(self.b,self.approve(self.b))
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'snapshot.json';p.write_text(json.dumps(s))
            tool=PlanningLookup(p,enabled=True)
            self.assertEqual('NEEDS_CLARIFICATION',tool.query('LOT_LOOKUP',lot='A2-1')['status'])
            self.assertEqual(1,len(tool.query('LOT_LOOKUP',project='Fixture',phase='2',lot='A2-1')['items']))
            self.assertEqual(2,len(tool.query('AUCTION_CATALOG',year=2026)['items']))
            self.assertEqual('OUTSIDE_COVERAGE',tool.query('AUCTION_CATALOG',year=2025)['status'])
            self.assertEqual([],tool.query('PROJECT_LIST')['items'])
            self.assertEqual(2,len(tool.query('PLANNING_STATUS')['items']))
    def test_disabled_and_tamper(self):
        self.assertEqual('DISABLED',PlanningLookup('/not/read').query('PROJECT_LIST')['status'])
        s,_=build_snapshot(self.b,self.approve(self.b));s['records'][0]['facts']['name']['value']='Changed'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'s.json';p.write_text(json.dumps(s))
            with self.assertRaises(ValueError):PlanningLookup(p,enabled=True).query('PROJECT_LIST')
    def test_expired_review(self):
        m=self.approve(self.b);m['sources']['s1']['reviewed_at']='2025-01-01T00:00:00+00:00';m['sources']['s1']['review_due_at']='2025-02-01T00:00:00+00:00';self.assertIsNone(build_snapshot(self.b,m)[0])
    def test_project_list_fixture(self):
        self.b["records"][0]["kind"]="PROJECT_PROFILE"
        s,_=build_snapshot(self.b,self.approve(self.b))
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"s.json";p.write_text(json.dumps(s))
            self.assertEqual(1,len(PlanningLookup(p,enabled=True).query("PROJECT_LIST")["items"]))
    def test_duplicate_ids_rejected(self):
        self.b["records"].append(copy.deepcopy(self.r))
        with self.assertRaises(ValueError):validate_bundle(self.b)
    def test_real_normalization_offline(self):
        from scripts.build_planning_snapshot import prepare
        root=Path(__file__).resolve().parents[2]/'SMARTPROP_DATA/processed'
        if not (root/'hoa-xuan-real-estate-sources/20261118T170115+0700/records.json').is_file():
            self.skipTest('Optional offline real dataset is not distributed with application source')
        b=prepare(root/'hoa-xuan-real-estate-sources/20261118T170115+0700',root/'hoa-xuan-planning-land/20261118T171234+0700')
        rs,_=validate_bundle(b);self.assertEqual(50,len(rs));by={r.id:r for r in rs}
        self.assertNotIn('project_area_ha',by['HX-RE-002'].facts)
        self.assertEqual(1.8,by['HX-RE-002'].facts['combined_area_ha'].value)
        self.assertEqual(10605,by['HX-RE-003'].facts['preliminary_land_area_sqm'].value)
        self.assertEqual(1.2,by['HX-RE-003'].facts['planning_area_ha'].value)
        self.assertEqual(7,sum(r.kind=='AUCTION_LAND_CATALOG' for r in rs))
        self.assertEqual(26,sum(r.kind=='PLANNING_LOT_CONSULTATION' for r in rs))
        self.assertIsNone(build_snapshot(b,initial_review(b))[0])
if __name__=='__main__':unittest.main()
