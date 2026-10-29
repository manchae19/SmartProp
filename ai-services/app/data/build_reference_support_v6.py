"""Publish aggregate reference coverage; never publish prices or listing IDs."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys

import training_v3_common as data

SERVICE=data.BASE.parents[1]
if str(SERVICE) not in sys.path:sys.path.insert(0,str(SERVICE))
from app.core.model_registry import V6_RUN,V6_MANIFEST_SHA256,V6_MODEL_DIR
from app.core.location_catalog import LOCATION_LABELS

SOURCE=data.BASE/'processed/training_next_preparation/runs/4fdb8ef79db89b16'
TARGET=SERVICE/'app/core/reference_support_v6.json'


def percentile(values,q):
    ordered=sorted(values);position=(len(ordered)-1)*q
    left=math.floor(position);right=math.ceil(position)
    return round(ordered[left]+(ordered[right]-ordered[left])*(position-left),4)


def profile(rows,*,reference_manifest_sha256):
    if len({r['pipeline_group'] for r in rows})!=len(rows) or len({r['record_key'] for r in rows})!=len(rows):
        raise ValueError('Repeated reference property group/key')
    if any(r['model_split']!='train' or r['reserved_splits']!='train' for r in rows):raise ValueError('Non-training reference row')
    grouped=defaultdict(list)
    for row in rows:
        area=float(row['area_sqm'])
        if not math.isfinite(area) or area<=0:raise ValueError('Invalid reference area')
        if row['category'] not in data.CATEGORIES or row['location_feature'] not in LOCATION_LABELS:raise ValueError('Unreviewed reference category/location')
        grouped[row['category'],row['location_feature']].append(area)
    categories={category:{} for category in data.CATEGORIES}
    for (category,location),areas in sorted(grouped.items()):
        categories[category][location]=dict(reference_groups=len(areas),
            area_percentiles_sqm=dict(p05=percentile(areas,.05),p95=percentile(areas,.95)) if len(areas)>=10 else None)
    return dict(version='v6_clean_reference_support_1',model_run=V6_RUN,model_manifest_sha256=V6_MANIFEST_SHA256,
        reference_manifest_sha256=reference_manifest_sha256,reference_groups=len(rows),
        reference_semantics='Cleaned training reference, not the exact complete 2214-row release training dataset',
        policy=dict(low_reference_groups_below=10,area_percentiles=[.05,.95],minimum_groups_for_area_range=10),
        interpretation='Sample coverage and descriptive area range only; not confidence or a prediction interval',
        categories=categories)


def payload():
    manifest=json.loads((SOURCE/'manifest.json').read_text(encoding='utf8'))
    data.verify(manifest['output_sha256'],SOURCE)
    if data.sha(V6_MODEL_DIR/'manifest.json')!=V6_MANIFEST_SHA256:raise ValueError('Release differs')
    for relative,expected in manifest['input_sha256'].items():
        if data.sha(data.BASE.parents[2]/relative)!=expected:raise ValueError('Reference source differs')
    rows=data.read(SOURCE/'train.csv')
    if len(rows)!=2213:raise ValueError('Unexpected reference cohort')
    return (json.dumps(profile(rows,reference_manifest_sha256=data.sha(SOURCE/'manifest.json')),
                       ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    expected=payload()
    if TARGET.exists():
        if TARGET.read_bytes()!=expected:raise ValueError('Published reference differs; do not overwrite silently')
    elif args.verify:raise ValueError('Reference profile missing')
    else:TARGET.write_bytes(expected)
    parsed=json.loads(expected)
    cells=[cell for locations in parsed['categories'].values() for cell in locations.values()]
    print(json.dumps(dict(verified=True,path=str(TARGET),sha256=data.sha(TARGET),reference_groups=parsed['reference_groups'],
                         cells=len(cells),low_reference_cells=sum(c['reference_groups']<10 for c in cells)),ensure_ascii=False))


if __name__=='__main__':main()
