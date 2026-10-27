# SmartProp Frontend

App Vue3/Vite chính ở `vue.ui/`, chung router cho người dùng và ADMIN. `vue.ui/admin-dashboard/` là scaffold riêng, không phải trang ADMIN đang nối Backend.

Node theo `engines` trong package.json. Tại `frontend/`, chạy `npm ci` rồi `npm run dev`; hoặc cài/chạy trực tiếp theo [hướng dẫn Vue](vue.ui/README.md). Build app chính bằng `npm run build`.

FE tại `http://127.0.0.1:5173`, Backend riêng8080. API mặc định `/api/v1` qua Vite proxy loopback; production cần reverse proxy cùng origin. Cấu hình `vue.ui/.env.local` theo `.env.example`; không đưa secrets Backend vào biến VITE_.

Home V3/Listings/Map dùng điều hướng và bộ lọc chung; giữ chi tiết, ảnh, yêu thích, so sánh, wizard ba bước, báo cáo, tài khoản và quản trị. Quyền cuối cùng do Backend quyết định; API trống/lỗi không fallback tin mẫu.

Access token ở memory. Khi Backend đã kiểm tra schema và bật refresh, đặt `VITE_ENABLE_REFRESH=true` để khôi phục đăng nhập bằng cookie HttpOnly. Lỗi mạng có màn hình thử lại; logout thu hồi session. Không lưu token trong Web Storage/URL.

Nháp wizard tách theo tài khoản/tin; ảnh chưa upload chỉ ở memory, cần chọn lại sau reload. Mutation kiểm tra version và đối chiếu khi mất phản hồi, không tự tạo thêm tin. Bản đồ/geocoding cần mạng, key và điều khoản provider phù hợp.

Test/evidence local không thuộc snapshot Git này. Xem [Backend](../backend/README.md) và [vận hành/backup](../ops/OPERATIONS.md).
