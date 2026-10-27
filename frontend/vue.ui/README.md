# SmartProp Vue — định giá bằng API v6

Frontend Vue 3/Vite dựa trên `main` commit `7368bc1`, tích hợp trên nhánh `feature/fe-ai-v6`. Form định giá dùng FastAPI; đăng nhập và lưu/xem/xóa lịch sử ở `/valuation` dùng BE Spring Boot/MySQL nhập từ `Backend-Huy`.

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

Tin trong `ListingDetailView.vue` vẫn là **tin minh họa của frontend**, có gắn nhãn; chỉ dự đoán giá được tính bằng model thật. Thông tin có cấu trúc được điền sẵn từ dữ liệu minh họa, người dùng có thể chỉnh để tính lại. Quản lý tin và các màn hình nghiệp vụ khác của FE cần nối riêng với BE. Model, snapshot dữ liệu train v6 và các luật trích đặc trưng giữ nguyên.

## Lịch sử định giá

Chạy BE ở terminal thứ ba từ gốc repo:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/run-demo.py
```

Runtime local hiện có tại `.scratch/devtools/`; máy khác cần JDK 21, Maven và MySQL ZIP trước. Vite proxy `/api/v1` tới `BE_API_TARGET` mặc định `http://127.0.0.1:8080`. Mở `/login?next=/valuation`, đăng ký/đăng nhập tài khoản thật rồi ước tính và chọn **Lưu kết quả**. JWT ở bộ nhớ, không dùng token/role giả trong localStorage; tải lại tab cần đăng nhập lại. Lịch sử vẫn được giữ trong MySQL theo tài khoản. [Hướng dẫn và kiểm chứng](../../docs/VALUATION_HISTORY.md).

## Kiểm thử

```powershell
cd frontend/vue.ui
npm.cmd test
npm.cmd run build
npm.cmd run test:e2e
```

- `npm test`: 10 kiểm thử payload, loại bỏ trường không áp dụng/giá/ID, nhãn địa bàn có dấu, chặn tiêu đề tin, đơn vị giá, HTTP, timeout và hủy request.
- E2E: 14 kiểm thử trên trình duyệt; 3 loại tài sản gọi API v6 thật qua proxy, cộng luồng đăng nhập/lưu/xóa và lỗi lịch sử. Lịch sử được mock trong trình duyệt; suite BE kiểm tra riêng với JWT/MySQL/model thật.
- E2E tự chạy API tại cổng **18080** và Vite tại **15173**, không tái sử dụng dịch vụ đang chạy. Hai cổng này phải trống. Môi trường Python phải có dependencies theo `ai-services/requirements.txt`.
- Kiểm tra toàn luồng lịch sử bằng BE/MySQL/model thật: từ gốc repo chạy `ai-services/.venv/Scripts/python.exe -X utf8 backend/scripts/check-history-mysql.py --browser`. Suite riêng `e2e-live/` có ba kịch bản, dùng Vite 15174, BE 18082, AI 18081 và MySQL 13317 trong schema/datadir mới. Không chạy trực tiếp cấu hình live vào database cá nhân. [Chi tiết và giới hạn](../../docs/VALUATION_HISTORY.md).
- Trên Windows, E2E mặc định dùng Edge có sẵn. Có thể đặt `$env:PLAYWRIGHT_CHANNEL='chrome'` nếu dùng Chrome. Trên Linux/macOS, chạy `npx playwright install chromium` trước lần kiểm thử đầu.
- `test-results/`, `playwright-report/`, `node_modules/`, `dist/` được bỏ qua khỏi Git.

Ngày 23/10/2026: build thành công; **7 kiểm thử FE, 10 kiểm thử trình duyệt và 17 kiểm thử API đều đạt**, bao gồm phát lại 299 dự đoán tham chiếu. Đã xem ảnh giao diện desktop/mobile và xác nhận hai cổng test được đóng sau kiểm tra. Hash của ba model/schema v6 và hai module đặc trưng gốc không thay đổi.

Ngày 26/10/2026: sửa nhãn địa bàn và chặn mã bị tách từ tiêu đề; **19 kiểm thử API, 10 kiểm thử FE và 12 E2E đạt**, 299 dự đoán cũ và giá của case Hòa Xuân trong ảnh vẫn giữ nguyên.

Ngày 27/10/2026: **3 kịch bản `e2e-live` đạt** qua Vue → BE → MySQL/model thật, gồm đủ ba loại tài sản, lịch sử sau đăng nhập lại, quyền sở hữu và thu hồi phiên. Không giả lập phản hồi API trong suite này. Harness cũng chạy đạt 13 kiểm thử BE; 10 kiểm thử FE và build đạt. Suite E2E thường 14 kịch bản là kết quả đã chốt trước đó, không cộng chung hoặc gọi cả hai suite là cùng một lần chạy.

Giới hạn chất lượng model xem [MODEL_V6.md](../../docs/MODEL_V6.md). Kết quả là **giá rao ước tính để tham khảo**, chưa phải giá giao dịch hoặc thẩm định thực địa.

Khi đăng nhập báo 502, từ gốc repo chạy `ai-services/.venv/Scripts/python.exe -X utf8 backend/scripts/check-demo.py` để kiểm tra riêng BE/MySQL và các proxy. Công cụ chỉ đọc, không hỏi mật khẩu hoặc dừng tiến trình đang chiếm cổng.
