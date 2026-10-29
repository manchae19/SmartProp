import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import collect_property_expansion_v2 as job


class CheckpointGuardTests(unittest.TestCase):
    def test_advanced_checkpoint_with_no_new_records_is_not_rewound(self):
        plan=dict(target=60,start_page=18,max_pages=16,max_per_locality=20)
        with tempfile.TemporaryDirectory() as temp,patch.object(job.old,'new_plan',return_value=(set(),plan)):
            root=Path(temp);cp=root/'checkpoint.json'
            initial=dict(next_page=18,attempted=[],historical_skipped=0,quota_skipped=0,page_signatures={})
            cp.write_text(json.dumps(initial),encoding='utf8')
            (root/'plan.json').write_text(json.dumps(plan),encoding='utf8')
            advanced=dict(initial,next_page=21,attempted=['cafeland:999'],finished=True)
            before=os.open
            def raced_open(path,*args,**kwargs):
                if Path(path).name=='collector.lock':cp.write_text(json.dumps(advanced),encoding='utf8')
                return before(path,*args,**kwargs)
            with patch.object(job.os,'open',side_effect=raced_open),self.assertRaisesRegex(ValueError,'checkpoint changed'):
                job.collect_new(root,lambda *_:self.fail('Network requested after race'))
            self.assertEqual(json.loads(cp.read_text(encoding='utf8')),advanced)
            self.assertFalse((root/'collector.lock').exists())
            self.assertFalse((root/'latest_run.json').exists())
            self.assertFalse((root/'invocations').exists())

    def test_completed_archived_batch_is_read_only_even_without_v2_receipt(self):
        plan=dict(target=1,start_page=18,max_pages=16,max_per_locality=20)
        with tempfile.TemporaryDirectory() as temp,patch.object(job.old,'new_plan',return_value=(set(),plan)):
            root=Path(temp)
            (root/'checkpoint.json').write_text(json.dumps(dict(next_page=34)),encoding='utf8')
            (root/'plan.json').write_text(json.dumps(plan),encoding='utf8')
            before={p.name:p.read_bytes() for p in root.iterdir()}
            result=job.collect_new(root,lambda *_:self.fail('network'))
            self.assertEqual(result['status'],'read_only_completed')
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})


if __name__=='__main__':unittest.main()
