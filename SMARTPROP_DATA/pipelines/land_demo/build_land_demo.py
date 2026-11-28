"""Build the processed Hòa Xuân land demo dataset from the unchanged raw copy.

    python -X utf8 SMARTPROP_DATA/pipelines/land_demo/build_land_demo.py [--version HX-LAND-DEMO-20261126]

Reads  SMARTPROP_DATA/raw/land_demo_hoa_xuan/<version>/        (never modified)
Writes SMARTPROP_DATA/processed/land_demo_hoa_xuan/<version>/   (normalized, relations, prices,
       flood, export, quarantine, manifest) and SMARTPROP_DATA/reports/LAND_DEMO_<version>.{json,md}.

The chatbot reads the raw copy through the same engine (ai-services/app/land), so the processed
files are an audit/export of exactly what the app shows, not a second source of truth.
"""
import argparse, collections, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--version', default='HX-LAND-DEMO-20261126')
args = parser.parse_args()
os.environ['SMARTPROP_LAND_DATA_VERSION'] = args.version
sys.path.insert(0, str(REPO / 'ai-services'))
from app.land import engine as e, imported_data as im  # noqa: E402
from app.land.paths import DATA_ROOT, PROCESSED_DIR  # noqa: E402

OUT = PROCESSED_DIR
for sub in ('normalized', 'relations', 'prices', 'flood', 'export'):
    (OUT / sub).mkdir(parents=True, exist_ok=True)
def write(rel, data):
    (OUT / rel).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

KIND = {}
for c in e.byid: KIND[c] = 'PLANNING_CELL'
for c in im.SOURCE_ROWS: KIND[c] = 'GULAND_PARCEL'
for c in e.unified_lots: KIND[c] = 'PROJECT_LOT_LOCATED'
for c in im.EXTRAS: KIND[c] = 'PROJECT_LOT_UNLOCATED'

records, prices, floods, relations, idmap = [], [], [], [], []
for code, kind in KIND.items():
    r = e.resolve(code)
    idmap.append({'landId': e.land_id(code), 'sourceCode': code, 'kind': kind})
    demo = r.get('demoPresentation') or {}
    records.append({'landId': e.land_id(code), 'sourceCode': code, 'kind': kind,
                    'displayName': r.get('displayName') or code, 'purposeGroup': r.get('purposeGroup') or e.purpose(r) if kind == 'PLANNING_CELL' else r.get('purposeGroup', 'housing'),
                    'areaSqm': r.get('computedAreaSqm'), 'sourceLandLabel': r.get('planningLabel') or r.get('landLabel'),
                    'located': kind != 'PROJECT_LOT_UNLOCATED', 'runtimeEligible': kind != 'PLANNING_CELL' or code in e.activeids,
                    'sourceEvidence': {'legalStatus': r.get('legalStatus', 'UNKNOWN'), 'verifiedForThisParcel': False},
                    'demoOverride': ({'rulesVersion': demo.get('version'), 'landType': demo.get('landType'), 'ownershipDocument': demo.get('ownershipDocument'),
                                      'recovery': demo.get('recovery'), 'dispute': demo.get('dispute'), 'compensation': demo.get('compensation'),
                                      'basis': 'USER_APPROVED_DEMO_SCENARIO'} if demo else None)})
    # Price evidence: every price says what it is, its unit, date and source.
    if r.get('roadPriceEvidence'):
        p = r['roadPriceEvidence']
        prices.append({'sourceCode': code, 'type': 'ROAD_ASKING_ESTIMATE', 'valueVnd': p['estimatedReferenceVnd'], 'unit': 'VND_TOTAL_FOR_COMPUTED_AREA',
                       'unitPriceMillionPerSqm': p['unitMillionPerSqm'], 'date': 'UNKNOWN', 'source': p['sourceUrl'], 'sampleCount': p['sampleCount'],
                       'confidence': p['confidence'], 'method': p['referenceMethod']})
    if r.get('demoPriceVnd') and kind == 'PLANNING_CELL':
        prices.append({'sourceCode': code, 'type': 'SIMULATED_DEMO', 'valueVnd': r['demoPriceVnd'], 'unit': 'VND_TOTAL_FOR_COMPUTED_AREA',
                       'unitPriceVndPerSqm': r.get('demoUnitPriceVndPerSqm'), 'date': 'NOT_APPLICABLE', 'source': 'DETERMINISTIC_HASH_10_60M_PER_SQM',
                       'label': 'Giá mô phỏng (không phải giá thị trường)'})
    if kind in ('PROJECT_LOT_LOCATED', 'PROJECT_LOT_UNLOCATED'):
        v = r.get('referencePriceVnd')
        lot = r.get('sourceLotEvidence') or im.EXTRAS.get(code) or {}
        if v: prices.append({'sourceCode': code, 'type': 'HISTORICAL_ASKING', 'valueVnd': v, 'unit': 'VND_TOTAL_FOR_LOT', 'date': lot.get('sourceDate') or 'UNKNOWN', 'source': lot.get('sourceUrl')})
    if kind == 'GULAND_PARCEL' and r.get('priceVnd'):
        prices.append({'sourceCode': code, 'type': 'SOURCE_ASKING', 'valueVnd': r['priceVnd'], 'unit': 'VND_TOTAL_FOR_PARCEL', 'date': 'UNKNOWN', 'source': r.get('sourceUrl')})
    fd = r.get('floodDisplay') or {}
    floods.append({'sourceCode': code, 'relation': fd.get('relation') or ('UNLOCATED' if fd.get('basis') == 'UNLOCATED' else 'NO_SOURCE_RECORD' if fd else 'NOT_APPLICABLE'),
                   'display': fd.get('display'), 'isDemoAssumption': fd.get('isDemoAssumption', False), 'recordIds': fd.get('recordIds', [])})
    if kind == 'GULAND_PARCEL':
        for cell in r.get('planningCandidates', []):
            relations.append({'from': code, 'to': cell, 'type': 'PARCEL_OVERLAPS_PLANNING_CELL', 'basis': 'SOURCE_GEOMETRY_CANDIDATE'})
    if kind == 'PROJECT_LOT_LOCATED':
        relations.append({'from': code, 'to': e.unified_lots[code]['planningCellId'], 'type': 'PROJECT_LOT_PIN_IN_PLANNING_CELL', 'basis': 'SOURCE_LISTING_PIN'})
    if kind.startswith('PROJECT_LOT'):
        relations.append({'from': code, 'to': 'PROJECT:Euro Village 2', 'type': 'BELONGS_TO_PROJECT', 'basis': 'SOURCE_PROJECT_LISTING'})

