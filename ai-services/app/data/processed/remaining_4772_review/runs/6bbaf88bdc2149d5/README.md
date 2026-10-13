# Rà soát toàn bộ 4.772 tin — ngày đăng là metadata

Đối chiếu ngày 13/10/2026 với collection đã chốt ngày 11/10/2026. Đã kiểm tra tất cả 4.772 ID đang chờ, dữ liệu nguồn và bằng chứng/cache đã lưu. Đây là rà soát bằng quy tắc, không khẳng định đã xác minh thủ công từng tài sản.

## Chính sách theo yêu cầu mới

Bỏ hai điều kiện loại tin `older_than_183_days` và `listing_date_unavailable`. XGBoost không yêu cầu ngày đăng hay tuổi tin tối đa 183 ngày; đây là ngưỡng trước đây của SmartProp. Ngày cũ/thiếu ngày vẫn được giữ trong metadata, không thay bằng ngày cào và không tự coi giá cũ là giá thị trường hiện tại. [Tài liệu đầu vào XGBoost](https://xgboost.readthedocs.io/en/stable/python/python_intro.html).

Giữ mọi điều kiện khác về giá/diện tích, danh mục, giao dịch/địa bàn, nội dung nhiều tài sản/giá trả trước, quyết định nguồn chưa giải quyết và trùng nhóm. Các ngưỡng giá/diện tích là quy tắc chất lượng SmartProp, không phải giới hạn bắt buộc của thư viện XGBoost. Không sửa nhãn theo mô hình.

| Kết quả trong 4.772 tin | Số ID |
|---|---:|
| needs_review | 3,752 |
| eligible | 980 |
| excluded | 40 |

| Lý do/kết quả chính, không chồng lặp | Số ID |
|---|---:|
| financial_multiple_or_special_asset_context | 876 |
| price_area_or_structure_unresolved | 881 |
| property_category_unresolved | 136 |
| eligible_after_date_policy_change | 980 |
| duplicate_group_unresolved | 44 |
| duplicate_representative_suppressed | 40 |
| prior_content_review_still_unresolved | 2 |
| source_blocked_not_individually_requested | 1,798 |
| detail_http_error | 7 |
| source_identity_unverified | 3 |
| geography_or_sale_unverified | 5 |

Toàn bộ collection sau chính sách mới: `{'eligible': 3062, 'needs_review': 3752, 'excluded': 1695}`. Nhóm trùng giữ một đại diện; nhóm còn thành viên có vấn đề giữ ngoài train. Không gán lại nhóm hay split lịch sử.

## Đầu vào XGBoost đã kiểm tra

Train **2,110**; validation **299** giữ đúng 299 ID v3; eligible giữ riêng **653**. Mọi nhóm validation/test cũ tiếp tục được giữ riêng. Các eligible holdout mới không nhập vào validation phát triển 299 dòng để giữ phép so sánh.

Đã tạo DMatrix thật bằng XGBoost cài trên máy, kiểm tra ma trận/nhãn hữu hạn và lưu buffer theo từng loại tài sản. Mã hóa diện tích, khu vực, phường, số phòng và cờ thiếu; vocabulary chỉ fit trên train. Giá mục tiêu là log của tổng giá rao (triệu VND), không phải giá giao dịch. Không dùng tiêu đề, mô tả, đơn giá hoặc ID làm feature. **Chưa huấn luyện model mới; model v3 giữ nguyên.**

## Tệp

- [Tất cả 4.772 kết quả theo ID](reviewed_4772.csv), [các chuyển trạng thái](status_changes.csv).
- [Collection sau rà soát](all_listings_after_review.csv), [eligible](eligible.csv), [còn chờ](needs_review.csv), [excluded](excluded.csv).
- [Train](training_inputs/train.csv), [validation cố định](training_inputs/validation.csv), [registry giữ riêng](training_inputs/reserved_holdout_registry.csv), [kiểm tra DMatrix](training_inputs/matrix_validation.json).
- [Số liệu và lý do](summary.json); thư mục `by_issue` chứa từng hàng chờ theo lý do chính.

1.798 URL Chợ Tốt chưa được yêu cầu từng tin do nguồn bị chặn trước đó; không trình bày thành 1.798 lỗi HTTP riêng. HTTP 200/khớp ID không tự chứng minh nhãn hoặc vị trí đúng. Chưa có dữ liệu vị trí cấp nhà mới; không thêm tâm đường vào feature.

Bộ mới thay đổi phân bố thời gian/nguồn so với v3; dùng chung validation để so sánh bước đầu, vẫn cần kiểm chứng theo thời gian hoặc tập mới độc lập. Validation phát triển đã dùng trước đây, không phải benchmark mới. Tin không ngày không thể tự gán thứ tự thời gian để đánh giá dự đoán tương lai.
