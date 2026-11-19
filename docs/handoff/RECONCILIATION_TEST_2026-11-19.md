# Nhánh thử tích hợp Backend-Huy/main

Nhánh: `test/reconcile-backend-huy-main`, xuất phát từ `d91bf039`.
Không merge vào main; không áp migration vào database thật.

## Những phần đã hòa giải

- Giữ React hooks hiện tại; phục hồi lựa chọn V1.3/V6, số đo bổ sung, điền nhanh địa chỉ và SHAP.
- V1.3 preview cần bật rõ ràng và có weights đã xác minh. V6 là phương án khả dụng khi thiếu V1.3.
- Lịch sử vẫn chỉ lưu V6, không ghi kết quả V1.3 thành kết quả V6.
- Launcher Windows dùng source chuẩn `ai-services/run_api.py`; bổ sung pandas và lock wheel Windows có SHA-256.
- Pip được pin theo wheel bất biến và SHA-256, thay cho URL pip.pyz thay đổi theo thời gian.
- Khôi phục cấu hình SQL RAG có kiểm tra host/schema/port, SELECT read-only và lựa chọn views; mặc định SQL tắt.
- Khôi phục ngữ nghĩa dưới/trên/tối đa/tối thiểu của diện tích và giữ giới hạn qua lượt chat.
- Bỏ khai báo propertyId trùng; kiểm tra UUID đúng cấu trúc và khoảng diện tích hợp lệ.
- Khôi phục bảng ảnh trùng và tiện ích trong trang chi tiết; không bỏ bảng nhận diện ảnh.
- Giữ metadata ảnh qua Backend API, hỗ trợ ảnh Cloudinary được phép, lọc thông tin liên hệ khỏi tiêu đề.
- Script local không ép đường dẫn F: hoặc ép lineage legacy; profile Backend được chọn rõ ràng.
- Default Flyway đọc V20 POI cùng V1–V23; không sửa SQL migration đã công bố.
- Caddy tách Backend/AI/chat/ảnh và không proxy API quản trị nội bộ ra public.
- Bỏ khóa quản trị AI mặc định; khóa đọc và quản trị độc lập, thiếu khóa thì từ chối.

## Bằng chứng kiểm tra

- Frontend build thành công; 65/65 test Node đạt.
- Kiểm tra trình duyệt ẩn với API fixture: điền nhanh địa chỉ, V1.3 số đo, SHAP, đổi V6 và ranh giới lưu lịch sử đạt.
  Script tái hiện: `frontend/e2e/valuation-reconciliation.e2e.mjs`.
- 148 test contract AI/RAG/ảnh trọng tâm: không lỗi, 2 ca bỏ qua vì thiếu tài nguyên tùy chọn.
- Script setup AI mới đã chạy thành công; launcher chuẩn khởi động v6.
- Dự đoán v6 thật kiểm tra riêng cho nhà, đất và căn hộ; không dùng model giả để chứng minh độ chính xác.
- Caddy 2.11.9 adapt/validate thành công. Chưa triển khai TLS hoặc public site.
- MySQL 8.0.43 cô lập trên cổng 13317: áp dụng và validate đủ 23 migration. JPA khởi tạo thành công với schema này.
  Lần thử đầu bằng user DDL hạn chế gặp quyền tạo trigger khi binary log bật; chạy lại trên schema thử mới bằng root của instance thử đạt.
- Backend đóng gói JAR thành công. Unit suite 154 test: 152 đạt, 2 lỗi lúc Java tạo selector loopback.
  Backend khởi động qua JDBC/JPA nhưng dừng tại khởi tạo Java HttpClient do cùng lỗi môi trường.

## Chưa đạt điều kiện merge main

- Bộ AI test đầy đủ đã chạy: 466 ca, 72 failure, 14 error, 7 skip. Không che hoặc xóa các ca lỗi để làm xanh bộ test.
  Nhiều ca cũ giả định tự tìm lại sau đổi tiêu chí, không có bước đồng ý gửi địa chỉ, hoặc interface cũ;
  một số ca yêu cầu weights V1.3 và FAISS chưa có trong runtime định giá.
- Chưa có weights V1.3 để nghiệm thu suy luận thật; chưa có E5/Ollama để nghiệm thu RAG thật.
- Chưa kiểm tra được toàn tuyến browser–Backend–DB–AI vì lỗi Java loopback trên máy thử.
- Cần nghiệm thu lại trên môi trường nhóm, chuyển các test hội thoại cũ sang contract đã chốt và xử lý mọi failure còn hợp lệ trước khi merge.
- Không chạy clean/repair/out-of-order và không tạo lại tài khoản/dữ liệu của database đang dùng.
