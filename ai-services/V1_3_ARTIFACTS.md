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
