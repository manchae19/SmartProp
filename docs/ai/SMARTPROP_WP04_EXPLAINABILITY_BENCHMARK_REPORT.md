# SmartProp â€” WP-04 Explainability Benchmark Report (Phase A)

**NhÃ£n:** `FRESH_EVIDENCE` (cháº¡y tháº­t trÃªn model V1.3) Â· input **synthetic**.

## 1. MÃ´i trÆ°á»ng & integrity

| | |
|---|---|
| Code SHA | `a0e3834` (worktree `research/wp04-explainable-ai`) |
| Python | 3.11.9 Â· xgboost **3.4.1** Â· venv `ai-services/.venv` |
| `model.json` | `3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03` âœ… |
| `calibration.json` | `17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645` âœ… |
| `feature_schema.json` | `84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea` âœ… |
| `artifact_manifest.json` | `419599ecbefbe24bbbc1754a0224a7c25747ac3a08827d4e14ea62a5e41f2dce` (khÃ´ng pinned; ghi nháº­n) |

## 2. Fixture

- 7 district Ã— 3 category (`HOUSE`, `LAND`, `APARTMENT`) Ã— 4 profile (`MINIMAL`, `TYPICAL`,
  `RICH`, `MISSINGNESS`) = **84 case** + **10 extras** (small/large area, NFC/NFD district,
  missing ward, invalid area, invalid location, ward/street observed, LAND+rooms).
- **VILLA khÃ´ng cÃ³ trong `normalized_type`** â€” villa lÃ  `house_subtype` cá»§a HOUSE â‡’ ghi nháº­n,
  khÃ´ng táº¡o category giáº£.
- Ward/street chá»‰ dÃ¹ng khi láº¥y tá»« vocabulary artifact; khÃ´ng bá»‹a Ä‘á»‹a danh.
- KhÃ´ng database, khÃ´ng research dataset, khÃ´ng holdout.

## 3. Káº¿t quáº£ (digest `acd5fff557a861bb`)

| Kiá»ƒm tra | max | median | p95 |
|---|---|---|---|
| TreeSHAP additivity (tÆ°Æ¡ng Ä‘á»‘i) | **1.499e-06** | 3.674e-07 | 1.036e-06 |
| Naive `expm1(z)` reconstruction | **2.108e-10** | 4.902e-11 | 1.368e-10 |
| Calibration reconstruction | **3.612e-06** | 3.612e-06 | 3.612e-06 |
| Top-K + remainder â‰¡ full (log unit) | **0.1239** | 0.0399 | 0.0901 |
| Grouped â‰¡ total | **0.0** | 0.0 | 0.0 |

`passed 84 Â· failed 0 Â· invalid-rejected 2 Â· exit 0`.
Provenance Ä‘áº¿m: OBSERVED 301 Â· DERIVED 1232 Â· MISSING 203 Â· NOT_APPLICABLE 112.

## 4. Latency (offline, CPU, single run, khÃ´ng warm-up tÃ¡ch riÃªng)

`median 39.32 ms Â· p95 47.99 ms` cho **toÃ n bá»™** `predict_from_v6_payload`
(adapter + transform + predict + SHAP + formatting). ÄÃ¢y lÃ  sá»‘ local, **khÃ´ng** pháº£i SLA.

## 5. Determinism

Hai láº§n cháº¡y cÃ¹ng cáº¥u hÃ¬nh cho digest **giá»‘ng nhau** (`acd5fff557a861bb`). Digest bao gá»“m
metric + provenance counts; **loáº¡i trá»«** latency vÃ  `results` (non-deterministic fields).

## 6. NgÆ°á»¡ng dung sai vÃ  lÃ½ do

- Additivity `1e-5` tÆ°Æ¡ng Ä‘á»‘i: margin float32 ~20â€“25, Ä‘o Ä‘Æ°á»£c tá»‘i Ä‘a 1.5e-6 â‡’ headroom ~7Ã—.
- Calibration `1e-5` tÆ°Æ¡ng Ä‘á»‘i: `exp()` trÃªn `z` float32 khuáº¿ch Ä‘áº¡i sai sá»‘, Ä‘o Ä‘Æ°á»£c 3.6e-6.
- Naive `1e-9` tÆ°Æ¡ng Ä‘á»‘i: cÃ¹ng `z` float64, chá»‰ khÃ¡c rounding int.
KhÃ´ng ná»›i thÃªm Ä‘á»ƒ "cho PASS"; cÃ¡c ngÆ°á»¡ng nÃ y suy ra tá»« precision thá»±c táº¿ cá»§a model.

## 7. Limitations

- Input synthetic â‡’ **khÃ´ng** suy ra hÃ nh vi thá»‹ trÆ°á»ng.
- VILLA khÃ´ng phá»§ (khÃ´ng pháº£i category trong schema).
- Ward/street coverage háº¡n cháº¿ do categorical cá»§a booster.
- KhÃ´ng Ä‘o cold-start riÃªng, khÃ´ng Ä‘o memory.
- ChÆ°a cháº¡y `test_valuation_shap_contract.py` / `probe_shap.py` (`NOT_RUN`).

## 8. CÃ¡ch cháº¡y

```bash
python docs/ai/benchmark/wp04_explainability_benchmark.py \
  --artifacts-dir <repo>/ai-services/artifacts/v1_3 --assertions
python docs/ai/benchmark/wp04_explainability_benchmark.py \
  --artifacts-dir <repo>/ai-services/artifacts/v1_3
```

DÃ¹ng **venv cá»§a project** (`ai-services/.venv`).
