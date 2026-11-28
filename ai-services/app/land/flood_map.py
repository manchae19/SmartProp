"""Serve only real OSM road reference lines; do not manufacture flood extents."""
from .paths import FLOOD_DIR
import json
from pathlib import Path
from .flood_evidence import CATALOG

PATH=FLOOD_DIR/'flood-map-context.geojson'
DATA=json.loads(PATH.read_text(encoding='utf-8'))
RECORDS={r['id']:r for r in CATALOG['records']}


def map_context(ids=None):
    chosen=set(ids) if ids is not None else set(RECORDS)
    features=[]
    for source in DATA['features']:
        matches=[rid for rid in source['properties']['recordIds'] if rid in chosen]
        if matches:
            features.append({**source,'properties':{**source['properties'],'recordIds':matches}})
    linked={rid for f in features for rid in f['properties']['recordIds']}
    return {'type':'FeatureCollection','features':features,'records':[RECORDS[rid] for rid in sorted(chosen) if rid in RECORDS],
            'metadata':{**DATA['metadata'],'requestedRecords':len(chosen),'mappedRecords':len(linked),
                        'unmappedRecordIds':sorted(chosen-linked),'hasVerifiedFloodPolygons':False,
                        'notice':'💧 Tuyến xanh và viền xanh nhạt: đường OSM có tên trong nguồn nguy cơ ngập. Viền là hiệu ứng hiển thị, không phải ranh vùng ngập. Chưa xác định điểm/đoạn ngập cụ thể.'}}
