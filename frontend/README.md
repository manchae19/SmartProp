# SmartProp Frontend — React + Vite

Chạy tại thư mục frontend:

```powershell
npm ci
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Mở http://127.0.0.1:5173/home. Backend giữ cổng 8080, proxy /api/v1 không đổi. Google Login giữ nguyên callback và cấu hình Backend. Trang quản trị nằm tại /admin/dashboard trong cùng ứng dụng.

Cấu trúc: src/app (entry/router), src/features (15 module nghiệp vụ), src/shared/components (UI/layout), src/shared/hooks, src/shared/lib, src/shared/state, src/shared/routing, src/styles và src/assets. State helpers dùng React useSyncExternalStore để tái sử dụng logic API/form hiện có; không có Vue runtime.

Giữ nguyên .env/.env.local và biến VITE_ đang dùng; không đưa secrets Backend vào Frontend. Dịch vụ Python/AI trong integrations có cấu hình riêng và được giữ nguyên.

Đã chạy một lần build React thành công. Không chạy test suite trong đợt migration; cần kiểm tra thủ công các luồng sau chuyển đổi.
