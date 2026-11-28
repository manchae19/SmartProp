# WP07 — Bằng chứng trong Unified Advisor

`POST /api/v1/advisor/consult` thêm `recommendedProperties[].evidence`. Các field hiện có tiếp tục chứa dữ liệu gốc. Backend tạo metadata từ kết quả đã lọc quyền của mỗi bất động sản. Không phát sinh truy vấn DB hoặc gọi thêm dịch vụ. React hiển thị giá rao, dự đoán V1.3 và hai nhóm Comparable bằng các component sẵn có. Mục **Nguồn và giới hạn của bằng chứng** mở theo yêu cầu.

## Hợp đồng API

| Field | Ý nghĩa |
|---|---|
| `kind` | Loại bằng chứng và mục đích sử dụng. |
| `source` | Mã nguồn do ứng dụng xác định. Giá trị `null` nghĩa là chưa rõ nguồn. Với dữ liệu chưa khả dụng, nguồn chỉ xác định dịch vụ được yêu cầu. |
| `status` | `AVAILABLE`, `PARTIAL`, `MISSING`, `UNAVAILABLE`, `INVALID`, `NOT_REQUESTED` hoặc `INSUFFICIENT_EVIDENCE`. Một thiếu sót chỉ tác động đến bằng chứng liên quan. |
| `observedAt`, `generatedAt` | ISO-8601 UTC hoặc `null`, lần lượt là thời điểm quan sát và tạo dữ liệu từ nguồn. |
| `freshness` | `UNKNOWN`, `RECENT` hoặc `STALE`. Hiện các kết quả Advisor được dùng ở đây chưa có thời điểm quan sát và trả `UNKNOWN`. UI có thể phân loại khi có nguồn và `observedAt` hợp lệ. Quá 90 ngày là `STALE`. `generatedAt` không xác định tuổi quan sát. |
| `limitations` | Danh sách mã giới hạn hữu hạn. UI dịch sang nhãn tiếng Việt. |
| `reference` | Tên field tương đối trong cùng bất động sản. Không chứa URL hoặc bản sao dữ liệu. |

| Kind | Source | Reference |
|---|---|---|
| `VALUATION` | `XGBOOST_V1_3` | `valuationEvidence` |
| `EXPLANATION` | `WP04_TREESHAP` | `valuationEvidence.explanation` |
| `SIMILAR_LISTING` | `WP02_COMPARABLE` | `comparableEvidence` |
| `VALUATION_SUPPORT` | `WP02_COMPARABLE` | `valuationComparableEvidence` |
| `LOCATION` | `SMARTPROP_GIS_POI` | `locationIntelligence` |
| `RECOMMENDATION` | `SMARTPROP_LISTING`, `EXTERNAL_LISTING` hoặc `TINIX_RESEARCH` khi đã được phép nghiên cứu | `source` |

Ví dụ metadata cho một lời gọi đã định giá thành công.

```json
{
  "kind": "VALUATION",
  "source": "XGBOOST_V1_3",
  "status": "AVAILABLE",
  "observedAt": null,
  "generatedAt": null,
  "freshness": "UNKNOWN",
  "limitations": ["ESTIMATED_ASKING_PRICE"],
  "reference": "valuationEvidence"
}
```

## Quy tắc trình bày và phạm vi

- V1.3 giữ giá rao ước tính từ payload cùng calibration và rounding hiện hành. Giá rao của tin, giá rao Comparable và điểm phù hợp được hiển thị riêng. Khi các giá trị khác nhau, ứng dụng giữ từng kết quả. Khi V1.3 chưa khả dụng, Advisor SAFE có thể trả tin và Comparable nhưng không có giá định giá thay thế.
- WP04 giữ payload TreeSHAP và dùng cùng component giải thích với các bề mặt khác. Phản hồi thiếu, lỗi hoặc không khớp với giá sẽ không có attribution thay thế.
- Hai purpose của WP02 giữ nguyên. `VALUATION_SUPPORT` tiếp tục độc lập với giá mục tiêu. Giao diện WP07 ẩn mẫu Comparable khi cohort có dưới 3 thực thể sau lọc trùng. Từ 3–4 chỉ có thể xem ví dụ. Trung vị cần ít nhất 5 quan sát công khai hợp lệ và cohort quét đủ, theo WP02.
- GIS chỉ dùng khoảng cách đường chim bay cho tọa độ được phép. Fallback hành chính giữ ngữ cảnh khu vực.
- Metadata không mang địa chỉ, tọa độ, ID thô, token, giá, điểm hoặc dữ liệu giải thích sao chép. UI kiểm tra mã nguồn và tham chiếu cho từng loại. Quyền xem research tiếp tục do backend và phiên hiện tại quyết định. Các consumer cũ có thể bỏ qua field bổ sung. Frontend chấp nhận payload cũ thiếu `evidence`.
- Market trong Advisor chờ đầu ra WP03. Buyer search, consent, land isolation, RAG state và proxy thuộc PR43. Kiểm thử độc lập WP07 không bao hàm một tree đã tích hợp PR43. Dữ liệu dùng trong E2E thuộc fixture cô lập.

## Kiểm thử và rollback

- Unit Java `AdvisorEvidenceProjectionTest` và unit Node `frontend/tests/advisorEvidence.test.mjs`. Cả hai thuộc source Git dù thư mục test có quy tắc ignore file mới.
- E2E `frontend/e2e/wp07-advisor-evidence.mjs` dùng fixture chuẩn WP04, build thực tế và Chromium. Lấy snapshot baseline bằng đối số `baseline` rồi chạy `candidate` với cùng dữ liệu fixture. Đặt `WP07_API` và `WP07_APP` là URL loopback của từng bản, `WP07_OUTPUT` là thư mục evidence dùng chung. Ở chế độ candidate, đặt `PLAYWRIGHT_PATH` và `CHROME` cho browser. Baseline và candidate có thể chia sẻ MySQL và FastAPI của cùng fixture, mỗi bản dùng cổng Spring riêng. Xem [hướng dẫn fixture](../../frontend/tests/wp04/browser/tools/README.md).
- Đặt `advisor.evidence.v2=false` hoặc `ADVISOR_EVIDENCE_V2=false` rồi khởi động lại Spring để bỏ field `evidence`. Giao diện dùng đường hiển thị cũ. Rollback toàn bộ bằng revert thông thường. Không có thay đổi schema hoặc model để hoàn nguyên.
