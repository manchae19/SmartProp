# Rà soát tiếp 90 tin và bổ sung nguồn — 27/10/2026

Tiếp nối [issue #7](https://github.com/manchae19/SmartProp/issues/7) qua
[issue #8](https://github.com/manchae19/SmartProp/issues/8). Giữ nguyên raw,
giao thức và bản khóa `apartment_pilot_review/runs/52c6b97aeb3f7227`.
Chưa đọc dự đoán/sai số trên dữ liệu mới để chọn tin hoặc sửa nhãn.

Giữ các ngưỡng giá/diện tích/ngày và cổng bằng chứng trong giao thức trước.
Phiên bản quy tắc mới chỉ sửa các trường hợp có bằng chứng ngôn ngữ:

- Cụm “liên hệ để nhận thông tin chi tiết” ở cuối mô tả không phải ranh giới
  bắt đầu mô tả. Chỉ bỏ metadata đứng đầu; cắt footer người đăng; bỏ phần nguồn
  tự lặp nhãn “Giá ... VND Diện tích ... m2”. Không dùng phần lặp để xác nhận nhãn.
- Từ “lỗ” phải là một từ độc lập, không nằm trong “block”. Nhãn “Giá bán” có
  ý nghĩa rõ hơn ngữ cảnh cho thuê ở câu trước; giá `/tháng` vẫn là giá thuê.
- “3 tỷ nhỉnh nhẹ” là mô tả xấp xỉ, không phải một giá tổng thứ hai. Chỉ nhận
  khi có giá bán chính xác khớp nhãn cùng diện tích, và không còn cờ khác.
- Không điền giá/diện tích thiếu, không chọn một phía của JSON-LD mâu thuẫn,
  không giải thích nhiều căn hoặc giá trả trước thành một căn có giá tổng.
  Nói rõ “codotel” cũng giữ chờ rà soát như “condotel”.

Mỗi tin trong 90 tin có quyết định và bằng chứng: bổ sung ứng viên, loại khỏi
phạm vi căn hộ bán, hoặc còn thiếu bằng chứng. “Loại” chỉ áp dụng cho nội dung
rõ ở tiêu đề/chủ thể: Huế, bán toàn tòa, homestay nguyên tài sản, hoặc đề nghị
cho thuê. Không xóa raw hoặc tự chuyển các tin này sang train nhà ở.

Nguồn bổ sung Nhadat24h: tối đa **30 ID chưa có trong 8.609 ID**, tối đa **12
trang danh sách cho toàn lô**, nhịp từ 3 giây, robots và checkpoint riêng. Không
theo chuyển hướng hoặc vượt chặn. JSON-LD Product phải xác nhận URL và tiêu đề;
trang thiếu Product chỉ được lưu chờ duyệt dựa trên URL/tiêu đề, cấm vào tập
kiểm chứng. Tách ngày lịch nguồn khỏi ngày thu; không suy ngày đăng từ “13 ngày trước”.
Chỉ được cập nhật mã collector trong lô dở khi toàn bộ tin đã lưu phân tích
lại giống hệt; lưu lịch sử policy, không đổi phạm vi, raw hoặc số nhãn.

So trùng 8.509 tin lịch sử, 100 tin CafeLand và tin bổ sung. Giữ liên kết nhóm
cũ, kể cả nhóm nghi trùng chưa giải thích được; không tách nhóm để tăng mẫu.
Mọi thành viên nhóm có nhãn chưa rõ vẫn bị cách ly. Nếu bằng chứng mới liên kết
với nhóm đã khóa, giữ bản cũ nguyên byte và ghi rủi ro/cách ly trong bản mở rộng.
Không dùng train/validation cũ hoặc pilot đã chấm để bù số lượng kiểm chứng mới.

Khóa toàn bộ nhóm qua rà soát làm `collection_holdout`; không thêm vào train.
Mốc 20 nhóm vẫn chỉ là mốc thực hành. Không đủ thì báo đúng số và chưa train/
chấm v7. Tài liệu/quy tắc được giữ trên Git; bằng chứng mô tả, HTML và CSV chỉ
giữ cục bộ. Model/API v6 và database đang dùng không thay đổi.
