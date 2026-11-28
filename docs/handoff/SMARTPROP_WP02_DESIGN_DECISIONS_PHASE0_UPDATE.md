# CẬP NHẬT QUYẾT ĐỊNH THIẾT KẾ WP-02 SAU REVIEW PHASE 0

- **Branch**: `fix/research-evidence-access-control`
- **Baseline**: `1f36205fbff5ef04f43c27af83c1694d500a9d61` (`origin/main`)
- **Trạng thái**: **CHỈ CẬP NHẬT THIẾT KẾ (DESIGN-ONLY)** — chưa triển khai mã nguồn production cho các hạng mục dưới đây trong Phase 0.

---

## 1. Tách bạch rõ Tìm kiếm theo Ngân sách Người mua vs Truy xuất Bằng chứng Định giá độc lập giá

Thiết kế WP-02 cập nhật phân định rạch ròi hai bài toán nghiệp vụ khác nhau để **không làm hỏng tính năng lọc ngân sách hợp lệ của người mua**, đồng thời **triệt tiêu rò rỉ xác nhận vòng tròn (circular evidence) trong định giá**:

| Chế độ / Luồng nghiệp vụ | Mục đích sử dụng | Quy tắc đối với Giá / Ngân sách |
|---|---|---|
| **1. Buyer Budget Search & Recommendation** (`/listings`, `/recommendations`, bước chọn `recommendedProperties` của `/advisor/consult`, và chế độ `SIMILAR_LISTING` khi người mua đang xem 1 tin đăng có giá niêm yết cố định) | Giúp người mua tìm bất động sản phù hợp khả năng chi trả thực tế của họ (`statedBudgetVnd` + `budgetFlexibilityPct`). | **GIỮ NGUYÊN lọc ngân sách hợp lệ**. Ngân sách ở đây là ràng buộc đầu vào của người mua, không phải dự báo của mô hình AI. |
| **2. Valuation Evidence Retrieval (`VALUATION_SUPPORT`)** (dùng khi cung cấp comparable đối chiếu cho kết quả định giá `XGBoost V1.3` tại `/valuation`, `/post` valuation preview, hoặc kiểm định độc lập giá trị bất động sản) | Cung cấp tập bất động sản tương đồng về mặt vật lý & vị trí để người dùng đối chiếu khách quan với con số dự báo V1.3. | **TUYỆT ĐỐI ĐỘC LẬP VỚI GIÁ TARGET (`priceVnd = null`, `W_PRICE = 0`)**: Không dùng giá dự báo của V1.3 và không dùng giá kỳ vọng của chủ nhà để cắt phong bì `[0.4×, 2.5×]` hay chấm điểm tương đồng. Chỉ lọc ngưỡng hợp lý toàn cục `[200M, 1.000B] VND` nhằm loại bỏ dữ liệu lỗi nhập liệu. |

---

## 2. Khử trùng lặp thực thể (Entity Deduplication) — Không áp dụng máy móc `v15-dup-1` cho mọi nguồn

Kết quả nghiên cứu V1.5 (`v15-dup-1`) được thiết kế trên tập TiniX giàu thuộc tính (có `street_name`, `ward`, `floor_count`, `frontage_width`, `road_width`, `bedroom_count`, `bathroom_count`, `house_direction`) và yêu cầu **ít nhất 3 trường vật lý non-null không mâu thuẫn**.

Qua kiểm chứng schema thực tế trên `origin/main`:
- `external_listings` **không có** các cột `ward`, `street_name`, `floors`, `frontage`, `road_width`, `bedrooms`, `bathrooms`, `direction` (chỉ có `source`, `source_listing_id`, `detail_url`, `title`, `category`, `district`, `area_sqm`, `price`, `address_raw`, `duplicate_group`).
- `properties` có `ward`, `address`, `bedrooms`, `bathrooms`, `floor`, `direction` và bảng `property_image_scan` (V21), nhưng **chưa có cột tách rời `frontage_width` / `road_width`**.

**Quyết định thiết kế hiệu chỉnh**:
1. **Không áp dụng nguyên xi `v15-dup-1` xuyên cả 3 nguồn** khi chưa kiểm chứng tương thích trường dữ liệu: nếu áp điều kiện `>= 3` trường vật lý lên `external_listings` thì tỷ lệ bắt trùng sẽ bằng `0%`; ngược lại nếu bỏ điều kiện tên đường và trường vật lý thì sẽ **gộp nhầm các căn nhà/lô đất khác nhau có cùng diện tích và giá trong cùng quận** (lặp lại sai lầm `6,6%` trước `v15-dup-1`).
2. **Chiến lược khử trùng lặp phân tầng theo độ giàu dữ liệu của từng cặp nguồn**:
   - **Tầng A — Định danh cứng (áp dụng ngay, độ chính xác 100%)**: Loại trừ tự khớp (`excludePropertyId`, `excludeExternalId`, `excludeTinixId`), trùng `canonicalUrl`, trùng `(source, source_listing_id)`, trùng `duplicate_group` nội bộ, hoặc cặp tin nội sàn bị đánh dấu `DUPLICATE` có xác thực trong `property_image_scan`.
   - **Tầng B — Nội bộ TiniX (`TINIX ↔ TINIX`)**: Áp dụng đúng chuẩn `v15-dup-1` vì đầy đủ 7 trường vật lý và `street_name`.
   - **Tầng C — Nội sàn & Xuyên nguồn (`SMARTPROP ↔ EXTERNAL ↔ TINIX`)**: **Bắt buộc phải thực hiện kiểm thử tương thích thực nghiệm (precision/false-merge audit trên tập mẫu đối chứng)** trước khi bật gộp tự động; khi chưa đủ bằng chứng định danh đường/dự án chuẩn hóa ở `external_listings`, chỉ gắn cờ cảnh báo `POSSIBLE_SAME_ENTITY` thay vì tự động xóa ứng viên hợp lệ.

