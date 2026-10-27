import csv
import tempfile
import unittest
from pathlib import Path
import audit_reserved_holdout as a


class HistoryTests(unittest.TestCase):
    def test_test_assignment_alone_is_not_exposure(self):
        row=dict(record_key='cafeland:1',model_split='test')
        self.assertEqual(a.activity(row,'test.csv'),'')
        self.assertEqual(a.activity(row,'baseline_inputs.csv'), '')
        self.assertEqual(a.activity(row,'holdout_predictions.csv'),'saved_prediction')

    def test_insufficient_category_is_not_baseline_fit(self):
        row=dict(record_key='cafeland:1',model_split='train',category='house')
        self.assertEqual(a.activity(row,'baseline_inputs.csv',{'apartment'}),'')
        self.assertEqual(a.activity(row,'baseline_inputs.csv',{'house'}),'baseline_train_input')

    def test_prepared_train_inputs_are_conservatively_flagged(self):
        self.assertEqual(a.activity(dict(record_key='cafeland:1'),'train.csv'),'train_input')

    def test_transitive_links_to_scored_id(self):
        catalog=[dict(path='old/groups.csv',rows=[dict(record_key='cafeland:1',pipeline_group='g'),dict(record_key='cafeland:2',pipeline_group='g')]),
                 dict(path='other/pairs.csv',rows=[dict(left='cafeland:2',right='cafeland:3')]),
                 dict(path='model/test_predictions.csv',rows=[dict(record_key='cafeland:3')])]
        graph,events=a.graph_and_events(catalog)
        membership,_=a.components(graph,{'cafeland:1','cafeland:4'})
        self.assertEqual(membership['cafeland:1'],membership['cafeland:3'])
        self.assertNotEqual(membership['cafeland:1'],membership['cafeland:4'])
        self.assertEqual(len(a.evidence_path(graph,'cafeland:1','cafeland:3')),2)
        self.assertEqual(len(events),1)

    def test_equal_group_names_in_different_files_do_not_link_unrelated_ids(self):
        graph,_=a.graph_and_events([dict(path='a.csv',rows=[dict(record_key='cafeland:1',pipeline_group='g')]),
                                   dict(path='b.csv',rows=[dict(record_key='cafeland:2',pipeline_group='g')])])
        membership,_=a.components(graph,{'cafeland:1','cafeland:2'})
        self.assertNotEqual(membership['cafeland:1'],membership['cafeland:2'])

    def test_cross_group_and_blocking_ids_are_links(self):
        graph,_=a.graph_and_events([dict(path='links.csv',rows=[dict(record_key='cafeland:1',other_record_key='nhadat24h:2',group_blocking_ids='homedy:3')])])
        membership,_=a.components(graph,{'cafeland:1'})
        self.assertEqual(membership['cafeland:1'],membership['nhadat24h:2'])
        self.assertEqual(membership['cafeland:1'],membership['homedy:3'])

    def test_duplicate_model_rows_do_not_duplicate_events(self):
        _,events=a.graph_and_events([dict(path='validation_predictions.csv',rows=[dict(record_key='cafeland:1')]*3)])
        self.assertEqual(len(events),1)

    def test_projection_never_returns_target_or_prediction_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.csv'
            with path.open('w',encoding='utf-8',newline='') as s:
                w=csv.writer(s);w.writerow(['record_key','price_million','predicted_million','category']);w.writerow(['cafeland:1','secret-target','secret-prediction','house'])
            fields,rows=a.projected(path)
        self.assertEqual(fields,['record_key','category'])
        self.assertEqual(rows,[dict(record_key='cafeland:1',category='house')])


if __name__=='__main__':unittest.main()
