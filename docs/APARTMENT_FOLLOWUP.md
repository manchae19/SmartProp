# Kết quả rà soát tiếp 90 tin căn hộ

Ngày 27/10/2026, theo [issue #8](https://github.com/manchae19/SmartProp/issues/8).
Đã đối chiếu **90/90 tin** với HTML đã lưu, phân tích lại và lưu bằng chứng
từng quyết định. Raw và bản khóa đầu tiên giữ nguyên.

| Kết quả trong 90 tin | Số tin |
|---|---:|
| Bổ sung ứng viên kiểm chứng | 3 |
| Loại khỏi phạm vi căn hộ bán | 10 |
| Chưa đủ bằng chứng | 77 |
| Tổng | 90 |

Ba tin được bổ sung là `cafeland:3136081`, `cafeland:3139807`,
`cafeland:3192653`. Không sửa giá/diện tích: xử lý lỗi nhận diện “block” thành
“lỗ”, giá bán đứng sau ngữ cảnh cho thuê, giá xấp xỉ đứng cạnh giá bán chính
xác, và câu “nhận thông tin chi tiết” ở cuối mô tả làm mất phần nội dung trước đó.
Tất cả vẫn phải qua ngưỡng, cổng nhãn và so trùng của giao thức trước.

10 tin loại khỏi phạm vi gồm 6 tin bán cả tòa, 1 homestay nguyên tài sản, 2
tin tiêu đề ghi TP Huế và 1 đề nghị cho thuê. Chỉ loại khỏi đợt căn hộ bán;
không xóa raw, không tự chuyển sang tập train loại khác. 77 tin còn lại vẫn
được giữ chờ bằng chứng, không đồng nghĩa đều là tin sai.

Đã thử nguồn Nhadat24h: **12 trang, 240 ID**, bỏ qua **238 ID đã có**, lưu
**2 ID mới** trong batch riêng. Cả hai còn chờ: một tin có giá theo phương án
thanh toán/diện tích thành phần, một tin thiếu Product JSON-LD để xác nhận
URL/đơn vị tiền theo giao thức. Không thu đủ mục tiêu tối đa 30 trong giới hạn
12 trang; không lấy lại ID cũ để bù. Checkpoint ở trang 13, đã dừng theo hạn mức.

Tập kiểm chứng hiện có **13 nhóm = 10 nhóm cũ + 3 bổ sung**, còn thiếu **7**
so với mốc thực hành 20. Hai tin Nhadat24h chưa được tính vào đó. Trên toàn bộ
102 tin mới: 13 ứng viên khóa riêng, 10 loại khỏi phạm vi, 79 cần bằng chứng.
Đã so trùng toàn kho 8.509 tin cũ, 100 tin CafeLand và lô mới; giữ các liên kết
nhóm cũ, không tách nhóm nghi trùng để tăng số lượng.

**Chưa thêm dữ liệu vào train, chưa train/chấm v7.** Model/API v6, dữ liệu chuẩn
bị 2.213 train + 299 validation và registry cũ giữ nguyên checksum. 13 nhóm
vẫn là giá rao qua rà soát nguồn, chưa phải giá giao dịch xác minh; mốc 20
không bảo đảm độ chính xác hoặc tính độc lập tài sản.

## Xem dữ liệu trên máy

`ai-services/app/data/processed/apartment_followup_review/latest.json` chọn run
hiện hành. Trong run có:

- `pending_90_decisions.csv`: đủ 90 quyết định, cờ đã giải quyết và cờ còn lại.
- `pending_evidence_private.json`: quote nguồn, trích đoạn chuẩn hóa, checksum.
- `recovered_candidates.csv`: 3 tin bổ sung.
- `excluded_scope.csv`: 10 tin ngoài phạm vi đợt này.
- `needs_evidence.csv`: 77 tin cũ + 2 tin mới đang chờ.
- `collection_holdout.csv`, `cohort_lock.json`: 13 nhóm khóa riêng, cấm dùng để train.
- `summary.json`, `manifest.json`, `duplicate_links.json`: số liệu và kiểm chứng.

Nguồn bổ sung ở `ai-services/app/data/data_raw/apartment_followup_nhadat24h/`.
CSV/cache/bằng chứng giữ cục bộ; chỉ script và báo cáo tổng hợp được commit.

## Kiểm chứng và tiếp tục

Từ gốc SmartProp:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/verify_apartment_followup.py
```

Verifier phân tích lại cache, tính lại quyết định/nhóm, kiểm tra đủ 90 bằng
chứng, bản khóa 13 nhóm và checksum bản v6/các tập cũ; không gọi mạng hoặc model.
Quy tắc và bộ đọc có kiểm thử riêng cho các lỗi ngữ cảnh, mâu thuẫn thật,
ngắt trước checkpoint, nghi trùng xuyên nguồn và bảo vệ nhóm đã khóa.

Không cần chạy lại collector: đã đạt hạn mức 12 trang. Lệnh cùng policy sẽ
không vượt hạn mức để cào tiếp. Đợt sau cần một nguồn/đợt tin thực sự chưa có;
giữ nguyên 13 nhóm đã khóa và so trùng cả 8.611 ID hiện có. Các tin thiếu diện
tích nhãn, giá mâu thuẫn hoặc bảng hàng phải có bằng chứng nguồn mới trước
khi xét lại, không tự điền từ tiêu đề hoặc giá AI.

[Giao thức đợt rà soát](../ai-services/app/data/APARTMENT_FOLLOWUP_PROTOCOL.md) ·
[Lô 100 tin ban đầu](APARTMENT_PILOT_100.md).
