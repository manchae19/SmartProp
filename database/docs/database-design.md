# SmartProp database design

Implemented: 32 ERD tables + 2 explicitly documented YOLOv8 tables. MySQL target **8.4.9**; SQL checks performed on available **8.0.43**, not the target container.

Source: SmartProp-ERD-full.png and proposal v1.1, FR-01..FR-15. No DBML found. PNG does not expose enum values, all keys, defaults or actions; these are implementation proposals, not asserted original requirements.

## Migration order

- V1: existing users/auth_sessions; file untouched.
- V2: additive accounts, roles, role bridge, reset tokens.
- V3: property, media, favorite, POI, stats.
- V4: provenance, datasets, models/config/deployments.
- V5: tasks, attempts, outbox, valuation, similarity.
- V6: reports, audit, notifications, flags/moderation.
- V7: YOLOv8 successful results and detections.

## Common conventions

- New entity IDs: application-generated canonical UUID strings in CHAR(36), ascii_bin. No silent UUID syntax validation is claimed; validate UUID input at API boundary.
- Existing user IDs and all user foreign keys stay BIGINT; existing session IDs stay VARCHAR(36).
- InnoDB/utf8mb4; timestamp instants are DATETIME(6), UTC. Defaults use UTC_TIMESTAMP(6); service supplies updated_at on edits.
- Every explicit FK is RESTRICT/RESTRICT; legacy V1 FKs retain their original behavior. Retention/deletion is a separate reviewed workflow, not cascades.
- Enum-like states use VARCHAR + CHECK. The database checks membership, not valid state transitions.
- Monetary fields use DECIMAL; scores/model values use DOUBLE.
- Schema reference includes exact nullable/default/PK/FK/CHECK/index definitions: [schema-reference.sql](schema-reference.sql).

## JSON contracts

- declared_amenities/amenities: array of canonical supported codes, e.g. ["SOFA","TV"]. Service owns approved taxonomy.
- shap_values: object with feature_names, feature_values, contributions arrays of matching length; base_value/model_output/output_scale are stored separately.
- input_snapshot: normalized property attributes, content version and immutable image IDs/checksums; no passwords, tokens or private legal-document content.
- model metrics/feature_schema/runtime_metadata, config parameters, validation_report: versioned objects with documented keys per model.
- comparison: array of {amenity_code,status,evidence_image_ids}; statuses VISUALLY_CONFIRMED, NOT_DETECTED, UNSUPPORTED. NOT_DETECTED is not proof of absence.
- bounding_box: {x_min,y_min,x_max,y_max}, each 0..1, max >= min.
- SQL validates JSON syntax and array shape where explicit CHECK exists; services validate these semantic schemas.

## Spatial contract

POINT SRID 4326. API uses longitude,latitude; construct via ST_GeomFromText('POINT(lon lat)',4326,'axis-order=long-lat'). Read with ST_Longitude/ST_Latitude. ST_Distance_Sphere returns meters. Spatial MBR prefilter plus exact distance is needed for radius search; distance alone does not guarantee index use. Separate p95 benchmarking remains pending.

## Per-table definitions

### ai_config_versions

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `version VARCHAR(50) NOT NULL`
- `parameters JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `approved_by BIGINT NOT NULL`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_config_approver FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_config_kind_version (kind,version)`
- `UNIQUE KEY uq_config_kind_id (kind,id)`
- `CONSTRAINT ck_config_kind CHECK (kind IN ('VALUATION', 'SIMILARITY', 'AMENITY'))`

### ai_deployments

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `model_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `config_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `updated_by BIGINT NOT NULL`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `PRIMARY KEY (kind)`

Constraints and indexes:

- `CONSTRAINT fk_deployment_model FOREIGN KEY (kind,model_version_id) REFERENCES model_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_deployment_config FOREIGN KEY (kind,config_version_id) REFERENCES ai_config_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_deployment_updater FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_deployment_kind CHECK (kind IN ('VALUATION', 'SIMILARITY', 'AMENITY'))`

