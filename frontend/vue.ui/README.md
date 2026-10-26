# SmartProp Vue — định giá bằng API v6

Frontend Vue 3/Vite được lấy từ `origin/main` commit `7368bc1` và tích hợp trên nhánh `feature/fe-ai-v6`. Form định giá dùng API FastAPI hiện có, chưa cần BE nghiệp vụ riêng cho demo này.

## Chạy tại máy

Đã kiểm tra với Node.js 24.18.1, npm 11.16.0 và môi trường Python của SmartProp. Tại gốc repo, terminal thứ nhất:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 .\ai-services\run_api.py
```

Terminal thứ hai:

```powershell
cd frontend/vue.ui
npm.cmd ci
npm.cmd run dev
```

Giữ cả hai terminal mở. Truy cập:

- **http://127.0.0.1:5173/valuation** — form định giá riêng, nhập thông tin tùy ý trong phạm vi model.
- **http://127.0.0.1:5173/home#valuation** — form ở mục Định giá trên trang chủ.
- **http://127.0.0.1:5173/listing/1** — nhà minh họa; `/listing/2` là căn hộ, `/listing/3` là đất.

Nhập/chỉnh thông tin rồi bấm **Ước tính giá rao**. Địa bàn lấy từ model cho đúng loại tài sản; phòng/tầng/lối vào/subtype chỉ hiện khi phù hợp. Các thông tin tùy chọn chưa rõ được để thiếu, không điền số 0 hoặc giá trị trung bình.

Tên địa bàn được hiển thị có dấu theo `location_labels` do API cung cấp; mã gửi tới model giữ nguyên. Dropdown tách quận/huyện cũ và địa bàn mở rộng, không đưa tiêu đề tin bị tách sai vào lựa chọn. **Phường/xã theo tin** là thông tin bổ sung độc lập, để trống khi chưa rõ; không tự điền từ địa bàn đang chọn. Khi cập nhật phần này cần khởi động lại FastAPI rồi tải lại FE. [Chi tiết lỗi và cách sửa](../../docs/LOCATION_LABELS.md).

## Luồng kết nối

```text
Trình duyệt Vue → /api/ai/model/options hoặc /api/ai/predict
               → Vite proxy → FastAPI http://127.0.0.1:8000
               → XGBoost v6/all → kết quả giá rao (VND)
```

Vite dev và preview có cùng cấu hình proxy, nên không cần sửa CORS của AI service. Nếu đổi cổng API, chép `.env.example` thành `.env.local`, sửa `AI_API_TARGET` và khởi động lại Vite. Biến này được đọc bởi proxy phía server, không đưa địa chỉ API vào mã client.

`npm.cmd run build` tạo `dist/`. Dùng `npm.cmd run preview` để thử tại **http://127.0.0.1:4173/valuation**, đồng thời giữ API chạy. Khi triển khai bản static, server hosting cần cấu hình reverse proxy `/api/ai/*` tương ứng; cấu hình Vite chỉ phục vụ dev/preview cục bộ.

## Thông tin được gửi và hiển thị

Request chỉ có `category`, `area_sqm`, `location_feature` và các trường tùy chọn hợp lệ `ward`, `rooms`, `floors`, `access_type`, `house_subtype`. Số được gửi bằng JSON number. Giá tin đăng, ID tin, nội dung/ảnh và các giá trị so sánh không vào request.

Kết quả hiển thị tổng giá theo tỷ/triệu đồng, giá VND đầy đủ, các giá trị model thực sự dùng, thông tin còn thiếu và cảnh báo. Đã bỏ các khoảng giá, kết luận “giá hợp lý” và tỷ lệ đóng góp mẫu trong khối định giá chi tiết tin. Không tạo khoảng tin cậy hoặc giá dự phòng khi API lỗi.

Đổi đầu vào hoặc chuyển tin sẽ xóa kết quả cũ và hủy yêu cầu đang chờ; phản hồi cũ không được ghi lên form mới. Mỗi yêu cầu có timeout 12 giây. Mất kết nối/đầu vào sai có thông báo và cho phép thử lại.

Tin trong `ListingDetailView.vue` vẫn là **tin minh họa của frontend**, có gắn nhãn; chỉ dự đoán giá được tính bằng model thật. Thông tin có cấu trúc được điền sẵn từ dữ liệu minh họa, người dùng có thể chỉnh để tính lại. Các luồng đăng nhập, quản lý tin và dữ liệu nghiệp vụ khác của FE chưa được nối với BE trong đợt này. Model, dữ liệu train và các luật trích đặc trưng giữ nguyên.

## Kiểm thử

```powershell
cd frontend/vue.ui
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e
```

- `npm test`: 10 kiểm thử payload, loại bỏ trường không áp dụng/giá/ID, nhãn địa bàn có dấu, chặn tiêu đề tin, đơn vị giá, HTTP, timeout và hủy request.
- E2E: 12 kiểm thử trên trình duyệt; 3 loại tài sản gọi API v6 thật qua proxy và đối chiếu với FastAPI trực tiếp, form mobile/desktop, lỗi kết nối, retry, nhập sai, phản hồi chậm và nhãn địa bàn có dấu giữ nguyên mã/giá.
- E2E tự chạy API tại cổng **18080** và Vite tại **15173**, không tái sử dụng dịch vụ đang chạy. Hai cổng này phải trống. Môi trường Python phải có dependencies theo `ai-services/requirements.txt`.
- Trên Windows, E2E mặc định dùng Edge có sẵn. Có thể đặt `$env:PLAYWRIGHT_CHANNEL='chrome'` nếu dùng Chrome. Trên Linux/macOS, chạy `npx playwright install chromium` trước lần kiểm thử đầu.
- `test-results/`, `playwright-report/`, `node_modules/`, `dist/` được bỏ qua khỏi Git.

Ngày 23/10/2026: build thành công; **7 kiểm thử FE, 10 kiểm thử trình duyệt và 17 kiểm thử API đều đạt**, bao gồm phát lại 299 dự đoán tham chiếu. Đã xem ảnh giao diện desktop/mobile và xác nhận hai cổng test được đóng sau kiểm tra. Hash của ba model/schema v6 và hai module đặc trưng gốc không thay đổi.

Ngày 26/10/2026: sửa nhãn địa bàn và chặn mã bị tách từ tiêu đề; **19 kiểm thử API, 10 kiểm thử FE và 12 E2E đạt**, 299 dự đoán cũ và giá của case Hòa Xuân trong ảnh vẫn giữ nguyên.

Giới hạn chất lượng model xem [MODEL_V6.md](../../docs/MODEL_V6.md). Kết quả là **giá rao ước tính để tham khảo**, chưa phải giá giao dịch hoặc thẩm định thực địa.
