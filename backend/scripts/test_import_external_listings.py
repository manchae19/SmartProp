"""Importer regression tests; all MySQL subprocesses are mocked."""
from collections import Counter
from contextlib import redirect_stdout
import copy
import csv
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('existing_importer',Path(__file__).with_name('import_external_listings.py'))
imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)
IDENTITY=json.dumps({'version':'8.0.46','port':3306,'database':'smartprop'})+'\n'
HISTORY='\n'.join(json.dumps(r) for r in [
 {'version':'13','type':'BASELINE','success':1,'checksum':None},
 {'version':'14','type':'SQL','success':1,'checksum':-1382804267}])+'\n'

class ImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with imp.DEFAULT_CSV.open(encoding='utf-8-sig',newline='') as f:cls.records=list(csv.DictReader(f))
        with redirect_stdout(io.StringIO()):cls.groups=imp.run_quality_gate(cls.records)

    def test_real_source_quality_dedup_and_holdout_contract(self):
        self.assertEqual(3204,len(self.records))
        self.assertEqual(3204,len({r['record_key'] for r in self.records}))
        self.assertEqual({'VALID':1723,'NEEDS_REVIEW':1419,'REJECTED':62},dict(Counter(r['quality_status'] for r in self.records)))
        self.assertEqual(332,len(self.groups))
        self.assertEqual(1024,sum(r['is_duplicate'] for r in self.records))
        self.assertEqual(983,sum(r['protected_holdout'].lower()=='true' for r in self.records))
        self.assertTrue(all(r['verification_status']=='UNVERIFIED' for r in self.records))
        self.assertEqual(1024,sum(g['listing_count'] for g in self.groups))

    def test_group_area_ranges_are_populated(self):
        for group in self.groups:
            self.assertIsNotNone(group['min_area'])
            self.assertLessEqual(group['min_area'],group['max_area'])

    def test_sql_is_transactional_dml_only_on_external_tables(self):
        sql=imp.build_import_sql(self.records,self.groups)
        self.assertNotRegex(sql,r'(?i)\b(?:CREATE|ALTER|DROP|TRUNCATE|DELETE|REPLACE|USE|FOREIGN_KEY_CHECKS)\b')
        self.assertEqual(1,sql.count('START TRANSACTION;'))
        self.assertTrue(sql.endswith('COMMIT;'))
        self.assertEqual({'external_duplicate_groups','external_listings'},set(re.findall(r'INSERT INTO\s+(\w+)',sql)))
        self.assertEqual(3204,sql.count('INSERT INTO external_listings'))
        self.assertEqual(332,sql.count('INSERT INTO external_duplicate_groups'))
        self.assertIn('is_protected_holdout OR VALUES(is_protected_holdout)',sql)

    def test_unicode_quotes_and_backslashes_are_not_executable_sql(self):
        text="Đà Nẵng\\'; DROP DATABASE smartprop; --"
        encoded=imp.escape_sql(text)
        self.assertNotIn('DROP',encoded)
        self.assertEqual(text,bytes.fromhex(encoded.split("'")[1]).decode('utf8'))
        self.assertEqual('1',imp.escape_sql(True))
        self.assertEqual('NULL',imp.escape_sql(None))
        self.assertEqual('123.45',imp.escape_sql(Decimal('123.45')))

    def test_nonfinite_numeric_rejected(self):
        for val in [float('nan'),float('inf'),Decimal('NaN')]:
            with self.subTest(value=str(val)),self.assertRaises(ValueError):imp.escape_sql(val)

    def test_naive_observation_time_rejected_before_connection(self):
        row=copy.deepcopy(self.records[0]);row['collected_at']='2026-10-10T10:00:00'
        with self.assertRaisesRegex(ValueError,'timezone'),patch.object(imp.subprocess,'run') as client:
            imp.import_to_mysql([row],[],password='fixture_not_a_real_secret')
        client.assert_not_called()

    def test_wrong_targets_rejected_without_client(self):
        for overrides in [{'port':13306},{'host':'localhost'},{'database':'smartprop_local_demo'}]:
            with self.subTest(overrides=overrides),patch.object(imp.subprocess,'run') as client:
                with self.assertRaisesRegex(ValueError,'Only MySQL Local'):
                    imp.import_to_mysql([],[],password='fixture_not_a_real_secret',**overrides)
                client.assert_not_called()

    def responses(self,outputs):
        return [subprocess.CompletedProcess([],0,stdout=value,stderr='') for value in outputs]

    def test_credentials_only_in_child_environment_and_no_ddl(self):
        replies=self.responses([IDENTITY,HISTORY,'0\n','', '3204\n','3204\n','332\n'])
        secret='fixture_not_a_real_secret'
        with patch.object(imp.subprocess,'run',side_effect=replies) as client:
            result=imp.import_to_mysql(self.records,self.groups,user='root',password=secret)
            self.assertEqual({'rows':3204,'unique_keys':3204,'groups':332},result)
            for call in client.call_args_list:
                self.assertNotIn(secret,' '.join(call.args[0]))
                self.assertNotIn('--force',call.args[0])
            batch=client.call_args_list[3].kwargs['input']
            self.assertTrue(batch.startswith('SET NAMES utf8mb4;'))
            self.assertNotRegex(batch,r'(?i)\bCREATE\s+TABLE\b')

    def test_bad_identity_history_or_verified_rows_stop_before_import(self):
        sequences=[self.responses(['{"version":"8.0.46","port":13306,"database":"smartprop"}\n']),
            self.responses([IDENTITY,'[]\n']),self.responses([IDENTITY,HISTORY,'1\n'])]
        for responses in sequences:
            with self.subTest(length=len(responses)),patch.object(imp.subprocess,'run',side_effect=responses) as client:
                with self.assertRaises((RuntimeError,TypeError)):
                    imp.import_to_mysql([],[],password='fixture_not_a_real_secret')
                self.assertTrue(all('START TRANSACTION' not in c.kwargs['input'] for c in client.call_args_list))

    def test_client_failure_stops_and_redacts_secret(self):
        secret='fixture_not_a_real_secret'
        failure=subprocess.CompletedProcess([],1,stdout='',stderr='client error '+secret)
        with patch.object(imp.subprocess,'run',return_value=failure) as client:
            with self.assertRaisesRegex(RuntimeError,'REDACTED') as err:
                imp.import_to_mysql([],[],password=secret)
            self.assertNotIn(secret,str(err.exception))
            self.assertEqual(1,client.call_count)

if __name__=='__main__':unittest.main()
