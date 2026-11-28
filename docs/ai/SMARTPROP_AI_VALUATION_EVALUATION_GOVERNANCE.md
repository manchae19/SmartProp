# SmartProp — AI Valuation Evaluation Governance

**Ngày:** 2026-11-25
**Phạm vi:** Đính chính trạng thái tập holdout lịch sử, protocol paired evaluation, và
kết quả đo trên dev test 4.403 mẫu.
**Liên quan:** [Full audit V1.3 ở nhánh nghiên cứu](../../../docs/ai/SMARTPROP_AI_VALUATION_V1_3_FULL_AUDIT.md)
(nhánh `feature/tinix-xgboost-standalone`) — tài liệu này **không** lặp lại nội dung audit.

---

## 1. Đính chính: tập 3.102 mẫu đã được đánh giá

### 1.1. Trạng thái thực tế

Tập **3.102 mẫu** ("reserved blind test", `split_v2`) **đã được mở và đánh giá** tại
**Step 20.11B**, không còn là blind test chưa từng mở.

**Bằng chứng:**

| Artifact | Nội dung |
|---|---|
| `.scratch/tinix-xgboost-v1/final-blind-20-11b/blind_evaluation.json` | `sample_count: 3102`, có metric đầy đủ cho `v1_2_baseline` và `v1_3_primary` |
| `.scratch/tinix-xgboost-v1/deployment-readiness-20-12/STATISTICAL_CLAIMS_AUDIT.md` | Phân tích bootstrap trên chính tập này, ghi rõ `split_v2 Reserved Blind Test (3,102 rows)` |

Kết quả đã công bố trên tập này (V1.3): MAPE 21.185%, Median APE 15.543%,
W20 61.315%, R² 0.6944, MAE 3.895B.

### 1.2. Tài liệu còn ghi sai trạng thái

Ba artifact dưới đây mô tả trạng thái **tại thời điểm tạo** (trước Step 20.11B), không
phải trạng thái hiện tại. **Không sửa các file này** — chúng đã đóng băng và có SHA256
trong manifest:

| File | Nội dung lỗi thời | Trạng thái đúng |
|---|---|---|
| `ai-services/artifacts/v1_3/artifact_manifest.json` → `evaluation.json` | `reserved_blind_test_unopened: PASS (3,102 samples sealed)` | Đã mở tại Step 20.11B |
| `.scratch/tinix-xgboost-v1/dataset-freeze-20-10a/FROZEN_SPLIT_MANIFEST.json` | `reserved_blind_test.status: SEALED_BLIND_TEST` | Đã mở tại Step 20.11B |
| `ai-services/evaluation/phase11_error_analysis.json` | `blind_test: "NOT_READ"` | Đã đọc tại Step 20.11B |

**Quy tắc:** đọc các trường này như *lịch sử cấu hình tại thời điểm tạo artifact*, không
phải trạng thái hiện hành. Bản ghi đính chính này là nguồn tham chiếu.

### 1.3. Hệ quả bắt buộc

- **Không** dùng tập 3.102 làm final holdout cho V1.4/V2.
- **Không** tuning trên tập 3.102.
- **Không** mở lại tập 3.102 trong công việc này.
- V1.4/V2 cần **holdout mới**, lấy từ nguồn dữ liệu độc lập, chưa từng được đọc.

---

## 2. Paired evaluation: legacy assumed vs real features

### 2.1. Protocol

| Thành phần | Giá trị |
|---|---|
| Cohort | Dev test `split_v2`, **4.403 mẫu** (2.025-02-25 → 2026-03-16) |
| Ground truth | `actual_vnd` trong `test_predictions_dev.csv`, khớp `target_vnd` của pool |
| Feature nguồn | `.scratch/tinix-xgboost-v1/leakage-hardening-20-9/pool_identity.csv` |
| Model | V1.3 hiện có — **không retrain, không đổi weights** |
| Calibration | Nguyên bản `calibration.json` (Duan by band) |
| Join | 4.403/4.403 ID khớp pool, **0 mẫu bị bỏ** |
| Feature điền | Chỉ lấy từ pool; **không** điền bằng ground truth, **không** dùng dữ liệu tương lai |

### 2.2. Năm chế độ input

