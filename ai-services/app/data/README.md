# SmartProp — dữ liệu và pipeline chung

Lọc toàn bộ dữ liệu đã cào bằng một lệnh từ `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/filter_all_collected.py
```

Xem [báo cáo của bản chạy mới nhất](processed/collection_pipeline/README.md).
Kết quả rà soát riêng cả 5.442 tin từng chờ nằm trong
[báo cáo nhóm chờ](processed/pending_collection_review/README.md).
Đợt bổ sung trang chi tiết cho 4.383 tin còn thiếu bằng chứng nằm trong
[báo cáo đối chiếu nguồn](processed/collection_source_review/README.md).
Pipeline đọc mọi nguồn raw, chuẩn hóa, áp dụng các quyết định rà soát nguồn đã lưu,
gom nghi trùng và xuất `eligible.csv`, `needs_review.csv`, `excluded.csv` cùng lý do.
`train_candidates.csv` chỉ chứa đại diện được phép xét cho train mới; giữ các nhóm
holdout trước đây khỏi train. Raw, các file duyệt và training_v1/v2 không bị ghi đè.
Đây là sàng lọc theo bằng chứng hiện có, chưa xác minh lại mọi trang chi tiết và
chưa thay thế bộ dữ liệu/model đã đánh giá. Singapore được kiểm kê riêng.

## Kiểm tra Nhadat24h — tài liệu đợt trước

File đầu vào có 2.027 dòng dữ liệu và một dòng tiêu đề. Tất cả 2.027 cặp source/source_listing_id đều khác nhau. Toàn bộ giá trị nguồn được giữ nguyên trong các CSV kết quả; cột bổ sung dùng để sàng lọc và đối chiếu.

## Kết quả

| Nhóm không chồng lặp | Số tin |
|---|---:|
| Ứng viên qua các quy tắc sàng lọc | 1.391 |
| Cần rà soát | 537 |
| Loại bất động sản khác, tách khỏi nhà/đất/căn hộ | 99 |
| Tổng | 2.027 |

Trong 1.391 ứng viên: 511 nhà ở, 347 căn hộ chung cư và 533 đất nền theo nhãn gợi ý. Đây là nhãn tự động, chưa xác minh trên trang chi tiết. Không gọi các ứng viên là dataset sạch hoặc giá giao dịch.

Có 77 tin giá “Thỏa thuận” và 224 tin có cờ giá theo quy tắc (đã bao gồm 77 tin thiếu giá). Có 7 tin nghi vấn diện tích. Có 22 tin trong 10 nhóm nghi trùng theo tiêu đề chuẩn hóa + quận + phường + giá + diện tích. Chưa xóa các tin này vì cùng thuộc tính không đủ chứng minh cùng bất động sản.

## Dùng file nào

- `processed/nhadat24h_audit.csv`: toàn bộ 2.027 tin với kết quả và lý do sàng lọc.
- `processed/nhadat24h_candidates.csv`: 1.391 ứng viên, chưa khử trùng xuyên nguồn.
- `processed/nhadat24h_houses_candidates.csv`: 511 ứng viên nhà ở; dùng để chuẩn bị bước gộp với mô hình nhà ở.
- `processed/nhadat24h_apartments_candidates.csv`: 347 ứng viên căn hộ.
- `processed/nhadat24h_land_candidates.csv`: 533 ứng viên đất.
- `processed/nhadat24h_needs_review.csv`: 537 tin cần rà soát theo `review_reasons`. Một tin có thể có nhiều lý do.
- `processed/nhadat24h_other_properties.csv`: 99 tin nhóm khác; vẫn giữ để dùng riêng.
- `processed/nhadat24h_recent_candidates.csv`: 1.101 ứng viên có tuổi theo thời gian hiển thị không quá 183 ngày tại lúc thu thập, gồm nhiều loại bất động sản.
- `processed/summary.json`: số liệu tổng hợp và mã SHA-256 đầu vào.
- `review_nhadat24h.py`: script tái lập kết quả; chỉ dùng Python standard library.

## Quy tắc và giới hạn

Địa điểm được kiểm tra bằng quận/huyện và địa chỉ thẻ tin. Toàn bộ file có quận/huyện trong bảy quận/huyện lịch sử của Đà Nẵng, chưa xác minh địa chỉ thực tế. `detail_fetched=False` cho toàn bộ tin.

Danh mục “Nhà đất thổ cư” không đủ để xác định nhà hay đất. Chỉ đề xuất loại khi danh mục cụ thể hoặc tiêu đề có dấu hiệu rõ; tin mâu thuẫn, có cả đất và nhà, hay còn mơ hồ vẫn cần rà soát. Tòa căn hộ/CHDV nguyên tòa, condotel, khách sạn, nhà trọ, shophouse và loại thương mại/nông nghiệp được giữ ngoài tập nhà/đất/căn hộ thông thường. Các quy tắc chỉ hỗ trợ phân loại; có thể còn sai hoặc thiếu.

Giá tổng được phân tích lại từ chuỗi hiển thị theo tỷ/triệu và so sánh với giá số của crawler. Không tự điền giá thỏa thuận. Các ngưỡng rà soát: giá dưới 100 triệu, đơn giá ngoài 2–300 triệu/m², diện tích ngoài 20–1.000 m². Đây là lựa chọn thử nghiệm, không chứng minh tin sai; không tự xóa giá cao/thấp. Không tự điền phòng ngủ, toilet hoặc tọa độ thiếu.

Thời gian hiển thị từ 04/01/2026 đến 09/10/2026. Có 1.753 tin hiển thị ngày cụ thể và 274 tin hiển thị số ngày trước. `displayed_date` của dạng tương đối được ước tính từ ngày thu thập ở UTC+7; không phải ngày đăng đã xác minh. Các trường `posted_at` và thời gian nguồn vẫn giữ nguyên. Thời gian hiển thị có thể phản ánh đăng lại/cập nhật.

Phân tuổi tại ngày thu thập: 1.568 tin không quá 183 ngày và 459 tin từ 184–366 ngày. Chưa có tin trên 366 ngày theo thời gian hiển thị trong file này. Giới hạn 183 ngày là lựa chọn baseline, không phải điều kiện bắt buộc. Giữ riêng dữ liệu cũ hơn để đánh giá ảnh hưởng thay vì xóa.

Chưa so khớp với Homedy, Chợ Tốt hoặc Batdongsan.vn. Khi gộp, loại trùng ID cùng nguồn rồi nhóm nghi cùng bất động sản xuyên nguồn. Giữ cùng nhóm bất động sản trong cùng tập train/validation/test và fit tiền xử lý trên train. Giá mục tiêu là giá rao bán.

## Chạy lại trên Windows

Chép script vào `F:\SmartProp\ai-services\app\data\`, rồi tại `F:\SmartProp` chạy:

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/review_nhadat24h.py --input ai-services/app/data/data_raw/nhadat24h_batch/nhadat24h_records.csv --output-dir ai-services/app/data/data_processed/nhadat24h_review
```

Nếu CSV nằm trong `nhadat24h_from_1200`, đổi đường dẫn `--input` tương ứng. Script không sửa CSV đầu vào và không dùng phép đảo nhãn dành riêng cho Chợ Tốt. Khi chạy lại với cùng thư mục kết quả, các CSV kết quả sẽ được tạo lại.
