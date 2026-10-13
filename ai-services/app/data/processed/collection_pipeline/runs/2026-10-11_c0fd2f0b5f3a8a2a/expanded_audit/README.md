# Rà soát toàn bộ dữ liệu — chấp nhận Đà Nẵng cũ và mới

Phạm vi theo yêu cầu: toàn bộ Đà Nẵng cũ và địa bàn Quảng Nam cũ thuộc Đà Nẵng mới. Căn cứ sáp nhập: [Nghị quyết 202/2025/QH15](https://baochinhphu.vn/nghi-quyet-cua-quoc-hoi-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-102250612191145158.htm).

Đối chiếu dữ liệu ngày 2026-10-11. Tổng **8,509 ID nguồn Việt Nam**, **2,780 ứng viên qua quy tắc**, **5,712 tin cần xử lý**, và 17 tin đã duyệt giữ/sửa từ đợt căn hộ trước. Ứng viên chưa phải dữ liệu đã xác minh sạch.

Có **929 tin đổi trạng thái** khi mở rộng phạm vi. Không còn bắt buộc gán một quận/huyện cũ. Cột `district` và `district_candidates` giữ nguyên; không ép Hội An, Điện Bàn hoặc phường giao ranh vào một quận cũ.

| Trạng thái | Số tin |
|---|---:|
| screened_candidate_unverified | 1,972 |
| needs_review | 4,094 |
| prior_exclude | 7 |
| prior_pending | 40 |
| other_property_or_building | 1,179 |
| outside_or_unverified_scope | 392 |
| screened_date_unknown | 808 |
| prior_reviewed_correct | 11 |
| prior_reviewed_keep | 6 |

| Thay đổi | Số tin |
|---|---:|
| district_needs_review -> needs_review | 615 |
| outside_or_unverified_scope -> needs_review | 201 |
| district_needs_review -> other_property_or_building | 17 |
| district_needs_review -> screened_candidate_unverified | 95 |
| outside_or_unverified_scope -> screened_date_unknown | 1 |

## Cách xét địa bàn

- Chấp nhận thành phần tỉnh/thành cuối địa chỉ là Đà Nẵng hoặc Quảng Nam; tên đường chứa “Quảng Nam” không đủ bằng chứng.
- Chấp nhận trường tỉnh nguồn đã có bằng chứng trong audit cũ. Tin Chợ Tốt cũ chỉ có tên file và nhãn quận vẫn cần xác minh tỉnh.
- Cờ chưa gán quận cũ được chuyển thành thông tin tùy chọn. Cờ phạm vi cũ được bỏ; cờ vùng từ crawler chỉ bỏ khi địa chỉ chứng minh thuộc phạm vi mới.
- Giữ các cờ giá, diện tích, loại giao dịch, ngày, nội dung, trùng lặp và quyết định duyệt căn hộ trước. Tin ở tỉnh khác vẫn cần cách ly khỏi tập ứng viên.
- Bốn cờ tọa độ từ audit cũ thuộc các tin gắn quận cũ; vẫn giữ để kiểm tra vị trí. Chưa kiểm tra ranh giới tọa độ của toàn bộ thành phố mới và chưa xác minh địa chỉ thực địa.

## Tệp kết quả

- `all_unique_listings_audit.csv`: mọi ID, địa bàn mới và trạng thái cũ để đối chiếu.
- `screened_candidates_unverified.csv`: ứng viên qua quy tắc, gồm tin thiếu ngày được đánh dấu riêng.
- `needs_review.csv`: các tin còn cần xử lý, gồm tin chờ/loại từ quyết định trước.
- `status_changes.csv`: các tin đổi trạng thái; `waived_scope_review_codes` ghi rõ cờ được bỏ.
- `summary.json`: tổng hợp và hash đầu vào.

Kiểm kê snapshot, kiểm tra Singapore và danh sách nghi trùng vẫn ở [audit gốc](../full_collection_audit/README.md). Nhóm nghi trùng cũ chỉ so theo quận/loại và chưa bao phủ đầy đủ các địa bàn mới; không coi là đã loại trùng bất động sản. Singapore giữ riêng, không cộng vào số tin Việt Nam. Không truy cập lại URL, không sửa raw, không huấn luyện lại hoặc đổi tập test.

Chạy lại sau khi audit gốc đã cập nhật:

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/expand_collection_audit_scope.py
```
