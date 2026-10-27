# Định giá và lịch sử theo tài khoản

Ngày 26/10/2026. Giữ API v6 đang dùng; mở rộng BE Spring Boot/MySQL lấy từ `origin/Backend-Huy` tại `ac13ec3`. Frontend vẫn dựa trên `main`, bổ sung đăng nhập thật và lịch sử tại `/valuation`. Các màn hình nghiệp vụ khác của FE hiện tại vẫn cần nối riêng với API BE.

```text
Ước tính: Vue → /api/ai/predict → FastAPI v6
Lưu: Vue + JWT + khóa yêu cầu → Spring Boot → FastAPI tính lại → MySQL
Xem/xóa: Vue + JWT → Spring Boot → lịch sử của đúng tài khoản
```

## Chạy trên máy hiện tại

Giữ API và FE đang chạy. Terminal thứ ba, tại gốc `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/run-demo.py
```

Launcher dùng JDK 21, Maven 3.9.11 và MySQL ZIP đã đặt tại `.scratch/devtools/`. Có thể thay bằng runtime cài riêng qua `JAVA_HOME`, `MAVEN_HOME`, `SMARTPROP_MYSQL_HOME`; trên máy khác phải cài các runtime này trước. Launcher build JAR khi chưa có hoặc mã Java/pom thay đổi. Maven cần mạng cho phụ thuộc chưa có trong cache.

MySQL demo riêng ở `127.0.0.1:13306`, BE ở `127.0.0.1:8080`; chỉ bind localhost. Cổng đang bận làm launcher dừng, không tắt ứng dụng khác. Database `smartprop_local_demo`, dữ liệu và cấu hình riêng lưu tại `backend/var/local-demo/`, được Git bỏ qua. Launcher không đọc `.env`, không dùng MySQL service/database nguồn. Root của instance thử nghiệm riêng dùng cấu hình khởi tạo local; tài khoản kết nối ứng dụng và khóa JWT được sinh riêng, không đưa vào Git. Đây là launcher demo trên máy cá nhân, không dùng để triển khai máy chủ.

Schema demo mới áp dụng SQL V1–V13; lần sau giữ dữ liệu, kiểm tra checksum migration cũ và chỉ áp dụng file mới. SQL đang áp dụng bị sửa hoặc áp dụng dở làm launcher dừng để kiểm tra, không reset database. `Ctrl+C` dừng BE và đúng MySQL demo vừa tạo, giữ dữ liệu trên đĩa. Không chạy hai launcher cùng thư mục dữ liệu. `--check` kiểm tra readiness rồi tự dừng stack; `--port` và `--db-port` đổi cổng nếu cần, khi đó cập nhật `BE_API_TARGET` của Vite tương ứng.

Mở **http://127.0.0.1:5173/login?next=/valuation**, đăng ký tài khoản BUYER/BROKER rồi đăng nhập. Tại `/valuation`, nhập thông tin → ước tính → **Lưu kết quả**. Lịch sử bên dưới hỗ trợ xem và xóa từng kết quả. Đăng xuất xóa token trong bộ nhớ; tải lại tab cần đăng nhập lại vì refresh session mặc định tắt. Dữ liệu lịch sử vẫn ở MySQL.

### Kiểm tra kết nối khi đăng nhập báo 502

