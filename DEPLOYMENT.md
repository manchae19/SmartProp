# Hướng dẫn khởi chạy và vận hành SmartProp (Option C - Production v6)

Tài liệu hướng dẫn khởi động toàn bộ hệ thống SmartProp gồm 3 tầng: **FastAPI (AI v6)**, **Spring Boot / MySQL (Backend)** và **Vue 3 / Vite (Frontend)**.

---

## 1. Yêu cầu môi trường

- **Hệ điều hành**: Windows 10/11 x64
- **Python**: 3.10+ (đã có sẵn virtual environment tại `ai-services/.venv`)
- **Node.js**: 18+ và npm (đã có sẵn `node_modules` tại `frontend/vue.ui`)
- **Java / MySQL / Maven**: Đã có sẵn runtime đóng gói cục bộ trong `.scratch/devtools/` (JDK 21, Maven 3.9, MySQL 8.4)

---

## 2. Thứ tự khởi chạy các dịch vụ

Mở **3 cửa sổ PowerShell** tại thư mục gốc dự án (`F:\SmartProp`):

### Terminal 1: Backend Spring Boot & MySQL riêng
Khởi động cơ sở dữ liệu MySQL demo cục bộ (cổng 13306) và Spring Boot API (cổng 8080):
```powershell
cd F:\SmartProp
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/run-demo.py
```
> Chờ đến khi xuất hiện dòng: `Started SmartPropApplication in ... seconds`.  
> Dữ liệu được lưu trữ cách ly tại `backend/var/local-demo/`.

### Terminal 2: AI Service (FastAPI v6)
Khởi động service định giá XGBoost model v6 (cổng 8000):
```powershell
cd F:\SmartProp
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/run_api.py
```
> Chờ đến khi xuất hiện dòng: `Uvicorn running on http://127.0.0.1:8000`.

### Terminal 3: Frontend (Vue 3 + Vite)
Khởi động giao diện người dùng (cổng 5173):
```powershell
cd F:\SmartProp\frontend\vue.ui
npm.cmd run dev
```
> Mở trình duyệt tại: **http://127.0.0.1:5173**

---

## 3. Kiểm tra kết nối tổng thể (Health Check)

Tại một terminal khác, chạy script kiểm tra tự động trạng thái của cả 3 service:
```powershell
cd F:\SmartProp
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/check-demo.py
```

Kết quả mong đợi:
```
OK: AI v6 — HTTP 200
OK: BE và MySQL — HTTP 200
OK: FE → AI — HTTP 200
OK: FE → BE — HTTP 401
Kết nối demo sẵn sàng. HTTP 401 của lịch sử là đúng vì phép kiểm tra không gửi tài khoản/JWT.
```

---

## 4. Luồng người dùng hoàn chỉnh (End-to-End User Flow)

1. **Khám phá bất động sản**:
   - Truy cập **http://127.0.0.1:5173/listings** để xem danh sách bất động sản (tự động tải từ Spring Boot `/api/v1/properties`, hỗ trợ tìm kiếm, lọc theo loại hình, quận, giá).
2. **Xem chi tiết & Định giá**:
   - Chọn một bất động sản hoặc vào **http://127.0.0.1:5173/valuation**.
   - Nhập thông số (loại hình, diện tích, địa bàn, số phòng, số tầng...).
   - Bấm **"Ước tính giá rao"** → Frontend gọi FastAPI (`/api/ai/predict`) chạy XGBoost model v6 để tính giá tham chiếu.
3. **Đăng nhập & Lưu lịch sử**:
   - Vào **http://127.0.0.1:5173/login**, đăng ký tài khoản mới hoặc đăng nhập.
   - Sau khi đăng nhập, tại form định giá bấm **"Lưu kết quả"** → Dữ liệu định giá được lưu bảo mật vào MySQL backend thông qua Spring Boot API (`/api/v1/users/me/valuation-history`).
   - Lịch sử định giá hiển thị ngay bên dưới, hỗ trợ xem lại và xóa lịch sử.

---

## 5. Chạy bộ kiểm thử tự động (Automated Test Suite)

- **Frontend Unit Tests** (10 tests):
  ```powershell
  cd F:\SmartProp\frontend\vue.ui
  npm.cmd test
  ```
- **Frontend E2E Tests** (14 Playwright tests):
  ```powershell
  cd F:\SmartProp\frontend\vue.ui
  npx.cmd playwright test tests/ e2e/
  ```
- **AI Service Tests** (32 tests):
  ```powershell
  cd F:\SmartProp
  .\ai-services\.venv\Scripts\python.exe -m unittest discover -s ai-services/tests -p "test_*.py"
  ```
