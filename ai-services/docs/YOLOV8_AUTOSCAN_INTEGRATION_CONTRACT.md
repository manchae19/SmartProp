# YOLOv8 → Auto-Scan integration contract (design only)

Status: **DESIGN ONLY — no migration, no schema change, no write to MySQL 3306.**

This document specifies how YOLOv8 object analysis would join the existing
Auto-Scan pipeline. Nothing here is implemented against the database yet; the
MVP stops at the standalone service, the API and the React demo.

## 1. Why a separate table and not a column on `property_image_scan`

`property_image_scan` (V21) answers one question per image: *is this photo a
duplicate of another listing's photo?* It has a `UNIQUE KEY` on
`property_image_id`, one row per image, and its `classification` column is
constrained to duplicate verdicts.

Object analysis answers a different question with a different lifecycle:

| | duplicate scan | object analysis |
|---|---|---|
| Trigger | upload / submit | upload / submit (same) |
| Failure mode | `PENDING_RETRY`, retried | `PENDING_RETRY`, retried |
| Re-run when | image bytes change | model version changes **or** image bytes change |
| Cardinality | 1 row per image | 1 row per image **per model version** |
| Payload | match list | detection list with boxes |

Re-running analysis after a model upgrade must not destroy the previous
verdict, because a reviewer may need to see what the old model reported. A
`UNIQUE(property_image_id)` column cannot express that; a versioned table can.

## 2. Proposed schema (NOT applied)

```sql
-- Proposed V22. Reviewed but NOT executed against any database.
CREATE TABLE property_image_analysis (
    id CHAR(36) NOT NULL,
    property_id CHAR(36) NOT NULL,
    property_image_id CHAR(36) NOT NULL,
    analysis_status VARCHAR(24) NOT NULL,      -- PENDING|SCANNING|COMPLETED|PENDING_RETRY
    algorithm_version VARCHAR(32) NOT NULL,    -- yolov8n-property-v1
    model_version VARCHAR(64) NOT NULL,        -- yolov8n@<sha256-prefix>
    detection_count INT NOT NULL DEFAULT 0,
    detections JSON NOT NULL,                  -- [{cocoId,cocoName,label,group,confidence,box,boxPixels}]
    counts_by_label JSON NOT NULL,             -- {"Giường":1,"Ghế":2}
    image_width INT NULL,
    image_height INT NULL,
    image_format VARCHAR(16) NULL,
    image_sha256 CHAR(64) NULL,
    inference_ms DECIMAL(10,2) NULL,
    error_code VARCHAR(64) NULL,
    analyzed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    UNIQUE KEY uq_image_analysis_version (property_image_id, model_version),
    KEY ix_image_analysis_property (property_id, analysis_status),
    KEY ix_image_analysis_status (analysis_status, detection_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

Notes that matter for review:

* `UNIQUE(property_image_id, model_version)` — one verdict per image per model,
  so a model upgrade adds a row instead of overwriting history.
* No foreign keys, matching the existing `property_image_scan` decision: the
  scan tables are evidence logs, and a cascade delete would silently destroy
  audit history.
* `detections` is JSON because the shape is model-specific and will change with
  the model; the stable, queryable facts (`detection_count`, `counts_by_label`)
  are promoted to columns.
* `image_sha256` lets a later job prove the analysed bytes are the current bytes
  without re-reading storage.

## 3. Pipeline placement

```text
POST /api/v1/properties/{id}/images
  └─ PropertyMediaService.upload()            (unchanged, commits first)
       ├─ PropertyImageScanService.schedule()      (existing, duplicate scan)
       └─ PropertyImageAnalysisService.schedule()  (new, object analysis)
             └─ POST http://127.0.0.1:18002/image-analysis/analyze
