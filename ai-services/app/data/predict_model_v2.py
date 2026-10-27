"""Standalone predictor for the frozen SmartProp v2 model bundle."""
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import numpy as np


def normalize(value):
    s=' '.join(str(value or '').lower().split())
    return ''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn').replace('đ','d')


def feature_matrix(rows,spec):
    result=[]
    for row in rows:
        ward=re.sub(r'^(phuong|xa|thi tran)\s+','',normalize(row.get('ward','')))
        if ward in ['khong xac dinh','dang cap nhat']:ward=''
        match=re.fullmatch(r'(\d+)(?:\.0)?(?:\s*(?:phòng|phong)(?:\s*(?:ngủ|ngu))?)?',str(row.get('rooms') or '').strip(),re.I)
        rooms=float(match[1]) if match and 1<=int(match[1])<=30 else None
        key=row['location_feature']+'|'+ward if ward else ''
        result.append([float(row['area_sqm']),rooms if rooms is not None else np.nan,
            float(rooms is None),float(not key),float(bool(key) and key not in spec['wards'])]+
            [float(row['location_feature']==v) for v in spec['locations']]+
            [float(key==v) for v in spec['wards']])
    return np.asarray(result,dtype=np.float32)


def predict(bundle,category,rows):
    bundle=Path(bundle)
    selection=json.loads((bundle/'selection.json').read_text(encoding='utf-8'))
    info=selection['categories'][category]
    for name,digest in selection['artifact_sha256'].items():
        if hashlib.sha256((bundle/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Model artifact changed: '+name)
    area=np.array([float(r['area_sqm']) for r in rows])
    if not np.all(np.isfinite(area)&(area>0)):raise ValueError('Area must be finite and positive')
    if info['family']=='xgboost':
        import xgboost as xgb
        spec=json.loads((bundle/info['schema_file']).read_text(encoding='utf-8'))
        model=xgb.Booster();model.load_model(bundle/info['model_file'])
        y=model.predict(xgb.DMatrix(feature_matrix(rows,spec)))
        return np.exp(np.clip(y,-20,30)) if spec['target_transform']=='log' else y
    params=json.loads((bundle/info['model_file']).read_text(encoding='utf-8'))
    if info['family']=='district_median_unit_price':
        return area*np.array([params['district_median_unit_price'].get(r['location_feature'],params['global_median_unit_price']) for r in rows])
    if info['family']=='log_area_district_ridge_alpha_1':
        x=np.array([[1,(np.log(a)-params['log_area_mean'])/params['log_area_scale']]+
                    [float(r['location_feature']==d) for d in params['districts']] for r,a in zip(rows,area)])
        return np.exp(x@np.array(params['ridge_coefficients']))
    raise ValueError('Unsupported model family')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=Path(__file__).parent/'processed/model_evaluation_v2/model_bundle')
    parser.add_argument('--category',required=True,choices=['Nhà ở','Đất nền','Căn hộ chung cư'])
    parser.add_argument('--area-sqm',required=True,type=float)
    parser.add_argument('--location',required=True,help='Exact stored location_feature, e.g. Hải Châu')
    parser.add_argument('--ward',default='')
    parser.add_argument('--rooms',default='')
    args=parser.parse_args()
    value=float(predict(args.bundle,args.category,[dict(area_sqm=args.area_sqm,location_feature=args.location,ward=args.ward,rooms=args.rooms)])[0])
    print(json.dumps(dict(predicted_asking_price_million=value,predicted_asking_price_vnd=value*1e6),ensure_ascii=False,indent=2))
