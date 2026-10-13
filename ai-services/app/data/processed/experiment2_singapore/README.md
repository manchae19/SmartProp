# Thí nghiệm 2: bổ sung dữ liệu Singapore cho dự đoán giá căn hộ Đà Nẵng

## Kết quả

Chưa có bằng chứng dữ liệu Singapore giúp cải thiện mô hình trong cấu hình này.

| Mô hình | MAE test (triệu VNĐ) | Median APE | R² |
|---|---:|---:|---:|
| Ridge chỉ Đà Nẵng | 878,407 | 21,340% | 0,5951 |
| Ridge Đà Nẵng + Singapore | 878,374 | 21,366% | 0,5949 |
| Median giá/m² địa phương (baseline đã có) | 895,617 | 13,651% | 0,5584 |

MAE ridge giảm khoảng **0,033 triệu đồng (33 nghìn đồng), tương đương 0,0038%**.
Khoảng bootstrap ghép cặp 95% của chênh lệch MAE (bổ sung trừ địa phương) là
**[-0,579; +0,604] triệu đồng**, có chứa 0. Median APE và R² không cải thiện.
MAE validation tăng nhẹ: 1.498,360 → 1.498,947 triệu đồng. Nếu chọn giữa hai
phương án bằng validation, sẽ giữ mô hình chỉ Đà Nẵng.
Baseline median địa phương vẫn là mô hình được chọn theo validation trong lần chạy trước;
không đổi lựa chọn đó chỉ vì ridge có MAE tốt hơn trên test.

## Dữ liệu và thiết kế

- Giữ nguyên `processed/smartprop_review/baseline_inputs.csv`: SHA256
  `af08029d0cfc9e757c951ab7f61b61b2798a28ca84ef1945e4b8270dcf18565f`.
- Chỉ dùng **296 căn hộ** đã lọc: train 241, validation 29, test 26. Không dùng toàn bộ
  tin nhà/đất hoặc toàn bộ dữ liệu thô của dự án cho thí nghiệm căn hộ.
- Nhóm nghi trùng bất động sản không giao nhau giữa các tập. Giữ nguyên test IDs;
  hash danh sách ID trong `metrics.json`. Dữ liệu Singapore chỉ đưa vào train.
- Nguồn chính thức: [HDB resale flat prices từ 2017](https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view),
  tải bằng [API data.gov.sg](https://guide.data.gov.sg/developer-guide/dataset-apis/download-dataset).
- Snapshot gồm 242.454 dòng. Chọn giao dịch tháng **04–09/2026**; loại 5 dòng giống hệt,
  còn 13.591 dòng hợp lệ. Chọn 3.000 dòng theo thứ tự hash SHA256 để tái lập,
  giới hạn khối lượng và tránh chọn mẫu theo mức giá. Dòng giống hệt không có nghĩa
  chắc chắn cùng một căn hộ vì nguồn không cung cấp ID giao dịch/căn hộ duy nhất.
- Tỷ giá snapshot [Vietcombank XML](https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx),
  thời điểm ghi trong nguồn `10/11/2026 6:29:14 PM`: trung bình mua chuyển khoản
  19.900,51 và bán 20.579,47 = **20.239,99 VNĐ/SGD**.
  `price_million = resale_price_SGD × 20239.99 / 1e6`.
  Đây là quy đổi bằng một snapshot, không phải tỷ giá lịch sử từng giao dịch.
- Cùng họ mô hình log-price ridge alpha=1: diện tích log chuẩn hóa từ train Đà Nẵng,
  hệ số quận cũ Đà Nẵng; nhánh Singapore có intercept riêng không phạt và hệ số town riêng.
  Chỉ chia sẻ hệ số diện tích. Không coi town Singapore là quận tương đương Đà Nẵng.
  Quy đổi tiền tệ được lưu đầy đủ; do intercept Singapore độc lập, nhân toàn bộ giá Singapore
  với một hằng số chỉ đổi intercept, không đổi dự đoán Đà Nẵng.
- Tổng trọng số Singapore / tổng trọng số Đà Nẵng thử 0,1; 0,25; 0,5; 1.
  Chọn **1** theo MAE validation Đà Nẵng, sau đó mới đánh giá test. Mỗi dòng Singapore
  nhận trọng số 241/3000; không để 3.000 dòng lấn át 241 dòng địa phương theo số lượng.
- Bootstrap 10.000 lần, seed 20261011, ghép cặp sai số trên cùng 26 dòng test;
  chưa bao gồm bất định do huấn luyện, chọn tham số và thu thập dữ liệu.

## Giới hạn và diễn giải

HDB là giá giao dịch căn hộ nhà ở công Singapore; dữ liệu Đà Nẵng là giá rao bán.
Khác biệt quyền sử dụng, thời hạn thuê, điều kiện giao dịch, đặc điểm nhà và thị trường
chưa được mô hình hóa. Diện tích HDB là floor area; diện tích rao tại Việt Nam chưa
được kiểm chứng cùng định nghĩa. Vì vậy đây là thử nghiệm chuyển giao quan hệ diện tích–giá,
không phải kết luận hai thị trường có thể định giá thay thế nhau.

Test chỉ có 26 căn hộ, đã từng được kiểm tra trong phân tích baseline; đây là đánh giá
khám phá trên holdout cố định, chưa phải benchmark độc lập cuối cùng. Không loại dòng
giá bất thường để làm đẹp kết quả. MAPE cao và nhạy với tin có giá rao rất thấp.
Không suy rộng kết quả này sang mọi mô hình hoặc mọi nguồn nước ngoài.

Ưu tiên tiếp theo: kiểm tra nhãn giá và bổ sung căn hộ Đà Nẵng, nhất là khu vực thiếu dữ liệu;
thiết lập tập test mới theo thời gian trước khi kết luận lợi ích của dữ liệu nước ngoài.
Giữ dữ liệu Singapore riêng để phục vụ đối chiếu mô tả; chưa ghép vào pipeline huấn luyện chính.

## Chạy lại

Từ `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/download_singapore_hdb.py
.\ai-services\.venv\Scripts\python.exe ai-services/app/data/experiment2_singapore.py
.\ai-services\.venv\Scripts\python.exe -m unittest discover -s ai-services/app/data -p test_experiment2_singapore.py
```

Để tái lập đúng snapshot hiện tại, chỉ chạy lệnh thí nghiệm và kiểm thử; lệnh tải có thể
làm mới tỷ giá. Dữ liệu thô HDB, XML tỷ giá và provenance nằm ở `data_raw/singapore_hdb`.
Kết quả số đầy đủ: `metrics.json`; tham số: `models.json`; dự đoán holdout:
`holdout_predictions.csv`; mẫu Singapore đã chuẩn hóa: `singapore_train.csv`.
