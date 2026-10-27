# Issue tracker: GitHub

Issue và spec của SmartProp được quản lý tại https://github.com/manchae19/SmartProp/issues. Dùng GitHub CLI (`gh`), chỉ định `--repo manchae19/SmartProp` cho các thao tác issue để xác định đúng repo.

## GitHub CLI trong Codex IDE trên máy hiện tại

Nếu `gh` chưa có trong PATH, dùng bản CLI chính thức đã kiểm tra SHA-256 qua helper PowerShell tại `.scratch/setup-matt-pocock-skills/gh.ps1`, ví dụ:

```powershell
& ./.scratch/setup-matt-pocock-skills/gh.ps1 issue list --repo manchae19/SmartProp --state open
```

Helper tái sử dụng đăng nhập GitHub của Git Credential Manager cho từng lệnh và chỉ giữ token trong bộ nhớ tiến trình. Không in hoặc lưu token vào repo. Khi máy khác đã có GitHub CLI đăng nhập sẵn, dùng trực tiếp các lệnh `gh` dưới đây.

## Quy ước

- Tạo issue: `gh issue create --repo manchae19/SmartProp --title "..." --body-file <file.md>`.
- Đọc issue: `gh issue view <number> --repo manchae19/SmartProp --json number,title,body,labels,comments`.
- Liệt kê issue: `gh issue list --repo manchae19/SmartProp --state open --json number,title,body,labels,comments`. Dùng bộ lọc `--label`/`--state` phù hợp; kiểm tra giới hạn/phân trang khi cần đọc toàn bộ.
- Bình luận: `gh issue comment <number> --repo manchae19/SmartProp --body-file <file.md>`.
- Thêm/bỏ nhãn: `gh issue edit <number> --repo manchae19/SmartProp --add-label "..."` / `--remove-label "..."`.
- Đóng issue: `gh issue close <number> --repo manchae19/SmartProp`.
- Nội dung nhiều dòng được lưu vào file UTF-8 và truyền bằng `--body-file`, giữ nguyên xuống dòng và ký tự đặc biệt.
- Quan hệ cha/con: dùng sub-issue nếu CLI/API hiện tại hỗ trợ. Khi không có sub-issue, đặt `Part of #<parent>` ở đầu issue con và liên kết issue con trong task list của issue cha.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Khi skill yêu cầu xuất bản lên issue tracker

Tạo GitHub issue trong `manchae19/SmartProp`. Khi skill yêu cầu đọc ticket liên quan, đọc issue theo số hoặc URL được cung cấp, gồm nội dung, nhãn và bình luận.

## Nhãn triage

Ánh xạ vai trò và ý nghĩa nằm trong `docs/agents/triage-labels.md`. Khi thiết lập, chỉ tạo nhãn còn thiếu; giữ nguyên nhãn đã tồn tại.

## Wayfinding

Các quy ước này phục vụ skill `wayfinder` khi được gọi:

- Map: một issue mang nhãn `wayfinder:map`, chứa Notes / Decisions-so-far / Fog.
- Ticket con: một issue liên kết với map bằng sub-issue hoặc task list + `Part of #<map>`. Nhãn loại là `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling` hoặc `wayfinder:task`.
- Phụ thuộc: ưu tiên issue dependencies của GitHub. Nếu không hỗ trợ, dùng dòng `Blocked by: #<n>, #<n>` ở đầu nội dung. Ticket chỉ hết bị chặn khi mọi blocker đã đóng. API dependencies dùng database ID của issue, không dùng số `#number` hoặc `node_id`.
- Frontier: xét các ticket con còn mở theo thứ tự trong map; bỏ qua ticket còn blocker mở hoặc đã có assignee.
- Nhận việc: `gh issue edit <number> --repo manchae19/SmartProp --add-assignee @me` trước khi thực hiện ticket.
- Hoàn tất: đăng câu trả lời, đóng ticket, rồi thêm tóm tắt và liên kết vào Decisions-so-far của map.