Từ gốc repo, chạy lệnh chỉ đọc sau; không cần nhập mật khẩu:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/check-demo.py
```

Lệnh kiểm tra AI 8000, readiness BE/MySQL 8080, FE → AI và FE → BE qua cổng 5173. Đường lịch sử phải trả **401 UNAUTHENTICATED** khi không gửi JWT; đây là dấu hiệu proxy đã tới API bảo vệ, không phải đăng nhập thất bại. Mã thoát 0 nghĩa các kết nối đúng hợp đồng; 1 nghĩa cần xem thành phần chưa sẵn sàng. Lệnh không xác nhận mật khẩu hoặc thao tác lưu của một tài khoản cụ thể, không khởi động/dừng tiến trình và không sửa database.

Ngày 26/10 đã quan sát FE trả 502 khi BE 8080 và MySQL demo chưa chạy. Khởi động lại stack riêng làm yêu cầu đăng nhập tài khoản thử không tồn tại trả 401 từ BE. Chưa xác định nguyên nhân phiên BE cũ dừng. Nếu `run-demo.py` báo cổng bận, dùng lệnh kiểm tra trước; không tắt tiến trình đang chiếm cổng hoặc mở thêm một launcher vào cùng thư mục dữ liệu. Nếu dùng cổng khác, truyền `--frontend-port`, `--ai-port`, `--backend-port` cho lệnh kiểm tra và chỉnh proxy Vite tương ứng.

## Hợp đồng và tính nhất quán

- `POST /api/v1/users/me/valuation-history`: JWT và header `Idempotency-Key` là UUID. Body chỉ nhận trường mô hình có cấu trúc: category, area_sqm, location_feature, ward, rooms, floors, access_type, house_subtype. Không nhận giá, owner, tiêu đề hoặc mô tả do client gửi để lưu.
- Server kiểm tra loại/địa bàn với API được pin, gọi v6 tính lại và lưu snapshot đầu vào, đầu ra được chọn qua whitelist, thời điểm và phiên bản model. Cùng tài khoản + cùng khóa + cùng đầu vào trả lại cùng bản ghi; khác đầu vào trả 409. UNIQUE trong MySQL chống bản ghi trùng ngay cả khi yêu cầu đến đồng thời. Thử lại từ FE giữ nguyên khóa của kết quả đang hiển thị.
- `GET` cùng đường dẫn: phân trang `page=0`, `size=20`, tối đa 100; `GET /{id}` xem snapshot, `DELETE /{id}` xóa. Mọi truy vấn đều lọc theo ID trong JWT, không nhận owner từ URL/body. ID của người khác trả 404.
- Lỗi lịch sử hoặc BE không thay giá đã hiển thị; guest vẫn ước tính trực tiếp qua AI. BE chưa bật model hoặc AI lỗi thì không lưu giá giả. Snapshot đã lưu không tự đổi theo lần train mới và không được dùng làm nhãn huấn luyện.
- Vite proxy `/api/v1` tới `BE_API_TARGET` mặc định 8080; `/api/ai` tới AI 8000. Production cần reverse proxy tương đương. Không sử dụng token giả từ localStorage để xác thực lịch sử.

## Database nguồn của nhóm

Workflow `backend/scripts/run-local.ps1 -Valuation` giữ Flyway/SQL init/seed tắt và Hibernate validate. Khi dùng database nguồn, DBA cần rà soát và áp dụng **V13__valuation_history.sql** theo quy trình triển khai trước khi dùng lịch sử. Không tự chạy migration/reset trên database nguồn trong công việc này. V1–V12 giữ nguyên byte từ nhánh BE. `valuation_history` dành cho snapshot định giá độc lập, không giả tạo `ai_tasks` hoặc `valuation_results` gắn tin/tác vụ trong schema cũ.

## Kiểm chứng

13 kiểm thử BE đã đạt, gồm API/security, retry, MySQL 8.4.13 thật, yêu cầu đồng thời, đọc sau khi mở lại repository, phân tách owner, và luồng HTTP đăng ký/đăng nhập JWT → Spring Boot → FastAPI v6 → lưu/xem/xóa. Toàn bộ V1–V13 đã áp dụng trong schema mới cổng 13317; AI thử nghiệm cổng 18081; stack thử nghiệm đã dừng. Test MySQL/live mặc định bỏ qua nếu không có URL môi trường của schema thử nghiệm đúng prefix; không tự dùng DB nguồn.

Chạy lại kiểm tra có MySQL/model thật bằng runtime local hoặc các biến runtime ở trên:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/check-history-mysql.py
```

