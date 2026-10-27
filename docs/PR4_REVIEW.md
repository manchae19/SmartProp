# Rà soát PR 4 và kiểm chứng tích hợp

Ngày 27/10/2026. Review theo skill `code-review` với hai hướng độc lập. Mốc gốc: `7368bc1fdecaa5b1259aa83e24adbf4a4b975113`; commit bắt đầu review: `d50d8865ecfa8881e1c544297260376038df486e`. Phạm vi 474 file, ưu tiên API/model loader, xác thực, FE định giá/lịch sử, persistence, launcher và chuẩn bị dữ liệu. Review không chứng nhận từng dòng crawler lịch sử hoặc các skill được nhập nguyên bản.

Đối chiếu yêu cầu tại [issue 3](https://github.com/manchae19/SmartProp/issues/3) và [issue 5](https://github.com/manchae19/SmartProp/issues/5). Các bản vá bên dưới đã được hai hướng review kiểm tra lại trước khi bàn giao.

## Standards

**Một vi phạm hợp đồng P2 đã xử lý.** Cleanup cũ chạy nối tiếp trong `run-demo.py` và `check-history-mysql.py`: nếu `backend.wait` hoặc `ai.wait` ném `TimeoutExpired`, chương trình bỏ qua bước dừng MySQL. Điều này trái cam kết dừng đúng stack do launcher tạo trong `VALUATION_HISTORY.md`.

Đã thay bằng `cleanup_all` để mọi thao tác cleanup được thử độc lập; `stop_owned` có thời gian chờ hữu hạn, kill dự phòng và `mysqladmin` có timeout. Test tại điểm gọi `run_demo.main()` mô phỏng Ctrl+C rồi BE không chịu thoát, xác nhận vẫn tới bước dừng MySQL. Có kiểm tra riêng trường hợp cleanup AI lỗi và graceful shutdown lỗi. Build kiểm thử đi vào `.scratch` riêng, không ghi đè JAR của BE đang dùng.

**Một nhận xét thiết kế P3, không chặn merge.** Có thể gom invariant kiểm tra phản hồi model được lặp trong `ValuationService` và `ValuationHistoryService`. Hai luồng có DTO/hợp đồng riêng; chưa thấy lỗi hành vi do phần lặp, nên chưa refactor trong đợt này.

Review lại bản vá không phát hiện lỗi Standards mới cần chặn merge.

## Spec

**Một lỗi P1 đã xử lý.** Yêu cầu database riêng có thể bị phá vỡ khi môi trường cha chứa `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME` hoặc `SPRING_APPLICATION_JSON`. Trước bản vá, launcher chỉ ghi `DB_URL`/`DB_USER`, có độ ưu tiên thấp hơn các cấu hình Spring trực tiếp. Đã xác nhận thứ tự ưu tiên bằng Spring-core 6.2.19 với giá trị tổng hợp, không kết nối database nguồn.

Đã lọc cấu hình Spring/JVM kế thừa, cố định datasource URL/username trên tham số Java, giữ mật khẩu/JWT trong biến môi trường riêng. Helper chỉ chấp nhận schema local demo hoặc schema thử có prefix riêng trên loopback. Không in secret hoặc đưa mật khẩu lên dòng lệnh.

Review lại xác nhận yêu cầu cách ly database được đáp ứng; không thấy sai lệch mới trong phần sửa. Các phần JWT, owner, tính lại giá, chống lưu trùng, catalog địa bàn và cohort chuẩn bị phù hợp yêu cầu đã rà soát. Chức năng nghiệp vụ ngoài định giá chưa được tuyên bố tích hợp đầy đủ.

## Bằng chứng sau sửa

- **6 regression test tổng hợp đạt**: cấu hình Spring/JVM xung đột, chặn schema/host không thuộc phạm vi, lỗi/timeout cleanup và đường gọi thật của launcher với tiến trình giả lập. Không signal tiến trình thật trong các test này.
- Chạy lại `check-history-mysql.py --browser` với datasource môi trường trỏ vào fixture không tồn tại ở cổng 1, JSON Spring/config location/JVM option xung đột: **13 kiểm thử BE và 3 live browser đạt**, không retry hoặc bỏ qua. MySQL/schema và JAR đều ở thư mục thử riêng; đủ ba loại tài sản được lưu/đọc/xóa bằng model thật.
- Kiểm tra kết nối demo của người dùng trả AI 200, BE/MySQL 200, FE → AI 200, FE → BE 401 không JWT. Phiên đăng nhập/database demo hiện có không được dùng làm fixture.
- Phân tích sai số dùng đúng 299 dự đoán đã lưu; 5 test và verifier đối chiếu 124 hàng phân nhóm đạt. Model, extractor, SQL nguồn và snapshot dữ liệu giữ nguyên.
- 26 kiểm thử API/Python chạy lại đạt, gồm 299 dự đoán đối chiếu qua API. Các kết quả FE 10 test/build và suite E2E cũ được ghi riêng theo lần chạy trong PR, không gọi là cùng một lượt kiểm tra mới.

Tổng Standards: 1 vi phạm P2 đã sửa, 1 gợi ý P3 không chặn. Tổng Spec: 1 lỗi P1 đã sửa. Không còn phát hiện chặn merge trong phạm vi đã review; kiểm chứng kỹ thuật không thay thế đánh giá mới về chất lượng giá.
