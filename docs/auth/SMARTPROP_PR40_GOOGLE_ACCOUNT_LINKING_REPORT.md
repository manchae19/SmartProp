# SmartProp PR #40 — Liên kết tài khoản Google

Ngày bàn giao 28/11/2026. Trạng thái **PR40_READY_FOR_INDEPENDENT_REVIEW**. Bản tích hợp để review, còn thiếu xác minh OAuth với Google thật và kiểm tra trước triển khai.

## 1. Checkpoint bàn giao

| Mốc | SHA hoặc nhánh |
| --- | --- |
| PR #40 gốc, đang mở và ở trạng thái Draft | `24fc5711171ff20b94dcb9945d38d2543b8bccf7` |
| Base ban đầu của PR | `d202792b4eb729fee36adc7012bf72beeabfb98a` |
| Main theo yêu cầu ban đầu | `f972d3a3465e5cc0ebe4260ddfbee7a8d32eee42` |
| Main xác minh lại sau PR #47 | `1c67a279a8ff6f6939767e82bb31b17584610864` |
| Merge chính | `c659433c71617cc9cc0042457f55928acf56cde3` |
| HEAD kiểm thử backend | `fe640eefe541bf05473d7262cb75b4f28956424b` |
| Nhánh bàn giao | `Nguyenhuy2706/SmartProp:integration/pr40-google-link-20261128` |

Hai lần merge dùng merge commit. Git không để lại file xung đột. Đã rà thủ công README, SecurityConfig và router. Git xác nhận main sau PR #47 là ancestor của bản kiểm thử. FE, RAG và các file production ở HEAD kiểm thử backend giống bản merge chính. Commit bàn giao chỉ thêm README và báo cáo. Dùng `git rev-parse HEAD` và `git ls-remote origin refs/heads/integration/pr40-google-link-20261128` trên fork để đối chiếu SHA của commit báo cáo. PR gốc nằm ở repository nhóm. [PR #40](https://github.com/manchae19/SmartProp/pull/40)

## 2. Thay đổi và phát hiện

| Mức độ | Phát hiện | Sửa và bằng chứng |
| --- | --- | --- |
| Cao | CSRF matcher khai báo trong PR bị mặc định miễn CSRF của Resource Server ghi đè đối với request có Bearer token. | Hai endpoint ghi liên kết yêu cầu cả JWT và CSRF. MockMvc kiểm tra request thiếu CSRF bị 403, Origin ngoài allowlist bị 403 và request không xác thực bị 401. Các đường dẫn khác giữ hành vi CSRF của main. |
| Cao | Binding callback được tái sử dụng qua trạng thái chung thay vì gắn với request đã tiêu thụ yêu cầu OAuth. | Consume đồng bộ và cấp vé từ binding trên chính request đã xác thực. Unit test kiểm tra trạng thái, TTL, sử dụng lại và hai lần tiêu thụ đồng thời. |
| Vừa | Trang hoàn tất tự khởi tạo lại phiên, có thể mất kết quả sau khi route bị tháo. Một số lỗi luồng có thể bị xử lý như hết phiên. | Dùng trạng thái phiên đã khôi phục và chỉ báo thành công sau khi API xác nhận đúng người dùng. Mật khẩu sai trả 400, vé không còn hiệu lực trả 410, khác phiên hoặc trùng danh tính trả 409. Phiên bị thu hồi vẫn trả 401. |
| Vừa | Giới hạn thử mật khẩu ban đầu theo phiên, có thể mất tác dụng khi người dùng bắt đầu một phiên khác. | Thêm cửa sổ 5/300 giây theo tài khoản cho start. Giữ giới hạn theo phiên và IP. Kết quả HTTP kiểm tra 429 và Retry-After. |
| Vừa | Matcher callback rộng hơn URI đã cấu hình và quy tắc claim authorized party cần rõ hơn. | Cố định đường dẫn callback, giữ endpoint Google tin cậy và đối chiếu claim `azp` với client ID. Signed OIDC fixture kiểm tra chữ ký, issuer, audience, nonce, hết hạn, state và verifier. |

### Luồng và contract

