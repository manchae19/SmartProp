# SMARTPROP — PR #43 RECOVERY, MAIN INTEGRATION & VALIDATION REPORT

- **Repository**: `https://github.com/manchae19/SmartProp`
- **Pull Request**: `https://github.com/manchae19/SmartProp/pull/43` (kept **Draft**)
- **Branch**: `feature/advisor-land-runtime-20261126`
- **Isolated Worktree**: `F:\SmartProp\.worktrees\pr43-advisor-land-integration`
- **Original PR #43 HEAD**: `f59edf223c98249ee6104c367c34537bd851aea5` (merge-base `bab3d7b5f71287af2de74f26afebb03db72b9bab`)
- **Integrated Approved `main` Baseline**: `d6be176f6c7fa27a1f33836e627965104f6a8d27`
- **Merge Commit (`--no-ff`)**: `d116508375abdc06ef9435c7d309e9dcce67b5da`
- **Reconciliation & Security Test Commit**: `dcb8805d26fddc87ccd24684d8175209f7d8741b`

---

## 1. Executive Summary

PR #43 (`feature/advisor-land-runtime-20261126`, previously 86 commits behind `origin/main` with 11 content conflicts and 8 additional overlapping files) has been integrated with `origin/main` (`d6be176f6c7fa27a1f33836e627965104f6a8d27`) via a normal non-fast-forward merge without rebase, force-push, migration edits, model artifact modifications, or protected database access.

All previously accepted `main` baselines — **PR #38** (Coordinate Provenance V1), **PR #44** (XGBoost V1.3 sole production valuation), **PR #45** (RAG session, budget, cancellation, and stale-confirmation invariants), **PR #46** (SAFE public/research separation & loopback boundary), **PR #47** (WP-02 Comparable evidence), and **PR #49** (shared `httpClient.js` session generations & React UI refresh) — remain authoritative and verified green alongside PR #43's Hòa Xuân land search, land maps/detail views, cross-source buyer search, estimated-origin nearby POIs, and persistent local runtime launcher.

---

## 2. Conflict-Resolution & Overlap Matrix (19 Overlapping Files)

