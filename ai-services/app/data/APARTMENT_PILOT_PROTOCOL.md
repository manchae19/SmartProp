# Quy trình lô thử 100 tin căn hộ

Đợt ngày 27/10/2026, theo [issue #7](https://github.com/manchae19/SmartProp/issues/7).
Chốt quy tắc trước khi xem dự đoán trên lô mới. Không đọc sai số mô hình để chọn tin.

- Thu tối đa 100 ID mới so với snapshot 8.509 tin. CafeLand công khai, kiểm tra
  robots.txt, cách tối thiểu 3 giây mỗi yêu cầu, tối đa 12 trang danh sách mỗi
  lần chạy. Tiếp tục checkpoint, giữ cache riêng. Chỉ cho phép chuyển hướng HTTPS
  cùng nguồn, cùng ID, được robots cho phép; JSON-LD phải xác nhận URL cuối.
- Tách ngày nguồn hiển thị khỏi thời điểm thu thập. Ngày nguồn có thể là ngày
  cập nhật/đăng lại; không chứng minh đây là bất động sản mới lên thị trường.
  Lô thử ưu tiên ngày nguồn trong 183 ngày tính từ ngày thu tại Việt Nam.
- Nhãn đích là **tổng giá rao VND**, không phải giá giao dịch. Cần giá và diện
  tích có cấu trúc, khớp danh sách/chi tiết/JSON-LD. Không lấy diện tích từ tiêu
  đề để tự điền nhãn thiếu. Các dấu hiệu giá trả trước, bảng hàng, nhiều căn,
  toàn tòa nhà, condotel, công trình chưa hoàn thành, mâu thuẫn nội dung/địa bàn
  đều đưa vào hàng đợi, giữ nguyên bằng chứng.
- Ngưỡng rà soát căn hộ theo quy tắc đang có: giá tối thiểu 500 triệu, diện tích
  25–200 m², đơn giá 15–150 triệu/m². Đây là ngưỡng ưu tiên duyệt, không chứng minh
  tin ngoài ngưỡng sai. Giá tổng và diện tích phải được mô tả của người đăng
  xác nhận, bỏ phần nguồn tự chèn tiêu đề/địa chỉ. Các số chênh quá 1% cần rà
  soát (cho phép làm tròn nhỏ); mâu thuẫn số phòng cũng cách ly. Không tự sửa số.
  Các bổ sung này xuất phát từ đọc nội dung, chưa xem dự đoán: tin bán toàn tòa
  7 phòng bị nguồn gắn nhãn căn hộ; tiêu đề 2PN nhưng mô tả 3PN; giá thanh toán
  70% đứng cạnh giá tổng. Không có giá/diện tích cụ thể trong mô tả thì chưa
  chứng minh được một căn có tổng giá xác định, dù đủ nhãn ở đầu trang.
- Đối chiếu toàn bộ 8.509 tin, kể cả tin bị loại và các tập đã giữ riêng. Giữ
  nhóm trùng cũ; thêm liên kết tiêu đề, diện tích/giá, tiêu đề tương tự bất kể
  giá (đề phòng đăng lại đổi giá), mô tả dài trùng và cụm nội dung gần trùng.
  Đây là **nghi trùng tài sản**, không phải xác nhận cùng căn. Nhóm có liên kết
  dữ liệu cũ được cách ly hoàn toàn. Một nhóm có nhãn/nội dung chưa rõ cũng
  không được đưa một thành viên khác vào tập học hoặc kiểm chứng.
- Không suy đoán tọa độ hoặc quận cũ từ một phường mới cắt qua nhiều địa bàn.
  Chỉ dùng khóa địa bàn đã có trong danh mục v6 hoặc ánh xạ hiện hành có bằng chứng.
- Khóa toàn bộ ứng viên qua quy tắc thành `collection_holdout`, **không huấn
  luyện trên lô này**. Cần tối thiểu **20 nhóm căn hộ qua rà soát** để cân nhắc
  đánh giá thăm dò v6/v7. Đây là mốc thực hành, không bảo đảm ý nghĩa thống kê.
  Dữ liệu huấn luyện v7 phải đến từ một đợt khác, được lọc và so trùng với tập
  đã khóa. Nếu chưa đủ 20 nhóm, giữ chúng để bổ sung cùng giao thức; chưa chạy
  v7 hoặc đo lặp trên vài tin để lựa chọn cấu hình.
- Không thay train/validation/holdout cũ, model v6, API hay database đang chạy.
  Lưu checksum raw, cache, quy tắc và danh sách khóa. Báo cả độ phủ bằng chứng
  mô tả lịch sử: không có cache không có nghĩa là đã chứng minh khác tài sản.

Ứng viên không có cờ vẫn là nhãn giá rao được rà soát bằng quy tắc, chưa xác
minh căn nhà thực địa hoặc giao dịch. Lô cùng nguồn/cùng thời điểm không thay
thế kiểm chứng độc lập nhiều nguồn và kiểm chứng thời gian.
