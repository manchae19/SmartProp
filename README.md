# SmartProp

Đồ án ước tính giá rao bất động sản Đà Nẵng bằng XGBoost. Nhánh tích hợp `feature/fe-ai-v6` kết hợp **API FastAPI v6** từ `develop-binh` với **frontend Vue 3/Vite** từ `origin/main` (`7368bc1`). Form ở trang chủ, trang định giá và chi tiết tin đã gọi model thật qua Vite proxy. Backend nghiệp vụ vẫn là khung và chưa cần cho luồng demo định giá.

## Chạy API trên Windows

Môi trường đã kiểm tra: Python 3.14.6, NumPy 2.5.3, XGBoost 3.4.1. Tại gốc repo:

```powershell
py -3.14 -m venv ai-services/.venv
.\ai-services\.venv\Scripts\python.exe -m pip install -r ai-services/requirements-dev.txt
.\ai-services\.venv\Scripts\python.exe -X utf8 .\ai-services\run_api.py
```

Nếu đã có môi trường ảo, dùng lại môi trường đó. Mở **http://127.0.0.1:8000/docs** để thử `POST /predict`. [Hướng dẫn API và đầu vào](ai-services/README.md).

## Chạy frontend ở terminal thứ hai

```powershell
cd frontend/vue.ui
npm.cmd ci
npm.cmd run dev
```

Mở **http://127.0.0.1:5173/valuation** để nhập thông tin và ước tính giá, hoặc **http://127.0.0.1:5173/listing/1** để thử từ tin minh họa. Giữ terminal API ở trên chạy cùng frontend. [Hướng dẫn FE–AI, cấu hình và kiểm thử](frontend/vue.ui/README.md).

## Cấu trúc chính

```text
ai-services/
  main.py                 FastAPI và vòng đời model
  run_api.py              Lệnh khởi động demo
  app/api/                Schema và endpoint
  app/core/               Phiên bản model được cố định
  app/models/xgboost/      Suy luận với schema/extractor v6
  app/data/               Mã crawler, lọc, huấn luyện và kiểm chứng
  artifacts/v6/           Ba model, schema, manifest và metrics (~2 MB)
  tests/                  Kiểm thử API và fixture parity 299 trường hợp
  scripts/                Đóng gói model từ kho dữ liệu cục bộ
frontend/vue.ui/           Frontend Vue từ main, đã nối form định giá với API v6
backend/                  Khung backend
docs/                     Bản đồ dự án và hướng dẫn GitHub
```

[Bản đồ các file](docs/PROJECT_MAP.md) · [Chuẩn bị commit/push](docs/GITHUB_PREPARATION.md) · [Tóm tắt chất lượng model](docs/MODEL_V6.md).

## Kiểm thử bản gọn

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/tests -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py
```

Bộ model và fixture kiểm thử nằm trong repo, nên chạy API và các kiểm thử này không cần kho CSV/HTML cào được.

## Dữ liệu cục bộ

`data_raw/`, `processed/`, CSV thô, checkpoint, cache HTML và `.scratch/` được giữ trên máy và bỏ qua khi commit. Các script/báo cáo lịch sử trong `app/data/` cần kho dữ liệu riêng để chạy đầy đủ. Model v6 và hai module đặc trưng được giữ nguyên byte để SHA-256 không thay đổi khi clone trên Windows/Linux.

Model học từ **2.214 tin**, có **299 validation phát triển**. Pilot lưu trữ 132 tin có MAPE **35,86%**, tỷ lệ sai số ≤20% **59,09%**; đây là bằng chứng ban đầu cho demo. Kết quả là **giá rao ước tính**, chưa xác minh giá giao dịch, tọa độ tài sản hoặc khoảng cách tiện ích.
