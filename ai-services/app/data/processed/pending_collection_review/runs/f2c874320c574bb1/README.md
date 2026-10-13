# Rà soát toàn bộ 5.442 tin đang chờ

**Đã kiểm tra mọi hàng trong nhóm chờ bằng dữ liệu đã lưu. Chưa mở lại toàn bộ 5.442 URL.** Giá là giá rao, không phải giá giao dịch đã xác minh.

| Kết quả không chồng lặp của nhóm 5.442 | Số tin |
|---|---:|
| Giá có điều kiện / nhiều tài sản | 240 |
| Qua lọc sau rà soát | 33 |
| Chưa chốt được giá tổng hoặc diện tích | 282 |
| Cần nguồn để chốt loại bất động sản | 1,568 |
| Nhóm nghi trùng còn vướng | 94 |
| Đã duyệt nguồn trước đây, vẫn chờ | 64 |
| Cần bằng chứng cho các cờ còn lại | 355 |
| Loại khỏi tập huấn luyện / nghi trùng | 91 |
| Chỉ cũ hơn ngưỡng 183 ngày, giữ riêng | 262 |
| Chợ Tốt cũ thiếu bằng chứng nguồn | 1,780 |
| Chỉ thiếu ngày, giữ riêng | 673 |

Khôi phục giá số từ chuỗi giá đầy đủ: **1,156 tin**; diện tích từ chuỗi m²: **1,130 tin**. Có 1,166 ID được bổ sung ít nhất một trường. Chỉ phân tích chuỗi nguồn, không suy nhãn từ mô hình, đơn giá, khoảng giá hoặc tiền trả trước.

Phân giải 86 cờ loại bằng danh mục nguồn cụ thể khi không có tín hiệu đối tượng đối lập. Danh mục nhà đất tổng hợp, đất có nhà, quảng cáo nhiều tài sản vẫn giữ chờ.

## Đọc các nhóm kết quả

- `passed_rules`: qua các quy tắc và nhóm sau rà soát; vẫn chưa xác minh độc lập toàn bộ mô tả.
- `excluded`: loại rõ từ danh mục thương mại/lưu trú/nông nghiệp hoặc giữ đại diện nghi trùng khỏi train. Không xóa raw.
- `historical_candidate`: chỉ vướng ngưỡng 183 ngày và nhóm đơn; giữ cho thử nghiệm lịch sử, không kết luận nhãn sai.
- `undated_candidate`: chỉ thiếu ngày và nhóm đơn; giữ riêng, không tự coi ngày thu thập là ngày đăng.
- Những nhóm còn lại: xem `next_action` và các mã lý do từng tin trong `reviewed_pending.csv`.

## Bằng chứng và truy cập nguồn

Đọc lại 68 trang/cache liên quan tới nhóm chờ: {'identity_verified': 67, 'blocked': 1}. Quyết định chờ trước đây vẫn giữ nguyên. Không coi HTTP 200 là đúng danh tính hoặc nhãn sạch.
Thử 1 URL/nguồn: CafeLand, Nhadat24h, Homedy và Alonhadat trả HTTP 200; Chợ Tốt chuyển sang nhatot.com và trả 403. Đây chỉ là kiểm tra khả năng truy cập mẫu, không phải kết quả tất cả URL. Không vượt chặn truy cập.
Trang Homedy mẫu không có trường ngày đăng trong vùng nội dung đã kiểm tra; không lấy ngày ảnh, ngày thành lập website hoặc ngày trang liên quan làm ngày tin.

## Kết quả toàn bộ bộ sưu tập sau rà soát

{'eligible': 1634, 'needs_review': 5326, 'excluded': 1549}. **1,081 ứng viên được phép xét cho train mới**, không thay thế training_v2. Các tập cũ, 137 tin test, raw và quyết định duyệt giữ nguyên.

Có 8 tin vốn không nằm trong nhóm chờ đổi trạng thái sau khi kiểm tra lại các cầu nối/giá trị mới. Xem `status_and_label_changes.csv`; không âm thầm sửa tập cũ.

## Tệp sử dụng

- [reviewed_pending.csv](reviewed_pending.csv): đủ 5.442 ID, trạng thái trước/sau, nhãn, lý do và hướng xử lý.
- [normalization_changes.csv](normalization_changes.csv): từng giá trị khôi phục và chuỗi gốc.
- [source_check_queue.csv](source_check_queue.csv): các tin còn cần bằng chứng chi tiết.
- [historical_candidates.csv](historical_candidates.csv), [undated_candidates.csv](undated_candidates.csv): nhóm thử nghiệm riêng, không trộn train chính.
- [all_listings_after_review.csv](all_listings_after_review.csv): kết quả đủ 8.509 ID; raw_json giữ literal dữ liệu gốc.
- `eligible.csv`, `needs_review.csv`, `excluded.csv`, `train_candidates.csv`: các tập sau rà soát có dấu vết nhóm/holdout.
- `cached_detail_evidence.csv`, `category_resolutions.csv`, `summary.json`, `manifest.json`: bằng chứng và hash.

Chạy lại:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/review_pending_collection.py
```

Cùng đầu vào dùng bản chạy đã xác minh hash; có thay đổi tạo bản chạy mới. Không huấn luyện mô hình trong bước này.