| File | Overlap Type | Resolution & Authoritative Contract |
|---|---|---|
| `ai-services/app/rag/config.py` | Conflict | Preserved `main` local staging SQL settings (`sql_port=13306`, port `3306` refusal without `sql_allow_production`) plus PR #43 operator comment. |
| `ai-services/app/rag/followup.py` | Conflict | Preserved `main` PR #45 `transaction_information`, `buy_to_let`, `mask_recurring_amounts`, `invalid_area_text`, and `explicit_search` guards; retained PR #43 `DANANG_DISTRICTS` edit detection and expanded `gia (?:dinh\|tang\|...)` non-price filter. |
| `ai-services/app/rag/money.py` | Conflict | Preserved `main` `recurring_amounts`, `mask_recurring_amounts`, and `format_vnd` (`" đồng"`) plus PR #43 negative-amount lookbehind guard (`(?<!\w)am`). |
| `ai-services/app/rag/orchestrator.py` | Conflict | Preserved `main` PR #45 `_listing_continuation`, `_prepare_listing_transaction` (`RENT`, `PURCHASE_DECLINED`, `RENT_DECLINED`, `CONFLICT`, `RECURRING_AMOUNT_CLARIFICATION`), `address_search`, `merge_area`, and `_enrich`; wired PR #43 `AMENITIES` continuation guard, `buyer_search`, `land_advisor` (`landId` reference selection + domain retirement), and `listOwner` tracking *after* transaction guards so land/buyer routing never bypasses rental or cancellation invariants. Removed dead `within_area` helper. |
| `ai-services/app/rag/personalization.py` | Conflict + Auto-merge shadow | Preserved `main` `merge_area`, `matches_area`, multi-bound `area_spec` (rejecting negative areas such as `-80 m²`), and `intake`; removed duplicate shadowed `area_spec`/`apply_area`/`describe_area` block brought in from pre-merge PR #43. |
| `ai-services/app/rag/session.py` | Conflict | Preserved `main` `Context.public()` area/price criteria projection (`minPriceVnd`, `maxAreaSqm`, `minAreaExclusive`, `maxAreaExclusive`). |
| `ai-services/app/rag/tools.py` | Conflict + Auto-merge shadow | Preserved `main` `_public_text` (HTML unescape + zero-width strip + phone/email/marker redaction), `_published_record`, `matches_area`, `_public_search`, and `sql_use_views` support (`rag_public_properties`); removed duplicate weaker `_public_text` and obsolete `SQL_PUBLIC_VIEWS_NOT_AVAILABLE` guard from pre-merge PR #43. Kept `allowEstimatedOrigin=true` on `property_nearby`. |
| `ai-services/app/rag/api.py` | Auto-merge | Combined `main` `guest_turns` concurrency lock with PR #43 `X-SmartProp-Chat-Revision`, `X-Content-Type-Options: nosniff`, `check_chat_origin` (`RAG_ALLOWED_ORIGINS`), and conditional `create_land_router()` mount when `land_enabled()` is true. |
| `ai-services/app/rag/schemas.py` | Auto-merge | Combined `main` `ranges_valid` area validator with PR #43 UUID-validated `landId` field on `ChatRequest`. |
| `ai-services/app/rag/scope.py` | Auto-merge | Combined `main` `recurring_amounts` scope guard with PR #43 courtesy/capability direct responses. |
| `backend/.../HybridRecommendationService.java` | Conflict | Preserved `main` PR #46 `recommendPublic` / `recommend(request, research, allowDemo)` isolation; retained PR #43 `ApiException(503, "PERSONALIZED_RANKING_DISABLED", ...)` when `v11Enabled=false`. |
| `backend/.../PropertyCoordinateAuditService.java` | Auto-merge (signature drift fixed) | Preserved `main` `pendingPage`, `stats`, and `reviewDetail`; updated PR #43 `legacyReference(Property)` to match `main`'s 11-parameter `PropertyCoordinateAudit.derive(...)` signature (`evidenceReference = null`, `distanceAnalysisEligible = false`, `parcelAnalysisEligible = false`). |
| `frontend/src/shared/lib/httpClient.js` | Conflict | Preserved `main` PR #49 implementation in full (`beginAuthChange`, `finishAuthChange`, `authGeneration`, `authTransition`, `installCredential`, `rotate({ allowNewIdentity: true })`); dropped pre-merge PR #43 `storageSessionHint` gate which would have broken cookie-based session restoration without prior `localStorage`. |
| `frontend/src/features/prediction/chatPresentation.js` | Conflict | Combined `main` `addressSearch` summary handling with PR #43 `buyerSearch`, `LAND_*`/`FLOOD_CATALOG` response kinds, and `chatCriteriaSummary`. |
| `frontend/src/features/prediction/chat.js` | Auto-merge | Combined `main` `validateEmptySearch` with PR #43 `BUYER_SEARCH` (`<=15%` over-budget cap, UUID/source checks) and `LAND_V1` (`demoOnly: true`, zero mixed citations/listings) packet validation. |
| `frontend/src/app/router.js` | Auto-merge | Preserved `main` `/news`, `/admin/coordinate-review`, and `SESSION_CHANGED` guard alongside PR #43 `/land/:id` (`LandDetailView`). |
| `frontend/src/features/property/ListingDetailView.jsx` | Auto-merge | Preserved `main` accessible gallery focus trap and WP-02 `ComparableEvidenceLookup` alongside PR #43 `nearbyPoiRows` 1 km straight-line POI section. |
| `ops/Caddyfile` | Conflict | Preserved `main` PR #46 `route { @loopbackOnly ... @loopbackVariant ... @ambiguousApiPath ... }` blocks and `-X-SmartProp-Demo-Key` / `-Forwarded` header stripping across `/api/chat/health` (`GET` -> `8001`), `/api/chat` (`8082`), `/api/land/*` (`GET` -> `8001`), and `/api/*` (`8080`), plus SPA fallback. |
| `README.md` | Auto-merge | Combined `main` setup docs with PR #43 unified local runtime launcher instructions (`ops/*-smartprop-local.ps1`). |

---

## 3. Re-evaluation of Original PR #43 Known Issues & Additional Fixes

