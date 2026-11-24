# SmartProp — News Backend V1: Triển khai

**Ngày:** 2026-11-24
**Branch:** `feature/news-backend-v1`
**Base:** `main @ d202792`
**Migration:** `V27__news_backend_v1.sql`

---

## 1. Tóm tắt

News Backend V1 cung cấp dữ liệu tin tức bất động sản thật cho Frontend PR #37, qua
ba endpoint công khai và một bộ API quản trị. Thu thập từ RSS/Atom bằng scheduler,
phân loại theo luật, chống trùng ở tầng DB.

**Không dùng LLM.** Không đụng XGBoost, RAG, AI Advisor. Không microservice mới.

---

## 2. Kiến trúc

```
RSS/Atom (nguồn đã duyệt quyền)
        ↓
NewsFeedFetcher   — SSRF guard, timeout, size limit, conditional GET
        ↓
NewsFeedParser    — RSS 2.0 / Atom, XXE-safe
        ↓
NewsText          — sanitize HTML, canonical URL, SHA-256
        ↓
NewsClassifier    — relevance filter + category + region (rule-based)
        ↓
MySQL             — unique (source_id, url_hash) chống trùng
        ↓
NewsService       — đọc, phân trang, lọc
        ↓
REST API          — /api/v1/news, /featured, /sources
```

**Package:** `vn.smartprop.modules.news` (theo convention `modules.<name>` của main).

| File | Trách nhiệm |
|---|---|
| `NewsSource` / `NewsArticle` / `NewsIngestionRun` | Entity |
| `NewsSourceRepository` / `NewsArticleRepository` / `NewsIngestionRunRepository` | Data access |
| `NewsUrlSafety` | SSRF guard |
| `NewsFeedFetcher` | HTTP client an toàn |
| `NewsFeedParser` | RSS/Atom parser, XXE-safe |
| `NewsText` | Sanitize + canonical URL + hash |
| `NewsClassifier` | Phân loại rule-based |
| `NewsIngestionService` | Điều phối thu thập |
| `NewsService` | Đọc public + admin |
| `NewsAdminService` | Quản trị nguồn/bài |
| `NewsController` / `NewsAdminController` | REST |
| `NewsScheduler` | Scheduler (mặc định tắt) |
| `NewsProperties` | Cấu hình |

---

## 3. Database

### Bảng

| Bảng | Cột | Vai trò |
|---|---:|---|
| `news_sources` | 22 | Nguồn tin + trạng thái quyền + conditional GET |
| `news_articles` | 19 | Bài viết (metadata + summary, không toàn văn) |
| `news_ingestion_runs` | 16 | Lịch sử đồng bộ |

### Ràng buộc then chốt

```sql
-- Chống trùng ở tầng DB, không chỉ kiểm tra exists trước INSERT.
UNIQUE KEY uq_news_articles_source_url (source_id, canonical_url_hash)
UNIQUE KEY uq_news_articles_source_external (source_id, external_id)

-- Enum hợp lệ.
CONSTRAINT ck_news_sources_rights CHECK (
  rights_review_status IN ('PENDING_REVIEW','APPROVED','REJECTED'))
CONSTRAINT ck_news_articles_status CHECK (
  publication_status IN ('VISIBLE','HIDDEN'))

-- Cascade: xoá nguồn xoá bài + lịch sử.
CONSTRAINT fk_news_articles_source FOREIGN KEY (source_id)
  REFERENCES news_sources (id) ON DELETE CASCADE
```

### Index

| Index | Phục vụ |
|---|---|
| `idx_news_sources_schedule` | Scheduler chọn nguồn đến hạn |
| `idx_news_articles_public` | Danh sách công khai |
| `idx_news_articles_category` | Lọc chuyên mục |
| `idx_news_articles_region` | Lọc Đà Nẵng |
| `idx_news_articles_featured` | Bài nổi bật |
| `idx_news_runs_source` | Lịch sử theo nguồn |

