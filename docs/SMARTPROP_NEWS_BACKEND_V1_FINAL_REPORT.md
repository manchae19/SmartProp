# PR #41 — Nghiệm thu frozen baseline

Trạng thái validation: **FRESH_VALIDATION_COMPLETE**. Baseline được duyệt: `b49a98fc333cbda1ff38d5511259a5329881812e`. Main vẫn ở SHA này sau fetch cuối. Giữ `LIVE_INGESTION_DISABLED` và `SOURCE_RIGHTS_APPROVAL_PENDING`.

## Candidate và phạm vi

- Normal merge: `b6d1f4fcc96aabbcb2c8e2f1ef24a87cfa1b6f83`, parents `9b9498be4a3b18cad5f5a7193ed04133ac7d6b98` và `b49a98fc333cbda1ff38d5511259a5329881812e`; ancestry PASS.
- Cây chạy backend regression: `72d34aebc86799d04ee98826c064ebad31e7f821`. Source HEAD sau sửa runner: `abf0e3a19018e35e93c113e9e1f625ed0148507d`, tree `8125ae0d3e048ff6da3457c5e3b35538da8b2a00`.
- Source ứng dụng backend/frontend/AI và toàn bộ SQL không đổi giữa hai cây. Sáu file sửa chỉ thuộc test/fixture: bỏ auto-baseline, tách marker khỏi schema trước migration, thu hồi quyền marker sau migration, cấu hình output evidence và ghi đúng yêu cầu Python3.12.
- Runners được kiểm thử trên working tree rồi commit nguyên nội dung. Trên source HEAD đã commit, real-model HTTP smoke tiếp tục đạt157/157. Không chạy lại suites không bị ảnh hưởng.
- Commit/tree giao cuối (documentation-only) và remote HEAD được ghi sau push tại PR41 description và `.scratch/evidence/pr41-final-validation-manifest.md`; không tự ghi SHA của chính commit vào nội dung commit.

## Kết quả fresh

| Gate | Kết quả thực tế |
|---|---|
| Backend integrated |640/640; Standard/profile matrix8/8; negative checksum được từ chối đúng. Lần đầu639/640 do thiếu cấu hình runner; rerun đã hoàn tất, không hạ assertion.|
| Advisor/Hibernate/News capability |13 Advisor cases trong640; V21/V26 read-only200/News503, V27 full News validation/503, pending full-mode refusal, valid/invalidV28 và protected destination guards.|
| Coordinate portability |39+8=47/47 trên fixture thứ hai độc lập; regression3311 đã có trong640.|
| Python/RAG/model |1.136 unique testcase PASS,0FAIL/ERROR,1 optional planning dataset SKIP sau đối chiếu XML theo classname/name. Model rerun101/101,9 subtests; không còn model/WP04 skip hoặc bốn lỗi ban đầu.|
| V1.3 artifact |ZIP/source8/8, destination trước8/8 và sau8/8; khớp approved acceptance.json; ZIP không đổi.|
| Giá authoritative |44/44 case: baseline và candidate chênh chính xác0VND; tất cảv1.3/AVAILABLE. Không đổi rounding/calibration/tolerance.|
| WP04 runtime |HTTP157/157; real standalone/posting/Advisor298/298; failure isolation11/11 gồm outage tiến trình thật và recoveryPID mới.|
| WP04 components |484/484 geometry checks tại320/390/768/1440;30/30 Advisor component checks. Đây là mocked components, tách khỏi real runtime.|
| Frontend/build |Candidate348/348; detached PR37@151a07b65/65; cả hai production builds exit0, fresh trong lượt nghiệm thu này.|
| News browser/API |12 scenario mỗi frontend; controlled503/retry6 viewport cases; backend outage thật. Candidate có session-bootstrap fail-closed/retry502; PR37 có News error/retry. Không interception API News.|
| Auth/session/security |Google browser IT1/1: real Chrome/Spring/MySQL với signed OIDC synthetic; reactive/shared session3/3; mocked session scope5/5. Phân loại từng ca trong manifest.|
| WP02 |3 Comparable MySQL+1 Advisor outage=4/4; không lấy Advisor với valuation disabled làm bằng chứng WP04.|
| Migration/database |Hai upgrade paths fresh PASS; V27=-1622560226,V28=-1006687404;14 full history/all-table checksum snapshot pairs không đổi; read-only INSERT bị từ chối thật.|
| Security/package |Heuristic source scan1.388 files,0 findings,exit0; npm audit0 vulnerabilities. Clean production package PASS; JAR không có test fixture/bootstrap/private identity.|

Không cộng lặp smoke, repeated runs hoặc subtests vào tổng unique. Historical Advisor26 là aggregate13+7+1+1+4; verifier19 là aggregate4 verifier+7 broken-schema+8 safety. Actual verifier có4 test methods, nằm trong640.

## Integrity và isolation

V13–V28 blobs khớp reviewed HEAD `da1d8c34c4303c84996f2f78212793c1f57a4228`. Standard target23; Local/Staging28; khôngV29, repair, history rewrite hoặc auto-baseline. Hai migration paths dùng schema synthetic mới, kiểm tra dữ liệu trướcV28 có0 APPROVED reference vi phạm; không sửa legacy row hoặc tự duyệt nguồn.

Fixture3311/3312 được đối chiếu manifest độc lập, authorization, executable/PID/start/owner, config hash, datadir/fileUUID và JDBC URL. Google dùng dedicated high-port fixture; WP04 dùng launcher/datadir riêng và restricted account. Physical JDBC queue của Advisor chỉ có các schema được cấp trên3311; WP04 live connection observation chỉ tới54041. Không kết nối3306/3307, shared DB hoặc load shared.env. Private identity/proof ở raw evidence, không đưa credentials vào Git.

## Evidence và giới hạn

Machine-readable summary: [acceptance.json](pr41-evidence/acceptance.json). Commands, profile/classification, dependencies, artifact identity, timing và raw paths ở summary/local manifest; raw logs giữ tại `.scratch/evidence/baseline-b49/`. Full Python metadata ở `python312-dependencies.json`; raw files có inventory SHA256.

Một optional offline planning dataset không được phân phối cùng source vẫn SKIP; synthetic planning tests đã PASS. Historical evidence cũ không được dùng thay mandatory fresh acceptance. Các mocked401/research/explanation mutations được ghi đúng phân loại; real price/model/runtime gates có evidence riêng. Scanner là heuristic và npm audit, không tuyên bố full-history/certified SCA.

DNS rebinding và304 logging race giữ giới hạn/backlog V1. Không train model, không commit artifact, không approve/merge/deploy, không thay branch main/PR43/WP06/PR37 hoặc mentor demo.
