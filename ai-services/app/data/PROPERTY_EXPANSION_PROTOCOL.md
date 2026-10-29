# Bổ sung dữ liệu và đường cong học — 29/10/2026

Issue#14. Giữ nguyên mọi raw/cohort/nhãn/model/ledger cũ. Không dùng kết quả
24 nhóm đã chấm hoặc299 validation để chọn dữ liệu hay cấu hình trong bước này.

## Thu nguồn

- Đọc lại tối đa11 CafeLand và143 Nhadat24h train căn hộ còn thiếu mô tả.
  Mỗi phản hồi giữ HTML, URL yêu cầu/đáp ứng, timestampUTC thực và giá/diện tích
  hiện tại; nhãn cũ chỉ để đối chiếu, không ghi đè hoặc dùng thay giá hiện tại.
- Thu thử tối đa60 ID CafeLand mới so với8.509 lịch sử +222 ID đợt trước,
  tối đa16 trang từ checkpoint18 của topup40. Tối đa20 tin/locality nguồn;
  địa bàn nguồn cũ/mới không tự ánh xạ thành cùng ranh giới. Không bảo đảm
  đủ60, tài sản độc lập hoặc tính đại diện thị trường.
- Robots, >=3giây giữa yêu cầu cùng nguồn, timeout25s, phản hồi giới hạn10MB.
  Chỉ HTTPS đúng host, redirect cùng ID và robots cho phép.403/429/challenge/
  lỗi mạng thì dừng nguồn, không thử đường vòng.404/410 không có nghĩa đã bán.
- Snapshot và metadata được công bố nguyên tử, checkpoint theo bản ghi đã lưu;
  chạy lại batch hoàn tất không gọi mạng. File tạm không thành evidence cuối.
- Giá và đặc trưng lấy từ cùng phản hồi, ngày đăng/cập nhật giữ metadata riêng.
  Đặc trưng không rõ, phủ định chưa phân giải, nhiều tài sản, mâu thuẫn hoặc
  tọa độ chưa xác minh giữ thiếu/cần review. Giấy tờ chỉ là lời khai.
- So nhóm với lịch sử và222 tin trước; ID mới không tự là tài sản mới. Tất cả
  dữ liệu bổ sung ở lớp nghiên cứu DO_NOT_TRAIN, chưa ghép vào train/encoder/
  early stopping hoặc chấm mô hình. Lô mới chưa dùng để chọn cấu hình.

## Chẩn đoán learning curve

Chỉ dùng2.213 train cũ và sidecar v6/all tương ứng. Chia3fold theo hash group,
train subset lồng nhau25/50/75/100% theo hash ID, không theo giá. Vocab/schema
chỉ fit trên subsettrain; mỗi outerfold giữ nguyên giữa các mức dữ liệu.
Params v3/v6 cố định, CPU4thread, seed42,300rounds, log target. Không earlystop,
không thay params theo điểmfold. Không đọc giá/feature của299 validation hoặc
pilot để fit/chấm/chọn mô hình; chỉ kiểm hash bảo vệ những file này.

Lưu cả MAE trên subsettrain và outerfold theo triệuVND, dự đoán và model/schema
để replay. Chênh lệch trên3fold là chẩn đoán train hiện có, không phải benchmark
độc lập hoặc bảo đảm hiệu quả khi thêm nguồn/dữ liệu mới. Không thay v6 trong API.
Giá rao theo một tháng chưa đủ dự báo xu hướng; tọa độ/POI thiếu giữmissing.
