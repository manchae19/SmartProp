import sys
from pathlib import Path
SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

import math
import numpy as np
import xgboost as xgb
from app.models.xgboost.predictor_v6 import PredictorV6

p6 = PredictorV6()
sample = {
    'category': 'Nhà ở',
    'area_sqm': 80.0,
    'location_feature': 'Hải Châu',
    'ward': 'Hải Châu 1',
    'floors': 2.0,
    'access_type': 'frontage',
    'rooms': 3
}

category = sample['category']
spec = p6.specs[category]
booster = p6.models[category]
row = dict(record_key='api:input', source='user_input', category=category, rooms='3', area_sqm='80.0', location_feature='Hải Châu', ward_source='hai chau 1')
origin = dict(title='', raw_json='{"source_category":""}')
feature, _ = p6.extractor.extract(row, origin, '')
feature['floors_claim'] = 2.0
feature['access_claim'] = 'frontage'
matrix = p6.extractor.encode([row], {row['record_key']: feature}, spec)
dmatrix = xgb.DMatrix(matrix, feature_names=spec['feature_names'])

contribs = booster.predict(dmatrix, pred_contribs=True)[0]
base_log = float(contribs[-1])
base_price_vnd = int(np.exp(base_log) * 1_000_000)

shap_items = []
for name, val in zip(spec['feature_names'], contribs[:-1]):
    val_float = float(val)
    if abs(val_float) < 1e-4:
        continue
    impact_pct = round((math.exp(val_float) - 1.0) * 100, 2)
    direction = "increase" if val_float > 0 else "decrease"
    
    # Friendly label
    label = name
    if name.startswith("location:"):
        label = f"Địa bàn: {name.split(':', 1)[1]}"
    elif name == "floors_claim":
        label = f"Số tầng nhà ({feature.get('floors_claim', 2)} tầng)"
    elif name == "access_frontage":
        label = "Lối vào mặt tiền đường"
    elif name == "access_alley":
        label = "Lối vào kiệt/hẻm"
    elif name.startswith("ward:"):
        label = f"Phường: {name.split(':', 1)[1]}"
    elif name == "ward_missing":
        label = "Thông tin phường/xã"
    elif name == "rooms_completed":
        label = f"Số phòng ngủ ({feature.get('rooms_completed', 3)} PN)"
        
    shap_items.append({
        "feature_name": name,
        "label": label,
        "shap_value": round(val_float, 4),
        "impact_pct": impact_pct,
        "direction": direction
    })

shap_items.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
print("Base log price:", base_log)
print("Base price VND:", f"{base_price_vnd:,} VND")
print("Top 6 SHAP factors:")
for it in shap_items[:6]:
    print(f"  {it['label']}: {it['shap_value']:+.4f} ({it['impact_pct']:+.1f}%) [{it['direction']}]")

