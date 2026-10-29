import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import train_nested_price_trial as job
from test_nested_price_trial import rows,values


class ArtifactTests(unittest.TestCase):
    def test_writer_lock_is_exclusive_and_owned_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with job.writer_lock(root):
                with self.assertRaisesRegex(ValueError,'Another trial'):
                    with job.writer_lock(root):pass
            self.assertFalse((root/'writer.lock').exists())

    def test_interrupted_lock_metadata_write_removes_only_owned_partial_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(job.json,'dump',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):
                with job.writer_lock(root):self.fail('Must not enter writer body')
            self.assertFalse((root/'writer.lock').exists())
            with job.writer_lock(root):self.assertTrue((root/'writer.lock').exists())

    def test_owned_cleanup_keeps_another_token_and_existing_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'writer.lock'
            with job.writer_lock(root):path.write_text('{"owner":"another"}',encoding='utf8')
            self.assertEqual(json.loads(path.read_text(encoding='utf8'))['owner'],'another')
            with self.assertRaisesRegex(ValueError,'Another trial'):
                with job.writer_lock(root):pass
            self.assertTrue(path.exists())

    def test_csv_replay_detects_identity_count_and_numeric_tampering(self):
        expected=[dict(record_key='x:1',outer_fold='0',predicted_million='1000.0')]
        job.compare_csv(expected,expected)
        for altered in [[],[dict(expected[0],record_key='x:2')],[dict(expected[0],outer_fold='0.0000000001')],
                        [dict(expected[0],predicted_million='1001.0')]]:
            with self.assertRaises(ValueError):job.compare_csv(altered,expected)

    def test_saved_study_replays_without_fitting_and_rejects_tampered_metric(self):
        sample=[]
        for index,category in enumerate(job.data.CATEGORIES):sample+=rows(90,category,prefix='c'+str(index))
        features=values(sample)
        with tempfile.TemporaryDirectory() as temporary,patch.dict(job.trial.PROTOCOL,rounds=3),patch('builtins.print'):
            root=Path(temporary);source=root/'fixture.txt';source.write_text('unchanged')
            inputs={str(source):job.data.sha(source)}
            directory=root/job.fingerprint(inputs);directory.mkdir()
            store=job.ModelArtifacts(directory,features)
            tables,objects=job.study(sample,features,store)
            self.assertEqual(len(tables['outer_predictions']),len(sample)*3)
            self.assertEqual(objects['summary']['train_groups'],len(sample))
            # Assert every inner fit/check is inside its outer training cohort.
            for index,category in enumerate(job.data.CATEGORIES):
                part=[r for r in sample if r['category']==category]
                for outer,fit,held in job.trial.partition(part,3,job.trial.PROTOCOL['outer_salt']):
                    outer_keys={r['record_key'] for r in held}
                    for record in store.records:
                        if record['category']==category and record['phase']=='inner' and record['outer_fold']==outer:
                            self.assertFalse(outer_keys&(set(record['train_keys'])|set(record['held_keys'])))
            for name,table in tables.items():
                fields,table=job.csv_table(table);job.data.write_csv(directory/(name+'.csv'),table,fields)
            for name,obj in objects.items():job.data.write_json(directory/(name+'.json'),obj)
            job.data.write_json(directory/'protocol.json',dict(job.trial.PROTOCOL,versions=job.versions()))
            job.data.write_json(directory/'manifest.json',dict(input_sha256=inputs,protected_sha256={},output_sha256=job.data.outputs(directory)))
            with patch.object(job,'context',return_value=(sample,features,inputs,{})),patch.object(job,'BASE',root), \
                 patch.object(job.xgb,'train',side_effect=AssertionError('Verifier must never fit')):
                self.assertTrue(job.verify(directory)['no_new_fitting'])
                table=job.data.read(directory/'metrics.csv');table[0]['mae_million']='999999'
                job.data.write_csv(directory/'metrics.csv',table,list(table[0]))
                # Updating the output hashes cannot hide a wrong derived metric.
                manifest=json.loads((directory/'manifest.json').read_text(encoding='utf8'))
                manifest['output_sha256']=job.data.outputs(directory);job.data.write_json(directory/'manifest.json',manifest)
                with self.assertRaisesRegex(ValueError,'numeric value differs'):job.verify(directory)


if __name__=='__main__':unittest.main()