---

## 3. Lọc thời gian (`Temporal / As-Of Filtering`)

- **Chế độ `LIVE_CURRENT_MARKET` (`asOfDate == null`)**:
  - Bắt buộc bổ sung điều kiện `(p.expires_at IS NULL OR p.expires_at > UTC_TIMESTAMP(6))` cho bảng `properties` (sửa thiếu sót hiện tại so với `CollectionSummaryService`).
  - Trả kèm ngày ghi nhận (`published_at` cho `properties` / `tinix_dataset_records`, `collected_at` cho `external_listings` — ghi rõ `dateBasis` từng nguồn vì `collected_at` là thời điểm thu thập, không đồng nhất với ngày đăng gốc).
- **Chế độ `HISTORICAL_AS_OF` (`asOfDate != null` — phục vụ backtest/đánh giá lịch sử)**:
  - Áp dụng điều kiện nghiêm ngặt `observedAt < asOfStartOfDayUtc`; mọi bản ghi thiếu ngày hợp lệ bị loại khỏi chế độ đánh giá lịch sử để đảm bảo không rò rỉ tương lai.

---

## 4. Tuyển chọn ứng viên tất định (Deterministic Candidate Selection)

- Mọi câu lệnh SQL có `LIMIT` trên `properties`, `external_listings` và `tinix_dataset_records` bắt buộc có mệnh đề `ORDER BY` tất định kết thúc bằng khóa chính duy nhất (`id ASC` / `internal_id ASC`).
- Bộ sắp xếp Java trong `ComparableRankingService` bắt buộc dùng chuỗi khóa thứ tự toàn phần (*total order*): `score DESC` → `stage ASC` → `areaDelta ASC` → `sourcePriority ASC` → `candidateId ASC`, đảm bảo cùng một trạng thái dữ liệu luôn trả về đúng một danh sách kết quả duy nhất.

---

## 5. Xử lý thiếu đặc trưng trong Similarity Scoring (Coverage Penalty)

- Ghi nhận vấn đề: chuẩn hóa `total / weightUsed` hiện tại có thể chấm điểm cao cho dòng `EXTERNAL_LISTING` thiếu `ward`, `bedrooms`, `floors` so với dòng `SMARTPROP` có đủ thông tin nhưng lệch nhẹ 1 thuộc tính.
- **Quyết định thiết kế**: Hệ số phạt/co giãn độ phủ đặc trưng (*coverage penalty / shrinkage*) phải được **kiểm định độ nhạy trên bộ fixture xếp hạng thực tế** (đối chiếu thứ hạng cặp `SMARTPROP` đủ trường vs `EXTERNAL_LISTING` thiếu trường ở nhiều quận và loại hình) trước khi chốt hằng số, tránh đặt hệ số phạt tùy ý làm triệt tiêu hoàn toàn nguồn `EXTERNAL_LISTING` ở chế độ công khai `SAFE` (nơi `TINIX_RESEARCH` đã bị khóa ở Phase 0).

---

## 6. Chiến lược Truy xuất & Tái sử dụng Schema hiện có (Thay thế ước lượng bộ nhớ chưa benchmark)

1. **Chính sách dữ liệu sau Phase 0**:
   - Ở chế độ công khai (`SAFE` mode), `TINIX_RESEARCH` **không được phép truy xuất**. Tập ứng viên công khai chỉ gồm `properties` và `external_listings` — cả hai bảng đều nhỏ và đã có sẵn cột/index phù hợp trong schema hiện hành (`V1..V26`), nên truy vấn SQL trực tiếp lọc theo `(district, category/property_type, area_sqm)` đáp ứng ngay mà **không cần bất kỳ chỉ mục RAM hay migration mới nào**.
2. **Đối với chế độ nghiên cứu / nội bộ có quyền truy cập `tinix_dataset_records`**:
   - **Gỡ bỏ ước lượng chưa kiểm chứng `"8–10 MB RAM"`** khỏi quyết định kiến trúc: dung lượng heap thực tế (bao gồm object header JVM, `String` backing arrays, `BigDecimal` instances và GC overhead cho ~55.816 bản ghi) cũng như thời gian nạp lạnh hiện ở trạng thái **`NOT_VERIFIED` (chưa chạy benchmark JOL / heap dump thực tế)**.
   - **Thứ tự ưu tiên kỹ thuật khi triển khai WP-02**:
     1. **Ưu tiên 1 — Tận dụng 100% schema hiện có (`V1..V26`)**: Kiểm tra kế hoạch thực thi (`EXPLAIN ANALYZE` chỉ đọc trên DB kiểm thử cô lập) đối với truy vấn hai pha hiện có kết hợp lọc sớm hoặc tái sử dụng snapshot đã có sẵn của hệ thống (`TinixSnapshotCache` trong module recommendation nếu tương thích cột) mà không tạo bản sao dữ liệu thứ hai trong RAM.
     2. **Ưu tiên 2 — Benchmark trước khi chọn giữa In-Memory Index và Covering Index SQL**: Chỉ chọn `ComparableTinixMemoryIndex` nếu đo thực tế mức tiêu thụ heap sau GC nằm trong ngưỡng an toàn và không trùng lặp với cache của `MarketAnalyticsService` / `TinixSnapshotCache`; ngược lại mới đề xuất covering index SQL ở phiên bản migration sau `V28` (sau khi PR #41 hoàn tất). Tuyệt đối không tạo migration trong Phase 0.
