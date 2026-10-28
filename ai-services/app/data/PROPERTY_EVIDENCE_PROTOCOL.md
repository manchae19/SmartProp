# Rà đặc trưng tài sản v1

Chốt29/10/2026, issue#12. Cohort cố định:2.213 train/299 validation, không dùng
24 nhóm đã chấm để sửa quy tắc, chọn mẫu hoặc quyết định cấu hình.

## Nguồn và bằng chứng

Đọc snapshot đã khóa, giữ nguyên raw/nhãn/diện tích/group/split/ledger/v6.
Tiêu đề và `legal_status` nguyên gốc là lời khai nguồn, có SHA văn bản/JSON.
Mô tả chỉ nhận khi xác minh danh tính/cấu trúc, HTTP200, hash HTML, header
giá/diện tích và loại tài sản khớp cohort; phân tích lại HTML kiểm tra văn bản.
Mô tả không qua cổng không dùng. Không tự sửa nhãn từ nội dung hoặc dự đoán AI.

Xuất tất cả feature/quote vào file DO_NOT_TRAIN. Lời rao được nhận không phải
đo đạc thực địa, xác minh giấy tờ hoặc sự thật pháp lý. Chưa tạo ma trận X hay
fit vocabulary/model. Coverage validation chỉ mô tả, không dùng ví dụ validation
để phát triển quy tắc. Quy tắc dùng fixture và ví dụ train.

## Trích lời rao

- `alley_width_m_claim`: chỉ số mét cạnh kiệt/hẻm; không ngang đất, số kiệt,
  khoảng cách ra đường, đường quy hoạch hoặc công trình lân cận. Dải1–20m
  là cổng rà soát; khoảng/range và mâu thuẫn giữ missing.
- `car_access_claim`: chỉ lời rao kiệt/hẻm ô tô hoặc ô tô vào tận tài sản;
  giữ phủ định rõ ràng. Có gara hoặc gần kiệt ô tô không chứng minh lối vào.
- `apartment_floor_claim`: chỉ số tầng của căn hộ; không số tầng tòa, căn1205,
  danh sách căn hoặc khoảng tầng. Dải1–80 là cổng rà soát, không khẳng định
  các tài sản ngoài dải là sai.
- `handover_year_claim`: năm bàn giao được nói rõ, không dự kiến/tương lai.
- `interior_claim`: full/cơ bản/không có được nói rõ; không suy full từ
  “cao cấp” hoặc “tặng nội thất”.
- `legal_document_claim`: ghi nhận lời rao giấy chứng nhận/hợp đồng/chờ cấp;
  không khẳng định chủ quyền hoặc khả năng giao dịch.
- Dự án/tòa: chỉ xuất ứng viên tên có quote vào hàng chờ, chưa tự chuẩn hóa
  tên hoặc gán mã từ tên đường/địa bàn. Cần kiểm danh tính dự án trước khi dùng.

Phủ định, tương lai, gần đó, giỏ hàng hoặc nhiều giá trị khác nhau của cùng
trường giữ missing. Mọi giá trị nhận được có source_kind, source_quote,
source_sha256 và rule; quote gốc giữ cục bộ. Không đưa nguyên văn/giá/ID vào X.

## Thu mô tả có mục tiêu

Hàng đợi chỉ từ train căn hộ CafeLand thiếu mô tả khớp, sắp theo ID, không theo
giá hoặc sai số. Một lô tối đa20 ID, robots và client giới hạn3giây hiện có;
chỉ HTTPS cùng nguồn/cùng ID, dừng khi403/429/challenge/lỗi mạng. Cache/metadata
tách riêng, mỗi phản hồi công bố nguyên tử và dùng làm checkpoint; không sửa
cache hoặc nhật ký cũ. HTTP404/410 giữ đúng trạng thái, không suy đã bán.

Refresh là quan sát mới. Có cùng giá/diện tích không chứng minh các đặc trưng
đã tồn tại ở thời điểm nhãn cũ; giữ trạng thái NOT_ASOF_VERIFIED và cấm tự ghép
vào train. Việc này xác định khả năng lấy trường từ nguồn và kế hoạch thu cohort
mới, không hợp thức hóa văn bản hiện tại thành bằng chứng quá khứ.

## Quyết định sau audit

Xuất coverage và hàng đợi thu thập trước khi thử model. Số mẫu có lời rao không
tự xác nhận chất lượng; cần rà quote/nguồn/thời gian và định nghĩa đầu vào API.
Không train chỉ để có phiên bản mới khi thiếu bằng chứng hoặc không có tập
kiểm chứng mới. Tiếp tục ghi quan sát giá theo thời gian cho phần xu hướng;
một tháng giá rao chưa đủ xác nhận xu hướng thị trường.
