"""Verify every extracted value/quote against the fixed cohort and saved source."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import training_v3_common as c
import build_property_features_v6 as job


def main():
    run=job.latest(job.OUT)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(m['input_sha256']);c.verify(m['protected_sha256']);c.verify(m['output_sha256'],run)
    summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    data=c.BASE/summary['dataset_run']
    parts={s:c.read(run/(s+'.csv')) for s in ['train','validation']}
    for split in parts:assert parts[split]==c.read(data/'training_inputs'/(split+'.csv'))
    reserved=c.read(run/'reserved_holdout_registry.csv')
    assert reserved==c.read(data/'training_inputs/reserved_holdout_registry.csv') and len(reserved)==684
    rows={r['record_key']:r for split in parts.values() for r in split}
    assert len(rows)==2513
    features=c.read(run/'features.csv');bykey={r['record_key']:r for r in features}
    assert len(features)==len(bykey)==2513 and bykey.keys()==rows.keys()
    assert not ({r['record_key'] for r in reserved}&bykey.keys())
    origin={r['record_key']:r for r in c.read(data/'all_listings_after_review.csv')}
    source=c.PROCESSED/'collection_source_review'
    parsed=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    evidence=c.read(run/'feature_evidence_DO_NOT_TRAIN.csv');proofs=defaultdict(list)
    for proof in evidence:
        key=proof['record_key'];row=rows[key]
        assert proof['model_split']==row['model_split']
        proofs[(key,proof['field'])].append(proof)
        if proof['source_kind']=='verified_detail_body':
            body,state=job.admit_body(row,parsed.get(key),fetch.get(key,{}))
            assert state=='verified_matching_snapshot' and proof['source_quote'] in body
            assert proof['source_sha256']==parsed[key]['detail_sha256']
            relative=(source/'detail_cache'/fetch[key]['file']).relative_to(c.BASE).as_posix()
            assert m['input_sha256'][relative]==proof['source_sha256']
        elif proof['source_kind']=='collected_title':assert proof['source_quote'] in origin[key]['title']
        elif proof['source_kind']=='structured_rooms':assert proof['value']==row['rooms']
        elif proof['source_kind']=='structured_source_category':
            assert proof['source_quote']==str(json.loads(origin[key]['raw_json'])['source_category'])
        else:raise ValueError('Unknown evidence source')
    for key,f in bykey.items():
        row=rows[key]
        assert f['model_split']==row['model_split'] and f['category']==row['category']
        if row['rooms']:assert float(f['rooms_completed'])==float(row['rooms'])
        for field in job.rules.FEATURES:
            value=f[field]
            if value:
                accepted=[p for p in proofs[(key,field)] if p['status'] in ['accepted','conflict_structured_retained']]
                assert accepted,(key,field)
                assert all(str(p['value'])==value for p in accepted),(key,field)
        body,state=job.admit_body(row,parsed.get(key),fetch.get(key,{}))
        expected,_=job.rules.extract(row,origin[key],body,parsed[key]['detail_sha256'] if body else '')
        for field in list(job.rules.FEATURES)+['conflict_fields','extraction_notes']:
            assert f[field]==str(expected[field]),(key,field)
        if row['category']=='Đất nền':assert not f['rooms_completed'] and not f['floors_claim'] and not f['house_subtype_claim']
        if row['category']=='Căn hộ chung cư':assert not f['floors_claim'] and not f['access_claim'] and not f['house_subtype_claim']
    for category in c.CATEGORIES:
        tr=[r for r in parts['train'] if r['category']==category]
        spec=job.rules.feature_spec(tr,category,'control')
        np.testing.assert_allclose(job.rules.encode(tr,bykey,spec),c.encode(tr,c.schema(tr)),equal_nan=True)
    assert c.read(run/'coverage.csv')==[{k:'' if v is None else str(v) for k,v in r.items()} for r in job.coverage(bykey,parts)]
    result=dict(verified=True,run=run.relative_to(job.OUT).as_posix(),train=2214,validation=299,reserved_eligible=684,
        feature_rows=2513,evidence_rows=len(evidence),all_values_replayed_with_quotes=True,
        source_html_sha256_verified=summary['verified_used_html_snapshots'],cohorts_labels_and_original_models_unchanged=True,
        control_matrix_exact=True,verifier_sha256=c.sha(Path(__file__)))
    c.write_json(job.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
