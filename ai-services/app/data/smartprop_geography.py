"""Historical Da Nang scope; retain ambiguity when new units cross old districts."""
import re
import unicodedata

REFERENCE = 'https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1659-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-da-nang-nam-2025-119250616202714604.htm'
DISTRICTS = ['Hải Châu', 'Thanh Khê', 'Sơn Trà', 'Ngũ Hành Sơn', 'Liên Chiểu', 'Cẩm Lệ', 'Hòa Vang']


def norm(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', str(s or '').lower())
                    if unicodedata.category(c) != 'Mn').replace('đ', 'd').split())


# Only new units wholly within one historical district get a unique assignment.
UNIQUE_NEW = {'an hai': 'Sơn Trà', 'hoa cuong': 'Hải Châu',
              'hoa tien': 'Hòa Vang', 'ba na': 'Hòa Vang'}
MIXED_NEW = {'an khe': ['Thanh Khê', 'Cẩm Lệ'],
             'hoa khanh': ['Liên Chiểu', 'Hòa Vang'],
             'hai van': ['Liên Chiểu', 'Hòa Vang'],
             'hoa xuan': ['Cẩm Lệ', 'Hòa Vang'],
             'lien chieu': ['Liên Chiểu', 'Hòa Vang']}


def resolve(address, district='', source=''):
    text = norm(address)
    if not re.search(r'\bda nang\b', text):
        return '', 'outside_or_unknown', ''
    # An explicit historical district label is stronger than an unqualified name.
    for d in DISTRICTS:
        prefix = 'huyen' if d == 'Hòa Vang' else 'quan'
        if re.search(r'\b' + prefix + ' ' + norm(d) + r'\b', text):
            return d, 'explicit_historical_district', d
    if source != 'cafeland':
        d = re.sub(r'^(quan|huyen)\s+', '', norm(district)).strip(' -')
        for candidate in DISTRICTS:
            if norm(candidate) == d:
                return candidate, 'source_historical_district', candidate
    parts = [re.sub(r'^(phuong|xa)\s+', '', norm(x)).strip(' -') for x in address.split(',')]
    place = parts[0] if parts else ''
    if place in MIXED_NEW:
        return '', 'crosses_historical_districts', '|'.join(MIXED_NEW[place])
    if place in UNIQUE_NEW:
        return UNIQUE_NEW[place], 'new_unit_mapped_to_historical_district', UNIQUE_NEW[place]
    for d in DISTRICTS:
        if place == norm(d):
            return d, 'source_area_within_historical_district', d
    return '', 'outside_or_unknown', ''
