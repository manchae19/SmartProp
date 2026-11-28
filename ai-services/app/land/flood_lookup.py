"""Catalogue search, distinct from parcel evidence and from live flood status."""
from .paths import FLOOD_DIR
import json
import pathlib
import re
from collections import Counter
from .flood_evidence import CATALOG, fold, is_flood_question

ADMIN = json.loads((FLOOD_DIR/'flood-admin-mapping.json').read_text(encoding='utf-8'))
TYPES = {'PLANNED_RISK': 'Nguy cơ ngập khi mưa lớn', 'RECORDED_POINT': 'Ghi nhận ngập theo nguồn', 'WEATHER_WARNING': 'Cảnh báo thời tiết lịch sử'}
MORE = re.compile(r'\b(tiep|them|khac|con)\b')


def contains(text, name):
    return bool(re.search(r'(?<![a-z0-9])' + re.escape(fold(name)) + r'(?![a-z0-9])', fold(text)))


def lookup(question, state):
    n = fold(question)
    follow = state.get('lastDomain') == 'flood' and bool(re.fullmatch(r'(?:xem |cho xem |con |cac |vi tri |diem |vung |nao |khac |khong |nua |hay |tiep |them|\?)+', n)) and bool(MORE.search(n))
    if not is_flood_question(question) and not follow:
        return None
    # Explicit plot questions always go through the plot selection path.
    if re.search(r'dn-qh-|\b(?:lo|o)(?: dat)?\s+(?:nay|do|thu|\d)', n):
        state['lastDomain'] = 'plot'
        return None
    if not follow and re.fullmatch(r'(?:cho nay |co |bi |ngap |lut |khong|\?)+', n):
        return None
    if re.search(r'\b(hien tai|bay gio|hom nay|dang ngap|thoi gian thuc)\b', n):
        return {'answer': 'Chưa có dữ liệu ngập theo thời gian thực. Bạn có thể hỏi “Danh sách vị trí nguy cơ ngập Đà Nẵng” để tra nguồn lịch sử và danh mục nguy cơ khi mưa lớn.', 'rows': [], 'floodRecords': [], 'responseKind': 'FLOOD_LIVE_UNAVAILABLE'}
    if follow:
        filters = state['floodFilters']
        offset = state.get('floodOffset', 0) + 10
    else:
        filters = {'type': 'PLANNED_RISK', 'ward': None, 'district': None, 'road': None, 'recordId': None}
        offset = 0
        if contains(n, 'tat ca du lieu') or contains(n, 'toan bo du lieu'):
            filters['type'] = None
        if re.search(r'ghi nhan|tung ngap|lich su ngap', n): filters['type'] = 'RECORDED_POINT'
        if re.search(r'canh bao', n): filters['type'] = 'WEATHER_WARNING'
        rid = re.search(r'\bpl8-[ivx]+-\d+\b', n)
        if rid: filters['recordId'] = rid[0].upper()
        district = next((name for name in ADMIN['historicalDistricts'] if contains(n, 'quan ' + name) or contains(n, 'huyen ' + name) or contains(n, name + ' cu')), None)
        if district is None and contains(n, 'Hòa Vang') and not re.search(r'\bxa\b', n):
            district = next((name for name in ADMIN['historicalDistricts'] if fold(name) == 'hoa vang'), None)
        if district:
            filters['district'] = district
        else:
            units = {r['current_unit'] for r in CATALOG['records'] if r.get('current_unit')}
            for ward in sorted(units, key=len, reverse=True):
                short = re.sub(r'^(Phường|Xã|Đặc khu) ', '', ward)
                if contains(n, ward) or contains(n, short):
                    filters['ward'] = ward
                    break
            if not filters['ward']:
                for ward in sorted(ADMIN['historicalWards'], key=lambda w: len(w['ward']), reverse=True):
                    if contains(n, ward['ward']):
                        if ward.get('mappingCertainty') == 'DETERMINISTIC_MANY_TO_ONE':
                            filters['ward'] = ward['nq1659Unit']
                        else:
                            return {'answer': 'Địa bàn cũ này có thay đổi một phần ranh giới. Hãy nêu phường hiện tại hoặc quận cũ để tránh đối chiếu nhầm.', 'rows': [], 'floodRecords': [], 'responseKind': 'FLOOD_CLARIFICATION'}
                        break
        roads = {r['street'] for r in CATALOG['records'] if r.get('street')}
        for record in CATALOG['records']:
            if record['location_text'].startswith('Các tuyến đường '):
                roads.update(record['location_text'][len('Các tuyến đường '):].split(', '))
        matched = [road for road in roads if contains(n, road)]
        if matched: filters['road'] = max(matched, key=len)
        elif re.search(r'\bduong\s+\S', n):
            return {'answer': 'Chưa tìm thấy tuyến đường bạn nêu trong danh mục trên Git. Điều này không chứng minh tuyến đường không ngập.', 'rows': [], 'floodRecords': [], 'responseKind': 'FLOOD_NO_MATCH'}
        if not filters['ward'] and not filters['district'] and not filters['road'] and not filters['recordId']:
            if re.search(r'\b(hue|ha noi|sai gon|ho chi minh|quang ngai)\b', n):
                return {'answer': 'Danh mục hiện chỉ có dữ liệu Đà Nẵng; chưa có dữ liệu cho địa bàn bạn hỏi.', 'rows': [], 'floodRecords': [], 'responseKind': 'FLOOD_OUTSIDE_COVERAGE'}
            known = re.search(r'da nang|tat ca|toan bo|danh sach|nhung|cac vung|cac diem|cac khu|vi tri|khu vuc|o dau', n)
            if not known:
                return {'answer': 'Bạn muốn tra địa bàn hoặc tuyến đường nào? Ví dụ: “Nguy cơ ngập phường Hòa Xuân” hoặc “Ngập ở quận Cẩm Lệ cũ”.', 'rows': [], 'floodRecords': [], 'responseKind': 'FLOOD_CLARIFICATION'}
    records = [r for r in CATALOG['records'] if (not filters['type'] or r['record_type'] == filters['type'])
               and (not filters['ward'] or r.get('current_unit') == filters['ward'])
               and (not filters['district'] or (r.get('source_district') or r.get('district')) == filters['district'])
               and (not filters['road'] or contains(r['location_text'], filters['road']) or fold(r.get('street')) == fold(filters['road']))
               and (not filters['recordId'] or r['id'] == filters['recordId'])]
    records.sort(key=lambda r: (r.get('source_district') or r.get('district') or '', r['id']))
    page = records[offset:offset + 10]
    state.update(lastDomain='flood', floodFilters=filters, floodOffset=offset)
    scope = filters['ward'] or ((filters['district'] + ' (quận/huyện cũ)') if filters['district'] else 'Đà Nẵng')
    if filters['road']: scope += ' · ' + filters['road']
    message = f'Tìm thấy {len(records)} bản ghi tại {scope}.'
    if page: message += f' Hiển thị {offset + 1}–{offset + len(page)}.'
    elif offset: message += ' Đã hết kết quả.'
    else: message += ' Không có bản ghi phù hợp; không có nghĩa khu vực không ngập.'
    message += '\nThông tin theo nguồn và ngày ghi nhận, không phản ánh tình trạng ngập hiện tại. Chưa có đường bao vùng ngập để hiển thị chính xác trên bản đồ.'
    if filters['ward']: message += '\nCác bản ghi chưa xác định được phường không được tự gán vào phường này.'
    if offset + len(page) < len(records): message += '\nBạn có thể nói “xem thêm” để xem các vị trí tiếp theo.'
    return {'answer': message, 'rows': [], 'floodRecords': [{**r, 'typeLabel': TYPES[r['record_type']]} for r in page],
            'responseKind': 'FLOOD_CATALOG', 'floodTotal': len(records), 'floodStart': offset + 1,
            'floodFilters': filters, 'floodAllIds':[r['id'] for r in records], 'sourceCommit': CATALOG['commit'], 'hasFloodGeometry': False}


def stats():
    return {'total': len(CATALOG['records']), 'byType': dict(Counter(r['record_type'] for r in CATALOG['records'])),
            'plannedMapped': sum(r['record_type'] == 'PLANNED_RISK' and bool(r.get('current_unit')) for r in CATALOG['records']),
            'plannedUnmapped': sum(r['record_type'] == 'PLANNED_RISK' and not r.get('current_unit') for r in CATALOG['records']),
            'sourceCommit': CATALOG['commit'], 'liveStatus': False, 'hasGeometry': False}
