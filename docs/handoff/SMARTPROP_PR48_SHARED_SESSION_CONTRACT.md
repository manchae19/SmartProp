# PR #48 và PR #49 — Hợp đồng shared session

Main baseline `1c67a279a8ff6f6939767e82bb31b17584610864`. PR #48 được kiểm theo `287b4b2d032a3d22581fd993e212366c452d7c3a`. PR #49 sở hữu một triển khai HTTP/session tại `frontend/src/shared/lib/httpClient.js` và một session store tại `frontend/src/features/auth/api.js`. PR #48 giữ backend OAuth và Google Linking UI trên nhánh riêng. [Báo cáo và bằng chứng tích hợp](SMARTPROP_PR49_TARGETED_SHARED_SESSION_CLOSURE.md)

## Identity, generation và credential

- `authGeneration` là bộ đếm **phía frontend** trên session store. Nó tăng khi phạm vi phiên hoặc authority thay đổi. JWT do Spring cấp mang `iss`, `sub`, `jti` và `ver`. Spring xác minh JWT và tiếp tục quyết định quyền truy cập. Frontend dùng claims để kiểm tra continuity trong scope đã nhận từ luồng xác thực.
- Cùng `sub/jti/ver` và authority qua refresh hợp lệ giữ nguyên `authGeneration`. Một thay đổi `ver`, role hoặc account status loại response nhạy cảm đã bắt đầu trước đó. Khác `sub/jti` hoặc token thiếu claims hợp lệ thu hồi scope cũ. Có thể bắt đầu scope khác qua login hoặc cookie initialization riêng.
- `scopeGen` tăng khi có credential write bên ngoài HTTP client. External A → X → A không khôi phục scope đã hết hiệu lực. `credentialGen` đếm các lần client cài credential, gồm renewal và khởi tạo. Client giữ một current credential và một snapshot credential gần nhất để nhận diện external writes.
- `sessionScope()` trả `epoch`, `identityEpoch`, `credentialGen`, `scopeGen`, `authGeneration` và cờ `authenticated`. Hàm này không chứa credential hay lịch sử token.
- Khóa của refresh flight gồm `epoch`, `identityEpoch`, `scopeGen`, `credentialGen` và `allowNewIdentity`. Chỉ flight đang sở hữu reference được xóa reference. Initialization kiểm tra epoch, identity, scope và credential gốc trước khi nhận profile, đổi status hoặc xử lý terminal error.

## Ownership và lỗi HTTP

- Login, logout và Google completion đặt `authTransition=true` và tăng generation trước async work. Chỉ operation đang sở hữu transition được kết thúc nó. Failed login có thể giữ credential trước đó trong scope mới. Work cũ vẫn bị loại.
- BroadcastChannel gửi action `login` hoặc `logout`. Tab khác xóa scope cũ và lấy credential qua cookie restoration nếu có refresh. Web Locks điều phối refresh và thay đổi cookie khi được hỗ trợ.
- 401 muộn có thể dùng credential đã refresh trong cùng session để thử lại safe GET/HEAD/OPTIONS. Phản hồi từ credential cũ không expire credential mới. Current-session 401 vẫn theo policy của route. Lỗi mật khẩu/validation của Google Linking giữ phiên hiện tại. Write bất định trả `AUTH_RETRY_REQUIRED` và yêu cầu người dùng chủ động gửi lại. AbortSignal không expire phiên.
- Market và các Advisor research surfaces bỏ dữ liệu research, hủy request hoặc probe theo cơ chế sẵn có và tắt opt-in khi scope đổi hoặc đang auth transition. Comparable ẩn hoặc vô hiệu hóa kết quả của scope cũ, chặn gọi khi account bị khóa hoặc không còn role phù hợp và yêu cầu truy vấn mới sau khi quyền trở lại. Các UI giữ scope khi JWT đổi qua verified same-session renewal. Backend authorization giữ nguyên.

## Tích hợp và tái kiểm thử

Dùng worktree cô lập ở đúng SHA PR #48. Giữ backend, Google Linking view và callback route của PR #48. Dùng shared HTTP client, auth API và các test từ PR #49; áp riêng hunk navigation bỏ profile response obsolete. Chạy bộ PR #48 nguyên bản, HTTP client, frontend và hai Chromium fixture scripts. Nếu thay đổi shared HTTP client, auth API hoặc OAuth execution path thì chạy lại `run-pr48-runtime.ps1` với MySQL Standard V23 và signed OIDC trên HTTPS loopback. PR #49 có hướng dẫn theo SHA và cách chạy trong PR body. [PR #49](https://github.com/manchae19/SmartProp/pull/49)
