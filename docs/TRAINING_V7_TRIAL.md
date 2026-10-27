# Thử nghiệm v7 — số phòng mâu thuẫn để missing

Ngày 27/10/2026, run `32216eeb551ec05b`. Đã huấn luyện đúng hai cấu hình chốt
trước điểm số trên **2.213 train**, **299 validation phát triển**, rồi chấm
**24 nhóm căn hộ** riêng. Cohort không tham gia train, vocabulary hoặc early stopping.

Giả thuyết: khi lời rao mâu thuẫn số phòng, dùng missing thay vì giữ số có cấu
trúc đang tranh chấp. Thay đúng **7 giá trị feature train**: 6 căn hộ, 1 nhà.
Các trường vốn missing giữ nguyên. Không đổi giá/diện tích/ID/split, không
đưa giá hoặc văn bản thô vào X; chưa có tọa độ hoặc khoảng cách POI.

## Kết quả

Trên 24 nhóm căn hộ, MAE tính theo triệu VND:

| Model | MAE | MAPE | Sai số ≤20% |
|---|---:|---:|---:|
| v6 đang dùng | 1.033,67 | 35,43% | 45,83% |
| Control v6/all trên bộ sạch | 1.033,67 | 35,43% | 45,83% |
| v7: mâu thuẫn số phòng để missing | 1.022,67 | 35,33% | 45,83% |

MAE giảm **1,06%**, MAPE giảm **0,094 điểm phần trăm**; số tin trong sai số
20% vẫn là **11/24**. Cải thiện nhỏ, chưa đủ căn cứ thay model ứng dụng.
Pilot nhỏ cùng nguồn CafeLand, không chứng minh độ chính xác chung hoặc giá
giao dịch. Không suy kết quả căn hộ sang nhà ở/đất nền.

Trên 299 validation phát triển: MAE control sạch **2.466,10 triệu** → v7
**2.460,08 triệu**; tỷ lệ sai số ≤20% cùng **49,16%**. Validation đã dùng nhiều
lần. Control sạch bỏ một địa bàn lỗi so với bộ v6 gốc 2.214 tin, nên không coi
mọi chênh lệch với bản lịch sử là tác động riêng của feature.

**Giữ v6 trong ứng dụng.** Model trial, dự đoán và metrics giữ cục bộ, không
thay artifacts/v6, API, database hoặc lịch sử định giá người dùng.

## Kiểm chứng và dùng tiếp

24 nhóm đã chấm, không còn fresh. Entry point mới kiểm giao ID/nhóm với mọi
receipt đã reserve/chấm; đổi metadata hoặc thêm một nhóm không cho phép chấm
lại các nhóm cũ để chọn cấu hình. `train_v7_trial.py` là trainer lịch sử đã
khóa nguồn; vận hành qua `run_v7_trial.py`, không gọi trực tiếp trainer cũ.

Replay kết quả đã lưu, không fit lại:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/run_v7_trial.py --verify
```

Verifier tải lại 6 model trial và model v6, tái tạo đủ **598 dự đoán validation**
và **72 dự đoán pilot**; đối chiếu key/config, nhãn, metric, checksum, receipt.
Đây là replay kiểm chứng, không lựa chọn cấu hình mới.

Đầu ra chọn qua `processed/models_v7_trial/latest.json`, tính từ
`ai-services/app/data/`. Bản chuẩn bị có `collection_DO_NOT_TRAIN.csv`, cấm
ghép vào train. Khôi phục pointer bản chuẩn bị đã hoàn tất sau crash được
kiểm tra đầy đủ checksum trước khi công bố lại.

Tiếp tục cải tiến bằng validation phát triển và bằng chứng đặc trưng đúng đề
bài; cấu hình khác cần cohort chưa từng chấm. Không tối ưu tiếp trên 24 nhóm
này chỉ vì kết quả chưa tốt.
