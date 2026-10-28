import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_property_evidence as audit
import collect_training_property_evidence as collector


class EvidenceAuditTests(unittest.TestCase):
    def test_protected_group_or_reservation_cannot_enter_train_audit(self):
        train = dict(record_key='cafeland:1', pipeline_group='g1', model_split='train', reserved_splits='train')
        val = dict(record_key='cafeland:2', pipeline_group='g2', model_split='validation', reserved_splits='validation')
        audit.validate_cohort(dict(train=[train], validation=[val]), [])
        with self.assertRaises(ValueError):
            audit.validate_cohort(dict(train=[train], validation=[val]), [dict(pipeline_group='g1')])
        with self.assertRaises(ValueError):
            audit.validate_cohort(dict(train=[dict(train, reserved_splits='test')], validation=[val]), [])
        with self.assertRaises(ValueError):
            audit.validate_cohort(dict(train=[train], validation=[dict(val, pipeline_group='g1')]), [])

    def test_unverified_body_does_not_supply_claims(self):
        row = dict(record_key='cafeland:1', category='Nhà ở', price_million='3000', area_sqm='60')
        origin = dict(title='Nhà ở', raw_json=json.dumps(dict(legal_status='Sổ hồng riêng')))
        sources, state, sha = audit.sources_for(row, origin,
            dict(identity_verified=False, description='Nhà kiệt rộng 5m.'), {}, [])
        self.assertEqual(state, 'unavailable_or_unverified')
        self.assertEqual(sha, '')
        self.assertEqual({s['kind'] for s in sources}, {'collected_title', 'structured_legal_status'})

    def test_refresh_is_reparsed_from_html_and_not_backdated(self):
        from test_collect_apartment_pilot import fixture
        body, card = fixture()
        row = dict(record_key=card['record_key'], pipeline_group='group', category='Căn hộ chung cư',
                   price_million='2500', area_sqm='55')
        origin = dict(card, title=card['listing_title'], raw_json='{}')
        record = dict(record_key=row['record_key'], pipeline_group='group', response_sha256=hashlib.sha256(body).hexdigest(),
            description='FAKE EDIT: apartment floor 99', fetch=dict(http_status=200, state='downloaded', response_url=card['detail_url']))
        with tempfile.TemporaryDirectory() as temp, patch.object(audit, 'SUPPLEMENT', Path(temp)):
            path = Path(temp) / 'evidence'
            path.mkdir()
            (path / (record['response_sha256'] + '.html')).write_bytes(body)
            sources, state, sha = audit.sources_for(row, origin, None, {}, [], record)
            self.assertEqual(state, 'refreshed_matching_labels_NOT_ASOF_VERIFIED')
            self.assertEqual(sha, record['response_sha256'])
            self.assertNotIn('FAKE EDIT', sources[-1]['text'])
            wrong_label = dict(row, price_million='9999')
            sources, state, sha = audit.sources_for(wrong_label, origin, None, {}, [], record)
            self.assertEqual(sha, '')


class TargetedCollectorTests(unittest.TestCase):
    def context(self, count):
        rows = [dict(record_key='cafeland:' + str(i), source_listing_id=str(i),
                     pipeline_group='group:' + str(i), detail_url=f'https://nhadat.cafeland.vn/test-{i}.html')
                for i in range(1, count + 1)]
        return rows, dict(max_records=count, input_sha256={'synthetic': 'a' * 64})

    def test_partial_resume_and_completed_run_are_durable_and_do_not_repeat_ids(self):
        calls = []
        class Client:
            def __init__(self, output, delay):
                pass
            def fetch(self, url):
                calls.append(url)
                self.last_url = url
                if len(calls) == 2:
                    raise KeyboardInterrupt()
                return b'<html>not found</html>', 404
        with tempfile.TemporaryDirectory() as temp, patch.object(collector, 'selection', side_effect=self.context):
            first = collector.run(2, temp, Client)
            self.assertEqual(first['status'], 'interrupted')
            self.assertEqual(first['records'], 1)
            second = collector.run(2, temp, Client)
            self.assertEqual(second['records'], 2)
            result = collector.run(2, temp, lambda *_: self.fail('Network reached on completed batch'))
            self.assertEqual(result['status'], 'read_only_completed')
            self.assertEqual(len(calls), 3)
            self.assertFalse((Path(temp) / 'collector.lock').exists())
            records = list((Path(temp) / 'records').glob('*.json'))
            self.assertEqual(len(records), 2)
            self.assertTrue(all(json.loads(p.read_text(encoding='utf8'))['training_allowed'] is False for p in records))

    def test_changed_policy_refused_without_touching_batch(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(collector, 'selection', side_effect=self.context):
            path = Path(temp) / 'plan.json'
            path.write_text('{}', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'policy/selection changed'):
                collector.run(1, temp, lambda *_: self.fail('Network reached'))
            self.assertEqual(path.read_text(encoding='utf8'), '{}')


if __name__ == '__main__':
    unittest.main()
