# WP-06 B3 · Input quality và bounded drift

## 22 feature và provenance

Registry khớp exact order của official `feature_schema.json`, AST transform và synthetic row đi qua transform thật. Sáu numeric raw, tám presence indicators, một derived frontage ratio và bảy categorical model features. B3 adapter nhận tuple 22 typed facts. Mỗi fact chứa raw-present bool, matrix status và provenance enum. Adapter không nhận raw price, GPS, địa chỉ, ward/street/project text hoặc feature vector. Inputs đến khi wiring sau này phải được phân loại bên cạnh existing transform. Hiện chỉ fixtures gọi adapter.

Ba nhóm số đo giữ độc lập. `feature_raw` đếm trước adapter, gồm input hiện diện nhưng invalid hoặc bị legacy adapter bỏ. `feature_matrix` bảo toàn present/missing/invalid/unknown observed semantics, kể cả numeric invalid bị chuyển thành NaN. `feature_effective` áp dụng domain applicability khi báo coverage per segment. Unknown chỉ áp dụng category và tách khỏi missing. Flags derived/defaulted/unverified độc lập. `USER_ASSERTED` không bao giờ tự thành `VERIFIED_SOURCE`. Derived indicator không được nhận raw-present hoặc direct verified provenance. Legacy bỏ các field optional mới và có thể mặc định width, nên được đếm ở mode riêng. Fixtures kiểm road-width invalid ở compat-real, road width default ở compat-legacy, raw street bị bỏ ở legacy, unknown street với `has_street=1`, prefix normalize ở canonical.

| Loại hình | Quy tắc áp dụng |
| --- | --- |
| HOUSE, VILLA | Giữ model-state của phòng, tầng, mặt tiền, hướng, địa chỉ coarse. Optional fields thiếu vẫn được phân loại missing khi applicable. |
| LAND | Floor/bedroom/bathroom, indicators tương ứng và hai direction fields là `not_applicable` ở domain reporting. Indicator thực tế vẫn được tính vào matrix-derived counters. |
| APARTMENT | Phòng/tầng/hướng căn hộ giữ theo matrix. Mặt tiền lô đất, `has_frontage` và ratio là `applicability_unknown` khi chỉ có property type. Có thể xác minh riêng schema policy tương lai. |
| OTHER | Unknown applicability cho các trường lệ thuộc type, giữ area/district và fields chung theo state. Không tạo dimension mới. |

Global, type, district và input mode đếm từng segment riêng. Surface slots vẫn giữ trong registry nhưng B3 FastAPI chưa gán authenticated origin. Unknown district gom `other` qua allowlist. Ward/street/project chỉ có state, không có category labels. Khi dashboard sau này đọc slices, giữ small-n privacy suppression theo governance và tách reporting cohort khỏi WP‑02 Comparable featureCoverage. Hard ceiling thực đo **3.986/4.096** slots. Không nhân các dimensions.

## Drift synthetic và applicability của số đo

Drift mặc định off. Hàm `compare` chỉ đánh giá `SYNTHETIC` với immutable reference đã approve trong fixture. Key gồm release, registry schema, Duan policy, input mode, population và reference version. Match đầy đủ, không tự sử dụng current window làm reference. Reference và current phải đủ minimum n ở **từng** denominator dùng chung. Current window cần freshness, expected/received sources và batches, không có drops/conflicts/lost terminals hoặc gauge discontinuity. Empty, sparse, partial và stale giữ explicit states, không xuất số giả. Real serving bị từ chối kể cả khi hai keys khớp và flag bật.

| Metric | Đại lượng và giới hạn |
| --- | --- |
| Missingness và unknown | Rate trên applicable. Delta là current − reference ở dạng phần. Không cộng not-applicable. |
| Categorical JS | Divergence base 2 [0,1], compare fixed ordered type buckets có unknown. Data chưa đủ không xuất estimate. |
| Histogram PSI và JS | Cùng bin edges. PSI add-0,5 rồi normalize từng population, xử lý zero bins. JS dùng base 2 và zero convention. Đây là bin-level comparisons, nhạy cách chia bin và không tái tạo raw ECDF. |
| Bounded W1 | Đơn vị VND. Mass của từng bin đặt ở midpoint, cộng absolute cumulative gap × khoảng cách hai midpoint. Sai số tuyệt đối tối đa bằng tổng weighted half-width của hai histograms nếu mọi quan sát ở fixed support. Support fixture 0–50 tỷ VND, 10 bins. Giá ngoài support cần chính sách riêng trước khi dùng reference thật. Không ngoại suy tail ở đây. |
| KS tại biên bin | Maximum CDF gap chỉ tại các registered boundaries, lower bound cho exact raw KS trên cùng support. Có thể bỏ lỡ shift trong một bin. Không dùng như p-value. |

Dữ liệu test cho mass ở hai bin liền nhau cho W1 = 1 tỷ và error bound = 1 tỷ VND, KS bin edges = 1 và JS = 1. Equal aggregates cho effect estimates bằng 0. Các ca khác khóa incompatible release/schema/calibration/mode/population/version, missing batch dù sample cao, terminal loss, invalid counts, empty/sparse reference và stale current. Các estimates này áp dụng cho prototype synthetic, không đánh giá production model accuracy.

`WP06_REAL_SERVING_REFERENCE_UNAVAILABLE`, `WP06_DELAYED_ACCURACY_DATA_UNAVAILABLE`, `WP05_REAL_CALIBRATION_DATA_UNAVAILABLE`. Không dùng holdout 3.102, dev cohort 4.403 hoặc protected TiniX. W20 historical inclusive source và research eligibility vẫn được ghi riêng trong [metric contract](SMARTPROP_WP06_MODEL_MONITORING_METRIC_CONTRACT.md). [B2 scope và evidence](SMARTPROP_WP06_FASTAPI_MONITORING_IMPLEMENTATION_REPORT.md).
