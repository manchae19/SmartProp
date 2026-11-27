# SmartProp — WP-04 Explainability Research Report (Phase A)

## 1. TreeSHAP trên V1.3

`booster.predict(dmat, pred_contribs=True, iteration_range=ir)` trả vector `[φ_1..φ_p, b]` với

    z = b + Σ φ_i        (log1p space)

**Đo trên model thật** (84 case): sai lệch tương đối `max 1.50e-06`, `median 3.67e-07`,
`p95 1.04e-06`. Đây là mức float32 (margin ~20–25), không phải lỗi thuật toán.

## 2. Vì sao log-space không cộng được thành VNĐ

    z = b + Σφ_i
    naive = expm1(z) = exp(b)·Π exp(φ_i) − 1

⇒ contribution **nhân** trong không gian `1+price`, không cộng tuyến tính trong VNĐ.
Phản ví dụ số (từ benchmark): với `z`, `b`, `Σφ` cho trước, `expm1(b) + Σ (expm1(φ_i)) ≠ expm1(z)`
— sai khác hàng trăm triệu đồng. Vì vậy **không** được hiển thị "diện tích làm tăng 500 triệu".

## 3. Hai cách biểu diễn hợp lệ

| | Công thức | Đúng toán học | Dễ hiểu |
|---|---|---|---|
| **A — log-space** | `φ_i` thô | ✅ chính xác tuyệt đối | ❌ |
| **B — multiplicative** | `exp(φ_i)` là factor trên `1+price` | ✅ chính xác | ⚠️ dễ bị đọc thành % giá |
| **C — VND waterfall tuần tự** | `price_k = price_{k-1}·exp(φ_k)` | ✅ chỉ khi giữ đúng thứ tự | ✅ nhưng **phụ thuộc thứ tự** |

Khuyến nghị: **A** cho advanced view (đúng), **B** cho user view (direction + relative),
**C** chỉ như minh hoạ có ghi rõ "thứ tự trình bày" và **không** gọi là SHAP attribution VNĐ.

## 4. Calibration

    final = max(0, exp(z) · factor(band_of(naive)) − 1)

Band chọn theo **naive** (chưa calib). Đo: reconstruction khớp `3.61e-06` tương đối (float32 qua
`exp`). Calibration **không phân bổ** cho từng feature — factor là phép biến đổi toàn cục theo
band, không phải contribution.

## 5. Top-K và grouping

- Top-6 thiếu phần dư tới **0.1239 log unit** ⇒ cần `other_contribution_log` (F01).
- Grouping theo 9 nhóm; kiểm chứng `Σ(grouped) − Σ(all) = 0.0` chính xác (không double-count).
- `Σ|φ|` **không** dùng làm signed contribution.

## 6. Provenance taxonomy (đề xuất)

`OBSERVED` · `DERIVED` · `DEFAULTED` · `MISSING` · `NOT_APPLICABLE` · `UNKNOWN_CATEGORY` ·
`UNVERIFIED`. Chỉ gán khi có evidence. Benchmark đếm được: OBSERVED 301 · DERIVED 1232 ·
MISSING 203 · NOT_APPLICABLE 112 trên 84 case.

## 7. Ranh giới tuyên bố

TreeSHAP giải thích **hành vi mô hình**, không phải nhân quả, không phải khoảng tin cậy,
không phải bằng chứng thị trường. Không suy ra prediction interval từ SHAP (WP-05).

## 8. Sự cố môi trường đã gặp (ghi lại để tái lập)

Chạy benchmark bằng **sai virtualenv** (`.scratch/v14-venv`, xgboost 3.x khác) gây
`XGBoostError: Found a category not in the training set ... column 17`. Với **venv của project**
(`ai-services/.venv`, xgboost 3.4.1) model chạy đúng (6.605.239.848 VND). Đây là lỗi môi trường,
**không** phải lỗi production — nhưng là cảnh báo: explanation phải kiểm tra version xgboost.


---

## 9. Sửa công thức sau review

### 9.1 Waterfall VNĐ tuần tự — công thức đúng

Với thứ tự trình bày `φ_1 … φ_p`, giá trị tại bước `k`:

```
p_0   = expm1(b)
p_k   = (p_{k-1} + 1) * exp(φ_k) - 1
```

Kiểm chứng: `p_p = expm1(b + Σφ) = naive`. Mỗi bước **phụ thuộc thứ tự**; do đó waterfall VNĐ
là **derived visualization**, **không** phải "SHAP attribution VNĐ". Không được trình bày
`p_k - p_{k-1}` như đóng góp độc lập của feature `k`.

### 9.2 Calibration là bước riêng

```
final = max(0, exp(z) * factor(band_of(naive)) - 1)
```

Factor phụ thuộc **band của naive**, không phụ thuộc từng feature ⇒ **không phân bổ** factor cho
các φ. Trình bày: naive → (policy, factor) → final, tách khỏi waterfall.

### 9.3 Ba mức hiển thị (thống nhất với Technical Design)

| Mức | Nội dung | Đúng toán học |
|---|---|---|
| **Level 1 — người dùng** | hướng tăng/giảm theo **nhóm**, thuộc tính còn thiếu, câu tiếng Việt | dựa trên log-φ, có ghi chú |
| **Level 2 — advanced** | log-space waterfall **chính xác**: base → Σφ → margin → naive → calibration → final, kèm `other` | ✅ exact |
| **Level 3 — optional** | multiplicative `exp(φ)` ("factor trên 1+giá") và/hoặc waterfall VNĐ có ghi rõ phụ thuộc thứ tự | ✅ nhưng dễ hiểu nhầm |

### 9.4 Đã đo / đã kiểm chứng / chưa triển khai

- **Đã đo:** top-K remainder tới **0.1239 log unit**; grouped ≡ total = 0.0; additivity ≤ 1.19e-06.
- **Đã kiểm chứng:** top-K + `other` tái lập đúng tổng contribution.
- **Chưa triển khai:** explanation contract trong production (design-phase only).

### 9.5 Cảnh báo field legacy

Nếu payload lịch sử có `impact_pct` (hoặc tương tự), đó **không** phải phần trăm tăng/giảm giá
giao dịch thực tế và **không** phải đóng góp SHAP VNĐ. Nếu dùng lại, phải đổi nhãn thành
"mức ảnh hưởng tương đối trên thang log" và không hiển thị như % giá.
