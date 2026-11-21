# XGBoost V1.3 model artifacts — distribution & setup

The V1.3 model weights are **not committed** (~28 MB). A fresh clone must fetch
and verify them before V1.3 inference is active. This is the recommended
localhost distribution path for the group.

## What inference needs

`ai-services/app/models/xgboost/predictor_v1_3.py` loads exactly four files from
`ai-services/artifacts/v1_3/` and verifies their SHA-256 against constants in the
source (`V1_3_MODEL_HASH`, `V1_3_SCHEMA_HASH`, `V1_3_CALIBRATION_HASH`):

| File | Bytes | Purpose |
|---|---|---|
| `model.json` | 28,512,676 | boosted-tree weights |
| `feature_schema.json` | 24,257 | feature order/schema |
| `calibration.json` | 547 | calibration parameters |
| `artifact_manifest.json` | 1,078 | artifact provenance |

The authoritative hashes live in `ai-services/artifacts/v1_3.manifest.json`.

## Setup (once per clone)

1. Put the four files on a release / object store reachable by the team.
2. From `ai-services/`:

   ```powershell
   ./scripts/fetch-v1_3-artifacts.ps1 -BaseUrl "https://<host>/v1_3"
   ```

   The script downloads each file and refuses it on any SHA-256 mismatch.

Alternative: use **Git LFS** — commit only the four files under
`ai-services/artifacts/v1_3/` to LFS if the team prefers `git lfs pull`.

## Fallback (safe by design)

If the artifacts are absent the AI service still starts:

- `GET /health` → `{"status":"ok","model_version":"v6","model_ready":true}`
- `GET /api/internal/v1_3/health` → `{"status":"degraded","model_version":"v1.3","model_ready":false}`

Verified by starting `create_app(v1_3_model_dir=<empty>)`: the V1.3 predictor is
initialised to `None`, V6 keeps serving, and the log records
`XGBoost V1.3 initialization deferred or failed`. No mock output is produced.

## Chạy dịch vụ với V1.3

V1.3 là model chính. Dịch vụ khởi động, trả `/model/options` và `/predict` chỉ với
bộ artifacts V1.3; V6 là tùy chọn và chỉ nạp khi artifacts của nó có mặt.

```powershell
cd ai-services
./scripts/fetch-v1_3-artifacts.ps1 -BaseUrl "https://<host>/v1_3"   # một lần mỗi clone
./scripts/run-valuation-v1_3.ps1 -Port 8000
```

Script xác minh SHA-256 của cả bốn file trước khi chạy, rồi đặt
`SMARTPROP_V1_3_REAL_FEATURES=true` và `SMARTPROP_V1_3_MODEL_DIR`.

Kiểm tra:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health          # {"status":"ok","model_version":"v1.3","model_ready":true}
Invoke-RestMethod http://127.0.0.1:8000/model/options   # categories + districts từ V1.3
```

Nếu artifacts thiếu hoặc hỏng, `/health` trả `{"status":"degraded","model_ready":false}`
kèm lý do, thay vì làm dịch vụ không khởi động được.

## Nhóm lấy artifacts ở đâu

Bộ artifacts V1.3 (~28 MB) **không commit**. Nhóm dùng một trong hai cách:

**Cách 1 — bản bàn giao trên máy chủ nội bộ.** Đặt bốn file vào một thư mục tĩnh
(ví dụ `\\smartprop-files\models\v1_3\` hoặc một bucket S3 của nhóm) rồi:

```powershell
./scripts/fetch-v1_3-artifacts.ps1 -BaseUrl "https://<đường-dẫn-nhóm-dùng>/v1_3"
```

**Cách 2 — chép tay từ máy đã có bộ đã xác minh.** Nếu đồng đội đã có
`ai-services/artifacts/v1_3/` hợp lệ, chép nguyên thư mục đó sang clone mới:

```powershell
Copy-Item -Recurse <may-da-co>\ai-services\artifacts\v1_3 ai-services\artifacts\v1_3
```

Cả hai cách đều phải qua bước xác minh SHA-256 mà
`run-valuation-v1_3.ps1` chạy trước khi khởi động, nên một bản sao hỏng sẽ bị
chặn ngay chứ không âm thầm cho ra giá sai.