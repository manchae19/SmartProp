"""Replay models plus every reported learning-curve metric, without fitting."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np

import measure_training_learning_curve as curve


def verify(directory):
    curve.verify(directory)
    data = curve.data
    models = json.loads((directory/'models.json').read_text(encoding='utf8'))
    groups = defaultdict(list)
    for row in data.read(directory/'predictions.csv'):
        groups[(row['model_key'],row['role'])].append(row)
    scores = data.read(directory/'fold_scores.csv')
    bykey = {r['model_key']:r for r in scores}
    if len(scores)!=36 or set(bykey)!={r['key'] for r in models}:raise ValueError('Score model keyset differs')
    for item in models:
        score = bykey[item['key']]
        if score['category']!=item['category'] or int(score['fold'])!=item['fold'] or float(score['fraction'])!=item['fraction']:
            raise ValueError('Fold metric identity differs')
        for role in ['train','outer']:
            rows = groups[item['key'],role]
            actual = [float(r['actual_million']) for r in rows]
            pred = [float(r['predicted_million']) for r in rows]
            result = curve.metrics(actual,pred)
            if int(score[role+'_n'])!=len(rows):raise ValueError('Metric sample count differs')
            np.testing.assert_allclose(float(score[role+'_mae_million']),result['mae'],rtol=1e-10,atol=1e-8)
            if role=='outer':np.testing.assert_allclose(float(score['outer_mape_pct']),result['mape'],rtol=1e-10,atol=1e-8)
    summaries = data.read(directory/'summary.csv')
    keys = {(r['category'],float(r['fraction'])) for r in summaries}
    expected = {(c,f) for c in data.CATEGORIES for f in curve.PROTOCOL['fractions']}
    if len(summaries)!=12 or keys!=expected:raise ValueError('Summary keyset differs')
    for summary in summaries:
        subset = [s for s in scores if (s['category'],float(s['fraction']))==(summary['category'],float(summary['fraction']))]
        held = [r for score in subset for r in groups[score['model_key'],'outer']]
        result = curve.metrics([float(r['actual_million']) for r in held],[float(r['predicted_million']) for r in held])
        values = dict(outer_mae_million=result['mae'],outer_mape_pct=result['mape'],
            mean_train_n=np.mean([int(s['train_n']) for s in subset]),
            train_mae_million=np.average([float(s['train_mae_million']) for s in subset],weights=[int(s['train_n']) for s in subset]),
            fold_mae_sd_million=np.std([float(s['outer_mae_million']) for s in subset],ddof=1))
        for key,value in values.items():
            np.testing.assert_allclose(float(summary[key]),value,rtol=1e-10,atol=1e-8)
    receipt = dict(verified=True,models=36,predictions=sum(len(v) for v in groups.values()),fold_metrics=36,summary_points=12,
        no_new_fitting=True,source_manifest_sha256=data.sha(directory/'manifest.json'),verifier_sha256=data.sha(Path(__file__)),
        verified_at_utc=datetime.now(timezone.utc).isoformat())
    data.write_json(curve.OUT/'verification.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    verify(curve.OUT/json.loads((curve.OUT/'latest.json').read_text(encoding='utf8'))['run'])
