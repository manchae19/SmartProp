"""Pure contracts for a bounded, train-only nested price-target experiment."""
from collections import Counter, defaultdict
import hashlib
import math

import numpy as np
import training_v3_common as data

ARMS=['log_total_squared','log_unit_squared','log_total_absolute']
CONTROL=ARMS[0]
PARAMS=dict(tree_method='hist',device='cpu',max_depth=3,eta=.03,min_child_weight=5,
            subsample=.8,colsample_bytree=.8,reg_lambda=10,seed=42,nthread=4,disable_default_eval_metric=1)
PROTOCOL=dict(arms=ARMS,rounds=300,params=PARAMS,outer_folds=3,inner_folds=2,
    outer_salt='price-trial-v1/outer/',inner_salt='price-trial-v1/inner/',final_salt='price-trial-v1/final/',
    min_location_median_count=5,feature_arm='v6/all',selection='pooled inner MAE million VND; arm order tie break',
    early_stopping=False,train_only=True,dev_validation_scored=False,pilot_scored=False,
    final_gate=dict(aggregate_mae_reduction_pct=5,category_max_mae_increase_pct=5,
                    category_max_within20_decrease_pp=5,min_nonworse_folds=2),automatic_deployment=False)


def partition(rows, folds, salt):
    ordered=sorted(rows,key=lambda r:r['record_key'])
    keys=[r['record_key'] for r in ordered];groups=[r['pipeline_group'] for r in ordered]
    if len(set(keys))!=len(keys) or len(set(groups))!=len(groups):raise ValueError('Repeated key or candidate group')
    buckets={g:int.from_bytes(hashlib.sha256((salt+g).encode()).digest()[:8],'big')%folds for g in groups}
    for fold in range(folds):
        fit=[r for r in ordered if buckets[r['pipeline_group']]!=fold]
        held=[r for r in ordered if buckets[r['pipeline_group']]==fold]
        if len(fit)<10 or not held:raise ValueError('Too few groups for declared CV')
        yield fold,fit,held


def areas(rows):
    values=np.asarray([float(r['area_sqm']) for r in rows])
    if not np.isfinite(values).all() or (values<=0).any():raise ValueError('Invalid area')
    return values


def labels(rows,arm):
    if arm not in ARMS:raise ValueError('Unknown arm')
    values=np.asarray([float(r['price_million']) for r in rows])
    if not np.isfinite(values).all() or (values<=0).any():raise ValueError('Invalid price')
    return np.log(values/areas(rows) if arm=='log_unit_squared' else values)


def inverse(predicted,rows,arm):
    if arm not in ARMS:raise ValueError('Unknown arm')
    values=np.asarray(predicted,dtype=float)
    if values.shape!=(len(rows),) or not np.isfinite(values).all():raise ValueError('Invalid prediction')
    return np.exp(np.clip(values,-20,30))*(areas(rows) if arm=='log_unit_squared' else 1)


def params(arm):
    if arm not in ARMS:raise ValueError('Unknown arm')
    return dict(PARAMS,objective='reg:absoluteerror' if arm=='log_total_absolute' else 'reg:squarederror')


def choose(scores):
    byarm=defaultdict(list)
    for row in scores:
        if row['arm'] not in ARMS:raise ValueError('Unknown arm score')
        if not math.isfinite(row['absolute_error_sum']) or row['absolute_error_sum']<0 or row['n']<=0:raise ValueError('Invalid inner score')
        byarm[row['arm']].append(row)
    if set(byarm)!=set(ARMS):raise ValueError('Missing inner arm')
    counts={arm:sum(r['n'] for r in values) for arm,values in byarm.items()}
    if len(set(counts.values()))!=1:raise ValueError('Unequal inner coverage')
    maes={arm:sum(r['absolute_error_sum'] for r in byarm[arm])/counts[arm] for arm in ARMS}
    return min(ARMS,key=lambda arm:(maes[arm],ARMS.index(arm))),maes


