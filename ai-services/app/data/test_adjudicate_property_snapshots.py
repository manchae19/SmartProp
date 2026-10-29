import copy
import hashlib
import unittest

import adjudicate_property_snapshots as job
from test_property_snapshot_adjudication import row


def snapshot(key, **changes):
    result=row(key,review_codes=[])
    result.update(source='fixture',observed_at='2026-10-29T12:00:00Z',response_sha256='a'*64,
        original_pipeline_group='',category=job.claims.APARTMENT,source_published_date='2026-10-29',
        source_age_days='0',label_basis='Current price and property claims from same response')
    result.update(changes)
    return result


def singleton_group(key):
    return 'property_candidate:'+hashlib.sha256(key.encode()).hexdigest()[:20]


class PreparationTests(unittest.TestCase):
    def test_assemble_conserves_labels_hash_time_and_reserves_fresh(self):
        a=snapshot('old:1',overlay_group=singleton_group('old:1'),original_pipeline_group='frozen:1')
        b=snapshot('new:1',overlay_group=singleton_group('new:1'))
        originals=copy.deepcopy([a,b])
        decisions,links=job.assemble([a,b],[],[dict(record_key='old:1')],[dict(record_key='old:1')],[])
        observations,features,proofs,candidates=job.prepared_tables(decisions)
        self.assertEqual([a,b],originals)
        self.assertEqual(links,[])
        self.assertEqual({r['dataset_role'] for r in candidates},{'train_refresh_candidate','fresh_evaluation_reserved'})
        for result in observations:
            original=next(x for x in originals if x['record_key']==result['record_key'])
            for field in ['price_million','area_sqm','response_sha256','observed_at']:
                self.assertEqual(result[field],original[field])
        self.assertTrue(all(not r['training_allowed'] for r in features+candidates))
        self.assertNotIn('price_million',features[0])
        self.assertTrue(all(p['response_sha256']=='a'*64 for p in proofs))

    def test_hidden_historical_member_cannot_become_new_holdout(self):
        keys=['old:1','new:1'];gid='property_candidate:'+hashlib.sha256('|'.join(sorted(keys)).encode()).hexdigest()[:20]
        current=snapshot('new:1',overlay_group=gid)
        results,_=job.assemble([current],[dict(left='old:1',right='new:1')],[],[dict(record_key='old:1')],[])
        self.assertEqual(results[0]['dataset_role'],'historical_linked_candidate')

    def test_mismatched_archived_component_fails_before_preparation(self):
        current=snapshot('new:1',overlay_group='wrong')
        with self.assertRaisesRegex(ValueError,'full group membership differs'):
            job.assemble([current],[],[],[],[])

    def test_duplicate_representatives_cannot_be_exported(self):
        a=job.rules.scan(snapshot('new:1'));b=job.rules.scan(snapshot('new:2'))
        for r in [a,b]:r.update(adjudicated_group='same',representative_key=r['record_key'],dataset_role='fresh_evaluation_reserved')
        with self.assertRaisesRegex(ValueError,'Repeated representative group'):
            job.prepared_tables([a,b])

    def test_schema_excludes_prices_and_raw_text_from_candidate_predictors(self):
        schema=job.schema()
        self.assertEqual(schema['status'],'DO_NOT_TRAIN')
        self.assertFalse(set(schema['allowed_predictor_candidates'])&set(schema['forbidden_predictors']))
        self.assertIn('unit_price',schema['forbidden_predictors'])


if __name__=='__main__':unittest.main()
