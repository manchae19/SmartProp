# WP04 final acceptance

[Machine-readable evidence](acceptance.json) is the final acceptance record. The [runtime instructions](../../../frontend/tests/wp04/browser/tools/README.md) reproduce the isolated fixture.

| Evidence | Final result |
| --- | --- |
| Failure isolation | 11/11, including a real FastAPI outage and recovery |
| Real runtime browser | 298/298 |
| Mocked three surfaces | 30/30, zero not run |
| Reactive authorization | 3/3 |
| Isolated MySQL integration | 4/4 |
| Frontend and WP02 browser | 348 tests and 12 groups |
| Spring Boot | 324 passed |
| FastAPI serial | 1,230 passed, 20 skipped, 105 subtests passed |
| Focused WP04 Python | 51 passed |
| Vite and asset audit | 273 modules and 148 files audited |
| V1.3 and migrations | 8 hash and size checks, 23 unchanged SQL versions applied in the fixture |

All listed suites exited zero. The JSON keeps check names, outcomes and counts. It omits raw HTTP payloads, logs, credentials, host paths, databases and model files.

The application evidence applies to tested commit `9fa708a070e352247ed08f4c8720dfe22221164b`, tree `d1e57dfee9a9315a7f53d4ca75dbdfd03962f9ac`, and was accepted at `a82bd7f69902db1e7c3d4bb0a4bd010901279c17`. Main was `0e9053f0c4085351a7d429f81995f6895ad80e33`. Git comparisons against the accepted head confirmed that this delivery changes evidence, documentation and fixture tooling only.

[Historical browser reports](../../../frontend/tests/wp04/browser/reports/historical) preserve earlier observations. The failure-isolation 24/35 and mocked surfaces three not-run results belong to superseded harness runs.

The research response in the revocation scenario is synthetic. Account changes and SAFE fallback use the real shared HTTP client and local Spring API. Production deployment, real Google OAuth, Caddy runtime and deployed database permissions remain unverified. The legacy V6/TiniX `AdvisorControllerLiveIT` is excluded from V1.3 acceptance.

[Separate launcher verification](launcher-verification.json) records the fresh V23 startup, 3/3 authorization, 11/11 failure isolation with real FastAPI recovery, 30/30 mocked surfaces, preflight rejections, and owned shutdown with the mentor listeners preserved.
