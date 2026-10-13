# Dữ liệu huấn luyện v2 sau đối chiếu nguồn

Đã tải và kiểm tra đúng danh tính **87 trang** trong hàng chờ train/validation. Quyết định: {'pending': 24, 'exclude': 35, 'keep': 21, 'correct': 7}. Quyết định dựa trên trang đã lưu, không theo sai số dự đoán. Không liên hệ người đăng và chưa xác minh giao dịch/pháp lý thực tế.

V1 có 1383 tin; v2 giữ **1323 tin**, cách ly **60 tin** gồm chờ/loại và một tin nghi trùng bổ sung. Chia tập: {'train': 1067, 'test': 137, 'validation': 119}. Không bổ sung 308 tin của đợt rà soát loại vào lần này.

**Test được sao chép nguyên byte từ v1; không thay ID, nhãn hoặc nhóm. Train/validation giữ nguyên split/nhóm của những hàng được giữ.** Validation đã giảm số hàng và có nhãn được sửa nên không so trực tiếp MAE mới với MAE cũ toàn bộ validation. Đối chiếu chỉ trên cùng ID và cùng nhãn v2 khi thử mô hình tiếp.

## Nguyên tắc

- Giá/diện tích chỉ sửa khi nội dung xác định cùng tài sản và số chính xác; không suy tổng giá từ tiền cọc, lịch trả phần trăm hoặc giá mô hình.
- Gói nhiều lô/giỏ hàng/booking, công trình studio và căn hộ lưu trú rõ ràng được giữ riêng khỏi mô hình một nhà/lô/căn hộ thông thường.
- Chưa đủ bằng chứng hoặc sai địa bàn/loại/định nghĩa diện tích thì chờ. Có thể đề cập số đúng tiềm năng trong ghi chú nhưng không áp dụng vào nhãn.
- Giá rao có thương lượng, phương án thanh toán và diện tích sân vườn/ngoài sổ được giữ trong ghi chú. Nhãn nguồn khớp mô tả không phải giá giao dịch đã xác minh.
- Cờ hết hạn trong parser CafeLand được giữ ở bằng chứng; không tự loại chỉ vì chữ này xuất hiện trong trang.

## Tệp kết quả

- `train.csv`, `validation.csv`, `test.csv`, `main_dataset.csv`: bộ v2.
- `label_review_changes.csv`: nhãn cũ/mới và lý do từng tin được giữ/sửa.
- `quarantined_from_v1.csv`: tin chờ/loại/nghi trùng, không mất raw.
- [review_decisions.csv](../training_source_review/review_decisions.csv): quyết định của đủ 87 tin, URL, thời điểm lấy và SHA256 HTML.
- [source_evidence.csv](../training_source_review/source_evidence.csv): nội dung nguồn và đối chiếu nhãn. HTML trong `training_source_review/detail_cache`.
- `summary.json`: kiểm tra hash, số lượng và test giữ nguyên.

308 tin đã phân giải cờ loại ở đợt trước vẫn chưa được thêm. V2 chỉ xử lý 87 tin đang có trong v1. Các tin ngoài hàng chờ giữ chất lượng sàng lọc ban đầu, chưa được kiểm tra lại chi tiết toàn bộ.

Chạy lại `python ai-services/app/data/finalize_training_source_review.py`: chỉ kiểm tra hash nếu v2 đã được chốt; muốn đổi quyết định phải tạo phiên bản khác.
