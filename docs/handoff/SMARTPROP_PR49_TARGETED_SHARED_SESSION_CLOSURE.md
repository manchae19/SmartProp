# PR #49 — Targeted shared-session closure

## Baselines và phạm vi

- PR #49 branch `integration/pr37-ui-validation`, reviewed remote `33024758a4ee7e01702e4c8bda6049d8bc076075`, local checkpoint `15af5a378424fa4de77f631d7c7f135d19c7b4ed`.
- Hợp đồng PR #48 được pin tại `287b4b2d032a3d22581fd993e212366c452d7c3a`, main đã duyệt `1c67a279a8ff6f6939767e82bb31b17584610864`.
- PR #49 sở hữu duy nhất một shared HTTP client và session store. Backend OAuth, Account UI Google Linking và các test browser PR #48 chỉ được overlay để thử trên archive cô lập. Nhánh PR #48 và PR #37 gốc không thay đổi.

## Tái hiện và sửa

Chạy chính file test PR #48 trên HTTP client ở checkpoint `15af5a3`, với auth API từ PR #48 để đưa đúng consumer vào test. Baseline 4 passed, 3 failed, exit 1. File test giữ nguyên Git blob `850c4f051059a2868495d4f0ff91d921e28977e9`, có đủ assertions gốc.

| Ca gốc | Bằng chứng tại checkpoint | Hành vi sau sửa |
| --- | --- | --- |
| Same-user khác session | Dòng 150 thấy scope vẫn bằng `0` dù promise đã reject. Fixture có JWT claims `iss/sub/jti/ver`. | Khác `jti` hoặc `sub` thu hồi credential và linking scope cũ, hủy hiệu lực response đang pending, trả `SESSION_CHANGED`. Khôi phục cookie sau đó bắt đầu bằng initialization riêng. |
| Login cùng account khi có request pending | Dòng 167 nhận `1` thay vì `null` khi login còn pending. | Login, logout và Google completion tăng generation và đưa `authTransition=true` trước bất kỳ async work. Operation mới nhất sở hữu transition. Login lỗi không khôi phục hiệu lực của request đã phát. Navigation bị hủy khi profile load trả `SESSION_CHANGED`. |
| Linking GET cũ nhận 401 | Dòng 207 nhận HTTP 401 thay vì kết quả retry. | GET/HEAD/OPTIONS từ phiên còn hợp lệ có thể thử một lần bằng credential đã renew. Một POST nhận 401 dù session đã recover vẫn trả `AUTH_RETRY_REQUIRED`. Không expire credential mới từ 401 cũ. Current linking 401 vẫn expire, lỗi mật khẩu nghiệp vụ giữ session. |

Refresh bình thường cần khớp issuer, cùng `sub/jti` có cấu trúc hợp lệ và account server response phù hợp. Đổi `ver`, role hoặc status có thể cập nhật trạng thái authoritative cùng server session và làm cũ mọi restricted response trước đó. Opaque hoặc malformed token không chứng minh renewal; luồng đăng nhập hoặc cookie restoration có thể tạo scope mới độc lập. Frontend dùng claims để fence UI, Spring tiếp tục xác minh JWT/session và quyền. Các test HTTP cũ nay dùng JWT fixture cho các ca cần continuity, giữ cửa kiểm thử opaque riêng. External ABA và đổi authority cùng token đều tăng scope, một refresh flight theo generation và scope, `sessionScope()` chỉ có generation/flag, AbortSignal tiếp tục áp dụng.

BroadcastChannel gửi hai action `login` và `logout` không kèm credential. Web Locks dùng chung cho refresh và mutation cookie khi trình duyệt hỗ trợ.

## Fresh evidence

Tested source commit `55050196387e00934ded0867acafe1338c1886d3`, tree `6e4c3a7b09497da9dc7ce68fbaf53c028e119617`. Báo cáo được thêm sau lượt test. Relative paths dưới đây nằm trong worktree PR #49.