1. Tài khoản SmartProp đã đăng nhập mở **Tài khoản → Bảo mật**. `GET /api/v1/auth/google/link/status` trả `available` và `linked`. Các thao tác ghi yêu cầu Bootstrap CSRF qua `GET /api/v1/auth/csrf`.
2. `POST /api/v1/auth/google/link/start` nhận `currentPassword`. Dịch vụ kiểm tra tài khoản ACTIVE, phiên và token version. Khi mật khẩu đúng, Backend đặt cookie flow tạm, trả đường dẫn authorize riêng. Mật khẩu sai giữ nguyên phiên và biểu mẫu báo lỗi.
3. `GET /api/v1/auth/oauth2/link/authorize/google` cần cookie yêu cầu hợp lệ. Spring Security gửi Authorization Code với state, PKCE S256 và nonce. Google phản hồi về đúng `/api/v1/auth/oauth2/callback/google`. Binding phân biệt sign-in với link, và xác thực token dựa trên chữ ký, issuer, audience, thời hạn, nonce, subject, email đã xác minh và authorized party khi áp dụng. [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect) · [RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700)
4. Callback chuyển trình duyệt về `/auth/google/link/complete` và cấp vé một lần bằng cookie HttpOnly. `POST /api/v1/auth/google/link/complete` yêu cầu phiên đang hoạt động khớp cả tài khoản lẫn ID phiên. Hai khóa duy nhất V15 là `(provider,subject_id)` và `(user_id,provider)`. Liên kết thành công chỉ ghi một hàng danh tính.
5. Tài khoản giữ email SmartProp cho cả trường hợp email Google trùng với tài khoản khác hoặc khác email của chính mình. Google Sign-In tiếp tục tra theo subject đã liên kết. Nếu subject thuộc về người khác, hệ thống báo xung đột và giữ nguyên hai tài khoản.

Luồng bắt đầu hết hạn sau tối đa 300 giây. Vé hết hạn sau 60 giây. Pending và ticket ở bộ nhớ, được dọn khi xử lý và có giới hạn kích thước. Mỗi phiên có 5 lần start và 5 lần complete trong 300 giây, kèm giới hạn start theo tài khoản. Authorize giới hạn 10/60 giây theo IP. Sai mật khẩu, hết hạn và xung đột chỉ báo lỗi trong luồng liên kết. Giao diện tải lại trạng thái bảo mật từ Backend.

### File liên quan

- Spring Boot trong `backend/src/main/java/vn/smartprop` gồm `modules/auth/google/{GoogleFlowStore,GoogleLinkController,GoogleLinkFlowStore,GoogleLinkService,GoogleOAuthConfigurer,GoogleProfile}.java` và `security/SecurityConfig.java`.
- React gồm `frontend/src/app/router.js`, `frontend/src/features/account/AccountView.jsx`, `frontend/src/features/auth/GoogleLinkCompleteView.jsx` và `frontend/src/features/auth/api.js`.
- Kiểm thử liên kết nằm trong `backend/src/test/java/vn/smartprop/modules/auth/google/`, `backend/src/test/java/vn/smartprop/security/{GoogleLinkHttpSecurityTest,SecurityConfigCsrfMatcherTest}.java`, `frontend/tests/googleLinkSession.test.mjs` và `frontend/tests/browser/pr40-google-link.cjs`.

## 3. Kiểm thử thực tế

