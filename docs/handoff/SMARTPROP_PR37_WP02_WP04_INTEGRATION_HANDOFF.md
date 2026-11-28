# HANDOFF TÍCH HỢP SONG SONG CHO WP-02 & WP-04 SAU KHI PR #37 HỢP NHẤT

- **Nhánh tích hợp PR #37**: `integration/pr37-ui-validation` (worktree cô lập `F:\SmartProp\.worktrees\pr37-ui-integration`)
- **Baseline `origin/main` đã tích hợp**: `f972d3a3465e5cc0ebe4260ddfbee7a8d32eee42`
- **Các nhánh song song đã kiểm tra chỉ đọc (100% không chạm tới)**:
  - **WP-02 Comparable Correctness**: `origin/feature/wp02-comparable-correctness` (`75b8f4f`)
  - **WP-04 Explainable AI**: `origin/research/wp04-explainable-ai` (`2f3af3f`)
  - **PR #43 Land Runtime**: `origin/feature/advisor-land-runtime-20261126` (`f59edf2`)
  - **PR #41 News Backend**: `origin/feature/news-backend-v1` (`da1d8c3`)

---

## 1. Phân tích Xung đột File Dùng Chung (Shared-File Overlap Matrix)

### 1.1. Giao thoa giữa `integration/pr37-ui-validation` và **WP-02** (`feature/wp02-comparable-correctness`)

| File dùng chung | Thay đổi phía PR #37 (`integration/pr37-ui-validation`) | Thay đổi phía WP-02 (`feature/wp02-comparable-correctness`) | Hướng dẫn hợp nhất bắt buộc |
|---|---|---|---|
| `frontend/src/features/property/ListingDetailView.jsx` | Cải tiến giao diện Signature (`.listing-gallery`, `.detail-layout`, `.detail-price`, `.detail-specs`, `.listing-evidence`, `.signature-gallery`), bổ sung `role="dialog" aria-modal="true"`, bẫy tiêu điểm bàn phím + phím `Escape`, giữ nguyên `<CoordinateStatusPanel coordinate={view.property?.coordinate} />`, và loại bỏ ký tự null `\u0000` tại khối bản đồ. | Import `ComparableEvidenceLookup` và chèn `<ComparableEvidenceLookup body={{ propertyId: view.property.id, purpose: "SIMILAR_LISTING" }} title="Đối chiếu tin tương đồng" />` ngay dưới `<ImageAnalysisSection propertyId={view.property?.id} />`. | **Giữ cả hai phía**: giữ toàn bộ cấu trúc Signature gallery/accessibility + `CoordinateStatusPanel` của PR #37, đồng thời chèn `<ComparableEvidenceLookup ... />` ngay sau `<ImageAnalysisSection propertyId={view.property?.id} />`. Không dùng `--ours` hay `--theirs`. |

*Lưu ý các file frontend khác của WP-02 không bị PR #37 chỉnh sửa*:
- `ComparablesView.jsx`, `ComparableListingsCard.jsx`, `ComparableListingsCard.css`, `ComparableEvidenceLookup.jsx`, `comparables.js`
- `AdvisorEvidencePanel.jsx`, `AdvisorResults.jsx`, `advisorAnalysis.js`
- `ValuationPanel.jsx`, `PostValuationPanel.jsx`
*(PR #37 giữ nguyên 100% phiên bản `origin/main` của các file trên để tránh xung đột với WP-02).*

### 1.2. Giao thoa giữa `integration/pr37-ui-validation` và **WP-04** (`research/wp04-explainable-ai`)

- **Hiện tại (`2f3af3f`)**: WP-04 chỉ thay đổi tầng Python `ai-services/app/api/{schemas,valuation}.py`, `ai-services/app/models/xgboost/{explanation_v1_3,predictor_v1_3}.py`, `ai-services/tests/test_wp04_*.py` và `docs/ai/SMARTPROP_WP04_*` — **`0` file chồng lấn trực tiếp** với PR #37!
- **Khi WP-04 nối UI giải thích SHAP/bằng chứng V1.3 ở giai đoạn sau**:
  - Sẽ tác động vào `ValuationPanel.jsx`, `PostValuationPanel.jsx`, `ListingDetailView.jsx` (khối `.listing-evidence`) và CSS theme `[data-ui-theme=slate]`.
  - Phải giữ nguyên quy tắc theme trong `frontend/src/styles/interface.css` (dùng biến `--ui-surface`, `--ui-soft`, `--ui-border`, `--ui-ink`, `--ui-accent`) và không hiển thị lại kết quả V6 hay giải thích SHAP giả tĩnh.

---

## 2. Các Bất biến Hợp đồng & Bảo mật Phải Bảo toàn Khi Merge Tiếp theo

1. **Coordinate Provenance V1 (`ListingDetailView.jsx`, `PostView.jsx`, `/admin/coordinate-review`)**:
   - Không gỡ `<CoordinateStatusPanel coordinate={view.property?.coordinate} />` trên `ListingDetailView.jsx`.
   - Giữ route `/admin/coordinate-review` (`AdminCoordinateReviewView.jsx`) trong `frontend/src/app/router.js`.
   - Không hiển thị điểm ghim hoặc tiện ích khoảng cách khi `canShowReferenceMap` / `canAnalyzeDistance` trả `false`.
2. **Phase 0 Research Data Isolation & Reactive Session (`MarketAnalyticsView.jsx`, `UnifiedAdvisorView.jsx`)**:
   - `MarketAnalyticsView.jsx` bắt buộc giữ kết nối `useSyncExternalStore(session.subscribe, session.getSnapshot)` thông qua `createMarketAnalyticsController` (`marketAnalyticsState.js`).
   - Không lộ tùy chọn `TINIX_RESEARCH` hoặc checkbox `includeResearch` cho khách ẩn danh, `BUYER`, `BROKER`, hoặc khi máy chủ tắt `app.market.research-enabled`.
   - Mọi sự kiện mất quyền (`logout`, hết hạn phiên, đổi tài khoản, `401`/`403`) phải lập tức hủy request đang bay, xóa dữ liệu research trên UI và chặn kết quả trả muộn.
3. **Market Data Honesty (`/market`, `/market/:district`, `TopSearchedAreas.jsx`)**:
   - Giữ đủ **7** quận/huyện Đà Nẵng (bao gồm `Hòa Vang` / `hoa-vang`); `getDistrictProfile` phải trả `null` với slug lạ, không bao giờ fallback sang `Sơn Trà`.
   - Không khôi phục mảng `priceHistory` giả 12 quý, `priceGrowthYoY`, `liquidityRating`, `viewsCount` tĩnh hay nhãn `"AI Valuation V1.3"` trên trang `/market`.
4. **XGBoost V1.3 Only & Asset Allowlist (`publicAssets.mjs`)**:
   - Mọi luồng định giá mới chỉ gọi `XGBoost V1.3` (không fallback V6, không tạo giá tĩnh).
   - Không đưa lại `media/areas/*.webp` vào `frontend/build/publicAssets.mjs` cho đến khi có hồ sơ chứng minh tác giả gốc và giấy phép phân phối lại hợp lệ.
