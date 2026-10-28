# Quan sát giá rao v1

Ngày chốt: **28/10/2026**, issue [#11](https://github.com/manchae19/SmartProp/issues/11).

## Phạm vi

Kho nghiên cứu cục bộ, SQLite chuẩn thư viện Python, tách khỏi database tài khoản
và lịch sử định giá. Chỉ tiếp nhận giá rao CafeLand có HTML nguồn và checksum.
Không tiếp nhận giá AI, tự tạo dữ liệu các tháng trước, thay model v6 hoặc đổi
registry/train/validation. Các tin mới hiện vẫn thuộc cohort đã bảo vệ.

## Định danh và thời gian

- Master: một `source + source_listing_id`. Quan sát: nhiều thời điểm UTC có múi
  giờ, mỗi thời điểm giữ giá/diện tích/trạng thái, SHA HTML và provenance JSON.
- Ngày nguồn giữ riêng; có thể là đăng/cập nhật/đăng lại. Nhập cache dùng đúng
  `collected_at` gốc, không dùng thời điểm nhập hoặc thời gian sửa file.
- Nhập lại bằng chứng giống nhau không thêm dòng. Cùng ID/thời điểm nhưng nội
  dung hoặc cách diễn giải khác bị từ chối; không ghi đè dữ liệu cũ.
- SQLite cấm UPDATE/DELETE trên hai bảng; verifier kiểm payload, SHA, HTML và
  kết quả phân tích lại. Đây là bảo vệ vận hành, không thay thế backup hoặc
  ngăn quản trị viên sửa trực tiếp file database.

## Nguồn ban đầu và quan sát lại

- Replay 220 cache CafeLand của ba batch pilot100/extension80/topup40, đối chiếu
  quyết định cố định `c458ee98726ea981`; 2 tin Nhadat24h chưa có adapter nên chưa
  nhập. 8.509 tin lịch sử được rà độ phủ bằng bộ train đã chuẩn bị; chưa nhập
  thành lịch sử giá có bằng chứng HTML trong kho mới.
- Watchlist: lấy tối đa 20 ID đầu theo `record_key` trong 24 nhóm qua review,
  không theo giá hay sai số model. Mỗi `run-id` lưu plan/checkpoint từ quan sát
  đã commit; chạy lại cùng run-id tiếp tục phần chưa lưu, hoàn tất thì không
  gọi mạng. Dùng run-id mới cho đợt quan sát tiếp theo.
- Tái sử dụng client hiện có: robots.txt, tối thiểu 3 giây giữa yêu cầu, timeout,
  giới hạn kích thước, chỉ redirect HTTPS cùng nguồn/cùng ID được robots cho
  phép. 403/429/challenge/lỗi mạng thì dừng, không vượt chặn.
- Mỗi phản hồi chi tiết được ghi bằng chứng và commit ngay. Mất kết nối trước
  khi nhận phản hồi không tạo giá. 404/410 là `not_found`, không phải `sold`;
  HTTP 200 sai cấu trúc là `parse_error`. Không mang giá cũ hoặc giá 0 vào lỗi.
- Giá thay đổi giữa card cũ và detail mới là điều cần theo dõi. Bỏ riêng các
  cờ so sánh card cũ (`listing_detail_*`), nhưng vẫn kiểm JSON-LD, cấu trúc,
  lời rao, phạm vi, loại tài sản, diện tích và địa bàn của detail mới. Nghi ID
  tái sử dụng/đổi tài sản thì cách ly, không nối thành cặp giá đáng tin.
- Chất lượng tiếp tục dùng quy tắc review căn hộ hiện hành, gồm cửa sổ ngày
  nguồn 183 ngày; đây là bộ theo dõi thử nghiệm bảo thủ, có thiên lệch chọn mẫu.
  Chưa tự mở rộng phạm vi hoặc xác nhận giấy phép/độ chính xác thực địa từ robots.

## Thống kê và cổng dữ liệu

- Tháng theo UTC+7. Chọn quan sát mới nhất của mỗi ID trong tháng **trước khi**
  lọc chất lượng để không giấu phản hồi lỗi bằng giá cũ. Không forward-fill.
- Gom nhóm ứng viên; nhóm có thành viên lỗi/chưa rõ, lệch giá >5%, diện tích
  >1% hoặc khác địa bàn/loại thì không đếm. Một nhóm tối đa một mẫu/tháng.
- Thống kê theo địa bàn × dải diện tích cố định: dưới20, 20–49, 50–79, 80–119,
  từ120 m². Giá là triệu VND tổng và triệu VND/m². Trung vị là mô tả mẫu,
  **không phải chỉ số điều chỉnh cơ cấu hay bằng chứng giá thị trường tăng**.
- Chỉ tính trung vị % thay đổi khi có ít nhất 10 cặp cùng nhóm, cùng ô, diện
  tích lệch không quá1%, trong hai tháng kề nhau. Đây vẫn là cặp tin rao nghi
  cùng tài sản, chịu thiên lệch tin sống lâu; không phải repeat-sales index.
- Quy ước kế hoạch: ít nhất 18 tháng liên tiếp có ≥10 nhóm/ô mới cân nhắc thiết
  kế backtest. Đây không phải điều kiện bảo đảm mô hình tốt. Chưa có thuật toán
  dự báo, số dự báo hoặc khoảng tin cậy trong phiên bản này.
- Backtest tương lai phải theo thời gian, nhiều mốc cắt, so với giá trị gần nhất
  và giữ dữ liệu kiểm chứng mới. Không dùng 24 nhóm đã chấm để chọn cấu hình.

## Hướng cải thiện định giá

`valuation_readiness.csv` đọc bộ sạch 2.213 train/299 validation, thống kê phần
thiếu của đặc trưng hiện có và tọa độ. `collection_priorities.csv` chỉ dùng số
nhóm **train** theo loại × địa bàn; mốc10 là gợi ý lấy mẫu, không cam kết cải
thiện. Không dùng pilot hoặc lỗi validation để tự đổi tập kiểm chứng.

Thu bổ sung có nguồn: độ rộng kiệt/ô tô vào; loại đất, pháp lý, hiện trạng;
dự án/tòa căn hộ, tầng, năm bàn giao, diện tích sử dụng, nội thất và thời hạn
sở hữu. Không coi số tầng nhà là tầng căn hộ. Chưa có tọa độ tài sản được xác
minh/quyền dùng ML và snapshot POI phù hợp thì giữ feature khoảng cách missing.

## Chạy và kiểm chứng

Tại gốc repo, dùng venv và dependencies crawler/review đã có:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py seed
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py observe --run-id 2026-10-28 --count 20
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py verify
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/market_price_pipeline.py report
```

Quan sát tiếp dùng run-id ngày mới, chạy thủ công một đợt/ngày trong thử nghiệm;
chưa đăng ký lịch tự chạy hoặc sử dụng API có phí. Không sửa code/policy trong
lúc collector chạy. Nếu nguồn thay đổi hoặc cần điều chỉnh quy tắc, tạo phiên
bản mới; không lặng lẽ diễn giải lại quan sát cũ. Backup toàn bộ
`data_raw/market_price_observations` khi collector đã dừng, gồm database và
`evidence/`. Không đưa HTML/mô tả nguồn/SQLite lên GitHub.

### Cơ sở phương pháp

- [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html):
  đánh giá theo thứ tự thời gian; không trộn tương lai vào quá khứ.
- [UK HPI methodology](https://www.gov.uk/government/publications/about-the-uk-house-price-index/about-the-uk-house-price-index):
  minh họa việc điều chỉnh khác biệt đặc tính/cơ cấu. UK HPI dùng giao dịch;
  dữ liệu rao SmartProp và thống kê thử nghiệm này không tương đương UK HPI.
