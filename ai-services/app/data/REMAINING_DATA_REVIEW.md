# Lọc tiếp dữ liệu còn lại — 15/10/2026

**Đã có đợt bổ sung mới:** [bộ train hiện tại](TRAINING_DATA_CURRENT.md) gồm **2.214 train**, **299 validation cố định**, **684 eligible giữ riêng**. Đợt mới thêm 18 train từ nhóm 3.605 tin bên dưới; báo cáo trong tài liệu này là snapshot trước đợt bổ sung, được giữ nguyên để truy vết. [Báo cáo mới](processed/remaining_diversity_review/runs/1d45c8941172a52d/README.md).

[Báo cáo hiện tại](processed/remaining_3752_review/README.md) dùng đầu vào là 3.752 ID còn chờ sau đợt bỏ chặn ngày đăng. Không bỏ qua dữ liệu còn lại: đã đối chiếu toàn bộ ID với quyết định nguồn, nội dung đã lưu và nhóm trùng hiện có.

| Kết quả đợt này | Số ID |
|---|---:|
| Eligible bổ sung | 113 |
| Giữ ngoài: 33 bản trùng nhóm và 1 nguyên tòa cho thuê | 34 |
| Còn cần bằng chứng/giải quyết mâu thuẫn | 3.605 |

Toàn bộ collection hiện có 3.175 eligible, 3.605 needs_review, 1.729 excluded; tổng vẫn là 8.509 ID nguồn duy nhất, không phải số tài sản vật lý được xác minh. Bộ đầu vào mới có **2.196 train**, **299 validation cố định**, **680 eligible giữ riêng**. V3/v4 và mọi số giá/diện tích đã chốt giữ nguyên; chưa huấn luyện model trên bộ 2.196 tin này.

## Nội dung đã xử lý

Hai lỗi được tái hiện bằng kiểm thử trước khi sửa trong module mới: bộ dò cũ đọc “4 tỷ 800” thành phần “4 tỷ”; bộ so diện tích gộp diện tích đất với diện tích sử dụng/xây dựng. Bản mới chỉ diễn giải thành phần triệu ba chữ số đầy đủ và chỉ phân biệt diện tích sử dụng/xây dựng khi có diện tích đất của đúng tin khớp header. Không sửa giá/diện tích số, không điền nhãn từ model, không coi số làm tròn là tự đúng.

13 kiểm thử đã đạt, gồm ví dụ tổng hợp tối thiểu và phát lại 3 tin CafeLand thật. Các kiểm tra chống duyệt nhầm bao gồm giá trả trước, diện tích đất mâu thuẫn, số m² sau giá, địa điểm chưa khớp, footer môi giới, dự định xây/cải tạo và cấu hình nguyên tòa cho thuê. Các parser/dataset cũ đã chốt được giữ nguyên; module `remaining_content_rules.py` và script mới ghi quyết định bổ sung theo phiên bản.

Đã kiểm tra SHA-256 của **277 HTML** cho các quyết định nguồn có thể áp dụng. Danh mục được đối chiếu nội dung tài sản thực tế, có 15 dòng thay đổi danh mục trong bản mới, kèm mã bằng chứng/quote. Đây là xác minh nội dung tin đăng, chưa xác minh giao dịch. Footer “tư vấn bất động sản nhà phố” không chứng minh tài sản là nhà.

## Vì sao còn 3.605 tin

- **1.798 tin Chợ Tốt** chưa có trang chi tiết do nguồn bị chặn trước đó; không phải 1.798 lần yêu cầu riêng đều nhận 403.
- **1.792 tin** có nguồn khớp ID nhưng còn vấn đề nội dung, giá/diện tích, danh mục, giao dịch/địa bàn hoặc nhóm.
- **15 tin** còn thiếu hoặc chưa khớp bằng chứng nguồn khác.

Các mã lý do có thể chồng lặp; ba nhóm độ phủ trên không chồng lặp. Các file `source_access_missing.csv` và `content_or_group_pending.csv` tách nhóm cần thu thập nguồn với nhóm cần xử lý nội dung/nhóm.

Một tin có thể hết cờ phân tích nội dung nhưng vẫn chưa được train: `cafeland:3145191` có diện tích đất 60 m² và diện tích xây dựng 180 m² được phân biệt rõ, nhưng nhóm liên kết còn thành viên chưa đạt nên vẫn chờ. `cafeland:2485950` ghi địa chỉ nguồn Ngũ Hành Sơn/Đà Nẵng nhưng nội dung nói “trung tâm Tam Quan”; giữ chờ để đối chiếu địa điểm, không chỉ bỏ cờ giá rồi duyệt. [Cổng chính thức phường Tam Quan](https://tamquan.gialai.gov.vn/) được lưu làm tham chiếu; không lấy điểm bản đồ từ tên đường để thay bằng chứng tài sản.

## Chạy lại

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/filter_remaining_3752.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_remaining_3752.py
./ai-services/.venv/Scripts/python.exe -X utf8 -m unittest discover -s ai-services/app/data -p test_remaining_content_rules.py -v
```

Cùng đầu vào/mã tạo lại đúng fingerprint và xác minh run đã chốt. Dùng `latest.json` tại `processed/remaining_3752_review` để chọn bản hiện tại; các run trung gian vẫn giữ để truy vết. Không chạy lại pipeline cũ rồi xem các cờ cũ là kết quả của bộ lọc nội dung mới.

[Kiểm chứng độc lập](processed/remaining_3752_review/verification.json) đối chiếu 3.752 kết luận, 8.509 dòng collection, giá/diện tích, các thay đổi danh mục, nhóm/reservation, 299 dòng validation và mọi hàng train v4 cũ; tải lại 6 buffer DMatrix để so với CSV/schema. Model v3/v4 được kiểm tra SHA-256 và không thay đổi.
