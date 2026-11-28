# SmartProp — WP-04 Explainability Technical Design (Phase A)

## 1. Contract đề xuất (additive, backward-compatible)

Giữ nguyên toàn bộ field hiện tại. Thêm nhánh `explanation` **mới**, không đổi tên field cũ:

```json
{
  "explanation_version": "1.0",
  "status": "AVAILABLE | PARTIAL | UNAVAILABLE | NOT_SUPPORTED",
  "method": "XGBOOST_NATIVE_TREESHAP",
  "output_space": "LOG1P_PRICE_VND",
  "target": "ASKING_PRICE_VND",
  "predicted_margin_log": 0.0,
  "base_value_log": 0.0,
  "base_price_vnd": 0,
  "naive_price_vnd": 0,
  "calibration": {"policy": "...", "factor": 1.0, "adjusted_price_vnd": 0},
  "factors": [{
    "feature_name": "area", "label_vi": "...",
    "input_state": "OBSERVED|DERIVED|MISSING|NOT_APPLICABLE|UNKNOWN_CATEGORY|DEFAULTED|UNVERIFIED",
    "contribution_log_raw": 0.0,
    "contribution_log_display": 0.0,
    "multiplicative_factor": 1.0,
    "direction": "INCREASE|DECREASE|NEUTRAL",
    "group": "AREA",
    "context_note_vi": ""
  }],
  "other_contribution_log": 0.0,
  "grouped_contributions": {"LOCATION": 0.0, "AREA": 0.0},
  "limitations": []
}
```

| Field | Required | Public | Ghi chú |
|---|---|---|---|
| `factors[].contribution_log_raw` | ✅ | ✅ | full precision, dùng để reconstruct |
| `contribution_log_display` | ❌ | ✅ | 4 dp cho UI |
| `multiplicative_factor` | ❌ | ✅ | `exp(φ)`, chỉ là biểu diễn |
| `other_contribution_log` | ✅ | ✅ | bắt buộc (F01) |
| `predicted_margin_log` | ✅ | ✅ | cần để kiểm chứng additivity |
| `status` | ✅ | ✅ | F05 |

**Không** trả: encoded vector đầy đủ, đường dẫn nội bộ, dữ liệu training, record id nguồn.

## 2. Provenance

`MISSING` ≠ `NOT_APPLICABLE` ≠ `UNKNOWN_CATEGORY`. Không hiển thị factor của feature `MISSING`
như thể đó là đặc điểm thực tế: dùng câu "Thông tin … chưa được cung cấp; mô hình dùng nhánh xử lý
dữ liệu thiếu."

## 3. Presentation

- **Level 1 (user):** giá, hướng tăng/giảm theo **nhóm**, danh sách thuộc tính còn thiếu, câu
  tiếng Việt theo template, nút mở chi tiết. Không hiện log unit như VNĐ.
- **Level 2 (advanced):** log-space waterfall (A), `other` + base, bridge naive → calibration →
  final, provenance badge, reconstruction formula.
- **Level 3 (optional):** multiplicative (B) với cảnh báo "factor trên (1+giá)".
- Component đề xuất: `ValuationExplanationPanel`, `FeatureContributionChart`,
  `FeatureProvenanceBadge`, `CalibrationExplanation`, `ExplanationUnavailableState`.
  Không dựa riêng vào màu; có nhãn văn bản + ARIA.

## 4. Failure policy

| Trạng thái | Điều kiện |
|---|---|
| `AVAILABLE` | đủ base + φ + reconstruction hợp lệ |
| `PARTIAL` | thiếu vài factor nhưng tổng + base vẫn khớp |
| `UNAVAILABLE` | SHAP lỗi/NaN/dimension mismatch |
| `NOT_SUPPORTED` | model không hỗ trợ |

Prediction **không** thay đổi theo trạng thái. Không bịa factor, không fallback V6.

## 5. Security

Không expose training rows, TiniX, holdout, path nội bộ, user id. Explanation là suy ra từ input
người dùng nhập + model, không phải truy cập dữ liệu huấn luyện.

## 6. WP boundaries

WP-04 = model explanation. WP-02 = comparable evidence (**không** dùng SHAP làm weight, không
dùng prediction để chọn comparable). WP-05 = interval (không suy từ SHAP). WP-06 = dashboard
(nhận metadata). WP-07 = Advisor hiển thị explanation như **một mục riêng**. WP-08 = RAG chỉ
diễn giải explanation đã được cấp quyền.


---

## 7. Bổ sung sau review

### 7.1 Schema trạng thái (nullability & hành vi)

| `status` | `factors` | `other_contribution_log` | `predicted_margin_log` | Hành vi |
|---|---|---|---|---|
| `AVAILABLE` | đầy đủ | required (number) | required | hiển thị Level 1 + 2 |
| `PARTIAL` | có thể thiếu vài factor | required | required | hiển thị + cảnh báo thiếu |
| `UNAVAILABLE` | **null** | **null** | **null** | chỉ hiện giá + thông báo |
| `NOT_SUPPORTED` | null | null | null | không hiện mục giải thích |

Prediction **không** phụ thuộc `status`. `factors[]` khi `UNAVAILABLE` phải là `null`, không
phải mảng rỗng (để phân biệt "không có" với "có nhưng rỗng").

### 7.2 Level 1/2/3

Thống nhất với Research Report §9.3: Level 1 = hướng + nhóm + missing; Level 2 = log-space
waterfall chính xác + bridge naive→calibration→final; Level 3 = multiplicative/VNĐ waterfall có
ghi rõ phụ thuộc thứ tự, **không** gọi là SHAP attribution VNĐ.

### 7.3 `impact_pct` và các field legacy

Không tái sử dụng `impact_pct` như "% giá tăng". Nếu cần, đặt tên mới
(`relative_log_effect`) kèm đơn vị "log unit" và tooltip. Không suy ra VNĐ từ log-φ nếu chỉ có
một feature (không tái lập được tổng).

### 7.4 API compatibility

Không đổi tên/xoá field hiện có. `shap_explanation` cũ **giữ nguyên**; nhánh `explanation` mới
là additive, có `explanation_version` để client cũ bỏ qua an toàn.