1. **`format_vnd` `"đồng"` vs `"VND"`**: Re-evaluated against `origin/main` (`d6be176f`). Authoritative `main` tests (`test_rag_area_filter.py`, `test_rag_ported_utilities.py`) and `money.py` standardize on `" đồng"` (e.g., `"3.000.000.000 đồng"`). Preserved `main` without weakening any test.
2. **Generic `"nhà"` property-type detection**: Verified in `followup.py` (`detect_property_type` leaves bare `"nhà"` unrestricted so platform home searches include apartments/houses/villas) while `buyer_search.py` only activates on explicit land/buyer-intake triggers (`lô đất`, `tìm đất`, `mua đất`, `đất ở`, `đất nông nghiệp`, or standalone `tôi có <budget>`). Generic `LAND` (`"tìm đất"`) queries both housing and agriculture in `buyer_search` without forcing residential-only or agriculture-only classification.
3. **`PublishedPropertyRepository` / public projection tests**: After removing the duplicate `_public_text` shadow and obsolete `sql_use_views` error in `tools.py`, `test_rag_public_projection.py` and `test_rag_sql_settings.py` pass completely.
4. **`ai-services/tests/test_security_audit.py`**: Executed in `ai-services\.venv` (`Python 3.14.6`, `pandas 3.0.6`) with `SMARTPROP_V1_3_MODEL_DIR=F:\SmartProp\ai-services\artifacts\v1_3` — **PASS** (`0` failures).
5. **Additional Bug Fixed (`buyer_search.py` unsupported locality order)**: Moved `requested_location(request.question)` before `if not state.get('location'):` so a first-turn query naming an unsupported locality (e.g., `"Tìm đất ở Hội An dưới 3 tỷ"`) immediately returns the explicit non-substitution refusal instead of asking for a Đà Nẵng district.
6. **Synthetic Demo Provenance Labels (`landApi.js`, `LandResults.jsx`, `BuyerSearchResults.jsx`)**: Kept synthetic pricing explicit (`SIMULATED_DEMO: 'Giá giả lập (demo)'` instead of `'Giá tham khảo'`), rendered `· Giả định` tags on demo profile fields in `LandResults.jsx`, and labeled land cards `'Dữ liệu đất Hòa Xuân (demo)'` in `BuyerSearchResults.jsx`.

---

## 4. Security, Provenance & Runtime Audit Summary

