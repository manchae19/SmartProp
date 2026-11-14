import json
import math
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

import numpy as np
import xgboost as xgb
from app.models.xgboost.predictor_v6 import PredictorV6
from app.models.xgboost.predictor_v1_3 import PredictorV1_3

p6 = PredictorV6()
sample = {'category': 'Nhà ở', 'area_sqm': 80.0, 'location_feature': 'Hải Châu', 'ward': 'Hải Châu 1'}
resp6 = p6.predict(sample)
print("V6 prediction:", resp6['predicted_asking_price_vnd'])

category = sample['category']
spec = p6.specs[category]
booster6 = p6.models[category]
row = dict(record_key='api:input', source='user_input', category=category, rooms='', area_sqm='80.0', location_feature='Hải Châu', ward_source='hai chau 1')
origin = dict(title='', raw_json='{"source_category":""}')
feature, _ = p6.extractor.extract(row, origin, '')
matrix = p6.extractor.encode([row], {row['record_key']: feature}, spec)
dmatrix = xgb.DMatrix(matrix, feature_names=spec['feature_names'])

contribs = booster6.predict(dmatrix, pred_contribs=True)
print("V6 SHAP contribs shape:", contribs.shape)
print("Feature names count:", len(spec['feature_names']))
base_value = contribs[0, -1]
print("Base value (expected log price):", base_value)
raw_pred = booster6.predict(dmatrix)[0]
print("Raw log pred:", raw_pred)
print("Sum of all contribs:", np.sum(contribs[0]))
print("Difference (additivity):", abs(np.sum(contribs[0]) - raw_pred))

# Get top 5 positive and top 5 negative SHAP features for V6
feat_contribs = []
for name, val in zip(spec['feature_names'], contribs[0, :-1]):
    if abs(val) > 1e-5:
        feat_contribs.append((name, float(val)))

feat_contribs.sort(key=lambda x: abs(x[1]), reverse=True)
print("\nTop 5 contributing features for V6:")
for name, val in feat_contribs[:5]:
    direction = "TĂNG" if val > 0 else "GIẢM"
    print(f"  {name}: {val:+.4f} log units ({direction})")

# Now check V1.3
p1_3 = PredictorV1_3()
resp1_3 = p1_3.predict_from_v6_payload(sample)
print("\nV1.3 prediction:", resp1_3['predicted_asking_price_vnd'])

import pandas as pd
from app.models.xgboost.features_v1_3 import transform
rec = resp1_3['features_used']
input_row = {
    "area": float(rec["area"]),
    "raw_floor_count": rec.get("floor_count"),
    "raw_frontage_width": rec.get("frontage_width"),
    "raw_road_width": rec.get("road_width"),
    "raw_bedroom_count": rec.get("bedroom_count"),
    "raw_bathroom_count": rec.get("bathroom_count"),
    "normalized_type": rec["normalized_type"],
    "district": rec["district"],
    "ward": rec.get("ward"),
    "raw_street_name": rec.get("street_name"),
    "raw_project_name": rec.get("project_name"),
    "raw_house_direction": rec.get("house_direction"),
    "raw_balcony_direction": rec.get("balcony_direction"),
}
df_in = pd.DataFrame([input_row])
X1_3 = transform(df_in, p1_3.schema)
booster1_3 = p1_3.model.get_booster()
dmat1_3 = xgb.DMatrix(X1_3, feature_names=list(X1_3.columns))
contribs1_3 = booster1_3.predict(dmat1_3, pred_contribs=True)
print("V1.3 SHAP contribs shape:", contribs1_3.shape)
base_val1_3 = contribs1_3[0, -1]
raw_pred1_3 = booster1_3.predict(dmat1_3)[0]
print("V1.3 Base value (bias):", base_val1_3)
print("V1.3 Raw log pred:", raw_pred1_3)
print("V1.3 Sum of contribs:", np.sum(contribs1_3[0]))
print("V1.3 Additivity diff:", abs(np.sum(contribs1_3[0]) - raw_pred1_3))

feat_contribs1_3 = []
for name, val in zip(list(X1_3.columns), contribs1_3[0, :-1]):
    if abs(val) > 1e-5:
        feat_contribs1_3.append((name, float(val)))
feat_contribs1_3.sort(key=lambda x: abs(x[1]), reverse=True)
print("\nTop 5 contributing features for V1.3:")
for name, val in feat_contribs1_3[:5]:
    direction = "TĂNG" if val > 0 else "GIẢM"
    print(f"  {name}: {val:+.4f} log units ({direction})")
