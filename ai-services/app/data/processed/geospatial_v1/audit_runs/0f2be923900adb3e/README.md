# Độ phủ vị trí SmartProp

Kiểm tra 8,509 ID duy nhất của collection hiện tại. Có 2,752 cặp tọa độ hợp lệ về số, 844 cặp khác nhau; tất cả còn chưa xác minh độ chính xác và quyền tái sử dụng để huấn luyện. Điểm lặp không tự chứng minh tin trùng hay vị trí sai.

Trong v3: 67 train và 6 validation có tọa độ. Có 80 ứng viên tọa độ đủ điều kiện dữ liệu; 2,002 tin đủ điều kiện còn cần định vị. Không lấy lại tin bị loại/chờ duyệt chỉ vì có tọa độ.

- `location_audit.csv`: toàn bộ ID, địa chỉ nguồn, trạng thái và số ID dùng cùng tọa độ.
- `coverage.csv`: độ phủ theo nguồn, cohort và trạng thái dữ liệu.
- `coordinate_review_template.csv`: bản mẫu cho các ứng viên có tọa độ; sao chép ra ngoài run trước khi duyệt.
- `geocoding_queue.csv`: hàng chờ địa chỉ, không phải địa chỉ đã định vị. Số trong địa chỉ chỉ là tín hiệu.

Chưa có tọa độ được duyệt dùng ML. Không sửa giá, diện tích, train/validation/test hoặc model v3. Dữ liệu test giữ riêng; không phân tích giá hay dự đoán của test.
