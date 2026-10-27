# Mở rộng kiểm chứng sau review PR #10

Ngày 27/10/2026, theo [issue #9](https://github.com/manchae19/SmartProp/issues/9).
Đã thu thêm **120 ID CafeLand mới** trong hai batch riêng 80 và 40, bắt đầu
ở vị trí đã dừng. Giữ robots, nhịp tối thiểu 3 giây và hạn mức từng batch;
không sửa CSV/checkpoint/metadata các lô trước.

Đã sửa so trùng để dùng cùng ranh giới mô tả v2 ở cả tin mới và lịch sử.
Regression bao phủ hai tiêu đề khác nhau nhưng mô tả dài trùng, kết thúc
bằng “liên hệ để nhận thông tin chi tiết”. Không nới cổng hoặc tách nhóm để
tăng số lượng. [Báo cáo review](APARTMENT_PIPELINE_REVIEW.md).

| Kết quả | Tổng các lô mới | Riêng 120 tin bổ sung |
|---|---:|---:|
| Nhóm ứng viên khóa riêng | 24 | 11 |
| Cần thêm bằng chứng | 186 | 107 |
| Ngoài phạm vi căn hộ bán | 12 | 2 |
| Tổng | 222 | 120 |

Giữ cả 13 nhóm trước. Đối chiếu 8.509 ID lịch sử và các batch mới: không
trùng ID; toàn kho đã đối chiếu hiện có **8.731 ID**. Nhóm văn bản chưa chứng
minh độc lập tài sản thực địa; nhãn là giá rao, không phải giao dịch xác minh.

Tập 24 nhóm đã được chấm trong [thử nghiệm v7](TRAINING_V7_TRIAL.md), không
còn là tập mới cho tối ưu cấu hình. Ledger và entry point vận hành chặn
trùng record/nhóm kể cả khi thay metadata hoặc mở rộng cohort. Cấm ghép vào train.

## Tệp và lệnh

Trong `ai-services/app/data/`:

- `data_raw/apartment_extension_80/`, `data_raw/apartment_topup_40/`: batch riêng,
  JSONL bền vững, CSV, checkpoint, robots, cache, policy.
- `processed/apartment_extension_review/latest.json`: bản rà soát hiện hành;
  có `collection_holdout.csv`, `cohort_lock.json`, quyết định và checksum.
- `processed/evaluation_ledger/`: cohort đã reserve/chấm, giữ ngoài Git.

Chỉ xem trạng thái batch đã khóa:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/collect_apartment_extension.py --status pilot
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/collect_apartment_extension.py --status nhadat
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/collect_apartment_extension.py --status extension
```

Không gọi lại collector lịch sử v1/v2. Mã cũ giữ cho replay; đường chạy mới
kiểm policy trước ghi, kiểm lại trạng thái sau lấy khóa, nhả khóa cả khi lỗi
đọc/xuất CSV. `repair_apartment_extension_csv.py` chỉ phục hồi từ log/cache
đã kiểm chứng trước khi cohort khóa.

Kiểm chứng nguồn/quyết định, không fit:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_apartment_extension.py
```

[Giao thức](../ai-services/app/data/APARTMENT_EXTENSION_PROTOCOL.md).

Môi trường pipeline dữ liệu cần cả bộ model và lxml:

```powershell
.\ai-services\.venv\Scripts\python.exe -m pip install -r ai-services/app/data/requirements_apartment_review.txt
```

Kiểm thử thuần không cần kho CSV/HTML cào được; verifier đầy đủ cần dữ liệu
cục bộ và các snapshot đã chốt. Raw/cache không có trong bản clone GitHub.