### Kết quả kiểm chứng

```
Flyway migrate: V27 applied, schema at v27
13/13 constraint test PASS (unique, FK, enum, cascade)
```

---

## 4. Migration lineage

**V27** — không trùng với V26 của PR #38.

### Thay đổi guard cần thiết

`MigrationLineageConfiguration` hardcode danh sách version và `target`. Đã cập nhật:

| Chỗ | Trước | Sau |
|---|---|---|
| `MigrationLineageConfiguration.target` | `"25"` | `"27"` |
| `Set.of(...)` pending check | đến `25` | đến `27` |
| `allowed` list | đến `25` | đến `27` |
| `pom.xml` flyway target | `25` | `27` |
| `application-hybrid-local-existing-v13.yml` | `'25'` | `'27'` |
| `...-staging.yml` | `'25'` | `'27'` |

**Quan trọng:** kiểm tra history đổi từ "khớp tuần tự từng vị trí" sang "mọi version
đã biết và tăng dần". Lý do: V26 (PR #38) và V27 (News) là hai nhánh độc lập — DB có
thể có V27 mà chưa có V26 nếu News merge trước. Guard cũ sẽ từ chối trường hợp đó.

---

## 5. API contract

Khớp chính xác Frontend PR #37.

### `GET /api/v1/news`

| Param | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `category` | string | — | Nhãn tiếng Việt hoặc enum |
| `q` | string | — | Tìm trong title/summary, tối đa 200 ký tự |
| `sort` | string | `newest` | `newest` / `oldest` |
| `page` | int | 0 | |
| `size` | int | 12 | Clamp tối đa 50 |

Response:

```json
{
  "items": [{
    "id": "uuid",
    "title": "Đà Nẵng đấu thầu khu đô thị 19.000 tỷ",
    "summary": "...",
    "category": "Thị trường BĐS",
    "region": "Đà Nẵng",
    "articleUrl": "https://vnexpress.net/...",
    "sourceName": "VnExpress Bất động sản",
    "sourceUrl": "https://vnexpress.net",
    "publishedAt": "2026-11-24T08:00:00Z",
    "fetchedAt": "2026-11-24T09:00:00Z",
    "locationTags": "da nang"
  }],
  "page": 0, "size": 12, "totalElements": 49, "totalPages": 5,
  "lastUpdatedAt": "2026-11-24T09:00:00Z",
  "refreshing": false,
  "sources": [{ "id": "...", "name": "...", "feedUrl": "...",
                "count": 49, "lastSuccessAt": "...", "status": "AVAILABLE" }]
}
```

### `GET /api/v1/news/featured`

Cùng cấu trúc. Xếp hạng: `featured` → Đà Nẵng → mới nhất.

### `GET /api/v1/news/sources`

```json
{ "sources": [...], "lastUpdatedAt": "..." }
```

**Không trả:** `rightsReference`, `lastError`, `httpEtag`, IP nội bộ, stack trace.

### Admin API (chỉ ADMIN)

| Endpoint | Method |
|---|---|
| `/api/v1/admin/news/sources` | GET, POST |
| `/api/v1/admin/news/sources/{id}` | GET, PATCH |
| `/api/v1/admin/news/sources/{id}/sync` | POST |
| `/api/v1/admin/news/articles` | GET |
| `/api/v1/admin/news/articles/{id}/visibility` | PATCH |
| `/api/v1/admin/news/articles/{id}/featured` | PATCH |
| `/api/v1/admin/news/ingestion-runs` | GET |
| `/api/v1/admin/news/stats` | GET |

**Không có endpoint nhận URL tùy ý để fetch.**

---

## 6. Nguồn tin — trạng thái thật

Khảo sát 2026-11-24:

