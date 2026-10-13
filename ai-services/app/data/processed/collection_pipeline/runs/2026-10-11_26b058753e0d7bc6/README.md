# Lọc toàn bộ dữ liệu SmartProp

Ngày đối chiếu: 2026-10-11. Đọc 20 file nguồn; 11,417 quan sát Việt Nam → **8,509 ID nguồn duy nhất**.

| Nhóm không chồng lặp | Số tin |
|---|---:|
| [eligible](eligible.csv) | 2,082 |
| [needs_review](needs_review.csv) | 4,772 |
| [excluded](excluded.csv) | 1,655 |

**1,435 đại diện đủ điều kiện xét cho train mới** trong [train_candidates.csv](train_candidates.csv). 647 đại diện qua lọc còn lại giữ dự phòng/holdout, không nhập vào train.

## Quy trình chung

1. Đọc toàn bộ CSV/JSONL raw, file cũ và sample; không cộng file processed thành tin mới. Singapore giữ riêng theo SGD/giao dịch HDB.
2. Gộp cùng source/ID, giữ dấu vết snapshot và mâu thuẫn. Kiểm tra URL/ID, bán hay thuê, nhà/đất/căn hộ, Đà Nẵng cũ hoặc mới, giá tổng và diện tích.
   Khôi phục trường giá/diện tích số còn thiếu khi chuỗi nguồn phân tích đầy đủ được; giữ nhãn gốc và nhật ký normalization_changes.csv. Không suy từ đơn giá, khoảng giá hoặc tiền trả trước.
3. Áp dụng quyết định nguồn đã lưu khi hash HTML và nhãn gốc phù hợp. Lưu cả quyết định cũ, mới, giữ/sửa/chờ/loại; không tự ghi lại các file duyệt.
4. Áp dụng quy tắc loại trên mọi tin có cờ, giữ các cờ giá/diện tích chưa giải quyết. Ngày thiếu, trên 183 ngày và ngoại lệ ngưỡng đi vào cần kiểm tra, không xóa raw.
5. Gom nghi trùng trên toàn bộ ID, kể cả cầu nối nhóm cũ. Nhóm mâu thuẫn hoặc có thành viên chưa đủ điều kiện được cách ly; nhóm qua lọc giữ một đại diện.
6. Giữ mọi ID/nhóm holdout cũ khỏi train; xuất ba nhóm và lý do. Không tạo lại test, không huấn luyện mô hình.

## Đọc kết quả

- `all_listings.csv`: một hàng/ID; nhãn gốc và nhãn sau duyệt, nhóm, trạng thái, lý do, bằng chứng, khả năng dùng cho train.
- `eligible.csv`: đã qua quy tắc và nhóm; vẫn là giá rao, chưa phải nhãn giao dịch được xác minh độc lập.
- `needs_review.csv`: các bằng chứng còn thiếu/mâu thuẫn. Không suy giá thỏa thuận, giá trả trước hoặc địa bàn từ tên file.
- `excluded.csv`: ngoài phạm vi/loại, đã duyệt loại hoặc đại diện nghi trùng bị giữ khỏi train. Xem `exclusion_codes`; nghi trùng không phải khẳng định cùng tài sản.
- `review_history.csv`, `duplicate_pairs.csv`: quyết định và liên kết nhóm truy vết được.
- `normalization_changes.csv`: từng trường được khôi phục từ chuỗi nguồn; raw_json vẫn giữ literal dữ liệu gốc.
- `source_audit/file_inventory.csv`, `summary.json`, `manifest.json`: kiểm kê và hash tái lập. Các tập/model/report trước và toàn bộ raw được kiểm tra giữ nguyên.

Bộ train ứng viên mới chưa thay thế training_v2. Nếu dùng để huấn luyện phiên bản mới, chỉ lấy `train_candidates.csv`; không dùng raw_json, tiêu đề chứa giá, đơn giá/m², cờ lọc, ID hay nhóm làm đặc trưng. Cần bộ đánh giá mới được chốt trước khi tối ưu; báo cáo v1/v2 và 137 tin test cũ vẫn giữ nguyên.

Chạy từ F:\SmartProp:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/filter_all_collected.py
```

Cùng dữ liệu/quyết định/mã/ngày: xác minh hash bản chạy đã có. Có thay đổi: tự tạo thư mục bản chạy mới, không ghi đè kết quả cũ. Không tải lại trang nguồn.
