# PR #41 — Ma trận nghiệm thu fresh

Approved baseline `b49a98fc333cbda1ff38d5511259a5329881812e`; source HEAD `abf0e3a19018e35e93c113e9e1f625ed0148507d`; tree `8125ae0d3e048ff6da3457c5e3b35538da8b2a00`. Nội dung ứng dụng khớp cây backend regression `72d34aebc86799d04ee98826c064ebad31e7f821`. Sáu file test/fixture thay đổi và các runtime liên quan đã được kiểm thử.

| Suite | PASS | SKIP | Phân loại / raw log |
|---|---:|---:|---|
|Backend integrated|640|0|UNIT_AND_REAL_SPRING_HIBERNATE_MYSQL; `.scratch/evidence/baseline-b49/backend-rerun.log`|
|Standard V23/profile matrix|8|0|REAL_SPRING_HIBERNATE_MYSQL; `.scratch/evidence/baseline-b49/standard.log`|
|Portable Coordinate and isolation|47|0|REAL_SPRING_HIBERNATE_MYSQL; `.scratch/evidence/baseline-b49/portable.log`|
|Google Linking browser runtime|1|0|REAL_CHROME_SPRING_MYSQL_SYNTHETIC_SIGNED_OIDC; `.scratch/evidence/baseline-b49/google-runtime.log`|
|WP02 Comparable and Advisor outage|4|0|REAL_MYSQL_AND_REAL_OFFLINE_AI_DESTINATION; `.scratch/evidence/baseline-b49/wp02-runtime.log`|
|V1.3/WP04/security/shadow|101|0|REAL_PINNED_MODEL_FASTAPI_IN_PROCESS_AND_OWNED_HTTP; `.scratch/evidence/baseline-b49/python312-model.log`|
|Candidate frontend|348|0|FRONTEND_UNIT_CONTRACT; `.scratch/evidence/baseline-b49/frontend.log`|
|PR37 frontend|65|0|FRONTEND_UNIT_CONTRACT; `.scratch/evidence/baseline-b49/pr37-frontend.log`|
|News candidate browser|12|0|REAL_CHROME_SPRING_MYSQL_SYNTHETIC_NEWS; `.scratch/evidence/baseline-b49/candidate-news-browser.log`|
|News PR37 browser|12|0|REAL_CHROME_SPRING_MYSQL_SYNTHETIC_NEWS; `.scratch/evidence/baseline-b49/news-browser-final.log`|
|Controlled News503 and retry|6|0|REAL_CHROME_STANDARD_V23_HTTP503; `.scratch/evidence/baseline-b49/news-controlled503-final.log`|
|WP04 HTTP|157|0|REAL_FASTAPI_AND_VITE_PROXY_HTTP; `.scratch/evidence/baseline-b49/wp04-runtime-final.log`|
|WP04 three valuation surfaces|298|0|REAL_CHROME_REACT_SPRING_FASTAPI_MYSQL; `.scratch/evidence/baseline-b49/wp04-runtime-surfaces-final.log`|
|WP04 failure isolation|11|0|MIXED_REAL_HTTP_HELD_RESPONSE_MOCKED_MUTATIONS_REAL_PROCESS_OUTAGE; `.scratch/evidence/baseline-b49/wp04-failure-isolation-final.log`|
|WP04 component geometry|484|0|MOCKED_COMPONENT_REAL_CHROME_VIEWPORT; `.scratch/evidence/baseline-b49/wp04-component.log`|
|WP04 Advisor components|30|0|MOCKED_COMPONENT_WITH_LINKED_ROUTE_FAILURE_EVIDENCE; `.scratch/evidence/baseline-b49/wp04-surfaces-final.log`|
|Reactive authorization and shared session|3|0|MIXED_REAL_MYSQL_SESSION_AND_SYNTHETIC_RESPONSE; `.scratch/evidence/baseline-b49/wp04-reactive-authorization-final.log`|
|Session scope browser|5|0|MOCKED_HTTP_REAL_CHROME; `.scratch/evidence/baseline-b49/session-browser.log`|
|Source HEAD real-model smoke|157|0|REAL_MODEL_HTTP_ON_COMMITTED_SOURCE_HEAD; `.scratch/evidence/baseline-b49/final-head-smoke/wp04-http.log`|

Python union theo exact testcase identity:1.136PASS,0FAIL/ERROR,1SKIP (optional offline planning dataset). Không cộng các suite lặp vào tổng. RAG/context/routing41modules chạy serial với network guard; model/WP04101cases rerun bằng Python3.12/XGBoost3.4.1 giải quyết toàn bộ model-related skips/failures.

Production build: `backend/mvnw.cmd -o -B -DskipTests clean package` exit0; Vite candidate và PR37 builds exit0. Security scan1.388files/0findings; npm audit0vulnerabilities. Fresh upgrade paths V26→V27→V28 và V27→V28 PASS. Artifact8/8 trước/sau; price invariance44/44,0VND drift.

Advisor actual13; historical26 là aggregate. Verifier actual4methods; historical19 là aggregate4+7+8.640 bao gồm các suite này. Component/mock checks không thay real runtime. Không có mandatory gate dùng historical REUSED_EVIDENCE.

Full commands/timings/classifications và price corpus results: [acceptance.json](pr41-evidence/acceptance.json). Raw evidence/timings và final delivery SHA/tree/remote confirmation: `.scratch/evidence/pr41-final-validation-manifest.md`.

`LIVE_INGESTION_DISABLED` · `SOURCE_RIGHTS_APPROVAL_PENDING`.