| Lệnh hoặc fixture | Kết quả | Evidence |
| --- | --- | --- |
| `node --test tests/googleLinkSession.test.mjs` | 7/7, exit 0 | `.smartprop/pr49-original-before.log`, `.smartprop/pr49-original-after.log` và suite tổng hợp bên dưới |
| `node --test tests/httpClient*.test.mjs tests/googleLinkSession*.test.mjs tests/pr49SharedAuthTransitions.test.mjs` | 65/65, 0 failures/skips, exit 0. Lặp lại 65/65 trong source archive. | `.smartprop/pr49-http.log`, `.smartprop/pr49-archive-unit.log` |
| `npm.cmd test` | 242/242, 0 failures/skips, exit 0. Bao gồm các test targeted Node. | `.smartprop/pr49-frontend.log` |
| `node tests/browser/pr40-google-link.cjs`, `node tests/browser/pr48-session-scope.cjs` trong overlay | 8/8 và 5/5, exit 0 mỗi lệnh. Chromium với HTTP fixtures. | `.smartprop/pr49-pr40-google-link.log`, `.smartprop/pr49-pr48-session-scope.log` |
| `node tests/browser/wp02-browser.mjs` | 12/12 Chromium, exit 0. HTTP fixtures. | `.smartprop/pr49-wp02.log` |
| `node e2e/pr37-validation.e2e.mjs --groups=g1,g2,g3,g13,g8,g12` | 6/6 Chromium, exit 0. HTTP fixtures. | `.smartprop/pr49-market-browser.log` |
| `node e2e/pages-smoke.e2e.mjs` | 11/11 route/viewport assertions, exit 0. HTTP fixtures. | `.smartprop/pr49-pages.log` |
| `npm.cmd run build`, `node e2e/pr37-dist-assets.mjs` | Vite 268 modules. Asset audit 145 dist files, 5 hình bị loại không xuất hiện, 30 approved assets khớp byte. Cả hai exit 0. | `.smartprop/pr49-vite.log`, `.smartprop/pr49-assets.log` |
| `frontend/tests/browser/run-pr48-runtime.ps1 -MySqlPort 53431 -FrontendPort 53433 -FullRegression` cùng các đường dẫn binary đã cài | 316/316 Spring, 0 failures, errors hoặc skips, exit 0. Tổng này đã gồm 1 Chromium full-stack runtime test, 4 isolated MySQL integration tests và các Auth/Phase 0 checks. | `.smartprop/pr49-runtime.log`, `.smartprop/pr49-runtime-browser.log` |

Combined runtime dùng archive của PR #49 source tree, PR #48 reviewed backend và fixture browser, cùng route hoàn tất Google Linking được overlay. Auth API và HTTP client giữ byte của tree PR #49. `.smartprop/pr49-combine.py` tạo archive, overlay và ghi SHA‑256 từng source file trong `.smartprop/pr49-combined-manifest.json`. Chạy launcher PR #48 bằng MySQL 8.0.46, V23, Spring Boot/Tomcat, Vite, Chromium, OpenSSL, signed OIDC provider, HTTPS loopback và `-FullRegression`. Fixture MySQL ở `127.0.0.1:53431`, frontend ở `127.0.0.1:53433`, datadir riêng, launcher xác minh process ownership và fixture test xác minh UUID, marker, database, account giới hạn, port và datadir. Browser đưa một 401 có kiểm soát để kích hoạt refresh thực; refresh và GET retry dùng Spring. Repo không thêm migration hoặc dependency. Protected DB, Google OAuth thực và production deployment nằm ngoài lượt kiểm thử này.

Chromium xác nhận password confirmation, linking, cùng-session refresh, JWT Spring ký và quyền gọi profile, Web Locks queue trong browser, cùng-user khác session làm stale response trả `SESSION_CHANGED`, cross-tab login/logout, callback bị thu hồi, Google Sign-In sau linking, cookie flags và account/listing/favorite/history ownership. Các lượt đầu đã chạy qua OAuth gốc nhưng báo lỗi trong phần chờ của assertion bổ sung. Lượt cuối sửa async polling trong fixture và chạy lại toàn bộ. Launcher dừng đúng fixture và cả hai port đều được xác nhận đã đóng.

## Reactive UI authorization closure

