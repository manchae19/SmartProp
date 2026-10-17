"""Reconcile analysis against frozen datasets/predictions, without refitting."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import training_v3_common as c
import train_training_v3 as experiment
import analyze_models_v5 as job


def equal_scores(actual,expected):
    for key,value in actual.items():
        if value is None:assert expected[key] is None
        else:np.testing.assert_allclose(value,expected[key],rtol=1e-9,atol=1e-8)


def main():
    run=job.latest(job.OUT)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],run)
    summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    data=c.BASE/summary['dataset_run']
    parts={s:c.read(data/'training_inputs'/(s+'.csv')) for s in ['train','validation']}
    validation={r['record_key']:r for r in parts['validation']}
    origin={r['record_key']:r for r in c.read(data/'all_listings_after_review.csv')}
    paired=c.read(run/'paired_validation.csv')
    assert len(paired)==len({r['record_key'] for r in paired})==299
    assert {r['record_key'] for r in paired}==validation.keys()
    predictions={};reports={}
    for version,relative in summary['model_runs'].items():
        model=c.BASE/relative
        reports[version]=json.loads((model/'metrics.json').read_text(encoding='utf-8'))
        predictions[version]={(p['record_key'],p['model']):p for p in c.read(model/'validation_predictions.csv')}
    for row in paired:
        original=validation[row['record_key']]
        assert float(row['actual_million'])==float(original['price_million'])
        assert float(row['area_sqm'])==float(original['area_sqm'])
        for field in ['source','category','pipeline_group','location_feature']:
            assert row[field]==original[field]
        assert row['title']==origin[row['record_key']]['title']
        assert row['label_action'].startswith('none;')
        for version in ['v3','v4','v5']:
            family=reports[version]['categories'][row['category']]['selected_by_validation_mae']
            assert row[version+'_model']==family
            p=predictions[version][(row['record_key'],family)]
            actual=float(p['actual_million']);predicted=float(p['predicted_million'])
            assert actual==float(row['actual_million']) and predicted==float(row[version+'_predicted_million'])
            np.testing.assert_allclose([float(row[version+'_signed_error_million']),float(row[version+'_absolute_error_million']),float(row[version+'_ape_pct'])],
                                      [predicted-actual,abs(predicted-actual),100*abs(predicted-actual)/actual],rtol=1e-10)
        for version in ['v3','v4']:
            np.testing.assert_allclose(float(row['v5_error_change_vs_'+version+'_million']),
                float(row['v5_absolute_error_million'])-float(row[version+'_absolute_error_million']),rtol=1e-10,atol=1e-8)
    for version in ['v3','v4','v5']:
        scores=job.metrics(paired,version)
        equal_scores(scores,summary['aggregate_selected'][version])
        equal_scores(scores,reports[version]['aggregate_selected_validation'])
    same=c.read(run/'same_family_validation.csv')
    assert len(same)==len({(r['record_key'],r['model']) for r in same})==897
    for row in same:
        assert row['record_key'] in validation
        for version in ['v3','v4','v5']:
            p=predictions[version][(row['record_key'],row['model'])]
            actual=float(p['actual_million']);predicted=float(p['predicted_million'])
            assert actual==float(row['actual_million']) and p['category']==row['category']
            assert predicted==float(row[version+'_predicted_million'])
            np.testing.assert_allclose(float(row[version+'_absolute_error_million']),abs(actual-predicted),rtol=1e-10)
    for version in ['v3','v4','v5']:
        xgb=[r for r in same if r['model']==experiment.FAMILIES[2]]
        equal_scores(c.scores([float(r['actual_million']) for r in xgb],[float(r[version+'_predicted_million']) for r in xgb]),summary['aggregate_xgboost'][version])
    segments=c.read(run/'segment_metrics.csv')
    dimensions={r['dimension'] for r in segments}
    for category in ['ALL']+c.CATEGORIES:
        subset=paired if category=='ALL' else [r for r in paired if r['category']==category]
        for dimension in dimensions:
            for version in ['v3','v4','v5']:
                grouped=[r for r in segments if r['category']==category and r['dimension']==dimension and r['version']==version]
                assert sum(int(r['n']) for r in grouped)==len(subset)
                for row in grouped:
                    members=[r for r in subset if str(r[dimension])==row['segment']]
                    expected=job.metrics(members,version)
                    for field,value in expected.items():
                        if value is None:assert not row[field]
                        else:np.testing.assert_allclose(float(row[field]),value,rtol=1e-9,atol=1e-8)
                    assert row['n_below_10']==str(len(members)<10)
                np.testing.assert_allclose(sum(float(r['mae_million'])*int(r['n']) for r in grouped),
                                          sum(float(r[version+'_absolute_error_million']) for r in subset),rtol=1e-9)
    contributions=c.read(run/'category_contributions.csv')
    assert len(contributions)==6
    for version in ['v3','v4']:
        subset=[r for r in contributions if r['reference_version']==version]
        assert {r['category'] for r in subset}==set(c.CATEGORIES)
        np.testing.assert_allclose(sum(float(r['contribution_to_overall_mae_change_million']) for r in subset),
            summary['aggregate_selected']['v5']['mae_million']-summary['aggregate_selected'][version]['mae_million'],rtol=1e-9)
    largest=sorted(paired,key=lambda r:float(r['v5_absolute_error_million']),reverse=True)
    expected_keys={r['record_key'] for r in largest[:10]}
    expected_keys|={r['record_key'] for r in sorted(paired,key=lambda r:float(r['v5_ape_pct']),reverse=True)[:10]}
    expected_keys|={r['record_key'] for r in sorted([r for r in paired if float(r['v5_error_change_vs_v3_million'])>0],key=lambda r:float(r['v5_error_change_vs_v3_million']),reverse=True)[:10]}
    priority=c.read(run/'priority_review.csv')
    assert len(priority)==len(expected_keys)==summary['priority_review_n']
    assert {r['record_key'] for r in priority}==expected_keys
    assert all(r['review_decision']=='not_reviewed' and not r['proposed_price_million'] and not r['proposed_area_sqm'] for r in priority)
    total=sum(float(r['v5_absolute_error_million']) for r in paired)
    for n in [10,20]:
        np.testing.assert_allclose(summary[f'top{n}_absolute_error_share_pct'],100*sum(float(r['v5_absolute_error_million']) for r in largest[:n])/total,rtol=1e-10)
    expensive=[r for r in paired if float(r['actual_million'])>=10000]
    assert len(expensive)==summary['price_ge10b_n']
    assert sum(float(r['v5_signed_error_million'])<0 for r in expensive)==summary['price_ge10b_underpredicted_n']
    np.testing.assert_allclose(summary['price_ge10b_absolute_error_share_pct'],100*sum(float(r['v5_absolute_error_million']) for r in expensive)/total,rtol=1e-10)
    for row in paired:np.testing.assert_allclose(float(row['v5_error_share_pct']),100*float(row['v5_absolute_error_million'])/total,rtol=1e-10)
    inventory=c.read(run/'feature_claim_inventory_DO_NOT_TRAIN.csv')
    assert len(inventory)==len({r['record_key'] for r in inventory})==2513
    assert {r['record_key'] for r in inventory}=={r['record_key'] for rows in parts.values() for r in rows}
    assert all('DO_NOT_TRAIN' in r['provenance'] and r['label_action']=='none' for r in inventory)
    watch=c.read(run/'source_scope_watchlist.csv')
    assert watch==[r for r in inventory if r['scope_review_flags']] and len(watch)==summary['scope_title_watchlist_n']
    coverage=experiment.feature_coverage(parts)
    assert c.read(run/'feature_coverage.csv')==[{k:str(v) for k,v in r.items()} for r in coverage]
    assert not summary['policy']['retrained'] and not summary['policy']['test_evaluated'] and summary['policy']['new_network_requests']==0
    result=dict(verified=True,run=run.relative_to(job.OUT).as_posix(),paired_validation_n=299,same_family_rows=897,
        priority_review_n=len(priority),scope_title_watchlist_n=len(watch),segment_rows=len(segments),
        frozen_models_and_dataset_sha256_unchanged=True,paired_metrics_and_error_shares_verified=True,
        feature_inventory_excludes_reserved_ids=True,no_relabeling=True,no_retraining=True,test_evaluated=False,
        verifier_sha256=c.sha(Path(__file__)))
    c.write_json(job.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
