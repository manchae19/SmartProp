# Domain Docs

SmartProp dùng bố cục **single-context**: thuật ngữ dùng chung trong `GLOSSARY.md`, quyết định kiến trúc trong `docs/adr/`, đều tính từ gốc repo.

## Trước khi khảo sát mã nguồn

- Đọc `GLOSSARY.md` nếu đã có.
- Nếu repo sau này có `GLOSSARY-MAP.md`, đọc map và các glossary liên quan đến công việc.
- Đọc các ADR trong `docs/adr/` có liên quan đến khu vực sắp thay đổi. Nếu sau này có ADR theo từng context, đọc cả các quyết định tương ứng.

Nếu glossary hoặc thư mục ADR chưa tồn tại, tiếp tục công việc. Skill `domain-modeling` tạo tài liệu khi thuật ngữ hoặc quyết định thực sự được chốt; không tạo glossary/ADR trống chỉ để hoàn tất setup.

## Dùng thuật ngữ thống nhất

Khi đặt tên khái niệm trong issue, đề xuất, giả thuyết hoặc test, dùng thuật ngữ đã định nghĩa trong glossary. Khái niệm chưa được định nghĩa cần đối chiếu với cách gọi hiện tại của dự án; ghi nhận khoảng trống có thật để xử lý qua `domain-modeling`.

## Mâu thuẫn với ADR

Nếu đề xuất trái với ADR hiện có, nêu rõ mã/tệp ADR và lý do muốn xem xét lại. Giữ quyết định hiện hành cho đến khi có quyết định thay thế được ghi nhận.
