"""Unit and isolated in-memory SQLite tests. Never writes to MySQL.

SQLite models insert-only identity/transaction rules, not MySQL DECIMAL/dialect.
"""
import copy
import csv
import json
import sqlite3
import unittest
from decimal import Decimal
from pathlib import Path
import final_review_recovered as review

class ReviewRulesTest(unittest.TestCase):
    def test_url_tracking_removed_identity_query_kept(self):
        self.assertEqual('https://nhadat.cafeland.vn/a-12.html?id=12',review.normalized_url('http://nhadat.cafeland.vn/a-12.html/?utm_source=x&id=12#fragment'))
        self.assertNotEqual(review.normalized_url('https://example.invalid/?id=12'),review.normalized_url('https://example.invalid/?id=13'))
        for value in ['javascript:alert(1)','https://user:pass@example.invalid/a','https://example.invalid:444/a']:
            with self.assertRaises(ValueError):review.normalized_url(value)

    def test_generic_location_is_not_an_asset_fingerprint(self):
        self.assertEqual('',review.specific_address('Quận Hải Châu, Đà Nẵng','Hải Châu'))
        self.assertTrue(review.specific_address('Đường Lý Văn Tố, Phường Phước Mỹ, Quận Sơn Trà, Đà Nẵng','Sơn Trà'))

    def test_holdout_risk_precedes_manual_and_source_review(self):
        self.assertEqual('BLOCKED',review.classify({'HOLDOUT'}, {'PRICE'}, {'PENDING'}))
        self.assertEqual('NEEDS_MANUAL_REVIEW',review.classify(set(), {'PRICE'}, {'PENDING'}))
        self.assertEqual('NEEDS_SOURCE_VERIFICATION',review.classify(set(),set(),{'PENDING'}))
        self.assertEqual('READY_FOR_INTERNAL_IMPORT',review.classify(set(),set(),set()))

    def test_unit_price_screen_never_changes_price(self):
        value=Decimal('175000000000')
        self.assertIn('UNIT_PRICE_ABOVE_INTERNAL_REVIEW_BAND',review.peer_outlier(value,[]))
        self.assertEqual(Decimal('175000000000'),value)
        self.assertEqual([],review.peer_outlier(Decimal('50000000'),[]))

    def test_similar_title_price_area_is_risk_not_physical_proof(self):
        base={'record_key':'s:1','title':'Căn nhà mặt tiền rất đẹp tại Hải Châu','category':'HOUSE','district':'Hải Châu','price':'2350000000','area_sqm':'80'}
        a=review.prepared_item(base);b=review.prepared_item(dict(base,record_key='s:2'),holdout=True)
        self.assertIn('TITLE_SIMILARITY65_PRICE10_AREA3',review.match_rules(a,b))
        self.assertEqual([],review.match_rules(a,a))
        self.assertTrue(b['holdout'])

class IsolatedSQLiteImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out=review.OUT
        cls.ready=review.prior.rows(out/'ready_for_internal_import.csv')
        cls.existing=json.loads((review.BEFORE/'mysql-external-snapshot.json').read_text(encoding='utf8'))
        assert len(cls.ready)==17 and len(cls.existing)==3204

    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.isolation_level=None
        # Mirror actual uniqueness (record_key only), deliberately not an invented
        # UNIQUE(source,source_listing_id) absent from MySQL.
        self.db.executescript('CREATE TABLE listings(record_key TEXT PRIMARY KEY,source TEXT NOT NULL,sid TEXT,verification TEXT,holdout INTEGER,price TEXT,grp TEXT); CREATE TABLE groups_table(id TEXT PRIMARY KEY);')
        for r in self.existing:
            self.db.execute('INSERT INTO listings VALUES(?,?,?,?,?,?,?)',(r['record_key'],r['source'],r['source_listing_id'],r['verification_status'],r['is_protected_holdout'],str(r['price_million']),r['duplicate_group']))
            if r['duplicate_group']:self.db.execute('INSERT OR IGNORE INTO groups_table VALUES(?)',(r['duplicate_group'],))

    def tearDown(self):self.db.close()

    def snapshot(self):
        return (self.db.execute('SELECT * FROM listings ORDER BY record_key').fetchall(),self.db.execute('SELECT * FROM groups_table ORDER BY id').fetchall())

    def apply_simulated(self,rows,fail_after=None):
        inserted=[];new_groups=[]
        self.db.execute('BEGIN')
        try:
            for r in rows:
                if r['decision']!='READY_FOR_INTERNAL_IMPORT' or r['verification_status']!='UNVERIFIED' or review.prior.truth(r['protected_holdout']):raise ValueError('Unapproved row')
                if r['record_key']!=r['source']+':'+r['source_listing_id']:raise ValueError('Noncanonical source identity')
                existing=self.db.execute('SELECT record_key FROM listings WHERE source=? AND sid=?',(r['source'],r['source_listing_id'])).fetchall()
                if existing:
                    if existing!=[(r['record_key'],)]:raise ValueError('Source identity alias collision')
                    continue
                group=r['final_suspected_cluster'] if len(r['cluster_members'].split('|'))>1 or r['previous_duplicate_group'] else None
                if group and not self.db.execute('SELECT 1 FROM groups_table WHERE id=?',(group,)).fetchone():
                    self.db.execute('INSERT INTO groups_table VALUES(?)',(group,));new_groups.append(group)
                self.db.execute('INSERT INTO listings VALUES(?,?,?,?,?,?,?)',(r['record_key'],r['source'],r['source_listing_id'],'UNVERIFIED',0,r['price_vnd'],group))
                inserted.append(r['record_key'])
                if fail_after is not None and len(inserted)==fail_after:raise RuntimeError('Synthetic failure inside isolated transaction')
            if self.db.execute('SELECT source,sid FROM listings GROUP BY source,sid HAVING COUNT(*)>1').fetchall():raise ValueError('Duplicate source identities')
            self.db.execute('COMMIT');return inserted,new_groups
        except Exception:self.db.execute('ROLLBACK');raise

    def test_first_import_repeat_preserves_983_holdouts_and_existing_rows(self):
        before=self.snapshot();inserted,groups=self.apply_simulated(self.ready)
        self.assertEqual(17,len(inserted));self.assertEqual(3221,self.db.execute('SELECT COUNT(*) FROM listings').fetchone()[0])
        self.assertEqual(983,self.db.execute('SELECT COUNT(*) FROM listings WHERE holdout=1').fetchone()[0])
        for old in before[0]:self.assertEqual(old,self.db.execute('SELECT * FROM listings WHERE record_key=?',(old[0],)).fetchone())
        first=self.snapshot();again=self.apply_simulated(self.ready)
        self.assertEqual(([],[]),again);self.assertEqual(first,self.snapshot())
        receipt={'engine':'SQLite :memory: ONLY','not_mysql_dialect_test':True,'mysql_writes':0,'before_listings':3204,'after_first':3221,'after_repeat':3221,'first_inserted':17,'repeat_inserted':0,'new_groups':len(groups),'protected_holdout_unchanged':983,'all_existing_rows_unchanged':True}
        (review.OUT/'sqlite-import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')

    def test_mid_transaction_failure_rolls_back_every_insert(self):
        before=self.snapshot()
        with self.assertRaises(RuntimeError):self.apply_simulated(self.ready,fail_after=3)
        self.assertEqual(before,self.snapshot())

    def test_blocked_row_is_rejected_before_any_commit(self):
        before=self.snapshot();rows=copy.deepcopy(self.ready);rows[1]['decision']='BLOCKED'
        with self.assertRaises(ValueError):self.apply_simulated(rows)
        self.assertEqual(before,self.snapshot())

    def test_existing_verified_status_is_never_downgraded(self):
        key=self.existing[0]['record_key']
        # A synthetic VERIFIED state in the isolated clone only, never MySQL.
        self.db.execute('UPDATE listings SET verification=? WHERE record_key=?',('VERIFIED',key))
        old=self.db.execute('SELECT * FROM listings WHERE record_key=?',(key,)).fetchone()
        self.apply_simulated(self.ready)
        self.assertEqual(old,self.db.execute('SELECT * FROM listings WHERE record_key=?',(key,)).fetchone())

    def test_current_db_key_constraint_alone_cannot_protect_source_pairs(self):
        old=self.existing[0]
        self.db.execute('INSERT INTO listings VALUES(?,?,?,?,?,?,?)',('alias:'+old['record_key'],old['source'],old['source_listing_id'],'UNVERIFIED',0,'1',None))
        self.assertTrue(self.db.execute('SELECT 1 FROM listings GROUP BY source,sid HAVING COUNT(*)>1').fetchall())
        before=self.snapshot()
        with self.assertRaises(ValueError):self.apply_simulated(self.ready)
        self.assertEqual(before,self.snapshot())

if __name__=='__main__':unittest.main()
