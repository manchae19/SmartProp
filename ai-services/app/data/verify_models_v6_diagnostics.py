"""Reconcile every diagnostic row/partition against saved predictions, never inference."""
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean
import training_v3_common as c
import analyze_models_v6 as job


def close(left,right):
    if not math.isclose(float(left),float(right),rel_tol=1e-9,abs_tol=1e-8):
        raise ValueError(f'Numeric reconciliation failed: {left} != {right}')


def reconcile_scores(saved,rows):
    actual=[float(r['actual_million']) for r in rows]
    predicted=[float(r['predicted_million']) for r in rows]
    scores=c.scores(actual,predicted)
    for key in ['n','mae_million','mape_pct','median_ape_pct','within_20pct','above_50pct']:
        close(saved[key],scores[key])
    close(saved['total_absolute_error_million'],sum(abs(y-p) for y,p in zip(actual,predicted)))
    close(saved['signed_mean_error_million'],mean(p-y for y,p in zip(actual,predicted)))
    close(saved['underpredicted_n'],sum(p<y for y,p in zip(actual,predicted)))


def main():
    run=job.OUT/json.loads((job.OUT/'latest.json').read_text(encoding='utf8'))['run']
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf8'))
    c.verify(manifest['input_sha256'],job.REPO);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],run)
    summary=json.loads((run/'summary.json').read_text(encoding='utf8'))
    validation=c.read(job.FEATURES/'validation.csv');train=c.read(job.FEATURES/'train.csv')
    rows=c.read(run/'validation_errors_DO_NOT_TRAIN.csv')
    keys=[r['record_key'] for r in rows]
    assert len(keys)==len(set(keys))==299 and set(keys)=={r['record_key'] for r in validation}
    assert not set(keys)&{r['record_key'] for r in train}
    assert not {r['pipeline_group'] for r in validation}&{r['pipeline_group'] for r in train}
    original={r['record_key']:r for r in validation}
    features={r['record_key']:r for r in c.read(job.FEATURES/'features.csv')}
    support=Counter((r['category'],r['location_feature']) for r in train)
    predictions={(r['record_key'],r['arm']):r for r in c.read(job.MODEL/'validation_predictions.csv')}
    for row in rows:
        key=row['record_key'];reference=original[key];prediction=predictions[(key,'all')]
        for field in ['source','category','pipeline_group','location_feature','area_sqm']:
            assert row[field]==reference[field]
        close(row['actual_million'],reference['price_million'])
        close(row['predicted_million'],prediction['predicted_million'])
        close(row['control_predicted_million'],predictions[(key,'control')]['predicted_million'])
        y,p=float(row['actual_million']),float(row['predicted_million'])
        close(row['absolute_error_million'],abs(y-p));close(row['ape_pct'],100*abs(y-p)/y)
        close(row['signed_error_million'],p-y)
        assert row['label_action']=='none; DO_NOT_TRAIN'
        feature=features[key]
        assert row['ward_status']==('available' if reference['ward_source'] else 'missing')
        assert row['rooms_status']==('not_applicable' if row['category']==c.CATEGORIES[1] else 'available' if feature['rooms_completed'] else 'missing')
        assert row['floors_status']==('not_applicable' if row['category']!=c.CATEGORIES[0] else 'available' if feature['floors_claim'] else 'missing')
        assert row['access_status']==('not_applicable' if row['category']==c.CATEGORIES[2] else feature['access_claim'] or 'missing')
        assert int(row['train_location_n'])==support[(row['category'],row['location_feature'])]
    selected={r['record_key']:r for r in c.read(job.MODEL/'selected_validation_errors.csv')}
    assert set(selected)==set(keys)
    for row in rows:close(row['absolute_error_million'],selected[row['record_key']]['absolute_error_million'])
    reconcile_scores(summary['selected'],rows)
    control=[dict(r,predicted_million=r['control_predicted_million']) for r in rows]
    reconcile_scores(summary['control'],control)
    for category in c.CATEGORIES:
        subset=[r for r in rows if r['category']==category]
        metrics=next(r for r in summary['categories'] if r['category']==category)
        reconcile_scores(metrics,subset)
        assert metrics['train_n']==sum(r['category']==category for r in train)
    for metrics in c.read(run/'category_metrics.csv'):
        reconcile_scores(metrics,[r for r in rows if r['category']==metrics['category']])
    groups=c.read(run/'segment_metrics.csv')
    for category in ['ALL']+c.CATEGORIES:
        subset=rows if category=='ALL' else [r for r in rows if r['category']==category]
        for dimension in {r['dimension'] for r in groups}:
            cells=[g for g in groups if g['category']==category and g['dimension']==dimension]
            assert sum(int(g['n']) for g in cells)==len(subset)
            assert {g['segment'] for g in cells}=={r[dimension] for r in subset}
            for cell in cells:
                members=[r for r in subset if r[dimension]==cell['segment']]
                reconcile_scores(cell,members)
                assert cell['small_group']==str(len(members)<10)
    catalog=json.loads(job.CATALOG.read_text(encoding='utf8'));allowed=catalog['legacy']|catalog['expanded']
    coverage=c.read(run/'location_coverage.csv')
    counts={split:Counter((r['category'],r['location_feature']) for r in part) for split,part in [('train',train),('validation',validation)]}
    assert {(r['category'],r['location_feature']) for r in coverage}==set(counts['train'])|set(counts['validation'])
    for cell in coverage:
        key=(cell['category'],cell['location_feature'])
        assert int(cell['train_n'])==counts['train'][key] and int(cell['validation_n'])==counts['validation'][key]
        expected=max(0,10-counts['train'][key]) if key[1] in allowed else 0
        assert int(cell['planning_gap'])==expected
    priorities=c.read(run/'collection_priorities.csv') if (run/'collection_priorities.csv').exists() else []
    assert {(r['category'],r['location_feature']) for r in priorities}=={(r['category'],r['location_feature']) for r in coverage if int(r['planning_gap'])>0}
    assert sum(int(r['planning_gap']) for r in priorities)==summary['coverage_planning_gap']
    total=sum(float(r['absolute_error_million']) for r in rows)
    close(summary['top10_error_share_pct'],100*sum(sorted([float(r['absolute_error_million']) for r in rows],reverse=True)[:10])/total)
    expensive=[r for r in rows if float(r['actual_million'])>=10000]
    assert len(expensive)==summary['price_ge10b_n']
    close(summary['price_ge10b_error_share_pct'],100*sum(float(r['absolute_error_million']) for r in expensive)/total)
    assert summary['policy']==job.POLICY and summary['policy']['pilot_read'] is False
    c.verify(manifest['protected_sha256'])
    proof=dict(verified=True,run=run.relative_to(job.OUT).as_posix(),validation_n=299,segment_rows=len(groups),
               category_rows=3,all_ids_labels_predictions_and_groups_reconciled=True,all_partitions_reconciled=True,
               frozen_files_unchanged=True,retrained=False,new_predictions=False,pilot_read=False,
               verifier_sha256=c.sha(Path(__file__)))
    c.write_json(job.OUT/'verification.json',proof)
    print(json.dumps(proof,ensure_ascii=False))


if __name__=='__main__':main()
