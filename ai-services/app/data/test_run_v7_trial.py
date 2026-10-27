import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import run_v7_trial as job
from run_v7_trial import assert_fresh


class EvaluationGuardTest(unittest.TestCase):
    def test_complete_preparation_recovers_pointer_after_publish_crash(self):
        repo=job.archived.preparation.BASE.parents[2]
        with tempfile.TemporaryDirectory(dir=repo,prefix='prep-pointer-') as d:
            root=Path(d);cohort_root=root/'cohort';cohort=cohort_root/'runs/current';cohort.mkdir(parents=True)
            (cohort/'manifest.json').write_text('{}',encoding='utf8')
            (cohort_root/'latest.json').write_text(json.dumps({'run':'runs/current'}),encoding='utf8')
            prepared_root=root/'prepared';prepared=prepared_root/'runs/complete';prepared.mkdir(parents=True)
            (prepared/'protocol.json').write_text(json.dumps(job.archived.preparation.PROTOCOL),encoding='utf8')
            key=(cohort/'manifest.json').relative_to(repo).as_posix()
            manifest={'input_sha256':{key:job.archived.data.sha(cohort/'manifest.json')},'output_sha256':{'protocol.json':job.archived.data.sha(prepared/'protocol.json')}}
            (prepared/'manifest.json').write_text(json.dumps(manifest),encoding='utf8')
            with patch.object(job.archived.preparation,'OUT',prepared_root),patch.object(job.archived.preparation.cohort,'OUT',cohort_root):job.restore_prepared_pointer()
            self.assertEqual(json.loads((prepared_root/'latest.json').read_text())['run'],'runs/complete')

    def test_changed_metadata_or_expanded_lock_cannot_reuse_evaluated_ids(self):
        old={'record_key':'old','property_candidate_group':'group1'}
        new={'record_key':'new','property_candidate_group':'group2'}
        with self.assertRaisesRegex(ValueError,'previously evaluated'):
            assert_fresh({'members':[old,new]},[old,new],[{'members':['old']}])

    def test_new_id_in_evaluated_property_group_is_blocked(self):
        old={'record_key':'old','property_candidate_group':'joined-group'}
        new={'record_key':'new','property_candidate_group':'joined-group'}
        with self.assertRaisesRegex(ValueError,'property groups'):
            assert_fresh({'members':[new]},[old,new],[{'members':['old']}])

    def test_omitting_old_ids_from_grouping_is_not_proof_of_freshness(self):
        new={'record_key':'new','property_candidate_group':'group2'}
        with self.assertRaisesRegex(ValueError,'missing previously evaluated'):
            assert_fresh({'members':[new]},[new],[{'members':['old']}])

    def test_distinct_new_groups_are_allowed(self):
        old={'record_key':'old','property_candidate_group':'group1'}
        new={'record_key':'new','property_candidate_group':'group2'}
        assert_fresh({'members':[new]},[old,new],[{'members':['old']}])


if __name__=='__main__':unittest.main()
