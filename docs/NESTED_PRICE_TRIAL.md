# Thử cách học giá với nested CV

[Issue #18](https://github.com/manchae19/SmartProp/issues/18) chốt trước khi
fit dữ liệu thật. Bộ train sạch có 2.213 nhóm; [đợt rà nguồn](PROPERTY_SOURCE_ADJUDICATION.md)
chưa phát hành thêm dữ liệu train. Đợt này dùng đúng nhãn/sidecar cũ để thử
ba cách học, không ghép mô tả hiện tại vào giá quá khứ.

Protocol: [NESTED_PRICE_TRIAL_PROTOCOL.md](../ai-services/app/data/NESTED_PRICE_TRIAL_PROTOCOL.md).
Chỉ chọn arm bằng hai inner folds; ba outer folds dùng để đánh giá thuật
toán chọn arm. Vocabulary fit-only, 300 rounds, params cố định, CPU 4 thread.
299 validation, mọi pilot/reserved/consumed cohort và 5 nhóm mới giữ riêng
không được dùng để fit, chọn hoặc chấm trong đợt này.

Các arm là log tổng giá/squared loss (control), log giá/m²/squared loss và
log tổng giá/absolute loss. Đơn giá là **target**, không được thêm vào X.
Thêm baseline median đơn giá theo địa bàn học trên outer train để biết
XGBoost hơn một phép ước tính đơn giản hay chưa.

Cổng đề cử: MAE gộp giảm ít nhất 5% và tốt hơn baseline median đơn giản;
từng loại không tăng MAE quá 5%, tỷ lệ
trong20% không giảm quá 5 điểm phần trăm, ít nhất 2/3 outer folds mỗi loại
không tệ hơn control. Candidate cuối chỉ được fit nếu qua toàn cổng; không
tự thay v6. Nếu không qua, giữ v6 và không mở thêm search theo điểm outer.

Đây là kiểm chứng nội bộ trên train đã được nghiên cứu, không phải benchmark
độc lập hoặc chứng minh giá giao dịch. Bảng ưu tiên thu thập dựa trên train,
không nhìn lỗi trên 5 nhóm mới. Việc thu sau phải có plan/giới hạn nguồn mới.

```powershell
# Tại gốc SmartProp, sau khi code/protocol được kiểm tra
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/train_nested_price_trial.py

# Tải lại model, tính lại selection/OOF/metrics, không fit
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/train_nested_price_trial.py --verify
```

Code lưu run bất biến theo SHA input/protocol/versions tại
`ai-services/app/data/processed/nested_price_trial/`. Dữ liệu/model nghiên
cứu giữ cục bộ; file tổng hợp kết quả được cập nhật sau lần chạy đã khóa.

## Kết quả thật — 29/10/2026

Run `60cdc75ec58eb1cd`: **70 model**, replay **16.766 prediction** của các
model, **6.639 dòng OOF** (2.213 nhóm × 3 phương pháp). Mỗi nhóm chỉ thuộc
một outer fold; ba phương pháp không tạo thêm mẫu độc lập. Tất cả giữ
300 rounds; không mở thêm arm hoặc đổi params sau điểm outer.

MAE tính theo triệu VND, chỉ kiểm chứng nội bộ trên train:

| Loại | Control | Chọn arm trong inner | Median đơn giá địa bàn | Thay đổi MAE so control |
|---|---:|---:|---:|---:|
| Nhà ở, 1.410 nhóm | 2.601,47 | 2.620,20 | 3.095,77 | Tăng 0,72% |
| Đất nền, 626 nhóm | 3.424,17 | 3.398,24 | 3.598,57 | Giảm 0,76% |
| Căn hộ, 177 nhóm | 1.151,54 | 1.112,68 | 1.162,63 | Giảm 3,37% |
| **Gộp 2.213 nhóm** | **2.718,22** | **2.719,72** | **3.083,38** | **Tăng 0,05%** |

Tỷ lệ sai số trong20% tăng từ 42,75% lên 43,56% khi gộp; MAPE lại tăng từ
40,58% lên 41,07%. Căn hộ giảm MAE nhưng tỷ lệ trong20% giảm từ 55,37% xuống
54,24%. Không lấy riêng một metric tốt để gọi thuật toán mới tốt hơn.

Inner chọn log đơn giá 6/9 lần, control 2/9, absolute loss 1/9. So với control,
thuật toán chọn arm không tệ hơn về MAE ở 2/3 fold nhà, 3/3 fold đất, 2/3 fold
căn hộ. MAE gộp tốt hơn median đơn giản khoảng 11,79%, nhưng **không đạt mức
cải thiện 5% so control**. Cổng đề cử không đạt; **0 final candidate**, giữ v6.
Các control ở đây là model tái fit trong outer train, không phải điểm của
release v6 trên 299 validation hoặc benchmark mới.

Thử nghiệm cho thấy việc đổi target/loss trong phạm vi đã chốt chưa giải
quyết chất lượng định giá. Kết quả không chứng minh mọi phương pháp khác
đều vô ích; đợt này dừng tìm cấu hình theo đúng protocol, chuyển trọng tâm
sang bằng chứng/độ phủ và giới hạn sử dụng.

## Thu dữ liệu gì tiếp?

`collection_priorities.csv` chỉ dùng OOF của **train** để ưu tiên nghiên cứu.
Có 56 cặp loại/địa bàn; 28 cặp có dưới 10 mẫu, tổng 61 nhóm. Tên địa bàn
nguồn cũ/mới giữ tách riêng, không cộng theo tên gần giống hoặc suy ranh giới.
Không dùng lỗi của 5 nhóm mới hoặc cohort đã tiêu thụ để chọn nơi thu.

| Nhóm cần chú ý | Bằng chứng từ train | Ưu tiên khi có plan thu mới |
|---|---|---|
| Căn hộ Liên Chiểu cũ / địa bàn `new_unit:lien chieu` / Thanh Khê | Lần lượt 4 / 3 / 6 nhóm | Một căn có giá tổng/diện tích rõ; dự án/tòa/tầng căn hộ và nguồn ngày tháng |
| Nhà Hòa Vang | 15 nhóm, median APE nội bộ 42,92% | Loại nhà, số tầng hiện hữu, lối vào/độ rộng kiệt có lời rao rõ |
| Đất Điện Bàn Đông theo nhãn nguồn mở rộng | 10 nhóm, median APE nội bộ 76,78% | Vị trí/địa bàn rõ, loại đất, pháp lý lời khai, đường vào, tổng giá |
| Đất Hòa Xuân mở rộng / Liên Chiểu mở rộng | 19 / 23 nhóm, median APE 48,96% / 38,21% | Phân khúc tương đồng; không ghép thành cùng quận/phường cũ |
| Các địa bàn mở rộng chỉ 1–5 nhóm | Sai số nội bộ dao động rất lớn | Chưa thể đánh giá ổn định; ưu tiên tăng độ phủ có nguồn và cảnh báo trong demo |

Cột `floors_claim` và `house_subtype_claim` của v6 chỉ áp dụng nhà ở;
`access_claim` không áp dụng căn hộ, `rooms_completed` không áp dụng đất.
Không diễn giải ô rỗng của trường không áp dụng thành thiếu dữ liệu cần điền.
Tầng căn hộ là trường nghiên cứu riêng, chưa có trong feature contract v6.

Ưu tiên là tin một tài sản với giá/diện tích và đặc trưng cùng phản hồi.
198 snapshot thiếu corroboration trong đợt trước không thể được sửa bằng
điền giả hoặc lặp lại bộ lọc. Đợt này **không cào thêm**; lô sau cần baseline
ID gồm toàn bộ các lô đã có, quota theo phân khúc, giới hạn nguồn và nhóm
kiểm chứng được khóa trước fit. Dữ liệu thu có mục tiêu cũng phải ghi rõ thiên
lệch mẫu; không gọi là đại diện toàn thị trường.

## Kiểm chứng và review

- **154 unit test đạt**, gồm 138 trước và 16 mới. Fixture có cả nhánh không
  đề cử và nhánh final 27 model chọn arm + 3 model cuối bằng gate fixture;
  gate thật được kiểm tra riêng. Verifier được test cấm mọi lệnh fit và phát
  hiện metric bị sửa ngay cả khi manifest output hash được cập nhật.
- Sau chạy thật, verifier tải lại đủ 70 model, tính lại membership/schema/
  selection/predictions/metrics/gate; đạt. Giữ 13 input và 38 protected file,
  không chấm 299 validation/pilot/5 nhóm mới, không sửa ledger hoặc model v6.
- Source manifest SHA:
  `594e162297211e9d573219220d8f78ebe7635ae3fbd03b3bc717bb963d2037bc`.

## Standards

0 hard violation. Heuristic P3 về lặp ngưỡng protocol/cổng thực thi đã sửa
để dùng `PROTOCOL['final_gate']`; reviewer kiểm tra lại đạt. Không chỉnh các
module đặc trưng/encoder lịch sử đã khóa.

Reviewer phát hiện lỗi chức năng P2 ngoài axis Standards: ngắt lúc ghi
metadata lock có thể để khóa của chính tiến trình lại. Đã bao cả creation
trong cleanup theo inode/dev/token; regression kiểm ngắt ghi và không xóa
lock người khác, reviewer xác nhận đạt trước first fit thật.

## Spec

Không có P1/P2 còn mở trong phạm vi review. Reviewer đối chiếu nested split,
vocabulary, inverse target, baseline, cổng đã chốt trước điểm số, conditional
final fit và replay không fit. Góp ý bổ sung fixture final-model path sau
cổng median mới đã thực hiện và đạt. Bổ sung cổng hơn median/CPU4 được ghi
trong issue và commit trước first fit thật. Không thay cấu hình theo kết quả.

Phần cải thiện demo tiếp theo là [cảnh báo độ phủ dữ liệu](VALUATION_DATA_SUPPORT.md),
không thay model/giá v6 và không lấy nghiên cứu này làm confidence cho người dùng.
