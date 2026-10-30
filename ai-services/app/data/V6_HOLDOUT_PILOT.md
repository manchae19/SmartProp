# Pilot kiểm chứng v6 — 17/10/2026

Đã sàng lọc **133 ứng viên** theo luật lưu trước khi chấm, giữ **132 tin** và chấm một lần bằng model/schema/extractor v6 `all` đã khóa. Một tin đất giữ chờ do nghi trùng nội dung dài qua hai nhóm. Không huấn luyện/tuning, không đổi nhãn hoặc các tập train/validation, không tự thay model ứng dụng.

[Kết quả](processed/v6_holdout_pilot/evaluation/runs/30daf763091ace37/README.md) · [Metrics](processed/v6_holdout_pilot/evaluation/runs/30daf763091ace37/metrics.json) · [Kiểm chứng độc lập](processed/v6_holdout_pilot/evaluation/verification.json) · [Sàng lọc trước chấm](processed/v6_holdout_pilot/screening/runs/2e559a31023367eb/README.md).

| Loại | Số tin | MAE (triệu VND) | MAPE | Sai số ≤20% |
|---|---:|---:|---:|---:|
| Nhà ở | 78 | 1.647,74 | 36,79% | 60,26% |
| Đất nền | 46 | 2.606,82 | 38,75% | 52,17% |
| Căn hộ | 8 | 760,32 | 10,20% | 87,50% |
| **Tổng** | **132** | **1.928,18** | **35,86%** | **59,09%** |

Sai số phần trăm trung vị toàn pilot **15,36%**; có **16/132 tin sai hơn 50%**. MAE đất vẫn lớn, căn hộ chỉ có 8 tin nên chưa đủ để kết luận ổn định theo phân khúc. Giá mục tiêu là giá rao, không phải giá giao dịch độc lập.

## Cách giữ phép đánh giá có ý nghĩa

- Kiểm tra lịch sử trước đó: 684 tin dự phòng gồm 539 ID có dấu vết train/validation hoặc dự đoán, 12 ID liên quan qua nhóm và 133 ứng viên không tìm thấy dấu vết. Chỉ nhóm cuối được đưa vào sàng lọc pilot.
- Luật sàng lọc cố định xét phạm vi nhà/đất ở/căn hộ đơn lẻ, nhiều tài sản, giá khởi điểm/trả trước và nghi trùng. So mô tả dài hoặc tiêu đề dài đã che giá giữa các nhóm; không dùng giá số hay residual để chọn cohort. Tin `cafeland:3149024` giữ chờ vì mô tả khớp `cafeland:3145188` ở nhóm khác. Đây là dấu hiệu nghi trùng, không phải xác minh tài sản vật lý.
- Cohort 132 ID, policy, model/schema/extractor được lưu hash trước khi dự đoán. Các giá trị nhãn dùng nguyên snapshot. Mọi outcome trong cohort được giữ, kể cả sai số cao.
- Dùng đúng bộ trích v6 và schema học từ 2.214 train; không học vocabulary từ pilot. 71 HTML mô tả thực sự dùng trong suy luận được kiểm tra SHA-256; các tin khác dùng tiêu đề/trường cấu trúc và missing theo quy tắc cũ. Bước sàng lọc trước đó kiểm tra 72 HTML của ứng viên có nguồn khớp ID.
- 9 kiểm thử luật sàng lọc đạt. Kiểm chứng độc lập đã phát lại quyết định sàng lọc/liên kết nghi trùng, đối chiếu nhãn, feature và 132 dự đoán; tải lại 3 model v6, so toàn bộ metric/phân nhóm. Model v3/v4/v5/v6 và dataset gốc giữ nguyên SHA-256.

**Từ nay 132 tin đã được chấm.** [Registry đã đánh giá](processed/v6_holdout_pilot/evaluation/runs/30daf763091ace37/evaluation_exposure_registry.csv) và file dự đoán được lưu để các đợt audit sau nhận diện exposure. 684 tin vẫn giữ reservation cũ; không chuyển pilot vào train. Con số 133 “chưa thấy dùng” trong snapshot audit là trạng thái **trước** lần chấm này, không còn là danh sách test mới chưa chấm. Các trường `actually_scored: 0` trong policy/cohort sàng lọc ghi thời điểm khóa trước chấm; trạng thái hiện tại xem `evaluation/evaluation_state.json` và metrics.

## Giới hạn

Đây là **pilot trên dữ liệu lưu trữ**, chưa tìm thấy model-use trước đó trong artifact cục bộ đã kiểm kê. Không xác nhận được mọi sử dụng bên ngoài repo, mọi trùng tài sản ẩn hoặc nhãn sai chưa biết. Dữ liệu đã qua lọc chung toàn collection; các tin không có mô tả được kiểm tra hạn chế theo tiêu đề. Đây không phải phép đánh giá theo thời gian tương lai hoặc chứng nhận giá thị trường hiện tại.

299 validation và 132 pilot có ID/phân bố khác nhau; không gọi MAE pilot thấp hơn là cải thiện model trên cùng một tập. Nếu dùng pilot để sửa luật/feature/tuning, phải xem nó là dữ liệu phát triển và cần tập kiểm chứng mới. Không chọn model khác sau khi nhìn pilot này.

Kết quả cung cấp bằng chứng ban đầu cho bản demo đồ án. Bước tiếp theo hợp lý là xây API dự đoán với đúng extractor/schema v6 và thể hiện giá là tham khảo; kiểm chứng theo thời gian hoặc bổ sung căn hộ mới có mục tiêu trước các kết luận rộng hơn. Chưa tự tích hợp vào API trong đợt đánh giá này.

## Xem lại và kiểm chứng

```powershell
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/evaluate_v6_holdout_pilot.py
./ai-services/.venv/Scripts/python.exe -X utf8 ai-services/app/data/verify_v6_holdout_pilot.py
```

Khi đã có `evaluation/latest.json`, lệnh đánh giá chỉ kiểm tra hash/kết quả đã lưu, không tính một lượt dự đoán mới. Verifier có tải model để phát lại dự đoán và đối chiếu artifact, không tạo thí nghiệm hoặc chọn lại model. Không chạy lại bước sàng lọc đã khóa để thay cohort sau khi thấy điểm. Lần kiểm tra lịch sử tiếp theo cần phiên bản audit mới vì các artifact chấm pilot đã bổ sung vào kho lịch sử.
