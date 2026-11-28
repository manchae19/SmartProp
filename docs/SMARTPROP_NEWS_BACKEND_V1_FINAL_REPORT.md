# PR #41 — Báo cáo hoàn tất News Backend V1

## Trạng thái hiện tại

Candidate đã tích hợp main đúng SHA được nhóm trưởng phê duyệt `0e9053f0c4085351a7d429f81995f6895ad80e33`. Trong lần xác minh cuối, `origin/main` đã tiến lên `b49a98fc333cbda1ff38d5511259a5329881812e` qua PR #50. Main mới sửa trùng ba file đang có trong cây PR41: `AdvisorDtos.java`, `AdvisorValuationAdapter.java`, và `ValuationService.java`. SHA mới nằm ngoài phê duyệt hiện có; không tự merge thêm thay đổi đó. Vì vậy chưa tuyên bố `PR41_READY_FOR_FINAL_INDEPENDENT_REVIEW`; cần xác nhận main baseline mới trước khi đóng gate cuối.

Giữ nguyên `LIVE_INGESTION_DISABLED` và `SOURCE_RIGHTS_APPROVAL_PENDING`. Không có RSS thật được tải, nguồn báo thật được duyệt, hay quyền sử dụng được giả lập.

## Tích hợp và thay đổi

- Normal merge của main được duyệt `0e9053f`; ancestry đã xác minh trước khi main tiếp tục tiến lên.
- V28 verifier kiểm tra đúng schema hiện tại, `news_sources`, loại `CHECK`, trạng thái `ENFORCED`, và cấu trúc biểu thức chính xác. Metadata sai bảng, sai loại, không enforce, sai toán tử/cột/literal, thiếu hoặc mơ hồ đều fail closed. Parser chấp nhận một số cách chuẩn hóa metadata MySQL mà không bỏ qua nội dung literal.
- Capability được xác định từ lineage, checksum và schema trước Hibernate validation. Local V21/V26 chỉ lọc ba bảng News chưa có; V27 xác thực đủ ba bảng nhưng News API vẫn 503; V28 hợp lệ mới bật News. Standard V23, schema lạ và schema thiếu/sai giữ hành vi fail closed.
- Fixture profile dành cho PR41 được chuyển khỏi `src/main/resources` sang `src/test/resources`. Guard độc lập, manifest authorization, lineage/checksum và Hibernate validation vẫn giữ nguyên. Production JAR được clean-package và xác nhận không chứa profile, manifest, fixture hay test class.
- Bộ test Advisor làm mới phiên Admin tổng hợp stale theo timeout idle 30 phút; không thay đổi logic xác thực production.
- Admin feature/publication updates dùng UPDATE mục tiêu, kiểm tra affected rows và đọc lại; concurrency chạy trên transaction thật với latch/barrier, kiểm tra SQL và hai thứ tự commit.
- Bộ fixture dùng manifest provisioner độc lập; không hardcode identity tác giả trong shared `CoordinateProvenanceIT`.

## Validation có bằng chứng

| Hạng mục | Kết quả |
|---|---|
| Full backend regression sau thay đổi cuối | **FRESH_PASS** 614/614, 0 fail/error/skip; `.scratch/evidence/integrated-backend-final-test-scope-guard.log` |
| Advisor read-only + Local/Staging policy simulation | **FRESH_PASS** 13/13, Spring Boot/Hibernate runtime; `.scratch/evidence/advisor-final-runtime-pass.log` |
| Standard V23 và profile dev/prod/combined | **FRESH_PASS** 8/8; `.scratch/evidence/standard-v23-final-post-fixture-guard.log` |
| V28 constraint MySQL negatives/normalization | **FRESH_PASS** 19/19 trên fixture cô lập; `.scratch/evidence/v28-verifier-mysql-final2.log` |
| Google Account Linking runtime | **FRESH_PASS** 1/1 trên fixture Standard riêng, Chrome/OIDC; `.scratch/evidence/pr48-google-link-runtime-standard-v23.log` |
| Production backend JAR | **FRESH_PASS**, clean package và kiểm tra loại trừ test-only resource; `.scratch/evidence/backend-clean-package-final-fixture-guard.log` |
| Frontend PR41 | **REUSED_EVIDENCE** 93/93; không đổi frontend/API contract |
| Frontend PR37 | **REUSED_EVIDENCE** 65/65; không đổi frontend/API contract |
| Chrome E2E, outage, frontend production builds | **REUSED_EVIDENCE** từ integrated baseline đã kiểm chứng; không tính là fresh |
| RAG / Python AI regression | **FRESH_PASS** 976 passed, 0 failed/errors, 73 subtests passed; `.scratch/evidence/rag-final-post-deps-clean.log`. Python V1.3 model API/unit tests are **NOT_RUN** because the real `artifacts/v1_3/model.json` is absent; no model was fabricated.
| `origin/main` mới nhất | `b49a98f` chưa được tích hợp vì ngoài SHA phê duyệt `0e9053f` |

Các bằng chứng trước đó trên cùng code candidate gồm 3/3 WP02 comparable runtime, 47 test regression portable/coordinate, Chrome real News integration 12 scenario + outage, và V26→V27→V28 cùng V27→V28 trên MySQL isolated. Raw evidence không được commit.

## Migration và database

Không sửa SQL hoặc history V13–V28; không tạo V29, không Flyway repair/baseline, không migration DB dùng chung. Checksum V27 `-1622560226`; V28 `-1006687404`. Dữ liệu được kiểm tra trước V28, không tạo `rightsReference` giả và không tự duyệt nguồn. Kiểm thử chỉ dùng MySQL riêng 127.0.0.1:3311; port 3306/3307 không được kết nối. Server UUID, datadir, schema, JDBC URL, process owner và config hash được đối chiếu với fixture manifest độc lập.

| Gate cuối | Trạng thái |
|---|---|
| Approved main SHA `0e9053f` tích hợp | PASS |
| V27/V28 schema capability và fail-closed | PASS theo fresh runtime/integration evidence |
| Database isolation, no protected-port connection | PASS theo fixture manifest và driver evidence |
| Migration integrity/checksum | PASS |
| Backend regression, Advisor, Standard V23, production package | PASS |
| RAG fresh regression | PASS: 976 passed, 0 failures/errors; Python V1.3 endpoint tests remain NOT_RUN because the model artifact is absent.
| Latest `origin/main` integrated | Chờ phê duyệt SHA mới; không tự tích hợp |
| Push/final remote head | Chưa chốt trong báo cáo này |

RAG fresh regression đã PASS. Trạng thái vẫn VALIDATION_PARTIAL cho đến khi nhóm trưởng quyết định về `origin/main` `b49a98f`, vì SHA đó có overlap chưa được duyệt để tích hợp. Chưa tuyên bố READY_FOR_FINAL_INDEPENDENT_REVIEW. Không approve hoặc merge PR #41.

Xem [test matrix](SMARTPROP_NEWS_BACKEND_V1_TEST_MATRIX.md), [implementation](SMARTPROP_NEWS_BACKEND_V1_IMPLEMENTATION.md), và [PR #37 handoff](handoff/SMARTPROP_PR37_NEWS_BACKEND_HANDOFF.md). Evidence manifest cuối được ghi dưới `.scratch/evidence/`; không commit log thô, credential, manifest riêng tư hoặc dữ liệu fixture.