### ai_task_attempts

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `attempt_no SMALLINT NOT NULL`
- `lease_token CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `worker_id VARCHAR(150) NOT NULL`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'RUNNING'`
- `started_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `lease_expires_at DATETIME(6) NOT NULL`
- `finished_at DATETIME(6)`
- `error_code VARCHAR(100)`
- `error_message TEXT`

Constraints and indexes:

- `CONSTRAINT fk_attempt_task FOREIGN KEY (task_id) REFERENCES ai_tasks (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_attempt_number (task_id,attempt_no)`
- `UNIQUE KEY uq_attempt_task_id (task_id,id)`
- `UNIQUE KEY uq_attempt_lease (lease_token)`
- `CONSTRAINT ck_attempt_status CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED'))`
- `CONSTRAINT ck_attempt_number CHECK (attempt_no BETWEEN 1 AND 2)`
- `CONSTRAINT ck_attempt_lease_time CHECK (lease_expires_at > started_at)`
- `KEY ix_attempt_expiry (status,lease_expires_at)`

### ai_tasks

UUID IDs, unique idempotency key; maximum two attempts (initial + one retry) per proposal. Snapshot creation and content version consistency are application responsibilities.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `requested_by BIGINT`
- `task_type VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `execution_mode VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `model_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `config_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `input_content_version INT NOT NULL`
- `input_snapshot JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `idempotency_key VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'QUEUED'`
- `attempt_count SMALLINT NOT NULL DEFAULT 0`
- `max_attempts SMALLINT NOT NULL DEFAULT 2`
- `error_code VARCHAR(100)`
- `error_message TEXT`
- `finished_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_task_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_task_requester FOREIGN KEY (requested_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_task_model FOREIGN KEY (task_type,model_version_id) REFERENCES model_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_task_config FOREIGN KEY (task_type,config_version_id) REFERENCES ai_config_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_task_idempotency (idempotency_key)`
- `UNIQUE KEY uq_task_type_id (task_type,id)`
- `UNIQUE KEY uq_task_property_id (id,property_id)`
- `CONSTRAINT ck_task_kind CHECK (task_type IN ('VALUATION', 'SIMILARITY', 'AMENITY'))`
- `CONSTRAINT ck_task_mode CHECK (execution_mode IN ('SYNC', 'ASYNC'))`
- `CONSTRAINT ck_task_status CHECK (status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED'))`
- `CONSTRAINT ck_task_version CHECK (input_content_version > 0)`
- `CONSTRAINT ck_task_attempts CHECK (attempt_count >= 0 AND max_attempts BETWEEN 1 AND 2 AND attempt_count <= max_attempts)`
- `KEY ix_task_queue (status,execution_mode,created_at)`
- `KEY ix_task_property (property_id,task_type,input_content_version,created_at)`

### amenity_analysis_results

Explicit extra table beyond the 32-table ERD. Stores a result even if no object is detected; comparison is an array.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `result_kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'AMENITY'`
- `declared_amenities_snapshot JSON NOT NULL DEFAULT (JSON_ARRAY())`
- `comparison JSON NOT NULL DEFAULT (JSON_ARRAY())`
- `latency_ms INT NOT NULL`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_amenity_task_kind FOREIGN KEY (result_kind,task_id) REFERENCES ai_tasks (task_type,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_amenity_attempt FOREIGN KEY (task_id,attempt_id) REFERENCES ai_task_attempts (task_id,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_amenity_task_property FOREIGN KEY (task_id,property_id) REFERENCES ai_tasks (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_amenity_attempt (attempt_id)`
- `UNIQUE KEY uq_amenity_property (id,property_id)`
- `CONSTRAINT ck_amenity_kind CHECK (result_kind='AMENITY')`
- `CONSTRAINT ck_amenity_latency CHECK (latency_ms >= 0)`
- `CONSTRAINT ck_amenity_snapshot_array CHECK (JSON_TYPE(declared_amenities_snapshot)='ARRAY')`
- `CONSTRAINT ck_amenity_comparison_array CHECK (JSON_TYPE(comparison)='ARRAY')`

### amenity_detections

Explicit extra table. Composite keys enforce that analysis and image belong to the same property. bounding_box is normalized xyxy JSON; shape/order are validated by service.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `analysis_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `image_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `class_name VARCHAR(100) NOT NULL`
- `confidence DOUBLE NOT NULL`
- `bounding_box JSON`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_detection_analysis FOREIGN KEY (analysis_id,property_id) REFERENCES amenity_analysis_results (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_detection_image FOREIGN KEY (image_id,property_id) REFERENCES property_images (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_detection_confidence CHECK (confidence BETWEEN 0 AND 1)`
- `KEY ix_detection_class (analysis_id,class_name)`

### audit_logs

Contains nullable UUID entity_id plus added entity_numeric_id for legacy user IDs. No cascading deletion. Secrets and sensitive legal documents must be redacted before insertion.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `actor_id BIGINT`
- `actor_type VARCHAR(15) NOT NULL`
- `request_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `action VARCHAR(100) NOT NULL`
- `entity_type VARCHAR(50) NOT NULL`
- `entity_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `entity_numeric_id BIGINT`
- `old_values JSON`
- `new_values JSON`
- `ip_address VARCHAR(45) CHARACTER SET ascii COLLATE ascii_bin`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_audit_actor_type CHECK (actor_type IN ('USER', 'SYSTEM'))`
- `KEY ix_audit_entity (entity_type,entity_id,created_at)`
- `KEY ix_audit_actor (actor_id,created_at)`
- `KEY ix_audit_request (request_id)`

### auth_sessions

V1 VARCHAR(36) preserved. Existing access-token-only login continues using revoked boolean. Nullable refresh_token_hash is reserved; this database change does not implement refresh-token rotation.

Existing V1 plus additive V2 columns; see schema-reference.sql and migration V2.

### data_sources

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `name VARCHAR(255) NOT NULL`
- `source_type VARCHAR(30) NOT NULL`
- `base_url TEXT`
- `license_basis TEXT NOT NULL`
- `permitted_use TEXT NOT NULL`
- `retention_policy TEXT`
- `reviewed_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:



### dataset_memberships

Composite FK enforces record/entity_group identity. Preventing one group from appearing across splits, observation-window eligibility and freezing require locked service transactions; not falsely claimed as CHECK guarantees.

Columns:

- `dataset_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `record_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `entity_group_key VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `split VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `PRIMARY KEY (dataset_version_id,record_id)`

Constraints and indexes:

- `CONSTRAINT fk_membership_version FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_membership_record FOREIGN KEY (record_id,entity_group_key) REFERENCES dataset_records (id,entity_group_key) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_membership_split CHECK (split IN ('TRAIN', 'VALIDATION', 'TEST'))`
- `KEY ix_membership_split (dataset_version_id,split,entity_group_key)`

### dataset_records

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `source_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `source_record_key VARCHAR(255) NOT NULL`
- `source_url TEXT`
- `observed_at DATETIME(6) NOT NULL`
- `collected_at DATETIME(6) NOT NULL`
- `country_code CHAR(2) NOT NULL DEFAULT 'VN'`
- `city VARCHAR(100) NOT NULL`
- `target_type VARCHAR(30) NOT NULL`
- `normalized_price_vnd DECIMAL(18,2)`
- `transaction_type VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `price_unit VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `features JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `raw_storage_key TEXT`
- `quality_status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'PENDING'`
- `rejection_reason TEXT`
- `entity_group_key VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `content_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`

Constraints and indexes:

- `CONSTRAINT fk_record_source FOREIGN KEY (source_id) REFERENCES data_sources (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_record_source (source_id,source_record_key,content_hash)`
- `UNIQUE KEY uq_record_group (id,entity_group_key)`
- `CONSTRAINT ck_record_price CHECK (normalized_price_vnd IS NULL OR normalized_price_vnd >= 0)`
- `CONSTRAINT ck_record_transaction CHECK (transaction_type IN ('SALE', 'RENT'))`
- `CONSTRAINT ck_record_price_unit CHECK (price_unit IN ('TOTAL', 'PER_MONTH', 'PER_YEAR', 'PER_DAY'))`
- `CONSTRAINT ck_record_quality CHECK (quality_status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'DUPLICATE'))`
- `KEY ix_record_time (city,quality_status,observed_at)`
- `KEY ix_record_group (entity_group_key)`

### dataset_versions

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `name VARCHAR(150) NOT NULL`
- `version VARCHAR(50) NOT NULL`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'DRAFT'`
- `window_start DATE NOT NULL`
- `train_end DATE NOT NULL`
- `validation_end DATE NOT NULL`
- `window_end DATE NOT NULL`
- `manifest_key TEXT`
- `checksum CHAR(64) CHARACTER SET ascii COLLATE ascii_bin`
- `preprocessing_version VARCHAR(100) NOT NULL`
- `validation_report JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `created_by BIGINT NOT NULL`
- `frozen_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_dataset_creator FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_dataset_version (name,version)`
- `CONSTRAINT ck_dataset_status CHECK (status IN ('DRAFT', 'VALIDATED', 'FROZEN', 'RETIRED'))`
- `CONSTRAINT ck_dataset_window CHECK (window_start <= train_end AND train_end < validation_end AND validation_end < window_end)`

### image_embeddings

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `index_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `image_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `faiss_vector_id BIGINT NOT NULL`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `PRIMARY KEY (index_version_id,image_id)`

Constraints and indexes:

- `CONSTRAINT fk_embedding_index FOREIGN KEY (index_version_id) REFERENCES image_index_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_embedding_image FOREIGN KEY (image_id) REFERENCES property_images (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_embedding_vector (index_version_id,faiss_vector_id)`
- `CONSTRAINT ck_vector_id CHECK (faiss_vector_id >= 0)`

### image_index_versions

FAISS artifact is external, referenced by artifact_key/hash. Vector IDs are stored in image_embeddings; raw vectors are not claimed to be in MySQL.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `embedding_model_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `embedding_kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'SIMILARITY'`
- `version VARCHAR(100) NOT NULL`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'BUILDING'`
- `artifact_key TEXT NOT NULL`
- `artifact_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin`
- `vector_dimension INT NOT NULL`
- `metric VARCHAR(30) NOT NULL`
- `preprocessing JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `image_count BIGINT NOT NULL DEFAULT 0`
- `ready_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_index_model_kind FOREIGN KEY (embedding_kind,embedding_model_id) REFERENCES model_versions (kind,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_index_version (embedding_model_id,version)`
- `CONSTRAINT ck_index_kind CHECK (embedding_kind='SIMILARITY')`
- `CONSTRAINT ck_index_dimension CHECK (vector_dimension > 0)`
- `CONSTRAINT ck_index_count CHECK (image_count >= 0)`
- `CONSTRAINT ck_index_status CHECK (status IN ('BUILDING', 'READY', 'FAILED', 'RETIRED'))`
- `CONSTRAINT ck_index_metric CHECK (metric IN ('COSINE', 'L2', 'INNER_PRODUCT'))`

### image_matches

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `run_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `index_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `matched_image_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- ``rank` SMALLINT NOT NULL`
- `similarity_score DOUBLE NOT NULL`
- `PRIMARY KEY (run_id,matched_image_id)`

Constraints and indexes:

- `CONSTRAINT fk_match_run_index FOREIGN KEY (run_id,index_version_id) REFERENCES image_similarity_runs (id,index_version_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_match_embedding FOREIGN KEY (index_version_id,matched_image_id) REFERENCES image_embeddings (index_version_id,image_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_match_rank (run_id,`rank`)`
- `CONSTRAINT ck_match_rank CHECK (`rank` > 0)`
- `CONSTRAINT ck_match_score CHECK (similarity_score BETWEEN -1 AND 1)`

### image_similarity_runs

Threshold/scores are normalized cosine similarity in [-1,1]. The service must transform other FAISS metrics appropriately; embedding index must use the task model, enforced in service.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `index_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `source_image_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `result_kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'SIMILARITY'`
- `threshold DOUBLE NOT NULL`
- `top_k SMALLINT NOT NULL`
- `latency_ms INT NOT NULL`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_similarity_task_kind FOREIGN KEY (result_kind,task_id) REFERENCES ai_tasks (task_type,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_similarity_attempt FOREIGN KEY (task_id,attempt_id) REFERENCES ai_task_attempts (task_id,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_similarity_task_property FOREIGN KEY (task_id,property_id) REFERENCES ai_tasks (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_similarity_source_property FOREIGN KEY (source_image_id,property_id) REFERENCES property_images (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_similarity_index FOREIGN KEY (index_version_id) REFERENCES image_index_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_run_index (id,index_version_id)`
- `UNIQUE KEY uq_run_source (attempt_id,source_image_id)`
- `CONSTRAINT ck_similarity_kind CHECK (result_kind='SIMILARITY')`
- `CONSTRAINT ck_similarity_threshold CHECK (threshold BETWEEN -1 AND 1)`
- `CONSTRAINT ck_similarity_topk CHECK (top_k BETWEEN 1 AND 100)`
- `CONSTRAINT ck_similarity_latency CHECK (latency_ms >= 0)`

### model_versions

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `name VARCHAR(100) NOT NULL`
- `version VARCHAR(50) NOT NULL`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'DRAFT'`
- `dataset_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `artifact_key TEXT NOT NULL`
- `artifact_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `metrics JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `feature_schema JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `runtime_metadata JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `approved_by BIGINT`
- `approved_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_model_dataset FOREIGN KEY (dataset_version_id) REFERENCES dataset_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_model_approver FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_model_name_version (kind,name,version)`
- `UNIQUE KEY uq_model_kind_id (kind,id)`
- `CONSTRAINT ck_model_kind CHECK (kind IN ('VALUATION', 'SIMILARITY', 'AMENITY'))`
- `CONSTRAINT ck_model_status CHECK (status IN ('DRAFT', 'VALIDATED', 'APPROVED', 'RETIRED'))`
- `CONSTRAINT ck_model_approval CHECK (status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))`

### moderation_actions

Target IDs may be combined; the service verifies that report/flag and property refer to the same case and actor is authorized.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `admin_id BIGINT NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `user_id BIGINT`
- `report_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `flag_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `action VARCHAR(40) NOT NULL`
- `reason TEXT NOT NULL`
- `previous_status VARCHAR(30)`
- `new_status VARCHAR(30)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_moderation_admin FOREIGN KEY (admin_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_moderation_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_moderation_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_moderation_report FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_moderation_flag FOREIGN KEY (flag_id) REFERENCES review_flags (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_moderation_target CHECK (property_id IS NOT NULL OR user_id IS NOT NULL OR report_id IS NOT NULL OR flag_id IS NOT NULL)`
- `KEY ix_moderation_property (property_id,created_at)`
- `KEY ix_moderation_report (report_id,created_at)`

### notifications

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `user_id BIGINT NOT NULL`
- `kind VARCHAR(50) NOT NULL`
- `title VARCHAR(255) NOT NULL`
- `body TEXT NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `report_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `read_at DATETIME(6)`
- `dedupe_key VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_notification_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_notification_report FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_notification_dedupe (user_id,dedupe_key)`
- `KEY ix_notification_inbox (user_id,read_at,created_at)`

### outbox_events

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `event_type VARCHAR(100) NOT NULL`
- `task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `payload JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `idempotency_key VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `available_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `published_at DATETIME(6)`
- `publish_attempts INT NOT NULL DEFAULT 0`
- `last_error TEXT`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_outbox_task FOREIGN KEY (task_id) REFERENCES ai_tasks (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_outbox_idempotency (idempotency_key)`
- `CONSTRAINT ck_outbox_attempts CHECK (publish_attempts >= 0)`
- `KEY ix_outbox_ready (published_at,available_at)`

### password_reset_tokens

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `user_id BIGINT NOT NULL`
- `token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `expires_at DATETIME(6) NOT NULL`
- `consumed_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_reset_hash (token_hash)`
- `KEY ix_reset_expiry (expires_at)`
- `CONSTRAINT ck_reset_expiry CHECK (expires_at > created_at)`

### points_of_interest

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `name VARCHAR(255) NOT NULL`
- `category VARCHAR(50) NOT NULL`
- `location POINT NOT NULL SRID 4326`
- `source_name VARCHAR(255)`
- `external_id VARCHAR(255)`
- `source_url TEXT`
- `observed_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `UNIQUE KEY uq_poi_source (source_name,external_id)`
- `KEY ix_poi_category (category)`
- `SPATIAL KEY sx_poi_location (location)`

### projects

Location nullable; no spatial index on this nullable column. properties and POI have spatial indexes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `name VARCHAR(255) NOT NULL`
- `developer VARCHAR(255)`
- `handover_year SMALLINT`
- `scale TEXT`
- `address TEXT`
- `location POINT SRID 4326`
- `amenities JSON NOT NULL DEFAULT (JSON_ARRAY())`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT ck_project_year CHECK (handover_year IS NULL OR handover_year BETWEEN 1900 AND 2200)`
- `CONSTRAINT ck_project_amenities CHECK (JSON_TYPE(amenities)='ARRAY')`

### properties

Proposal decision: location required at creation to support a spatial index. Do not use fake (0,0) points for unknown locations. A future coordinate-free draft flow requires a reviewed schema change.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `owner_id BIGINT NOT NULL`
- `project_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `title VARCHAR(255) NOT NULL`
- `description TEXT`
- `property_type VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `transaction_type VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `price DECIMAL(18,2) NOT NULL`
- `currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'VND'`
- `price_unit VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `area_sqm DECIMAL(12,2) NOT NULL`
- `bedrooms SMALLINT`
- `bathrooms SMALLINT`
- `floor VARCHAR(30)`
- `block VARCHAR(50)`
- `direction VARCHAR(30)`
- `address TEXT`
- `city VARCHAR(100) NOT NULL DEFAULT 'Da Nang'`
- `district VARCHAR(100)`
- `ward VARCHAR(100)`
- `location POINT NOT NULL SRID 4326`
- `contact_name VARCHAR(150)`
- `contact_phone VARCHAR(30)`
- `contact_email VARCHAR(254)`
- `declared_amenities JSON NOT NULL DEFAULT (JSON_ARRAY())`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'DRAFT'`
- `content_version INT NOT NULL DEFAULT 1`
- `published_at DATETIME(6)`
- `expires_at DATETIME(6)`
- `closed_at DATETIME(6)`
- `deleted_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_property_owner FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_property_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_property_type CHECK (property_type IN ('HOUSE', 'APARTMENT', 'LAND', 'VILLA', 'ROOM', 'COMMERCIAL'))`
- `CONSTRAINT ck_transaction_type CHECK (transaction_type IN ('SALE', 'RENT'))`
- `CONSTRAINT ck_price_unit CHECK (price_unit IN ('TOTAL', 'PER_MONTH', 'PER_YEAR', 'PER_DAY'))`
- `CONSTRAINT ck_property_status CHECK (status IN ('DRAFT', 'PENDING', 'PUBLISHED', 'REJECTED', 'HIDDEN', 'EXPIRED', 'CLOSED'))`
- `CONSTRAINT ck_property_price CHECK (price >= 0)`
- `CONSTRAINT ck_property_area CHECK (area_sqm > 0)`
- `CONSTRAINT ck_property_bedrooms CHECK (bedrooms IS NULL OR bedrooms >= 0)`
- `CONSTRAINT ck_property_bathrooms CHECK (bathrooms IS NULL OR bathrooms >= 0)`
- `CONSTRAINT ck_property_content_version CHECK (content_version > 0)`
- `CONSTRAINT ck_property_price_period CHECK (transaction_type <> 'SALE' OR price_unit='TOTAL')`
- `CONSTRAINT ck_property_amenities CHECK (JSON_TYPE(declared_amenities)='ARRAY')`
- `KEY ix_properties_search (status,deleted_at,property_type,transaction_type,price)`
- `KEY ix_properties_region (status,city,district,area_sqm)`
- `KEY ix_properties_owner (owner_id,status,created_at)`
- `KEY ix_properties_moderation (status,created_at)`
- `SPATIAL KEY sx_properties_location (location)`

### property_daily_stats

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `stat_date DATE NOT NULL`
- `view_count BIGINT NOT NULL DEFAULT 0`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `PRIMARY KEY (property_id,stat_date)`

Constraints and indexes:

- `CONSTRAINT fk_stats_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_stats_nonnegative CHECK (view_count >= 0)`

### property_images

Soft-deleted records are retained as AI evidence. Generated active_cover and active_sort implement one active cover and nonduplicate active order; at least one cover is a service rule.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `uploaded_by BIGINT NOT NULL`
- `storage_key VARCHAR(512) NOT NULL`
- `original_filename VARCHAR(255)`
- `mime_type VARCHAR(50) NOT NULL`
- `byte_size BIGINT NOT NULL`
- `sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin`
- `width_px INT`
- `height_px INT`
- `sort_order INT NOT NULL`
- `is_cover BOOLEAN NOT NULL DEFAULT FALSE`
- `deleted_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `active_cover CHAR(36) CHARACTER SET ascii COLLATE ascii_bin GENERATED ALWAYS AS (CASE WHEN is_cover=1 AND deleted_at IS NULL THEN property_id ELSE NULL END) STORED`
- `active_sort INT GENERATED ALWAYS AS (CASE WHEN deleted_at IS NULL THEN sort_order ELSE NULL END) STORED`

Constraints and indexes:

- `CONSTRAINT fk_image_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_image_uploader FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_image_property (id,property_id)`
- `UNIQUE KEY uq_image_cover (active_cover)`
- `UNIQUE KEY uq_image_sort (property_id,active_sort)`
- `CONSTRAINT ck_image_size CHECK (byte_size > 0)`
- `CONSTRAINT ck_image_dimensions CHECK ((width_px IS NULL OR width_px > 0) AND (height_px IS NULL OR height_px > 0))`
- `CONSTRAINT ck_image_order CHECK (sort_order >= 0)`
- `CONSTRAINT ck_image_cover_boolean CHECK (is_cover IN (0,1))`
- `KEY ix_image_checksum (sha256)`

### report_attachments

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `report_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `storage_key VARCHAR(512) NOT NULL`
- `mime_type VARCHAR(50) NOT NULL`
- `byte_size BIGINT NOT NULL`
- `sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_attachment_report FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_attachment_size CHECK (byte_size > 0)`

### reports

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `reporter_id BIGINT NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `reason_code VARCHAR(50) NOT NULL`
- `description TEXT NOT NULL`
- `contact_email VARCHAR(254)`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN'`
- `assigned_to BIGINT`
- `resolved_by BIGINT`
- `resolution_note TEXT`
- `resolved_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_report_user FOREIGN KEY (reporter_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_report_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_report_assignee FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_report_resolver FOREIGN KEY (resolved_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT ck_report_status CHECK (status IN ('OPEN', 'PROCESSING', 'RESOLVED', 'REJECTED'))`
- `CONSTRAINT ck_report_resolved CHECK (status NOT IN ('RESOLVED','REJECTED') OR (resolved_by IS NOT NULL AND resolved_at IS NOT NULL AND resolution_note IS NOT NULL))`
- `KEY ix_report_queue (status,created_at)`
- `KEY ix_report_owner (reporter_id,created_at)`
- `KEY ix_report_property (property_id,status)`

### review_flags

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `ai_task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin`
- `flag_type VARCHAR(50) NOT NULL`
- `severity VARCHAR(20) NOT NULL`
- `status VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'OPEN'`
- `evidence JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `dedupe_key VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `reviewed_by BIGINT`
- `reviewed_at DATETIME(6)`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `updated_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_flag_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_flag_task_property FOREIGN KEY (ai_task_id,property_id) REFERENCES ai_tasks (id,property_id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_flag_reviewer FOREIGN KEY (reviewed_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_flag_dedupe (dedupe_key)`
- `CONSTRAINT ck_flag_status CHECK (status IN ('OPEN', 'REVIEWED', 'DISMISSED'))`
- `CONSTRAINT ck_flag_severity CHECK (severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH'))`
- `KEY ix_flag_queue (status,severity,created_at)`

### roles

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `code VARCHAR(20) NOT NULL PRIMARY KEY`
- `name VARCHAR(100) NOT NULL`

Constraints and indexes:

- `CONSTRAINT ck_roles_code CHECK (code IN ('BUYER', 'BROKER', 'ADMIN'))`

### saved_properties

See SQL constraints and indexes below. Service authorization is required for writes.

Columns:

- `user_id BIGINT NOT NULL`
- `property_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `saved_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `PRIMARY KEY (user_id,property_id)`

Constraints and indexes:

- `CONSTRAINT fk_saved_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_saved_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `KEY ix_saved_recent (user_id,saved_at)`

### user_roles

Compatibility projection of users.role, synchronized on account insert/role update by triggers. users.role is authoritative until a dedicated multi-role service is implemented. Do not grant roles directly through this table.

Columns:

- `user_id BIGINT NOT NULL`
- `role_code VARCHAR(20) NOT NULL`
- `granted_by BIGINT`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`
- `PRIMARY KEY (user_id, role_code)`

Constraints and indexes:

- `CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_user_roles_role FOREIGN KEY (role_code) REFERENCES roles (code) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_user_roles_grantor FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT`

### users

V1 BIGINT/IDENTITY preserved for existing Java Long entity. Role/status checks remain BUYER/BROKER/ADMIN and ACTIVE/LOCKED. Soft-delete metadata is added; current API must be enhanced to enforce deleted_at/token_version when it starts using these fields.

Existing V1 plus additive V2 columns; see schema-reference.sql and migration V2.

### valuation_results

SHAP JSON contract below; base_value/model_output can be log-scale while reference_price is a DECIMAL currency amount.

Columns:

- `id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY`
- `task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `result_kind VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'VALUATION'`
- `reference_price DECIMAL(18,2) NOT NULL`
- `currency CHAR(3) CHARACTER SET ascii COLLATE ascii_bin NOT NULL DEFAULT 'VND'`
- `price_unit VARCHAR(30) CHARACTER SET ascii COLLATE ascii_bin NOT NULL`
- `base_value DOUBLE NOT NULL`
- `model_output DOUBLE NOT NULL`
- `output_scale VARCHAR(20) NOT NULL`
- `shap_values JSON NOT NULL DEFAULT (JSON_OBJECT())`
- `warnings JSON NOT NULL DEFAULT (JSON_ARRAY())`
- `latency_ms INT NOT NULL`
- `created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6))`

Constraints and indexes:

- `CONSTRAINT fk_valuation_task_kind FOREIGN KEY (result_kind,task_id) REFERENCES ai_tasks (task_type,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `CONSTRAINT fk_valuation_attempt FOREIGN KEY (task_id,attempt_id) REFERENCES ai_task_attempts (task_id,id) ON DELETE RESTRICT ON UPDATE RESTRICT`
- `UNIQUE KEY uq_valuation_attempt (attempt_id)`
- `CONSTRAINT ck_valuation_kind CHECK (result_kind='VALUATION')`
- `CONSTRAINT ck_valuation_price CHECK (reference_price >= 0)`
- `CONSTRAINT ck_valuation_latency CHECK (latency_ms >= 0)`
- `CONSTRAINT ck_valuation_price_unit CHECK (price_unit IN ('TOTAL', 'PER_MONTH', 'PER_YEAR', 'PER_DAY'))`
- `CONSTRAINT ck_valuation_scale CHECK (output_scale IN ('PRICE', 'LOG_PRICE'))`
