# Lô thử 100 tin căn hộ — 27/10/2026

Theo [issue #7](https://github.com/manchae19/SmartProp/issues/7), đã thu thêm
**100 tin CafeLand không trùng ID với 8.509 tin cũ**, lưu riêng. Homedy ngắt kết
nối khi kiểm tra; Nhadat24h trả trang công khai nhưng chưa dùng cho đợt này.
Đã tuân thủ robots.txt, nhịp tối thiểu 3 giây, giữ checkpoint và cache.

**Kết quả: 10 ứng viên kiểm chứng, 90 tin cần rà soát/cách ly.**
Chưa thêm tin nào vào train và chưa huấn luyện v7. Mốc cân nhắc kiểm chứng
đã chốt là 20 nhóm qua rà soát; còn thiếu ít nhất 10 nhóm. Mốc này không phải
bảo đảm thống kê. Không thay model v6 hoặc lịch sử định giá đang chạy.

Ngày nguồn hiển thị từ **21/07 đến 27/10/2026**: 42 tin tháng 7, 5 tin tháng 9,
53 tin tháng 10. Có thể là ngày cập nhật/đăng lại, không phải thời điểm giao dịch.

Các cờ có thể chồng nhau: 29 tin thiếu diện tích có cấu trúc, 10 tin không có
tổng giá dùng được, 38 tin có dấu hiệu bảng hàng/nhiều căn, 9 tin lệch giá giữa
nhãn và JSON-LD. Một tin nghi liên kết tài sản cũ đã cách ly. Có cả tin nhãn
“căn hộ” nhưng bán toàn tòa, mâu thuẫn số phòng và mô tả căn hộ tại Huế.
90 tin không đồng nghĩa 90 tin sai: cần xử lý từng lý do trong dữ liệu gốc.

Đã kiểm tra checksum và phân tích lại đủ 100 cache. Đối chiếu nhóm/tiêu đề/
diện tích/giá trên toàn bộ 8.509 tin; mô tả lịch sử có xác minh danh tính chỉ
phủ 2.575 tin. Việc chưa phát hiện liên kết không chứng minh khác căn nhà.
10 ứng viên vẫn là **giá rao qua quy tắc**, chưa phải nhãn giao dịch xác minh.

## Tệp cục bộ

- `ai-services/app/data/data_raw/apartment_pilot_100/apartment_records.csv`: 100 tin thô.
- Cùng thư mục: `records.jsonl`, `checkpoint.json`, `policy.json`, `latest_run.json`, cache HTML.
- `ai-services/app/data/processed/apartment_pilot_review/latest.json`: chọn bản rà soát hiện hành.
- Trong run được chọn: `README.md`, `all_decisions.csv`, `needs_review.csv`,
  `collection_holdout.csv`, `cohort_lock.json`, `duplicate_links.json`, checksum.

CSV/cache/checkpoint giữ trên máy, được `.gitignore` bảo vệ. GitHub chỉ chứa
script, kiểm thử và báo cáo tổng hợp; không đưa nội dung người đăng vào commit.

## Chạy và kiểm chứng

Từ `F:\SmartProp`, nếu lô còn dở, cùng lệnh tiếp tục từ checkpoint; đích là
**100 tin tổng cộng trong lô**, không phải thêm 100 mỗi lần chạy. Mỗi lần duyệt
tối đa 12 trang từ vị trí đã lưu. Hiện đã đủ 100, không cần cào lại.

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/collect_apartment_pilot.py --target 100 --pages 12 --delay 3
```

Kiểm chứng lô đã khóa, hoàn toàn ngoại tuyến:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_apartment_pilot.py
```

Tạo bản rà soát mới khi quy tắc/đầu vào thay đổi, không ghi đè run cũ:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/review_apartment_pilot.py
```

Chạy lại cùng đầu vào/quy tắc đã có run thì dùng verifier. Verifier kiểm tra
cache, CSV so với nhật ký JSONL, tính lại các quyết định/nhóm, danh sách khóa,
và checksum model v6/các tập đã chuẩn bị. Không chạy dự đoán trên lô mới.

[Quy tắc đầy đủ](../ai-services/app/data/APARTMENT_PILOT_PROTOCOL.md).
Bước tiếp theo: bổ sung bằng chứng cho 90 tin và/hoặc thu một lô từ nguồn khác;
so trùng với toàn bộ kho và 10 nhóm đã khóa. Giữ tập kiểm chứng riêng trước
khi chuẩn bị dữ liệu huấn luyện v7. Bộ chuẩn bị cũ vẫn là **2.213 train +
299 validation phát triển**.
