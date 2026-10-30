# Lưu mô tả và địa chỉ nguồn — phiên bản 2

`collect_chotot_locations_v2.py` dùng lại bước chuẩn hóa của crawler Chợ Tốt cũ, bổ sung giữ các trường mô tả, địa chỉ, số nhà/số kiệt và chiều rộng khi phản hồi nguồn thực sự cung cấp. Không sửa crawler cũ, CSV/JSONL cũ hoặc model. Không tự dựng mô tả từ tiêu đề hay ghép tên đường/phường thành địa chỉ đầy đủ.

Mỗi trường giữ giá trị nguồn và bằng chứng riêng trong JSONL/checkpoint. Các alias là trường tùy chọn cần đối chiếu phản hồi thực tế, không khẳng định API hiện luôn trả những trường này. `body`/`description` được lưu vào `description_raw`; `full_address`/`address`/`address_raw` vào `address_detail_raw`. Chỉ giữ các trường định trước, không lưu toàn bộ đối tượng tài khoản/người bán. Nội dung mô tả có thể chứa giá/liên hệ, chỉ phục vụ kiểm tra bằng chứng; không đưa nguyên văn vào XGBoost.

Số nhà/kiệt/chiều rộng do nguồn khai báo vẫn chưa xác minh. `location_verified`, `reuse_for_ml_verified`, `model_feature_approved` luôn khởi tạo False. Không định vị tự động và không suy quyền dùng ML từ việc truy cập được một trang.

## Nhập bản lưu có sẵn, không gọi mạng

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/app/data/collect_chotot_locations_v2.py import --input ai-services/app/data/data_raw/chotot_incremental/records.jsonl --normalized-input --output ai-services/app/data/processed/location_capture_v2/archive_import
```

Lần nhập kiểm tra đã tạo 100 ID từ bản lưu cũ, không có mô tả/địa chỉ chi tiết mới: bản cũ không lưu các trường đó. Đây là 100 ID đã có, **không phải 100 tin thu thập mới** và không tự ghép vào training. Trường thiếu vẫn để thiếu. Chạy lại cùng output cập nhật theo ID, không nhân đôi hàng; giữ bằng chứng cũ của các trường mà bản mới không cung cấp.

Với bản xuất API hợp lệ chứa `{"ads": [...]}`, dùng `import --input <file.json>` và bỏ `--normalized-input`. Bằng chứng gồm đường dẫn, SHA-256 và thứ tự phần tử. Không lấy mô tả của ID khác.

## Các lần thu thập sau

Chế độ `collect` dùng cùng public listing feed của crawler cũ, tối đa 5 trang/100 ID mới, mặc định 1 trang/20 ID, cách yêu cầu ít nhất 3 giây. Không gọi API chi tiết thay thế hay giải/vượt chặn trang chi tiết. Không chạy chế độ này trong đợt hiện tại vì nguồn chi tiết đã bị chặn; việc lưu thêm trường không khắc phục quyền truy cập hoặc làm API cung cấp dữ liệu còn thiếu.

Output mặc định riêng tại `data_raw/chotot_locations_v2`; không chỉ định thư mục crawler cũ. Checkpoint v2 lưu dữ liệu và cursor cùng một lần thay thế atomic; CSV/JSONL xuất lại từ checkpoint. Có khóa tránh hai tiến trình ghi đồng thời. Dừng giữa trang giữ cursor ở trang đó để tiếp tục bằng ID; việc trang nguồn thay đổi theo thời gian vẫn có thể gây bỏ sót, không bảo đảm hoàn tất toàn nguồn.

4 kiểm thử đã đạt: giữ nguyên mô tả nguồn, không dựng dữ liệu thiếu, từ chối ID/URL lệch, không nhân đôi hoặc xóa bằng chứng trường cũ khi tiếp tục. Không tự coi bản nhập có mô tả là dữ liệu đã sạch/được phép train.