| Nguồn | Feed URL | HTTP | Format | Items | Quyền |
|---|---|---|---:|---:|---|
| VnExpress BĐS | `https://vnexpress.net/rss/bat-dong-san.rss` | 200 | RSS | 60 | **PENDING_REVIEW** |
| VnExpress Kinh doanh | `https://vnexpress.net/rss/kinh-doanh.rss` | 200 | RSS | 60 | **PENDING_REVIEW** |
| VietnamNet BĐS | `https://vietnamnet.vn/rss/bat-dong-san.rss` | 200 | RSS | 1000 | **PENDING_REVIEW** |
| Tuổi Trẻ BĐS | `https://tuoitre.vn/rss/bat-dong-san.rss` | 404 | — | 0 | — |
| Thanh Niên BĐS | `https://thanhnien.vn/rss/bat-dong-san.rss` | 404 | — | 0 | — |
| Báo Đà Nẵng | `https://baodanang.vn/rss/home.rss` | 403 | — | 0 | — |
| Bộ Xây dựng | `https://moc.gov.vn/rss/tin-tuc.rss` | ERR | — | 0 | — |

**HTTP 200 + RSS hợp lệ KHÔNG phải bằng chứng quyền tái bản nội dung.** Mọi nguồn vẫn
`PENDING_REVIEW` cho đến khi có văn bản cho phép. Không nguồn nào được bật.

---

## 7. Ingestion — kết quả thật

Chạy với VnExpress BĐS trên DB cô lập (`127.0.0.1:3307`):

```
Lần 1: SUCCESS  received=60  inserted=49  updated=0   duplicate=0  rejected=11
Lần 2: SUCCESS  received=60  inserted=0   updated=49  duplicate=0  rejected=11
```

**Idempotent:** lần 2 không chèn mới, chỉ cập nhật `lastSeenAt`/`fetchedAt`.

**11 bài bị loại:** không liên quan bất động sản (relevance filter hoạt động).

**Phân bố:**

| Category | Region | Số bài |
|---|---|---:|
| MARKET | VIETNAM | 17 |
| RESIDENTIAL | VIETNAM | 16 |
| PLANNING | VIETNAM | 4 |
| RESIDENTIAL | CENTRAL | 3 |
| MARKET | CENTRAL | 3 |
| **MARKET** | **DA_NANG** | **2** |
| PLANNING | CENTRAL | 1 |
| PROJECTS | VIETNAM | 1 |
| PROJECTS | CENTRAL | 1 |
| LEGAL | CENTRAL | 1 |

**Bài Đà Nẵng thật:**

- "Đà Nẵng tìm nhà đầu tư khu đô thị Tây Bắc sườn đồi 9.900 tỷ" — MARKET / DA_NANG
- "Đà Nẵng đấu thầu quốc tế khu đô thị gần 19.000 tỷ đồng" — MARKET / DA_NANG

**`publishedAt ≈ fetchedAt`: 0 bài** — không gán sai thời điểm.

---

## 8. Security

| Hạng mục | Cơ chế | Test |
|---|---|---|
| **SSRF** | `NewsUrlSafety`: chặn loopback/private/link-local/CGNAT/metadata, IPv4+IPv6, IPv4-mapped, kiểm tra lại mỗi redirect | 15 test PASS |
| **XXE** | `disallow-doctype-decl`, tắt external entities/DTD, `FEATURE_SECURE_PROCESSING`, EntityResolver rỗng | 2 test PASS |
| **XSS** | `NewsText.clean`: bỏ script/style kèm nội dung, bỏ mọi tag, giải entity, không trả HTML | 3 test PASS |
| **SQL injection** | JPA parameterized, enum validation, LIKE escape, page size clamp | 1 test PASS |
| **Authorization** | `access.admin()` kiểm tra role trong DB, không tin JWT claim | 5 test PASS |
| **Rate limit** | Tôn trọng 429 + `Retry-After`, không retry vô hạn | Code path |
| **Concurrency** | Unique constraint ở DB, bắt `DataIntegrityViolationException` | 1 test PASS |

