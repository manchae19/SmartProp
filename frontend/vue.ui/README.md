# SmartProp Vue

App người dùng/ADMIN. Router: `src/router/index.js`; API: `src/services/api.js`; màn hình: `user/views/`, `admin/views/`; component chung: `src/components/`.

```powershell
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
npm run build
```

Backend local8080, FE dùng `/api/v1` qua proxy. Cấu hình `.env.local` theo `.env.example`, restart Vite sau thay đổi. Production cần HTTPS reverse proxy `/api` cùng domain.

Để giữ đăng nhập sau F5, bật `VITE_ENABLE_REFRESH=true` sau khi Backend đã kiểm tra schema/cookie/CORS và bật refresh. Access token chỉ ở memory; refresh cookie HttpOnly. Không lưu token vào localStorage/sessionStorage.

Home/Listings/Map có điều hướng chung. Wizard ba bước giữ xác nhận vị trí, kiểm tra version và quyền. ADMIN thật ở `/admin/dashboard`. `build/publicAssets.mjs` kiểm soát ảnh/video public, không đưa uploads/tệp thực thi vào đó.

Xem [Frontend](../README.md), [Backend](../../backend/README.md). Test, browser profiles và kết quả kiểm thử chỉ giữ local, không thuộc snapshot Git này.
