# SmartProp AI — API định giá v6

API FastAPI phục vụ demo đồ án, sử dụng ba model XGBoost v6 cho **nhà ở, đất nền và căn hộ**. Model được nạp một lần khi khởi động. Phiên bản cố định: `b4b1339d3f35857e`, cấu hình `all`; các lần train mới không tự thay model của API.

## Chạy tại thư mục gốc repository SmartProp

Môi trường hiện tại đã cài thư viện. Khi cần cài lại:

```powershell
.\ai-services\.venv\Scripts\python.exe -m pip install -r ai-services/requirements.txt
```

Khởi động API trong terminal và giữ terminal đó mở:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 .\ai-services\run_api.py
```

Mở **http://127.0.0.1:8000/docs**, chọn `POST /predict` → **Try it out** để nhập thông tin. Dừng bằng `Ctrl+C`. API chạy CPU, mỗi model dùng 4 luồng; cấu hình demo dùng một worker. Nếu cổng 8000 đã có ứng dụng khác, chọn cổng khác và đổi URL tương ứng.

Ví dụ đổi cổng: thêm `--port 8001` vào cuối lệnh. Script tự xác định thư mục ứng dụng và gọi Uvicorn trực tiếp bằng Python, không qua CLI Click. Khi khởi động thành công, terminal hiện `Application startup complete` và URL đang phục vụ.

Nếu lệnh `python -m uvicorn ...` chỉ hiện `Aborted!`, dùng lệnh `run_api.py` trên để thấy tiến trình nạp thư viện/model và lỗi gốc nếu có. `Aborted!` là thông báo của lớp CLI khi bị hủy/ngắt hoặc gặp EOF; riêng thông báo đó chưa xác định được nguyên nhân ở terminal. Trong đợt kiểm tra ngày 17/10/2026, lệnh CLI cũ chạy thành công ở cả chế độ có và không có terminal tương tác; chưa tái hiện được lần lỗi người dùng báo.

### Nếu API khởi động rồi tự tắt

Các dòng `Application startup complete` → `Shutting down` → `Application shutdown complete` cho thấy tiến trình đã khởi động rồi tắt có trình tự. Log đó chưa cho biết nguyên nhân. Chạy lại với chế độ chẩn đoán:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 .\ai-services\run_api.py --diagnose
```

Terminal in đường dẫn file JSONL trong `.scratch/api-diagnostics/`. Chế độ này ghi thời điểm UTC, thời gian từ lúc chạy, PID/PID cha, kết quả khởi động và tín hiệu dừng mà Uvicorn nhận được (`SIGINT`, `SIGTERM` hoặc `SIGBREAK`). Có tín hiệu không đồng nghĩa người dùng đã bấm dừng; log chưa xác định được ứng dụng nào gửi tín hiệu. Không có sự kiện thoát khi tiến trình bị kết thúc cưỡng bức hoặc máy tắt. Log không ghi nội dung tin, địa chỉ bất động sản hay request body và đã được Git bỏ qua. Chẩn đoán dùng một worker của demo, giữ cách xử lý tín hiệu của Uvicorn và không tự khởi động lại API.

Ngày 26/10/2026: chạy lệnh bình thường tại gốc repo vẫn hoạt động qua 8 lần kiểm tra `/health`; chưa tái hiện được hiện tượng tự tắt ngay người dùng báo. Bổ sung chẩn đoán để thu bằng chứng, chưa coi là đã sửa nguyên nhân.

## Endpoint

| Phương thức | Đường dẫn | Mục đích |
|---|---|---|
| GET | `/health` | Kiểm tra model đã sẵn sàng |
| GET | `/model/options` | Danh sách loại tài sản và mã địa bàn model hỗ trợ cho từng loại |
| POST | `/predict` | Ước tính tổng giá rao, trả cả VND và triệu VND |
| GET | `/docs` | Swagger để thử API |

API trả HTTP **422** khi đầu vào sai và **503** khi model chưa sẵn sàng. Thiếu hoặc sai SHA-256 của model/schema/mã trích đặc trưng làm khởi động thất bại; không chọn model thay thế.

### Đầu vào `/predict`

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `category` | Có | `Nhà ở`, `Đất nền`, `Căn hộ chung cư` |
| `area_sqm` | Có | Diện tích m², số hữu hạn từ 20 đến 1.000 trong phạm vi API v6 |
| `location_feature` | Có | Một giá trị trong `locations` của đúng loại lấy từ `/model/options` |
| `ward` | Không | Phường/xã; được chuẩn hóa theo vocabulary đã học từ train |
| `rooms` | Không | Số phòng ngủ nguyên 1–30; dùng cho nhà/căn hộ |
| `floors` | Không | Số tầng hiện hữu của **nhà**, 1–20; không phải tầng căn hộ hoặc số tầng tòa nhà |
| `access_type` | Không | `alley` = kiệt/hẻm, `frontage` = mặt tiền; dùng cho nhà/đất |
| `house_subtype` | Không | `villa` = biệt thự, `house_c4` = nhà cấp 4; chỉ dùng cho nhà |
| `title` | Không | Tiêu đề, tối đa 500 ký tự |
| `description` | Không | Nội dung mô tả, tối đa 8.000 ký tự |

