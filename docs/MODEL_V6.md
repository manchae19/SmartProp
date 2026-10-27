# Model v6 đang dùng trong demo

Run cố định `b4b1339d3f35857e`, cấu hình `all`. Bundle trong [ai-services/artifacts/v6](../ai-services/artifacts/v6/) là bản sao byte nguyên vẹn của model/schema đã kiểm chứng; không huấn luyện lại khi đóng gói GitHub.

| Nhóm | Train | Validation phát triển |
|---|---:|---:|
| Nhà ở | 1.411 | 153 |
| Đất nền | 626 | 115 |
| Căn hộ | 177 | 31 |
| Tổng | 2.214 | 299 |

Feature: diện tích, địa bàn/phường, số phòng ngủ, tầng nhà, mặt tiền/kiệt và subtype nhà. Các giá trị thiếu giữ theo schema học từ train; nguyên văn mô tả, giá/đơn giá, ID và nguồn không vào X. Chưa có tọa độ tài sản được xác minh hoặc khoảng cách tới tiện ích.

[Metrics huấn luyện đã lưu](../ai-services/artifacts/v6/metrics.json): v6/all có MAE **2.457,33 triệu VND**, MAPE **36,13%**, tỷ lệ sai số ≤20% **49,16%** trên 299 validation được dùng nhiều lần để phát triển/chọn cấu hình. Các trường trạng thái trong metrics/manifest ghi thời điểm tạo artifact, không mô tả mọi công việc về sau.

## Pilot lưu trữ đã chấm một lần

| Loại | Số tin | MAE (triệu VND) | MAPE | Sai số ≤20% |
|---|---:|---:|---:|---:|
| Nhà ở | 78 | 1.647,74 | 36,79% | 60,26% |
| Đất nền | 46 | 2.606,82 | 38,75% | 52,17% |
| Căn hộ | 8 | 760,32 | 10,20% | 87,50% |
| Tổng | 132 | 1.928,18 | 35,86% | 59,09% |

Có 16/132 tin sai hơn 50%. Căn hộ chỉ có 8 mẫu kiểm chứng. Pilot là dữ liệu lưu trữ đã sàng lọc trước khi chấm, không xác nhận mọi trùng tài sản ẩn hoặc sử dụng bên ngoài repo; chưa phải đánh giá theo thời gian tương lai hoặc theo giá giao dịch.

132 tin đã được đánh giá, không coi là test mới để chấm/tuning lại. Kho chi tiết, registry exposure và báo cáo nguồn vẫn ở `ai-services/app/data/processed/` cục bộ, không đưa vào bản GitHub gọn. [Báo cáo pilot lịch sử](../ai-services/app/data/V6_HOLDOUT_PILOT.md).

Kết quả phục vụ demo **giá rao ước tính**. Cần kiểm chứng trên dữ liệu mới trước khi kết luận rộng hơn về chất lượng định giá.

[Phân tích sai số ngày 27/10](MODEL_V6_DIAGNOSTICS.md) đối chiếu đúng 299 dự đoán đã lưu theo loại, địa bàn, khoảng giá và thiếu đặc trưng; kèm kế hoạch bổ sung dựa trên độ phủ train. Không huấn luyện hoặc chấm lại pilot trong bước này.
