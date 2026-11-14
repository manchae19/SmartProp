# Đưa bản gọn lên nhánh GitHub

Đã tách mã nguồn/tài liệu/bundle v6 khỏi dữ liệu và các kết quả sinh tự động. Nhánh hiện tại khi chuẩn bị: **`develop-binh`**. Không tự commit, push, đổi nhánh hoặc viết lại lịch sử.

Ngày 17/10/2026: bỏ theo dõi **3.448 file**, giữ khoảng **4,99 GB dữ liệu/cache trên máy**; phần mã nguồn/tài liệu/model dự kiến commit có **296 file, khoảng 3,6 MB**. Một bản sao chỉ chứa phần này (không có raw/processed/.venv) đã chạy đạt 17 kiểm thử, đủ 299 dự đoán parity và smoke test HTTP cả ba loại tài sản bằng môi trường Python hiện có.

## Phần được giữ trong repo

- Mã API, launcher, dependency, kiểm thử và fixture 299 trường hợp.
- Bundle v6 khoảng 2 MB, đúng SHA-256 model/schema đã chốt.
- Mã crawler, lọc, huấn luyện và kiểm chứng lịch sử.
- README, bản đồ file, báo cáo Markdown và khung frontend/backend.
- Cấu hình agent của dự án.

Các thư mục dữ liệu raw/processed, CSV thô, cache, checkpoint và `.scratch/` đã được đưa vào `.gitignore`. Với các file đã có trong Git, chỉ bỏ khỏi index bằng `git rm --cached`: file cục bộ vẫn còn nguyên. `git status` sẽ hiện nhiều dòng **D** đã stage cho các file này; đó là xóa khỏi phiên bản Git kế tiếp.

## Tự kiểm tra và đẩy nhánh hiện tại

Tại gốc repo:

```powershell
git branch --show-current
git diff --cached --stat
git add -A
git diff --cached --stat
git diff --cached --check
git commit -m "Prepare compact SmartProp v6 API release"
git push -u origin develop-binh
```

Chỉ dùng lệnh push trên nếu bạn vẫn đang ở `develop-binh`. Nếu muốn một nhánh mới, chạy `git switch -c feature/smartprop-v6-demo` trước bước commit và push đúng tên nhánh đó. Không dùng `git clean` để dọn các file bị ignore: đó là kho dữ liệu/môi trường cục bộ vẫn cần giữ.

## Kiểm thử trước commit

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/tests -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py
```

Các kiểm thử API dùng bundle và fixture trong repo, không cần CSV/HTML lịch sử. Các script huấn luyện/kiểm chứng lịch sử cần khôi phục archive vào đúng đường dẫn cũ; không lấy bundle demo làm bản thay thế cho kho dữ liệu đầy đủ.

## Giới hạn của việc làm gọn

Các commit cũ vẫn chứa dữ liệu đã từng được lưu. Bỏ file khỏi index giảm nội dung checkout và phần thêm vào trong commit mới, **không làm nhẹ toàn bộ lịch sử clone**. Không thực hiện purge, force-push hoặc đổi lịch sử của repo đang chia sẻ trong lần chuẩn bị này.
