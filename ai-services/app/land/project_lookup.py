"""Source-reported project facts, separate from parcel-level verification."""
import json
import re
from pathlib import Path
from .budget_rules import fold

from .paths import DATA_ROOT
DATA = DATA_ROOT / 'outputs/hoa-xuan-projects-20261125'
PROJECTS = json.loads((DATA / 'projects.json').read_text(encoding='utf-8'))
LOTS = json.loads((DATA / 'unified-lots.json').read_text(encoding='utf-8'))

def lookup(question, state, has_filters=False):
    n = fold(question)
    project = next((p for p in PROJECTS if any(re.search(r'(?<!\w)' + re.escape(fold(a)) + r'(?!\w)', n) for a in p['aliases'])), None)
    block_query = re.search(r'\bb2[.\- ]?(\d+)\b', n)
    if project is None and block_query:
        project = PROJECTS[0]
    if project is None:
        return None
    selected_lots = LOTS
    if block_query:
        selected_lots = [x for x in LOTS if x['block'] == 'B2.' + block_query[1]]
        number = re.search(r'\blo\s+(\d+)(?!\d)(?!\s*(?:ty|ti|trieu))', n)
        if number:
            selected_lots = [x for x in selected_lots if int(number[1]) in x['lotNumbers']]
    lines = [project['name'] + ' — ' + ', '.join(project['aliases'][1:]),
             'Khu vực: ' + project['parentArea'] + ', ' + project['phase'] + '; ' + project['location'] + '.',
             'Chủ đầu tư: ' + project['developerSourceReported'] + ' (theo nguồn giới thiệu dự án).',
             'Sổ hồng: ' + project['pinkBookDescription'],
             'Giấy tờ chính chủ, tranh chấp, thế chấp và thu hồi của từng lô: chưa xác minh.']
    block = re.search(r'\bb2[.\- ]?11\b', n)
    if block:
        lines += ['Block B2.11 có hồ sơ nguồn:', '• Lô 7: 312,7 m².',
                  '• Lô 14 và 15: tổng 658,7 m²; chưa có diện tích riêng từng lô.',
                  'Tin nguồn năm 2021 ghi đã hết hàng; chưa nối được đường bao từng lô.']
        lines.extend(x['sourceUrl'] for x in LOTS)
    else:
        lines += ['Đã tìm thấy nguồn sơ đồ phân lô; chưa khớp block/số lô với đường bao trên bản đồ.']
    if has_filters:
        lines += ['Chưa thể trả danh sách đúng giá/diện tích trong riêng dự án này vì chưa hoàn tất nối từng lô; hãy bỏ tên dự án nếu muốn tìm toàn Hòa Xuân.']
    lines += ['Nguồn thông tin dự án:'] + project['sources']
    # Do not retain an unrelated map selection or fabricate project membership.
    state.update(selected=None, seen=[], offset=0)
    return {'answer': '\n'.join(lines), 'rows': [], 'project': project,
            'sourceLots': selected_lots, 'clearPlotSelection': True}
