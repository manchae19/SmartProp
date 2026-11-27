# HANDOFF CHO PR #37 (`feature/news-ui-refresh`) — XỬ LÝ DỮ LIỆU THỊ TRƯỜNG HARDCODED TRÊN `/market` (`WP03-F02`)

- **Branch sinh tài liệu**: `fix/research-evidence-access-control` (Phase 0 — không chạm vào các file thuộc PR #37 để tránh xung đột merge).
- **Baseline đã rà soát**: `1f36205fbff5ef04f43c27af83c1694d500a9d61` (`origin/main`).
- **Mục tiêu**: Bàn giao chính xác vị trí mã nguồn, nguyên nhân gốc và đặc tả hành vi UI cần chỉnh sửa trên nhánh PR #37 (hoặc PR kế tiếp ngay sau khi PR #37 merge) nhằm loại bỏ các số liệu giả lập chưa có bằng chứng đang hiển thị trên `/market` và `/market/:district`.

---

## 1. Danh sách File & Dòng mã nguồn liên quan (`origin/main` @ `1f36205`)

| File | Dòng mã nguồn | Vấn đề cụ thể |
|---|---|---|
| `frontend/src/features/market/marketData.js` | `L4–L297` | Định nghĩa `DISTRICT_PROFILES` cho **6 quận** (thiếu huyện **Hòa Vang**), chứa các con số thị trường viết cứng: `viewsCount`, `activeListingsCount`, `macro.avgPricePerM2`, `macro.priceGrowthYoY`, `macro.liquidityRating`, `aiInsights` (cam kết biên độ tăng giá `10 - 15%/năm`, thời gian thanh khoản `30 - 45 ngày`), và chuỗi 12 quý `priceHistory` (`Q1/24` đến `Q4/26`). |
| `frontend/src/features/market/marketData.js` | `L299–L308` | Hàm `getDistrictProfile(districtName)` fallback mọi tên quận không khớp (bao gồm **`Hòa Vang` / `hoa-vang`**) về **`DISTRICT_PROFILES['Sơn Trà']`** (`L307`). |
| `frontend/src/features/market/MarketInsightsView.jsx` | `L56–L63` | `getLatestHousePrice()` và `getLatestApartmentPrice()` lấy phần tử cuối mảng hằng số `priceHistory` hoặc fallback cứng `"145,0 triệu/m²"` / `"62,0 triệu/m²"`. |
| `frontend/src/features/market/MarketInsightsView.jsx` | `L309–L336`, `L345`, `L361`, `L460–L509` | Hiển thị `avgPricePerM2`, `priceGrowthYoY` (`▲ +9.4% so với cùng kỳ`), `liquidityRating` (`Rất cao 94/100 · Cập nhật Quý 4/2026`), và gắn nhãn sai sự thật **`"6 quận trọng điểm · Dữ liệu chuẩn hóa & AI Valuation V1.3"`** (`L345`). |
| `frontend/src/features/market/MarketInsightsView.jsx` | `L702–L775` | Render `<PriceTrendChart history={view.currentDistrict.priceHistory} />` và khối nhận định gắn huy hiệu **`"SMARTPROP AI MARKET INTELLIGENCE · MODEL V1.3"`** (`L711`) cho văn bản tĩnh viết tay trong `aiInsights`. |
| `frontend/src/features/market/PriceTrendChart.jsx` | `L64–L80`, `L194–L208`, `L304` | Vẽ đường biểu đồ mượt 12 quý từ mảng tĩnh và gắn nhãn tooltip **`"Chuẩn hóa"`** (`L304`) như thể được tính từ dữ liệu lịch sử thực. |
| `frontend/src/features/market/TopSearchedAreas.jsx` | `L28–L37`, `L109–L134`, `L163–L182` | Xếp hạng khu vực theo `viewsCount` tĩnh (`37.637 lượt xem`), `activeListingsCount` tĩnh (`1.674 bất động sản đang bán`), `avgPricePerM2` và `priceGrowthYoY` tĩnh; bỏ qua `Hòa Vang`. |
| `frontend/src/features/market/MarketAnalyticsView.jsx` | `L97–L111` | Hiển thị công khai tùy chọn nguồn `TINIX_RESEARCH` trong `<select>` và checkbox `"Bao gồm dữ liệu nghiên cứu TiniX (CC BY-NC 4.0)"` cho mọi khách truy cập không có quyền, khiến người dùng bấm vào sẽ nhận lỗi `403 Forbidden` từ backend sau khi Phase 0 khóa quyền truy cập. |

---

## 2. Nguyên nhân gốc (Root Cause) & Hành vi hiện tại

1. **Tách rời giữa UI chính `/market` và API thật `/api/v1/properties/market-analytics`**: Backend đã có endpoint tổng hợp dữ liệu thật (`MarketAnalyticsController`), nhưng route `/market` trên Header lại đọc hoàn toàn từ bộ hằng số tĩnh `marketData.js` (chỉ gọi `/api/v1/properties?district=...` để lấy 6 thẻ tin đăng ở cuối trang).
2. **Gán nhãn sai nguồn gốc mô hình AI**: Mô hình `XGBoost V1.3` chỉ thực hiện định giá từng bất động sản dựa trên 22 đặc trưng vật lý/vị trí, **không sinh ra** dự báo tăng giá YoY, chỉ số thanh khoản `0–100`, hay đường xu hướng quý `Q1/24–Q4/26`. Việc gắn nhãn `"AI Valuation V1.3"` lên dữ liệu tĩnh làm người dùng hiểu sai nghiêm trọng năng lực hệ thống.
3. **Lỗi ánh xạ địa giới hành chính Đà Nẵng**: Thiếu huyện `Hòa Vang` (1 trong 7 đơn vị hành chính cấp quận/huyện của Đà Nẵng trong toàn bộ hệ thống SmartProp) và dùng `return DISTRICT_PROFILES['Sơn Trà']` làm giá trị mặc định khi không tìm thấy slug, dẫn tới `/market/hoa-vang` hiển thị toàn bộ thông tin của Quận Sơn Trà (kèm truy vấn tin đăng `district=Sơn Trà` tại `L75-76`!).

---

## 3. Phân loại chi tiết dữ liệu trong `marketData.js`: Bỏ hẳn vs Giữ có ghi nguồn

| Trường dữ liệu hiện tại | Quyết định bắt buộc | Hướng xử lý trên UI |
|---|---|---|
| `macro.avgPricePerM2`, `latestHousePrice`, `latestApartmentPrice` (hằng số tĩnh) | **BỎ HẲN HẰNG SỐ TĨNH** | Thay bằng số liệu `medianPricePerSqm` thực tế lấy từ `GET /api/v1/properties/market-analytics` (phân tách riêng từng `propertyType`: `LAND`, `HOUSE`, `APARTMENT`, `VILLA`), ghi rõ cơ sở **"Trung vị giá rao bán (asking price)"** và cỡ mẫu `n`. |
| `macro.priceGrowthYoY` (`+9.4%`, `+14.2%`...) | **BỎ HẲN** | Hệ thống hiện chưa có chuỗi quan sát lịch sử công khai đủ điều kiện kiểm định để tính tăng trưởng YoY (`NO_FORECAST`). Không thay bằng số giả khác. |
| `macro.liquidityRating` (`94/100`, `Cập nhật Quý 4/2026`) | **BỎ HẲN** | SmartProp không có dữ liệu giao dịch chốt công chứng hoặc thời gian hấp thụ thực tế để chấm điểm thanh khoản. |
| `viewsCount` (`37.637`), `activeListingsCount` (`1.674`) tĩnh | **BỎ HẲN HẰNG SỐ TĨNH** | Số lượng tin đang bán chỉ được lấy từ `count` thực tế của API (`/market-analytics` hoặc `/market-summary`); bỏ nhãn `"lượt xem"` nếu chưa nối bộ đếm telemetry thật. |
| `priceHistory` (`Q1/24–Q4/26`, 12 quý tĩnh) & nhãn `"Chuẩn hóa"` | **BỎ HẲN MẢNG GIẢ LẬP** | Ở chế độ công khai (`includeResearch=false`), dữ liệu hiện không có chuỗi thời gian (`temporalStatus = "NOT_REQUESTED"` hoặc `"INSUFFICIENT_DATA"`). Không vẽ đường xu hướng từ mảng mẫu; hiển thị trạng thái chưa đủ lịch sử thời gian công khai hoặc thay bằng biểu đồ phân bố khoảng giá/loại hình thực tế (`priceBands`, `byPropertyType`). |
| Huy hiệu `"AI Valuation V1.3"` trên trang `/market` & khối `aiInsights` dự báo `10–15%/năm` | **BỎ NHÃN V1.3 & BỎ DỰ BÁO LỢI NHUẬN** | Đổi thành mô tả địa lý - hạ tầng trung lập (ghi rõ *"Thông tin tổng quan địa bàn tham khảo, không phải dự báo giá hay khuyến nghị đầu tư từ mô hình AI V1.3"*). |
| `name`, `slug`, `lat`, `lon`, `zoom`, mô tả vị trí hành chính & danh mục hạ tầng công khai | **CÓ THỂ GIỮ** (bổ sung đủ **7 quận/huyện** gồm `Hòa Vang`) | Ghi rõ nguồn quy hoạch/địa lý hành chính tĩnh; không trộn lẫn với chỉ số giá thị trường. |

---

## 4. Quy tắc bắt buộc cho Quyền dữ liệu nghiên cứu, `Hòa Vang` & Empty State khi thiếu dữ liệu thật

1. **Ẩn hoàn toàn tùy chọn dữ liệu nghiên cứu (`TINIX_RESEARCH`) với người dùng không có quyền (`MarketAnalyticsView.jsx:L97–L111`)**:
   - Kể từ Phase 0, backend `GET /api/v1/properties/market-analytics` chặn cứng `includeResearch=true` và `source=TINIX_RESEARCH` bằng `403 Forbidden` trừ khi phiên đăng nhập là **`ADMIN` đang hoạt động (`ACTIVE`)** VÀ cờ cấu hình máy chủ được bật.
   - Trên `MarketAnalyticsView.jsx` (đang nằm trong phạm vi PR #37):
     - **Không hiển thị** lựa chọn `TINIX_RESEARCH` trong dropdown `Nguồn` và **không hiển thị** checkbox `"Bao gồm dữ liệu nghiên cứu TiniX"` đối với khách ẩn danh, `BUYER`, `BROKER`, hoặc khi máy chủ chưa bật chế độ nghiên cứu.
     - **Không để UI có sẵn checkbox gửi request chắc chắn bị `403`**; nếu trạng thái phiên thay đổi (đăng xuất hoặc không đủ quyền), tự động reset `includeResearch = false` và `source = 'ALL'`.
2. **Không bao giờ fallback `Hòa Vang` sang `Sơn Trà`**:
   - Bổ sung đầy đủ cấu hình địa lý hành chính của **`Hòa Vang`** (`slug: 'hoa-vang'`, `name: 'Huyện Hòa Vang'`, `shortName: 'Hòa Vang'`, tọa độ trung tâm hành chính Hòa Vang) vào danh sách **7 quận/huyện**.
   - Nếu URL `/market/:slug` nhận một `slug` không tồn tại trong 7 quận/huyện Đà Nẵng: `getDistrictProfile(slug)` phải trả `null` và UI hiển thị **trạng thái không tìm thấy khu vực** (kèm nút quay lại danh sách 7 quận/huyện), tuyệt đối không âm thầm hiển thị `Sơn Trà`.
3. **Không tự tạo thống kê thị trường & Hiển thị Empty / Insufficient Sample State trung thực**:
   - Khi gọi API thật cho một `(district, propertyType)` mà `dataStatus === 'INSUFFICIENT_DATA'` hoặc `count === 0`:
     - Hiển thị rõ: *"Chưa đủ mẫu tin rao công khai hợp lệ (`n = <count>`, ngưỡng tối thiểu `<minSample>`) để tính trung vị đơn giá."*
     - Không tự tạo trung vị/trung bình, không điền giá mặc định (`"145,0 triệu/m²"`), không nội suy từ quận bên cạnh, không vẽ biểu đồ mẫu hay gán mác `"AI Valuation V1.3"`.

---

## 5. Hợp đồng tích hợp API dự kiến (Tương thích ngay với Phase 0 & hậu WP-03)

- **Endpoint công khai an toàn**:
  `GET /api/v1/properties/market-analytics?district=<tên quận>&propertyType=<LAND|HOUSE|APARTMENT|VILLA>&includeResearch=false`
  *(Sử dụng helper sẵn có `loadMarketAnalytics` trong `frontend/src/features/market/marketAnalytics.js` — truyền `includeResearch: false`, không bao giờ truyền `includeResearch: true` hay `source: 'TINIX_RESEARCH'` trên trang công khai `/market`).*
- **Các trường đọc an toàn**:
  - `data.overall.count`, `data.overall.dataStatus`, `data.overall.medianPricePerSqm`, `data.overall.medianAskingPriceVnd`
  - `data.byDistrict`, `data.byPropertyType`, `data.priceBands`, `data.areaBands`
  - `data.meta.minSample`, `data.meta.disclaimer`, `data.meta.dataQualityWarnings`
  - Khi WP-03 triển khai đầy đủ, các trường mở rộng (`p25PricePerSqm`, `p75PricePerSqm`, `latestObservedDate`, `sampleSupportTier`) sẽ được bổ sung theo hướng additive, không phá vỡ cấu trúc hiện tại.

---

## 6. Kiểm thử hồi quy bắt buộc khi PR #37 / WP-03 UI cập nhật

1. **Unit test (`node --test`)**:
   - Kiểm tra danh sách khu vực có đủ **7 quận/huyện** (bao gồm `Hòa Vang` / `hoa-vang`).
   - Kiểm tra `getDistrictProfile('hoa-vang')` trả đúng `Hòa Vang`, và `getDistrictProfile('khong-ton-tai')` trả `null` (không trả `Sơn Trà`).
   - Kiểm tra không còn bất kỳ chuỗi/trường dự báo tăng trưởng tĩnh (`priceGrowthYoY`, `liquidityRating`, `priceHistory` giả lập) hay nhãn `"AI Valuation V1.3"` gắn lên dữ liệu thống kê thị trường.
2. **Playwright E2E**:
   - Mở `/market/hoa-vang` (ẩn danh): tiêu đề, bản đồ và truy vấn `/api/v1/properties?district=Hòa+Vang` khớp đúng Hòa Vang; các ô thiếu mẫu hiển thị trạng thái `Chưa đủ mẫu` thay vì số giả; `0` request gửi `includeResearch=true`.
