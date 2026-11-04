import unittest
from unittest.mock import Mock
from pathlib import Path
from tinix_quality_v2_dry_run import select

class ReadOnlyContractTests(unittest.TestCase):
    def test_mutations_and_multi_statement_sql_rejected_before_driver(self):
        cursor=Mock()
        for sql in ['UPDATE tinix_dataset_records SET quality_status=1','DELETE FROM x','INSERT INTO x VALUES(1)','ALTER TABLE x ADD x INT','DROP TABLE x','SELECT 1; UPDATE x SET y=1','CALL write_something()']:
            with self.assertRaises(ValueError):select(cursor,sql)
        cursor.execute.assert_not_called()
    def test_bound_read_query_allowed(self):
        cursor=Mock();select(cursor,'SELECT internal_id FROM tinix_dataset_records WHERE internal_id=%s',('a'*64,))
        cursor.execute.assert_called_once_with('SELECT internal_id FROM tinix_dataset_records WHERE internal_id=%s',('a'*64,))
    def test_v2_is_not_wired_into_live_importer(self):
        script=Path(__file__).with_name('tinix_dataset.py').read_text(encoding='utf8')
        self.assertIn('from tinix_quality import quality',script)
        self.assertNotIn('from tinix_quality_v2 import',script)
if __name__=='__main__':unittest.main()