Các số phải là JSON number, không phải chuỗi hoặc boolean. Trường không biết thì bỏ qua hoặc gửi `null` (riêng `title`/`description` dùng chuỗi rỗng). Không gửi giá/đơn giá vào đầu vào dự đoán; trường ngoài schema bị từ chối.

`location_feature` là token của model, gồm tên quận/huyện cũ và một số token `new_unit:...` của bộ dữ liệu. `/model/options` chỉ trả các mã có trong model của đúng loại và có nhãn đã kiểm tra tại `app/core/location_catalog_v6.json`; `location_labels` cung cấp nhãn hiển thị có dấu. Client hiển thị nhãn nhưng gửi nguyên mã, không suy diễn ánh xạ địa giới cũ/mới. Mã tiêu đề tin đã xác định sai bị chặn ở cả lựa chọn và `/predict`. Phường/xã theo tin không có hoặc ít mẫu trong vocabulary được encode bằng trạng thái chưa biết/ít mẫu và có cảnh báo. [Nguyên nhân và kiểm chứng sửa địa bàn](../docs/LOCATION_LABELS.md).

Tiêu đề/mô tả chỉ được bộ trích v6 lấy lời nêu rõ về phòng ngủ, tầng, mặt tiền/kiệt và subtype theo đúng luật đã dùng khi train. Model không nhận nguyên văn văn bản. Thông tin khai báo tùy chọn được ưu tiên khi không mâu thuẫn; nếu tầng/access/subtype mâu thuẫn với lời trích thì giữ thiếu và cảnh báo. Số phòng có cấu trúc được giữ khi mô tả mâu thuẫn, giống chính sách train. Các lời rao này chưa phải thông tin đã xác minh thực địa.

### Gọi bằng PowerShell ở terminal thứ hai

```powershell
$options = Invoke-RestMethod http://127.0.0.1:8000/model/options
$house = $options.categories | Where-Object { $_.category -eq 'Nhà ở' }
$payload = @{
    category = 'Nhà ở'
    area_sqm = 80
    location_feature = $house.locations[0]
    rooms = 3
    floors = 2
    access_type = 'alley'
}
$body = [System.Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json))
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/predict `
    -ContentType 'application/json; charset=utf-8' -Body $body
```

Kết quả có `predicted_asking_price_vnd`, `predicted_asking_price_million`, `model_run`, `features_used`, `missing_features` và `warnings`. Hai trường giá đều là **tổng giá**, không phải giá/m². `features_used` cho biết giá trị thực sự đã encode; giá trị thiếu được giữ đúng missing flag/NaN của schema train. API không tự điền số trung bình vào trường thiếu.

## Kiểm thử

```powershell
.\ai-services\.venv\Scripts\python.exe -m pip install -r ai-services/requirements-dev.txt
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/tests -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py --diagnose
```

Kiểm thử bao gồm ba loại tài sản, trường thiếu, trích văn bản/mâu thuẫn, đầu vào không hợp lệ và ngăn nạp artifact sai. Bộ kiểm thử phát lại **299 dự đoán validation đã được đánh giá trước đó** qua API, đối chiếu với fixture `tests/fixtures/v6_validation_parity.json`. Fixture chứa đầu vào có cấu trúc và dự đoán đã lưu, kèm SHA-256 nguồn; không chứa ID tin, URL, mô tả, thông tin liên hệ hoặc giá rao thực tế. Đây là kiểm tra tính đúng của suy luận, không phải một lần đánh giá chất lượng trên test mới. Không cần kho CSV/HTML lịch sử để chạy các kiểm thử API.

Ngày 17/10/2026: **17 kiểm thử đạt**, đủ **299 dự đoán đối chiếu khớp**; smoke test HTTP Uvicorn trên localhost đạt cho cả ba loại, `/health`, `/docs` và đầu vào lỗi. Smoke test tự dừng server sau khi kiểm tra. `pip check` không phát hiện phụ thuộc lỗi.

Smoke test hiện chạy chính `run_api.py` trong một tiến trình riêng, đóng stdin và dùng thư mục làm việc khác SmartProp. Đã xác nhận launcher khởi động thành công, đủ endpoint trả kết quả đúng và tiến trình/cổng được đóng sau kiểm tra. Không thay đổi model hoặc mã trích đặc trưng để xử lý lỗi khởi chạy.

## Artifact cần có

Vị trí mặc định:

```text
artifacts/v6/
  manifest.json
  selection.json
  models/all/category_1_xgboost.json
  models/all/category_1_schema.json
  models/all/category_2_xgboost.json
  models/all/category_2_schema.json
  models/all/category_3_xgboost.json
  models/all/category_3_schema.json