Script tạo datadir và schema thử nghiệm mới, áp dụng SQL chỉ tại instance đó, chạy Maven test rồi dừng MySQL/AI do chính nó tạo. Cần trống cổng 13317/18081. Log và datadir thử nghiệm được giữ tại `.scratch/` để truy vết, không vào Git. Launcher demo `--check` cũng đã trả readiness `UP` rồi dừng đúng stack.

14 kiểm thử trình duyệt đạt: 12 luồng định giá hiện có và 2 luồng lịch sử. Hai luồng lịch sử trình duyệt dùng phản hồi BE giả lập; kiểm thử HTTP/live BE ở trên dùng JWT/MySQL/model thật. Không coi kiểm thử kỹ thuật là đánh giá mới về độ chính xác giá.

### Kiểm thử trình duyệt với toàn bộ dịch vụ thật

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/check-history-mysql.py --browser
```

Chế độ này chạy suite BE, đóng gói JAR rồi mở thêm BE riêng cổng **18082** và Vite **15174**, dùng MySQL **13317** và AI v6 **18081** của cùng đợt kiểm tra. Cả bốn cổng phải trống. Cần Node và `npm.cmd ci` tại `frontend/vue.ui` ngoài các runtime Java/MySQL/Python đã nêu. Trên Windows mặc định dùng Edge có sẵn, như suite E2E thường.

Ba kịch bản trong `frontend/vue.ui/e2e-live/history.spec.js` dùng API thật, không giả lập phản hồi: đăng ký/đăng nhập và lưu đủ ba loại tài sản, đọc lại sau đăng xuất/đăng nhập; tài khoản khác không đọc/xóa được snapshot và JWT bị thu hồi sau đăng xuất; đăng nhập sai rồi thử lại và tải lại trang không làm mất lịch sử trong MySQL. So giá server lưu với giá v6 đã hiển thị, không tạo giá mẫu. JWT/mật khẩu chỉ thuộc fixture tổng hợp; không dùng thông tin tài khoản cá nhân.

Chạy qua launcher để tạo schema `smartprop_history_*` và datadir mới. Cấu hình Playwright live chặn chạy trực tiếp khi thiếu dấu hiệu môi trường thử nghiệm. Log BE, báo cáo JSON và dữ liệu thử được giữ trong `.scratch/mysql-history-*`; trace/ảnh lỗi trong `frontend/vue.ui/test-results/`, đều ngoài Git. Sau kiểm tra, các tiến trình do đợt thử tạo được dừng; không dùng `backend/var/local-demo/` hoặc database nguồn. Đây là kiểm chứng tích hợp, không huấn luyện lại hoặc chấm thêm chất lượng giá.

Ngày **27/10/2026**, lệnh `--browser` chạy đạt **13 kiểm thử BE, 0 bỏ qua** và **3 kiểm thử trình duyệt với API thật, không retry/bỏ qua** trên Edge. Công cụ kiểm tra kết nối trả đúng 200/200/200/401 trong stack riêng; khi các dịch vụ demo mặc định tắt, nó trả mã thoát 1 cùng hướng dẫn cho từng thành phần. Chạy trực tiếp cấu hình Playwright live thiếu môi trường thử nghiệm bị chặn trước khi mở dịch vụ. **10 kiểm thử FE và build production cũng đạt**. Model/extractor v6, SQL nguồn và dữ liệu đã khóa không thay đổi.

Sau review cùng ngày, launcher được ghim datasource URL/user trên lệnh JVM, lọc cấu hình Spring/JVM kế thừa và giữ secret trong môi trường riêng. Cleanup độc lập cho từng tiến trình, có timeout/fallback; lỗi dừng AI/BE không bỏ qua MySQL. **6 regression test tổng hợp đạt**; chạy lại 13 BE + 3 live browser với cấu hình Spring xung đột tổng hợp vẫn đạt. Harness build JAR vào `target/` bên trong workspace thử `.scratch/mysql-history-*`, giữ mặc định Maven thông thường ở `backend/target`. [Chi tiết review](PR4_REVIEW.md).
