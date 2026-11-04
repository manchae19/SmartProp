# SmartProp — Recommendation Frontend (2026-11-02)

> Cập nhật Bước18.3: ô ngân sách dùng **VNĐ**, ví dụ `2.350.000.000` hoặc `2350000000`. Nút chọn nhanh là tùy chọn. FE giữ chính xác từng đồng bằng phép toán số nguyên; API vẫn nhận `budgetVnd`. Báo cáo: `.scratch/hybrid-full-audit/step18-3/STEP18_3_INTEGRATION_REPORT.md`. Các số liệu kiểm thử bên dưới là lịch sử của từng lượt.

Đã hoàn thiện trên backend-huy-latest, giữ HEAD d0c5943. Chỉ sửa Vue Advisor, các điểm truy cập, tests và tài liệu; không sửa Backend, Flyway, MySQL, XGBoost, Broker, Avatar, Google OAuth, .env hoặc ListingCard.vue. Không commit/push/merge. Hash toàn bộ file Backend src/scripts và SQL database đã được đối chiếu trước/sau; không thay đổi.

## Người dùng có thể sử dụng trực tiếp

- Mở `/advisor` không cần đăng nhập; vào bằng nút “Tư vấn BĐS” trên Header desktop, mục cùng tên trong menu mobile/tablet hoặc nút “Tư vấn BĐS theo nhu cầu” trên trang chủ.
- Nhập ngân sách bằng số nguyên VNĐ, có thể dùng dấu chấm phân nhóm nghìn; khi rời ô, số hợp lệ được định dạng Việt Nam. Không nhập `2,5` để biểu thị tỷ. Giới hạn từ 1 đến 999.999.999.999.999 VNĐ. Chọn mục đích mua để ở/đầu tư/mua để cho thuê, loại BĐS, diện tích tối thiểu, địa bàn/phường và tối đa 5 hoặc 10 tin. Ngân sách cho RENTAL vẫn là tổng giá mua, không phải tiền thuê.
- Xem tối đa5 khu vực và10 tin do API trả về, không tự thêm mục để đủ số lượng. Thẻ hiển thị giá/diện tích/địa bàn, điểm phù hợp trên100, lý do, nguồn, trạng thái đủ điều kiện và cảnh báo chất lượng. Liên kết tin SmartProp đi tới trang chi tiết; nguồn ngoài chỉ cho URL HTTP(S) an toàn và mở thẻ mới.
- Chọn khu vực để gửi lại bộ lọc tương ứng. Khi thay đổi form mà chưa gửi, trang báo rõ kết quả vẫn theo nhu cầu đã gửi trước đó. Có nút Đặt lại và Điều chỉnh bộ lọc trong empty state.
- Chọn “Xem trên bản đồ” để chọn/định vị ghim; chọn ghim để cuộn và focus thẻ tương ứng. Hai chiều dùng chung ID tin và trạng thái selected. Map desktop bám khi cuộn; mobile xuống dưới danh sách.
- Vị trí lấy từ DTO chi tiết của đúng tin PROPERTY công khai. Loại ID không khớp, DRAFT, HIDDEN, vị trí cấp tòa nhà chưa được chấp thuận, tọa độ thiếu/không phải số/ngoài giới hạn phép chiếu hoặc0,0. Không geocode địa chỉ crawler, không dùng tâm địa bàn làm ghim. Hiển thị mức độ chính xác do nguồn khai báo; tọa độ hợp lệ không đồng nghĩa đã xác minh đúng căn nhà. Nguồn ngoài chưa có API tọa độ công khai sẽ không có ghim.
- Kết quả hiển thị ngay sau Recommendation; tải vị trí riêng, không chặn danh sách khi một chi tiết lỗi. Có trạng thái loading, khóa form trong lúc gửi, retry lỗi kết nối/dịch vụ, retry tải vị trí, thông báo lỗi tile và Safe Mode không có kết quả. Cập nhật không đồng bộ cũ bị bỏ qua sau reset/đổi truy vấn/rời trang.

## An toàn dữ liệu công khai

Frontend chỉ nhận mode SAFE/method HEURISTIC_V1 đúng contract. Tin platform cần cặp PLATFORM_PUBLISHED; nguồn ngoài cần VALID+VERIFIED. Từ chối response demo, UNVERIFIED, REJECTED, holdout, khu vực có unverified/review, nguồn không rõ, schema sai, ID/nhóm trùng hoặc quá giới hạn. Không có ô/source selector/demo key trong FE; request Recommendation không gửi Authorization hoặc X-SmartProp-Demo-Key, không tự retry login/refresh cho request public. Cơ chế tài khoản chung của ứng dụng giữ nguyên.

Không tuyên bố đây là AI cá nhân hóa đã huấn luyện, dự đoán lợi nhuận hoặc độ chính xác định giá. Điểm là heuristic tham khảo; giá là tổng giá rao bán. Lý do/cảnh báo render bằng text Vue, không v-html.

## Kiểm thử và giới hạn bằng chứng