| Hạng mục | PASS | FAIL | Skip | Exit | Môi trường |
| --- | ---: | ---: | ---: | ---: | --- |
| Maven test | 311 | 0 | 0 | 0 | HEAD `fe640ee`. Gồm HTTP MockMvc, Tomcat loopback, Research, Coordinate Provenance, Auth/Refresh và lịch sử định giá. |
| MySQL liên kết, đã tính trong 311 | 4 | 0 | 0 | 0 | MySQL 8.0.43 riêng, loopback cổng 51951, datadir riêng và schema `smartprop_pr40_test` có marker. Thực thi đúng SQL V15 trên schema fixture. |
| OIDC ký RSA và HTTP liên kết, đã tính trong 311 | 14 | 0 | 0 | 0 | 8 ca với ID token ký bằng khóa tạm qua Spring Security, 6 ca HTTP MockMvc. |
| Frontend Node | 157 | 0 | 0 | 0 | HEAD `c659433`. FE và RAG tại `fe640ee` giống hệt. |
| Vite production build | Hoàn tất | 0 | 0 | 0 | HEAD `c659433`. |
| Chromium desktop/mobile | 8 | 0 | 0 | 0 | Edge headless, giao diện React thật và API fixture. Rộng 1440 và 390 px. Thành công, hủy, hết hạn, trùng danh tính. Mỗi ca xác nhận nhập sai mật khẩu vẫn ở phiên hiện tại. |
| RAG fixture | 26 | 0 | 0 | 0 | 9 checkpoint, 17 hội thoại nhiều lượt. Không gọi model/dataset thật. |
| FastAPI toàn bộ, WP02 live IT, OAuth Google thật, production | NOT_RUN | — | — | — | Không nằm trong các bằng chứng runtime trên. |

MySQL fixture xác nhận số lượng và giá trị các dòng tài khoản, email, hash mật khẩu, tên, vai trò, trạng thái, chủ tin, yêu thích và lịch sử định giá giữ nguyên. Rollback sau insert giả lập, FK và race hai tài khoản cùng subject đều đạt. Repo người dùng/phiên trong bài test SQL dùng mock, còn insert, FK, unique và transaction chạy trên MySQL thật. Browser dùng API giả lập. OAuth fixture ký token nội bộ và kiểm tra các trạng thái qua Spring. Chưa chạy trọn vòng browser → Spring → MySQL → Google trên cùng môi trường.

### Trạng thái nghiệm thu

| Trạng thái | Bằng chứng hoặc giới hạn |
| --- | --- |
| PR40_MAIN_BASELINE_INTEGRATED | `1c67a27` là ancestor. |
| PR40_GOOGLE_OAUTH_FLOW_SECURITY_PASS · PR40_OIDC_IDENTITY_VERIFICATION_PASS · PR40_STATE_PKCE_VALIDATION_PASS | Signed OIDC fixture, Spring authorization resolver, flow store và HTTP callback path. Token exchange dùng fixture, không gọi Google. |
| PR40_PASSWORD_CONFIRMATION_PASS · PR40_WRONG_PASSWORD_SESSION_PRESERVED · PR40_ACCOUNT_OWNERSHIP_PRESERVED | Unit, MockMvc, browser fixture và MySQL cô lập. |
| PR40_NO_EMAIL_BASED_ACCOUNT_MERGE · PR40_IDENTITY_CONFLICT_HANDLING_PASS · PR40_CONCURRENT_LINKING_PASS | Cùng email với account khác giữ nguyên cả hai, cùng subject chỉ một thành công, kiểm tra trùng trên cùng account. |
| PR40_CSRF_PROTECTION_PASS · PR40_REPLAY_PROTECTION_PASS · PR40_FLOW_TTL_ENFORCED · PR40_USER_SESSION_BINDING_PASS | Kiểm tra route, request thiếu token, Origin ngoài phạm vi, callback không hợp lệ, cùng ticket, TTL, đổi phiên/tài khoản, khóa/xóa và đổi token version. |
| PR40_RATE_LIMIT_VALIDATION_PASS | PASS phạm vi 429, Retry-After, 5 lượt start/complete và 10 lượt authorize/IP. Chưa chờ hết cửa sổ 300 giây để xác minh việc mở lại hạn mức ở runtime. |
| PR40_GOOGLE_SIGN_IN_REGRESSION_PASS · PR40_REFRESH_SESSION_REGRESSION_PASS · PR40_REACTIVE_AUTHORIZATION_PASS | Phạm vi fixture và test hiện có. Signed OIDC qua cả hai resolver, session restore và invalidation của HTTP client. Chưa kiểm tra đổi tài khoản ngay giữa callback trên trình duyệt thật. |
| PR40_PHASE0_SECURITY_PRESERVED · PR40_PUBLIC_RESEARCH_ISOLATION_PASS | MockMvc Research, Advisor/Comparable/Market research và Tomcat loopback. |
| PR40_BACKEND_REGRESSION_PASS · PR40_ISOLATED_MYSQL_PASS · PR40_FRONTEND_REGRESSION_PASS · PR40_VITE_BUILD_PASS · PR40_BROWSER_VALIDATION_PASS | Kết quả bảng kiểm thử trên. |
| PR40_SECRET_SCAN_PASS | Quét diff so với main và các đường dẫn bàn giao. Chỉ có fixture rõ ràng. Không bao gồm secrets thật, dump, tệp môi trường, dữ liệu hoặc model. |
| PR40_MIGRATIONS_UNCHANGED | `git diff --exit-code team/main HEAD -- database` trả 0. Không chạy Flyway trên DB thật. |
| V1.3 runtime integrity — NOT_RUN | Manifest SHA-256 và mã AI giống main. Thiếu 4 artifact inference trên máy để đối chiếu byte thực tế. Không đánh dấu PR40_V1_3_ARTIFACT_INTEGRITY_PASS. |
| PR40_PARALLEL_WORKTREE_ISOLATION_PASS | Worktree và server MySQL riêng. Các ref remote dưới đây chỉ đọc. |
| Kiểm tra remote HEAD | Xác minh SHA bằng `git ls-remote` sau khi bàn giao nhánh tích hợp. |
| **PR40_REAL_GOOGLE_OAUTH_NOT_RUN** | Chưa dùng Web OAuth Client thật, tài khoản Google thật, TLS hay callback production. |

