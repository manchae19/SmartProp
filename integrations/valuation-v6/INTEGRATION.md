# SmartProp: tích hợp bundle giá v6 nguyên bản

Nguồn: `SmartProp-develop-binh.zip`, SHA-256 và từng file gốc trong `SOURCE_MANIFEST.json`. Ba model XGBoost, run `b4b1339d3f35857e`, configuration `all`. Tất cả file được liệt kê trong manifest giữ byte nguyên bản. `requirements-windows.lock` và tài liệu này là phần vận hành mới, không thay thuật toán. `ai-services/` hiện có không thay đổi.

## Chạy local trên Windows amd64

Từ repository root, Java 21/JAVA_HOME và backend đã build:

```powershell
# Chỉ lần đầu: Python riêng và các wheel có hash; không cài global/PATH.
powershell -NoProfile -File backend/scripts/setup-valuation-runtime.ps1
# Terminal 1: kiểm hash bundle rồi chạy model, chỉ bind 127.0.0.1:8000.
powershell -NoProfile -File backend/scripts/run-valuation.ps1
# Terminal 2: bật bridge có phân quyền; giữ Flyway/seed/DDL write tắt.
powershell -NoProfile -File backend/scripts/run-local.ps1 -Transport NIO2 -Valuation
# Terminal 3: FE như bình thường.
cd frontend/vue.ui
npm run dev -- --host 127.0.0.1
```

Mặc định `app.valuation.enabled=false`; launcher BE phải có `-Valuation` để bật. Chỉ model chạy ở port8000 không làm bridge tự bật. Dừng model không ngăn đăng tin. Không cần migration/SMTP/Google key mới cho panel này. Google Maps dùng cấu hình sẵn có riêng.

Runtime nằm trong `backend/var/valuation-v6-runtime` (đã ignore). Setup kiểm hash CPython3.14.8 embeddable, pip zipapp và tất cả wheel Windows được khóa, cài qua `--target`, không sửa Python hệ thống. Nếu URL pip zipapp cập nhật và hash không khớp, setup dừng; cần xác minh bản mới trước khi cập nhật hash, không bỏ kiểm tra.

Nguồn runtime: [Python release](https://www.python.org/downloads/release/python-3148/), [Windows embeddable distribution](https://docs.python.org/3/using/windows.html), [pip standalone zip application](https://pip.pypa.io/en/stable/installation/#standalone-zip-application).

## Phạm vi và dữ liệu

- Chỉ giá rao tham khảo cho tin **SALE**, HOUSE/VILLA/LAND/APARTMENT, 20–1000m². Không phải giá giao dịch hoặc thẩm định.
- Danh sách khu vực là giao của vocabulary theo category với bảy quận/huyện chuẩn của bộ dữ liệu Đà Nẵng. Địa bàn mới chưa khớp phải do người đăng xác nhận khu vực tương ứng; không chọn sẵn địa bàn đầu tiên. Alias nội bộ `new_unit:*` không đưa ra UI.
- BE gửi loại, diện tích, khu vực, optional ward/rooms và nội dung tiêu đề/mô tả; không gửi trường giá chào, owner/contact/email/phone/token/tọa độ. Tiêu đề/mô tả là nội dung người dùng nhập, có thể tự chứa thông tin cá nhân; chúng chỉ gửi tới model loopback và không ghi request body vào log. Model không dùng Google tọa độ.
- Mô tả >8000 ký tự: chỉ đoạn đầu dùng suy luận, có cảnh báo; bản tin giữ nguyên tối đa20000. Số phòng0 được coi là chưa khai báo, không gán giả. Frozen extractor có thể suy luận đặc trưng từ nội dung, phản ánh trong `featuresUsed`.
- ZIP **không có CSV/raw training dataset**; không import tin huấn luyện vào database, không training/crawler. Không có weights YOLO/Siamese hoặc SHAP contributions.
- 299 parity cases xác nhận tái lập prediction đã lưu, **không phải** bộ đánh giá độc lập mới. Metrics đi kèm của tác giả: 2214 train/299 development validation, MAPE khoảng36.13%, MAE khoảng2457 triệu VND. Cần bộ dữ liệu độc lập trước khi dùng cho quyết định kinh doanh.

## Kiểm thử

```powershell
backend/var/valuation-v6-runtime/python/python.exe -X utf8 -m unittest discover -s integrations/valuation-v6/tests -p test_api_v6.py
backend/var/valuation-v6-runtime/python/python.exe -X utf8 integrations/valuation-v6/tests/smoke_http_v6.py
# Model phải đang chạy, chỉ DB thử3307; không dùng database smartprop thật.
powershell -NoProfile -File backend/scripts/run-isolated-mysql.ps1 -Valuation
```

BE dùng HTTP client cố định loopback, không redirect, 1s connect/5s mỗi exchange, response tối đa64KiB. Không chuyển Bearer tới model. Hai API kiểm ACTIVE và BROKER/ADMIN, private/no-store; preview10/phút/user,30/phút/IP; options30/phút/user,90/phút/IP. IP lấy remoteAddr. Limiter in-memory theo instance; cần shared limiter khi triển khai nhiều instance.
