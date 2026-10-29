# Thử đặc trưng có nguồn và lô 75 tin — issue #21

Chốt trước thu mạng và trước fit. Ngày 29/10/2026. Base mã nguồn: `e63a11887a3cbd1f006e985370ed1ab3b7dd19ae`.

## Nguồn và thời gian

- Cohort thí nghiệm nội bộ: đúng 2.213 nhóm train sạch tại preparation `4fdb8ef79db89b16`. Không thêm hoặc đổi giá, nhóm/split cũ. Validation 299, pilot 132/24, tập dự phòng và 5 nhóm mới đã dành riêng không dùng để chọn/chấm model lần này.
- Rà toàn bộ 424 giá trị street gốc. Tên đường chỉ là lời nguồn, chuẩn hóa Unicode/khoảng trắng/tiền tố đường; không tự khôi phục dấu, không suy quận, không geocode, không dùng tâm đường/phường làm tọa độ. Đường có nhiều tên, quảng cáo, chỉ dẫn gần/cách hoặc độ rộng không được coi là tên đường chắc chắn.
- Chỉ title, street, legal_status và thuộc tính có sẵn trong raw cùng bản ghi giá cũ được dùng để trích đặc trưng bổ sung. Không dùng bất kỳ mô tả HTML refresh nào cho nhãn cũ, kể cả giá/diện tích trùng. Mọi giá trị mới có quote, hash raw và trạng thái; mâu thuẫn giữ thiếu.
- Các lời nguồn thử thêm: đường, rộng kiệt, ô tô vào, tầng căn hộ, nội thất, pháp lý; cộng diện tích đất ở và chiều ngang thửa khi được nêu rõ. Đây là lời rao, chưa phải đo đạc/xác minh pháp lý. Không dùng giá/đơn giá, ngày tương lai, người bán/liên hệ hoặc đoạn giá làm X.

## Thu mới có giới hạn

- Batch riêng `data_raw/source_features_75_20261029`; CafeLand tối đa 75 ID (25 nhà riêng, 25 đất ở/thổ cư, 25 căn hộ). Tối đa 12 trang mỗi loại, không bù quota giữa các loại. Nhà/đất từ trang 1; căn hộ từ checkpoint sau lô 60 trước, chốt số trang vào plan trước request. Ưu tiên tránh lặp lại các trang đã lấy; không hứa đạt 75 nhóm đạt chất lượng.
- Loại 8.791 ID đã biết (8.509 lịch sử + 222 batch cũ + 60 mở rộng), tối đa 10 tin/loại/địa bàn đã được catalog duyệt; địa bàn chưa rõ giữ hàng chờ, không đoán theo tiêu đề. Một ID chỉ lưu một lần trong batch; đọc lại hoàn tất không truy cập mạng.
- robots cùng host HTTPS, ít nhất 3 giây/request, giới hạn response, không login/bypass. Dừng toàn bộ lượt khi 403/429/challenge/lỗi mạng/HTML sai. Có checkpoint từng ID, hash nội dung và khóa chủ sở hữu; kiểm tra lại state sau khi lấy khóa. 404/410 được ghi nhận, không suy đã bán. Bản ghi tải thành công không có nghĩa đủ train.
- Review offline replay từ body và listing đã lưu, giá/thuộc tính cùng response; kiểm tra bán/loại tài sản, tổng giá VND, area, ngày nguồn 0–183 ngày, nội dung một tài sản, xung đột/giá từ/booking/chiết khấu/giá che. Kiểm tra trùng nhóm với toàn bộ lịch sử + 222 + 60 + cạnh nhóm bảo vệ, giữ mọi liên kết cũ. Nhóm có liên kết cũ hoặc thành viên chưa rõ không là fresh.
- Tin đạt yêu cầu mới giữ **reserved, DO_NOT_TRAIN**, không nhập vào model nội bộ. Không chấm tập mới nếu dưới 20 nhóm sạch mỗi loại; dù đủ cũng cần protocol thí nghiệm độc lập trước khi mở nhãn đánh giá. Không tiêu thụ 5 nhóm cũ.

## Thí nghiệm nội bộ đóng băng

- Hai cấu hình duy nhất: `v6_all` và `source_enriched`. Cùng 2.213 nhóm, cùng 3 fold theo SHA256(`source-feature-v1/fold/` + pipeline_group) mod 3, không chọn lại salt. Xuất membership trước fit. Không tuning/early stopping hoặc chọn mẫu theo sai số.
- Baseline giữ nguyên `property_text_features_v6.py` và v6/all frozen values. Enriched nối đặc trưng mới có nguồn gốc. Tên đường one-hot được fit **chỉ trên phần fit** với tối thiểu 3 nhóm/đường; held-only/hiếm giữ unknown; không điền từ điển bằng validation. Giá/diện tích chỉ dùng theo baseline đã có; giá/đơn giá không là X mới.
- XGBoost CPU 4 threads, seed 42, hist, 300 rounds, objective reg:squarederror trên log tổng giá, depth 3, eta .03, min_child_weight 5, subsample .8, colsample_bytree .8, lambda 10. Dự đoán exp log, không thay model ứng dụng.
- Báo MAE triệu VND, MAPE, median APE, within20, R² từng loại và pooled, từng fold, và baseline median đơn giá theo loại/địa bàn (>=5 nhóm fit, fallback median loại). Không dùng `100-MAPE` làm accuracy.
- Chỉ đề cử nghiên cứu tiếp nếu MAE pooled giảm >=5%, tốt hơn median, MAE mỗi loại không tăng >5%, within20 mỗi loại không giảm >5 điểm %, và ít nhất 2/3 fold mỗi loại không kém baseline. Đây là CV thăm dò trên train đã nghiên cứu, không phải đánh giá độc lập hay cổng tự deploy. Nếu không đạt giữ v6, không fit final replacement.
- Manifest lưu input/protected hashes, source/schema/model, prediction và membership. Verify tải model để tái lập dự đoán/metrics không gọi fit. Bảo vệ raw/run/splits/ledger/v6 trước và sau. Không dự báo xu hướng giá từ thử nghiệm này.
