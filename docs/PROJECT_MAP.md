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

`frontend/`, `backend/`, `docker-compose.yml` hiện là khung chưa có ứng dụng chạy hoàn chỉnh. `AGENTS.md`, `docs/agents/`, `.agents/skills/`, `skills-lock.json` chứa hướng dẫn làm việc cho agent.

`data_raw/`, `processed/`, CSV thô, checkpoint, cache HTML, `.venv/`, `__pycache__/` và `.scratch/` ở trên máy; được bỏ qua khỏi các commit mới. Việc bỏ theo dõi Git không xóa file cục bộ và không thay lịch sử commit cũ.
