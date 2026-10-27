# Bản đồ file SmartProp

## Đọc và chạy trước

| File/thư mục | Vai trò |
|---|---|
| [README gốc](../README.md) | Tổng quan, cài đặt và chạy nhanh |
| [ai-services/README.md](../ai-services/README.md) | Endpoint, schema, ví dụ dự đoán và kiểm thử |
| [ai-services/run_api.py](../ai-services/run_api.py) | Khởi chạy demo trên localhost |
| [ai-services/main.py](../ai-services/main.py) | FastAPI, tải model lúc startup, xử lý lỗi validation |
| [app/api/schemas.py](../ai-services/app/api/schemas.py) | Kiểu đầu vào/đầu ra và giới hạn theo loại tài sản |
| [app/api/valuation.py](../ai-services/app/api/valuation.py) | `/health`, `/model/options`, `/predict` |
| [app/core/model_registry.py](../ai-services/app/core/model_registry.py) | Run, manifest SHA-256 và đường dẫn bundle v6 cố định |
| [app/models/xgboost/predictor_v6.py](../ai-services/app/models/xgboost/predictor_v6.py) | Kiểm tra artifact, encode feature, suy luận và đổi đơn vị giá |
| [artifacts/v6](../ai-services/artifacts/v6/) | 3 model + 3 schema + manifest + selection + metrics; khoảng 2 MB |
| [tests/test_api_v6.py](../ai-services/tests/test_api_v6.py) | Kiểm thử API và phát lại 299 dự đoán đã lưu |
| [tests/fixtures/v6_validation_parity.json](../ai-services/tests/fixtures/v6_validation_parity.json) | Đầu vào kiểm thử có cấu trúc và dự đoán tham chiếu |
| [tests/smoke_http_v6.py](../ai-services/tests/smoke_http_v6.py) | Khởi chạy launcher thực tế, thử HTTP, tự dừng tiến trình test |
| [scripts/package_v6.py](../ai-services/scripts/package_v6.py) | Tạo lại bundle/fixture từ kho dữ liệu cục bộ có hash đúng |

## Mã xử lý dữ liệu

Mã lịch sử được giữ để truy vết, tránh đổi đường dẫn/import hoặc phá hash các lần train đã khóa. Không cần chạy toàn bộ các script này khi chỉ demo API.

| Nhóm trong `ai-services/app/data/` | Vai trò |
|---|---|
| `crawl_*.py`, `crawler_cafeland/`, `collect_*.py` | Thu thập theo nguồn, checkpoint và chống trùng |
| `audit_*.py`, `review_*.py`, `filter_*.py` | Kiểm kê, rà soát và phân nhóm dữ liệu |
| `remaining_content_rules.py`, `remaining_diversity_rules.py` | Luật xử lý tin còn chờ và bổ sung dữ liệu train |
| `train_*.py`, `build_training_*.py` | Chuẩn bị dữ liệu và huấn luyện các phiên bản |
| `training_v3_common.py` | Encoder nền dùng chung; giữ nguyên byte cho model v6 |
| `property_text_features_v6.py` | Trích phòng/tầng, access/subtype và encode v6; giữ nguyên byte |
| `build_property_features_v6.py`, `train_property_features_v6.py` | Tạo feature có bằng chứng và thí nghiệm v6 |
| `audit_reserved_holdout.py`, `prepare_v6_holdout_pilot.py`, `evaluate_v6_holdout_pilot.py` | Kiểm tra lịch sử, khóa cohort và chấm pilot |
| `verify_*.py`, `test_*.py` | Kiểm chứng các pipeline/thí nghiệm khi có kho dữ liệu đầy đủ |
| `TRAINING_DATA_CURRENT.md`, `TRAINING_V*.md`, `V6_HOLDOUT_PILOT.md` | Báo cáo lịch sử; các liên kết `processed/...` cần archive cục bộ |

Các lần sàng lọc và chấm pilot đã khóa không được chạy lại để thay cohort hoặc xem cùng tin là test mới. [Tóm tắt chất lượng model](MODEL_V6.md).

## Các phần còn lại

Nhánh `feature/fe-ai-v6` đã ghép lịch sử `main`, dùng FE từ `7368bc1`, nhập mã BE/database từ `Backend-Huy` tại `ac13ec3` và mở rộng lịch sử định giá. Model v6 vẫn giữ nguyên. `docker-compose.yml` trên nhánh này còn là khung; demo dùng launcher MySQL riêng.

