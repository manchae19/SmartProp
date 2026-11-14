# RAG SQL staging — configuration and startup

## Safety defaults

- `RAG_SQL_ENABLED=false` by default. RAG POI/FAISS/Qwen does not require SQL.
- When enabled, the SQL port must be a configured local datasource; **3306 is rejected unless `RAG_SQL_ALLOW_PRODUCTION=true` is explicitly set**.
- There is no automatic fallback from the configured datasource to 3306.
- The repository only runs a fixed `SELECT` against `properties`; the connection starts with `SET SESSION TRANSACTION READ ONLY`.
- Credentials are read from environment variables and are never written to source.

## Environment

```text
RAG_SQL_ENABLED=true
RAG_SQL_HOST=127.0.0.1
RAG_SQL_PORT=13306
RAG_SQL_DATABASE=smartprop_staging
RAG_DB_USER=rag_reader
RAG_DB_PASSWORD=<set-locally>
RAG_SQL_ALLOW_PRODUCTION=false
```

## Minimum SELECT-only database user

Run on the staging instance only:

```sql
CREATE USER 'rag_reader'@'127.0.0.1' IDENTIFIED BY '<local-password>';
GRANT SELECT ON smartprop_staging.properties TO 'rag_reader'@'127.0.0.1';
GRANT SELECT ON smartprop_staging.property_images TO 'rag_reader'@'127.0.0.1';
GRANT SELECT ON smartprop_staging.projects TO 'rag_reader'@'127.0.0.1';
GRANT SELECT ON smartprop_staging.property_legal_documents TO 'rag_reader'@'127.0.0.1';
FLUSH PRIVILEGES;
```

The repository only reads the public projection: property rows, public images, project metadata,
and aggregate legal counts. It never reads `users`, contact fields, private legal files, or
authentication tables.

### Optional public-view mode

For production, create the views in `RAG_PUBLIC_VIEWS.sql` with an administrative account,
then grant the RAG reader `SELECT` on the three views only and set:

```text
RAG_SQL_USE_VIEWS=true
```

In this mode the reader does **not** need `SELECT` on the base tables. The views are
`SQL SECURITY DEFINER` and expose only the approved columns. Keep `false` for table mode.

Do not grant `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, or `EXECUTE`.

## Startup sequence

1. Start staging MySQL on 13306.
2. Start Spring Boot on 8080 with `APP_RECOMMENDATION_V11_ENABLED=true`.
3. Export the `RAG_SQL_*` variables above.
4. Run:

```powershell
cd ai-services
.\scripts\run-chat-local.ps1 -Port 8001 -BackendUrl http://127.0.0.1:8080
```

The script preserves an explicitly supplied `RAG_SQL_ENABLED` value. It does not start SQL unless the value is true.

## Production

Do not point this demo configuration at production MySQL 3306. A production rollout requires a separately approved read-only account, explicit datasource approval, least-privilege review, and an audit of the fixed projection. Use `RAG_SQL_ALLOW_PRODUCTION` only after that approval.
