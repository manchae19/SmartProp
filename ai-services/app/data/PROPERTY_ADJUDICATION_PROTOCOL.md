# Rà soát snapshot còn chờ — 29/10/2026

Issue #16, tiếp nối #14. Chỉ đọc 234 snapshot của run
`property_expansion_review/runs/e58bb9db7377e200`, gồm 222 tin đang chờ.
Không gọi website, đọc dự đoán hoặc thay kết quả cổng cũ.

## Quyết định trước khi chạy

- Giữ mọi cờ nguồn cũ trừ lỗi thiếu corroboration được giải quyết bằng giá
  VND đầy đủ, có nhãn giá tổng rõ ràng trong chính lời người bán và diện tích
  khớp. Giữ dung sai 1% của cổng cũ, không sửa giá/diện tích cấu trúc.
- Bỏ đúng heading/echo metadata ở đầu/cuối mô tả, không cắt lời người bán
  tại số điện thoại hoặc “liên hệ”. Đọc cả phần sau liên hệ để phát hiện giỏ
  hàng, giá/diện tích/phòng ngủ khác. Metadata lặp không là corroboration.
- Giá thuê, giá theo m², trả trước, booking, khoản vay, quà tặng và giá có
  điều kiện không được nhận làm giá tổng vô điều kiện. Nếu có nhiều giá tổng
  hoặc giá tổng khác header, vẫn chờ đối chiếu.
- Tin bán nguyên tòa/ngoài phạm vi hoặc chào bán rõ nhiều căn được tách khỏi
  tập một căn hộ. Cờ chưa rõ không đồng nghĩa dữ liệu sai: giữ quarantine và
  ghi hành động cần bổ sung cho từng lý do.
- Heading “tòa căn hộ” hoặc số lượng tòa trong tổng quan dự án không tự chứng
  minh bán nguyên tòa. Cờ loại chỉ dựa vào heading được hạ thành cần review,
  không chuyển thành ứng viên qua nguồn. Giữ lý do cũ và bằng chứng chuyển cờ.
- Kiểm tra cả 12 ứng viên đã qua cổng cũ. Giữ cờ mới về giỏ hàng sau liên hệ,
  bàn giao chưa rõ, phòng ngủ PN/BR khác header và đơn giá khác tổng giá/diện tích.
- Liên kết mã căn chỉ khi cùng tên dự án được ghi rõ trong mô tả, mã đủ cụ thể
  có nhiều thành phần và cùng diện tích trong 1%. Bằng chứng này chỉ bổ sung
  liên kết, không xóa liên kết cũ hoặc chứng minh tài sản độc lập.
- Giữ mọi nhóm bảo vệ và quan hệ lịch sử. Một thành viên chưa giải quyết,
  khác địa bàn hoặc giá/diện tích mâu thuẫn chặn cả nhóm. Chọn một đại diện
  theo ID cố định, không theo giá hoặc sai số mô hình.

## Phiên bản thử nghiệm

Giá, diện tích và đặc trưng phải thuộc cùng phản hồi/thời điểm quan sát.
Xuất một hàng/nhóm ứng viên, phân vai `train_refresh_candidate` (nhóm train
đã có) và `fresh_evaluation_reserved` (nhóm chưa gặp lịch sử). Nhóm mới được
giữ ngoài train. Không bổ sung bản đọc lại thành tài sản mới trong train.

Các bảng chưa được phát hành thành X train. Mốc tối thiểu 20 nhóm kiểm chứng
chỉ là điều kiện vận hành đã dùng trong pilot, không bảo đảm tính đại diện
hoặc độ chính xác thống kê. Cần khóa giả thuyết/feature matrix/split/protocol
riêng trước mọi fit hoặc scoring. Đợt này chỉ chuẩn bị dữ liệu và đánh giá
điều kiện, không chọn siêu tham số, không chấm lại cohort đã tiêu thụ.

Giữ nguyên 2.213 train, 299 validation, reserved registry, evaluation ledger,
raw/run cũ, model v6, API và MySQL. Tọa độ/POI chưa xác minh giữ thiếu.
Kết quả xuất cục bộ có manifest và replay; GitHub chỉ có code/tổng hợp.
