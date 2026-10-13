# Đánh giá mô hình đã chốt trên test v2

**Đánh giá thử nghiệm trên test đã từng được xem ở v1, chưa phải kiểm chứng độc lập cuối cùng.** 137 ID, nhãn và nhóm test giữ nguyên từng byte. Lựa chọn mô hình được ghi trước khi chấm test: Ridge cho nhà, trung vị đơn giá theo địa bàn cho đất, XGBoost bổ sung phường/số phòng và log giá cho căn hộ. Mô hình đã huấn luyện chỉ trên train v2, chọn/dừng sớm bằng validation v2; không huấn luyện lại khi chấm test.

| Loại | Số test | MAE cơ sở v1 | MAE XGBoost v1 | MAE mô hình chốt v2 | MAPE v2 | R² v2 |
|---|---:|---:|---:|---:|---:|---:|
| Nhà ở | 80 | 3096.1 | 3121.7 | 3093.5 | 33.4% | 0.618 |
| Đất nền | 37 | 2908.6 | 2931.5 | 2969.2 | 55.4% | 0.612 |
| Căn hộ chung cư | 20 | 872.3 | 812.9 | 933.5 | 29.0% | 0.597 |

MAE tính bằng triệu VND, càng thấp càng tốt. Các cột dùng cùng ID và nhãn test. MAPE nhạy với tin giá thấp; R² không phải tỷ lệ dự đoán đúng. Không chọn lại mô hình theo bảng test này.

## Tệp dùng cho đồ án

- `test_comparison.csv`: bảng chỉ số cho v1 cơ sở, v1 XGBoost và v2 đã chọn.
- `test_predictions.csv`: đối chiếu từng ID để tái lập chỉ số, không phải hàng chờ sửa nhãn theo dự đoán.
- `metrics.json`: kết quả, phiên bản môi trường và giới hạn.
- `model_bundle/selection.json`: mô hình được chọn, schema, hash; baseline JSON và XGBoost JSON tương ứng.
- `model_bundle/predict.py`, `requirements.txt`: suy luận độc lập với các script dữ liệu dự án.
- `manifest.json`: hash đầu vào/đầu ra để kiểm tra tái lập. Các CSV dữ liệu ở [training_v2](../training_v2/README.md).

## Chạy dự đoán

Từ `F:\SmartProp`:

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/predict_model_v2.py --category "Căn hộ chung cư" --area-sqm 65 --location "Sơn Trà" --ward "Phường An Hải Bắc" --rooms 2
```

Đầu ra là giá rao dự đoán (triệu VND và VND). `location` phải khớp nhãn địa bàn đã lưu; địa bàn chưa thấy dùng mức chung/không có chỉ báo địa bàn. Phường và số phòng có thể bỏ trống nếu không có dữ liệu. Không nhập giá rao hoặc đơn giá vào đặc trưng.

Để dùng bản độc lập trong thư mục model_bundle, chạy `predict.py --bundle .` cùng các tham số trên. Những mô hình này chưa phù hợp để coi là định giá giao dịch đã xác minh.

Chạy lại `python ai-services/app/data/evaluate_selected_v2.py`: kiểm tra hash của kết quả đã chốt, không chấm lại hoặc đổi lựa chọn.
