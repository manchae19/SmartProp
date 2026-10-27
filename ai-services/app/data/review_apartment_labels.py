"""Evidence-based audit of frozen apartment inputs, independent of model errors."""
import csv
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from html import escape
from urllib.parse import urlparse
from lxml import html
from prepare_smartprop_dataset import BASE, CATEGORIES, number, price, save_csv
from smartprop_geography import norm

OUT = BASE / 'processed/apartment_review'
SOURCE = BASE / 'processed/smartprop_review/baseline_inputs.csv'
MONEY = re.compile(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(ty|ti|trieu|tr)(?![a-z])(?:\s*(\d+)\s*trieu)?')
AREA = re.compile(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*m[2²](?!\d)')
LABELS = {
    'low_total_price': 'Tổng giá dưới 500 triệu: kiểm tra tổng giá/giá trả trước/giá theo m²',
    'unit_price_band': 'Đơn giá ngoài 15–150 triệu/m²: ngưỡng ưu tiên duyệt, không kết luận sai',
    'area_band': 'Diện tích ngoài 25–200m²: cần xác minh căn hộ và định nghĩa diện tích',
    'possible_partial_price': 'Có dấu hiệu thanh toán/trả trước/giá khởi điểm',
    'rental_title': 'Tiêu đề bắt đầu cho thuê trong tập tin bán',
    'nonstandard_property': 'Có dấu hiệu condotel/căn hộ dịch vụ/khách sạn',
    'title_price_conflict': 'Giá tổng trong tiêu đề lệch giá nhãn trên 10%',
    'title_area_conflict': 'Diện tích trong tiêu đề lệch nhãn trên 5%',
    'raw_parse_mismatch': 'Giá/diện tích thô không khớp giá/diện tích chuẩn hóa',
    'detail_unavailable': 'Trang chi tiết không còn truy cập được',
    'detail_identity_unverified': 'Không xác minh được đúng trang chi tiết/tiêu đề',
    'detail_structure_unverified': 'Thiếu vùng nội dung hoặc nhãn giá/diện tích dự kiến',
    'current_detail_changed': 'Nhãn giá/diện tích hiện tại khác snapshot đã cào',
    'description_price_conflict': 'Giá tổng nêu trong mô tả không khớp nhãn giá',
    'description_unit_price': 'Mô tả có giá theo m²: cần xác định nhãn tổng giá',
    'multiple_properties': 'Mô tả có dấu hiệu nhiều căn/giỏ hàng',
    'expired_listing': 'Nguồn ghi tin hết hạn',
}

def text(node):
    return ' '.join(' '.join(node.itertext()).split())

def money_mentions(value):
    """Context matters: rent, discount, installment and unit prices are not total prices."""
    value = norm(value).replace('t.y', 'ty')
    result = []
    for match in MONEY.finditer(value):
        before, after = value[max(0, match.start()-55):match.start()], value[match.end():match.end()+25]
        amount = float(match[1].replace(',', '.'))*(1000 if match[2] in ['ty','ti'] else 1)
        if match[3]:
            amount += float(match[3])
        kind = 'total_candidate'
        if re.match(r'\s*(?:/\s*m[2²]|mot m[2²])', after):
            kind = 'unit_price'
        elif re.match(r'\s*(?:/\s*(?:th|thang|nam)|th\b|thang\b)', after) or re.search(r'(dong tien|thu nhap|cho thue|tien thue).{0,20}$', before):
            kind = 'rental_income'
        elif re.search(r'(giam|thap hon|re hon|chiet khau|lo|loi|tiet kiem).{0,20}$', before):
            kind = 'discount_or_profit'
        elif re.search(r'(tra truoc|thanh toan|chi tu|gia tu).{0,20}$', before):
            kind = 'partial_or_starting'
        elif re.search(r'(chua toi|duoi|hon|tu).{0,8}$', before):
            kind = 'bound'
        result.append(dict(amount_million=amount, kind=kind,
            context=value[max(0,match.start()-55):match.end()+35]))
    return result

def by_class(root, cls):
    return root.xpath('//*[contains(concat(" ", normalize-space(@class), " "), $v)]', v=' '+cls+' ')

def detail(row, meta):
    if meta['http_status'] != 200:
        return dict(state='unavailable'), ['detail_unavailable']
    path = OUT / 'detail_cache' / meta['file']
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == meta['sha256']
    root = html.fromstring(body)
    source = row['source']
    headings = root.xpath('//*[@id="txtcontenttieudetin"]') if source=='nhadat24h' else by_class(root,'head-title')
    heading = text(headings[0]) if headings else ''
    url = meta['response_url']
    ident = (re.search(r'-ID(\d+)$',urlparse(url).path) if source=='nhadat24h'
             else re.search(r'-(\d+)\.html$',urlparse(url).path))
    if urlparse(url).hostname != urlparse(row['detail_url']).hostname or not ident or ident[1] != row['source_listing_id'] or not heading or SequenceMatcher(None,norm(heading),norm(row['title'])).ratio()<.8:
        return dict(state='identity_unverified', title=heading), ['detail_identity_unverified']
    if source=='nhadat24h':
        boxes = root.xpath('//*[contains(@id,"lbGiaDienTich")]')
        label = norm(text(boxes[0])) if boxes else ''
        match = re.search(r'(?:can ban|can thue)\s*:\s*(.+?)\s*-\s*(\d+(?:[.,]\d+)?\s*m[2²])',label)
        pr, ar = (match[1], match[2]) if match else ('','')
        descriptions = by_class(root,'sub1detailmaincontent')
        if descriptions:
            # Source description ends before contact/author/keywords/widgets.
            descriptions = descriptions[0].xpath('./div') or descriptions
        description = text(descriptions[0]) if descriptions else ''
        description = re.split(r'\bChat\b|Thông tin người đăng|Xem thêm từ khóa',description)[0]
    else:
        data = {}
        for box in by_class(root,'col-item'):
            labels = box.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," infor-note ")]')
            values = box.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," infor-data ")]')
            if labels and values:
                data[norm(text(labels[0]))] = text(values[0])
        pr, ar = data.get('gia ban',''), data.get('dien tich','')
        descriptions = by_class(root,'reals-description')
        description = text(descriptions[0]) if descriptions else ''
    area_match = AREA.fullmatch(norm(ar))
    result = dict(state='identity_verified', title=heading, price_raw=pr, area_raw=ar,
        price_million=price(pr), area_sqm=float(area_match[1].replace(',','.')) if area_match else None,
        description=description, fetched_at_utc=meta['fetched_at_utc'])
    flags = []
    if not description or result['price_million'] is None or result['area_sqm'] is None:
        flags.append('detail_structure_unverified')
    if source=='cafeland' and 'tin het han' in norm(text(root)):
        flags.append('expired_listing')
    return result, flags

