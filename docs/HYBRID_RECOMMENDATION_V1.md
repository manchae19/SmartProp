# Hybrid Recommendation V1

> Local V18/API đọc PASS: xem [FLYWAY_LOCAL_V18_RESULT.md](FLYWAY_LOCAL_V18_RESULT.md). Người dùng đã xác nhận đăng nhập trong thời gian kiểm thử; thay đổi sessions11→12 có khả năng liên quan, chưa đối chiếu độc lập. Các bảng khác không đổi. Không chạy lại apply.

> Cập nhật Local forward-only 2026-11-02: xem [FLYWAY_LOCAL_FORWARD_ONLY.md](FLYWAY_LOCAL_FORWARD_ONLY.md). Profile Local nay có V17/V18 pending; dùng launcher/profile mới. Các số liệu/test bên dưới là báo cáo tích hợp trước đó. Chưa migrate/repair.

API `POST /api/v1/recommendations` tự kết hợp tin `properties` được PUBLISHED và external đủ điều kiện. Không nhận tham số chọn nguồn. Chỉ SELECT, không tạo dữ liệu, schema hoặc gọi XGBoost.

```json
{"budgetVnd":2000000000,"purpose":"LIVING","propertyType":"ALL","minAreaSqm":60,"district":"Cẩm Lệ","limit":10}
```

budgetVnd là tổng giá mua VND, bắt buộc >0. purpose: LIVING/INVESTMENT/RENTAL; RENTAL nghĩa mua để khai thác cho thuê, không phải tìm giá thuê tháng. propertyType: ALL/HOUSE/APARTMENT/LAND/VILLA/ROOM/COMMERCIAL. minAreaSqm,district,ward tùy chọn; limit mặc định10, từ1 đến10. Output topAreas tối đa5 và topProperties tối đa limit; ít ứng viên thì trả ít hơn, không tạo dữ liệu bổ sung.

## Điều kiện dữ liệu

- Properties: PUBLISHED, không deleted/hết hạn, SALE,VND,TOTAL; giá/diện tích dương và nằm trong ngân sách/diện tích tối thiểu. PUBLISHED không được gán nhãn VERIFIED.
- Mặc định APP_RECOMMENDATION_ALLOW_UNVERIFIED_EXTERNAL=false: external chỉ VALID+VERIFIED, quality_issues rỗng. REJECTED/holdout luôn bị loại.
- Demo true: VALID+UNVERIFIED được dùng kèm cảnh báo. NEEDS_REVIEW chỉ được dùng khi issues không rỗng và toàn bộ thuộc NEAR_DUPLICATE/MISSING_DISTRICT; loại CATEGORY_MISMATCH,MULTI_PROPERTY,lỗi giá/diện tích/404 hoặc metadata không hợp lệ.
- Bỏ cả duplicate group chứa bất kỳ protected holdout; các nhóm còn lại chỉ có một đại diện điểm cao nhất, hòa điểm chọn ID theo thứ tự chữ. Chưa suy ra trùng chéo nguồn khi không có group chung.
- district so khớp đầy đủ sau chuẩn hóa dấu/khoảng trắng. External chưa có ward chuẩn hóa: khi lọc ward, không suy ra từ address_raw và loại các external thiếu ward.
- Mỗi nguồn đọc tối đa10001 ứng viên theo ID, có cảnh báo nếu chạm giới hạn; khu vực là nhãn theo nguồn, không phải kết luận đơn vị hành chính đã chuẩn hóa.

## Điểm heuristic công khai

budgetFit = 100 × max(0, 1 − abs(price/budget − 0.8)/0.8). Đây là quy tắc dành khoảng đệm ngân sách20%, không phải mô hình thị trường.

areaFit = 100 × min(1, area/target), target=1.5×minAreaSqm khi có yêu cầu, nếu không là100m². Trọng số budget/area: LIVING60/40, INVESTMENT80/20, RENTAL70/30. Trừ10 điểm UNVERIFIED và15 điểm NEEDS_REVIEW. Điểm chặn0–100, làm tròn2 số. Không phải xác suất/độ tin cậy, dự báo tăng giá, lợi suất thuê hoặc AI cá nhân hóa đã huấn luyện.

Điểm khu vực là trung bình điểm ứng viên sau lọc/khử nhóm trùng trong từng district/ward; giá rao bình quân và số mẫu chỉ mô tả tập ứng viên. Không suy ra giá giao dịch, tăng trưởng hay đầy đủ nguồn cung.

## Demo nội bộ

Bật flag chỉ trong môi trường nội bộ. Từ Bước18.4, endpoint yêu cầu **JWT của tài khoản ADMIN đang có phiên hợp lệ**, kết nối loopback và header X-SmartProp-Demo-Key khớp secret APP_RECOMMENDATION_DEMO_KEY. Khóa riêng không thay thế đăng nhập; BUYER/BROKER hoặc chỉ có khóa sẽ bị403, bearer token không hợp lệ bị401 bởi chuỗi xác thực hiện có. Key không cấu hình/sai/không gửi:403. Không ghi key/token vào repo, log, URL hoặc Frontend công khai. Không public/reverse-proxy phiên demo. Response no-store; cảnh báo UNVERIFIED/NEEDS_REVIEW có ở từng tin và khu vực liên quan. SAFE vẫn truy cập không cần đăng nhập và chặn UNVERIFIED.

Báo cáo rà soát trước import: `.scratch/hybrid-full-audit/step18-4/STEP18_4_FINAL_REVIEW_REPORT.md`. Các runner demo của các bước trước chỉ dùng khóa riêng sẽ không còn được chấp nhận; không tắt kiểm tra ADMIN để chạy lại chúng.

## Kiểm thử trên backend-huy-latest

Xem `docs/BACKEND_HUY_INTEGRATION.md` về hai lịch sử Flyway và profile Local cần dùng. Build đã kiểm thử tại `.scratch/backend-huy-integration/build`.

Integration test có source `RecommendationMySqlIntegrationTest`, chỉ bật khi process có `SMARTPROP_HYBRID_LOCAL_TEST=true` và credentials Local. Frontend có `e2e/advisor.live.mjs`, không dùng mock API.

Bộ harness Local hiện có có thể chạy từ F:\SmartProp:

```powershell
python -X utf8 .scratch/backend-huy-integration/run_local_checks.py
```

Harness chỉ đọc DB127.0.0.1:3306/smartprop, kiểm UUID/schema/history rồi gọi API thật trong hai chế độ. Nó đọc riêng credentials từ .env trong bộ nhớ, không in mật khẩu. Không migrate/import/seed hoặc dùng demo13306. Kết quả và log ở .scratch/backend-huy-integration. Kết quả safe rỗng khi chưa có nguồn đủ điều kiện là hợp lệ.
