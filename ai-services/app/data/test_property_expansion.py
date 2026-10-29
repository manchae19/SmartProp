import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request
from urllib.robotparser import RobotFileParser

import collect_property_expansion as job
from resume_nhadat_property_expansion import ascii_path


def row(number, area='A'):
    return dict(record_key=f'cafeland:{number}', source='cafeland', source_listing_id=str(number),
                detail_url=f'https://nhadat.cafeland.vn/test-{number}.html', listing_address_raw=area)


class ExpansionTests(unittest.TestCase):
    def test_unicode_path_encoding_preserves_identity_and_existing_escapes(self):
        value = 'https://nhadat24h.net/can-ho-90m²-%C4%91-ID123'
        encoded = ascii_path(value)
        self.assertIn('90m%C2%B2-%C4%91', encoded)
        self.assertEqual(encoded, ascii_path(encoded))
        self.assertEqual(job.audit.parser.audit.sid_url('nhadat24h', value),
                         job.audit.parser.audit.sid_url('nhadat24h', encoded))

    def test_refresh_resumes_only_uncommitted_and_keeps_current_response_time(self):
        plan = dict(rows=[row(1), row(2)], source='cafeland', input_sha256={})
        calls = []
        class Client:
            def __init__(self, *args):
                pass
            def fetch(self, url):
                calls.append(url); self.last_url = url
                if len(calls) == 2:
                    raise KeyboardInterrupt()
                return b'gone', 404
        with tempfile.TemporaryDirectory() as temp, patch.object(job, 'refresh_plan', return_value=plan):
            self.assertEqual(job.refresh('cafeland', temp, Client)['status'], 'interrupted')
            self.assertEqual(job.refresh('cafeland', temp, Client)['total'], 2)
            self.assertEqual(job.refresh('cafeland', temp, lambda *_: self.fail('network'))['status'], 'read_only_completed')
            records = job.verified_records(Path(temp))
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(r['observed_at'].endswith('+00:00') and not r['training_allowed'] for r in records))
            self.assertFalse((Path(temp) / 'collector.lock').exists())

    def test_new_batch_excludes_history_and_caps_localities(self):
        cards = [row(0), row(1), row(2), row(3, 'B')]
        plan = dict(target=2, start_page=18, max_pages=2, max_per_locality=1)
        calls = []
        class Client:
            def __init__(self, *args):
                pass
            def fetch(self, url):
                calls.append(url); self.last_url = url
                return b'listing' if 'page-' in url else b'detail', 200
        with tempfile.TemporaryDirectory() as temp, patch.object(job, 'new_plan', return_value=({'cafeland:0'}, plan)), \
                patch.object(job.cafe, 'listing_page', return_value=(cards, set())), \
                patch.object(job.pilot, 'location', side_effect=lambda r, _: (r['address_raw'], 'fixture')):
            result = job.collect_new(temp, Client)
            self.assertEqual(result['total'], 2)
            self.assertEqual({r['record_key'] for r in job.verified_records(Path(temp))}, {'cafeland:1', 'cafeland:3'})
            cp = json.loads((Path(temp) / 'checkpoint.json').read_text(encoding='utf8'))
            self.assertEqual((cp['historical_skipped'], cp['quota_skipped']), (1, 1))
            self.assertEqual(job.collect_new(temp, lambda *_: self.fail('network'))['status'], 'read_only_completed')
            self.assertEqual(len(calls), 3)

    def test_policy_refusal_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(job, 'refresh_plan', return_value={'rows': []}):
            path = Path(temp) / 'plan.json'; path.write_text('{}', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'plan changed'):
                job.refresh('cafeland', temp)
            self.assertEqual(path.read_text(encoding='utf8'), '{}')

    def test_redirect_is_only_same_source_same_id_allowed_https(self):
        client = object.__new__(job.SourceClient)
        client.host='nhadat.cafeland.vn'; client.source='cafeland'; client.last=0; client.delay=3
        client.robot=RobotFileParser(); client.robot.parse(['User-agent: *', 'Allow: /'])
        handlers=[]
        class Response:
            status=200; url='https://nhadat.cafeland.vn/test-1.html'
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'ok'
        class Opener:
            def open(self,*args,**kwargs):return Response()
        def opener(handler):handlers.append(handler() if isinstance(handler,type) else handler);return Opener()
        with patch.object(job,'build_opener',side_effect=opener), patch.object(job.time,'sleep'):
            client.fetch(Response.url)
            h=handlers[0];req=Request(Response.url)
            self.assertIsNotNone(h.redirect_request(req,None,301,'',{},'https://nhadat.cafeland.vn/new-1.html'))
            for url in ['https://nhadat.cafeland.vn/new-2.html','http://nhadat.cafeland.vn/new-1.html','https://example.com/new-1.html']:
                with self.assertRaises(ValueError):h.redirect_request(req,None,301,'',{},url)


if __name__ == '__main__':unittest.main()