- **Coordinate & GIS Security (PR #38 + PR #43)**:
  - `PropertyCoordinateAuditService.legacyReference` assigns `verificationStatus="UNVERIFIED"`, `coordinateSource="UNKNOWN"`, `accuracyLevel="UNKNOWN"`, `distanceAnalysisEligible=false`, `parcelAnalysisEligible=false`, and `referenceMapEligible=true` *only* when `DanangSpatialValidator` confirms `VERIFIED_EXACT` or `VERIFIED_BOUNDARY_BUFFER`.
  - Out-of-bounds pins (`OUTSIDE_DANANG_BOUNDS`) and `REJECTED` audit records (`revision >= 1`, `referenceMapEligible=false`) remain blocked even when `allowEstimatedOrigin=true`.
  - `NearbyService.advisorOrigin(id)` (used for verified commute analysis) continues to require `distanceEligible(id)` and returns `null` for estimated pins.
- **Land API & Overview Cache**:
  - `land_enabled()` fails closed (`False`) when `RAG_LAND_ENABLED` is `false`/`0`/`off` or any of the 15 required Hòa Xuân dataset files is absent; `/land/*` routes are not mounted when disabled.
  - `/land/records/{record_id}` and `/land/neighbors` enforce `^[A-Za-z0-9._-]{1,80}$`, strip `geometry`, `sourceFile`, and `reviewFlags` from neighbor feature properties, cap `/land/flood-map` at `200` IDs, and mark `verifiedForThisParcel: false`.
  - `OverviewService` restricts LLM output to binary indices (`0` or `1`) over pre-vetted grounded Vietnamese sentence pairs and rejects tampered disk cache files.
- **Runtime Launcher & RAG Preparation**:
  - `ops/local-runtime.ps1` serializes start/stop per checkout via named mutex (`Local\SmartPropRuntime-<sha256>`) and reuses healthy services without killing external processes; `ops/stop-smartprop-local.ps1` verifies `root`, `CreationDate`, and `CommandLine` before stopping any PID.
  - `ai-services/scripts/prepare_rag_local.py` acquires `.prepare.lock` (`msvcrt.LK_NBLCK` / `fcntl.LOCK_EX`) and reuses valid corpus/FAISS artifacts without rebuilding unnecessarily or touching MySQL `3306`.

---

## 5. Fresh Validation & Regression Evidence

### 5.1 Automated Unit & Integration Suites (Mocked / In-Process)

| Suite | Command | Result | Details |
|---|---|---|---|
| **Python FastAPI + Full RAG + Land + Security + V1.3** (54 files) | `pytest -rs -q tests/test_*.py tests/parity/test_*.py` | **PASS** (`Exit 0`) | **`1188 passed`**, `19 skipped`, `0 failed`, `105 subtests passed` (includes `test_pr43_land_and_rag.py` `8/8`, `test_security_audit.py`, `test_v1_3_unit.py`, PR #45 transaction/cancellation/area/address suites). |
| **Spring Boot Backend + Security + GIS + WP-02** (31 suites) | `.\mvnw.cmd -o -q test` | **PASS** (`Exit 0`) | **`277 passed`**, `0 failed`, `0 errors`, `0 skipped` (includes `Pr43EstimatedOriginSecurityTest` `5/5`, `NearbyServiceTest`, `ResearchAccessHttpSecurityTest` embedded Tomcat `RemoteIpValve`, WP-02 comparables). |
| **Frontend Recursive Unit & Contract** (28 files) | `node --test <all *.test.mjs/*.test.js>` | **PASS** (`Exit 0`) | **`251 passed`**, `0 failed`, `0 skipped` (includes `pr43LandAndNearbyContract.test.mjs` `4/4`, PR #49 `httpClientRefreshEpoch`, `httpClientInitializationAba`, `pr49SharedAuthTransitions`, Market/Advisor session revocation). |
| **Vite Production Build & Public Assets Gate** | `npx vite build` | **PASS** (`Exit 0`) | `278` modules transformed; `smartprop-approved-public-assets` plugin passed. |
| **Caddyfile Static Security & Route Check** | Structural assertion script on `ops/Caddyfile` | **PASS** (`9/9`) | Verified `route` ordering, research loopback 403 blocks, `@ambiguousApiPath`, `/api/chat/health`, `/api/chat`, `/api/land/*`, header stripping, and SPA fallback. |

**Itemized Python Skips (19 total, 0 failures)**:
- `tests/test_api_v6.py` (13 skips): `V6 is no longer the public model; see test_v6_v1_3_contract.py` (expected per PR #44).
- `tests/test_planning_data.py` (1 skip): `Optional offline real dataset is not distributed with application source`.
- `tests/test_vision_detector.py` (5 skips): `yolov8n.pt weights are not present`.

### 5.2 Actual Runtime & Real Headless Chromium Suites

| Runtime Check | Environment | Result | Details |
|---|---|---|---|
| **WP-02 Chromium Browser Regression** | Real headless Chromium + Vite (`wp02-browser.mjs`) | **PASS** (`Exit 0`) | All **12 / 12** WP-02 browser groups passed (Comparable API form, token downgrade/restoration, criteria invalidation, mobile responsive, `ListingDetailView` `SIMILAR_LISTING`, Valuation/PostValuation/Advisor separation). |
| **PR #43 Land, Chat, Map & Listing Chromium E2E** | Real headless Chromium (`1440x900`, `768x1024`, `390x844`) + Vite + loopback upstream | **PASS** (`Exit 0`) | **5 / 5** suites passed: (1) `/land/:id` detail + overview + demo disclaimers + zero horizontal overflow at `1440/768/390`; (2) `/land/non-existent-record` graceful 404 UI; (3) `/advisor/chat` `LAND_SEARCH` cards + Leaflet `LandMap` + `SelectedLand` + `Giả định` tags; (4) `/advisor/chat` `BUYER_SEARCH` cross-source SmartProp + Hòa Xuân demo cards + `+15%` reference note; (5) `/listing/:id` PR #43 1 km POIs + estimated-origin notice + PR #47 `ComparableEvidenceLookup` RBAC guard. Zero uncaught exceptions. |
| **Embedded Tomcat TCP HTTP Security** | Real embedded Tomcat (`ResearchAccessHttpSecurityTest`) | **PASS** (`Exit 0`) | Verified loopback vs proxy-forwarded research route blocking and `RemoteIpValve` behavior. |
| **Launcher Mutex Contention & Foreign-PID Guard** | Real PowerShell processes + named OS mutex (`ops/local-runtime.ps1`, `ops/stop-smartprop-local.ps1`) | **PASS** (`Exit 0`) | Concurrent `Enter-SpRuntimeLock` blocked with contention error; `stop-smartprop-local.ps1` refused to kill mismatched PID/root/command process. |
| **V1.3 Model Artifact Checksums & Zero Diff** | Real `artifacts/v1_3/*.json` + `PredictorV1_3` load | **PASS** | `model.json` (`3c56b693...`), `feature_schema.json` (`84be275b...`), `calibration.json` (`17632bdf...`), `artifact_manifest.json` (`419599ec...`) verified; zero Git diff on `ai-services/artifacts` and `backend/src/main/resources/db/migration`. |
| **Parallel Mentor Demo & Protected DB Isolation** | Read-only port check | **PASS** | Port `5183` mentor demo untouched and listening; zero connections/writes/migrations executed against MySQL `3306` or `3307`. |

---

## 6. Remaining Environmental Limitations (Non-Blocking, Truthfully Reported)

1. **Optional Hòa Xuân Dataset Not Versioned in Git**: `SMARTPROP_DATA/raw/land_demo_hoa_xuan/HX-LAND-DEMO-20261126` is intentionally gitignored; in environments without that dataset unpacked, `land_enabled()` returns `False`, `/land/*` is unmounted, and standard SmartProp chat/property search operates normally.
2. **Caddy Binary Runtime**: `caddy` executable is not installed on this Windows machine; `ops/Caddyfile` was validated structurally and proxy header/route security was verified via embedded Tomcat HTTP tests, while live `caddy run` binary execution is `NOT_RUN`.
3. **MySQL `LiveIT` / V24–V26 Live DB**: Per Section 8 database safety rules, protected MySQL instances (`3306`, `3307`) were not accessed or migrated (`LiveIT`: `NOT_RUN`).

---

## 7. Required PR #43 Verification Gates

- `PR43_CURRENT_MAIN_INTEGRATED`: **PASS** (`origin/main` @ `d6be176f6c7fa27a1f33836e627965104f6a8d27` ancestor-verified)
- `PR43_PR45_RAG_CONTRACT_PRESERVED`: **PASS**
- `PR43_PHASE0_SECURITY_PRESERVED`: **PASS**
- `PR43_WP02_REGRESSION_PASS`: **PASS** (Backend + Frontend + 12/12 Chromium groups)
- `PR43_PR49_SHARED_SESSION_PRESERVED`: **PASS** (`httpClient.js` + `pr49SharedAuthTransitions` / `httpClientRefreshEpoch` / `httpClientInitializationAba`)
- `PR43_LAND_FEATURE_ISOLATION_PASS`: **PASS**
- `PR43_GIS_COORDINATE_SECURITY_PASS`: **PASS**
- `PR43_LAND_DATA_PROVENANCE_PASS`: **PASS**
- `PR43_FULL_RAG_REGRESSION_PASS`: **PASS**
- `PR43_BACKEND_REGRESSION_PASS`: **PASS** (`277/277`)
- `PR43_FRONTEND_REGRESSION_PASS`: **PASS** (`251/251` + `vite build` exit `0`)
- `PR43_BROWSER_REGRESSION_PASS`: **PASS** (`12/12` WP-02 + `5/5` PR #43 Chromium E2E across `1440/768/390`)
- `PR43_V1_3_ARTIFACT_INTEGRITY_PASS`: **PASS**
- `PR43_MIGRATIONS_UNCHANGED`: **PASS**
- `PR43_REMOTE_HEAD_VERIFIED`: **PASS**

Status tokens:
- `PR43_READY_FOR_INDEPENDENT_REVIEW`
- `WAITING_FOR_PR43_MERGE_AUTHORIZATION`
