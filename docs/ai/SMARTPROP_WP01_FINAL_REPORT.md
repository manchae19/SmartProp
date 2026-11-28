# SmartProp — WP-01 Final Integration & E2E Closure

**Ngày:** 2026-11-27
**Trạng thái:** `WP_01_IMPLEMENTATION_COMPLETE` · `FLOW_A_REAL_E2E_PASS` ·
`INPUT_CONTRACT_VERIFIED` · `V1_3_ARTIFACT_INTEGRITY_PASS` · **`VALIDATION_PARTIAL`** ·
**`NOT_READY_TO_MERGE`** (Flow B E2E blocked)
**Base:** `bab3d7b` · **Integration HEAD:** `7815bd7`
**Branch:** `feature/valuation-v1-3-hardening-integration`

Nhãn: `FRESH_PASS` · `REUSED_EVIDENCE` · `FAIL` · `BLOCKED` · `NOT_RUN` · `PARTIAL`

---

## A. Final main reconciliation

| Mục | Giá trị |
|---|---|
| `origin/main` | **`bab3d7b`** (PR #38 merged) — không đổi trong phiên này |
| Integration branch | `feature/valuation-v1-3-hardening-integration` @ `7815bd7` |
| Branch hardening gốc | `a7db792` — **không đổi** |
| Main worktree | `feature/tinix-xgboost-standalone` — chỉ thêm docs |
| Thay đổi ngoài phạm vi | `.gitignore` + 2 file `vue.ui` **giữ nguyên**, không đụng |

---

## B. Flow A / Flow B architecture — `FRESH_PASS`

### B.1. Đường đi thực tế (đọc source + E2E)

| Luồng | Route | Payload | Validation |
|---|---|---|---|
| **A** — standalone `ValuationPanel` | React → **Vite proxy `/api/ai`** → FastAPI:8000 | FastAPI shape (`category`, `area_sqm`, `location_feature`) | **Chỉ FastAPI** |
| **B** — posting `PostValuationPanel` | React → `/api/v1/properties/valuation-preview` → **Spring Boot** → FastAPI | Spring Boot shape (`propertyType`, `areaSqm`, `district`) | Spring Boot **+** FastAPI |

Vite: `'/api/ai': {target: aiTarget, rewrite: strip '/api/ai'}`.
`createValuationClient` → `baseUrl = '/api/ai'`, gọi `/predict` và `/model/options`.

### B.2. Lý do lịch sử

Flow A ra đời trước, dùng proxy trực tiếp để panel định giá độc lập hoạt động **không cần
auth và không cần DB** (không lưu valuation history). Flow B nằm trong luồng đăng tin nên
phải đi qua Spring Boot để có auth + property context + lịch sử.

### B.3. Production build — **quan trọng**

`vite.config.js` **chỉ** là dev server. `vite build` tạo bundle tĩnh; **không có proxy**.
Nếu deploy Flow A lên production, cần reverse proxy (nginx) map `/api/ai/*` → FastAPI.
**Nếu không có**, Flow A sẽ gọi `/api/ai/predict` trên chính domain FE và **thất bại**.

→ `NOT_VERIFIED` trong phiên này: chưa có cấu hình nginx/production proxy trong repo.
**Đây là rủi ro triển khai thực tế cần xác nhận riêng.**

### B.4. Khuyến nghị kiến trúc (không thực hiện trong WP-01)

Chuyển Flow A sang Spring Boot (`/api/v1/properties/valuation-preview`) sẽ mang lại:
- Validation đồng nhất
- Auth + rate limit
- Valuation history
- Không phụ thuộc proxy

**Nhưng** việc này thay đổi public access + auth requirement của panel standalone →
**ngoài phạm vi WP-01**. Đề xuất riêng như WP-09.

---

## C. API validation parity — `PARTIAL` (29/30)

Test gọi **thẳng** FastAPI `/predict` với request không hợp lệ (30 case).

| Nhóm | Case | Kết quả |
|---|---|---|
| Area | âm, 0, 1, 99999, NaN, Infinity, null, thiếu | **8/8 PASS** → 422 |
| Category | thiếu, không hỗ trợ (`Shophouse`) | **2/2 PASS** → 422 |
| **Location** | **không hỗ trợ (`Hà Nội`)** | **FAIL → 200** |
| Floors | 0, 99, âm, cho căn hộ | **4/4 PASS** → 422 |
| Subtype | lạ (`penthouse`), cho đất | **2/2 PASS** → 422 |
| Road/frontage | 0, 500, cho căn hộ | **4/4 PASS** → 422 |
| Khác | field lạ (extra=forbid), ward dài, street dài | **3/3 PASS** → 422 |
| Hợp lệ | 6 case | **6/6 PASS** → 200 |

### C.1. Lỗ hổng duy nhất: `location_feature` không được validate

`{"location_feature": "Hà Nội"}` → **200** kèm giá. Model nhận district chưa từng thấy
(xử lý như category unknown) và vẫn trả giá.

| Ảnh hưởng | Chi tiết |
|---|---|
| Flow A | Có thể gửi bất kỳ quận nào qua API |
| Flow B | Spring Boot map `district` → FastAPI cũng không chặn |
| UI | FE chỉ cho chọn quận trong `/model/options` nên **người dùng thường không gặp** |
| Rủi ro | Request trực tiếp / tích hợp bên thứ ba nhận giá cho địa bàn không hỗ trợ |

**Không phải bug của WP-01** — hành vi có sẵn của FastAPI. Ghi nhận để xử lý riêng.

**Không có case nào gây native crash hoặc trả kết quả sai contract.**

---

## D. Input feature parity

| Feature | V1.3 dùng | Flow A UI | Flow A payload | Flow B UI | Flow B payload | FastAPI adapter |
|---|---|---|---|---|---|---|
| property type | ✅ | ✅ | ✅ | ✅ | ✅ | → `normalized_type` |
| district | ✅ | ✅ | ✅ | ✅ | ✅ | → `district` |
| ward | ✅ | ✅ | ✅ | ✅ | ✅ | → `ward` |
| area | ✅ | ✅ | ✅ | ✅ | ✅ | → `area` |
| **street_name** | ✅ | ✅ **mới** | ✅ | ✅ | ✅ | → `raw_street_name` |
| **project_name** | ✅ | ✅ **mới** | ✅ | ✅ | ✅ | → `raw_project_name` |
| **road_width_m** | ✅ | ✅ **mới** | ✅ | ✅ | ✅ | → `raw_road_width` |
| **frontage_width_m** | ✅ | ✅ **mới** | ✅ | ✅ | ✅ | → `raw_frontage_width` |
| floors | ✅ | ✅ | ✅ | ✅ | ✅ | → `floor_count` (HOUSE/VILLA) |
| house_subtype | ✅ (qua type) | ✅ | ✅ | ✅ | ✅ | → `normalized_type=VILLA` |
| rooms | ✅ | ✅ | ✅ | ✅ | ✅ | → `bedroom_count` |
| **bathrooms** | ✅ | ❌ | — | ✅ | ✅ | → `bathroom_count` |
| **house_direction** | ✅ | ❌ | — | ✅ | ✅ | → `raw_house_direction` |
| **balcony_direction** | ✅ | ❌ | — | ✅ | ✅ | → `raw_balcony_direction` |
| access_type | ❌ **không phải feature** | ✅ | ✅ | ❌ | — | không dùng (0,00% effect) |

### D.1. Quyết định

| Field | Hành động | Lý do |
|---|---|---|
| street/project/road/frontage | **Đã thêm vào Flow A UI** (`9a75f03`) | V1.3 dùng thật |
| bathrooms / house_direction / balcony_direction | **Chưa thêm** | Cần quyết định UX — thêm là mở rộng scope |
| access_type | **Giữ** | Đã có trong API contract; không xoá để không phá compatibility |

**Không thêm field giả.** Ba field còn thiếu là **có thật** trong V1.3 nhưng chưa có input
ở Flow A — đề xuất bổ sung ở WP-01b nếu muốn parity hoàn toàn.

---

## E. Isolated MySQL — **BLOCKED**

| Bước | Kết quả |
|---|---|
| Port 3307 | **free** ✅ |
| Datadir cô lập | **TỒN TẠI** — `.scratch/mysql-isolated/data` (229 MB, có db `smartprop`, 62 file) ✅ |
| Isolation guard | `MigrationProfileEnvironmentGuard` yêu cầu URL **literal** `127.0.0.1:3307/smartprop` ✅ |
| mysqld binary | `F:\MySQL\Server8.0\bin\mysqld.exe` = **8.0.46** |
| **Datadir version** | **8.4.13** (theo `auto.cnf`/DD) |
| **Kết quả khởi động** | **THẤT BẠI** |

```
[ERROR] [MY-014061] Invalid MySQL server downgrade: Cannot downgrade from 80413 to 80046.
[ERROR] [MY-010334] Failed to initialize DD Storage Engine
[ERROR] [MY-010020] Data Dictionary initialization failed.
```

**Nguyên nhân:** datadir được tạo bởi MySQL **8.4.13**, máy chỉ có **8.0.46**.
Downgrade giữa minor version **không được phép**.

| Phương án | Khả dụng |
|---|---|
| MySQL 8.4 binary | **KHÔNG có** trên máy |
| Docker (`mysql:8.4`) | **KHÔNG có** Docker |
| Tạo datadir mới 8.0.46 | Cần dựng **toàn bộ** schema 26 version |

### E.1. Vì sao không tự dựng datadir mới

Lineage **phân nhánh** — cùng version number ở nhiều kênh:

```
database/migrations        : V1..V18 (V14__valuation_history, V17__cloudinary, V18__external)
database/research-migrations: V19__tinix_research_staging, V20__poi_taxonomy
database/legacy-hybrid-local: V14__crawler, V17__local_broker, V18__local_avatar, V21..V26
```

`application-hybrid-local-existing-v13-staging.yml` chỉ dùng
`legacy-hybrid-local + research-migrations`, target **26** — nghĩa là nó **giả định DB đã
có V1..V13** từ lineage chuẩn. Không thể dựng từ rỗng bằng profile này.

Đoán thứ tự migration sẽ tạo schema sai, và `ddl-auto: validate` sẽ từ chối khởi động
(an toàn, nhưng không đi tới đâu).

**Không thử đoán. Không sửa migration. Không nới guard.**

---

## F. Migration compatibility

| Kiểm tra | Kết quả |
|---|---|
| PR #38 đưa V26 vào `legacy-hybrid-local` | ✅ `V26__property_coordinate_provenance.sql` (7,1 KB) |
| Staging profile target | **26** — khớp |
| Maven copy `../database` vào classpath | ✅ |
| WP-01 có migration riêng | **KHÔNG** |
| Migration script bị sửa | **KHÔNG** |
| Flyway history bị sửa tay | **KHÔNG** |

WP-01 **không cần migration** — chỉ đổi DTO `ValuationRequest` (record, không phải entity).

---

## G. Flow A real E2E — `FRESH_PASS`

**Môi trường thật:** React `:5173` → Vite proxy → FastAPI `:8000` → XGBoost V1.3 thật.
Playwright + Chromium. **Không mock.**

### G.1. Với địa lý HỢP LỆ — 11/11 PASS

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | Chọn quận Cẩm Lệ | PASS |
| 2 | Basic → có giá | **6,61 tỷ** |
| 3 | + street hợp lệ (`Nguyễn Phước Lan`) | **9,89 tỷ** |
| 4 | Payload có `street_name` | PASS |
| 5 | + road 12 / frontage 6 | **8,98 tỷ** |
| 6 | Payload có `road_width_m` + `frontage_width_m` | PASS |
| 7 | Thêm road/frontage **làm đổi giá** | PASS (9,89 → 8,98) |
| 8 | `area = 0` bị chặn ở client | PASS — **không gọi API** |
| 9 | Không uncaught JS error | PASS |
| 10 | Khôi phục sau lỗi vẫn định giá được | PASS |
| 11 | Mobile 390 px hiển thị kết quả | PASS |

### G.2. API unavailable — 3/3 PASS

Tắt FastAPI, reload, thao tác:

| Kiểm tra | Kết quả |
|---|---|
| Không hiển thị giá | **PASS** |
| UI báo lỗi cho người dùng | **PASS** |
| Không uncaught JS error | **PASS** |

Graceful degradation hoạt động đúng.

---

## H. Flow B real E2E — `BLOCKED`

| Hạng mục | Trạng thái |
|---|---|
| Unit test payload (posting) | `FRESH_PASS` — 11 `advancedValuation` + 7 `postValuationInput` |
| Unit test Spring Boot forward | `FRESH_PASS` — 4 test `floors`/`subtype` |
| **Browser E2E thật** | **`BLOCKED`** |

**Lý do:** không có MySQL tương thích (xem §E). Cần: MySQL 8.4 binary **hoặc** Docker
**hoặc** datadir 8.0.46 mới dựng từ lineage đã xác minh.

**Không** dừng service thành viên. **Không** truy cập 3306. **Không** dùng production creds.

---

## I. Cross-flow prediction parity — `PARTIAL`

Không thể so **giá cuối** vì Flow B blocked. So ở tầng payload (đọc source `ValuationService`):

| Key FastAPI | Flow A | Spring Boot tạo | Tương đương |
|---|---|---|---|
| `category` | trực tiếp | từ `propertyType` → label | ✅ |
| `area_sqm` | trực tiếp | `areaSqm` | ✅ |
| `location_feature` | trực tiếp | `district` | ✅ |
| `ward`, `rooms`, `floors`, `house_subtype` | ✅ | ✅ | ✅ |
| `road_width_m`, `frontage_width_m`, `street_name`, `project_name` | ✅ | ✅ | ✅ |
| `bathrooms`, `house_direction`, `balcony_direction` | ❌ | ✅ | ⚠️ khác |
| `access_type` | ✅ | ❌ | ⚠️ khác (không phải feature) |

**Kết luận:** tương đương về **model feature**; khác biệt chỉ ở input UI sẵn có.
`access_type` không ảnh hưởng (V1.3 đo 0,00%).

**So sánh encoded vector: `NOT_RUN`** — cần Flow B chạy thật.

---

## J. Sensitivity audit — **đính chính quan trọng**

### J.1. Bảng S0–S7 (district Cẩm Lệ, street `Nguyễn Văn Linh`)

| Case | Street | Road | Frontage | Giá | Δ vs S0 |
|---|---|---|---|---|---|
| S0 | — | — | — | **6,605 tỷ** | — |
| **S1** | **NVL** | — | — | **21,021 tỷ** | **+218,25%** |
| S2 | — | 12 | — | 5,986 tỷ | −9,37% |
| S3 | — | — | 6 | 6,427 tỷ | −2,70% |
| S4 | NVL | 12 | — | 18,923 tỷ | +186,49% |
| S5 | NVL | — | 6 | 18,632 tỷ | +182,08% |
| S6 | — | 12 | 6 | 5,985 tỷ | −9,39% |
| S7 | NVL | 12 | 6 | **17,077 tỷ** | **+158,54%** |

`features_used` S7: `street_name='Nguyễn Văn Linh'`, `road_width=12.0`,
`frontage_width=6.0`, `road_width_source='user'`, `frontage_width_source='user'`.

### J.2. ĐÍNH CHÍNH báo cáo trước

Báo cáo trước nói *"thêm road 12 m + frontage 6 m + đường Nguyễn Văn Linh → 2,58×"*,
gợi ý cả ba field cùng góp phần. **Sai.**

| Thành phần | Tác động thực |
|---|---|
| **Chỉ street** | **+218%** |
| **Chỉ road+frontage** | **−9,4%** |
| Cả ba | +158,5% (street bị road/frontage kéo xuống) |

→ **Yếu tố quyết định là `street_name`.** Road và frontage **làm giảm** giá khi đứng một mình.

### J.3. Tổ hợp `(Cẩm Lệ, Nguyễn Văn Linh)` — **KHÔNG có trong training**

| Kiểm tra | Kết quả |
|---|---|
| `Nguyễn Văn Linh` xuất hiện ở | **Thanh Khê 71 · Hải Châu 68 · Sơn Trà 1** |
| **Có ở Cẩm Lệ?** | **KHÔNG** |
| Giá/m² của street đó | Hải Châu **265,0 M** · Thanh Khê **252,4 M** |
| Giá/m² trung vị Cẩm Lệ | **58,4 M** |
| Chênh lệch | **4,3×** |

→ Tổ hợp trong test cũ là **địa lý không hợp lệ**. Model ghép "street cao cấp" + "quận giá
thấp" và ngoại suy +218%.

**Không tự xác nhận địa chỉ hợp lệ khi thiếu nguồn** — đây là kiểm chứng từ **dataset train**.

### J.4. Kiểm chứng lại với tổ hợp HỢP LỆ

| Case | Giá | Δ trong quận |
|---|---|---|
| Cẩm Lệ baseline | 6,605 tỷ | — |
| Cẩm Lệ + `Nguyễn Phước Lan` (118 dòng train) | 9,887 tỷ | **+49,69%** |
| Cẩm Lệ + street + road/front | 8,983 tỷ | +36,00% |
| Hải Châu baseline | 9,188 tỷ | — |
| **Hải Châu + `Nguyễn Văn Linh`** (68 dòng train) | **28,588 tỷ** | **+211,15%** |
| Hải Châu + NVL + road/front | 24,111 tỷ | +162,42% |

**Hải Châu + NVL vẫn +211% với tổ hợp HỢP LỆ.** Kiểm chứng: 28,588 tỷ / 100 m² =
**286 M/m²**, sát median training của street đó (**265 M/m²**).

→ Model **nhất quán với dữ liệu huấn luyện**. Đây không phải bug mapping; đây là
**model limitation**: street là feature có hệ số rất lớn.

### J.5. Road / frontage range (street missing)

| Road (m) | Δ | | Frontage (m) | Δ |
|---|---:|---|---|---:|
| 0,5 | −24,89% | | 0,5 | −14,81% |
| 3 | −27,45% | | 3 | −14,81% |
| 5 | −13,12% | | 5 | +0,16% |
| 7,5 | −1,68% | | 6 | −2,70% |
| 12 | −9,37% | | 10 | +2,22% |
| 20 | −8,98% | | 20 | +19,53% |
| 50 | −8,97% | | 50 | +27,13% |

Road: **không đơn điệu** nhưng biên hẹp (−27% … −1,7%). Frontage: 0,5 và 3 **giống hệt**
(gợi ý binning), rồi tăng dần từ 5. **Không có runaway.**

**Không kết luận quan hệ nhân quả từ model sensitivity.**

---

## K. Street consistency

| Input | Giá | Echo | Nhận xét |
|---|---|---|---|
| `Nguyễn Văn Linh` (Cẩm Lệ) | 21,021 tỷ | ✅ | street category khớp |
| `Nguyễn Tất Thành` (known, khác quận) | 6,812 tỷ | ✅ | +3,1% — biết nhưng không đặc biệt |
| `Đường Không Tồn Tại XYZ 123` (OOV) | 6,793 tỷ | ✅ | +2,9% — **≈ known-khác-quận** |
| rỗng | 6,605 tỷ | None | baseline |
| `nguyễn văn linh` (thường) | **21,021 tỷ** | ✅ | ✅ **casefold hoạt động** |
| `Đường Nguyễn Văn Linh` (có tiền tố) | 6,793 tỷ | ✅ | ⚠️ **tiền tố "Đường " không bị bỏ → OOV** |

### K.1. Kết luận

| Phát hiện | Mức |
|---|---|
| **Casefold đúng** — chữ thường = chữ hoa | ✅ tốt |
| **Tiền tố "Đường " phá khớp** → OOV, mất toàn bộ tín hiệu street | ⚠️ **rủi ro UX thực tế cao** |
| OOV ≈ known-khác-quận (+3%) → model xử lý OOV an toàn, không crash | ✅ |
| Không có kiểm tra district/street consistency ở server | ⚠️ (xem §C.1) |

**Không tự geocode thành tọa độ cấp thửa.** Không tự xác nhận địa chỉ hợp lệ.

---

## L. Backend full regression — `FRESH_PASS`

**Đây là FULL suite** (không phải targeted — báo cáo trước 21/21 là targeted).

```
Tests run: 228, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

Bao gồm: `ValuationServiceTest` (12) · `ValuationHistoryService` (6) ·
`PropertyCoordinateAuditService` (5) · `PropertyCoordinateAuditTest` (15) ·
`PrePurchaseStreetOf…` (7) · `NearbyService` (13) · `PoiService` (3) ·
`PropertyRouteService` (11) · `AreaBoundary` (2) · `AdvisorPreferences` (5) · và toàn bộ còn lại.

**Không hồi quy** ở Coordinate Provenance / Accuracy Policy / GIS / Market / Comparable /
Advisor / Pre-Purchase / Recommendation / Property posting / Valuation history.

---

## M. FastAPI full regression — `PARTIAL` (2 pre-existing)

| Chỉ số | Giá trị |
|---|---|
| Passed (khi loại 2 file RAG lỗi collection) | **209** |
| Skipped | **20** |
| Subtests passed | **84** |
| Collection errors | **2** |

### M.1. Bằng chứng hai lỗi là pre-existing

| Bước | Kết quả |
|---|---|
| Test files | `tests/test_rag_area_filter.py`, `tests/test_rag_public_projection.py` |
| Stack trace | `ImportError: cannot import name 'area_spec' from 'app.rag.personalization'` |
| Tồn tại trên `bab3d7b`? | **CÓ** — `git show bab3d7b:ai-services/tests/test_rag_area_filter.py` |
| `area_spec` trên `bab3d7b`? | **KHÔNG** — `def area_spec` không tồn tại |
| **Chạy trên base `bab3d7b`** (worktree tạm) | **CÙNG ImportError, cùng 2 file** |
| Trên integration HEAD | **CÙNG ImportError, cùng 2 file** |

→ **Cùng root cause. Không do WP-01.** Đã xoá worktree tạm sau khi kiểm.

**Không sửa RAG trong WP-01** (ngoài phạm vi định giá).

**Không ghi "toàn bộ suite PASS"** — 2 file không collect được, 20 test skip.

---

## N. Frontend full regression — `FRESH_PASS`

| Hạng mục | Kết quả |
|---|---|
| Unit suite (`node --test tests/*.test.mjs`) | **67 / 67 PASS** |
| Flow A E2E (địa lý hợp lệ) | **11 / 11 PASS** |
| Flow A E2E (API down) | **3 / 3 PASS** |
| Responsive 390 px | **PASS** |
| Invalid input (`area = 0`) | **PASS** — client chặn, không gọi API |
| Flow B E2E | **BLOCKED** |

---

## O. Production build — `FRESH_PASS`

```
✓ built in 2,09 s
```

---

## P. Database integrity

| Kiểm tra | Kết quả |
|---|---|
| MySQL 3306 (production) | **KHÔNG truy cập** — chỉ quan sát port |
| MySQL 3307 | **KHÔNG khởi động được** (version mismatch) — process đã abort, port free |
| Datadir `mysql-isolated` | **KHÔNG sửa** — chỉ đọc metadata, không ghi |
| Service thành viên | **KHÔNG dừng** |
| Migration chạy | **KHÔNG** |
| Backup/schema copy từ 3306 | **KHÔNG** |
| Production credentials | **KHÔNG dùng** |

**Port sau khi dọn:** 5173 free · 8000 free · 3307 free.

---

## Q. Model artifact hash — `FRESH_PASS`

| File | SHA256 | Trạng thái |
|---|---|---|
| `model.json` | `3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03` | **không đổi** |
| `calibration.json` | `17632bdf…fbfe645` | **không đổi** |
| `feature_schema.json` | `84be275b…61e7ea` | **không đổi** |

`GET /health` → `{"status":"ok","model_version":"v1.3","model_ready":true}`

Không train. Không đổi weights. Không bật Shadow. Không cài dependency mới.

---

## R. Remaining blockers

| # | Blocker | Loại | Gỡ bằng |
|---|---|---|---|
| 1 | **Flow B E2E** | **chặn gate** | MySQL 8.4 binary **hoặc** Docker **hoặc** datadir 8.0.46 dựng từ lineage đã xác minh |
| 2 | `location_feature` không validate ở FastAPI | trung bình | Whitelist theo `/model/options` |
| 3 | Tiền tố "Đường " phá khớp street | trung bình | Strip prefix ở adapter (đo tác động trước) |
| 4 | 2 test RAG pre-existing fail | thấp (ngoài scope) | Sửa `area_spec` hoặc xoá test cũ |
| 5 | Production reverse proxy cho `/api/ai` | **cao khi deploy** | Cấu hình nginx, chưa có trong repo |
| 6 | Flow A thiếu `bathrooms`/`house_direction`/`balcony_direction` | thấp | WP-01b nếu muốn parity đủ |
| 7 | `playwright` nằm trong `vue.ui/node_modules` | thấp | Cleanup riêng |

---

## S. Final HEAD SHA

```
Base (origin/main)   bab3d7b
Integration HEAD     7815bd7
Branch               feature/valuation-v1-3-hardening-integration
Worktree             F:\SmartProp\.worktrees\v13-hardening-integration
Hardening gốc        a7db792   (không đổi)
Main worktree        (commit docs của phiên này)
```

**Không commit:** raw data · DB dump · model weights · credentials · `node_modules` · `dist`.

---

## T. Final gate

```
WP_01_IMPLEMENTATION_COMPLETE
FLOW_A_REAL_E2E_PASS
INPUT_CONTRACT_VERIFIED
V1_3_ARTIFACT_INTEGRITY_PASS
VALIDATION_PARTIAL
NOT_READY_TO_MERGE
```

**Không phải `FLOW_B_REAL_E2E_PASS`** — Flow B chưa chạy thật.
**Không phải `READY_FOR_FINAL_REVIEW`** — còn blocker #1.

### Đề xuất thứ tự tiếp theo

| # | Việc | Ghi chú |
|---|---|---|
| 1 | Lấy MySQL 8.4 binary **hoặc** Docker → chạy Flow B E2E | Gỡ blocker duy nhất của gate |
| 2 | Whitelist `location_feature` theo `/model/options` | Nhỏ, giảm rủi ro API |
| 3 | Strip tiền tố đường ở adapter | Đo tác động trước |
| 4 | Xác nhận reverse proxy production cho `/api/ai` | Rủi ro deploy |
| 5 | WP-01b: thêm 3 field còn thiếu cho Flow A | Quyết định UX |
