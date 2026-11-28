# Isolated MySQL integration fixtures

`CoordinateProvenanceIT` and News integration tests require explicit fixture authorization.
No expected identity is discovered from the database under test. The provisioner must create
the manifest **before** the test connects, using its allocated endpoint, initialization record
(`auto.cnf` UUID), datadir, config and owned process information. Do not use `SELECT @@...`
to manufacture expected values. Credentials stay in process environment, outside the manifest/Git.

Provision a dedicated local MySQL process on an unused loopback port other than3306/3307.
Never point this runner at another member's instance. The process must be visible in the same
OS/process namespace as the JVM, under the provisioner's user. Container-based CI must run
the JVM and owned MySQL process in that namespace, or provision a native disposable instance.

The UTF-8 Java-properties manifest has these independently supplied fields:

```properties
authorization=<unique-run-authorization>
jdbcUrl=jdbc:mysql://127.0.0.1:<allocated-port>/<allocated-schema>?connectionTimeZone=UTC
port=<allocated-port>
schema=<allocated-synthetic-schema>
serverUuid=<UUID-recorded-during-initialization>
datadir=<absolute-datadir>
ownershipFile=<absolute-owned-marker-file>
pid=<owned-mysqld-PID>
executable=<absolute-mysqld-path>
owner=<process-owner-user>
startedAt=<process-start-UTC-ISO-8601>
configPath=<absolute-config-file>
configSha256=<SHA256-of-config>
```

Use forward slashes for paths in Java properties. `ownershipFile` contains exactly the
authorization value. Supply `SMARTPROP_TEST_FIXTURE_MANIFEST` and, separately,
`SMARTPROP_TEST_FIXTURE_AUTHORIZATION`; set `DB_URL` to the exact authorized JDBC URL,
plus process-only `DB_USER`, `DB_PASSWORD`, `JWT_SECRET`. Without the manifest/authorization
the shared Coordinate test fails before fixture writes. Protected ports/schema, destination
mismatch, UUID/datadir mismatch, wrong owner/executable/start time, changed config or absent
ownership marker are rejected. The guard checks destination/authorization/ownership before
JDBC identity reads; neither it nor capability discovery writes SQL.

Provision the existing synthetic schema contract and use official Flyway baseline13 followed
by unchanged crawler14 and Local17–28. No copying, repairing or editing Flyway history.
Seed only clearly marked synthetic ADMIN/BROKER/BUYER accounts with unusable login hashes.
The shared Coordinate regression uses test-only `IsolatedCoordinateFixture`: it replaces
deployment endpoint literals with the independent ownership manifest, **retaining** exact
ordered Local V28 history, full Flyway checksum validation, the V28 CHECK, and full Hibernate
schema validation before startup. Its two `@TestBean` replacements are limited to the test
bootstrap; authentication, business services and production Local/Staging guards are unchanged.

```powershell
./backend/mvnw.cmd -f backend/pom.xml test '-Dtest=CoordinateProvenanceIT,IsolatedDatabaseSafetyIT'
```

Test-only helpers are excluded from the production jar. `Pr41DatabaseTestSafety` is a News
compatibility wrapper around this generic guard; shared Coordinate code does not reference it.
Do not enable a deployment profile pinned to a different endpoint for the portable test command.

Evidence from the targeted review uses two independently provisioned fixtures:3311 and3312,
with different PID, UUID, schema and datadir. Both run all39 Coordinate tests and8 safety tests
with0 skips. Exact expected/observed identity and final SHA belong in the local final manifest.
