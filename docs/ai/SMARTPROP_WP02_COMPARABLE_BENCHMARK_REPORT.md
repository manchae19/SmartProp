# SmartProp — WP-02 Comparable Benchmark Report (Phase A)

**Nhãn:** `SYNTHETIC_BENCHMARK` · **Không** phải đánh giá thị trường thật.
**Base:** `origin/main` @ `a0e3834` · **Phase A:** không sửa production.

---

## 1. Provenance của fixture

- Sinh hoàn toàn bằng code: `docs/ai/benchmark/wp02_comparable_benchmark.py`
- Số cohort: **28** = 7 quận × 4 loại hình (`LAND`, `HOUSE`, `APARTMENT`, `VILLA`)
- Quận: Hải Châu, Thanh Khê, Sơn Trà, Ngũ Hành Sơn, Liên Chiểu, Cẩm Lệ, Hòa Vang (khớp bộ địa
  bàn hiện có của dự án).
- Mỗi cohort: 6 tài sản **thật sự tương đồng** (nhãn relevant) + 1 self-match cùng entity +
  1 bản trùng cross-source + 1 repost cùng entity + 1 sai địa bàn + 1 sai loại hình +
  1 outlier giá cao + 1 outlier giá thấp + 1 tin cũ + 1 tin thiếu dữ liệu + 1 dòng TiniX.
- **Nhãn relevance KHÔNG dùng giá**: tài sản relevant được chọn theo diện tích ±10%, cùng
  quận/loại, một nửa cùng đường; giá được rút rộng 0.5×–1.8× để giá trở nên vô thông tin.
  Đây là sửa lỗi phương pháp: phiên bản đầu định nghĩa relevant theo giá ⇒ tự tạo vòng lặp giá.
- Không dùng dữ liệu thật, không truy cập DB, không dùng TiniX.

## 2. Định nghĩa metric

| Metric | Định nghĩa |
|---|---|
| `P@k` | tỉ lệ ứng viên relevant trong top-k (trung bình trên cohort) |
| `R@k` | `hits / min(k, số relevant)` |
| `NDCG@k` | binary relevance, `log2(rank+2)` |
| `self_match_leak` | tỉ lệ kết quả có `entity_id == reference.entity_id` |
| `duplicate_rate` | tỉ lệ kết quả trùng entity trong cùng một top-k |
| `locality_error` | tỉ lệ kết quả sai quận |
| `type_error` | tỉ lệ kết quả sai loại hình |
| `tinix_leaks` | số dòng `TINIX_RESEARCH` xuất hiện trong kết quả public |

## 3. Các phương án so sánh

| | Mô tả |
|---|---|
| **A** | Baseline hiện tại: dải giá 0.4×–2.5×, `LIMIT` sau khi sắp theo độ gần giá, `notSelf` chỉ theo id, trọng số phẳng |
| **B** | Retrieval sửa: hard filter loại hình + quận **trước** `LIMIT`, không dải giá, entity resolution, `ORDER BY` ổn định |
| **C** | B + similarity theo loại hình, bỏ giá khỏi similarity, phạt coverage |
| **D** | C + ngưỡng evidence confidence ≥ 0.55 |

## 4. Kết quả

### k = 5 (28 cohort, seed 20261127, digest `6920347b30e89f79`)

| Phương án | P@5 | R@5 | NDCG@5 | self | dup | loc | type | tinix |
|---|---|---|---|---|---|---|---|---|
| A baseline | 0.779 | 0.779 | 0.813 | **0.029** | **0.043** | 0.000 | **0.107** | 0 |
| B retrieval+dedupe | 0.843 | 0.843 | 0.847 | **0.000** | **0.000** | 0.000 | **0.000** | 0 |
| C type-aware | 0.843 | 0.843 | **0.880** | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| D +confidence gate | 0.843 | 0.843 | 0.880 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |

### k = 10 (seed 20261127, digest `dffe16e592c1994f`)

| Phương án | P@10 | R@10 | NDCG@10 | self | dup | type |
|---|---|---|---|---|---|---|
| A baseline | 0.600 | 1.000 | 0.930 | **0.100** | **0.100** | **0.100** |
| B | 0.600 | 1.000 | 0.938 | 0.000 | 0.000 | 0.000 |
| C | 0.600 | 1.000 | **0.967** | 0.000 | 0.000 | 0.000 |
| D | 0.600 | 1.000 | 0.967 | 0.000 | 0.000 | 0.000 |

## 5. Diễn giải (trung thực)

1. **Baseline rò rỉ thật**: self-match 2.9% (k=5) → **10%** (k=10); duplicate 4.3% → 10%;
   sai loại hình 10.7% → 10%. Nguyên nhân khớp source: `notSelf` chỉ so id (F02), không dedupe,
   và `LIMIT` sau khi sắp theo giá để loại hình sai chiếm slot (F03).
2. **B là mức cải thiện lớn nhất**: P@5 +0.064, NDCG +0.034, và **loại bỏ hoàn toàn** ba loại lỗi.
3. **C chỉ thêm NDCG** (+0.033 ở cả k=5 và k=10), không thêm precision. C là phần "làm đúng thứ
   tự", không phải "tìm thêm được".
4. **D không có giá trị đo được**: ngưỡng 0.55 không loại ứng viên nào trên fixture này
   ⇒ confidence layer **chưa có bằng chứng**; đề xuất hoãn, không đưa vào bước 1.
5. **TiniX leak = 0 ở mọi phương án** vì benchmark loại `TINIX_RESEARCH` trước khi tính —
   đây là **mô hình hoá ranh giới bảo mật**, không phải bằng chứng rằng production đã an toàn.
   Production hiện **vẫn** truy vấn TiniX trên đường public (F01), chờ PR #46.

## 6. Reproducibility

```bash
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 10
python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5 --json   # digest + số liệu
```

- Deterministic theo `--seed` (mặc định 20261127); `digest` in ra để so sánh giữa các lần chạy.
- Không phụ thuộc DB, network, model artifact. Chỉ cần Python 3.11+.

## 7. Limitations

- Nhãn relevance do benchmark tự sinh ⇒ **không** suy ra Precision/Recall thị trường thật.
- Chưa có nhãn người thật; chưa đo trên cohort thật.
- Ngưỡng confidence (0.55) là giả định, chưa calibration.
- Entity resolution T3 (toạ độ) không được mô phỏng đầy đủ vì fixture không có toạ độ thật.
- Hành vi SQL thật (index, `LIMIT`, thời gian truy vấn) **chưa** đo — cần `EXPLAIN` ở Phase B.
