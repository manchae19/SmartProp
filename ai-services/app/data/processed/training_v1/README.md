# Bộ dữ liệu huấn luyện v1 — thử nghiệm

Từ 2,780 ứng viên: **1,383 tin tập chính có ngày**, **720 tin thiếu ngày giữ riêng**, **522 tin cách ly**, **155 tin nghi trùng không dùng làm đại diện**.

Giá mục tiêu là giá rao bán toàn bộ, đơn vị triệu VND; diện tích m². Nhãn được đối chiếu với các trường raw hiện có, chưa xác minh lại toàn bộ trang chi tiết và chưa phải giá giao dịch. Nhiều raw không lưu mô tả đầy đủ nên chưa kiểm tra được mọi điều kiện trong nội dung.

| Loại | Train | Validation | Test |
|---|---:|---:|---:|
| Nhà ở | 657 | 68 | 80 |
| Đất nền | 292 | 37 | 37 |
| Căn hộ chung cư | 171 | 21 | 20 |

## Quy tắc lựa chọn

- Chỉ xét 2.780 ứng viên của audit mở rộng; không tự nhập 17 nhãn duyệt trước vào bộ này.
- Đối chiếu lại giá thô/giá chi tiết, giá dương và diện tích hợp lệ, loại bán, địa bàn, cờ loại/ngày nguồn, nhiều tài sản hoặc nhiều tổng giá trong tiêu đề. CafeLand luôn bật cờ ngày khi lưu ngày cập nhật: giữ nếu đã phân tích được mốc này, không coi đó là ngày đăng đầu.
- Giữ nguyên các ngưỡng audit. Không cắt ngoại lệ theo phân phối toàn bộ dữ liệu hoặc dùng test để chọn ngưỡng.
- Gom nghi trùng trên toàn bộ 8.509 ID, gồm liên kết audit cũ, tiêu đề chuẩn hóa trùng (ít nhất 6 từ khác nhau), hoặc tiêu đề tương tự ≥0,88 với giao token ≥0,65/8 từ, diện tích lệch ≤1%, giá lệch ≤5%. Không giới hạn quận để bỏ sót ít hơn khi địa bàn đổi tên.
- Liên kết nghi trùng có thể gom nhầm hoặc bỏ sót. Nhóm có mâu thuẫn giá/diện tích/loại/quận cũ, hoặc liên kết với nhãn đã sửa/chờ/loại được cách ly để duyệt.
- Mỗi nhóm giữ một đại diện: ưu tiên có ngày, có snapshot chi tiết, thời điểm thu thập mới hơn, sau đó ID. Các thành viên vẫn có trong nhật ký, không xóa raw.
- Nhóm được chia cố định bằng SHA256, ngưỡng 80/10/10; không phân tầng nên tỷ lệ thực tế dao động. Đây là đánh giá ngẫu nhiên theo nhóm, chưa phải dự báo thời gian tương lai.
- Tập thiếu ngày không trộn vào tập chính; nếu thử nghiệm bổ sung, chỉ dùng các hàng có model_split=train để giữ nguyên holdout chính.
- district giữ nhãn lịch sử; location_feature dùng quận cũ nếu có, nếu không dùng đơn vị địa chỉ mới. Không ép phường mới vào quận cũ.

## Sử dụng

`train.csv`, `validation.csv`, `test.csv` là đầu vào tập chính. Chỉ chọn biến đầu vào có sẵn tại thời điểm dự đoán. **Không dùng price_per_sqm_million, tiêu đề/mô tả chứa giá, raw_json, mã nhóm hay các cờ kiểm tra giá làm đặc trưng**, vì có thể tiết lộ nhãn. Mọi encoder, chuẩn hóa và chọn mô hình phải học trên train, chọn bằng validation; test dùng báo cáo cuối.

`candidate_decisions.csv` đối soát mọi ứng viên; `quarantined.csv` ghi lý do cách ly; `suppressed_duplicates.csv` ghi ID đại diện. `possible_duplicate_pairs.csv` và `all_collection_group_assignments.csv` giữ bằng chứng gom nhóm trên toàn bộ bộ sưu tập.

Dữ liệu gốc và các bộ baseline/apartment/Singapore trước được giữ nguyên. Bộ v1 có split riêng, không so trực tiếp sai số với test cũ.

Chạy lại: `python ai-services/app/data/build_training_v1.py`. Sau đó chạy `python ai-services/app/data/train_training_v1.py` để cập nhật mô hình cơ sở.

Xem [kết quả mô hình cơ sở](BASELINE.md). Nếu xây lại dữ liệu, phải chạy lại mô hình để chỉ số khớp hash đầu vào.