| Mode | Nội dung |
|---|---|
| `legacy_frontage` | Base + đường 10m / mặt tiền 5m (giả định legacy) |
| `legacy_alley` | Base + đường 3m / mặt tiền 4m (giả định legacy) |
| `basic_missing` | Chỉ area/type/district/ward/bedrooms; kích thước để trống |
| `full_real` | Toàn bộ feature thật có trong pool |
| `real_no_street` | `full_real` bỏ `street_name` (cô lập đóng góp của tên đường) |

Base = `area`, `normalized_type`, `district`, `ward`, `bedroom_count`.

### 2.3. Kết quả

| Mode | n | MAE (B) | RMSE (B) | MAPE % | MedAPE % | P90 % | W20 % | R² | bias (B) | under % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `legacy_frontage` | 4.403 | 6.4762 | 18.2980 | 29.356 | 23.805 | 60.232 | 42.54 | 0.3390 | −5.2961 | 64.14 |
| `legacy_alley` | 4.403 | 9.8868 | 21.6097 | 48.867 | 50.317 | 72.834 | 9.18 | 0.0781 | −9.8428 | 96.39 |
| `basic_missing` | 4.403 | 5.3458 | 14.1707 | 27.889 | 23.258 | 54.232 | 43.20 | 0.6036 | −3.5799 | 68.27 |
| **`full_real`** | 4.403 | **3.7653** | **11.6365** | **19.815** | **15.023** | **41.171** | **62.37** | **0.7327** | −2.1020 | 68.68 |
| `real_no_street` | 4.403 | 4.6820 | 12.2725 | 23.628 | 18.795 | 48.165 | 52.80 | 0.7027 | −2.9611 | 67.86 |

### 2.4. Kiểm chứng harness

`full_real` tái lập **chính xác** metric đã công bố của V1.3 trên dev test:
MAPE 19.8155%, MedAPE 15.0230%, W20 62.3666%, R² 0.7327, MAE 3.7653B.
→ Harness đo đúng; các mode còn lại dùng cùng model, cùng calibration, cùng metric.

### 2.5. Kết luận có bằng chứng

**a) Giả định kích thước legacy tệ hơn để trống.**

| So sánh | MAPE | Δ |
|---|---:|---:|
| `basic_missing` (để trống) | 27.889% | — |
| `legacy_frontage` (10m/5m) | 29.356% | **+1.47 pp tệ hơn** |
| `legacy_alley` (3m/4m) | 48.867% | **+20.98 pp tệ hơn** |

Giả định hẻm 3m/4m đặc biệt tai hại: W20 rơi từ 43.2% xuống **9.18%**, under-prediction
tăng lên **96.4%**. Đây là bằng chứng trực tiếp rằng việc bịa kích thước trong production
**gây hại**, không chỉ là vấn đề trung thực dữ liệu.

**b) Feature thật cải thiện rõ rệt so với basic.**

`basic_missing` 27.889% → `full_real` 19.815% = **−8.07 pp MAPE**, W20 43.20% → 62.37%,
R² 0.6036 → 0.7327, bias −3.58B → −2.10B.

**c) Tên đường đóng góp lớn nhất trong nhóm feature thật.**

`real_no_street` 23.628% → `full_real` 19.815% = **−3.81 pp MAPE**
(MedAPE −3.77 pp, W20 +9.56 pp, R² +0.030).

**d) Không kết luận độ chính xác production tăng.** Đây là đo trên dev test với feature
lấy từ nguồn, **không** phải đo trên dữ liệu người dùng thật nhập. Người dùng thật sẽ
nhập thiếu nhiều hơn; tỷ lệ điền thực tế cần đo riêng.

---

## 3. Street feature analysis

### 3.1. Encoding thực tế

`raw_street_name` là **categorical feature**, không phải target encoding.

Bằng chứng: `ai-services/artifacts/v1_3/feature_schema.json` liệt kê
`raw_street_name` trong `categorical` (cùng `district`, `ward`, `project_name`,
`house_direction`, `balcony_direction`). `numeric` chỉ chứa các biến số.

**Hệ quả:**
- **Không có** target-encoding leakage cho street — không có target encoding nào cả.
- Đính chính mô tả trước đây ("street target encoding mạnh") là **sai**.
- Feature importance cao của street là do mô hình học được phân biệt theo tuyến đường,
  không phải do leakage.

### 3.2. Chuẩn hoá

`clean_category` (`ai-services/app/models/xgboost/features_v1_3.py`):

