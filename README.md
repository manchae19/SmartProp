# SmartProp

Đồ án ước tính giá rao bất động sản Đà Nẵng bằng XGBoost. Nhánh `feature/fe-ai-v6` kết hợp **API FastAPI v6**, **frontend Vue 3/Vite** từ `main` (`7368bc1`) và **BE Spring Boot/MySQL** từ `Backend-Huy` (`ac13ec3`). Form định giá gọi model thật; tại `/valuation`, tài khoản đăng nhập có thể lưu, xem và xóa lịch sử. Các màn hình nghiệp vụ khác của frontend vẫn cần nối riêng với BE.

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

## Chạy BE để lưu lịch sử

Máy hiện tại đã có runtime cục bộ. Terminal thứ ba tại gốc repo:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 backend/scripts/run-demo.py
```

BE 8080 và MySQL demo riêng 13306, dữ liệu giữ tại `backend/var/local-demo/`. Đăng ký/đăng nhập rồi quay lại `/valuation` để lưu kết quả. Launcher không dùng database nguồn hoặc `.env`. Máy mới cần JDK 21, Maven và MySQL ZIP. [Hướng dẫn và kiểm chứng lịch sử](docs/VALUATION_HISTORY.md).

Nếu đăng nhập báo 502 hoặc launcher báo cổng đang được dùng, chạy `ai-services/.venv/Scripts/python.exe -X utf8 backend/scripts/check-demo.py` để kiểm tra kết nối trước. Lệnh chỉ đọc, không dừng dịch vụ hoặc yêu cầu mật khẩu.

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
backend/                  Spring Boot: đăng nhập, nghiệp vụ và lịch sử định giá
database/                 SQL nguồn và migration V13 cho lịch sử
docs/                     Bản đồ dự án và hướng dẫn GitHub
```

[Bản đồ các file](docs/PROJECT_MAP.md) · [Chuẩn bị commit/push](docs/GITHUB_PREPARATION.md) · [Tóm tắt chất lượng model](docs/MODEL_V6.md).

[Phân tích sai số v6 và kế hoạch bổ sung dữ liệu](docs/MODEL_V6_DIAGNOSTICS.md) · [Review tích hợp](docs/PR4_REVIEW.md) · [Thiết lập database trên máy hiện tại](docs/DATABASE_SETUP_LOCAL.md).

[Chuẩn bị dữ liệu lần train tiếp theo](docs/GEOSPATIAL_NEXT.md): đã xuất 2.213 train + 299 validation, cách ly một mã địa bàn sai. Chưa thay model demo; chưa có tọa độ tài sản được xác minh để train đặc trưng khoảng cách.

[Lô thử 100 tin căn hộ mới](docs/APARTMENT_PILOT_100.md): 10 ứng viên khóa riêng để kiểm chứng, 90 tin cần rà soát. Chưa thêm vào train hoặc huấn luyện v7.

[Đã rà soát tiếp 90 tin](docs/APARTMENT_FOLLOWUP.md): bổ sung 3 ứng viên, loại 10 tin khỏi phạm vi, còn 77 cần bằng chứng. Tập kiểm chứng mở rộng có 13 nhóm; chưa train v7.

[Mở rộng sau review](docs/APARTMENT_EXTENSION.md): thêm 120 ID, khóa 24 nhóm và hoàn tất [thử nghiệm v7](docs/TRAINING_V7_TRIAL.md). Cải thiện nhỏ, giữ v6 trong ứng dụng; 24 nhóm đã chấm không dùng để tối ưu tiếp.

## Kiểm thử bản gọn

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/tests -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py
```

Bộ model và fixture kiểm thử nằm trong repo, nên chạy API và các kiểm thử này không cần kho CSV/HTML cào được.

## Dữ liệu cục bộ

`data_raw/`, `processed/`, CSV thô, checkpoint, cache HTML và `.scratch/` được giữ trên máy và bỏ qua khi commit. Các script/báo cáo lịch sử trong `app/data/` cần kho dữ liệu riêng để chạy đầy đủ. Model v6 và hai module đặc trưng được giữ nguyên byte để SHA-256 không thay đổi khi clone trên Windows/Linux.

Model học từ **2.214 tin**, có **299 validation phát triển**. Pilot lưu trữ 132 tin có MAPE **35,86%**, tỷ lệ sai số ≤20% **59,09%**; đây là bằng chứng ban đầu cho demo. Kết quả là **giá rao ước tính**, chưa xác minh giá giao dịch, tọa độ tài sản hoặc khoảng cách tiện ích.
