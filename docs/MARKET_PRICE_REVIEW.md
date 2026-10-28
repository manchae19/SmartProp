# Review quan sát giá rao

Ngày29/10/2026. Theo skill `code-review`, so sánh mốc
`24b074731d028c2d9fe4c0ae8b86f2a0ca6b4adc` với commit `533c0a1` cho issue#11.
Hai trục được rà độc lập; các bản sửa sau được kiểm tra lại có mục tiêu.

## Standards

Không phát hiện vi phạm tiêu chuẩn đã ghi trong repo. Một heuristic P3:
phần diễn giải phản hồi lặp trong collector và verifier. Đã gom vào
`interpret_response`, giữ đối chiếu replay riêng. Kiểm tra lại:0 vi phạm,
0 heuristic còn mở trong phạm vi này.

## Spec

Hai lỗi P2 đã được tái hiện và sửa:

1. HTTP200 rỗng gây `lxml.etree.ParserError`, chưa lưu bằng chứng/trạng thái.
   Hàm dùng chung hiện bắt `LxmlError`, lưu `parse_error` với giá thiếu và replay
   cùng cách diễn giải. Regression đi qua collector, lưu kho và verifier.
2. Ngắt giữa ghi HTML để lại file mang tên SHA nhưng nội dung dở, làm retry
   luôn thất bại. Hiện ghi/fsync temporary rồi công bố bằng hard link nguyên
   tử, từ chối ghi đè; dọn temporary khi lỗi. Regression ngắt sau5byte xác
   nhận không làm hỏng evidence cuối và retry lưu được đúng một quan sát.

Kiểm tra lại: cả2 lỗi đã sửa, không có finding Spec còn mở trong phạm vi này.
22 kiểm thử quan sát giá đạt, gồm2 regression mới. Bằng chứng đã công bố mà bị
sửa vẫn bị từ chối. Raw/model/split/ledger và lịch sử tài khoản không bị sửa.
