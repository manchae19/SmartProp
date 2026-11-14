"""Guard/schema tests. No MySQL credentials, connection or writes."""
import importlib.util,sys,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('local_forward',HERE/'flyway-local-forward.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class LocalForwardTest(unittest.TestCase):
    def test_distinct_migration_locations_and_versions(self):
        inventory,wanted=m.migration_inventory()
        self.assertEqual(m.NEW_TABLES,set(wanted))
        self.assertNotIn('valuation_history',wanted)
        local={p.name for p in m.LOCAL.glob('V*.sql')}
        self.assertEqual(m.EXPECTED_LOCAL,local)
        self.assertEqual(m.CANONICAL,m.sha(m.LOCAL/'V14__crawler_external_listings.sql'))
    def test_forward_ddl_copied_exactly_from_standard(self):
        for original,local in [('V13__broker_applications.sql','V17__local_broker_applications.sql'),('V15__profile_avatar_and_google_identity.sql','V18__local_avatar_and_google_identity.sql')]:
            a=(m.ROOT/'database/migrations'/original).read_text(encoding='utf8')
            b=(m.LOCAL/local).read_text(encoding='utf8')
            self.assertTrue(b.endswith(a))
    def test_preserves_index_fk_and_check_contract(self):
        _,wanted=m.migration_inventory()
        self.assertEqual(2,len(wanted['broker_applications']['foreign_keys']))
        self.assertEqual(5,len(wanted['broker_applications']['checks']))
        self.assertIn('uq_broker_application_user',wanted['broker_applications']['indexes'])
        self.assertIn('ix_broker_application_queue',wanted['broker_applications']['indexes'])
        self.assertIn('uq_avatar_storage',wanted['user_avatars']['indexes'])
        self.assertIn('uq_external_subject',wanted['user_external_identities']['indexes'])
        self.assertIn('uq_external_user_provider',wanted['user_external_identities']['indexes'])
    def test_check_expression_literal_and_precedence_not_flattened(self):
        parse=lambda s:m.schema.CheckExpression(s).parse()
        self.assertNotEqual(parse("status='PENDING'"),parse("status='APPROVED'"))
        self.assertNotEqual(parse('a=1 AND (b=2 OR c=3)'),parse('(a=1 AND b=2) OR c=3'))
    def test_query_rejects_writes_and_multiple_statements_before_connection(self):
        client=object.__new__(m.Local)
        for sql in ['DELETE FROM properties','SELECT 1; DROP DATABASE smartprop','CREATE TABLE bad(id INT)']:
            with self.assertRaises(ValueError):client.query(sql)
    def test_forbidden_flyway_goals(self):
        client=object.__new__(m.Local)
        for goal in ['clean','baseline','repair']:
            with self.assertRaises(ValueError):client.flyway(goal)
        with self.assertRaises(ValueError):client.flyway('migrate',standard=True)
    def test_apply_without_review_hash_stops_before_credentials(self):
        with patch.object(sys,'argv',['script','--apply']),patch.object(m,'credentials',side_effect=AssertionError('Must not access credentials')):
            with self.assertRaisesRegex(RuntimeError,'reviewed plan'):m.main()
    def test_maven_profiles_do_not_merge_locations(self):
        ns={'m':'http://maven.apache.org/POM/4.0.0'};root=ET.parse(m.ROOT/'backend/pom.xml').getroot()
        expected={m.PROFILE:'legacy-hybrid-local','standard-migrations':'/migrations'}
        for profile in root.findall('m:profiles/m:profile',ns):
            name=profile.find('m:id',ns).text
            if name in expected:
                loc=profile.findall('.//m:locations/m:location',ns)
                self.assertEqual(1,len(loc));self.assertTrue(loc[0].text.endswith(expected[name]))
                self.assertEqual('false',profile.find('.//m:baselineOnMigrate',ns).text)
                self.assertEqual('true',profile.find('.//m:cleanDisabled',ns).text)
    def test_snapshot_change_never_passes_postcheck(self):
        before={'ddl':{'users':'DDL','flyway_schema_history':'H'},'rowcounts':{'users':0},'checksums':{'users':'1'},'triggers':[],'history':[]}
        after={'ddl':{'users':'CHANGED','flyway_schema_history':'H',**{t:'NEW' for t in m.NEW_TABLES}},'rowcounts':{'users':0},'checksums':{'users':'1'}}
        with self.assertRaisesRegex(RuntimeError,'Existing table changed'):m.check_after(before,after,{})

if __name__=='__main__':unittest.main()
