# SmartProp

SmartProp ước tính giá rao bất động sản và nghiên cứu biến động giá rao từ dữ liệu có nguồn.

## Language

**Tin rao**:
Một tin do nguồn công bố, được nhận diện bởi tên nguồn và ID tin. Một tài sản có thể có nhiều tin rao.

**Quan sát giá rao**:
Giá và trạng thái trang tin mà hệ thống thực sự đọc được tại một thời điểm, kèm bằng chứng nguồn. Ngày đăng hoặc cập nhật của nguồn không thay thế thời điểm quan sát.
_Avoid_: Giá giao dịch, giá lịch sử tại ngày đăng

**Nhóm tài sản ứng viên**:
Các tin có bằng chứng nghi cùng tài sản và được xử lý chung để hạn chế đếm trùng. Nhóm này chưa chứng minh tài sản đã được xác minh ngoài thực tế.

**Lịch sử định giá**:
Kết quả AI mà người dùng lưu cùng thông tin đầu vào. Đây không phải quan sát giá thị trường hoặc nhãn giá giao dịch.

**Chuỗi giá rao mô tả**:
Thống kê giá rao theo thời gian của mẫu đã thu thập và rà soát. Biến động cơ cấu mẫu, đăng lại và độ phủ nguồn có thể ảnh hưởng thống kê này.
_Avoid_: Giá thị trường chính thức, dự báo giá
