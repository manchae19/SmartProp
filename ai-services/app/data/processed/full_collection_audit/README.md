# Kiểm tra toàn bộ dữ liệu đã thu thập

> **Phạm vi đã được mở rộng theo yêu cầu:** chấp nhận Đà Nẵng cũ và Đà Nẵng mới, gồm Quảng Nam cũ. Xem [kết quả hiện hành](../full_collection_audit_expanded/README.md): 2.780 ứng viên qua quy tắc, tăng 96 tin. Báo cáo bên dưới giữ lại kết quả đối chiếu theo 7 quận/huyện cũ; không dùng giới hạn địa bàn cũ để loại tin trong đợt rà soát mới.

Ngày đối chiếu: 2026-10-11. Đã đọc 20 file CSV/JSONL nguồn, gồm batch chính, file cũ, sample, file bổ sung và cách ly. Không đọc lại các CSV processed như tin mới.

## Số lượng đã đối soát

- Việt Nam: **8,509 ID nguồn duy nhất**, không đồng nghĩa từng đó bất động sản khác nhau.
- Có 11,297 dòng CSV Việt Nam và 120 dòng JSONL mirror; tổng 11,417 quan sát/snapshot.
- 2,883 ID xuất hiện ở nhiều quan sát. Không cộng mẫu thử, file khôi phục và bản JSONL/CSV thành các tin mới.
- Không có ID trùng trong từng file Việt Nam. Không có lỗi cấu trúc CSV/JSONL hoặc ID không hợp lệ trong snapshot hiện tại.
- Không tìm thấy khác biệt giá/diện tích đáng kể giữa các snapshot cùng ID. Sai số float nhỏ không coi là mâu thuẫn; việc này không chứng minh giá nguồn đúng.
- `danang_bds_10k_raw.csv` và `nhadat24h_quarantine.csv` hiện không có dòng dữ liệu.

| Nguồn | ID duy nhất | Qua quy tắc, có ngày | Qua quy tắc, thiếu ngày | Đã duyệt giữ/sửa từ căn hộ |
|---|---:|---:|---:|---:|
| alonhadat | 37 | 35 | 0 | 0 |
| cafeland | 2,300 | 804 | 0 | 0 |
| chotot | 2,753 | 88 | 0 | 0 |
| homedy | 1,392 | 18 | 807 | 0 |
| nhadat24h | 2,027 | 932 | 0 | 17 |

## Trạng thái loại trừ nhau

| Trạng thái | Số tin |
|---|---:|
| Qua quy tắc, có mốc hiển thị/cập nhật; chưa xác minh sạch | 1,877 |
| Cần rà soát nhãn/chất lượng/bằng chứng | 3,278 |
| Chưa gán chắc một quận/huyện cũ | 727 |
| Đã duyệt căn hộ: loại khỏi phạm vi | 7 |
| Đã duyệt căn hộ: đang chờ xác minh | 40 |
| Ngoài hoặc chưa chứng minh thuộc Đà Nẵng cũ | 594 |
| Loại khác/toàn công trình hoặc có dấu hiệu cần phân loại riêng | 1,162 |
| Qua các quy tắc khác nhưng chưa có ngày | 807 |
| Đã duyệt căn hộ: sửa nhãn | 11 |
| Đã duyệt căn hộ: giữ nhãn | 6 |

Các nhóm trạng thái cộng đúng tổng ID Việt Nam. Cột `review_codes` có thể chứa nhiều lý do cùng lúc; không cộng số cờ thành số tin.

## Những vấn đề đáng chú ý

- 4,025 tin không có mốc đăng/cập nhật đáng tin trong dữ liệu; không dùng ngày thu thập hoặc URL ảnh thay thế.
- 2.653 tin Chợ Tốt cũ thiếu ngày, giá thô gốc, trường loại giao dịch và bằng chứng tỉnh nguồn. Tên file Đà Nẵng + nhãn quận chỉ là dấu hiệu phạm vi, chưa đủ xác minh. Không tự coi mọi tin là bán.
- 393 tin Homedy ngoài hoặc chưa chứng minh thuộc Đà Nẵng cũ; giữ riêng khỏi nhóm ứng viên.
- 1,420 tin thiếu/không hợp lệ giá số; 1,259 tin thiếu/không hợp lệ diện tích số. Nhiều thẻ CafeLand có văn bản giá/diện tích nhưng để trống số chuẩn hóa do chưa lấy chi tiết, khác lỗi chuyển đổi đơn vị.
- 220 tin có dấu hiệu giá trong tiêu đề lệch nhãn; 238 tiêu đề có dấu hiệu thanh toán/giá khởi điểm/booking. Cờ chỉ ưu tiên duyệt, có thể sai với số viết tắt hoặc quảng cáo.
- 490 tin có mốc hiển thị/cập nhật quá 183 ngày; 4 tin có tọa độ cần kiểm tra địa lý.
- 359 cặp nghi cùng bất động sản, trong đó 90 cặp khác nguồn. Nhóm nghi trùng chỉ là heuristic theo tiêu đề, quận/loại, diện tích và giá; không tự xóa tin.

Đối với 64 căn hộ đã duyệt: tham chiếu nguyên 11 sửa, 6 giữ, 7 loại, 40 chờ; không ghi đè quyết định hoặc dữ liệu v2. Audit này giữ giá/diện tích raw trong cột chính; nhãn sửa trước đó nằm ở `prior_corrected_*`, không phải lần sửa mới.

