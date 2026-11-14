import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_apartment_extension as job
from test_collect_apartment_pilot import fixture


class ExtensionLifecycleTest(unittest.TestCase):
    def test_read_error_after_acquiring_lock_releases_lock_without_export(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);(out/'policy.json').write_text(json.dumps({'start_page':1}),encoding='utf8')
            calls=0
            def failing_sha(path):
                nonlocal calls
                calls+=1
                if calls>1:raise PermissionError('Read blocked after lock')
                return 'snapshot'
            with patch.object(job,'baseline',return_value=({'old:1'},{'start_page':1})),patch.object(job.source,'sha',side_effect=failing_sha),patch.object(job.source,'export_csv',side_effect=AssertionError('No export')):
                with self.assertRaises(PermissionError):job.run(out)
            self.assertFalse((out/'collector.lock').exists())

    def test_state_changed_just_before_lock_is_rejected_without_export(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);original_open=job.os.open
            def racing_open(path,*args,**kwargs):
                (out/'records.jsonl').write_text(json.dumps({'record_key':'other:1'})+'\n',encoding='utf8')
                (out/'checkpoint.json').write_text(json.dumps({'next_page':2,'attempted':['other:1'],'historical_skipped':0}),encoding='utf8')
                return original_open(path,*args,**kwargs)
            with patch.object(job,'baseline',return_value=({'old:1'},{'start_page':1})),patch.object(job.os,'open',side_effect=racing_open),patch.object(job.source,'Client',side_effect=AssertionError('No network')),patch.object(job.source,'export_csv',side_effect=AssertionError('No export')):
                with self.assertRaisesRegex(ValueError,'changed while acquiring lock'):job.run(out)
            self.assertEqual(len(job.load_rows(out)),1)
            self.assertEqual(json.loads((out/'checkpoint.json').read_text())['next_page'],2)
            self.assertFalse((out/'collector.lock').exists())

    def test_completed_batch_and_policy_rejection_do_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);(out/'records.jsonl').write_text(json.dumps({'record_key':'new:1'})+'\n',encoding='utf8')
            policy={'start_page':1,'test':True};(out/'policy.json').write_text(json.dumps(policy),encoding='utf8')
            before={p.name:p.read_bytes() for p in out.iterdir()}
            with patch.object(job,'TARGET',1),patch.object(job,'baseline',return_value=({'old:1'},policy)),patch.object(job.source,'Client',side_effect=AssertionError('No network')):
                self.assertEqual(job.run(out),0)
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})
            with patch.object(job,'baseline',return_value=({'old:1'},dict(policy,test=False))),self.assertRaises(ValueError):job.run(out)
            self.assertEqual(before,{p.name:p.read_bytes() for p in out.iterdir()})

    def test_export_failure_releases_only_owned_lock_and_keeps_durable_log(self):
        body,row=fixture()
        class Client:
            def __init__(self,*args):pass
            def fetch(self,url):self.last_url=url;return (b'listing' if '/nha-dat-ban/' in url else body),200
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            with patch.object(job,'TARGET',1),patch.object(job,'baseline',return_value=({'old:1'},{'start_page':1})),patch.object(job.source,'Client',Client),patch.object(job.source,'listing_page',return_value=([row],set())),patch.object(job.source,'export_csv',side_effect=PermissionError('CSV locked')):
                with self.assertRaises(PermissionError):job.run(out)
            self.assertFalse((out/'collector.lock').exists())
            self.assertEqual(len(job.load_rows(out)),1)
            import repair_apartment_extension_csv as recovery
            recovery.repair(out,review_root=out/'no_review')
            self.assertTrue((out/'apartment_records.csv').exists())
            (out/'collector.lock').write_text('another collector',encoding='utf8')
            with patch.object(job,'baseline',return_value=({'old:1'},{'start_page':1})),self.assertRaises(FileExistsError):job.run(out)
            self.assertEqual((out/'collector.lock').read_text(),'another collector')


if __name__=='__main__':unittest.main()
