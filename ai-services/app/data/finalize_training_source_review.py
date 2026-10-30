"""Document source review of 87 listings and build v2, preserving raw/v1/test."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from audit_all_collected import BASE, read, save_csv, number

REVIEW=BASE/'processed/training_source_review'
V1=BASE/'processed/training_v1'
OUT=BASE/'processed/training_v2'

# Read against identity-checked cached descriptions. Never derived from residuals.
# A current description is evidence about the advertised asset, not a transaction.
KEEP={
 'cafeland:2459324':'Một lô Nguyễn Như Đỗ, 100m², mô tả ghi giá tổng 3,35 tỷ, khớp nhãn.',
 'cafeland:2479247':'Một nhà gác lửng Nguyễn Nhàn, 117m², 3PN; giá bán cụ thể 4,3 tỷ. Những số 4/5 tỷ khác là so sánh quảng cáo.',
 'cafeland:2481678':'Một nhà 2 tầng Hòa Quý, 90m², 3PN; mô tả ghi tổng giá 3,5 tỷ.',
 'cafeland:2555401':'Một lô Nguyễn Như Đỗ, 80m²; mô tả ghi tổng giá 2,25 tỷ.',
 'cafeland:2555532':'Một lô Hoàng Hiệp, 100m²; mô tả ghi tổng giá 6,4 tỷ.',
 'cafeland:2557328':'Một lô 228m² làm nhà vườn, mô tả ghi tổng giá 2,5 tỷ. Không phải nhà xây sẵn theo nội dung.',
 'cafeland:2959030':'Một lô 100m² Cầu Đỏ Túy Loan, giá trong mô tả 3,09 tỷ khớp nhãn; tiêu đề 3 tỷ là gần đúng.',
 'cafeland:3144975':'Một nhà mê lửng Nguyễn Thị Ba, 75m²; phần thông tin cuối mô tả ghi tổng 6,6 tỷ, khớp nhãn.',
 'cafeland:3147456':'Một nhà 3 tầng Trần Quang Khải, 79m², 4PN; giá nguồn 7,3 tỷ khớp snapshot.',
 'cafeland:3168538':'Nhà 2 tầng Đa Mặn 11, giá bán 7,95 tỷ. Giữ diện tích đất 77m², không cộng phần sử dụng thêm ngoài sổ; thu nhập thuê 15 triệu/tháng không phải giá bán.',
 'cafeland:3187442':'Căn 1109 tầng 11 Hiyori Aqua Tower, 65m², 2PN; nhãn giá tổng 4,7 tỷ ổn định và không có tổng giá đối lập. Thanh toán theo tiến độ.',
 'cafeland:3184784':'Một lô Văn Tiến Dũng, 250m² (10x25), mô tả ghi tổng giá 6,9 tỷ. Cụm sở hữu không phải bằng chứng loại tài sản đặc biệt.',
 'nhadat24h:4375898':'Một nhà K130 Điện Biên Phủ, 71m², 3PN. Giữ giá nhãn nguồn 4,55 tỷ; mô tả chỉ nêu khoảng 4,x tỷ, không dùng khoảng giá để sửa.',
 'nhadat24h:4376801':'Nội dung nêu duy nhất một lô Nam Sơn, 120m². Giữ giá nhãn 1 tỷ vì mô tả không nêu tổng giá khác; cờ một lô là dương tính giả.',
 'nhadat24h:4381109':'Một nhà góc Điện Biên Phủ, 48m², 2 tầng. Giữ nhãn 4,85 tỷ; tiêu đề/mô tả nêu gần đúng 4,8x tỷ.',
 'nhadat24h:4382420':'Một nhà mê lửng kiệt Đống Đa, 68m², 2PN. Giữ nhãn 4,85 tỷ; nội dung nêu 4,8x tỷ.',
 'nhadat24h:4385371':'Một nhà mê lửng kiệt Đống Đa, 68m², 2PN. Giữ nhãn 4,85 tỷ; mô tả tương tự tin 4382420, đánh dấu nghi trùng bổ sung.',
 'nhadat24h:4391547':'Một nhà 3 tầng Thanh Long, 3PN. Giữ giá/diện tích từ nhãn nguồn 5,1 tỷ/50m², chưa xác nhận được diện tích trong mô tả; không có nhãn tổng giá đối lập.',
 'nhadat24h:4394081':'Một căn Masteri Rivera trục 09 tầng 17, thông thủy 67m², mô tả ghi giá tổng 5,7 tỷ bao thuế phí. Thu nhập thuê kỳ vọng không phải giá bán.',
 'nhadat24h:4377849':'Một nhà lửng Đống Đa, 51m² đất trên sổ và thêm 14m² ngoài sổ. Giữ 51m²; giá nhãn 3,45 tỷ phù hợp khoảng 3,x tỷ, không cộng đất ngoài sổ.',
 'nhadat24h:4379680':'Một nhà 2 tầng kiệt Trần Cao Vân, 60m², 3PN. Giữ giá nguồn 4,75 tỷ; nội dung 4,xx tỷ là gần đúng.',
}
CORRECT={
 'nhadat24h:4347477':(None,151.4,'Mô tả một nhà 2 tầng Lê Quang Sung ghi đất 151,4m²; 151m² là nhãn làm tròn. Khả năng tách hai lô là tiềm năng, chưa phải đang bán hai lô riêng.'),
 'nhadat24h:4360788':(3900,None,'Tiêu đề đã lưu và mô tả cùng nêu tổng giá 3,9 tỷ cho căn sân vườn 120m²; nhãn 4 tỷ lệch. Diện tích quảng cáo gồm sân vườn, chưa có diện tích thông thủy riêng.'),
 'nhadat24h:4382452':(None,33.3,'Mô tả xác định mã SL1-15.06, diện tích 33,3m² và tổng giá dự kiến 2,6 tỷ gồm VAT/KPBT; nhãn diện tích 35m² lệch.'),
 'nhadat24h:4382885':(None,121,'Một lô DH8, mô tả ghi 121m² và tổng giá 1,690 tỷ. Nhãn 120m² là làm tròn; không suy diện tích theo số lô.'),
 'nhadat24h:4393663':(None,78.6,'Căn Capital Square 2PN, mô tả ghi 78,6m² và tổng giá 6,8 tỷ. Nhãn 78m² làm tròn; 30 triệu/tháng là giá thuê.'),
 'nhadat24h:4400805':(None,66.46,'Phần thông tin căn 2PN Hiyori ghi diện tích sử dụng 66,46m² và tổng giá 4,6 tỷ; nhãn 66m² làm tròn.'),
 'nhadat24h:4401331':(2042,29.4,'Mô tả căn studio F2 tầng 15 trục 25 ghi 29,4m² và giá 2 tỷ 042 triệu = 2,042 tỷ; nhãn 2,040 tỷ/30m² làm tròn.'),
}
EXCLUDE={
 'cafeland:2281695':'Nội dung nhận booking, 50 triệu/book, nhiều loại căn Newtown Diamond; không xác định một căn 83m² có tổng giá riêng.',
 'cafeland:2932528':'Bán cặp đất Minh Mạng/Nguyễn Cơ Thạch; không có giá và diện tích từng thửa. Tách khỏi mục tiêu một lô riêng, không chia đôi tự động.',
 'cafeland:2947670':'Hai lô Võ An Ninh số 46/47 đã có công trình 5 tầng và nhà kho, giá bán lẻ phải liên hệ; không phải quan sát một lô đất trống.',
 'cafeland:3146695':'Hai lô tổng 400m² nhưng giá 1,29 tỷ/lô và diện tích 200m²/lô; địa bàn mô tả Điện Bàn Bắc cũng khác nhãn Hòa Tiến. Không chọn một lô ẩn danh để tạo quan sát.',
 'cafeland:3154276':'Gói ba lô Nguyễn Thần Hiến, tổng 300m²/26,4 tỷ; không phải một lô độc lập.',
 'cafeland:3154481':'Ba lô tổng 600m², mô tả 200m²/lô với giá 1,29 tỷ và địa bàn Điện Bàn Bắc; đối tượng/diện tích không khớp một quan sát.',
 'cafeland:3154756':'Bán cặp hai lô Mỹ Khê tổng 840m²/134,99 tỷ; giữ riêng gói nhiều thửa, không dùng cho mục tiêu một lô.',
 'cafeland:3168420':'Ba lô 110m²/lô, 795 triệu/lô có lựa chọn lô góc; chưa xác định lô nào tương ứng mẫu.',
 'cafeland:3172145':'Ba lô gồm lô góc, 100m²/lô và 940 triệu/lô; nhiều tài sản, địa bàn Đại Hiệp khác nhãn Hòa Tiến.',
 'cafeland:3173264':'Giỏ 20 lô, nhiều diện tích/vị trí và giá từ 7xx đến 1,1x tỷ; không có một quan sát xác định.',
 'cafeland:3176062':'Cặp đất Hoàng Bình Chính, 200m² và 12 tỷ cho gói; không có thông tin riêng từng lô.',
 'cafeland:3176162':'Hai lô TĐC Dragon, 108m²/lô và 2,58 tỷ/lô; chưa chọn một lô cụ thể.',
 'cafeland:3176796':'Quỹ căn Hiyori chỉ giá từ 4,x tỷ, không định danh căn/diện tích tương ứng 58m².',
 'cafeland:3180673':'Quảng cáo 23 căn Hiyori, diện tích từ 50m² khác nhãn 41m²; giá chỉ từ 4 tỷ.',
 'cafeland:3182098':'Giỏ 23 căn Hiyori, diện tích 45,20–161,88m²; không biết căn nào tương ứng nhãn 67m²/4,3 tỷ.',
 'cafeland:3182112':'Ba lô góc Phú Mỹ An tổng 337m²/21 tỷ và sổ riêng từng lô; giữ khỏi mục tiêu một lô.',
 'nhadat24h:4361497':'Bán công trình 5 studio đang vận hành cho thuê; không phải nhà ở thông thường hoặc một căn hộ độc lập.',
 'nhadat24h:4362723':'Quảng cáo nhiều loại căn The Poet và chính sách booking, chưa xác định căn 45m²/5 tỷ.',
 'nhadat24h:4366172':'Nội dung quảng cáo dự án FourS Tower/booking, không có căn và tổng giá riêng.',
 'nhadat24h:4367054':'Nội dung nhận booking Sun Symphony 5, nhiều loại căn; nhãn 30m²/3,1 tỷ không được gắn với một căn cụ thể.',
 'nhadat24h:4373610':'Ba lô 120m²/lô, giá từ 1,2xx tỷ; không chọn được một quan sát tổng giá chính xác.',
 'nhadat24h:4377907':'Hai lô 190m²/lô và giá từ 1,1x tỷ/nền; nhãn 94m² không phù hợp, không đủ giá chính xác để sửa.',
 'nhadat24h:4379999':'Giỏ đất 124–283m², giá từ 1,4xx tỷ; không xác định lô 150m²/1 tỷ.',
 'nhadat24h:4380709':'Quảng cáo nhiều loại căn 43–121m², chưa xác định căn 72m² và tổng giá 5,8 tỷ.',
 'nhadat24h:4380726':'Quảng cáo loại căn 43–121m², không có căn riêng ứng với 73m²/6 tỷ.',
 'nhadat24h:4384533':'Quảng cáo booking S-Light và chính sách dự án, không xác định căn 33,3m²/3,26 tỷ.',
 'nhadat24h:4395238':'Ba lô 125m²/lô, chỉ nêu giá 62 triệu/m²; nhãn là gói tổng 375m², không phải một lô.',
 'nhadat24h:4396919':'Nội dung xác định căn hộ lưu trú TTC Plaza và nhiều loại diện tích; không phải căn hộ ở thông thường riêng lẻ.',
 'nhadat24h:4397716':'Mô hình căn hộ lưu trú TTC Plaza vận hành TUI SUNEO, quảng cáo giá từ 2,x tỷ và trả 20%; giữ riêng phân khúc lưu trú.',
 'nhadat24h:4398151':'Giỏ 23 căn Hiyori với khoảng diện tích; không xác định một căn tương ứng nhãn.',
 'nhadat24h:4399311':'Nội dung quảng cáo 199 căn hộ lưu trú TTC Plaza, trả 20% nhận nhà; ngoài tập căn hộ ở thông thường và chưa có một căn xác định.',
 'nhadat24h:4399805':'Booking cả tòa F2, giá dự kiến từ 2,x tỷ và tiền giữ chỗ 50 triệu; nhãn 1,6 tỷ/32m² không phải căn bán rõ ràng.',
 'nhadat24h:4400239':'Giới thiệu 23 căn Hiyori mở bán, mời nhận danh sách; không xác định riêng căn 58m²/4,5 tỷ.',
 'nhadat24h:4374835':'Hai lô tổng khoảng 200m², mỗi lô 100–120m², giá từ 8xx triệu; không thể chọn 110m²/890 triệu là một căn/lô cụ thể.',
 'nhadat24h:4393629':'Nội dung dự án The Legend nhiều diện tích 58–393m², giá từ 7,x tỷ, không định danh căn 56m²/6 tỷ.',
}
PENDING={
 'cafeland:1904852':'Chỉ có tổng quan hai tòa Times Square và nhiều loại căn/chính sách; chưa chứng minh căn riêng 90m²/10,3 tỷ.',
 'cafeland:2977981':'Mô tả 95m² khác nhãn 93m², giá chỉ từ 8,x tỷ; chưa có tổng giá chính xác hoặc định nghĩa diện tích để sửa.',
 'cafeland:3150191':'Tiêu đề bán đất tặng nhà, mô tả chỉ đất và hai mức 7,1/6,75 tỷ. Chưa giải quyết được hiện trạng công trình/loại tài sản.',
 'cafeland:3154217':'Nhãn 134m² nhưng mô tả 180m² gồm 153m² đất ở/27m² đất trồng cây và nhà C4; địa chỉ đường cũng khác. Không chọn một diện tích.',
 'cafeland:3154905':'Nhà 3–4 tầng kèm đất trống 216m²; mô tả giá 100 triệu/m² khác nhẹ tổng 21,8 tỷ nguồn. Cần xác nhận tổng giá và loại tài sản.',
 'cafeland:3154932':'Tiêu đề nhà hai lô góc nhưng chưa mô tả rõ hiện trạng nhà hoặc giá cho từng tài sản; giữ chờ.',
 'cafeland:3157095':'Tiêu đề/mô tả ghi 1,16 tỷ nhưng nhãn 1,1 tỷ; mô tả không xác nhận diện tích 115m². Cần xác nhận cùng đối tượng trước khi sửa.',
 'cafeland:3160514':'Mô tả là nhà cấp 4 với phòng ngủ và thu nhập thuê, còn danh mục/tiêu đề bán đất tặng nhà; cần chốt loại định giá nhà hay đất.',
 'cafeland:3160515':'Nhãn diện tích 221m² nhưng mô tả 211m². Chưa biết bên nào sai, không tự chọn.',
 'cafeland:3163843':'Diện tích/giá 175m²/795 triệu khớp nhưng nội dung Đại Hiệp khác nhãn Hòa Tiến. Địa bàn đều có thể trong thành phố mới nhưng chưa sửa được vị trí.',
 'cafeland:3177012':'Mô tả tổng quan Mia Plaza, không chỉ ra một căn 63m²/3 tỷ; cần căn và tổng giá riêng.',
 'cafeland:3187419':'Giá 2 tỷ/96m² khớp nhưng mô tả xã Hiệp Đức khác nhãn Cẩm Lệ và có nhà cấp 4. Chưa chốt địa bàn/loại.',
 'cafeland:3160524':'Bán đất tặng nhà nhưng mô tả nhà hai tầng dùng được và vị trí gần cầu Sông Hàn; nhãn đất/địa bàn cần kiểm tra thêm.',
 'cafeland:3154908':'Đất có nhà 127m² trên sổ và thêm 25m² ngoài sổ; giá 7,6 tỷ rõ nhưng chưa chốt loại đất hay nhà.',
 'nhadat24h:4363271':'Nhãn 73m² nhưng mô tả 79m²; chưa biết diện tích thông thủy/tim tường hay nhầm căn. Không sửa diện tích thiếu định nghĩa.',
 'nhadat24h:4371968':'Tiêu đề 2,399 tỷ khác nhãn 2,4 tỷ, mô tả chỉ chính sách trả trước 70% và chiết khấu, chưa xác nhận tổng giá của căn 54m².',
 'nhadat24h:4387633':'Nội dung quảng cáo căn 2PN Victory Place và mời check căn/bảng giá; chưa xác định căn riêng 77,84m²/7,33 tỷ.',
 'nhadat24h:4395380':'Mô tả giá quanh 2,6 tỷ và 31,55m² khác nhãn 2 tỷ/31m²; giá không chính xác và phân khúc khai thác cần làm rõ.',
 'nhadat24h:4395642':'Căn D tầng 6 trục 06, 36,36m²; mô tả tổng giá TTS 70% là 3,032 tỷ, khoảng 2 tỷ để nhận nhà. Cần xác minh phân khúc/pháp lý trước khi áp dụng nhãn khác.',
 'nhadat24h:4395705':'Một nhà 84m² nhưng đang chia hai căn cho thuê; chưa chốt nhà ở thông thường hay công trình đầu tư lưu trú.',
 'nhadat24h:4396539':'Căn D-12A-09, 31,73m², tổng giá thanh toán nhanh 3,68 tỷ; 2,65 tỷ chỉ để nhận nhà, khác nhãn tổng. Đang vận hành khách sạn nên cần xác minh phân khúc; chưa áp dụng sửa giá.',
 'nhadat24h:4396785':'Căn D-16-04, giá TTS 3,3 tỷ rõ nhưng 37,62m² khác nhãn 38m² và đang vận hành khách sạn. Cần xác minh loại/pháp lý, không tự ghép với căn hộ ở.',
 'nhadat24h:4396478':'Mô tả nhiều lựa chọn tòa A1/D, studio giá 2,8 tỷ và nhiều phương án trả 50/70/95%; chưa định danh căn 57m²/2 tỷ. Không nhân đôi giá.',
 'nhadat24h:4363060':'Mô tả căn F5 tầng 5 căn 12, 3PN, 91,6m²+24,4m² sân vườn =116m²; các tổng giá 5,010/5,274/4,183 tỷ theo phương án. Nhãn 1,63 tỷ/38m² sai đối tượng, chưa chọn một phương án.',
}


def decide(e):
    key=e['record_key']
    if e['detail_state']!='identity_verified' or 'detail_structure_unverified' in e['detail_flags']:
        return 'pending',None,None,'Không đủ trang chi tiết đúng danh tính/cấu trúc để quyết định.'
    if key in KEEP:return 'keep',None,None,KEEP[key]
    if key in CORRECT:
        p,a,note=CORRECT[key];return 'correct',p,a,note
    if key in EXCLUDE:return 'exclude',None,None,EXCLUDE[key]
    if key in PENDING:return 'pending',None,None,PENDING[key]
    raise ValueError('Unreviewed record: '+key)


def main():
    evidence=read(REVIEW/'source_evidence.csv')
    assert len(evidence)==87 and len({r['record_key'] for r in evidence})==87
    mapping_sets=[set(KEEP),set(CORRECT),set(EXCLUDE),set(PENDING)]
    assert len(set.union(*mapping_sets))==sum(map(len,mapping_sets))==87
    assert set.union(*mapping_sets)=={r['record_key'] for r in evidence}
    rawsummary=json.loads((BASE/'processed/full_collection_audit/summary.json').read_text(encoding='utf-8'))
    inputs=[V1/(s+'.csv') for s in ['main_dataset','train','validation','test']]+[
        REVIEW/'source_evidence.csv',REVIEW/'fetch_manifest.json',Path(__file__).resolve()]
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    for p,h in rawsummary['input_sha256'].items():
        assert hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h,'Raw changed: '+p
    if (OUT/'summary.json').exists():
        frozen=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
        assert frozen['input_sha256']=={p.relative_to(BASE).as_posix():h for p,h in hashes.items()},'v2 already frozen; use a new version for changed review'
        for p,h in frozen['output_sha256'].items():assert hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h
        print('Training v2 frozen: hashes verified. No files changed.');return
    decisions=[]
    for e in evidence:
        body=(REVIEW/'detail_cache'/(e['record_key'].replace(':','_')+'.html')).read_bytes()
        assert hashlib.sha256(body).hexdigest()==e['detail_sha256']
        decision,p,a,note=decide(e)
        decisions.append(dict(record_key=e['record_key'],decision=decision,price_million=p,area_sqm=a,
            original_price_million=e['original_price_million'],original_area_sqm=e['original_area_sqm'],
            split=e['split'],duplicate_candidate_group=e['duplicate_candidate_group'],note=note,
            source_url=e['detail_url'],detail_sha256=e['detail_sha256'],detail_fetched_at=e['fetched_at_utc'],
            reviewer='assistant_cached_source_review',reviewed_on='2026-10-11',
            evidence_scope='advertised source content; not independently verified transaction or title deed'))
    bykey={r['record_key']:r for r in decisions}
    rows=read(V1/'main_dataset.csv');fields=list(rows[0]);included=[];quarantine=[];changes=[]
    # New duplicate evidence: these two train records describe the same 68m² house.
    # Keep original group IDs/splits, suppress one representative rather than reassign groups.
    extra_duplicate={'nhadat24h:4385371':'nhadat24h:4382420'}
    byrow={r['record_key']:r for r in rows}
    assert all(byrow[k]['model_split']==byrow[v]['model_split']=='train' for k,v in extra_duplicate.items())
    for row in rows:
        d=bykey.get(row['record_key'])
        if d and d['decision'] in ['pending','exclude']:
            quarantine.append(dict(row,source_review_decision=d['decision'],source_review_note=d['note']));continue
        if row['record_key'] in extra_duplicate:
            quarantine.append(dict(row,source_review_decision='suppressed_duplicate',
                source_review_note='Mô tả nhà kiệt Đống Đa 68m²/4,85 tỷ trùng nội dung với '+extra_duplicate[row['record_key']]));continue
        r=dict(row)
        if d:
            for k in ['price_million','area_sqm']:
                if d[k] is not None:
                    assert number(d[k]) and float(d[k])>0
                    r[k]=str(float(d[k]))
            r['price_per_sqm_million']=str(float(r['price_million'])/float(r['area_sqm']))
            r['label_quality']='source_detail_reviewed_'+d['decision']
            changes.append(dict(record_key=r['record_key'],decision=d['decision'],split=r['model_split'],
                old_price_million=row['price_million'],new_price_million=r['price_million'],
                old_area_sqm=row['area_sqm'],new_area_sqm=r['area_sqm'],note=d['note']))
        included.append(r)
    assert len(included)+len(quarantine)==len(rows)
    assert all(r['model_split'] in ['train','validation'] for r in quarantine)
    assert all(r['model_split']==byrow[r['record_key']]['model_split'] and r['duplicate_candidate_group']==byrow[r['record_key']]['duplicate_candidate_group'] for r in included)
    assert len({r['duplicate_candidate_group'] for r in included})==len(included)
    OUT.mkdir(parents=True,exist_ok=True)
    save_csv(REVIEW/'review_decisions.csv',decisions,list(decisions[0]))
    for decision in ['pending','exclude','correct','keep']:
        save_csv(REVIEW/(decision+'.csv'),[r for r in decisions if r['decision']==decision],list(decisions[0]))
    save_csv(OUT/'main_dataset.csv',included,fields)
    for split in ['train','validation']:
        save_csv(OUT/(split+'.csv'),[r for r in included if r['model_split']==split],fields)
    (OUT/'test.csv').write_bytes((V1/'test.csv').read_bytes())
    save_csv(OUT/'quarantined_from_v1.csv',quarantine,fields+['source_review_decision','source_review_note'])
    save_csv(OUT/'label_review_changes.csv',changes,list(changes[0]))
    assert (OUT/'test.csv').read_bytes()==(V1/'test.csv').read_bytes()
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
    assert all(hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h for p,h in rawsummary['input_sha256'].items())
    outputs=list(OUT.glob('*.csv'))+[REVIEW/'review_decisions.csv']
    summary=dict(reviewed_records=87,decisions=dict(Counter(r['decision'] for r in decisions)),
        v1_rows=len(rows),v2_rows=len(included),removed_from_training_or_validation=len(quarantine),
        splits=dict(Counter(r['model_split'] for r in included)),
        categories={c:dict(Counter(r['model_split'] for r in included if r['category']==c)) for c in sorted({r['category'] for r in included})},
        corrected_numeric_records=sum(r['decision']=='correct' for r in decisions),
        test_identical_to_v1=True,raw_and_v1_unchanged=True,new_test_evaluation=False,
        input_sha256={p.relative_to(BASE).as_posix():h for p,h in hashes.items()},
        output_sha256={p.relative_to(BASE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs})
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Dữ liệu huấn luyện v2 sau đối chiếu nguồn','',
        f'Đã tải và kiểm tra đúng danh tính **87 trang** trong hàng chờ train/validation. Quyết định: {summary["decisions"]}. '
        'Quyết định dựa trên trang đã lưu, không theo sai số dự đoán. Không liên hệ người đăng và chưa xác minh giao dịch/pháp lý thực tế.', '',
        f'V1 có {len(rows)} tin; v2 giữ **{len(included)} tin**, cách ly **{len(quarantine)} tin** gồm chờ/loại và một tin nghi trùng bổ sung. '
        f'Chia tập: {summary["splits"]}. Không bổ sung 308 tin của đợt rà soát loại vào lần này.', '',
        '**Test được sao chép nguyên byte từ v1; không thay ID, nhãn hoặc nhóm. Train/validation giữ nguyên split/nhóm của những hàng được giữ.** '
        'Validation đã giảm số hàng và có nhãn được sửa nên không so trực tiếp MAE mới với MAE cũ toàn bộ validation. '
        'Đối chiếu chỉ trên cùng ID và cùng nhãn v2 khi thử mô hình tiếp.', '',
        '## Nguyên tắc', '',
        '- Giá/diện tích chỉ sửa khi nội dung xác định cùng tài sản và số chính xác; không suy tổng giá từ tiền cọc, lịch trả phần trăm hoặc giá mô hình.',
        '- Gói nhiều lô/giỏ hàng/booking, công trình studio và căn hộ lưu trú rõ ràng được giữ riêng khỏi mô hình một nhà/lô/căn hộ thông thường.',
        '- Chưa đủ bằng chứng hoặc sai địa bàn/loại/định nghĩa diện tích thì chờ. Có thể đề cập số đúng tiềm năng trong ghi chú nhưng không áp dụng vào nhãn.',
        '- Giá rao có thương lượng, phương án thanh toán và diện tích sân vườn/ngoài sổ được giữ trong ghi chú. Nhãn nguồn khớp mô tả không phải giá giao dịch đã xác minh.',
        '- Cờ hết hạn trong parser CafeLand được giữ ở bằng chứng; không tự loại chỉ vì chữ này xuất hiện trong trang.', '',
        '## Tệp kết quả', '',
        '- `train.csv`, `validation.csv`, `test.csv`, `main_dataset.csv`: bộ v2.',
        '- `label_review_changes.csv`: nhãn cũ/mới và lý do từng tin được giữ/sửa.',
        '- `quarantined_from_v1.csv`: tin chờ/loại/nghi trùng, không mất raw.',
        '- [review_decisions.csv](../training_source_review/review_decisions.csv): quyết định của đủ 87 tin, URL, thời điểm lấy và SHA256 HTML.',
        '- [source_evidence.csv](../training_source_review/source_evidence.csv): nội dung nguồn và đối chiếu nhãn. HTML trong `training_source_review/detail_cache`.',
        '- `summary.json`: kiểm tra hash, số lượng và test giữ nguyên.', '',
        '308 tin đã phân giải cờ loại ở đợt trước vẫn chưa được thêm. V2 chỉ xử lý 87 tin đang có trong v1. '
        'Các tin ngoài hàng chờ giữ chất lượng sàng lọc ban đầu, chưa được kiểm tra lại chi tiết toàn bộ.', '',
        'Chạy lại `python ai-services/app/data/finalize_training_source_review.py`: chỉ kiểm tra hash nếu v2 đã được chốt; muốn đổi quyết định phải tạo phiên bản khác.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    (REVIEW/'README.md').write_text('# Đối chiếu nguồn 87 tin\n\n'+
        f'Đã tải đủ 87 trang, đúng danh tính 87/87. Quyết định: {summary["decisions"]}.\n\n'+
        'Xem `review_decisions.csv`, các file keep/correct/exclude/pending và bằng chứng `source_evidence.csv`, `detail_cache`, `fetch_manifest.json`. '+
        'Dữ liệu sau áp dụng và giới hạn: [training_v2](../training_v2/README.md).\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if not k.endswith('sha256')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
