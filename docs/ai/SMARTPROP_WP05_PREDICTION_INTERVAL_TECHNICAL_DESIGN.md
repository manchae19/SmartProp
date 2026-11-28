# WP-05 — Thiết kế kỹ thuật dự kiến cho Phase B

Thiết kế này dành cho review. Phase A chỉ có benchmark synthetic. Mọi bounds public chờ dữ liệu đủ quyền sử dụng và nghiệm thu thống kê. Giữ V1.3 làm nguồn duy nhất của `predicted_asking_price_vnd`.

## Spring, FastAPI và React

| Luồng hiện tại | Điểm mở rộng dự kiến |
| --- | --- |
| Standalone `ValuationPanel.jsx` → client `valuation.js` → `/api/ai/predict` → FastAPI `/predict` | FastAPI xác thực request như hiện tại, chạy V1.3 một lần. Sau khi point hợp lệ, interval module nhận p, identity của pipeline và metadata feature hiệu dụng. Client validate interval riêng khỏi price. |
| Posting `PostValuationPanel.jsx` → `/api/v1/properties/valuation-preview` → `ValuationService.previewV13` / `ValuationClient` → FastAPI `/predict` | Thêm field optional cuối `ValuationService.Preview` và giữ constructor/interface cũ khi cần. Validate object riêng, giữ nguyên chuỗi giá VND của projection cũ và các lỗi/authorization hiện hành. |
| Unified Advisor → `/api/v1/advisor/consult` → `AdvisorValuationAdapter` → FastAPI `/predict` | Thêm optional interval trong `ValuationEvidence`, tách khỏi explanation và Comparable. Giữ nguyên các nhánh skip/available của point estimate, SAFE/research auth và hai Comparable evidence fields độc lập. |

Alias `/predict/v1_3_preview` có thể dùng cùng projection khi contract được duyệt. Default-off config, không có surface, route public, auth scope, proxy, lookup listing hay database mới. FastAPI chịu trách nhiệm duy nhất tính bounds. Spring kiểm tương thích transport/object; React chỉ format và display theo trạng thái. Không recompute từ SHAP, Cohort WP-02, MAPE, feature coverage hay giá lịch sử.

## Artifact riêng, chưa có file production

Đề xuất `interval_artifact_version` theo semantic version, `interval_id` bất biến cho mỗi calibration run và checksum/signature cấp phát qua release manifest. Runtime kiểm file trước khi publish immutable snapshot vào memory.

| Nhóm | Các trường nội bộ và validation |
| --- | --- |
| Pipeline identity | Model version và run ID, SHA-256 model/schema/Duan point policy, version source của adapter/transformer, fingerprint input mode và application contract, target và đơn vị. Mismatch fail closed. Ba hash không thay thế input mode hoặc feature-policy version. |
| Interval | Method ID, score formula version, exact nominal levels, alpha per tail nếu có, normalization và bounds policy, group rule version, fallback policy và eligibility. Reject coverage lạ, unsupported method, group/range chồng, cutoff nonfinite, reorder bounds hoặc mismatch coverage scopes. |
| Calibration | Cohort ID nội bộ, owner approval reference, effective entity count, feature/label date ranges, source/population restrictions, counts theo nhóm, quantiles và transform parameters. Không có raw rows, residual arrays, property IDs hay credentials. |
| Evidence | Aggregate evaluation reference/digest, subgroup uncertainty, criteria release đã predeclare, known limitations, expiration/review date. Runtime chỉ expose version opaque và metadata đã được duyệt. |

Preselect một nominal level sau nghiệm thu real, hoặc dùng một eligibility/group partition đáp ứng mức coverage cao nhất và test nesting nếu phục vụ nhiều mức. Benchmark có thể đổi group support theo alpha nên nesting giữa các phương pháp/nhóm phân tách không tự được bảo đảm. Mọi fallback phải có evidence đúng deployment population và một release gate về coverage của policy hỗn hợp. Khi support thấp, ưu tiên không phát bounds. Chỉ dùng GLOBAL_FALLBACK khi đã đánh giá và công bố scope; không gán mức coverage nhóm cho kết quả global.

## Additive contract dự kiến

FastAPI trả `prediction_interval` optional. Khi feature flag off hoặc server cũ thì field có thể vắng mặt. Spring có thể chiếu `predictionInterval` với field camelCase tương ứng, dùng DTO kiểm schema version. Các price fields hiện có giữ nguyên. Khi point prediction vốn lỗi, route giữ nguyên hành vi cũ; các trạng thái bên dưới chỉ áp dụng khi point được trả thành công.

