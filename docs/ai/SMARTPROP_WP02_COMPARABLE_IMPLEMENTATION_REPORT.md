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

## Targeted final corrections

The five-surface Chromium fixture reproduced the direct Comparable result remaining visible after a BROKER-to-BUYER role change with the same token at reviewed HEAD `75b8f4fc100cc3f61f5e15157b1492382f3d50ec`. The direct search and embedded lookup now scope their request state to the authenticated actor, role, token and criteria. A new scope clears displayed results and discards late success and failure responses. Revocation followed immediately by restoration still requires a new request. The server authorization and scoring paths remain as reviewed.

Advisor copies `Candidate.featureCoverage` into both comparable evidence lists. Legacy Java construction and JSON without coverage remain supported. MockMvc verifies both response paths against the real Advisor controller and orchestration with synthetic inputs. Chromium verifies that both cards render the existing score and the provided coverage.

### Fresh verification

| Suite | Command or selection | Passed | Failed | Skipped | Exit |
| --- | --- | ---: | ---: | ---: | ---: |
| Comparable Java | `mvnw.cmd -o -Dtest=Comparable*Test test` | 40 | 0 | 0 | 0 |
| Advisor and security | `mvnw.cmd -o -Dtest=Advisor*Test,ResearchAccessHttpSecurityTest test` | 36 | 0 | 0 | 0 |
| Spring Boot | `mvnw.cmd -o test` | 272 | 0 | 0 | 0 |
| Synthetic MySQL | `mvnw.cmd -o -Dtest=ComparableSyntheticMysqlIT test` on the dedicated fixture instance | 3 | 0 | 0 | 0 |
| RAG | `tests/run_isolated.py -q -rs --tb=short` with all `tests/test_rag*.py` | 911 | 0 | 0 | 0 |
| Full FastAPI serial | `tests/run_isolated.py -q -rs --tb=short tests` | 1180 | 0 | 19 | 0 |
| Historical valuation | Isolated runner with the three historical V1.3 regression IDs | 3 | 0 | 0 | 0 |
| Frontend recursive | `npm.cmd test` | 154 | 0 | 0 | 0 |
| Vite production build | `npm.cmd run build` | build pass | 0 | — | 0 |
| Chromium | `node tests/browser/wp02-browser.mjs` with `WP02_CHROMIUM` set to the executable | 12 groups | 0 | 0 | 0 |

Run the Chromium command from `frontend` with Node 22.12 or later. The browser exercises real React components with mocked HTTP, including same-token role withdrawal, logout and login, actor change, role restoration, and criteria changes during pending responses. Spring runs the MockMvc contract and embedded Tomcat loopback boundary tests. The dedicated MySQL instance exercises real repository SQL and the ranking service with synthetic listings. A combined Chromium-to-Spring-to-MySQL HTTP run is `NOT_RUN`. Production SQL performance, production market accuracy, deployed Caddy, and live MySQL grants and views remain unverified.

FastAPI had zero collection or setup errors. Its 19 skips are the retired public V6 cases and optional planning and vision inputs. Eight V1.3 artifact SHA-256 checks matched. Git verified that valuation production code, migrations, RAG, Recommendation and Phase 0 backend security and deployment files match main. Local evidence is in `.smartprop/wp02-final-*.log`, `.smartprop/wp02-final-*.exit` and `.smartprop/wp02-final-artifact-integrity.json`.

### Read-only integration matrix

Main `f972d3a3465e5cc0ebe4260ddfbee7a8d32eee42` is an ancestor of WP-02. The overlaps below compare WP-02's paths changed since main with each other branch's paths changed since its own common base with main. The conflict column uses a virtual merge of the two full branch histories.

| Branch | Compared HEAD | WP-02 path overlap | Virtual merge |
| --- | --- | --- | --- |
| `research/wp04-explainable-ai` | `2f3af3f120ce7ecbd070571f0a78b8893b7cc9f4` | None | Clean |
| PR #37 | `151a07b4472ea0fd3134fb50f4f3de757e83d46f` | `ListingDetailView.jsx` | Clean |
| PR #43 | `f59edf223c98249ee6104c367c34537bd851aea5` | `ListingDetailView.jsx` | Ten content conflicts inherited from the divergent history |

PR #43 conflicts in `ai-services/app/rag/{config,followup,money,orchestrator,personalization,session,tools}.py`, `HybridRecommendationService.java`, `chatPresentation.js` and `ops/Caddyfile`. Preserve main's Phase 0 public SAFE isolation, research authorization and proxy boundaries, PR #45's cancellation and strict-filter behavior, and WP-02's listing lookup scope and separate Advisor comparable outputs. If WP-04 later changes the Advisor surface, preserve its explanation contract alongside both comparable evidence lists.