## 4. Đối chiếu nhánh song song

Đối chiếu theo merge base giữa từng remote HEAD và `main` rồi lấy giao tập đường dẫn với PR #40.

| Nhánh | Remote HEAD | Chồng lấn | Điều cần giữ khi gộp |
| --- | --- | --- | --- |
| PR #37 News | `151a07b4472ea0fd3134fb50f4f3de757e83d46f` | `frontend/src/app/router.js` | Giữ route News và route hoàn tất liên kết Google cùng điều kiện xác thực. |
| WP02 Comparable | `29fc9c9f7761d79fd8d83c6203e59ba05c8e4c85` | Không có. Đã vào main qua #47. | Giữ ranh giới SAFE/Research và model V1.3. |
| WP04 Explainable AI | `6d27a9254ba7871d85682837636172184131c49a` | Không có tại thời điểm kiểm tra. | Giữ cơ chế reactive auth và thu hồi trạng thái Research khi đổi quyền. |
| PR #43 Advisor Land | `f59edf223c98249ee6104c367c34537bd851aea5` | README và router. | Giữ các route Advisor/Land, cấu hình dữ liệu và cả hai đường dẫn Google. |

## 5. Chạy lại và rollback

- Backend trên JDK theo `backend/pom.xml`. Chạy `.\mvnw.cmd -B test` trong `backend/`. Bật Docker để Testcontainers dựng DB riêng, hoặc chỉ trỏ fixture standalone khi đã xác minh đúng datadir, PID và marker. Lệnh test dùng schema thử, không xuất dữ liệu sang server dùng chung.
- Frontend trong `frontend/`. Chạy `npm ci`, `npm test`, `npm run build`. Nếu Playwright Core đặt ngoài repo, trỏ `PR40_BROWSER_PLAYWRIGHT` tới thư mục gói. Cài Chromium cho Playwright hoặc trỏ `PR40_BROWSER_EXECUTABLE` tới Edge/Chrome đã cài. Từ root chạy `node frontend/tests/browser/pr40-google-link.cjs`.
- RAG trong môi trường Python của dự án, tại `ai-services/`. Chạy `python -m unittest discover -s tests -p test_chat_checkpoints.py`, sau đó chạy cùng lệnh với `test_rag_multiturn.py`.
- Cấu hình thật theo README. Bật `GOOGLE_LOGIN_ENABLED`, `REFRESH_ENABLED` và `VITE_ENABLE_REFRESH`. Dùng OAuth Web application với exact callback, cùng hostname/origin với frontend. Dùng HTTPS và cookie Secure ngoài loopback. Lưu client ID/secret trong cấu hình backend riêng. Mở PR gốc vẫn ở chế độ Draft trong thời gian review.
- Nếu cần tạm ngưng luồng Google thì tắt `GOOGLE_LOGIN_ENABLED` và khởi động lại Backend. Cờ này cũng ngưng Google Sign-In. Nếu vẫn cần Sign-In, dùng bản frontend/backend của baseline đã phê duyệt `1c67a27` để rollback liên kết. Không có migration phải đảo ngược. Các hàng danh tính đã tạo hợp lệ tiếp tục tồn tại trong V15. Pending flow và ticket mất hiệu lực sau restart. Nhiều instance cần store dùng chung được thiết kế riêng.
- Chờ review độc lập, OAuth thật và xác minh runtime trước khi đổi trạng thái PR hoặc triển khai. Người review có thể bắt đầu từ diff `1c67a27...HEAD`, sau đó dùng kịch bản browser và bảng test trên.