```

Khi clone repo sang máy khác, các artifact trên và hai tệp `app/data/training_v3_common.py`, `app/data/property_text_features_v6.py` đã có sẵn. `.gitattributes` giữ nguyên byte cho các file được kiểm tra SHA-256. Có thể đặt `SMARTPROP_V6_MODEL_DIR` để đổi thư mục artifact, nhưng manifest vẫn phải đúng SHA-256 của bản đã chốt trong `app/core/model_registry.py`.

`scripts/package_v6.py` đóng gói từ đúng run lịch sử vào `artifacts/v6` và tạo fixture. Script yêu cầu kho `processed/` cục bộ, kiểm tra hash nguồn và từ chối ghi đè nội dung khác. Không cần chạy script này để khởi động bản clone đã có bundle. Model và hai module đặc trưng giữ nguyên nội dung; chỉ đường dẫn model mặc định của API chuyển sang bundle gọn.

## Phạm vi kết quả

Đây là **giá rao ước tính** từ dữ liệu tin đăng, phục vụ thử nghiệm/demo. [Pilot 132 tin](app/data/V6_HOLDOUT_PILOT.md) có MAPE 35,86% và tỷ lệ sai số ≤20% là 59,09%; sai số này không phải mức bảo đảm cho từng dự đoán. Căn hộ chỉ có 8 mẫu trong pilot. API không xuất khoảng tin cậy khi chưa có hiệu chỉnh được kiểm chứng.

Model có đặc trưng mặt tiền/kiệt theo lời mô tả; chưa có độ rộng hẻm, tọa độ tài sản được xác minh hoặc khoảng cách tới tiện ích. [Frontend Vue](../frontend/vue.ui/README.md) đã nối form định giá với API qua Vite proxy trên nhánh tích hợp. Backend nghiệp vụ và dữ liệu tin đăng thật chưa được nối vào; chưa triển khai công khai. [Kết quả huấn luyện v6](app/data/TRAINING_V6.md).


## G2: bổ sung tài liệu RAG (không huấn luyện lại Qwen)

Kho POI từ API giữ nguyên. Kho tài liệu riêng mặc định là `.scratch/rag-data/documents-corpus.json`;
launcher chat đọc kho này nếu có. Khi chưa có tài liệu đã duyệt, bot báo thiếu nguồn.
Không nhập báo cáo nội bộ, thông tin cá nhân hoặc fixture vào kho thật.

1. Cài extension vào venv RAG: `.\.scratch\rag-venv\Scripts\python.exe -m pip install -r ai-services/requirements-rag-documents.txt`.
2. Sao chép `ai-services/rag-sources.example.json` vào thư mục intake riêng, đặt tài liệu bên trong cùng thư mục đó.
   Điền URL HTTPS gốc, đơn vị phát hành, ngày ban hành/lấy nguồn, hạn rà soát, phiên bản, địa bàn;
   chỉ đặt `approval=APPROVED`, `permission=PERMITTED` khi đã kiểm tra và ghi căn cứ `permissionBasis`.
   `validUntil` là hạn cần rà soát dữ liệu, không tự chứng minh văn bản còn hiệu lực pháp lý.
3. Từ gốc repo chạy dry-run:

```powershell
.\.scratch\rag-venv\Scripts\python.exe ai-services/scripts/ingest_rag_documents.py --manifest <thu-muc-intake>/sources.json --output .scratch/rag-data/documents-corpus.json --report <thu-muc-intake>/validation.json
```

4. Kiểm tra báo cáo rồi thêm `--write` để thay snapshot nguyên tử. Nguồn có `status=REMOVED`
   hoặc bỏ khỏi manifest sẽ bị loại khỏi snapshot mới. Muốn xóa toàn bộ kho phải thêm `--allow-empty`.
   Lô có bản ghi BLOCKED không ghi đè kho cũ. Đừng đặt output/report trùng đường dẫn tài liệu gốc.
5. URL trực tiếp: bỏ `path`, khai báo hostname chính xác trong `allowedHosts`, thêm `--fetch-urls`.
   Chỉ dùng khi được phép trích xuất/tái sử dụng; công cụ kiểm tra robots, chặn IP/private DNS, redirect,
   URL chứa token/query, giới hạn 5 MB/request và timeout. Không tự crawl liên kết hoặc vượt chặn truy cập.
   Chưa có nguồn ngoài nào được tự động thêm/duyệt chỉ vì công khai trên Internet.

Hỗ trợ PDF văn bản, TXT UTF-8, Markdown; PDF scan/khóa/hỏng cần xử lý thủ công, chưa có OCR.
PDF trích xuất trong worker tối đa 30 giây, tối đa 200 trang. Dữ liệu chỉ được trích dẫn lại;
không phải chứng nhận pháp lý/quy hoạch. Mâu thuẫn tự động hiện dựa trên `claimKey`/`claimValue`
được người rà soát gắn, chưa phải mô hình tự phát hiện mọi mâu thuẫn ngữ nghĩa.

Chat dùng BM25 + E5/FAISS + RRF và giới hạn trích đoạn mỗi nguồn. Embedding tài liệu được cache có giới hạn
và tự đổi theo phiên bản nguồn; chưa phải ingestion chạy lịch nền. Không có thêm database hoặc dịch vụ vector mới.
Sau khi đổi kho, có thể hỏi lại ngay; khởi động lại chat sẽ xóa cache RAM cũ.
