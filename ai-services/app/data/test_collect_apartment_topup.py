import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_apartment_topup as job


class TopupPolicyTest(unittest.TestCase):
    def test_separate_policy_starts_at_extension_checkpoint_and_skips_its_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'checkpoint.json').write_text(json.dumps({'next_page':19}),encoding='utf8')
            with patch.object(job,'BASELINE',return_value=({'old:1'},{'start_page':13})),patch.object(job.runner,'OUT',root),patch.object(job.runner,'load_rows',return_value=[{'record_key':'new80:1'}]),patch.object(job.runner.source,'sha',return_value='digest'):
                keys,policy=job.baseline()
        self.assertEqual(keys,{'old:1','new80:1'})
        self.assertEqual((policy['start_page'],policy['target'],policy['max_pages_total']),(19,40,4))


if __name__=='__main__':unittest.main()
