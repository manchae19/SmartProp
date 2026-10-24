# SmartProp Vue frontend

App Vue3/Vite chính, gồm user/admin. Chạy từ frontend/ theo [hướng dẫn](../README.md). Giao diện ở user/views/ và admin/views/ được khôi phục từ SmartProp.zip. Router src/router/index.js; API src/services/api.js; services legacy.js/legacyPost.js nối dữ liệu thật vào bố cục gốc. Component ảnh/bằng chứng dùng chung ở src/components/business/.

```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
npm test
npm run build
npm run test:browser
```

Không ghi đè .env.local nếu đã có. VITE_API_BASE_URL mặc định http://localhost:8080/api/v1, production /api/v1. CORS phải khớp origin, đổi.env cần restart Vite. JWT chỉ memory; nháp tin sessionStorage theo user, không lưu token. API lỗi không fallback mock.

API và quyền truy cập: [BACKEND_API_CONTRACT.md](../../docs/backend-tasks/BACKEND_API_CONTRACT.md). PDF/retention/AI/email/chat có các giới hạn ghi trong [kế hoạch backend](../../docs/backend-tasks/BACKEND_COMPLETION_AUDIT.md).


Kiểm tra Chrome: test:browser chạy tests/browser-restored.mjs; browser-live.mjs dành cho BE/MySQL thử riêng.