| Phần BE/dữ liệu mới | Vai trò |
|---|---|
| [VALUATION_HISTORY.md](VALUATION_HISTORY.md) | Cách chạy 3 thành phần, quyền truy cập và kết quả kiểm thử |
| [backend/scripts/run-demo.py](../backend/scripts/run-demo.py) | Chạy Spring Boot/MySQL demo riêng, giữ dữ liệu và không đọc database nguồn |
| [backend/scripts/check-demo.py](../backend/scripts/check-demo.py) | Kiểm tra kết nối AI, BE/MySQL và proxy FE mà không gửi thông tin đăng nhập |
| [backend/scripts/check-history-mysql.py](../backend/scripts/check-history-mysql.py) | Kiểm thử schema riêng; thêm `--browser` để chạy cả Vue và BE thật |
| [backend/src/main/java/vn/smartprop/valuation](../backend/src/main/java/vn/smartprop/valuation/) | Cổng v6 và API lưu/xem/xóa snapshot theo tài khoản |
| [database/migrations/V13__valuation_history.sql](../database/migrations/V13__valuation_history.sql) | Bảng lịch sử, khóa chống trùng và chỉ mục owner/thời gian |
| [prepare_training_next.py](../ai-services/app/data/prepare_training_next.py) | Bản chuẩn bị cohort mới, cách ly mã địa bàn sai và xuất readiness |
| [GEOSPATIAL_NEXT.md](GEOSPATIAL_NEXT.md) | Số liệu v6 hiện tại, dữ liệu vị trí còn thiếu và nguồn được phép |
| [MODEL_V6_DIAGNOSTICS.md](MODEL_V6_DIAGNOSTICS.md) | Sai số validation theo loại/địa bàn và kế hoạch bổ sung độ phủ |
| [PR4_REVIEW.md](PR4_REVIEW.md) | Review Standards/Spec và bản vá cách ly database/cleanup |

| File FE | Vai trò |
|---|---|
| [frontend/vue.ui/README.md](../frontend/vue.ui/README.md) | Chạy FE/API, proxy, dữ liệu minh họa và kiểm thử |
| [src/services/valuation.js](../frontend/vue.ui/src/services/valuation.js) | Kiểm tra đầu vào, gọi API, timeout/hủy yêu cầu và định dạng giá |
| [app/core/location_catalog_v6.json](../ai-services/app/core/location_catalog_v6.json) | Mã địa bàn v6 được phép công khai, nhãn có dấu và mã bị chặn do sai nguồn |
| [src/components/ValuationPanel.vue](../frontend/vue.ui/src/components/ValuationPanel.vue) | Form theo loại tài sản, tải lựa chọn từ model, hiển thị giá/feature/missing/cảnh báo |
| [src/components/ValuationHistory.vue](../frontend/vue.ui/src/components/ValuationHistory.vue) | Lịch sử của tài khoản, phân trang, xóa và trạng thái lỗi |
| [user/views/ValuationView.vue](../frontend/vue.ui/user/views/ValuationView.vue) | Trang `/valuation` để nhập thông tin riêng |
| [user/views/HomeView.vue](../frontend/vue.ui/user/views/HomeView.vue) | Dùng form v6 tại mục Định giá của trang chủ |
| [user/views/ListingDetailView.vue](../frontend/vue.ui/user/views/ListingDetailView.vue) | Dùng thông tin có cấu trúc của tin minh họa để gọi v6; đã bỏ giá và tỷ lệ ảnh hưởng mẫu |
| [vite.config.js](../frontend/vue.ui/vite.config.js) | Proxy `/api/ai/*` tới FastAPI, `/api/v1/*` tới BE khi dev/preview |
| [tests/valuation.test.js](../frontend/vue.ui/tests/valuation.test.js) | Kiểm thử payload, HTTP, hủy/timeout và đơn vị giá |
| [e2e/valuation.spec.js](../frontend/vue.ui/e2e/valuation.spec.js) | Kiểm thử trình duyệt, trong đó có cả 3 loại gọi v6 thật |
| [e2e-live/history.spec.js](../frontend/vue.ui/e2e-live/history.spec.js) | Kiểm thử toàn luồng đăng ký/đăng nhập, giá và lịch sử bằng BE/MySQL/model thật |

[Giải thích lỗi tên địa bàn và cách sửa](LOCATION_LABELS.md). Catalog chỉ phục vụ API/hiển thị, không thay vocabulary hoặc model đã khóa.

`AGENTS.md`, `docs/agents/`, `.agents/skills/`, `skills-lock.json` chứa hướng dẫn làm việc cho agent.

`data_raw/`, `processed/`, CSV thô, checkpoint, cache HTML, `.venv/`, `__pycache__/` và `.scratch/` ở trên máy; được bỏ qua khỏi các commit mới. Việc bỏ theo dõi Git không xóa file cục bộ và không thay lịch sử commit cũ.