**Giới hạn đã biết:** DNS rebinding vẫn có thể xảy ra (kiểm tra DNS và kết nối là hai
thời điểm). Lớp phòng thủ thứ hai: chỉ fetch URL đã lưu trong `news_sources`, không có
endpoint nhận URL tùy ý.

---

## 9. Cấu hình

```yaml
app:
  news:
    enabled: true                 # API đọc
    ingestion-enabled: false      # MẶC ĐỊNH TẮT
    allow-http: false             # chỉ https
    connect-timeout-ms: 5000
    read-timeout-ms: 15000
    max-feed-bytes: 2097152
    max-redirects: 3
    max-page-size: 50
    featured-limit: 6
    user-agent: "SmartPropNewsBot/1.0 (+https://smartprop.vn/bot)"
```

**Mặc định an toàn:** ingestion tắt, không nguồn nào được bật, không tự gọi mạng.

---

## 10. Test

| Suite | PASS | FAIL | NOT_RUN |
|---|---:|---:|---:|
| Backend unit (toàn bộ) | **237** | 0 | 0 |
| — `NewsFeedParserTest` | 10 | 0 | 0 |
| — `NewsUrlSafetyTest` | 15 | 0 | 0 |
| — `NewsTextAndClassifierTest` | 24 | 0 | 0 |
| HTTP integration (`NewsApiIT`) | **22** | 0 | 0 |
| MySQL constraint | **13** | 0 | 0 |
| Live ingestion (`NewsLiveIngestionIT`) | **1** | 0 | 0 |
| Flyway migrate | **V27 applied** | 0 | 0 |
| Frontend contract | — | — | **NOT_RUN** |
| Playwright E2E | — | — | **NOT_RUN** |

### Lỗi đã phát hiện và sửa trong quá trình test

| Lỗi | Nguyên nhân | Sửa |
|---|---|---|
| `foldForMatch("Đà Nẵng")` → `"?à Nẵng"` | `Đ` (U+0110) không decompose bằng NFD | Thay `Đ/đ` → `D/d` trước NFD |
| `parseDate("Tue, 24 Nov 2026 08:00:00 +0700")` → null | `RFC_1123_DATE_TIME` chỉ nhận `+07:00` | Thêm pattern RFC 822 với `Z` |
| Test date dùng "Mon" cho 2026-11-24 (là Tuesday) | Test data sai | Sửa thành "Tue" |
| `canonical_url_hash` CHAR vs VARCHAR | Entity thiếu `@JdbcTypeCode(SqlTypes.CHAR)` | Thêm annotation |
| `fetch_interval_minutes` SMALLINT vs int | Entity khai `int` | Đổi sang `short` |
| Flyway không thấy V27 | `pom.xml` `<target>25</target>` thắng profile | Sửa pom target |
| Lineage guard từ chối V27 khi thiếu V26 | Kiểm tra khớp tuần tự từng vị trí | Đổi sang "mọi version đã biết, tăng dần" |

---

## 11. Triển khai

### Runbook

1. **Backup** database trước khi migrate.
2. Kiểm tra Flyway lineage: `flyway:info` — schema version hiện tại.
3. Xác minh PR #38 (V26) đã merge hay chưa. Nếu chưa, V27 vẫn chạy được (guard đã sửa).
4. Test migration trên bản sao cô lập trước.
5. `flyway:migrate` — áp dụng V27.
6. Khởi động Backend với `app.news.ingestion-enabled=false` (mặc định).
7. Kiểm tra `GET /api/v1/news` trả 200 với `items: []`.
8. Tạo nguồn qua `POST /api/v1/admin/news/sources` — sẽ ở `PENDING_REVIEW`.
9. **Chỉ sau khi có văn bản cho phép**: `PATCH` với `rightsReviewStatus=APPROVED` +
   `rightsReference`, rồi `enabled=true`.
10. Bật `app.news.ingestion-enabled=true` khi được phép.
11. Kiểm tra `GET /api/v1/admin/news/ingestion-runs`.
12. Tích hợp PR #37.

