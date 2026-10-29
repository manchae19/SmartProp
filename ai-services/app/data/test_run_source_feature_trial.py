import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_source_feature_trial as job


class SourceTrialIntegrationTests(unittest.TestCase):
    def test_fit_then_replay_without_fit_and_reject_semantic_prediction_tamper(self):
        rows, base, extra = [], {}, {}
        for category in job.data.CATEGORIES:
            for i in range(30):
                key = category + str(i)
                rows.append(dict(record_key=key, category=category, pipeline_group=key,
                    area_sqm=str(50+i), price_million=str(1000+50*i), location_feature='Hải Châu',
                    rooms='', ward_source=''))
                base[key] = dict(rooms_completed='', floors_claim='', access_claim='', house_subtype_claim='')
                extra[key] = dict.fromkeys(job.feature.FIELDS, '')
                extra[key].update(street_key='ha huy tap', street_raw='Đường Hà Huy Tập', street_status='accepted_source_claim_not_geocoded')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source.json'
            source.write_text('[]')
            inputs = {str(source): job.data.sha(source)}
            out = root/'output'
            policy = dict(job.POLICY, rounds=3)
            with patch.object(job, 'OUT', out), patch.object(job, 'context', return_value=(rows, base, extra, [], inputs, {})), patch.object(job, 'POLICY', policy), patch.object(job.previous, 'BASE', root):
                result = job.run()
                self.assertEqual(result['models'], 18)
                run = out/'runs'/result['run_id']
                self.assertEqual(len(job.data.read(run/'fold_membership.csv')), 270)
                with patch.object(job.xgb, 'train', side_effect=AssertionError('verify must not fit')):
                    self.assertTrue(job.verify(run)['no_new_fitting'])
                    path = run/'predictions.csv'
                    values = job.data.read(path)
                    values[0]['predicted_million'] = '1'
                    job.data.write_csv(path, values, list(values[0]))
                    manifest = json.loads((run/'manifest.json').read_text(encoding='utf8'))
                    manifest['output_sha256'] = job.data.outputs(run)
                    job.atomic_json(run/'manifest.json', manifest)
                    with self.assertRaisesRegex(ValueError, 'numeric value differs'):
                        job.verify(run)


if __name__=='__main__': unittest.main()
