from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import collect_source_features_75 as job
import source_feature_io as io
from test_collect_apartment_pilot import fixture


class CollectionTests(unittest.TestCase):
    def plan(self):
        return dict(target_each=1, max_pages_each=2, max_per_category_locality=1,
            starts={'Nhà ở': job.STARTS['Nhà ở']}, start_pages={'Nhà ở': 1})

    def test_current_house_category_does_not_inherit_apartment_flag(self):
        body, row = fixture(source_category='ban-nha-rieng')
        record = dict(row, sampling_category='Nhà ở', observed_at='2026-10-29T00:00:00Z',
                      fetch={'response_url': row['detail_url']})
        parsed = job.parse_detail(body, record)
        self.assertEqual(parsed['category'], 'Nhà ở')
        self.assertEqual(parsed['source_evidence_flags'], [])
        record['sampling_category'] = 'Đất nền'
        self.assertIn('source_category_differs_from_sampling_category', job.parse_detail(body, record)['source_evidence_flags'])

    def test_durable_record_resume_after_checkpoint_interrupt_is_read_only(self):
        body, row = fixture(source_category='ban-nha-rieng')
        row['sampling_category'] = 'Nhà ở'
        class Client:
            def __init__(self, *_): pass
            def fetch(self, url):
                self.last_url = url
                return body, 200
        original = job.atomic_json
        def interrupted(path, value):
            if path.name == 'checkpoint.json': raise KeyboardInterrupt()
            original(path, value)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(job, 'listing_page', return_value=([row], set())), patch.object(job, 'atomic_json', side_effect=interrupted):
                result = job.collect(root, Client, lambda: (set(), self.plan()))
            self.assertEqual(result['status'], 'interrupted')
            self.assertFalse((root/'collector.lock').exists())
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result = job.collect(root, lambda *_: self.fail('Network on completed batch'), lambda: (set(), self.plan()))
            self.assertEqual(result['status'], 'read_only_completed')
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_checkpoint_race_has_no_request_and_preserves_other_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            @contextmanager
            def racing(*_):
                io.atomic_json(root/'checkpoint.json', {'completed': ['Nhà ở']})
                yield
            with patch.object(job, 'writer_lock', racing), self.assertRaisesRegex(ValueError, 'Batch changed'):
                job.collect(root, lambda *_: self.fail('Network after race'), lambda: (set(), self.plan()))
            self.assertFalse((root/'plan.json').exists())
            self.assertEqual(json.loads((root/'checkpoint.json').read_text())['completed'], ['Nhà ở'])

    def test_partial_lock_write_cleanup_does_not_leave_own_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(io.json, 'dump', side_effect=KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt):
                with io.writer_lock(root): self.fail('Must not yield')
            self.assertFalse((root/'writer.lock').exists())
            (root/'writer.lock').write_text('other writer')
            with self.assertRaises(ValueError):
                with io.writer_lock(root): self.fail('Must not yield')
            self.assertEqual((root/'writer.lock').read_text(), 'other writer')


if __name__ == '__main__': unittest.main()
