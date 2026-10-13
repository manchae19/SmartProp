# Bổ sung bằng chứng cho 4.383 tin đang chờ

Đối chiếu trang nguồn theo ID/tiêu đề, vùng nội dung chính, loại tài sản, giá tổng, diện tích và địa bàn. Đây là kiểm tra tự động theo quy tắc có lưu HTML/hash, không phải xác minh giao dịch hay duyệt tay từng tin.

| Nguồn | Số tin | Trang HTTP 200 | Đúng ID/tiêu đề | Giữ | Sửa loại | Loại | Chờ |
|---|---:|---:|---:|---:|---:|---:|---:|
| alonhadat | 5 | 5 | 5 | 1 | 0 | 0 | 4 |
| cafeland | 1,414 | 1,414 | 1,414 | 496 | 13 | 47 | 858 |
| chotot | 1,798 | 0 | 0 | 0 | 0 | 0 | 1,798 |
| homedy | 328 | 321 | 318 | 62 | 0 | 15 | 251 |
| nhadat24h | 838 | 838 | 838 | 60 | 49 | 4 | 725 |

**Quyết định nguồn chưa đồng nghĩa đủ điều kiện train.** Sau khi áp dụng vào pipeline chung, tính lại tuổi tin, ngưỡng số, nhóm nghi trùng và bảo vệ holdout:

| Kết quả riêng hàng chờ 4.383 tin | Số tin |
|---|---:|
| [eligible](queue_eligible.csv) | 449 |
| [needs_review](queue_needs_review.csv) | 3,832 |
| [excluded](queue_excluded.csv) | 102 |

Trong nhóm qua lọc, **355** đại diện được xét cho train; phần còn lại bảo vệ holdout. Không đưa toàn bộ nhóm giữ/sửa loại vào train.

## Lý do chính còn chờ (không chồng lặp)

| Nhóm | Số tin |
|---|---:|
| Giá có điều kiện/nhiều tài sản/dự án/tài sản đặc thù | 809 |
| Giá/diện tích/cấu trúc trường chưa rõ | 883 |
| Trường hợp phức tạp đang chờ từ đợt duyệt trước | 64 |
| Loại tài sản thiếu căn cứ hoặc mâu thuẫn | 139 |
| Nhóm nghi trùng còn mâu thuẫn hoặc thành viên chờ | 54 |
| Ngày đăng thiếu, cũ hoặc chưa xác minh | 75 |
| Nguồn chặn truy cập; chưa kiểm tra từng URL | 1,798 |
| Trang lỗi hoặc chưa tải được | 7 |
| Chưa đối chiếu được đúng ID/tiêu đề | 3 |

## Bằng chứng và giới hạn

- [review_decisions.csv](review_decisions.csv): mỗi ID một quyết định, loại đề xuất, giá/diện tích đề xuất, URL, hash HTML và lý do. Các cột sửa giá/diện tích để trống; không tự coi thay đổi trên trang hiện tại là lỗi của snapshot cũ.
- [parsed_evidence.json](parsed_evidence.json), [fetch_manifest.json](fetch_manifest.json), `detail_cache/`: nội dung chính đã trích và trang tải thực tế. `reviewer=source_detail_rules_not_manual_verification` phân biệt với duyệt tay.
- 1.798 tin Chợ Tốt chưa được yêu cầu từng URL. Nguồn từng trả 403 ở một URL thử; không diễn giải thành 1.798 URL đều trả 403. Không vượt chặn truy cập.
- Trang lỗi/chuyển ID/tiêu đề không khớp, ngày thiếu/cũ, giá/diện tích mâu thuẫn, nhiều tài sản, tài sản đặc thù và quyết định pending cũ không tự được duyệt qua.
- 52 liên kết mô tả dài trùng hoàn toàn, giá/diện tích phù hợp được bổ sung như **nghi trùng**, không khẳng định cùng tài sản. Tính lại nhóm trên toàn bộ 8.509 ID và giữ cầu nối holdout cũ.
- Raw, training_v1/v2, review cũ và 137 tin test giữ nguyên; không huấn luyện mô hình. Giá đang xét là giá rao.

## Kết quả toàn bộ bộ sưu tập

**2,082 qua lọc; 4,772 cần kiểm tra; 1,655 loại. 1,435 ứng viên train.**

[Mở báo cáo pipeline chung](../collection_pipeline/runs/2026-10-11_26b058753e0d7bc6/README.md). [Xem thay đổi so với đợt trước](collection_changes.csv).

## Chạy lại

Từ `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/fetch_pending_details.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/review_source_details.py
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/filter_all_collected.py
```

Checkpoint bỏ qua ID đã xử lý. Khi bản duyệt đã chốt, kiểm tra hash và giữ nguyên kết quả. Muốn kiểm tra snapshot nguồn mới phải tạo đợt/thư mục mới.