Source commit đã kiểm thử `52b8fd87d0fdb65f643b8f5cc8d37993760087a2`, tree `dce41bc691a4ad9ab4df58ab61294b24bf3819b0`. Các ca mới dừng response bằng deferred barriers để tái lập thứ tự đổi quyền và hoàn thành request.

- **Market Analytics** xóa research đang hiển thị, abort research request, bỏ opt-in và chuyển sang SAFE khi auth transition bắt đầu hoặc generation thay đổi. Failed login hay phục hồi thông tin cũ cần opt-in lại. Renewal cùng session giữ kết quả và request đang chạy.
- **Comparable WP‑02** dùng cùng projected scope cho trang trực tiếp và các lookup nhúng. Role, account status, auth transition và generation tham gia kiểm tra scope. Locked account và transition không gửi request mới. Response cũ bị loại cả khi revoke và restore trước lần render kế tiếp.
- **Các consumer gần kề**. Google Linking đã dùng generation và transition qua auth API. Market Insights và Top Searched Areas chỉ gọi SAFE. Unified Advisor và Advisor legacy có cùng khoảng trống ở research scope nên được vá tại gate hiện hữu. Unified Advisor dùng abort riêng cho research; Advisor legacy abort capability probe và loại response cũ bằng sequence guard, giữ SAFE hoạt động. Audit cũng ghi nhận AdminLayout lấy số liệu dashboard lúc mount, với route và API kiểm quyền riêng. Lượt này không thay đổi lifecycle toàn khu admin hoặc các route owner-only.

| Fresh check | Kết quả | Log trong `.smartprop/` |
| --- | --- | --- |
| Original PR #48, Git blob `850c4f051059a2868495d4f0ff91d921e28977e9` | 7/7 | `pr49-ui-pr48-7.log` |
| Shared-session/HTTP | 65/65 | `pr49-ui-shared.log` |
| Market và Unified Advisor targeted | 24/24 | `pr49-ui-targeted.log` |
| Frontend recursive | 247/247 | `pr49-ui-frontend.log` |
| Chromium WP‑02 | 12/12, bổ sung assertion cho BROKER/ADMIN, account lock, generation và restore | `pr49-ui-wp02.log` |
| Chromium PR #49 | Market g1/g2/g3/g13 và g8/g12 6/6; route/viewport smoke 11/11 | `pr49-ui-market-browser.log`, `pr49-ui-pages.log` |
| Hai browser harness PR #48 với HTTP fixture | Google Linking 8/8, session-scope 5/5 | `pr49-ui-pr40-google-link.log`, `pr49-ui-pr48-session-scope.log` |
| Vite và asset audit | 269 modules, 146 tệp dist; 5 ảnh bị loại vắng mặt và 30 approved assets khớp byte | `pr49-ui-vite.log`, `pr49-ui-assets.log` |

Tất cả lệnh ở bảng exit 0. Các bộ Node có 0 failed, cancelled hoặc skipped. Các test mục tiêu đã nằm trong frontend recursive.

`REUSED_EVIDENCE` cho 316/316 Spring và controlled OAuth HTTPS runtime ở tree `6e4c3a7b09497da9dc7ce68fbaf53c028e119617`. Manifest SHA‑256 của hai archive kết hợp xác nhận HTTP client, auth API, router, app entry, Login/Google/Account views, OAuth harness, provisioning script, dependency lock và toàn bộ backend/PR #48 OAuth overlay giống nhau. Delta chỉ có các UI nghiên cứu/Comparable, fixture regression của chúng và tài liệu. Hai browser harness PR #48 đã chạy mới trên archive kết hợp với tree reactive. Không khởi động lại MySQL fixture và chưa xác minh Google OAuth thực hoặc deployment.

## Delivery

Delivery ban đầu đã hoàn tất bằng OAuth GitHub. Local, remote branch và Draft PR #49 được xác minh ở `6e6b059ecc0f8ff5e93941974ef33103b1e25f87`; PR body đã được đọc lại để xác minh nội dung. Phiên này tiếp tục từ đúng SHA đó, giữ PR #49 Draft và đưa bản vá reactive lên cùng nhánh qua fast-forward. Main, PR #48 và PR #37 gốc giữ nguyên. [PR #49](https://github.com/manchae19/SmartProp/pull/49)