| Field | Type và quy tắc |
| --- | --- |
| `interval_version`, `status` | String bắt buộc nếu có object. Consumer bỏ qua version không hỗ trợ và giữ point. |
| `target`, `point_prediction_vnd` | `ASKING_PRICE_VND` và integer VND bằng đúng point V1.3. Equality cần kiểm tại từng projection. |
| `lower_vnd`, `upper_vnd` | Integer dương trong safe range của JSON/JS, có giá trị chỉ khi `AVAILABLE`; invariant `1 ≤ lower ≤ point ≤ upper ≤ 2^53−1`. Outward round tại server. Reject corruption/overflow, không clip upper để giả vờ hợp lệ. |
| `nominal_coverage` | Decimal fraction trong danh sách đã nghiệm thu. Null với non-AVAILABLE để consumer không hiển thị phần trăm khi thiếu bounds. |
| `method`, `calibration_scope` | Method ID và một trong GLOBAL/GROUP/GLOBAL_FALLBACK khi AVAILABLE, null cho non-AVAILABLE. Scope public không bao gồm sensitive group selector. |
| `calibration_sample_count` | Số entity thực sự tạo cutoff được dùng; có thể null nếu publication policy yêu cầu ẩn. Với fallback chỉ mô tả cohort global. |
| `calibration_artifact_version` | Phiên bản opaque của artifact khi AVAILABLE; null ở non-AVAILABLE. Không expose path, date, license/source, hash riêng tư hoặc ID cohort. |
| `limitations` | Mảng code/chuỗi public đã allowlist. Tránh nhúng raw exceptions hoặc giá trị feature do user nhập. |

| Status | Hành vi |
| --- | --- |
| `AVAILABLE` | Artifact hợp lệ và tương thích, mode/nhóm đã qua eligibility và support, và hai bounds hữu hạn đạt invariant. |
| `INSUFFICIENT_CALIBRATION` | Input thuộc scope dự kiến nhưng không có support hợp lệ và fallback đã được duyệt chưa có. Không có bounds. |
| `UNAVAILABLE` | Artifact thiếu, sai hash/version, quá hạn, bị disable runtime, lỗi nội bộ hoặc numeric failure. Giữ point và không cung cấp bounds thay thế. |
| `NOT_SUPPORTED` | Mode, phân khúc, quần thể, target hoặc nominal level ngoài artifact; request định giá hợp lệ vẫn có point. |

### Failure isolation và rollback

Nạp interval artifact độc lập với startup của predictor. Validate/checksum đầy đủ, sau đó đổi con trỏ bất biến một lần, hoặc giữ state UNAVAILABLE khi artifact mới hỏng. Không phục vụ artifact cũ nếu identity/version khác hoặc đã bị thu hồi. Một lỗi tính interval hoặc parse DTO không làm fail request point. Không retry prediction để tính interval. Tắt flag để bỏ optional envelope trên mọi surface, quay lại artifact version đã phê duyệt **và tương thích** khi được phép, hoặc giữ unavailable. Không cần migration hay sửa model directory. Cache nếu có phải gắn pipeline/interval artifact version và semantics auth hiện hành.

## Giao diện tiếng Việt

Reuse panel nhỏ ở ba luồng. Giữ dòng giá “Giá rao ước tính V1.3”, tiếp theo “Khoảng dự đoán giá rao” và hai bound hiển thị VND làm tròn ra ngoài theo tick hợp lý, kể cả khi số nằm sát ngưỡng. Ví dụ caption đã validate “Mức bao phủ mục tiêu 90% trên các trường hợp tương tự thuộc phạm vi hiệu chỉnh.” Tách note về dữ liệu đầu vào/coverage scope, và “Giá rao ước tính có thể khác giá giao dịch.” Với unsupported, insufficient hoặc lỗi hiển thị “Chưa đủ dữ liệu để hiển thị khoảng dự đoán” theo reason public. Trạng thái tương tác accessible, tương thích mobile và không giữ kết quả cũ khi criteria/session đổi.

WP-02 giữ bằng chứng tin rao so sánh. WP-04 giải thích hành vi model. WP-05 thể hiện sai số dự đoán. WP-06 giám sát, WP-07 tổ hợp Advisor theo evidence types và WP-08 chỉ diễn giải những evidence đã được cấp quyền. Không dùng “độ tin cậy 90% cho tài sản này”, giá giao dịch cam kết, nhân quả, hoặc số lẻ không có ý nghĩa.

## WP-06 handoff

Đề xuất aggregate counters cho availability/status, histogram absolute/relative widths, fallback rate, missing/unknown state buckets, artifact mismatch, invalid bounds và distribution drift của predictions/feature states. Theo dõi theo model/interval version, flow, scope đã được duyệt và time window. Giới hạn cardinality, sampling và suppress subgroup nhỏ; không đưa raw addresses, IDs, user data hay rows vào metric. True delayed empirical coverage và tail miss cần cohort nhãn giá rao hợp pháp với entity dedupe, outcome delay, selection/ascertainment bias và confidence interval. Unlabeled telemetry giúp phát hiện shift, không đo coverage. Phase A không thêm telemetry hay DB write.
