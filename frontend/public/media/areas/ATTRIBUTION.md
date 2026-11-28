# Khu vực Đà Nẵng — trạng thái bản quyền & cách ly tệp ảnh

Các tệp WebP trong thư mục này (`son-tra.webp`, `hai-chau.webp`, `ngu-hanh-son.webp`, `lien-chieu.webp`, `cam-le.webp`) được cung cấp trước đó từ thư mục local nhưng **chưa xác minh được tác giả gốc, giấy phép sử dụng và vị trí địa lý độc lập**:

| Tệp | Khu vực dự kiến | Nguồn/tác giả | Quyền sử dụng | Trạng thái phân phối (`dist`) & UI |
|---|---|---|---|---|
| `son-tra.webp` | Sơn Trà | Chưa xác minh tác giả gốc | Chưa xác minh giấy phép/quyền sử dụng | **ĐÃ GỠ KHỎI UI & `publicAssets.mjs` (KHÔNG PHÁT HÀNH)** |
| `hai-chau.webp` | Hải Châu | Chưa xác minh tác giả gốc | Chưa xác minh giấy phép/quyền sử dụng | **ĐÃ GỠ KHỎI UI & `publicAssets.mjs` (KHÔNG PHÁT HÀNH)** |
| `ngu-hanh-son.webp` | Ngũ Hành Sơn | Chưa xác minh tác giả gốc | Chưa xác minh giấy phép/quyền sử dụng | **ĐÃ GỠ KHỎI UI & `publicAssets.mjs` (KHÔNG PHÁT HÀNH)** |
| `lien-chieu.webp` | Liên Chiểu | Chưa xác minh tác giả gốc | Chưa xác minh giấy phép/quyền sử dụng | **ĐÃ GỠ KHỎI UI & `publicAssets.mjs` (KHÔNG PHÁT HÀNH)** |
| `cam-le.webp` | Cẩm Lệ | Chưa xác minh tác giả gốc | Chưa xác minh giấy phép/quyền sử dụng | **ĐÃ GỠ KHỎI UI & `publicAssets.mjs` (KHÔNG PHÁT HÀNH)** |

Quy tắc bắt buộc:
- Không tuyên bố các tệp trên có giấy phép hợp lệ khi chưa có bằng chứng gốc.
- Không đưa vào danh sách cho phép `frontend/build/publicAssets.mjs` (không sao chép sang `dist/` và chặn phục vụ qua dev server).
- Giao diện `TopSearchedAreas` sử dụng đồ họa vector biểu trưng trung lập tự chủ của SmartProp (gắn nhãn rõ `"Minh họa biểu trưng · Không phải ảnh thực địa"`), không dùng ảnh chụp chưa rõ quyền sử dụng.
