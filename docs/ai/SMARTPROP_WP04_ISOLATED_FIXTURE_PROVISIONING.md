# WP-04 isolated Standard-V23 fixture — provisioning log

Sanitised. No credentials, no protected data. Written after Checkpoint 1 was attempted.

## 1. Instance actually provisioned (verified)

| Fact | Value |
|---|---|
| Binary | `F:\SmartProp\.scratch\mysql-8.4\mysql-8.4.13-winx64\bin\mysqld.exe` |
| Version | **8.4.13** |
| Datadir | `F:\SmartProp\.scratch\wp04-mysql\data` (fresh, `--initialize-insecure`) |
| Bind | `127.0.0.1` only, `--mysqlx=0` |
| Port | **3407** (verified free before start) |
| Server UUID | `165b1d47-eaff-11f1-8898-7085c2fe30d2` |
| PID (first start / restart) | 20472 / 6084 |
| Schema | `smartprop_wp04_runtime` (utf8mb4_unicode_ci) |
| Runtime user | `wp04_rt@127.0.0.1`, grants limited to that schema |
| Protected ports | 3306/3307/3311/3312 never contacted |

Commands used (no secrets):

```
mysqld --initialize-insecure --datadir=<tmp>/data --basedir=<mysql8.4>
mysqld --datadir=<tmp>/data --port=3407 --bind-address=127.0.0.1 --mysqlx=0
mysql -h 127.0.0.1 -P 3407 -u root -e "CREATE DATABASE smartprop_wp04_runtime ..."
```

First attempt failed at `ERROR 1130 Host '127.0.0.1' is not allowed to connect` because
`--skip-name-resolve` left only `root@localhost`; restarting without that flag fixed it.

## 2. Migration attempt — BLOCKED with an exact cause

Command (Standard lineage through V23, separately controlled, guard untouched):

```
mvnw -o flyway:migrate   -Dflyway.url=jdbc:mysql://127.0.0.1:3407/smartprop_wp04_runtime?connectionTimeZone=UTC   -Dflyway.user=wp04_rt -Dflyway.password=***   -Dflyway.locations=filesystem:<repo>/database/migrations,filesystem:<repo>/database/research-migrations/poi   -Dflyway.target=23
```

Exit code **1**. Flyway history after the attempt:

| version | success | description |
|---|---|---|
| 1 | 1 | accounts and sessions |
| 2 | **0** | extend accounts and roles |

Applying `V2__extend_accounts_and_roles.sql` directly reproduces the root cause:

```
ERROR 3822 (HY000) at line 5: Duplicate check constraint name 'ck_user_token_version'.
```

- V1 succeeded, so connectivity, credentials and locations are correct.
- MySQL **8.4** requires `CHECK` constraint names to be unique **per schema**; MySQL 8.0 (the
  lineage the migrations were written for) scoped them per table. V2 therefore cannot apply on the
  8.4 binary.
- The migration SQL is immutable for this task and the lineage guard must not be weakened, so this is
  a hard stop, not a configuration mistake.

## 3. What this blocks

Spring Boot cannot start with `ddl-auto=validate` against an empty schema, so:

- `WP04_ISOLATED_STANDARD_V23_FIXTURE_VERIFIED` — **not satisfied** (instance verified, lineage not).
- Real posting preview and Advisor runtime gates — **not run**.
- Three real browser route interactions — **not run**.

## 4. Unblocking options (need a decision, none applied)

1. Provision the same fixture with a **MySQL 8.0.x** binary (the lineage's target version). V2 would
   then apply and the rest of the chain can be validated unchanged.
2. Obtain approval to make V2 portable (e.g. schema-unique check names) — a migration change outside
   this task's scope and explicitly forbidden right now.

## 5. Cleanup

The disposable instance was stopped; the datadir is retained at
`F:\SmartProp\.scratch\wp04-mysql\data` so the run can be repeated verbatim once a MySQL 8.0
binary is available. No production or group database was ever contacted.
