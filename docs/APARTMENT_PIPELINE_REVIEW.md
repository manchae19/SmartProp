# Review pipeline căn hộ trước PR #10

Phạm vi đầu: `aa30b4e...f1301d5` (hai commit `9108b5d`, `f1301d5`).
Spec: issue #7, #8 và hai giao thức căn hộ trong `ai-services/app/data/`.
Review theo skill [code-review](../.agents/skills/code-review/SKILL.md).

## Standards

Không thấy vi phạm quy ước có văn bản trong `AGENTS.md`, các tài liệu agent
hoặc `.gitattributes`.

- **P3, heuristic Duplicated Code:** hai bản review lặp cổng xung đột nhóm:
  giá 5%, diện tích 1%, địa bàn, thành viên chưa rõ. Đây là nhận xét thiết kế,
  không phải vi phạm bắt buộc. Giữ mã đã khóa checksum; bản mới tái sử dụng
  hàm nhóm hiện có thay vì thêm một bản cổng khác.
- **Correctness P2:** collector v1 không bảo vệ `lock.unlink()` khi xuất CSV
  lỗi. Đường chạy mới luôn nhả khóa đã giữ, lưu nhật ký bền vững và cho phép
  phục hồi CSV đã kiểm SHA/replay trước khi khóa cohort.

Review bổ sung đã tái hiện thêm race: log/checkpoint đổi sau preflight nhưng
trước lấy khóa, có thể ghi lặp ID hoặc lùi checkpoint. Đã bổ sung snapshot
policy/log/checkpoint, kiểm tra lại ngay khi lấy khóa và từ chối không export
nếu trạng thái đổi. Regression dùng lịch xen kẽ trong thư mục tạm, không gọi mạng.

## Spec

- **P1:** lọc nhãn v2 khôi phục mô tả trước footer, nhưng dedup vẫn dùng ranh
  giới v1. Hai ID khác nguồn/tiêu đề khác nhau, mô tả dài giống nhau kết thúc
  “liên hệ để nhận thông tin chi tiết” có thể lọt cohort. Đã dùng ranh giới v2
  cho cả tin mới và lịch sử; regression yêu cầu liên kết lịch sử và cách ly,
  đồng thời giữ nguyên mô tả nguồn trong đầu ra.
- **P2:** entry point collector cũ ghi `latest_run.json` ngay cả khi đã hoàn
  tất hoặc từ chối policy, làm metadata đã khóa đổi. Giữ mã cũ cho replay;
  hướng dẫn chuyển sang status chỉ đọc và đường chạy mới kiểm tra trước mọi ghi.
  Không sửa âm thầm SHA của script/run lịch sử. Hạn chế: gọi trực tiếp entry
  point lịch sử vẫn có lỗi này; không dùng chúng để vận hành batch đã khóa.
- **P2 bổ sung:** bước chuẩn bị v7 giả định cohort có dòng đầu tiên. Đã đọc
  header kể cả cohort rỗng, viết qua thư mục staging rồi mới công bố manifest/
  latest. Có regression cho cohort chỉ có header.

Không thấy sửa nhãn giá/diện tích hoặc split cũ. Chuẩn bị v7 chỉ đặt missing
`rooms_completed` khi có cờ xung đột, không fit/chấm trong bước chuẩn bị.
So trùng vẫn dựa vào bằng chứng văn bản, chưa chứng minh độc lập tài sản thực tế.

Tổng trục đầu: Standards 0 vi phạm bắt buộc, 1 smell (kèm 1 lỗi correctness);
Spec 2 finding, nặng nhất P1. Các lỗi mới được xử lý theo đường chạy có phiên
bản và kiểm thử; mã/run đã chốt giữ nguyên, cổng nhóm không bị nới để đủ mẫu.

## Kiểm tra bổ sung sau thử nghiệm

- Race đã có regression; lỗi đọc SHA sau lấy khóa cũng được bảo vệ cleanup.
- Bản chuẩn bị hoàn tất có thể phục hồi pointer sau cửa sổ crash giữa rename
  và publish; chỉ công bố lại khi khớp protocol cùng toàn bộ input/output SHA.
- Trainer lịch sử chặn theo SHA lock nhưng chưa đủ để chống cohort mở rộng.
  Entry point vận hành `run_v7_trial.py` kiểm giao record/nhóm với mọi receipt,
  đồng thời từ chối grouping view bỏ mất ID đã chấm. Có kiểm thử đổi metadata,
  mở rộng lock, ID mới cùng nhóm và view thiếu ID. Mã/model run đã chấm giữ nguyên.
- Verifier tải lại model, kiểm đủ tập key/config và nhãn nguồn, rồi khớp
  receipt run/cohort/members. Run hiện tại không có rò rỉ train/validation.

Hạn chế còn lại: entry point lịch sử giữ nguyên để replay, không dùng để vận
hành; hướng dẫn mới dùng wrapper. Không tự merge hoặc triển khai model.