**WAITING_FOR_PR40_FINAL_REVIEW**


## 6. Nghiệm thu sửa đổi PR #48

Ngày 28/11/2026. Bản review ban đầu `3ab750b8f458a4fec074ef1c8a2f6057fb0c16bc`. Main được duyệt và xác minh lại tại `1c67a279a8ff6f6939767e82bb31b17584610864`. Kiểm thử bản code cuối ở `4b04d643047dbe5a7bd09bbc9cb5466e4e9dab12`. Commit bàn giao tiếp theo cập nhật báo cáo. SHA local/remote đầy đủ được ghi trong mô tả PR. [PR #48](https://github.com/manchae19/SmartProp/pull/48)

| Finding | Sửa và bằng chứng |
| --- | --- |
| P2-01 – Phản hồi cũ theo phiên | `httpClient.js` đánh dấu thế hệ xác thực trong bộ nhớ. Refresh cùng subject, session và token version giữ nguyên phạm vi. Logout, đăng nhập lại cùng người, đổi người, đổi phiên qua refresh, mất xác thực và khóa tài khoản làm mất phạm vi cũ khi client xử lý trạng thái tương ứng. `AccountView.jsx`, `auth/api.js` và `GoogleLinkCompleteView.jsx` bỏ phản hồi, lỗi và chuyển hướng đến muộn. 401 đến từ access token cũ không hủy phiên cùng thế hệ đã refresh thành công. Request ghi cần người dùng gửi lại nếu credential cũ bị từ chối. |
| P2-02 – Runtime tích hợp | Chromium và React chạy qua proxy HTTPS loopback đến Spring Boot/Tomcat và MySQL 8.0.43 cô lập. Spring sử dụng bảng và repository thật trên schema chuẩn V1–V23. Provider kiểm thử dùng endpoint loopback, ký RSA và xác minh PKCE S256, code, redirect URI. App xác minh OIDC qua Spring. |
| P2-03 – Nhiều luồng | Mỗi cặp account/session có một luồng mới nhất. Sau xác nhận mật khẩu thành công, start mới hủy yêu cầu, callback đang trao đổi token và vé chưa tiêu thụ của luồng cũ. Callback bị hủy chỉ dọn chính luồng đã nhận. Ticket được tiêu thụ nguyên tử và yêu cầu đúng account/session. Tab cùng phiên dùng chung quy tắc, phiên hoặc tài khoản khác độc lập. Nếu complete đã nhận và tiêu thụ vé trước start mới, transaction đã bắt đầu tiếp tục theo kiểm tra phiên hiện tại. |
| Rate limit | Giữ 5 start và 5 complete trên mỗi phiên trong 300 giây, 5 lượt xác nhận mật khẩu trên mỗi tài khoản trong 300 giây và 10 authorize trên mỗi IP trong 60 giây. Đồng hồ kiểm thử xác nhận 429, Retry-After, giới hạn chung khi đổi phiên và chấp nhận lại sau khi hết cửa sổ. |

### Bằng chứng runtime và cookie

- Chromium đăng nhập bằng tài khoản SmartProp đã có mật khẩu. Sai mật khẩu trả 400, giữ phiên và không tạo cookie luồng. Mật khẩu đúng dẫn qua CSRF cookie/header, callback đúng origin và phục hồi đúng ID phiên trước khi gọi complete.
- Browser xác nhận cookie luồng và vé có HttpOnly, SameSite=Lax, Path=/api/v1/auth, Secure trên HTTPS và Max-Age lần lượt 300 và 60 giây. Complete xóa cả hai cookie và POST lại trả 410. Unit test dùng đồng hồ để xác nhận hết hạn.
- Google Sign-In thử nghiệm đăng nhập lại theo subject đã liên kết. Email của provider trùng một tài khoản SmartProp khác. Hai tài khoản vẫn độc lập, dữ liệu hồ sơ, role, password hash, quan hệ chủ tin, tin yêu thích và lịch sử định giá không đổi.
- Ca thứ ba giữ callback tại provider cho đến khi phiên SmartProp đã bị logout qua HTTP. Callback đến sau thu hồi, refresh trả 401, giao diện yêu cầu bắt đầu lại, không gửi POST complete và không ghi thêm danh tính. Unit test độc lập xác nhận service cũng từ chối hoàn tất với phiên đã bị thu hồi.
- Launcher kiểm tra cổng loopback, listener PID và datadir trước khi tạo schema. Harness kiểm tra lại JDBC URL, tên schema, MySQL UUID, datadir, cổng, user chỉ dùng cho schema thử và marker trước khi migrate. Dùng dữ liệu tổng hợp mới. Bốn ca SQL V15 tối giản và ca full-schema chạy trên hai schema riêng của cùng MySQL cô lập.

### Kết quả trên bản chốt

| Bộ kiểm thử | PASS | FAIL | SKIP | Exit |
| --- | ---: | ---: | ---: | ---: |
| Spring Boot Maven, gồm OIDC, Phase 0, auth/refresh, WP-02, MySQL và runtime | 316 | 0 | 0 | 0 |
| Fixture MySQL V15 tối giản, đã tính trong 316 | 4 | 0 | 0 | 0 |
| Chromium + Spring + MySQL + provider kiểm thử qua HTTPS, đã tính trong 316 | 1 | 0 | 0 | 0 |
| Node frontend recursive | 161 | 0 | 0 | 0 |
| Chromium React với API fixture, 8 ca desktop/mobile và 5 ca chuyển phiên | 13 | 0 | 0 | 0 |
| Vite production build | Hoàn tất | 0 | 0 | 0 |
| RAG fixture checkpoint và nhiều lượt | 26 | 0 | 0 | 0 |

Các mốc lỗi ban đầu của harness gồm cấu hình proxy HTTPS, so sánh geometry kiểu byte array và đồng bộ thời điểm callback thu hồi. Bộ kết quả trên lấy từ lần chạy hoàn tất sau khi sửa các lỗi fixture. Full FastAPI live, WP-02 live IT và runtime production chưa chạy. Runtime OAuth dùng provider loopback và key ký sinh tại chỗ. Google thật vẫn ở trạng thái `PR40_REAL_GOOGLE_OAUTH_NOT_RUN`. Việc đối chiếu đủ bốn tệp artifact inference V1.3 vẫn ở trạng thái `PR40_V1_3_ARTIFACT_INTEGRITY_PENDING`. Manifest và cây AI/migration giống main.

### Đối chiếu nhánh song song

| Nhánh | Remote HEAD đối chiếu | Đường dẫn chồng lấn với PR #48 |
| --- | --- | --- |
| WP-04 Explainable AI | `074bb7333b93651d8f0bd8cae5b4a01cf63f3834` | Không có |
| WP-05 Prediction Interval | `a0a5d88db1a77bc3dc55f9981dd313faa52f5b8b` | Không có |
| WP-06 Model Monitoring | Chưa thấy HEAD hoặc PR tương ứng ở remote | Chưa xác minh |
| PR #37 | `151a07b4472ea0fd3134fb50f4f3de757e83d46f` | Router |
| PR #41 | `da1d8c34c4303c84996f2f78212793c1f57a4228` | SecurityConfig |
| PR #43 | `f59edf223c98249ee6104c367c34537bd851aea5` | README, router, httpClient |

### Chạy lại và nghiệm thu thật

- Chạy `frontend/tests/browser/run-pr48-runtime.ps1` từ root, truyền `-MySqlBin`, `-PlaywrightCore` và `-BrowserExecutable` trỏ đến các công cụ đã có. Thêm `-OpenSsl` để kiểm tra TLS/Secure và `-FullRegression` để chạy cùng suite Maven. Các cổng mặc định cao và có thể đổi bằng `-MySqlPort` và `-FrontendPort`. Launcher tạo và dừng MySQL cô lập. Chỉ dùng các thư mục và log sinh ra từ máy thử nghiệm.
- Chạy `npm test` và `npm run build` trong frontend. Từ root chạy `node frontend/tests/browser/pr40-google-link.cjs` và `node frontend/tests/browser/pr48-session-scope.cjs` với Playwright/Chromium đã có. Lệnh RAG fixture giữ như mục 5.
- Khi chủ sở hữu duyệt cấu hình và tài khoản Google test, đăng ký đúng callback Web application, dùng cùng HTTPS origin, bật refresh trên cả FE/BE và đặt OAuth secret riêng tại backend. Dùng tài khoản SmartProp tổng hợp đã có mật khẩu. Kiểm tra liên kết, hủy, đăng xuất và đăng nhập bằng Google theo subject trên DB thử riêng. Chỉ ghi mã trạng thái, kết quả, phiên bản chạy và phép so sánh bảo toàn dữ liệu.
- Rollback như mục 5. Store vẫn trong bộ nhớ và có TTL. Restart làm hết hiệu lực luồng tạm. Nhiều instance cần thiết kế store dùng chung đã được review. Release vẫn chờ Google OAuth thật và xác minh môi trường triển khai.

**PR48_READY_FOR_FINAL_INDEPENDENT_REVIEW**

**WAITING_FOR_PR48_MERGE_AUTHORIZATION**

## 7. Tích hợp main sau PR #49

Ngày 28/11/2026. GitHub xác nhận PR #48 mở ở trạng thái Draft, head `287b4b2d032a3d22581fd993e212366c452d7c3a`, nhánh `integration/pr40-google-link-20261128`. Main được fetch và xác minh tại `d6be176f6c7fa27a1f33836e627965104f6a8d27`.

Commit nguồn đã kiểm thử `e61e9701d21ddbe56907279abf13fabb26fb6c24`, tree `4b290ff8116d507336c529cab0867afda6d9f60c`. Đây là merge commit có hai parent lần lượt là head PR #48 và main được duyệt. Commit bàn giao sau đó chỉ cập nhật báo cáo này. Mô tả PR ghi SHA và tree của cả hai commit.

### Giải quyết conflict và phạm vi

- Giữ nguyên byte Git của `frontend/src/shared/lib/httpClient.js` và `frontend/src/features/auth/api.js` từ main. Bản PR #49 đã cung cấp `getGoogleLinkScope`, `startGoogleLink` và `completeGoogleLink`. Kiến trúc dùng một HTTP client và một session store, hỗ trợ single-flight refresh, Web Locks, BroadcastChannel, `authGeneration` và `authTransition`. Phản hồi obsolete bị loại theo scope. Chỉ các request đọc an toàn đủ điều kiện mới được retry. Request ghi cần thao tác gửi lại rõ ràng.
- Giữ route `/auth/google/link/complete`, form xác nhận mật khẩu và màn hình callback của PR #48. Router tích hợp giữ xử lý profile điều hướng từ main. Backend Google Linking và bảy ca regression gốc giữ nguyên.
- Market, Comparable và Advisor giữ cơ chế thu hồi quyền, loại phản hồi stale và đường dẫn public SAFE từ main. Kiểm tra Git xác nhận `ai-services/` và `database/` giống main.

### Kết quả chạy trên cây tích hợp

| Kiểm thử | Kết quả | Exit | Log |
| --- | --- | ---: | --- |
| Shared HTTP/session | 65 pass, 0 fail/skip | 0 | `pr48-shared.log` |
| Bảy ca nguyên bản PR #48 | 7 pass, 0 fail/skip | 0 | `pr48-original7.log` |
| Market và Advisor reactive authorization | 24 pass, 0 fail/skip | 0 | `pr48-reactive.log` |
| Frontend recursive | 247 pass, 0 fail/skip | 0 | `pr48-frontend.log` |
| Google Linking Chromium với HTTP fixture | 8 kịch bản ở 1440/390 px | 0 | `pr40-browser.log` |
| Account/session transition Chromium với HTTP fixture | 5 kịch bản | 0 | `pr48-session-browser.log` |
| WP02 Chromium với HTTP fixture | 12/12 nhóm | 0 | `pr48-wp02.log` |
| Full Spring Boot với isolated MySQL và controlled OAuth | 316 pass, 0 fail/error/skip | 0 | `pr48-backend-runtime.log` |
| Vite production build | 270 modules | 0 | `pr48-build.log` |
| Asset audit | 147 tệp kiểm tra, 5 ảnh hạn chế vắng mặt, 30 asset duyệt khớp byte | 0 | `pr48-assets.log` |
| V1.3 artifacts | 8/8 kiểm tra SHA-256 và kích thước trên hai bản artifact | 0 | `pr48-artifacts.json` |

Bộ Spring gồm 44 ca Google Linking, OIDC và CSRF, trong đó có 4 ca SQL MySQL và 1 ca browser runtime chạy Spring/Tomcat và schema chuẩn V1–V23 trên MySQL riêng. Các số targeted nằm trong suite tổng tương ứng. Lượt mở WP02 đầu dừng ở cấu hình do thiếu biến `WP02_CHROMIUM`. Lượt chọn đúng Chromium và thư mục frontend chạy đủ 12 nhóm.

Lệnh Node chạy trong `frontend/`: `npm test`, `node --test tests/httpClient*.test.mjs tests/googleLinkSession*.test.mjs tests/pr49SharedAuthTransitions.test.mjs`, `node --test tests/googleLinkSession.test.mjs`, `node --test tests/marketAnalyticsSession.test.mjs tests/unifiedAdvisorSession.test.mjs`, `npm run build` và `node e2e/pr37-dist-assets.mjs`. Lệnh WP02 là `node tests/browser/wp02-browser.mjs` với `WP02_CHROMIUM` trỏ đến Edge cục bộ. Hai browser runner Google dùng `pr40-google-link.cjs` và `pr48-session-scope.cjs`. Spring chạy qua `frontend/tests/browser/run-pr48-runtime.ps1 -FullRegression` với MySQL và HTTPS loopback trên cổng 53983/53985. Log và các mã thoát nằm trong `.smartprop/` của worktree `pr48-final-main`.

### Bằng chứng bảo mật và giới hạn

- Xác nhận mật khẩu hiện tại, PKCE S256, state, OIDC issuer/signature/nonce, CSRF, scope tài khoản và session, vé chỉ dùng một lần và kiểm tra quyền phía server. Trùng Google subject bị từ chối. Trùng email giữa hai tài khoản không tự liên kết. Đối chiếu trong MySQL giữ nguyên tin, yêu thích và lịch sử định giá.
- Controlled OAuth qua Chromium xác nhận sai mật khẩu trả 400, phiên sống được khôi phục qua callback, cookie có Secure/HttpOnly/SameSite, replay trả 410 và callback đến sau logout bị chặn. Kiểm thử Java và browser fixture bổ sung account lock, session replacement, stale completion và renewal. `pr48-controlled-oauth.log` chỉ ghi method, route và status.
- Google OAuth thật, Caddy production và DB triển khai chưa được xác minh. Store pending flow/ticket nằm trong bộ nhớ, có TTL và thuộc phạm vi một instance. Fixture full-stack vẫn có HTTP 503 trên GET broker application, đã có trong lần kiểm tra PR #49 trước đó. Luồng liên kết, quyền, dữ liệu và các assertion OAuth đều đạt.
- Fixture đã dừng các listener của mình, năm listener mentor demo vẫn nguyên. Không đổi migration, weights, main hoặc worktree song song. Không triển khai.

Nguồn sẵn sàng cho review độc lập. PR duy trì Draft và chờ quyết định merge của chủ sở hữu.
