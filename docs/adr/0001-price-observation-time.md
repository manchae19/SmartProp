# Lưu nhiều quan sát cho một tin rao

Giữ định danh tin duy nhất và bổ sung quan sát bất biến theo thời điểm thực sự đọc trang, thay vì bỏ qua ID cũ hoặc ghi đè giá. Dữ liệu hiện có thường chỉ có ngày đăng/cập nhật do nguồn hiển thị; gán giá vừa đọc về ngày đó sẽ tạo lịch sử chưa từng được quan sát. Vì vậy ngày nguồn được giữ làm metadata, chuỗi giá dùng thời điểm quan sát; lịch sử người dùng lưu kết quả AI thuộc nghiệp vụ riêng và không được nhập làm giá thị trường.

Tin biến mất chỉ mang nghĩa nguồn trả 404/410 tại lần đọc; không suy ra đã bán hoặc giá bằng 0. Thiếu tọa độ hoặc bằng chứng đặc trưng vẫn giữ thiếu. Kho nghiên cứu cục bộ tách khỏi MySQL của người dùng để không đưa dữ liệu nguồn chưa đủ kiểm chứng vào luồng định giá đang chạy.
