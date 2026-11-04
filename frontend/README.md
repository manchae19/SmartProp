# SmartProp Frontend

App Vue3/Vite chính ở ``, chung router cho người dùng và ADMIN. `admin-dashboard/` là scaffold riêng, không phải trang ADMIN đang nối Backend.

Node theo `engines` trong package.json. Tại `frontend/`, chạy `npm ci` rồi `npm run dev`; hoặc cài/chạy trực tiếp theo [hướng dẫn Vue](README.md). Build app chính bằng `npm run build`.

FE tại `http://127.0.0.1:5173`, Backend riêng8080. API mặc định `/api/v1` qua Vite proxy loopback; production cần reverse proxy cùng origin. Cấu hình `.env.local` theo `.env.example`; không đưa secrets Backend vào biến VITE_.

Home V3/Listings/Map dùng điều hướng và bộ lọc chung; giữ chi tiết, ảnh, yêu thích, so sánh, wizard ba bước, báo cáo, tài khoản và quản trị. Quyền cuối cùng do Backend quyết định; API trống/lỗi không fallback tin mẫu.

Access token ở memory. Khi Backend đã kiểm tra schema và bật refresh, đặt `VITE_ENABLE_REFRESH=true` để khôi phục đăng nhập bằng cookie HttpOnly. Lỗi mạng có màn hình thử lại; logout thu hồi session. Không lưu token trong Web Storage/URL.

Nháp wizard tách theo tài khoản/tin; ảnh chưa upload chỉ ở memory, cần chọn lại sau reload. Mutation kiểm tra version và đối chiếu khi mất phản hồi, không tự tạo thêm tin. Bản đồ/geocoding cần mạng, key và điều khoản provider phù hợp.

Test/evidence local không thuộc snapshot Git này. Xem [Backend](../backend/README.md) và [vận hành/backup](../ops/OPERATIONS.md).


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
