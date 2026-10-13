"""Apply documented source review to a new apartment dataset, preserving raw data."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from prepare_smartprop_dataset import BASE, CATEGORIES, save_csv

REVIEW = BASE / 'processed/apartment_review'
OUT = BASE / 'processed/apartment_v2'
SOURCE = BASE / 'processed/smartprop_review/baseline_inputs.csv'

# Each exception below was read against the cached detail, not model predictions.
# Prices are advertised full totals under the recorded terms, not transactions.
OVERRIDES = {
 'nhadat24h:4395745': ('correct',2700,None,'Tiêu đề và mô tả cùng ghi 2,7 tỷ cho F1-03A-05, 70m² = 53,8 thông thủy + 16,2 sân vườn. Nhãn 189 triệu mâu thuẫn.', 'Giá tổng quảng cáo khi thanh toán sớm; diện tích gồm sân vườn.'),
 'nhadat24h:4393989': ('correct',9500,70.3,'Mô tả căn 2PN ghi rõ Giá bán 9,5 tỷ (có thương lượng), diện tích 70,3m². 40 triệu/tháng là giá thuê.', 'Có thương lượng; đã loại dòng tiền thuê khỏi tổng giá.'),
 'nhadat24h:4393797': ('correct',4700,None,'Mô tả Monarchy nhắc giá 4,7 tỷ hai lần; tiêu đề ghi 4 7 tỉ. Nhãn 3,5 tỷ mâu thuẫn.', 'Sẵn sổ, giá rao; diện tích 70m² theo nhãn nguồn, chưa kiểm chứng đo đạc.'),
 'nhadat24h:4386429': ('correct',5700,66.7,'Mô tả ghi Giá 5,7 tỷ bao thuế phí, 4,3 tỷ trả trước + 1,4 tỷ còn lại; diện tích thông thủy 66,7m².', 'Tổng giá gồm thuế phí chuyển nhượng; thanh toán theo hai đợt.'),
 'nhadat24h:4380789': ('correct',None,53.8,'Mô tả ghi diện tích 53,8m² và giá 2,3 tỷ. Tiêu đề 53 8m2 bị regex đọc thành 8m²; nhãn diện tích 54 là số làm tròn.', 'Giá quảng cáo trực tiếp CĐT; thông tin chiết khấu lên đến 26% không đủ để suy giá khác.'),
 'nhadat24h:4385198': ('correct',None,45,'Tiêu đề và mô tả cùng giá 7,3 tỷ; mô tả xác định studio 45m² tầng 15, nhãn diện tích 46m².', 'Giữ mức giá cao có bằng chứng, không loại vì vượt ngưỡng đơn giá.'),
 'nhadat24h:4363205': ('correct',7900,72.5,'Phần Thông tin sản phẩm ghi Giá bán 7 tỷ 900 triệu, diện tích 72,5m²; không lấy quà tặng 700/500 triệu làm giá.', 'Giá quảng cáo trước ưu đãi bổ sung; 30% là lịch thanh toán, không phải tổng giá.'),
 'nhadat24h:4386416': ('correct',1747,33.3,'Mã căn SL1-09-16, 33,3m²; tiêu đề 1,747 tỷ khớp tổng giá sau chiết khấu của phương án thanh toán nhanh 95%.', 'Tổng giá rao theo phương án thanh toán nhanh 95%, không phải số tiền riêng đợt 95%; phương án khác có giá khác.'),
 'nhadat24h:4370965': ('correct',4167,None,'Mã F5-03-12, tổng diện tích sổ 116m² = 91,6 căn hộ + 24,4 sân vườn. Tiêu đề 4,167 tỷ khớp phương án thanh toán nhanh 95%.', 'Tổng giá rao theo thanh toán nhanh 95%; diện tích gồm sân vườn; phương án khác có giá khác.'),
 'nhadat24h:4395293': ('correct',2330,None,'Nhỉnh 2 tỷ là cách nói gần đúng; mô tả căn F5-12-21 ghi Giá TTN 2,330 tỷ và diện tích 48m².', 'Tổng giá quảng cáo khi thanh toán nhanh (TTN).'),
 'nhadat24h:4395406': ('correct',2521,None,'Mô tả xác định studio 30m² tầng 20, Giá TTS 2,521 tỷ. Những căn hộ là lời giới thiệu, không phải danh sách nhiều căn cụ thể.', 'Tổng giá quảng cáo theo TTS; cần giữ điều kiện thanh toán trong diễn giải mô hình.'),
 'nhadat24h:4370936': ('keep',None,None,'2tỷ4 nghĩa là 2,4 tỷ, khớp nhãn. 70m² là tổng diện tích sử dụng gồm phần căn hộ 52m²; không phải 52 và 70 là hai căn.', 'Diện tích gồm sân vườn; giá tổng 2,4 tỷ theo tiêu đề/mô tả.'),
 'nhadat24h:4388404': ('keep',None,None,'Tiêu đề và mô tả cùng giá bán công khai 7,4 tỷ. 30 triệu/tháng là thu nhập thuê. Không có bằng chứng giá cao là sai.', 'Giữ giá rao cao; diện tích 46m² theo nhãn nguồn.'),
 'nhadat24h:4379583': ('keep',None,None,'Mô tả xác nhận chính chủ gửi bán căn góc 2PN, 75m²; tiền thuê 50 triệu/tháng không phải giá bán. Nhãn chi tiết 15 tỷ khớp snapshot, không có tổng giá đối lập.', 'Giá bán theo nhãn nguồn; chưa có xác nhận độc lập của chủ nhà. Không loại chỉ vì đơn giá cao.'),
 'nhadat24h:4395115': ('keep',None,None,'Mô tả xác định căn góc 3PN 145m², khớp diện tích; nhãn 27 tỷ khớp snapshot. Không có giá khác hoặc dấu hiệu trả trước.', 'Giữ giá rao theo nhãn nguồn dù đơn giá cao; chưa xác minh giao dịch.'),
 'nhadat24h:4394028': ('keep',None,None,'Tin xác định studio tầng cao trục 04; nhãn 8,4 tỷ/45m² ổn định. 40–50 triệu/tháng là lợi nhuận thuê, không phải tổng giá.', 'Giữ giá rao theo nhãn; phần giới thiệu dự án không được dùng để suy thêm giá.'),
 'nhadat24h:4397339': ('keep',None,None,'80tr m2 trong tiêu đề là giá theo m², không phải tổng giá 80 triệu. Giữ nhãn 5 tỷ/67m²; đơn giá nhãn khoảng 74,63 triệu/m², tiêu đề là tham chiếu quảng cáo.', 'Nhãn tổng giá nguồn, tiêu đề đơn giá quảng cáo không dùng để nhân lại giá; chưa có báo giá độc lập.'),
 'nhadat24h:4361386': ('exclude',None,None,'Cả tiêu đề và mô tả đều cho thuê căn hộ/phòng sinh hoạt chung; ngoài tập căn hộ bán.', ''),
 'nhadat24h:4364758': ('exclude',None,None,'Mô tả bán cả công trình gồm văn phòng và tổng 9 căn cho thuê; không phải một căn hộ chung cư 425m².', ''),
 'nhadat24h:4397834': ('exclude',None,None,'Nội dung nhận booking cả tòa F2, 50 triệu/booking; chưa chỉ ra một căn có tổng giá bán và diện tích riêng.', ''),
 'nhadat24h:4368726': ('exclude',None,None,'Giỏ hàng hơn 20 căn, nhiều loại/diện tích và giá 8,x–15,x tỷ; không xác định một căn tương ứng nhãn 184 triệu/45m².', ''),
 'nhadat24h:4396528': ('exclude',None,None,'Quảng cáo giỏ hàng studio/1PN/2PN 47–82m², giá từ 2,x tỷ; hợp đồng thuê theo thời hạn dự án, chưa xác định một căn.', ''),
 'nhadat24h:4395086': ('exclude',None,None,'Tiêu đề và mô tả độc quyền 2 căn, không phân biệt từng căn/giá; không đủ một quan sát căn hộ riêng.', ''),
 'cafeland:2146428': ('exclude',None,None,'Tiêu đề thanh toán 30%; mô tả 1tỷ6 (30%), diện tích mô tả 82,5m² khác nhãn 100m²; nhãn 1,6 tỷ là khoản thanh toán, không phải tổng giá.', ''),
 'nhadat24h:4368616': ('pending',None,None,'Mô tả có căn sân vườn và nhiều căn khác với giá khác nhau; mã F1-03A-05 còn xuất hiện trong các tin khác. Chưa chốt quan sát/căn và diện tích thống nhất.', ''),
 'nhadat24h:4369560': ('pending',None,None,'F103A05 có giá khoảng 2,6 tỷ trong nội dung nhưng nhãn 6,3 tỷ; nhiều căn khác và mã căn trùng tin khác. Chưa đủ căn cứ chọn giá chính xác.', ''),
 'nhadat24h:4398421': ('pending',None,None,'Tiêu đề từ 2,991 tỷ, nhãn 2,990 tỷ nhưng phương án 95% mô tả 2,911 tỷ; nhiều phương án giá. Không tự chọn một số.', ''),
 'nhadat24h:4361442': ('pending',None,None,'Nhãn/tiêu đề diện tích 48m² nhưng mô tả 51m²; chưa biết diện tích nào cùng căn và cùng định nghĩa.', ''),
 'nhadat24h:4363275': ('pending',None,None,'Nhãn 8 tỷ/45m², mô tả giá 7,x tỷ/47m². Giá không chính xác và diện tích mâu thuẫn; chưa sửa.', ''),
 'nhadat24h:4381530': ('pending',None,None,'Nhãn 45m² nhưng mô tả 45,49m² và mời nhận giá từng căn; chưa xác định chắc một căn và tổng giá riêng.', ''),
 'nhadat24h:4362743': ('pending',None,None,'Mô tả M Landmark là tổ hợp lưu trú/nghỉ dưỡng, chưa phân biệt căn hộ ở và sản phẩm dịch vụ cụ thể; cần xác minh phân khúc và quyền sử dụng.', ''),
 'nhadat24h:4374076': ('pending',None,None,'Mô tả nêu căn hộ lưu trú, nghỉ dưỡng và condotel trong tổ hợp M Landmark; chưa xác minh loại căn/quyền sử dụng của tin.', ''),
}

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))

def decide(row):
    key = row['record_key']
    if key in OVERRIDES:
        decision, p, a, note, terms = OVERRIDES[key]
    else:
        decision, p, a, terms = 'pending', None, None, ''
        note = 'Chưa đủ bằng chứng xác định một tổng giá và diện tích nhất quán. Giữ ngoài tập v2; không suy giá từ khoảng giá, tiền trả trước, mô hình hoặc căn khác. Cờ: '+row['review_codes']
    return dict(record_key=key, decision=decision, price_million=p, area_sqm=a,
        note=note, terms=terms, reviewer='assistant_source_review',reviewed_on='2026-10-11')

def apply(row, decision):
    result = dict(row)
    result.update(original_price_million=row['price_million'],original_area_sqm=row['area_sqm'],
        label_quality='screened_unverified',review_decision='not_flagged',review_terms='',review_note='Chưa lấy lại chi tiết trong đợt rà soát ưu tiên.')
    if decision:
        if decision['decision'] not in ['keep','correct']:
            return None
        for key in ['price_million','area_sqm']:
            value=decision[key]
            if value is not None:
                if not math.isfinite(value) or value<=0:
                    raise ValueError('Invalid corrected numeric label')
                result[key]=str(float(value))
        result.update(label_quality='source_reviewed_'+decision['decision'],
            review_decision=decision['decision'],review_terms=decision['terms'],review_note=decision['note'])
    result['price_per_sqm_million']=str(float(result['price_million'])/float(result['area_sqm']))
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    queue=REVIEW/'needs_review.csv'
    before=queue.read_bytes()
    baseline=SOURCE.read_bytes()
    if (OUT/'summary.json').exists():
        report=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
        if before!=(OUT/'reviewed_queue.csv').read_bytes():
            raise ValueError('Reviewer queue changed after v2; reconcile in a new version, without overwriting v2.')
        assert hashlib.sha256(baseline).hexdigest()==report['source_input_sha256']
        assert hashlib.sha256((OUT/'baseline_inputs.csv').read_bytes()).hexdigest()==report['dataset_sha256']
        print('Apartment v2 already finalized; verified frozen dataset and reviewer queue. No files changed.')
        return
    rows=[r for r in read(SOURCE) if r['category']==CATEGORIES[2]]
    pending=read(queue)
    if any(r['reviewer_decision'] or r['reviewer_note'] or r['proposed_price_million'] or r['proposed_area_sqm'] for r in pending):
        raise ValueError('Existing reviewer edits detected; preserve and reconcile them before rerunning.')
    assert len(rows)==296 and len(pending)==64
    assert set(OVERRIDES)<={r['record_key'] for r in pending}
    manifest=json.loads((REVIEW/'fetch_manifest.json').read_text(encoding='utf-8'))
    protected=json.loads((REVIEW/'summary.json').read_text(encoding='utf-8'))['protected_input_sha256']
    assert all(hashlib.sha256((BASE/path).read_bytes()).hexdigest()==sha for path,sha in protected.items())
    decisions={r['record_key']:decide(r) for r in pending}
    for row in pending:
        d=decisions[row['record_key']]
        meta=manifest[row['record_key']]
        body=(REVIEW/'detail_cache'/meta['file']).read_bytes()
        assert hashlib.sha256(body).hexdigest()==meta['sha256']
        assert row['detail_check_state']=='identity_verified'
        d.update(source_url=row['detail_url'],detail_sha256=meta['sha256'],detail_fetched_at=meta['fetched_at_utc'])
        row.update(reviewer_decision=d['decision'],reviewer_note=d['note']+(' Điều kiện: '+d['terms'] if d['terms'] else ''),
            proposed_price_million=d['price_million'] if d['price_million'] is not None else '',
            proposed_area_sqm=d['area_sqm'] if d['area_sqm'] is not None else '')
    included,excluded=[],[]
    for row in rows:
        d=decisions.get(row['record_key'])
        result=apply(row,d)
        if result: included.append(result)
        else: excluded.append(dict(row,review_decision=d['decision'],review_note=d['note']))
    ids={r['record_key'] for r in included}
    assert len(ids)==len(included) and not ids & {r['record_key'] for r in excluded}
    assert len(included)+len(excluded)==len(rows)
    assert len({r['duplicate_candidate_group'] for r in included})==len(included)
    assert all(r['model_split']==next(x['model_split'] for x in rows if x['record_key']==r['record_key']) for r in included)
    (OUT/'review_queue_before.csv').write_bytes(before)
    save_csv(OUT/'review_decisions.csv',list(decisions.values()),list(next(iter(decisions.values()))))
    save_csv(OUT/'reviewed_queue.csv',pending,list(pending[0]))
    save_csv(OUT/'baseline_inputs.csv',included,list(included[0]))
    save_csv(OUT/'quarantined.csv',excluded,list(excluded[0]))
    report=dict(version='apartment_v2',review_date='2026-10-11',total_original=len(rows),reviewed_flagged=len(pending),
        decisions=dict(Counter(d['decision'] for d in decisions.values())),included=len(included),quarantined=len(excluded),
        split_counts=dict(Counter(r['model_split'] for r in included)),
        quality_counts=dict(Counter(r['label_quality'] for r in included)),
        source_input_sha256=hashlib.sha256(baseline).hexdigest(),review_queue_before_sha256=hashlib.sha256(before).hexdigest(),
        dataset_sha256=hashlib.sha256((OUT/'baseline_inputs.csv').read_bytes()).hexdigest(),
        model_errors_used=False, fresh_test=False,
        limitations=['232 unflagged records are screened, not detail-verified.',
          'Source-reviewed means consistency of advertised labels, not verified sale transactions.',
          'Advertised full totals under fast/early payment plans may differ; terms retained, no automatic discount arithmetic.',
          'Garden-inclusive and interior floor areas coexist; retained with explicit notes.',
          'Filtered/corrected holdout is exploratory; it is not directly comparable to original aggregate metrics.'])
    assert SOURCE.read_bytes()==baseline and queue.read_bytes()==before
    assert all(hashlib.sha256((BASE/path).read_bytes()).hexdigest()==sha for path,sha in protected.items())
    # Keep the IDE review queue useful, with an exact backup already saved.
    temporary=queue.with_suffix('.reviewed.tmp')
    temporary.write_bytes((OUT/'reviewed_queue.csv').read_bytes())
    import time
    for attempt in range(10):
        try:
            temporary.replace(queue)
            break
        except PermissionError:
            if attempt==9: raise
            time.sleep(min(.2*(attempt+1),1))
    (OUT/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))

if __name__=='__main__':
    main()
