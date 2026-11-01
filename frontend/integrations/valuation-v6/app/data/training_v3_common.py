"""Frozen, explicit feature contract and integrity helpers for SmartProp v3."""
import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROCESSED = BASE / 'processed'
CATEGORIES = ['Nhà ở', 'Đất nền', 'Căn hộ chung cư']
FIELDS = ['record_key', 'source', 'category', 'model_split', 'pipeline_group',
          'reserved_splits', 'area_sqm', 'price_million', 'location_feature',
          'ward_source', 'rooms', 'displayed_date', 'date_basis',
          'geographic_scope_status', 'detail_url', 'label_quality']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False), encoding='utf-8')


def verify(hashes, base=BASE):
    for relative, expected in hashes.items():
        if sha(base / relative) != expected:
            raise ValueError('Frozen file changed: ' + relative)


def outputs(directory):
    return {p.relative_to(directory).as_posix(): sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'manifest.json'}


def normalized(value):
    value = unicodedata.normalize('NFD', str(value or '').lower().replace('đ', 'd'))
    return ' '.join(''.join(c for c in value if unicodedata.category(c) != 'Mn').split())


def safe_source_features(row):
    # Read only named structured fields; never extract features from price/title/description.
    raw = json.loads(row['raw_json'])
    ward = re.sub(r'^(phuong|xa|thi tran)\s+', '', normalized(raw.get('ward')))
    if ward in {'', 'khong xac dinh', 'dang cap nhat'}:
        ward = ''
    match = re.fullmatch(r'(\d+)(?:\.0)?(?:\s*phong(?:\s*ngu)?)?',
                         normalized(raw.get('rooms')))
    rooms = str(int(match[1])) if match and 1 <= int(match[1]) <= 30 else ''
    if row['category'] == 'Đất nền':
        rooms = ''
    return dict(ward_source=ward, rooms=rooms)


def cohort(row):
    if row['pipeline_status'] != 'eligible':
        return None
    splits = set(filter(None, row['reserved_splits'].split(';')))
    if row['training_allowed'] == 'True':
        if (row['protected_holdout'] != 'False' or row['assigned_split'] != 'train'
                or splits != {'train'}):
            raise ValueError('Train has a holdout reservation: ' + row['record_key'])
        return 'train'
    if 'validation' in splits and 'test' not in splits:
        if row['protected_holdout'] != 'True':
            raise ValueError('Validation is not protected')
        return 'validation'
    return 'reserved'


def model_row(row, split):
    result = {k: row.get(k, '') for k in FIELDS}
    result.update(model_split=split, **safe_source_features(row))
    return result


def validate_parts(parts, reserved_groups=()):
    ids, groups = set(), set(reserved_groups)
    for split in ('train', 'validation'):
        rows = parts[split]
        keys = {r['record_key'] for r in rows}
        current = {r['pipeline_group'] for r in rows}
        if len(keys) != len(rows) or len(current) != len(rows) or keys & ids or current & groups:
            raise ValueError('Repeated ID or suspected property group across cohorts')
        for r in rows:
            if r['model_split'] != split or r['category'] not in CATEGORIES:
                raise ValueError('Unexpected split or category')
            reservation = set(r['reserved_splits'].split(';'))
            if split == 'train' and reservation != {'train'}:
                raise ValueError('Reserved holdout in train')
            if split == 'validation' and ('test' in reservation or 'validation' not in reservation):
                raise ValueError('Test reservation in validation')
            if not r['displayed_date'] or not r['geographic_scope_status'].startswith('accepted_'):
                raise ValueError('Missing date or geography evidence')
            if not r['location_feature']:
                raise ValueError('Missing location feature')
            for field in ('price_million', 'area_sqm'):
                if not math.isfinite(float(r[field])) or float(r[field]) <= 0:
                    raise ValueError('Invalid numeric label/area')
        ids.update(keys)
        groups.update(current)


def schema(train):
    locations = sorted({r['location_feature'] for r in train})
    wards = Counter(r['location_feature'] + '|' + r['ward_source']
                    for r in train if r['ward_source'])
    wards = sorted(w for w, count in wards.items() if count >= 3)
    return dict(locations=locations, wards=wards, min_ward_train_count=3,
                target_transform='natural_log',
                feature_names=['area_sqm', 'rooms', 'rooms_missing', 'ward_missing',
                               'ward_unseen_or_rare'] + ['location:' + v for v in locations]
                              + ['ward:' + v for v in wards])


def encode(rows, spec):
    import numpy as np
    matrix = []
    for row in rows:
        room = float(row['rooms']) if row['rooms'] and row['category'] != 'Đất nền' else np.nan
        ward = row['location_feature'] + '|' + row['ward_source'] if row['ward_source'] else ''
        matrix.append([float(row['area_sqm']), room, float(np.isnan(room)), float(not ward),
                       float(bool(ward) and ward not in spec['wards'])]
                      + [float(row['location_feature'] == v) for v in spec['locations']]
                      + [float(ward == v) for v in spec['wards']])
    return np.asarray(matrix, dtype=np.float32)


def scores(actual, predicted):
    import numpy as np
    y, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if len(y) == 0 or len(y) != len(p) or not np.isfinite(p).all() or (y <= 0).any():
        raise ValueError('Invalid predictions or labels')
    errors = np.abs(y - p)
    ape = errors / y * 100
    variance = np.sum((y - y.mean()) ** 2)
    return dict(n=len(y), mae_million=float(errors.mean()),
                rmse_million=float(np.sqrt(np.mean((y-p)**2))),
                mape_pct=float(ape.mean()), median_ape_pct=float(np.median(ape)),
                within_20pct=float(np.mean(ape <= 20)*100),
                above_50pct=int(np.sum(ape > 50)),
                r2=float(1-np.sum((y-p)**2)/variance) if variance > 0 else None)