| Hạng mục | Kết quả |
|---|---|
| Vue/Node tests | PASS:13 tests,0 lỗi; gồm compile/render component Vue |
| Vite production build | PASS |
| API thật qua Vite proxy | HTTP200:2 tỷ LIVING ALL;5 tỷ INVESTMENT HOUSE;3 tỷ RENTAL APARTMENT;2,5 tỷ LIVING LAND |
| Bộ lọc tùy chọn | PASS:địa bàn Cẩm Lệ,diện tích60,limit5 gửi đúng contract |
| Desktop1440×1000 | PASS:Header/Home CTA,form,loading,empty,error/retry,stale criteria |
| Mobile390×844 và360×800 | PASS:menu,reset/validation,không tràn ngang |
| Loading/offline | PASS:chỉ giữ chậm hoặc abort request; retry trả response thật, không mock payload API |
| OpenStreetMap | PASS:tile HTTPS thật tải được,attribution hiện; không ghim giả |
| Credentials/source gate | PASS:không demo key/Authorization; không request khóa demo |
| Backend hiện đang ở8080 | HTTP401 UNAUTHENTICATED; chưa đáp ứng contract public Recommendation |
| FE xử lý401 thật từ8080 | PASS:thông báo dịch vụ công khai chưa sẵn sàng,không redirect login/không thêm credentials |
| Phạm vi tạm hoãn | Giữ nguyên nguồn Backend/Broker/Avatar/Google/Flyway/SQL/XGBoost; không kiểm thử nghiệp vụ này |

**API Safe hiện trả0 khu vực/0 tin cho các ca đã chạy.** Empty state là kết quả thật, không bật demo hoặc seed để có thẻ. Thẻ5 khu vực/10 tin, điểm/lý do/nguồn/cảnh báo, an toàn HTML và trạng thái chọn cùng ID được kiểm bằng fixture chỉ tồn tại trong unit/component tests. Chưa có bằng chứng live click-to-pin với tin đủ điều kiện vì dataset Safe chưa trả tin có tọa độ. Không coi fixture là dữ liệu thật hoặc kết quả Recommendation thực tế.

Lượt đầu sandbox chặn tile; đã chạy lại trình duyệt với truy cập mạng và thấy tile OSM thật. Không bỏ kiểm tra chứng chỉ, không proxy ảnh giả. Mạng lỗi vẫn có thông báo tải lại. Các test dùng Backend tạm trên loopback/cổng ngẫu nhiên, JDBC read-only, startup migration/import/seed tắt; paused features tắt riêng cho process test. Không thay cấu hình hoặc dừng Backend đang chạy của người dùng. Process Backend/Vite do test tạo đã dừng.

## Chạy và kiểm tra lại

Giữ Backend của bạn ở Safe Mode (`APP_RECOMMENDATION_ALLOW_UNVERIFIED_EXTERNAL=false`) và endpoint POST/api/v1/recommendations công khai. Dịch vụ8080 đang chạy hiện trả401, nên không được xem là cùng contract đã PASS. Lượt này không thay/dừng process8080, không sửa launcher/SecurityConfig hoặc gắn credentials vào FE để vượt lỗi.

Để sử dụng, chạy Backend hiện có hỗ trợ route công khai ở một cổng còn trống (ví dụ8082, theo hướng dẫn Local V18), rồi trỏ Vite tới cổng đó. Backend dùng trong live tests đã khởi động từ JAR hiện có trên cổng ngẫu nhiên, trả HTTP200 thật; process test đã dừng. Đây là việc chọn đúng dịch vụ đích, không yêu cầu bật demo hoặc sửa nghiệp vụ Backend.

```powershell
cd F:/SmartProp/frontend/vue.ui
npm.cmd run dev
```

Mở http://127.0.0.1:5173/advisor. Proxy mặc định tới127.0.0.1:8080. Nếu Backend chạy cổng khác, đặt `$env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8082'` trước npm run dev; không cần sửa.env.

Biến proxy được đọc khi Vite khởi động. Nếu Vite của bạn đang chạy, áp dụng biến ở terminal đó và khởi động lại Vite của chính bạn. Không dừng tiến trình không rõ chủ sở hữu. Ví dụ terminal Vue:

```powershell
cd F:/SmartProp/frontend/vue.ui
$env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8082'
npm.cmd run dev
```

```powershell
npm.cmd test
npm.cmd run build
```

Khi Vite/Backend thật đang chạy, từ F:/SmartProp:

```powershell
node frontend/vue.ui/e2e/advisor.live.mjs http://127.0.0.1:5173 .scratch/advisor-browser
```

Browser test không tạo dữ liệu hay đăng nhập. Dùng profile trình duyệt mới không có credentials. Cần truy cập mạng OSM để test nền bản đồ PASS. Evidence lượt này tại `.scratch/advisor-fe/`:tests.log,build.log,live-result.json,browser/advisor-browser-result.json và ảnh advisor-desktop.png/advisor-mobile.png. Runtime secrets không ghi vào tài liệu/artifact.

## Danh sách file thuộc lượt FE

- `.gitignore`
- `frontend/vue.ui/src/components/layout/AppHeader.vue`
- `frontend/vue.ui/src/components/AdvisorResults.vue`
- `frontend/vue.ui/src/services/siteNavigation.js`
- `frontend/vue.ui/src/services/advisor.js`
- `frontend/vue.ui/user/views/HomeView.vue`
- `frontend/vue.ui/user/views/AdvisorView.vue`
- `frontend/vue.ui/tests/advisor.test.mjs`
- `frontend/vue.ui/tests/advisor-render.test.mjs`
- `frontend/vue.ui/e2e/advisor.live.mjs`
- `docs/ADVISOR_FRONTEND.md`
