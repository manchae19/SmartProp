import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import prepare_recovered_external as p

class RecoveryPlannerTest(unittest.TestCase):
    def test_sql_preview_uses_external_insert_only_and_escapes_provenance(self):
        row=dict(record_key='s:1',source='s',source_listing_id='1',title="Unicode nhà; quote'",detail_url='https://example.invalid/1',
            category='Nhà ở',district='Hải Châu',address_raw='',transaction_basis='ARCHIVED_SOURCE_SALE_EVIDENCE',
            price_vnd='2350000001',price_million='2350.000001',area_sqm='80',quality_status='VALID',quality_issues='[]',
            duplicate_group='',protected_holdout=False,collected_at='',evidence_sha256='unit-fixture-hash')
        sql=p.build_insert_only_preview([row],[])
        self.assertIn('LEFT JOIN external_listings AS existing_row',sql)
        self.assertIn('WHERE existing_row.record_key IS NULL',sql)
        self.assertIn('2350000001',sql)
        self.assertNotIn(row['title'],sql)
        self.assertNotIn('ON DUPLICATE KEY UPDATE',sql)
        self.assertNotIn('INSERT INTO properties',sql)
        self.assertIn('raw_metadata',sql)
        self.assertTrue(sql.endswith('COMMIT;\n'))
    def test_dedup_union_keeps_pipeline_siblings_and_protected_transitive_links(self):
        result=p.merged_groups(['new1','new2','old-held','separate'],[['new1','new2'],['new2','old-held']])
        self.assertEqual({'new1','new2','old-held'},result['new1'])
        self.assertEqual({'separate'},result['separate'])
    def test_idempotent_insert_only_preserves_existing_verified_record(self):
        old={'record_key':'a','verification_status':'VERIFIED','protected_holdout':True}
        staged=[{'record_key':'a','verification_status':'UNVERIFIED'}, {'record_key':'b','verification_status':'UNVERIFIED'}, {'record_key':'b'}]
        before=copy.deepcopy(staged)
        first=p.new_records_only(staged,{old['record_key']})
        self.assertEqual(['b'],[r['record_key'] for r in first])
        self.assertEqual([],p.new_records_only(staged,{'a','b'}))
        self.assertEqual(staged,before);self.assertEqual(old['verification_status'],'VERIFIED')

    def test_missing_evidence_and_sale_never_default_to_sale(self):
        row={'record_key':'s:1','evidence_path':'not-a-real-cache-file','detail_url':'https://example.invalid/1'}
        reasons=p.evidence_reasons(row,{}, {})
        self.assertIn('SALE_NOT_EVIDENCED',reasons)
        self.assertIn('MISSING_OR_UNSAFE_EVIDENCE_PATH',reasons)

    def test_cached_hash_redirect_and_mismatched_price_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cache=root/'ai-services/app/data/processed/collection_source_review/detail_cache'
            cache.mkdir(parents=True);html=cache/'s_1.html';html.write_bytes(b'archived unit fixture')
            h=hashlib.sha256(html.read_bytes()).hexdigest()
            r={'record_key':'s:1','evidence_path':str(html.relative_to(root)),'detail_url':'https://example.invalid/1',
                'normalized_category':'Nhà ở','normalized_district':'Hải Châu','normalized_price_million':'2350.000001',
                'normalized_price_vnd':'2350000001','normalized_area_sqm':'80','normalized_transaction_type':'SALE'}
            evidence={'record_key':'s:1','detail_sha256':h,'http_status':200,'identity_verified':True,'structure_verified':True,
                'sale_verified':True,'category':'Nhà ở','address_raw':'Hải Châu, Đà Nẵng','price_million':'2350.000001','area_sqm':'80','flags':[]}
            manifest={'sha256':h,'requested_url':r['detail_url'],'response_url':r['detail_url'],'http_status':200}
            with patch.object(p,'ROOT',root):
                self.assertEqual([],p.evidence_reasons(r,{'s:1':evidence},{'s:1':manifest}))
                manifest['response_url']='https://example.invalid/2'
                self.assertIn('SOURCE_URL_OR_REDIRECT_MISMATCH',p.evidence_reasons(r,{'s:1':evidence},{'s:1':manifest}))
                evidence['price_million']='2350'
                self.assertIn('SOURCE_PRICE_MILLION_MISMATCH',p.evidence_reasons(r,{'s:1':evidence},{'s:1':manifest}))
                html.write_bytes(b'changed')
                self.assertIn('EVIDENCE_HASH_MISMATCH',p.evidence_reasons(r,{'s:1':evidence},{'s:1':manifest}))

    def test_readonly_script_has_no_database_write_execution_path(self):
        import ast
        tree=ast.parse(Path(p.__file__).read_text(encoding='utf8'))
        forbidden={'import_to_mysql','build_import_sql','flyway','execute','executemany','commit'}
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in forbidden for n in ast.walk(tree)))
        with patch('sys.argv',['planner','--apply']):
            with self.assertRaises(SystemExit):p.main()

if __name__=='__main__':unittest.main()
