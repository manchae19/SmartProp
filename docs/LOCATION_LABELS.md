# Địa bàn không dấu và tiêu đề tin trong dropdown — 26/10/2026

## Nguyên nhân đã xác nhận

Mã `new_unit:hoa xuan` trong vocabulary v6 cố ý được chuẩn hóa không dấu. Trước bản sửa, hàm `locationLabel()` ở FE chỉ cắt tiền tố rồi thêm “phường/xã”, nên mã nội bộ bị hiển thị trực tiếp. Đây là thiếu sót ở lớp hiển thị khi tích hợp FE, không phải lỗi font hoặc một phép suy luận tên địa danh của XGBoost.

Mã `new_unit:ban nha rieng duong nguyen duy hieu - phuong cam chau` là lỗi dữ liệu nguồn. Tin `homedy:3205669` không có quận/huyện; thành phần đầu `address_raw` thực tế là tiêu đề tin. Fallback trong `filter_all_collected.py`/`build_training_v1.py` lấy `new_unit:` cộng với thành phần đó, làm tiêu đề lọt vào `location_feature` và vocabulary của nhà ở. Đã đối chiếu lại audit nguồn: chuẩn hóa thành phần đầu địa chỉ khớp đúng mã hỏng. Mã này có trong **1 tin train**, không nằm trong **299 validation**.

## Cách xử lý

- [Catalog có kiểm tra](../ai-services/app/core/location_catalog_v6.json) lưu nhãn có dấu cho 7 mã quận/huyện lịch sử và 25 mã địa bàn mở rộng đang có trong v6. Tên được đối chiếu [danh mục chính thức trong Nghị quyết 1659/NQ-UBTVQH15](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1659-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-thanh-pho-da-nang-nam-2025-119250616202714604.htm).
- `/model/options` trả `location_labels` bên cạnh các mã lựa chọn. Mã không có nhãn đã kiểm tra bị loại khỏi danh sách. `/predict` cũng chặn mã đó bằng HTTP 422.
- FE chỉ hiển thị nhãn, vẫn gửi nguyên mã cho model. Dropdown tách nhóm quận/huyện cũ và địa bàn mở rộng. FE kết nối API cũ chưa có nhãn chỉ giữ các lựa chọn quận/huyện cũ đã biết, không tự đưa mã lạ hoặc tiêu đề ra màn hình.
- Không tự gán loại hành chính hoặc ánh xạ một mã mở rộng về quận/huyện cũ: fallback `new_unit:` chỉ nói cách mã được tạo, không chứng minh ranh giới địa lý. Nhãn “địa bàn mở rộng” thể hiện giới hạn này.
- `ward_source` là feature riêng, nay được ghi rõ **Phường/xã theo tin** trên form/kết quả. FE giữ dấu của giá trị người dùng nhập khi trình bày; giá trị chuẩn hóa model nhận và missing flag giữ nguyên. Không tự điền ô này từ lựa chọn địa bàn.

## Kiểm chứng và giới hạn

Đã chạy **19 kiểm thử API**, **10 kiểm thử FE**, **12 kiểm thử trình duyệt** và build. Đủ **299 dự đoán tham chiếu** vẫn khớp; case Hòa Xuân 200 m², 3 phòng, 2 tầng, kiệt, nhà cấp 4 vẫn trả **4.283.741.699 VND**. Request giữ `location_feature: new_unit:hoa xuan`; nhãn hiển thị thành “Hòa Xuân (địa bàn mở rộng)”.

Hash model, schema, hai module feature gốc và các CSV đã khóa giữ nguyên. Không huấn luyện lại hoặc viết lại báo cáo đánh giá cũ. Bản v6 vẫn từng học từ tin có mã sai; việc chặn API không xóa ảnh hưởng của tin đó trong model. Trước bản train mới, cần rà soát lại bằng chứng của `homedy:3205669` và xử lý luật tách địa bàn theo một phiên bản dữ liệu mới; không đoán lại địa điểm hoặc sửa snapshot cũ.

Sau cập nhật, khởi động lại FastAPI và tải lại trang FE để nhận catalog mới. Lần chạy API cũ trong bộ nhớ không tự nhận thay đổi mã nguồn.
