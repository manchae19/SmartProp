import unittest
from pathlib import Path
import tempfile
from prepare_v7_trial import mask, read_collection


class FeatureMaskTest(unittest.TestCase):
    def test_empty_cohort_keeps_header_without_indexing_first_row(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'collection.csv';path.write_text('record_key,cohort_split\n',encoding='utf8')
            fields,rows=read_collection(path)
        self.assertEqual(fields,['record_key','cohort_split']);self.assertEqual(rows,[])

    def test_only_conflicting_bedrooms_change_and_input_is_untouched(self):
        rows=[dict(record_key='a',model_split='train',category='Căn hộ chung cư',rooms_completed='2',conflict_fields='rooms_completed'),
              dict(record_key='b',model_split='validation',category='Nhà ở',rooms_completed='3',conflict_fields='floors_claim')]
        result,changes=mask(rows)
        self.assertEqual(result[0]['rooms_completed'],'');self.assertEqual(result[1],rows[1])
        self.assertEqual(rows[0]['rooms_completed'],'2');self.assertEqual(len(changes),1)


if __name__=='__main__':unittest.main()
