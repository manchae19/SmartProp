# Mở rộng kiểm chứng và sửa so trùng — 27/10/2026

Giữ nguyên các batch/run #7–#8 và mã được khóa checksum. Hai bản đầu là bằng
chứng lịch sử; bản mở rộng phải kiểm tra lại tính độc lập nhóm trước khi sử dụng.

Review mã phát hiện phần so trùng vẫn dùng ranh giới mô tả v1, trong khi phần
lọc nhãn đã dùng v2. Phiên bản này dùng cùng `subject` v2 cho mô tả cả hai phía:
tin mới và bằng chứng lịch sử. Giữ raw gốc, giá/diện tích và tất cả liên kết
nhóm cũ. Tin mới liên kết lịch sử hoặc nhóm có cờ vẫn bị cách ly; không tách
nhóm hoặc sửa giá để tăng số lượng. Có kiểm thử tái hiện tiêu đề khác nhau,
mô tả dài trùng kết thúc bằng câu “liên hệ để nhận thông tin chi tiết”.

Lô CafeLand bổ sung riêng: tối đa **80 ID mới** so với toàn bộ **8.611 ID**,
bắt đầu ở trang đang dở của lô trước, tối đa **8 trang** cho toàn lô, nhịp từ
3 giây. Dùng robots, URL cùng nguồn/cùng ID và bộ đọc nguồn như lô đầu.
Không sửa checkpoint, CSV hoặc metadata của lô cũ. Dữ liệu mới giữ riêng,
tiếp tục nhật ký JSONL và checkpoint, không dùng để train.

Sau lô 80 có 18 nhóm đạt cổng (chưa dự đoán), bổ sung một batch riêng tối đa
**40 ID mới**, **4 trang** từ checkpoint batch 80, đối chiếu **8.691 ID**.
Giữ nguyên các cổng; không bảo đảm số lượng đạt. Không ghép batch để đổi hạn
mức cũ. Kết quả cuối gộp tất cả các batch trước khi khóa nhóm.

Lệnh `collect_apartment_extension.py --status pilot|nhadat|extension` chỉ đọc.
Không chạy lại entry point collector v1/v2 trên batch đã khóa: mã lịch sử có
nhánh `finally` ghi metadata kể cả khi từ chối policy hoặc đã đủ tin. Lệnh
mở rộng mới kiểm tra policy/hoàn tất trước mọi ghi; khóa luôn được tháo trong
`finally` kể cả CSV đang bị Excel khóa. Nếu xuất CSV thất bại, JSONL vẫn giữ
nguyên; cần phục hồi CSV từ log khi đóng tệp đang khóa trước khi rà soát.

Khóa toàn bộ nhóm đạt cổng nguồn/ngày/giá/diện tích thành `collection_holdout`.
Mốc 20 nhóm chỉ là mốc thực hành, không bảo đảm thống kê. Chưa train/chấm v7
khi chưa đạt hoặc còn vấn đề chống trùng. Không tạo tọa độ/POI giả, không dùng
giá AI làm nhãn, không thay model/API v6 hoặc database đang chạy.