def median_baseline(fit,held):
    unit=np.asarray([float(r['price_million']) for r in fit])/areas(fit)
    fallback=float(np.median(unit));locations=defaultdict(list)
    for row,value in zip(fit,unit):locations[row['location_feature']].append(float(value))
    values={key:float(np.median(v)) for key,v in locations.items() if len(v)>=PROTOCOL['min_location_median_count']}
    return np.asarray([values.get(r['location_feature'],fallback) for r in held])*areas(held)


def evaluate(predictions):
    metrics=[];folds=[]
    categories=data.CATEGORIES+['ALL']
    for category in categories:
        for method in ['control','selected','median_unit_location']:
            rows=[r for r in predictions if r['method']==method and (category=='ALL' or r['category']==category)]
            score=data.scores([r['actual_million'] for r in rows],[r['predicted_million'] for r in rows])
            metrics.append(dict(category=category,method=method,**score))
            if category!='ALL':
                for fold in range(PROTOCOL['outer_folds']):
                    subset=[r for r in rows if r['outer_fold']==fold]
                    value=data.scores([r['actual_million'] for r in subset],[r['predicted_million'] for r in subset])
                    folds.append(dict(category=category,method=method,outer_fold=fold,**value))
    return metrics,folds


def nomination_gate(metrics,folds):
    values={(r['category'],r['method']):r for r in metrics}
    before=values['ALL','control']['mae_million'];after=values['ALL','selected']['mae_million']
    gain=100*(before-after)/before if before>0 else 0
    checks=[dict(check='aggregate_mae_reduction_at_least_5pct',passed=gain>=5,value=gain)]
    for category in data.CATEGORIES:
        a,b=values[category,'control'],values[category,'selected']
        increase=100*(b['mae_million']-a['mae_million'])/a['mae_million'] if a['mae_million']>0 else (0 if b['mae_million']==0 else None)
        nonworse=sum(next(r['mae_million'] for r in folds if (r['category'],r['method'],r['outer_fold'])==(category,'selected',f))
                     <=next(r['mae_million'] for r in folds if (r['category'],r['method'],r['outer_fold'])==(category,'control',f))
                     for f in range(PROTOCOL['outer_folds']))
        checks += [dict(category=category,check='category_mae_increase_at_most_5pct',passed=increase is not None and increase<=5,value=increase),
                   dict(category=category,check='within20_decrease_at_most_5pp',passed=a['within_20pct']-b['within_20pct']<=5,value=a['within_20pct']-b['within_20pct']),
                   dict(category=category,check='at_least_2_nonworse_folds',passed=nonworse>=2,value=nonworse)]
    return dict(passed=all(c['passed'] for c in checks),checks=checks,aggregate_mae_reduction_pct=gain,
                independent_test=False,production_promotion_allowed=False)


def collection_priorities(rows,features,predictions):
    predicted={r['record_key']:r for r in predictions if r['method']=='control'}
    groups=defaultdict(list)
    for row in rows:groups[row['category'],row['location_feature']].append(row)
    result=[]
    for (category,location),members in groups.items():
        errors=[100*abs(predicted[r['record_key']]['predicted_million']-float(r['price_million']))/float(r['price_million']) for r in members]
        missing={field:sum(not str(features[r['record_key']].get(field,'')) for r in members) for field in ['rooms_completed','floors_claim','access_claim','house_subtype_claim']}
        result.append(dict(category=category,location=location,train_groups=len(members),
            median_ape_pct=float(np.median(errors)),within20_pct=float(np.mean(np.asarray(errors)<=20)*100),
            **{'missing_'+key:value for key,value in missing.items()},
            priority='sparse_train' if len(members)<10 else 'high_train_oof_error' if np.median(errors)>=25 else 'monitor',
            interpretation='Train-only internal slice; future targeted samples are not a representative market benchmark'))
    return sorted(result,key=lambda r:(r['category'],r['priority']!='sparse_train',-r['median_ape_pct'],r['location']))
