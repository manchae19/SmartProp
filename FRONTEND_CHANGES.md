# Ghi chú thay đổi Frontend — Backend-Huy

- Nhánh đích: manchae19/SmartProp / Backend-Huy.
- Mốc đối chiếu trước đồng bộ: 4210ef462156cf2362fc9c5d0f090d4b08d5e2a2.
- Source SmartProp được đồng bộ từ commit 6e4abc86a7eea2ac471d82b866d75538b79c2232 của bản local đã build.
- Đường dẫn frontend/ và backend/ nằm ở gốc repository đích; không tạo thư mục SmartProp lồng thêm.
- 87 file Frontend thay đổi: 54 thêm, 33 sửa, 0 xóa.

## Các nhóm cần nhóm Frontend review

- Trang chủ/danh sách/chi tiết/bản đồ: nối API tin công khai, lọc khu vực, danh mục dự án và hiển thị trạng thái dữ liệu.
- Đăng tin: form theo bước, lưu nháp, validation, ảnh, địa chỉ và chọn ghim Google Maps/OSM; xử lý kết quả request chưa xác định.
- Tài khoản: đăng nhập/đăng ký, refresh/session opt-in, xử lý email, danh sách phiên và lỗi API.
- Module nghiệp vụ: liên hệ, yêu thích, báo cáo, thông báo, nhắn tin và tài liệu pháp lý; có trang quản trị dự án.
- Services/router/components dùng chung và CSS đã có thay đổi; nhóm FE nên review các diff dưới đây trước khi gộp sang nhánh khác.
- Build/dependencies: package/lockfile, Vite và build/publicAssets.mjs. publicAssets.mjs là source plugin, không phải build output.

## Danh sách đầy đủ so với Backend-Huy trước khi đồng bộ

