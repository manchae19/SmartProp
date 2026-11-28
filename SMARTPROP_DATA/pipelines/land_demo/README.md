# Dữ liệu demo đất Hòa Xuân (công cụ đất trong chatbot SmartProp)

Phiên bản hiện tại: `HX-LAND-DEMO-20261126`.

## Bố cục

| Thư mục | Nội dung | Ai ghi |
|---|---|---|
| `raw/land_demo_hoa_xuan/<ver>/outputs/` | Bản sao **không sửa** của `chatbot-test/outputs` (Guland, ô quy hoạch, giá đường, dự án, `demo-policy-20261126.json`) | Chỉ sao chép |
| `raw/land_demo_hoa_xuan/<ver>/flood/` | Danh mục nguy cơ ngập, ánh xạ địa bàn, GeoJSON tuyến tham chiếu | Chỉ sao chép |
| `processed/land_demo_hoa_xuan/<ver>/` | `normalized/`, `relations/` (gồm `id-map.json` mã nguồn ↔ UUID), `prices/`, `flood/`, `export/`, `quarantine.json`, `manifest.json` (sha256 từng tệp nguồn) | `build_land_demo.py` |
| `demo/config/land-demo-rules-<ver>.json` | Quy tắc trình diễn (loại đất, sổ, thu hồi, ngập). **Tách riêng khỏi bằng chứng nguồn** | `build_land_demo.py` |
| `reports/LAND_DEMO_<ver>.{json,md}` | Thống kê, số bản ghi cách ly | `build_land_demo.py` |

Ứng dụng (`ai-services/app/land`) đọc trực tiếp bản `raw`, qua cùng một engine. Bản `processed` là bản kiểm toán/xuất của đúng những gì ứng dụng hiển thị, không phải nguồn dữ liệu thứ hai. UUID đất là UUIDv5, sinh dưới namespace riêng `https://smartprop.local/land-demo/hoa-xuan`, nên không bao giờ trùng UUID tin đăng (`properties`).

## Dựng lại dữ liệu đã xử lý

```powershell
cd D:\C2SE.01CMU\code\SmartProp
.\.scratch\rag-venv\Scripts\python.exe -X utf8 SMARTPROP_DATA\pipelines\land_demo\build_land_demo.py --version HX-LAND-DEMO-20261126
```

## Cập nhật dữ liệu (phiên bản mới)

1. Tạo `raw/land_demo_hoa_xuan/<ver-mới>/`, sao chép `outputs/` và `flood/` mới vào. Không sửa thư mục phiên bản cũ.
2. Chạy pipeline với `--version <ver-mới>`, rồi đọc `reports/LAND_DEMO_<ver-mới>.md` và `quarantine.json`.
3. Đặt biến `SMARTPROP_LAND_DATA_VERSION=<ver-mới>` cho dịch vụ chat. Có thể đặt thêm `SMARTPROP_LAND_DATA_DIR` nếu dữ liệu nằm ngoài repo.
4. Khởi động lại dịch vụ chat sau khi backend đã UP. Chạy `ai-services/tests/test_land_demo.py` và bộ 194 ca.
5. Muốn quay lại thì đặt lại biến phiên bản cũ rồi khởi động lại.

## Chuyển từ demo sang dữ liệu thật

Quy tắc demo nằm ở `demo/config/land-demo-rules-<ver>.json` và được áp dụng trong `ai-services/app/land/demo_documents.py`. Mọi giá trị demo đều mang cờ `demo`/`isDemoAssumption`, và giao diện gắn nhãn "Kịch bản demo".

1. Khi có giấy tờ, quy hoạch hoặc ngập đã xác minh, thêm chúng làm nguồn (kèm URL, ngày, đơn vị) trong `raw/<ver-mới>`. Không ghi đè giá trị demo.
2. Trong `demo_documents.py`, ưu tiên giá trị nguồn đã xác minh. Chỉ dùng quy tắc demo khi chưa có nguồn, hoặc tắt hẳn quy tắc demo cho phiên bản đó.
3. Với giá: loại `SIMULATED_DEMO` và `ROAD_ASKING_ESTIMATE` phải được thay bằng giá giao dịch/chào bán có nguồn. Nhãn loại giá vẫn giữ nguyên.
4. Cập nhật kỳ vọng trong các test `DemoRule*` tương ứng.

Không được ghi rằng các giả định demo đã được cơ quan nào xác nhận.