## Mốc thời gian trong dữ liệu

| Nguồn | Có mốc | Mốc nhỏ nhất | Mốc lớn nhất | Quá 183 ngày |
|---|---:|---|---|---:|
| alonhadat | 37 | 2026-10-05 | 2026-10-10 | 0 |
| cafeland | 2,300 | 2026-03-14 | 2026-10-10 | 16 |
| chotot | 100 | 2026-10-09 | 2026-10-10 | 0 |
| homedy | 20 | 2026-08-06 | 2026-10-02 | 0 |
| nhadat24h | 2,027 | 2026-01-04 | 2026-10-09 | 474 |

Đây là mốc hiển thị/cập nhật nguồn; không khẳng định ngày đăng đầu hoặc ngày giao dịch. Nhadat24h có ngày tương đối được ước lượng theo ngày thu thập. Homedy chỉ tìm được ngày ở 20 ID từ snapshot thử cùng ID; các tin khác không suy ngày. Tọa độ kiểm tra bằng hình chữ nhật 15,6–16,5°N / 107,7–108,5°E chỉ là cờ kỹ thuật, không phải ranh giới pháp lý.

## Dữ liệu Singapore

Đã kiểm tra riêng **242,454 dòng HDB**, tháng 2017-01 đến 2026-10. Không có dòng bị cờ thiếu trường/giá SGD/diện tích/tháng không hợp lệ theo quy tắc. Có 318 dòng giống hệt dòng trước; nguồn không có ID giao dịch duy nhất nên không kết luận đó là giao dịch trùng và không xóa.

Tháng 10/2026 đang diễn ra tại ngày kiểm tra, không coi là dữ liệu tháng đầy đủ. HDB là giá giao dịch SGD, khác giá rao Việt Nam; không cộng vào 8.509 ID và không ghép vào tập huấn luyện trong lần này.

## Phạm vi kiểm tra và tệp kết quả

**Đã kiểm tra toàn bộ bản ghi trong các file nguồn đã phát hiện. Chưa truy cập lại toàn bộ trang chi tiết và chưa kiểm tra tất cả URL còn sống.** Cờ `detail_fetched` chỉ nói crawler từng lưu dữ liệu từ chi tiết; không có nghĩa lần này đã đọc lại đầy đủ mô tả. Bằng chứng HTML của đợt 64 căn hộ được giữ nguyên ở thư mục trước.

Giá theo tỷ/triệu, diện tích m², giá số/giá văn bản và giá chi tiết được đối chiếu khi có. Giá trả trước, thuê, giảm giá, giá/m² được phân biệt bằng ngữ cảnh. Ngưỡng rà soát: tổng giá 100–200.000 triệu; diện tích 20–1.000m²; đơn giá 2–300 triệu/m². Căn hộ ưu tiên thêm giá dưới 500 triệu hoặc đơn giá ngoài 15–150 triệu/m². Ngưỡng là quy tắc kỹ thuật, không kết luận mặt bằng thị trường.

Địa bàn dùng bộ phân giải 7 quận/huyện cũ đã có của dự án, giữ các đơn vị mới giao nhau ở trạng thái mơ hồ. Không dùng phường mới để ép thành một quận cũ. Chưa xác minh tọa độ thực địa/quyền sở hữu/giá giao dịch.

- `all_unique_listings_audit.csv`: 8.509 ID Việt Nam, từng lý do và provenance bản gốc.
- `needs_review.csv`: mọi tin cần xử lý phạm vi, loại hoặc chất lượng, gồm nhóm ngoài phạm vi và các quyết định chờ/loại trước đó.
- `screened_candidates_unverified.csv`: các tin qua quy tắc; chưa phải bộ sạch, chưa loại hết nghi trùng bất động sản.
- `all_snapshot_observations.csv`: mọi snapshot Việt Nam, giữ JSON gốc và vị trí dòng nguồn.
- `file_inventory.csv`, `repeated_source_ids.csv`: kiểm kê và ID xuất hiện nhiều quan sát.
- `possible_duplicate_properties.csv`: hai ID/URL và quy tắc nghi trùng.
- `snapshot_value_conflicts.csv`, `malformed_rows.csv`: các vấn đề cấu trúc/khác biệt snapshot; hiện chỉ có header.
- `singapore_flagged_rows.csv`, `singapore_exact_row_repeats.csv`: kiểm tra riêng HDB.
- `summary.json`: số lượng, khoảng ngày, quy tắc, SHA256 của tất cả đầu vào.

Đã đối chiếu SHA256 trước/sau: toàn bộ đầu vào giữ nguyên. Không huấn luyện lại hoặc thay tập test ở lần audit này.

## Ưu tiên tiếp theo

1. Giải quyết tin thuê/booking/toàn công trình, loại ngoài 7 quận/huyện và địa bàn chưa rõ.
2. Đối chiếu nguồn cho các mâu thuẫn tổng giá, giá trả trước, giá/m²; xử lý 40 căn hộ đang chờ nếu có bằng chứng mới.
3. Bổ sung bằng chứng ngày, loại giao dịch và giá gốc cho Chợ Tốt cũ; không tự suy từ tên file.
4. Kiểm tra các cặp nghi trùng theo dự án/mã căn, rồi mới chốt phiên bản dữ liệu dùng huấn luyện.

Chạy lại từ `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/audit_all_collected.py
.\ai-services\.venv\Scripts\python.exe -m unittest discover -s ai-services/app/data -p test_audit_all_collected.py
```