| Trạng thái | File |
|---|---|
| Thêm mới | [frontend/README.md](frontend/README.md) |
| Thêm mới | [frontend/package-lock.json](frontend/package-lock.json) |
| Chỉnh sửa | [frontend/package.json](frontend/package.json) |
| Thêm mới | [frontend/vue.ui/.env.example](frontend/vue.ui/.env.example) |
| Thêm mới | [frontend/vue.ui/README.md](frontend/vue.ui/README.md) |
| Chỉnh sửa | [frontend/vue.ui/admin-dashboard/package-lock.json](frontend/vue.ui/admin-dashboard/package-lock.json) |
| Chỉnh sửa | [frontend/vue.ui/admin-dashboard/package.json](frontend/vue.ui/admin-dashboard/package.json) |
| Chỉnh sửa | [frontend/vue.ui/admin-dashboard/vite.config.js](frontend/vue.ui/admin-dashboard/vite.config.js) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/AdminLayout.vue](frontend/vue.ui/admin/views/AdminLayout.vue) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/AiConfigView.vue](frontend/vue.ui/admin/views/AiConfigView.vue) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/AuditLogsView.vue](frontend/vue.ui/admin/views/AuditLogsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/DashboardView.vue](frontend/vue.ui/admin/views/DashboardView.vue) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/PostsView.vue](frontend/vue.ui/admin/views/PostsView.vue) |
| Thêm mới | [frontend/vue.ui/admin/views/ProjectsView.vue](frontend/vue.ui/admin/views/ProjectsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/ReportsView.vue](frontend/vue.ui/admin/views/ReportsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/admin/views/UsersView.vue](frontend/vue.ui/admin/views/UsersView.vue) |
| Thêm mới | [frontend/vue.ui/build/publicAssets.mjs](frontend/vue.ui/build/publicAssets.mjs) |
| Chỉnh sửa | [frontend/vue.ui/index.html](frontend/vue.ui/index.html) |
| Chỉnh sửa | [frontend/vue.ui/package-lock.json](frontend/vue.ui/package-lock.json) |
| Chỉnh sửa | [frontend/vue.ui/package.json](frontend/vue.ui/package.json) |
| Chỉnh sửa | [frontend/vue.ui/src/App.vue](frontend/vue.ui/src/App.vue) |
| Thêm mới | [frontend/vue.ui/src/components/BusinessPage.vue](frontend/vue.ui/src/components/BusinessPage.vue) |
| Thêm mới | [frontend/vue.ui/src/components/ContactPanel.vue](frontend/vue.ui/src/components/ContactPanel.vue) |
| Thêm mới | [frontend/vue.ui/src/components/GooglePropertyLocation.vue](frontend/vue.ui/src/components/GooglePropertyLocation.vue) |
| Thêm mới | [frontend/vue.ui/src/components/LegacyPager.vue](frontend/vue.ui/src/components/LegacyPager.vue) |
| Thêm mới | [frontend/vue.ui/src/components/LegacyState.vue](frontend/vue.ui/src/components/LegacyState.vue) |
| Thêm mới | [frontend/vue.ui/src/components/LegalDocuments.vue](frontend/vue.ui/src/components/LegalDocuments.vue) |
| Chỉnh sửa | [frontend/vue.ui/src/components/LoginView.vue](frontend/vue.ui/src/components/LoginView.vue) |
| Thêm mới | [frontend/vue.ui/src/components/ManualLocationMap.vue](frontend/vue.ui/src/components/ManualLocationMap.vue) |
| Thêm mới | [frontend/vue.ui/src/components/MarketSummary.vue](frontend/vue.ui/src/components/MarketSummary.vue) |
| Thêm mới | [frontend/vue.ui/src/components/NotificationBadge.vue](frontend/vue.ui/src/components/NotificationBadge.vue) |
| Thêm mới | [frontend/vue.ui/src/components/PostStepNav.vue](frontend/vue.ui/src/components/PostStepNav.vue) |
| Thêm mới | [frontend/vue.ui/src/components/PostValidationSummary.vue](frontend/vue.ui/src/components/PostValidationSummary.vue) |
| Thêm mới | [frontend/vue.ui/src/components/PostValuationPanel.vue](frontend/vue.ui/src/components/PostValuationPanel.vue) |
| Thêm mới | [frontend/vue.ui/src/components/ProjectDirectory.vue](frontend/vue.ui/src/components/ProjectDirectory.vue) |
| Thêm mới | [frontend/vue.ui/src/components/PropertyMap.vue](frontend/vue.ui/src/components/PropertyMap.vue) |
| Chỉnh sửa | [frontend/vue.ui/src/components/RegisterView.vue](frontend/vue.ui/src/components/RegisterView.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/AdminShell.vue](frontend/vue.ui/src/components/business/AdminShell.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/AdminView.vue](frontend/vue.ui/src/components/business/AdminView.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/AppShell.vue](frontend/vue.ui/src/components/business/AppShell.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/CatalogView.vue](frontend/vue.ui/src/components/business/CatalogView.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/DetailView.vue](frontend/vue.ui/src/components/business/DetailView.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/ListingCard.vue](frontend/vue.ui/src/components/business/ListingCard.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/Pager.vue](frontend/vue.ui/src/components/business/Pager.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/PostWizard.vue](frontend/vue.ui/src/components/business/PostWizard.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/PrivateImage.vue](frontend/vue.ui/src/components/business/PrivateImage.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/ReportDetails.vue](frontend/vue.ui/src/components/business/ReportDetails.vue) |
| Thêm mới | [frontend/vue.ui/src/components/business/ReportsView.vue](frontend/vue.ui/src/components/business/ReportsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/src/router/index.js](frontend/vue.ui/src/router/index.js) |
| Thêm mới | [frontend/vue.ui/src/services/api.js](frontend/vue.ui/src/services/api.js) |
| Thêm mới | [frontend/vue.ui/src/services/collection.js](frontend/vue.ui/src/services/collection.js) |
| Thêm mới | [frontend/vue.ui/src/services/contact.js](frontend/vue.ui/src/services/contact.js) |
| Thêm mới | [frontend/vue.ui/src/services/districts.js](frontend/vue.ui/src/services/districts.js) |
| Thêm mới | [frontend/vue.ui/src/services/googleMaps.js](frontend/vue.ui/src/services/googleMaps.js) |
| Thêm mới | [frontend/vue.ui/src/services/googleMapsLocation.js](frontend/vue.ui/src/services/googleMapsLocation.js) |
| Thêm mới | [frontend/vue.ui/src/services/httpClient.js](frontend/vue.ui/src/services/httpClient.js) |
| Thêm mới | [frontend/vue.ui/src/services/legacy.js](frontend/vue.ui/src/services/legacy.js) |
| Thêm mới | [frontend/vue.ui/src/services/legacyPost.js](frontend/vue.ui/src/services/legacyPost.js) |
| Thêm mới | [frontend/vue.ui/src/services/notifications.js](frontend/vue.ui/src/services/notifications.js) |
| Thêm mới | [frontend/vue.ui/src/services/pagedResource.js](frontend/vue.ui/src/services/pagedResource.js) |
| Thêm mới | [frontend/vue.ui/src/services/postForm.js](frontend/vue.ui/src/services/postForm.js) |
| Thêm mới | [frontend/vue.ui/src/services/postMap.js](frontend/vue.ui/src/services/postMap.js) |
| Thêm mới | [frontend/vue.ui/src/services/property.js](frontend/vue.ui/src/services/property.js) |
| Thêm mới | [frontend/vue.ui/src/services/thread.js](frontend/vue.ui/src/services/thread.js) |
| Thêm mới | [frontend/vue.ui/src/services/useCollection.js](frontend/vue.ui/src/services/useCollection.js) |
| Thêm mới | [frontend/vue.ui/src/services/usePublicListings.js](frontend/vue.ui/src/services/usePublicListings.js) |
| Thêm mới | [frontend/vue.ui/src/services/valuation.js](frontend/vue.ui/src/services/valuation.js) |
| Chỉnh sửa | [frontend/vue.ui/src/style.css](frontend/vue.ui/src/style.css) |
| Chỉnh sửa | [frontend/vue.ui/user/views/AccountView.vue](frontend/vue.ui/user/views/AccountView.vue) |
| Thêm mới | [frontend/vue.ui/user/views/EmailActionView.vue](frontend/vue.ui/user/views/EmailActionView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/FavoriteView.vue](frontend/vue.ui/user/views/FavoriteView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/HomeView.vue](frontend/vue.ui/user/views/HomeView.vue) |
| Thêm mới | [frontend/vue.ui/user/views/LegalDocumentsView.vue](frontend/vue.ui/user/views/LegalDocumentsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/ListingDetailView.vue](frontend/vue.ui/user/views/ListingDetailView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/ListingsView.vue](frontend/vue.ui/user/views/ListingsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/MapView.vue](frontend/vue.ui/user/views/MapView.vue) |
| Thêm mới | [frontend/vue.ui/user/views/MessagesView.vue](frontend/vue.ui/user/views/MessagesView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/MyListingView.vue](frontend/vue.ui/user/views/MyListingView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/MyReportsView.vue](frontend/vue.ui/user/views/MyReportsView.vue) |
| Thêm mới | [frontend/vue.ui/user/views/NotificationsView.vue](frontend/vue.ui/user/views/NotificationsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/PostStep2View.vue](frontend/vue.ui/user/views/PostStep2View.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/PostStep3View.vue](frontend/vue.ui/user/views/PostStep3View.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/PostStep4View.vue](frontend/vue.ui/user/views/PostStep4View.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/PostView.vue](frontend/vue.ui/user/views/PostView.vue) |
| Chỉnh sửa | [frontend/vue.ui/user/views/ReportListingView.vue](frontend/vue.ui/user/views/ReportListingView.vue) |
| Thêm mới | [frontend/vue.ui/user/views/SessionsView.vue](frontend/vue.ui/user/views/SessionsView.vue) |
| Chỉnh sửa | [frontend/vue.ui/vite.config.js](frontend/vue.ui/vite.config.js) |

## Phạm vi và kiểm tra

- Không đưa Smartprot_tool, file test, script test, .exe, secrets, upload local hoặc build output lên nhánh.
- database.zip không được đưa lên vì chứa nhiều .exe. Source database/migrations, seeds và các tài liệu/schema cần thiết được đưa riêng theo cây source.
- ai-services/ giữ nguyên nội dung đang có trên nhánh đích; không sửa thuật toán/model trong lần đồng bộ này. integrations/valuation-v6 lấy nguyên source đã có, loại test và cache.
- Source FE/admin và Backend đã build thành công ở lượt kiểm tra commit 6e4abc8; Backend package dùng Java 21 và skip test. Lần đồng bộ này kiểm tra diff và secret trên đúng snapshot chuẩn bị push, không chạy database hoặc migration.
- .env.example chỉ là cấu hình mẫu. .env thực tế và khóa Google/Backend không được đưa vào Git.
- Trang quản trị đang nối API nằm trong frontend/vue.ui tại /admin/dashboard. admin-dashboard là scaffold riêng được giữ theo source.
