"""Read-only flood evidence adapter for the isolated Hoa Xuan demo.

Uses a pinned Git seed snapshot, not a live backend connection. Nearby-road
context never becomes parcel-level or confirmed street-frontage evidence.
"""
from .paths import FLOOD_DIR
import json
import pathlib
import re
import unicodedata

CATALOG = json.loads((FLOOD_DIR/'flood-catalog-full.json').read_text(encoding='utf-8'))


def fold(value):
    return ' '.join(unicodedata.normalize('NFD', (value or '').lower().replace('đ', 'd')).encode('ascii', 'ignore').decode().split())


def street_key(value):
    return re.sub(r'^(?:duong|street)\s+', '', fold(value))


def is_flood_question(question):
    return bool(re.search(r'\b(?:ngap|lut|lu lut|mua lon|ngap ung)\b', fold(question)))


def evidence(address=None, ward='Phường Hòa Xuân', geometry=None):
    address = address or {}
    road = address.get('road')
    records = [r for r in CATALOG['records'] if fold(r['current_unit']) == fold(ward)]
    items = []
    for record in records:
        # Strict street equality agrees with the project's current query.
        exact = bool(road and street_key(road) == street_key(record['street']))
        # Preserve other explicitly named roads as text context only. No inferred
        # geometry, no automatic reinterpretation as the database street field.
        key = street_key(road)
        mentioned = bool(key and re.search(r'(?<![a-z0-9])' + re.escape(key) + r'(?![a-z0-9])', fold(record['location_text'])))
        if exact or mentioned:
            items.append({**record, 'matchBasis': 'NEARBY_ROAD_CONTEXT' if exact else 'SOURCE_TEXT_ROAD_CONTEXT', 'parcelMatch': False})
    if geometry:
        from .flood_spatial import matches
        spatial=matches(json.dumps(geometry,sort_keys=True))
        byid={r['id']:r for r in CATALOG['records']};existing={r['id'] for r in items}
        for match in spatial:
            if match['id'] not in existing:
                items.append({**byid[match['id']], 'matchBasis':'WITHIN_ILLUSTRATIVE_MAP_CORRIDOR','distanceMeters':match['distanceMeters'],'referenceRoad':match['roadName'],'parcelMatch':False})
    for item in items:
        item['relation'] = RELATION[item['matchBasis']]
    items.sort(key=lambda i: (RELATION_ORDER.index(i['relation']), i.get('distanceMeters') or 0, i['id']))
    relation = items[0]['relation'] if items else 'NO_SOURCE_RECORD'
    status = 'NEARBY_ROAD_CONTEXT' if items else 'INSUFFICIENT_EVIDENCE'
    return {'status': status, 'relation': relation, 'message': relation_message(items, road), 'nearbyRoad': road,
            'currentUnit': ward, 'parcelMatch': False, 'items': items,
            'integrationMode': CATALOG['mode'], 'sourceCommit': CATALOG['commit']}


# Three different things, never merged into one wording:
#  DIRECT_SOURCE_MATCH   — the source names this street inside this current ward
#                          (the backend PrePurchaseService rule: same street + same ward).
#  SOURCE_TEXT_MENTION   — the source description mentions the street near the lot.
#  ILLUSTRATIVE_CORRIDOR — the lot touches the 80 m display corridor drawn around an OSM road
#                          the source names. A display aid, not a surveyed flood extent.
RELATION = {'NEARBY_ROAD_CONTEXT': 'DIRECT_SOURCE_MATCH', 'SOURCE_TEXT_ROAD_CONTEXT': 'SOURCE_TEXT_MENTION',
            'WITHIN_ILLUSTRATIVE_MAP_CORRIDOR': 'ILLUSTRATIVE_CORRIDOR'}
RELATION_ORDER = ['DIRECT_SOURCE_MATCH', 'SOURCE_TEXT_MENTION', 'ILLUSTRATIVE_CORRIDOR']


def relation_message(items, road=None):
    """Always quote the location as the SOURCE states it, never the road the lot sits on."""
    if not items:
        return ('Chưa tìm thấy bản ghi nguy cơ ngập theo tên đường hoặc tuyến tham chiếu gần lô. '
                'Điều này không có nghĩa lô không ngập.')
    top = items[0]
    where = '“' + top['location_text'] + '”'
    if top['relation'] == 'DIRECT_SOURCE_MATCH':
        text = ('Nguồn nêu nguy cơ ngập khi mưa lớn tại ' + where + '. Lô ở gần ' + (road or 'tuyến này') +
                ', trùng tên đường và địa bàn với nguồn')
    elif top['relation'] == 'SOURCE_TEXT_MENTION':
        text = 'Mô tả của nguồn có nhắc tuyến đường gần lô: ' + where
    else:
        text = ('Lô nằm trong dải minh họa 80 m quanh tuyến tham chiếu ' + (top.get('referenceRoad') or 'trong nguồn') +
                ' của vị trí nguồn ' + where + '. Dải này chỉ để minh họa, không phải ranh ngập đo đạc')
    return text + '; chưa xác nhận hiện trạng ngập của riêng lô này.'


def answer(value):
    lines = ['Ngập lụt: ' + value['message']]
    for item in value['items']:
        lines += ['Vị trí trong nguồn: ' + item['location_text'],
                  'Nguồn: ' + item['source_title'] + ' (' + item['publication_date'] + ').',
                  item['source_url']]
    return '\n'.join(lines)
