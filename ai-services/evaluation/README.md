# V6/V1.3 evaluation evidence — reproduction and governance

This directory is for **aggregate, non-row-level** evaluation metadata that is safe to keep in Git.
The authoritative manifest is [`model_evaluation_manifest.json`](./model_evaluation_manifest.json).

## 1. Evidence locations

| Evidence | Location | Git? |
|---|---|---|
| V1.3 evaluation aggregate | `ai-services/artifacts/v1_3/evidence/evaluation.json` | **No** (local/ignored) |
| V1.3 dev-test predictions | `ai-services/artifacts/v1_3/evidence/test_predictions_dev.csv` | **No** (local/ignored) |
| V1.3 integrated train | `ai-services/artifacts/v1_3/evidence/train_v1_3_integrated.csv` | **No** (local/ignored) |
| V1.3 evidence hashes | `ai-services/artifacts/v1_3/evidence/SHA256SUMS.txt` | No (local) |
| V6 development metrics | `ai-services/artifacts/v6/metrics.json` | Yes (existing model artifact) |
| V6 reserved registry | `ai-services/app/data/processed/property_features_v6/runs/*/reserved_holdout_registry.csv` | Local/data-dependent |
| 3,102 blind records | **Do not retrieve or open** | Sealed |

The evidence files were recovered byte-for-byte from
`F:\SmartProp\.scratch\tinix-xgboost-v1\v1-3` and verified against
`ai-services/artifacts/v1_3/artifact_manifest.json`.

## 2. Reproduce the V1.3 dev-test metrics

Prerequisites: Python 3.11+; only the standard library is required.

```powershell
cd F:\SmartProp\.worktrees\integration-tinix\ai-services
python scripts/verify_v1_3_evidence.py
```

The script:
- verifies byte sizes and SHA-256 for `evaluation.json`, `test_predictions_dev.csv`,
  `train_v1_3_integrated.csv`;
- recomputes metrics from `actual_vnd` and `pred_v1_3_vnd`;
- checks 4,403 rows and zero train/test entity overlap;
- prints `VERIFY_RESULT=PASS` and `blind_test=NOT_READ`.

Expected metrics:

| Metric | Expected |
|---|---:|
| Rows | 4,403 |
| MAE | 3,765,301,650.61 VND |
| RMSE | 11,636,512,511.63 VND |
| MAPE | 19.8155% |
| Median APE | 15.0230% |
| P90 APE | 41.1728% |
| Within-20% | 62.3666% |
| R² | 0.732672 |
| Mean signed bias | −2,102,000,485.86 VND |
| Under-predicted | 68.6804% |

If a hash fails, do not “fix” the metric or regenerate the artifact. Stop and report
the evidence provenance mismatch.

## 3. Evaluation scopes (do not mix)

| Scope | V6 | V1.3 |
|---|---|---|
| Development validation | 299 rows; used for repeated development/model selection | 6,894 rows; used for early stopping/selection |
| Dev-test | **not available** | 4,403 rows; entity/time out-of-sample; **not blind** |
| Reserved/holdout | 684 IDs with registry, **no predictions/metrics** | — |
| Blind test | — | **3,102 sealed; no metric** |

Definitions:
- **Development validation** — used during model development/selection; not an independent test.
- **Dev-test** — held-out rows used for development evaluation; report with split and caveat.
- **Reserved set** — IDs withheld but not necessarily evaluated; requires a protocol and labels.
- **Blind test** — one-time evaluation after model/process freeze; no peeking or iterative tuning.

## 4. Metric formulas and units

All monetary metrics use **VND** for V1.3 (V6 artifact uses million VND; never mix units).

- MAE = mean(|prediction − actual|)
- RMSE = sqrt(mean((prediction − actual)²))
- MAPE = mean(|prediction − actual| / max(actual, 1)) × 100
- Median APE = median of absolute percentage errors
- P90 APE = 90th percentile (linear interpolation)
- Within-20% = share of rows with APE ≤ 20%
- R² = 1 − SSE/SST
- Signed bias = mean(prediction − actual)

Metrics are **row-weighted**; V1.3 dev-test has 4,403 rows / 4,163 entities (240 repeated
entities). Do not describe them as entity-weighted.

## 5. Distribution policy

- **Keep in Git:** this README, `model_evaluation_manifest.json`, aggregate metric tables,
  hashes, split counts, caveats.
- **Keep local/controlled:** `evaluation.json`, `test_predictions_dev.csv`,
  `train_v1_3_integrated.csv`. They contain row-level dataset derivatives and are excluded
  from Git (`ai-services/artifacts/v1_3/`).
- **Never publish:** raw training rows, entity-level prices/IDs, or the sealed blind set without
  dataset-owner and academic-supervisor approval.
- V1.3 model card is CC BY-NC 4.0; Zenodo source is CC BY 4.0; TiniX is academic and requires
  owner approval for redistribution.
- If a team needs row-level evidence, use an access-controlled academic artifact store or a
  signed release with hashes; do not attach it to a public PR or chat.

## 6. Blind-test protocol (proposal only — not executed)

1. Freeze V1.3 model, preprocessing, calibration and inference code; record commit/tag and hashes.
2. Freeze this protocol and metric definitions before opening 3,102 records.
3. Have an independent evaluator/data custodian unlock once; no V6/V1.3 tuning afterward.
4. Evaluate only the frozen models; report MAE/RMSE/MAPE/median/P90/within-20/R²/bias and
   segment results, regardless of outcome.
5. Do not use blind results to select features, calibration or model version; no second opening.
6. Publish aggregate metrics and caveats; keep row-level blind predictions sealed/controlled.

V6's 684 reserved IDs need a separate audit of labels and leakage before they can be called a
holdout. They are **not** a blind metric today.

## 7. Model display policy

- **V6 remains the active primary** valuation path.
- **V1.3 is preview/experimental**, shown with version, dev-test source and limitations; it is
  never averaged with V6 and never auto-promoted.
- UI must show missing features and that `road_width`/`frontage_width` for V1.3 are **derived
  from access type**, not measured facts.
- SHAP is an explanation of model contributions, not causality.

## 8. Current status

- Evidence hashes: **PASS**.
- Dev-test 4,403 metric reproduction: **PASS** (MAE 3,765,301,650.61 VND).
- Train/test entity overlap: **0**.
- Blind 3,102: **sealed / not read**.
- V6: development validation only; no holdout metric.
