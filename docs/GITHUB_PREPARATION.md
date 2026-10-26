# Đưa bản gọn lên nhánh GitHub

Đã tách mã nguồn/tài liệu/bundle v6 khỏi dữ liệu trên `develop-binh`. Nhánh `feature/fe-ai-v6` đã có commit `3f2ca86` cho FE–AI và merge `97de3e1` ghép lịch sử `main`. Bản mở rộng dùng mã BE/database tại `Backend-Huy` (`ac13ec3`), thêm lịch sử định giá và chuẩn bị dữ liệu mới. Không viết lại lịch sử hoặc đẩy trực tiếp vào `main`; bàn giao qua PR.

Ngày 26/10/2026: đã đẩy commit tính năng `2bc8d77` lên `origin/feature/fe-ai-v6` và tạo [PR #4 vào main](https://github.com/manchae19/SmartProp/pull/4), gắn [issue #3](https://github.com/manchae19/SmartProp/issues/3). PR đang chờ review, chưa merge. Các lệnh commit/push phía dưới là hướng dẫn cho thay đổi tiếp theo, không cần chạy lại để bàn giao bản này.

Ngày 17/10/2026: bỏ theo dõi **3.448 file**, giữ khoảng **4,99 GB dữ liệu/cache trên máy**; phần mã nguồn/tài liệu/model dự kiến commit có **296 file, khoảng 3,6 MB**. Một bản sao chỉ chứa phần này (không có raw/processed/.venv) đã chạy đạt 17 kiểm thử, đủ 299 dự đoán parity và smoke test HTTP cả ba loại tài sản bằng môi trường Python hiện có.

Các số kích thước trên là mốc trước khi đưa frontend vào. Frontend mới giữ tài nguyên từ `main`, gồm video nền có sẵn; `node_modules`, bản build và kết quả kiểm thử vẫn bị ignore. Kho CSV/HTML/raw/processed tiếp tục ở ngoài Git.

## Phần được giữ trong repo

- Mã API, launcher, dependency, kiểm thử và fixture 299 trường hợp.
- Bundle v6 khoảng 2 MB, đúng SHA-256 model/schema đã chốt.
- Mã crawler, lọc, huấn luyện và kiểm chứng lịch sử.
- README, bản đồ file, báo cáo Markdown, frontend, BE Spring Boot, SQL nguồn và kiểm thử.
- Cấu hình agent của dự án.

Các thư mục dữ liệu raw/processed, CSV thô, cache, checkpoint và `.scratch/` đã được đưa vào `.gitignore`. Với các file đã có trong Git, chỉ bỏ khỏi index bằng `git rm --cached`: file cục bộ vẫn còn nguyên. `git status` sẽ hiện nhiều dòng **D** đã stage cho các file này; đó là xóa khỏi phiên bản Git kế tiếp.

Phần bỏ theo dõi ở trên đã nằm trong commit chuẩn bị bản gọn; không cần chạy lại. `backend/target/` và `backend/var/` cũng bị ignore, gồm JAR, MySQL demo, JWT/config và lịch sử tài khoản. Chỉ SQL migration/test fixture tổng hợp được đưa lên Git, không đưa database thật hoặc mật khẩu vào PR.

## Tự kiểm tra và đẩy nhánh hiện tại

Tại gốc repo:

```powershell
git branch --show-current
git diff --cached --stat
git add -A
git diff --cached --stat
git diff --cached --check
git commit -m "Integrate Vue frontend with v6 valuation API"
git push -u origin feature/fe-ai-v6
```

Chỉ dùng lệnh push trên nếu vẫn đang ở `feature/fe-ai-v6`. Kiểm tra tên nhánh trước khi commit/push. Không dùng `git clean` để dọn các file bị ignore: đó là kho dữ liệu/môi trường cục bộ vẫn cần giữ.

## Kiểm thử trước commit

```powershell
.\ai-services\.venv\Scripts\python.exe -X utf8 -m unittest discover -s ai-services/tests -v
.\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/tests/smoke_http_v6.py
```

Các kiểm thử API dùng bundle và fixture trong repo, không cần CSV/HTML lịch sử. Các script huấn luyện/kiểm chứng lịch sử cần khôi phục archive vào đúng đường dẫn cũ; không lấy bundle demo làm bản thay thế cho kho dữ liệu đầy đủ.

## Giới hạn của việc làm gọn

Các commit cũ vẫn chứa dữ liệu đã từng được lưu. Bỏ file khỏi index giảm nội dung checkout và phần thêm vào trong commit mới, **không làm nhẹ toàn bộ lịch sử clone**. Không thực hiện purge, force-push hoặc đổi lịch sử của repo đang chia sẻ trong lần chuẩn bị này.
