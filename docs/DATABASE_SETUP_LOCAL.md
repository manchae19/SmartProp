# Thiết lập database SmartProp trên máy hiện tại

Hướng dẫn cho `F:\SmartProp`, đối chiếu ngày 27/10/2026 với file `C:\Users\manchae\Downloads\database.zip` do BE cung cấp.

## File ZIP chứa gì

ZIP chứa mã SQL tạo bảng và tài liệu, không chứa bộ cài MySQL Server. Bảy migration V1–V7 trong ZIP khớp SHA-256 với các file cùng tên đang có trong `database/migrations/` của repo. Repo hiện có đủ V1–V13; V13 tạo bảng lịch sử định giá `valuation_history`. Chỉ dùng V1–V7 sẽ thiếu các bảng mà BE hiện tại cần.

ZIP còn có `database.exe`, `docs.exe`, `migrations.exe`, `scripts.exe`, `seeds.exe`. Các tệp này không cần cho việc tạo database và chưa được xác minh nguồn gốc; không chạy chúng. Không cần chép đè thư mục `database/` hiện tại bằng bản ZIP cũ.

## Cách chạy đã kiểm chứng trên máy này

Máy hiện tại đã có JDK, Maven và MySQL ZIP tại `.scratch/devtools/`. Dùng launcher trong repo để tạo hoặc mở lại database local riêng, áp dụng migration còn thiếu và chạy backend. Không phải cài thêm MySQL service hoặc Docker cho cách chạy này.

### Terminal thứ nhất chạy database và backend

Tại gốc dự án:

```powershell
cd F:\SmartProp
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/run-demo.py
```

Lần chạy đầu có thể cần tải thư viện/build BE. Chờ dòng `Started SmartPropApplication` rồi giữ terminal mở. Không thêm `--check` khi muốn dùng ứng dụng: tùy chọn đó kiểm tra xong sẽ tự dừng stack.

- MySQL riêng: `127.0.0.1:13306`.
- Database: `smartprop_local_demo`.
- Backend: `http://127.0.0.1:8080`.
- Dữ liệu và cấu hình được giữ tại `backend/var/local-demo/`, đã bị Git bỏ qua. Chạy lại dùng dữ liệu đã lưu.
- Launcher tự cấu hình tài khoản kết nối và JWT, không cần tạo `.env` cho cách chạy này. Không đưa thư mục dữ liệu hoặc cấu hình riêng lên GitHub.

Launcher kiểm tra checksum migration đã áp dụng, không tự reset database. Nếu báo cổng 8080 hoặc 13306 đang bận, không mở thêm launcher vào cùng thư mục dữ liệu; kiểm tra dịch vụ đang chạy theo phần bên dưới.

### Terminal thứ hai chạy AI

```powershell
cd F:\SmartProp
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/run_api.py
```

Giữ terminal mở, chờ API chạy ở cổng 8000.

### Terminal thứ ba chạy frontend

```powershell
cd F:\SmartProp\frontend\vue.ui
npm.cmd run dev
```

Dependencies frontend đã được cài trên máy này. Nếu thiếu `node_modules`, chạy `npm.cmd ci` tại thư mục trên trước khi mở Vite.

Mở `http://127.0.0.1:5173/login?next=/valuation`, chọn **Đăng ký**, tạo tài khoản rồi đăng nhập. Tại trang định giá, nhập thông tin → **Ước tính giá rao** → **Lưu kết quả**. Lịch sử được lưu trong MySQL theo tài khoản.

## Kiểm tra kết nối và bảng lịch sử

Ở một terminal khác tại gốc repo:

```powershell
cd F:\SmartProp
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/check-demo.py
```

Kết quả đúng là AI 200, BE/MySQL 200, FE → AI 200 và FE → BE 401. Phép kiểm tra lịch sử cố ý không gửi JWT nên 401 là đúng, không phải lỗi đăng nhập. Nếu xuất hiện 502, xem terminal BE và cấu hình proxy; không tự kết luận mật khẩu sai.

Có thể kiểm tra bảng bằng client MySQL đã có trên máy, khi launcher đang chạy:

```powershell
& '.\.scratch\devtools\mysql-8.4.13-winx64\bin\mysql.exe' --no-defaults --protocol=TCP --host=127.0.0.1 --port=13306 --user=root smartprop_local_demo --execute="SHOW TABLES LIKE 'valuation_history';"
```

Lệnh này chỉ đọc tên bảng của instance demo riêng. Cấu hình root này thuộc instance local do launcher tạo, không phải hướng dẫn truy cập MySQL khác hoặc triển khai production.

`Ctrl+C` ở terminal launcher dừng BE và đúng MySQL demo của nó; dữ liệu trên đĩa vẫn được giữ. Sau đó frontend không thể đăng nhập/lưu lịch sử cho đến khi BE/MySQL chạy lại. Tải lại trang cần đăng nhập lại vì JWT hiện chỉ giữ trong bộ nhớ trình duyệt.

## Khi nhóm muốn dùng database nguồn thay cho demo

Database riêng ở trên đã chạy BE thật nhưng tách khỏi database nguồn của nhóm. Nếu BE yêu cầu kết nối schema `smartprop` hoặc MySQL service riêng, cần thống nhất host/cổng, tài khoản và lịch sử migration với người phụ trách BE. Không chạy lại toàn bộ V1–V13 lên một database đã có bảng hoặc bật Flyway theo README trong ZIP mà chưa kiểm tra lịch sử hiện có. Không dùng `schema-reference.sql` thay cho chuỗi migration.

Workflow nguồn hiện tại dùng `.env` riêng và `backend/scripts/run-local.ps1 -Valuation`, với Hibernate chỉ validate, Flyway/SQL init/seed tắt. File ZIP này không có V8–V13 và không cung cấp đầy đủ môi trường cấu hình đó. Cần dùng bộ migration hiện tại của repo và quy trình migration của nhóm khi chuyển sang database nguồn.

[Chi tiết backend và lịch sử định giá](VALUATION_HISTORY.md).