quarantine = ([{'sourceCode': x['id'], 'kind': 'GULAND_PARCEL', 'reasons': x['reviewFlags']} for x in im.RECORDS if x['reviewFlags']] +
              [{'sourceCode': c, 'kind': 'PLANNING_CELL', 'reasons': ['NOT_IN_RUNTIME_VALIDATED_SET']} for c in e.byid if c not in e.activeids])
write('normalized/land-records.json', records); write('relations/id-map.json', idmap); write('relations/relations.json', relations)
write('prices/price-evidence.json', prices); write('flood/flood-relations.json', floods)
write('flood/flood-catalog-check.json', {'records': len(e.FLOOD_CATALOG['records']), 'byType': dict(collections.Counter(x['record_type'] for x in e.FLOOD_CATALOG['records'])), 'sourceCommit': e.FLOOD_CATALOG['commit']})
write('export/README.json', {'runtime': 'ai-services/app/land reads ' + str(DATA_ROOT.relative_to(REPO)), 'note': 'No separate export copy; the engine is the single reader.'})
write('quarantine.json', quarantine)

rules = json.loads((DATA_ROOT / 'outputs/demo-policy-20261126.json').read_text(encoding='utf-8'))
rules['flood'] = {'noSourceRecord': 'Chưa có bản ghi ngập trùng tuyến đường nguồn (giả định kịch bản demo — không xác nhận an toàn ngập)', 'relations': ['DIRECT_SOURCE_MATCH', 'SOURCE_TEXT_MENTION', 'ILLUSTRATIVE_CORRIDOR'], 'unlocated': 'Chưa xác định vị trí để đối chiếu', 'corridorMeters': 80, 'corridorIsIllustrative': True}
rules['compensation'] = 'Chưa xác minh'
cfg = REPO / 'SMARTPROP_DATA' / 'demo' / 'config' / f'land-demo-rules-{args.version}.json'
cfg.write_text(json.dumps(rules, ensure_ascii=False, indent=1), encoding='utf-8')

sources = sorted(p for p in DATA_ROOT.rglob('*') if p.is_file())
counts = {'byKind': dict(collections.Counter(KIND.values())),
          'planningCellsActive': len(e.activeids), 'planningCellsQuarantined': sum(1 for q in quarantine if q['kind'] == 'PLANNING_CELL'),
          'gulandParcelsSearchable': len(im.SOURCE_ROWS), 'gulandRecordsQuarantined': sum(1 for q in quarantine if q['kind'] == 'GULAND_PARCEL'),
          'pricesByType': dict(collections.Counter(p['type'] for p in prices)),
          'floodRelations': dict(collections.Counter(f['relation'] for f in floods)), 'relations': dict(collections.Counter(r['type'] for r in relations)),
          'floodCatalog': len(e.FLOOD_CATALOG['records'])}
manifest = {'version': args.version, 'builtAt': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'raw': str(DATA_ROOT.relative_to(REPO)),
            'rules': str(cfg.relative_to(REPO)), 'counts': counts,
            'demoOnly': True, 'containsSyntheticData': True, 'publicApproved': False, 'demoApproved': True,
            'rightsApprovalRef': None, 'excludedFromValuationComparableMarket': True,
            'notCombined': 'Planning cells, Guland parcels and project lots are different entity types; counts are never added into one total of real lots.',
            'processing': ['Planning cells: active = runtime-validated, area > 0', 'Simulated price: only residential cells 60–500 m², deterministic 10–60 million VND/m², labelled SIMULATED_DEMO',
                           'Road estimate replaces simulated price for search where present; simulated value kept in price-evidence', 'Guland: rows with review flags quarantined',
                           'Project lots without a source pin stay unlocated; no geometry is created', 'Flood: catalog is the pinned git snapshot; relations computed by app.land.flood_evidence'],
            'sources': [{'path': str(p.relative_to(DATA_ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sources]}
write('manifest.json', manifest)
rep = REPO / 'SMARTPROP_DATA' / 'reports'
(rep / f'LAND_DEMO_{args.version}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
md = [f'# Land demo {args.version}', '', f'Built {manifest["builtAt"]} from `{manifest["raw"]}`.', '', '| Metric | Value |', '|---|---|']
md += [f'| {k} | {json.dumps(v, ensure_ascii=False)} |' for k, v in counts.items()]
(rep / f'LAND_DEMO_{args.version}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
print(json.dumps(counts, ensure_ascii=False, indent=1))
