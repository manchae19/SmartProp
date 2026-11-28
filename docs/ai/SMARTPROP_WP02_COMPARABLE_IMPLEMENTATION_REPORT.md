# WP-02 Comparable Correctness implementation report

## Scope

Phase B5–B8 follows the independent conditional review of 94917fae795d118f842f69a7189aac7a32a8504e on main f972d3a3465e5cc0ebe4260ddfbee7a8d32eee42.

- P1 derives URL identity from recognized listing routes or supported listing-ID parameters on detail routes. It preserves path case, identifying query values and fragments. Generic links stay available for display and provide no automatic identity match. Vendor keys still use source namespaces.
- P2 reruns a saturated source query once using the same deterministic area-distance / ID order and a bounded limit. The per-source scanned limits are 600 SmartProp, 1200 external and 900 authorized research rows per filter pass. One extra row detects truncation. Incomplete scans produce an explicit limitation and withhold medians.
- B5 uses the applicable observed features for each property type, with no invented missing values. Land omits room and floor features. Apartments use bedrooms and explicit project identity. House and villa use structural features supported by the source. Public rows carry no inferred frontage or road width. Java sensitivity checks compared no shrinkage and 5%, 25% and 50% coverage penalties. Fixture rankings changed without enough evidence to choose a production coefficient. BF remains the scoring policy with feature coverage presented independently.
- B6 publishes purpose, scan completeness, per-source provenance, eligible and returned counts, dedupe and public asking-price medians. The statistical cohort excludes unverified research observations, even in authorized research responses. Incomplete scans or fewer than five eligible public observations suppress medians and report INSUFFICIENT_EVIDENCE.
- B7 uses the shared card for the direct form, property detail, standalone valuation, posting preview and Unified Advisor. Detail submits SIMILAR_LISTING. The direct buyer form sends an unchanged absolute budget. Valuation submits only independent physical inputs. Advisor displays separate similar-listing and valuation-support evidence and does not feed comparable results into V1.3.
- WP-04 handoff. WP-02 only reads existing valuation inputs and availability and adds separate Comparable UI and DTO fields. Preserve both evidence objects if the feature surfaces meet in a later integration. WP-04 explanation fields, estimators, model artifacts and output values retain their existing contracts.

## Remaining limits

Unknown URL structures and cross-source entity matches without trusted identity remain unresolved. The queue can still hit its bounded scan. The five-price rule suppresses unstable summaries but does not validate prices against transactions. The fixture and synthetic benchmark results do not establish production recall, precision, execution plans or latency. Confidence gate D, historical as-of, T3 automatic merges, new indexes, migrations, labeled market-data evaluation and production deployment remain deferred.

See the [API contract](SMARTPROP_WP02_COMPARABLE_API_CONTRACT.md) and [benchmark report](SMARTPROP_WP02_COMPARABLE_BENCHMARK_REPORT.md).

## Fresh validation on the implementation tree

| Suite | Command or fixture | Passed | Failed | Skipped | Exit |
| --- | --- | ---: | ---: | ---: | ---: |
| Preflight Java Comparable | mvnw.cmd -o -Dtest=Comparable*Test test | 35 | 0 | 0 | 0 |
| Preflight synthetic MySQL | mvnw.cmd -o -Dtest=ComparableSyntheticMysqlIT test | 3 | 0 | 0 | 0 |
| Spring Boot regression | mvnw.cmd -o test | 271 | 0 | 0 | 0 |
| Final synthetic MySQL | Same SQL test class, separate loopback server with verified child PID, data-dir and UUID | 3 | 0 | 0 | 0 |
| RAG regression | tests/run_isolated.py with tests/test_rag*.py | 911 | 0 | 0 | 0 |
| Full FastAPI serial | tests/run_isolated.py -q -rs --tb=short tests | 1180 | 0 | 19 | 0 |
| Historical valuation | Three historical regression IDs selected with the same isolated runner | 3 | 0 | 0 | 0 |
| Frontend recursive | npm.cmd test | 154 | 0 | 0 | 0 |
| Vite production build | npm.cmd run build | 246 modules | 0 | — | 0 |
| Chromium | Local fixture server and six assertions groups spanning all five integrated surfaces | 6 groups | 0 | 0 | 0 |

FastAPI had zero collection and setup errors. The 19 skips are the 13 retired public V6 cases, one optional planning snapshot and five cases missing optional YOLOv8 weights. The browser used the actual React surfaces with synthetic HTTP responses and exercised desktop and mobile, delayed loading, empty and insufficient states, retry, purpose-specific requests and research hiding. It did not use a protected service. The MySQL fixture used synthetic rows on a dedicated ephemeral loopback listener and was stopped after the run.

The isolated V1.3 artifact snapshot matched all eight SHA-256 values. Git diff against the main baseline confirms valuation production paths, RAG, Recommendation, security configuration and database migrations are intact. Public/research checks run through the existing Spring security regression, Comparable/Advisor tests and frontend session tests. Local run evidence is under the worktree's .smartprop directory in wp02-b58-*.log and wp02-b58-*.exit. Graphify and the working tree diff were checked before publication.