### Rollback

1. `app.news.ingestion-enabled=false` — dừng thu thập.
2. Revert code nếu cần.
3. **Giữ schema và dữ liệu** để bảo toàn lịch sử.
4. `DROP TABLE` chỉ khi có phê duyệt riêng.

---

## 12. Tích hợp PR #37

### Trạng thái

| Hạng mục | Trạng thái |
|---|---|
| Backend News tồn tại | **CÓ** |
| Ba endpoint công khai | **HOẠT ĐỘNG** |
| JSON contract khớp PR #37 | **CÓ** (22 test) |
| Dữ liệu thật | **CÓ** (49 bài từ VnExpress) |
| Nguồn được phê duyệt | **KHÔNG** — tất cả PENDING_REVIEW |
| Scheduler | **HOẠT ĐỘNG** nhưng mặc định tắt |
| News page test với Backend thật | **NOT_RUN** |
| 5 ảnh quận | **BLOCKER** của PR #37 |
| PR #38/#39 merge | **CHƯA** |

### Các bước tích hợp (sau khi PR #38/#39 merge)

1. Merge PR #38 (coordinate provenance).
2. Merge PR #39 (admin coordinate review).
3. Merge News Backend V1.
4. Đồng bộ `main` vào PR #37.
5. Giữ route `/news` và `/admin/coordinate-review`.
6. Giữ `CoordinateStatusPanel`.
7. Kết nối News API — không cần sửa Frontend, contract đã khớp.
8. Xử lý 5 ảnh quận chưa rõ quyền.
9. Chạy regression với Backend thật.
10. Chạy E2E.
11. Chuyển PR #37 sang Ready.

---

## 13. Giới hạn

| Hạng mục | Trạng thái |
|---|---|
| Backend News V1 | **IMPLEMENTED + TESTED** |
| RSS/Atom ingestion | **IMPLEMENTED + TESTED** (live) |
| SSRF/XXE/XSS protection | **IMPLEMENTED + TESTED** |
| Deduplication | **IMPLEMENTED + TESTED** |
| Scheduler | **IMPLEMENTED**, mặc định tắt |
| Public API | **IMPLEMENTED + TESTED** |
| Admin API | **IMPLEMENTED + TESTED** |
| Nguồn được phê duyệt quyền | **KHÔNG CÓ** — cần văn bản pháp lý |
| Frontend contract test | **NOT_RUN** |
| Playwright E2E | **NOT_RUN** |
| Admin News UI | **NOT_IMPLEMENTED** — PR riêng |
| AI summarization | **NOT_IMPLEMENTED** — roadmap V2 |
| Ảnh báo chí | **KHÔNG BẬT** — `NEWS_IMAGE_PERMISSIONS = {}` |

---

## 14. Quyết định thiết kế

| Quyết định | Lý do |
|---|---|
| Rule-based classification, không LLM | Không chi phí token định kỳ; deterministic, test được |
| Unique constraint ở DB, không chỉ check exists | Chống race condition khi hai ingestion chạy đồng thời |
| Fetch ngoài transaction | Không giữ DB lock trong lúc chờ network |
| `publishedAt` NULL khi feed không cung cấp | Không gán `fetchedAt` giả làm ngày đăng |
| Nguồn mới luôn PENDING_REVIEW + disabled | Không tự động thu thập khi chưa duyệt quyền |
| APPROVED bắt buộc có `rightsReference` | Không duyệt quyền mà không có căn cứ |
| Không endpoint nhận URL tùy ý | SSRF không thể khai thác qua API |
| Chỉ lưu metadata + summary | Không lưu toàn văn, không vi phạm bản quyền |
| Không lưu ảnh báo chí | Tôn trọng `newsImagePolicy.js` của PR #37 |
| Scheduler mặc định tắt | Không tự gọi mạng ngoài khi chưa cấu hình |
