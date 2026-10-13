"""Train separate XGBoost asking-price regressors on the frozen v1 splits."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_all_collected import BASE, read, save_csv
from prepare_smartprop_dataset import CATEGORIES
from train_smartprop_baseline import metrics


def load(directory):
    parts = {s:read(directory/(s+'.csv')) for s in ['train','validation','test']}
    seen_ids,seen_groups = set(),set()
    for split,rows in parts.items():
        ids = {r['record_key'] for r in rows}
        groups = {r['duplicate_candidate_group'] for r in rows}
        if len(ids)!=len(rows) or len(groups)!=len(rows) or ids&seen_ids or groups&seen_groups:
            raise ValueError('Repeated ID/property group within or across splits')
        for r in rows:
            if r['model_split']!=split or r['v1_disposition']!='main' or r['v1_review_codes']:
                raise ValueError('Unexpected split or review status: '+r['record_key'])
            if not r['displayed_date'] or r['category'] not in CATEGORIES:
                raise ValueError('Missing date/unsupported category: '+r['record_key'])
            if not all(np.isfinite(float(r[k])) and float(r[k])>0 for k in ['price_million','area_sqm']):
                raise ValueError('Invalid price/area: '+r['record_key'])
        seen_ids.update(ids);seen_groups.update(groups)
    return parts


def encode(rows,locations):
    # Vocabulary is fit on train only; unseen locations have all zero indicators.
    return np.asarray([[float(r['area_sqm'])]+[float(r['location_feature']==loc) for loc in locations]
                       for r in rows],dtype=np.float32)


def main(args):
    paths = [args.input_dir/(s+'.csv') for s in ['train','validation','test']]
    hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    parts = load(args.input_dir)
    if args.check_data:
        print(json.dumps({s:len(rows) for s,rows in parts.items()},indent=2))
        print('PASS: IDs/groups disjoint; labels, dates and split statuses valid. No training performed.')
        return
    try:
        import xgboost as xgb
    except ImportError:
        raise SystemExit('XGBoost is missing. Install it with this Python: python -m pip install xgboost')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    report = dict(xgboost_version=xgb.__version__,target='total asking price in million VND',
        features=['area_sqm','train-only one-hot location_feature'],seed=42,
        source_sha256={p.name:h for p,h in hashes.items()},categories={},
        limitations=['Automatically screened asking prices; not verified transactions.',
            'Suspected duplicate grouping can miss or overgroup properties.',
            'Grouped random holdouts, not future-time evaluation; small category test sets.'])
    predictions=[]
    for i,category in enumerate(CATEGORIES,1):
        subset = {s:[r for r in rows if r['category']==category] for s,rows in parts.items()}
        if any(len(rows)<5 for rows in subset.values()):
            report['categories'][category]=dict(status='insufficient_data',counts={s:len(r) for s,r in subset.items()})
            continue
        locations=sorted({r['location_feature'] for r in subset['train']})
        mats={s:xgb.DMatrix(encode(rows,locations),label=[float(r['price_million']) for r in rows])
              for s,rows in subset.items()}
        params=dict(objective='reg:squarederror',eval_metric='mae',tree_method='hist',
                    max_depth=3,eta=.03,min_child_weight=5,subsample=.8,colsample_bytree=.8,
                    reg_lambda=10,seed=42,nthread=4)
        print('Training:',category,flush=True)
        booster=xgb.train(params,mats['train'],num_boost_round=1500,
            evals=[(mats['validation'],'validation')],early_stopping_rounds=50,verbose_eval=100)
        # Native train returns the last iteration: retain only trees through best iteration.
        best=booster[:booster.best_iteration+1]
        info=dict(counts={s:len(rows) for s,rows in subset.items()},params=params,
                  best_iteration=booster.best_iteration,model_file=f'category_{i}.json')
        for split in ['validation','test']:
            pred=best.predict(mats[split])
            info[split]=metrics([float(r['price_million']) for r in subset[split]],pred)
            for row,value in zip(subset[split],pred):
                predictions.append(dict(record_key=row['record_key'],category=category,split=split,
                    actual_million=row['price_million'],predicted_million=float(value)))
        best.save_model(args.output_dir/info['model_file'])
        (args.output_dir/f'category_{i}_features.json').write_text(json.dumps(dict(
            category=category,feature_order=['area_sqm']+['location:'+loc for loc in locations],
            location_vocabulary=locations,unseen_location='all-zero location indicators'),ensure_ascii=False,indent=2),encoding='utf-8')
        report['categories'][category]=info
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
    (args.output_dir/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(args.output_dir/'holdout_predictions.csv',predictions,
             ['record_key','category','split','actual_million','predicted_million'])
    print(json.dumps(report['categories'],ensure_ascii=False,indent=2))
    print('Saved:',args.output_dir)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=BASE/'processed/training_v1')
    parser.add_argument('--output-dir',type=Path,default=BASE/'processed/xgboost_v1')
    parser.add_argument('--check-data',action='store_true',help='Validate frozen CSV splits without importing XGBoost')
    main(parser.parse_args())