```

The two schedulers must be independent:

* separate executors, so a slow YOLO inference cannot delay duplicate scanning;
* separate in-flight locks keyed by `propertyId`;
* separate failure states — a YOLO failure must never mark a duplicate scan as
  clean, and vice versa.

Ordering is **not** a hard dependency. Duplicate scanning is cheap and already
proven; object analysis is the newer, heavier step. Running them concurrently
keeps the existing latency profile for the duplicate verdict.

## 4. Backend service contract

```java
@Service
public class PropertyImageAnalysisService {
    static final String ALGORITHM_VERSION = "yolov8n-property-v1";

    @Async("imageAnalysisExecutor")
    public void schedule(String propertyId);

    public AnalysisView view(String propertyId);
}
```

Rules carried over from `PropertyImageScanService`, because they are the
lessons that made Auto-Scan trustworthy:

1. **Never report a clean result on failure.** A failed call writes
   `PENDING_RETRY` plus `error_code`; it never writes `detection_count = 0`.
2. **Skip only when genuinely fresh.** Re-analyse when the image changed
   (`scannedAt < image.updatedAt`) or the model version changed.
3. **Bounded batch.** Reuse the existing 30-image ceiling; a listing with more
   images is skipped rather than partially analysed.
4. **Read-only on storage.** Bytes are read through the existing
   `LocalFileStore` / `CloudinaryImageDelivery` paths; nothing is written back.
5. **No automatic moderation action.** A detection count never rejects,
   publishes or flags a listing. It is evidence for a human.

## 5. API surface (proposed)

```text
GET  /api/v1/properties/{id}/image-analysis        public if listing public, else owner/ADMIN
POST /api/v1/properties/{id}/image-analysis/retry  owner/ADMIN
GET  /api/v1/admin/image-analysis                  ADMIN, listings with detections
```

Response shape mirrors the standalone service so the React component can be
reused unchanged:

```json
{
  "propertyId": "...",
  "status": "COMPLETED",
  "modelVersion": "yolov8n@f59b3d833e2f",
  "images": [
    {
      "imageId": "...",
      "detectionCount": 10,
      "countsByLabel": {"Ghế": 2, "Cây cảnh": 5},
      "detections": [{"cocoName": "chair", "label": "Ghế", "confidence": 0.92, "box": [0.1,0.2,0.3,0.4]}],
      "inferenceMs": 45.2
    }
  ],
  "limitations": ["..."]
}
```

## 6. Security review points

* The vision service binds `127.0.0.1` only and is never exposed publicly.
* It accepts bytes, never a URL — the same SSRF reasoning as the duplicate
  scanner. There is no field a caller could use to make the server fetch an
  arbitrary address.
* Uploads are capped at 8 MiB, 40 megapixels and 12 000 px per edge, checked
  from the image header before any pixel is decoded.
* Rate limit is 20 analyses/minute per client, with a single inference slot, so
  one caller cannot saturate the CPU that also serves XGBoost and RAG.
* No image is persisted by the vision service; only the derived JSON would be
  stored, and only after the migration above is approved.

## 7. What is deliberately NOT in this MVP

| Item | Reason |
|---|---|
| V22 migration | Requires approval; the task forbids production migration. |
| Backend scheduler + entity | Depends on V22; would be dead code today. |
| Listing Detail panel | Depends on the backend endpoint above. |
| Auto-trigger on upload | Would write to MySQL 3306, which is forbidden here. |
| Custom-trained model | Task forbids training; COCO pretrained only. |
| Bathtub/wardrobe/AC detection | COCO has no such classes; claiming them would be false. |

## 8. Activation checklist (when approved)

1. Review and apply V22 on an isolated clone first; verify `flyway:validate`.
2. Add `PropertyImageAnalysisService` + executor + controller behind a flag
   (`APP_IMAGE_ANALYSIS_ENABLED=false` by default).
3. Point `APP_IMAGE_ANALYSIS_BASE_URL` at `127.0.0.1:18002`.
4. Add the vision service to `ops/start-smartprop-local.ps1` with the same
   health-gate pattern used for imagecheck 18001.
5. Run the Auto-Scan regression suite plus the new analysis E2E before enabling
   the flag in any shared environment.
