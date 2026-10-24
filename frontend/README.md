# SmartProp frontend

Ứng dụng chính frontend/vue.ui (Vue3/Vite8), cùng router cho người dùng và /admin. Giao diện đã khôi phục từ SmartProp.zip: router dùng vue.ui/user/views/ và vue.ui/admin/views/. Services legacy.js/legacyPost.js nối dữ liệu API thật vào template/CSS gốc. src/components/business/ giữ các component hỗ trợ ảnh/bằng chứng và phiên bản giao diện trước để tham chiếu.

Node^20.19 hoặc>=22.12. Tại frontend/:

```powershell
npm install
npm run dev
npm test
npm run build
npm run test:browser
```

npm install chỉ cần khi chưa cài dependencies; giữ lockfile hiện có. App chạy http://127.0.0.1:5173, strictPort. Backend phải chạy riêng tại8080. VITE_API_BASE_URL mặc định http://localhost:8080/api/v1; production cùng domain dùng /api/v1 và build lại. Không chép root.env hoặc secrets server vào FE. Preview phải chọn port khớp CORS và dừng dev nếu trùng port.

## Tính năng đang dùng API thật

Home/listings/map, chi tiết/ảnh/POI, wizard đăng tin4 bước, tin của tôi, favorite, reports/evidence; admin dashboard/posts/users/reports/audit; account/preferences/password/logout. Không hiển thị dữ liệu mẫu khi API trống. BUYER không đăng tin, BROKER/ADMIN đăng tin của mình; backend kiểm tra quyền. Route /admin cần ADMIN từ DB.

JWT chỉ giữ memory; refresh cần login lại;401 xóa phiên. Tệp riêng tải bằng Bearer qua Blob URL, không token trong URL. Nháp wizard lưu sessionStorage theo user ID, ảnh chưa upload ở memory và cần chọn lại sau reload. Ghi tin/ảnh cần expectedVersion và xử lý409, gửi duyệt không đồng nghĩa đã được công khai.

13 transport/model tests không thay thế E2E. npm run test:browser dùng Chrome headless/profile tạm: phần guest dùng BE thật chỉ đọc, phần UI mutations dùng fixture tổng hợp được đánh dấu rõ. Luồng trình duyệt với BE/MySQL thật chạy qua backend/scripts/run-isolated-mysql.ps1 (cần FE dev5173 đang chạy và Chrome cài sẵn). Screenshot/kết quả ở vue.ui/test-results/, đã bỏ khỏi Git.

Xem [API contract](../docs/backend-tasks/BACKEND_API_CONTRACT.md) và [kế hoạch backend](../docs/backend-tasks/BACKEND_COMPLETION_AUDIT.md). Map nền OpenStreetMap cần mạng; AI, reset/verify email, inbox/chat chưa triển khai.
