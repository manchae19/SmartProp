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