def audit(row, current=None, detail_flags=()):
    raw = json.loads(row['raw_json'])
    pr, ar = float(row['price_million']), float(row['area_sqm'])
    title = norm(row['title'])
    flags = list(detail_flags)
    if pr < 500: flags.append('low_total_price')
    if not 15 <= pr/ar <= 150: flags.append('unit_price_band')
    if not 25 <= ar <= 200: flags.append('area_band')
    if re.search(r'\b(tra truoc|thanh toan|chi tu|gia tu)\b',title): flags.append('possible_partial_price')
    if re.match(r'^(?:can\s+)?cho thue\b',title): flags.append('rental_title')
    if re.search(r'\b(condotel|can ho dich vu|khach san)\b',title): flags.append('nonstandard_property')
    am = AREA.fullmatch(norm(raw.get('area_raw','')))
    if price(raw.get('price_raw','')) != pr or not am or abs(float(am[1].replace(',','.'))-ar)>.01:
        flags.append('raw_parse_mismatch')
    mentions = money_mentions(row['title'])
    totals = [m['amount_million'] for m in mentions if m['kind']=='total_candidate']
    if totals and all(abs(p-pr)/max(p,pr)>.1 for p in totals): flags.append('title_price_conflict')
    title_areas = [float(m[1].replace(',','.')) for m in AREA.finditer(title)]
    if title_areas and all(abs(a-ar)/max(a,ar)>.05 for a in title_areas): flags.append('title_area_conflict')
    description_mentions = []
    if current and current.get('state')=='identity_verified':
        cp, ca = current['price_million'], current['area_sqm']
        if (cp is not None and abs(cp-pr)>.01) or (ca is not None and abs(ca-ar)>.01):
            flags.append('current_detail_changed')
        description_mentions = money_mentions(current['description'])
        dtotals = [m['amount_million'] for m in description_mentions if m['kind']=='total_candidate']
        if dtotals and all(abs(p-pr)/max(p,pr)>.1 for p in dtotals): flags.append('description_price_conflict')
        if any(m['kind']=='unit_price' for m in description_mentions): flags.append('description_unit_price')
        dnorm = norm(current['description'])
        if re.search(r'\b(tra truoc|thanh toan|chi tu|gia tu)\b',dnorm): flags.append('possible_partial_price')
        if re.search(r'\b(gio hang|cac can|nhieu can)\b',dnorm): flags.append('multiple_properties')
    flags = sorted(set(flags))
    return dict(record_key=row['record_key'], source=row['source'], source_listing_id=row['source_listing_id'],
        title=row['title'], detail_url=row['detail_url'], district=row['district'],
        original_split=row['model_split'], duplicate_candidate_group=row['duplicate_candidate_group'],
        price_million=pr, area_sqm=ar, unit_price_million_sqm=pr/ar,
        price_raw=raw.get('price_raw',''), area_raw=raw.get('area_raw',''),
        displayed_date=row['displayed_date'], date_basis=row['date_basis'],
        audit_status='needs_review' if flags else 'no_rule_flag_unverified',
        review_codes=';'.join(flags), review_reasons='; '.join(LABELS[f] for f in flags),
        title_money_evidence=json.dumps(mentions,ensure_ascii=False),
        title_area_evidence=json.dumps(title_areas),
        detail_check_state=(current or {}).get('state','not_fetched'),
        current_detail_price_million=(current or {}).get('price_million'),
        current_detail_area_sqm=(current or {}).get('area_sqm'),
        description_money_evidence=json.dumps(description_mentions,ensure_ascii=False),
        description=(current or {}).get('description',''),
        proposed_price_million='', proposed_area_sqm='', reviewer_decision='', reviewer_note='')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with SOURCE.open(encoding='utf-8-sig',newline='') as stream:
        allrows = list(csv.DictReader(stream))
    rows = [r for r in allrows if r['category']==CATEGORIES[2]]
    assert len(rows)==len({r['record_key'] for r in rows})
    inputs = {SOURCE:before}
    for row in rows:
        path = BASE / row['input_file']
        if path not in inputs: inputs[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = OUT/'fetch_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    results = []
    for row in rows:
        current, flags = detail(row,manifest[row['record_key']]) if row['record_key'] in manifest else (None,[])
        results.append(audit(row,current,flags))
    # Review order uses source evidence only, never test errors or model predictions.
    results.sort(key=lambda r:(r['audit_status']!='needs_review', -len(r['review_codes'].split(';')), r['record_key']))
    pending = [r for r in results if r['audit_status']=='needs_review']
    unflagged = [r for r in results if r['audit_status']!='needs_review']
    for name,rs in [('all_apartments_audit.csv',results),('needs_review.csv',pending),('unflagged_candidates.csv',unflagged)]:
        save_csv(OUT/name,rs,list(results[0]))
    summary = dict(total=len(rows), needs_review=len(pending), no_rule_flag_unverified=len(unflagged),
        by_source=dict(Counter(r['source'] for r in results)),
        detail_states=dict(Counter(r['detail_check_state'] for r in results)),
        review_rule_counts=dict(Counter(c for r in pending for c in r['review_codes'].split(';'))),
        protected_input_sha256={str(p.relative_to(BASE)):h for p,h in inputs.items()},
        rules=LABELS, thresholds=dict(total_price_min_million=500,unit_price_band_million_sqm=[15,150],area_band_sqm=[25,200]),
        labels_changed=0, model_errors_used=False,
        limitation='No-rule-flag is not verified clean. Detail snapshots may differ from original collection. Existing experimental test is not a fresh final benchmark.')
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in inputs.items())
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    cards=[]
    for row in results:
        url=row['detail_url']
        safe=urlparse(url).scheme=='https' and urlparse(url).hostname in ['nhadat24h.net','nhadat.cafeland.vn']
        link=f'<a href="{escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">Mở tin gốc</a>' if safe else 'URL không hợp lệ'
        cards.append(f'<article><h3>{escape(row["record_key"])} — {escape(row["title"])}</h3><p>{row["price_million"]:,.1f} triệu · {row["area_sqm"]}m² · {row["unit_price_million_sqm"]:,.2f} triệu/m² · {escape(row["audit_status"])}</p><p>{escape(row["review_reasons"])}</p>{link}<details><summary>Bằng chứng mô tả / tiêu đề</summary><p>{escape(row["title_money_evidence"])}</p><p>{escape(row["description"])}</p></details></article>')
    document='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Rà soát nhãn căn hộ SmartProp</title><style>body{font:16px system-ui;max-width:1080px;margin:32px auto;padding:0 20px;background:#f5f7fa;color:#182838}article{background:white;padding:20px;margin:16px 0;border:1px solid #ccd5df;border-radius:8px}p{line-height:1.6;overflow-wrap:anywhere}input{padding:12px;width:90%}h3{line-height:1.5}</style><h1>Rà soát 296 tin căn hộ</h1><p>Giữ nguyên nhãn gốc. Tin không có cờ vẫn chưa được xác minh sạch. Ghi quyết định ở bản sao CSV needs_review.csv; không sửa dữ liệu raw. Không chọn tin theo sai số mô hình.</p><input id="search" placeholder="Tìm ID, tiêu đề hoặc lý do"><main>'+''.join(cards)+'</main><script>document.getElementById("search").addEventListener("input",function(){const q=this.value.toLocaleLowerCase();for(const e of document.querySelectorAll("article"))e.hidden=!e.textContent.toLocaleLowerCase().includes(q)})</script></html>'
    (OUT/'review.html').write_text(document,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=True,indent=2))

if __name__=='__main__':
    main()