```
None / NaN / "" / "none" / "nan" → "__MISSING__"
còn lại → unicodedata.normalize("NFC", s).casefold()
```

NFC + casefold xử lý được khác biệt dấu/hoa-thường. **Không** xử lý alias
("NVL" vs "Nguyễn Văn Linh") và **không** sửa lỗi chính tả.

### 3.3. Vocabulary

| Chỉ số | Giá trị |
|---|---|
| Street khác nhau trong training | 1.795 |
| Đủ ngưỡng vocab (≥10 lần) | **690** |
| Singleton (chỉ 1 lần) | 312 |
| Coverage training | 74.0% (27.100/36.617) |

1.105 street dưới ngưỡng 10 lần → không có category riêng, gộp vào fallback.

### 3.4. Hành vi với street ngoài vocabulary

Đo qua HTTP thật trên cùng một property:

| Chuyển đổi | Δ giá |
|---|---:|
| missing → `Nguyễn Văn Linh` (trong vocab) | **+77.97%** |
| `Nguyễn Văn Linh` → `Đường Không Tồn Tại XYZ` (ngoài vocab) | **−36.40%** |

Street ngoài vocabulary bị đối xử như category không xác định, kéo giá về mức trung bình
thấp hơn — nhất quán với việc XGBoost dùng default direction cho category chưa thấy.

### 3.5. Rủi ro đã ghi nhận (không sửa trong nhiệm vụ này)

| Rủi ro | Mô tả |
|---|---|
| Alias | "NVL" và "Nguyễn Văn Linh" là hai category khác nhau |
| Chính tả | Sai một ký tự → rơi khỏi vocabulary, mất đóng góp (−36%) |
| Trùng tên đường giữa quận | `raw_street_name` không ghép với `district`; "Lê Lợi" ở hai quận là một category |
| Street mới | Đường mới mở không có trong vocab → mất tín hiệu |

**Không thay đổi encoding, calibration hoặc weights trong nhiệm vụ này.**

---

## 4. Đề xuất V1.4 dựa trên bằng chứng

### 4.1. Ưu tiên cao — có số đo

| # | Việc | Bằng chứng | Cần retrain |
|---|---|---|---|
| 1 | Street normalization + alias map + ghép district | `real_no_street` cho thấy street trị giá 3.81 pp; alias/chính tả làm mất trắng tín hiệu | **Có** (đổi feature) |
| 2 | Giữ nguyên real-feature mode làm mặc định production | Legacy assumption tệ hơn 1.47–20.98 pp | Không (đã làm) |
| 3 | Thu thập tỷ lệ điền thật của người dùng | Đo trên dev test dùng feature từ nguồn; người dùng thật sẽ thiếu nhiều hơn | Không |
| 4 | Holdout mới cho V1.4 | Tập 3.102 đã mở | Không |

### 4.2. Ưu tiên trung bình

| # | Việc | Ghi chú |
|---|---|---|
| 5 | Xử lý street ngoài vocabulary | Fallback theo `district` thay vì category rỗng |
| 6 | Bổ sung dữ liệu phân khúc thiếu | VILLA 948 mẫu, Hòa Vang 1.158, <2B 941 |
| 7 | Market/Comparable feature theo fold | Chưa đo; phải tránh leak |

### 4.3. Không làm

- Không kết luận CatBoost/LightGBM kém hơn khi chưa benchmark cùng cohort.
- Không dùng tập 3.102 để tuning.
- Không thêm feature mà training không có (`legal_status`, `land_depth`, `lat/lon`).

---

## 5. Trạng thái kiểm chứng của tài liệu này

| Hạng mục | Trạng thái |
|---|---|
| Paired evaluation trên dev test | **VERIFIED** — chạy thật, 5 mode × 4.403 mẫu |
| Harness tái lập metric công bố | **VERIFIED** — `full_real` khớp tuyệt đối |
| Street encoding là categorical | **VERIFIED** — đọc `feature_schema.json` |
| Street ngoài vocabulary | **VERIFIED** — đo qua HTTP thật |
| Tập 3.102 đã mở | **VERIFIED** — có `blind_evaluation.json` |
| Tỷ lệ điền feature của người dùng thật | **NOT_RUN** — cần telemetry production |
| Benchmark CatBoost/LightGBM | **NOT_RUN** |
