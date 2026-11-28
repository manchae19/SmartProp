# WP-04 isolated Standard-V23 fixture — provisioning and root cause

Sanitised. No credentials, no protected data.

## 1. Correction to the earlier diagnosis

The previous version of this document blamed **MySQL 8.4** for requiring `CHECK` constraint names to
be unique per schema, and suggested that MySQL 8.0 would behave differently. **That was wrong.**
MySQL **8.0.16 and later** have the same rule and the same error (`ER_CHECK_CONSTRAINT_DUP_NAME`,
3822). V2 declares `ck_user_token_version` **exactly once** (on `users`), and the migrated fixture
contains exactly one such constraint, owned by `wp04_runtime_v23.users`.

The duplicate-constraint error seen earlier was an **artifact of re-running V2 by hand against a
schema where an earlier attempt had already added the constraint** — not the original failure.

## 2. Original failure (clean fixture, single run)

| Fact | Value |
|---|---|
| Server | MySQL **8.4.13** (portable, `F:\SmartProp\.scratch\mysql-8.4\mysql-8.4.13-winx64`) |
| Fixture | fresh datadir `wp04-mysql/data-clean`, schema `wp04_runtime_clean` |
| Server UUID | `0f5afd1e-eb00-11f1-94da-7085c2fe30d2` (PID 35020) |
| Command | `mvnw -o flyway:migrate -Dflyway.target=23 -Dflyway.locations=filesystem:<repo>/database/migrations,filesystem:<repo>/database/research-migrations/poi` |
| Result | V1 applied; **V2 failed** at `V2__extend_accounts_and_roles.sql` **line 54** |
| SQLSTATE | **HY000** |
| Error code | **1419** |
| Message | `You do not have the SUPER privilege and binary logging is enabled (you *might* want to use the less safe log_bin_trust_function_creators variable)` |

Line 54 is the `CREATE TRIGGER users_role_insert` compatibility bridge (V2 also creates
`users_role_update`). MySQL 8.4 enables binary logging by default, and creating a trigger under
binary logging requires `SUPER` or `log_bin_trust_function_creators=1`.

**Conclusion:** the blocker is a **server-configuration** requirement for trigger creation, not a
migration defect, not a CHECK-name rule, and not a MySQL 8.4-vs-8.0 difference.

## 3. Clean fixture that applies the unchanged lineage

| Fact | Value |
|---|---|
| Server | MySQL 8.4.13, datadir `wp04-mysql/data-ok` (fresh `--initialize-insecure`) |
| Bind | `127.0.0.1`, `--mysqlx=0`, port **3407** (verified free) |
| Server UUID | `54afb557-eb00-11f1-886b-7085c2fe30d2` (PID 34408) |
| Server flag | `--log-bin-trust-function-creators=1` (fixture-scoped, not a migration change) |
| Schema / user | `wp04_runtime_v23` / `wp04_v23@127.0.0.1` (grants limited to that schema) |
| Migrations | unchanged files under `database/migrations` + `database/research-migrations/poi` |
| Result | **23/23 applied**, `now at version v23`, exit 0 |
| `flyway:validate` | **Successfully validated 23 migrations**, exit 0 |

Post-migration verification (read-only):

- `flyway_schema_history`: **23 rows, 23 success, 0 failed**.
- **56** tables.
- Triggers present: `users_role_insert`, `users_role_update`, `session_revoke_update`,
  `properties_listing_code_insert`, `properties_listing_code_update`.
- Core tables present: `users`, `auth_sessions`, `roles`, `user_roles`, `properties`,
  `property_images`.
- `ck_user_token_version` exists exactly once, on `users` — no duplicate.

No migration file was edited, no Flyway history was fabricated, no guard/lineage validation was
weakened, and `ddl-auto=create` was never used.

## 4. Fixtures preserved for investigation

- `wp04-mysql/data` — first attempt (V1 ok, V2 failed, then a manual V2 replay produced the
  misleading duplicate error). Read-only.
- `wp04-mysql/data-clean` — clean reproduction of the original V2 failure (log above). Read-only.
- `wp04-mysql/data-ok` — the verified V23 fixture used for runtime work.

## 5. What is still open

Checkpoint 1 requires Hibernate schema validation, which needs Spring Boot started against this
fixture with `spring.jpa.hibernate.ddl-auto=validate`, runtime Flyway disabled and SQL init disabled
(the `standard-migrations` profile already enforces all three and, unlike the local/staging profiles,
does not pin the JDBC URL to a protected instance). Synthetic seeding (BROKER, BUYER, ADMIN, published
properties) and Checkpoints 2–3 (FastAPI + Spring runtime, three browser surfaces) remain.

---

## Seed and runtime note

Eight synthetic HOUSE properties are seeded idempotently (`WP04-HOUSE-1..8`, upsert on the unique
listing code). `location` is a `POINT` column with **SRID 4326**, and MySQL expects
`ST_GeomFromText('POINT(latitude longitude)', 4326)` — latitude first. Passing longitude first fails
with "Latitude 108.19 is out of range".

The fixture was used for real Spring → FastAPI preview and Advisor runs; results are recorded in
`SMARTPROP_WP04_B6_B7_RUNTIME_EVIDENCE.md`.
