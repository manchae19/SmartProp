# PR #41 — Ma trận kiểm thử cuối

## Fresh validation

| Suite | Kết quả | Command/evidence |
|---|---:|---|
| Backend unit + integration/local + concurrency + coordinate + V28 verifier | **FRESH_PASS 614/614**, 0 lỗi/bỏ qua | Runner `.scratch/tools/pr41-run-tests.ps1`, profile test-only PR41; `.scratch/evidence/integrated-backend-final-test-scope-guard.log` |
| Advisor Local V21/V26/V27 read-only, Local/Staging full-mode pending refusal, V27 Hibernate checks, V28 capability, identity guards | **FRESH_PASS 13/13** | `mvnw ... test -Dtest=AdvisorReadOnlyRuntimeIT`; `.scratch/evidence/advisor-final-runtime-pass.log`; Spring Boot/Hibernate và HTTP thật |
| Standard V23, dev, prod, dev+prod | **FRESH_PASS 8/8** | `mvnw ... test -Dtest=NewsStandardV23IT,NewsStandardDevIT,NewsStandardProdIT,NewsStandardCombinedIT`; `.scratch/evidence/standard-v23-final-post-fixture-guard.log` |
| V28 constraint verifier: exact, normalized, missing, ambiguous, wrong table/type, unenforced, weakened/malformed | **FRESH_PASS 19/19** | MySQL 8 isolated; `.scratch/evidence/v28-verifier-mysql-final2.log` |
| Google Account Linking | **FRESH_PASS 1/1** | `.scratch/evidence/pr48-google-link-runtime-standard-v23.log`; isolated Standard V23, real Spring/Chrome/OIDC |
| Package production | **FRESH_PASS** | `mvnw clean -Dmaven.test.skip=true package`; `.scratch/evidence/backend-clean-package-final-fixture-guard.log`; JAR không có test profile/class/fixture |

## Fresh evidence đã có trước lượt cuối

| Suite | Kết quả | Evidence |
|---|---:|---|
| WP02 comparable runtime trên fixture được cấp | **FRESH_PASS 3/3** | `.scratch/evidence/` WP02 fixture logs |
| Coordinate portability + guard trên hai fixture độc lập | **FRESH_PASS 47 test**, gồm 39 provenance + 8 safety | `.scratch/evidence/targeted/portable-coordinate-final.log` và 3311 evidence |
| V26→V27→V28 và V27→V28 migration path | **FRESH_PASS** | `.scratch/evidence/v28/` migration evidence; Flyway validate và checksum khớp |
| Browser News integration + outage | **FRESH_PASS 12 scenario + outage**, synthetic dataset, real Spring/MySQL | `.scratch/evidence/chrome-real-integration.json`, `chrome-error-state.json` |

## Evidence tái sử dụng và chưa hoàn tất

| Hạng mục | Trạng thái | Phạm vi |
|---|---|---|
| Frontend PR41 | **REUSED_EVIDENCE 93/93** | Không có frontend/API contract change |
| Frontend PR37 | **REUSED_EVIDENCE 65/65** | Không sửa branch PR37, không đổi contract |
| Chrome screenshots/E2E và frontend production builds trên integrated baseline | **REUSED_EVIDENCE** | Không ghi FRESH_PASS cho lượt này |
| RAG Python regression | **FRESH_PASS 976 passed**, 0 failures/errors, 73 subtests; `.scratch/evidence/rag-final-post-deps-clean.log`. Python V1.3 model tests are **NOT_RUN** because the required model artifact is absent.
| Freshness theo latest `origin/main` | **BLOCKED** | Remote main mới `b49a98f` chưa được phê duyệt để tích hợp; branch vẫn chứa main đã duyệt `0e9053f` |
| Native DB dùng chung 3306/3307, live RSS, duyệt nguồn thật | **NOT_RUN** | Bị cấm trong phạm vi PR #41 |

## Database isolation

Runtime PR41 chỉ dùng `127.0.0.1:3311/pr41_local`, identity được kiểm tra từ manifest do provisioner độc lập tạo: port, schema, UUID, datadir, PID/owner, config hash và JDBC URL. `SMARTPROP_TEST_FIXTURE_AUTHORIZATION` chỉ truyền bằng environment process; không lưu trong Git hoặc log. Driver evidence không ghi destination protected. Không load `.env` dùng chung. Fixture khác cho Google và portability có datadir/UUID/schema riêng.

## Migration integrity

- Không thay migration SQL hoặc Flyway history V13–V28; không tạo V29.
- V27 checksum `-1622560226`; V28 checksum `-1006687404`.
- Không repair, auto-baseline hay migrate shared database.
- Negative constraint tests thay đổi DDL trên fixture synthetic riêng và phục hồi trong `finally`.
- Không sửa legacy rights, không tạo rightsReference giả, không tự duyệt source.

## Lệnh chính

```powershell
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=AdvisorReadOnlyRuntimeIT'
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=NewsStandardV23IT,NewsStandardDevIT,NewsStandardProdIT,NewsStandardCombinedIT'
./backend/mvnw.cmd -f backend/pom.xml clean '-Dmaven.test.skip=true' package
```

Các lệnh runtime chỉ chạy sau pre-connection guard và xác nhận manifest. Không chạy chúng với JDBC URL/profile mặc định hoặc `.env` chung.
