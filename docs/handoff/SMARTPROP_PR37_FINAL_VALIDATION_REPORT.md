# PR #37 final validation

Integration branch `integration/pr37-ui-validation` started at `b33e4fc8cc2c4612245543862f8dcdd17573f56c` on approved main `1c67a279a8ff6f6939767e82bb31b17584610864`. The original [PR #37](https://github.com/manchae19/SmartProp/pull/37) has its own reviewed head `151a07b4472ea0fd3134fb50f4f3de757e83d46f`. This report describes the correction commit containing it. Local and remote SHA verification is recorded in the local `.smartprop/pr37-remote.json` handoff.

## Final findings

1. **Market session scope and opt-in.** Mount and public requests always submit `includeResearch=false` without a bearer token. The active ADMIN session can submit an explicit research request. TiniX source options, capability and research results appear only after an authorized response. A 403 or a response with research disabled clears research and returns to SAFE. A terminal 401 also invalidates the expired session. Token, actor, role and status transitions clear restricted state and abort its request. An obsolete response cannot repopulate it. Restoration requires a new opt-in. Research metadata in a purportedly public payload is rejected. Existing server-side guards remain authoritative.
2. **Tests in Git and cancellation.** `git check-ignore -v` located the repository rule for the existing Market tests. The two Market tests and the auth/coordinate test were explicitly added alongside the new HTTP client test. External cancellation and timeout have distinct outcomes. Aborted, obsolete and late refreshed responses cannot apply data or expire a replacement session. Shared refresh remains usable by a second caller when the first caller aborts. The existing session store contract still supplies the session snapshot and subscriptions.
3. **Browser coverage.** The retained Market and News checks and new route cases exercise real React pages with production-mode Vite assets and mocked HTTP. Checks assert specific UI states and positive request counts before checking request attributes. Opt-in tests wait for the actual HTTP status, since a fast denial can reset the checkbox before the automation reads it. The normal production distribution was audited separately.

## Tracked tests and entry points

- `frontend/tests/marketAnalyticsSession.test.mjs`
- `frontend/tests/marketDataAndAssets.test.mjs`
- `frontend/tests/httpClientAbortSession.test.mjs`
- `frontend/tests/authAndCoordinateStatus.test.mjs`
- `frontend/e2e/pr37-validation.e2e.mjs`, `pr37-surfaces.mjs`, `pr37-market-fixture.mjs`, `pr37-preview.mjs`, `pr37-session-entry.js`, and `pr37-dist-assets.mjs`.
- `frontend/e2e/news-ui.e2e.mjs`, `pages-smoke.e2e.mjs`, and the existing `frontend/tests/browser/wp02-browser.mjs`.

## Fresh tests

Run the Node commands in `frontend` and Maven in `backend`. Browser setup and the loopback Vite preview commands are in the [E2E README](../../frontend/e2e/README.md). Each row has a matching `.log` and `.exit` file under the local `.smartprop` directory. Counts for targeted suites overlap with the recursive suite.

| Suite | Command | Passed / failed / skipped | Exit | Log basename |
| --- | --- | --- | --- | --- |
| Frontend recursive | `npm.cmd test` | 194 / 0 / 0 | 0 | `pr37-frontend` |
| Frontend recursive from Git archive | `git archive HEAD frontend`, extract, reuse existing dependencies and run `npm.cmd test` | 194 / 0 / 0 | 0 | `pr37-repro` |
| Market session | `node --test tests/marketAnalyticsSession.test.mjs` | 15 / 0 / 0 | 0 | `pr37-market-session` |
| Market data/assets | `node --test tests/marketDataAndAssets.test.mjs` | 5 / 0 / 0 | 0 | `pr37-market-assets` |
| HTTP client | `node --test tests/httpClientAbortSession.test.mjs` | 17 / 0 / 0 | 0 | `pr37-http-client` |
| Admin coordinate | `node --test tests/coordinateEligibility.test.mjs tests/coordinateReview.test.mjs tests/authAndCoordinateStatus.test.mjs` | 31 / 0 / 0 | 0 | `pr37-admin-coordinate` |
| Standard Vite production | `npm.cmd run build` | Build completed, 268 modules | 0 | `pr37-vite` |
| Production distribution assets | `node e2e/pr37-dist-assets.mjs` | Audit completed, 145 files | 0 | `pr37-dist-assets` |
| Chromium Market and News | `node e2e/pr37-validation.e2e.mjs --groups=g1,g2,g3,g4,g5,g6,g7,g13,g14` | 9 / 0 / 0 groups | 0 | `pr37-browser-market-news` |
| Chromium core routes | `node e2e/pr37-validation.e2e.mjs --groups=g8,g9,g10,g11,g12,g15,g16,g17,g18` | 9 / 0 / 0 groups | 0 | `pr37-browser-core` |
| Existing News E2E | `node e2e/news-ui.e2e.mjs` | 7 / 0 / 0 checks | 0 | `pr37-news-ui` |
| Existing Pages Smoke | `node e2e/pages-smoke.e2e.mjs` | 11 / 0 / 0 checks | 0 | `pr37-pages-smoke` |
| Existing WP-02 Chromium | `node tests/browser/wp02-browser.mjs` | 12 / 0 / 0 groups | 0 | `pr37-wp02` |
| Spring security and Market | `./mvnw.cmd -o '-Dtest=ResearchAccessHttpSecurityTest,MarketAnalyticsServiceTest,TomcatLoopbackProxyBoundaryTest' test` | 17 / 0 / 0, 0 setup errors | 0 | `pr37-backend-security` |
| Existing Post Location | `node e2e/post-location.e2e.mjs` with a loopback base and blank staging credentials | 0 / 0 / 1 | 0 | `pr37-post-location` |

The Market session suite uses artificial sessions for anonymous, BUYER, BROKER and ADMIN, for allowed and disabled research, 401/403, lock and unavailable states, same-user renewal, ADMIN account replacement, role revocation, logout and rapid revocation/restoration. It includes delayed fixtures that resolve after cancellation. Spring tests exercise the actual security and Market service code with controlled collaborators, including the Tomcat loopback/proxy contract. Browser tests use mocked HTTP. They do not establish live React → RAG → Spring → database compatibility.

## Route coverage at 390, 768 and 1440 px

| Surface | Groups | Evidence |
| --- | --- | --- |
| A. Home, header, footer and navigation | g8 | Home and footer content, viewport-appropriate navigation and mobile drawer |
| B. Listings | g9 | District filter request, populated fixture cards and decoded card images |
| C. Listing Detail | g10 | Gallery controls and images, coordinate source and Comparable request by property ID |
| D. Projects and Project Directory | g11 | Directory and detail navigation, expected projects request, imagery and official attribution |
| E. Account and Login | g12 | Authenticated account rendering and synthetic login with a real routed request |
| F. Market Insights | g1–g4, g6–g7 | Hòa Vang, unknown district, public requests, layout, images and unavailable data |
| G. Market Analytics | g3–g4, g13 | Public-only requests, readable metrics, affirmative ADMIN opt-in, session changes, late response, 401/403 and recovery |
| H. News | g5–g6, g14 | Unavailable message, retry, empty state, art attribution and a successful synthetic envelope |
| I. Posting and valuation preview | g15 | Preview request, explicit address consent, synthetic geocoding, candidate and manual pin confirmation |
| J. Admin Coordinate Review | g16 | Queue and history with authenticated requests and visible controls |
| K. Standalone valuation and Comparable | g17, all 12 WP-02 groups | V1.3 model options, request body, results and evidence, with separate WP-02 checks for buyer budget and reactive authorization |
| L. Chatbot and Advisor | g18, Advisor WP-02 groups | Public chat, next message with session ID, Advisor SAFE request, two evidence sections, score and feature coverage |

Responsive checks include critical element and ancestor bounds, as well as document width. The local `.smartprop/pr37-screenshots/` directory contains 51 PNGs. Representative images are `market-analytics-390.png`, `gallery-768.png` and `admin-coordinate-1440.png`. The two Chromium batch JSON files record each group outcome.

## Production assets and preservation

- Standard `dist` excludes all five withheld district images by filename and SHA-256. All 30 allowlisted assets matched input bytes. Compiled static image references, News art provenance, and fixture entry exclusion passed. Browser checks decoded route imagery, checked informative alternative text and exercised News disclosure and source attribution.
- The cumulative branch diff against approved main contains no changes in `backend`, `ai-services`, `database` or `ops`. This is source preservation evidence for Phase 0 infrastructure, PR #45 RAG, and production valuation and migrations. V1.3 artifact SHA-256 checks matched 8/8 across the two local copies checked against the approved manifest. Chromium separately tests the route-level V1.3 request contract with fixture responses.
- Coordinate provenance and Admin Coordinate Review passed their browser and Node coverage. Comparable's price-independent valuation-support evidence, buyer-budget ceiling, both Advisor evidence lists, feature coverage, and reactive authorization remain preservation requirements in [the integration handoff](SMARTPROP_PR37_WP02_WP04_INTEGRATION_HANDOFF.md).

## Incomplete live verification

| Legacy E2E | Status | Reason and available evidence |
| --- | --- | --- |
| `node e2e/listing-analysis.e2e.mjs` | BLOCKED, NOT_RUN | Needs staged listing data and authenticated services. g10 exercises gallery, coordinate provenance and Comparable through synthetic HTTP. |
| `node e2e/post-location.e2e.mjs` | SKIP | The script exits zero with the auth scenario skipped. g15 exercises consent, geocoder, pin and valuation preview through synthetic HTTP. |
| `node e2e/valuation.e2e.mjs` | BLOCKED, NOT_RUN | Legacy live script requires its runtime and expects legacy V6 output. g15 and g17 exercise the V1.3 UI contract with synthetic HTTP. |
| `node e2e/chatbot.e2e.mjs` | BLOCKED, NOT_RUN | Requires live services and staged fixtures. g18 exercises the chat and Advisor routes with synthetic HTTP. |

News production availability, target Caddy runtime, MySQL live integration, grants and deployed views were not verified. Public News continues to show an unavailable message if its source is absent. Production market accuracy and SQL performance were outside this validation.

## Parallel integration

Read-only assessment against the remote heads below. Path overlaps are scoped to changes since the approved main. Virtual merges also cover conflicts introduced by earlier main history.

| Parallel work | Observed remote SHA | Overlap and preservation |
| --- | --- | --- |
| WP-04 | `a7e02d1002dab707150db15ba9cd37d0fd4c2d09` | No current path overlap. Preserve both Advisor evidence lists, independent feature coverage and the current valuation/Comparable surfaces. |
| WP-05 | `a0a5d88db1a77bc3dc55f9981dd313faa52f5b8b` | No current path overlap. Preserve V1.3 and status/availability semantics on the valuation surfaces. |
| PR #40 | `24fc5711171ff20b94dcb9945d38d2543b8bccf7` | `router.js`. Preserve account linking and the current session-store API and authenticated request invalidation. |
| PR #43 | `f59edf223c98249ee6104c367c34537bd851aea5` | `router.js`, `ListingDetailView.jsx` and `httpClient.js`. Ten virtual conflicts span seven RAG modules, `HybridRecommendationService.java`, `chatPresentation.js` and the Caddyfile. Preserve Phase 0, PR #45 RAG and WP-02 evidence plus PR #37 coordinate and session guards. |

The earlier Market and News run is retained as historical evidence. All counts above apply to the final correction tree.

---

## P2 closure — authentication epoch vs legitimate token refresh

**Finding:** `httpClient.request()` compared the access-token value captured at send time with the
current one and treated any difference as a replaced session. That conflated a legitimate refresh
(issued by this same client after a 401) with logout, account switching or revocation. Consequences:
a late 401 could not reuse the token another request had already refreshed, and a request that had
already **succeeded** at the backend was reported as failed merely because credentials rotated.

**Fix (narrow, in `frontend/src/shared/lib/httpClient.js`):**

- `rotations` — monotonic counter incremented only inside `accept()` after a refresh this client
  performed and scope-verified. A token change is tolerated only when `rotations` advanced and the
  actor is unchanged.
- `identityEpoch` — incremented whenever `status`/actor id/role/status changes. A revocation that is
  briefly restored still invalidates in-flight requests, because the epoch moved even though the
  final snapshot looks identical to the start.
- `epoch` (logout / session replacement) and role/actor boundaries are unchanged.
- Late 401 with an already-completed refresh now **reuses** it instead of starting a second refresh;
  writes still never replay (`AUTH_RETRY_REQUIRED` preserved).
- No credentials are logged.

### Deterministic tests — `frontend/tests/httpClientRefreshEpoch.test.mjs` (9 passed)

| Case | Result |
|---|---|
| A two concurrent GETs, delayed 401 after shared refresh | both recover, exactly 1 refresh, no logout |
| B successful GET completing after a legitimate refresh | resolves, not `SESSION_CHANGED` |
| C mutation confirmed by backend while token rotated | result returned, exactly 1 POST (no replay) |
| D POST receives 401 during refresh | `AUTH_RETRY_REQUIRED`, session recovered, no replay |
| E account replacement mid-flight | `SESSION_CHANGED` |
| F role revoked then restored with the same token | `SESSION_CHANGED` (identity epoch moved) |
| G external abort during shared refresh | `REQUEST_ABORTED`, no logout |
| H different actor, same token | `SESSION_CHANGED` |
| I logout mid-flight | `SESSION_CHANGED`, token not resurrected |

### Fresh regression (this run, exit codes)

| Suite | Command | Result |
|---|---|---|
| httpClient abort + refresh epoch | `node --test tests/httpClient*.test.mjs` | 9 + 6 passed, exit 0 |
| Full frontend recursive | `npm test` | **203 tests, 203 pass, 0 fail**, exit 0 |
| WP-02 Chromium | `WP02_CHROMIUM=... node tests/browser/wp02-browser.mjs` | 8 groups PASS, exit 0 |
| PR #37 market + research authorization | `PR37_BASE=http://127.0.0.1:5173 node e2e/pr37-validation.e2e.mjs --groups=g1,g2,g3` | 3/3 groups, exit 0 |
| Account / login / navigation smoke | `node e2e/pages-smoke.e2e.mjs` | PASS (incl. responsive 390/768/1440), exit 0 |
| District asset integrity | `node e2e/pr37-dist-assets.mjs` | 5 withheld absent, 30 approved byte-identical, exit 0 |
| Vite production build | `npm run build` | PASS (1.74s) |

Integrity: no change under `backend/src`, `ai-services/`, or `db/`; the four V1.3 artifacts hash
identically (`3c56b693…`, `17632bdf…`, `84be275b…`, `419599ec…`); main and other branches untouched.

---

## Verified refresh continuity — edge-case closure

**Finding (P2, follow-up):** the previous fix accepted *any* token change once `rotations` had
advanced and the actor matched. That proved "a refresh happened", not "this token came from it".
After a verified refresh A→B, an externally written token C for the same actor would still satisfy
the old condition, so an in-flight request could bind to credentials this client never issued.

**Fix (still confined to `frontend/src/shared/lib/httpClient.js`):**

- `verifiedTokens` — the set of access tokens this client obtained from a refresh it performed and
  scope-verified. A token change is tolerated **only** when the new token is in that chain and the
  old one is not; anything else is `SESSION_CHANGED`.
- `accept(result, current, { verified })` — refresh passes `verified: true` and extends the chain;
  session creation (login, Google completion) now **invalidates the epoch and clears the chain**
  instead of counting as a rotation. This separates credential renewal from session creation.
- `rotate()` captures `identityEpoch` and validates it in every `ensureRefreshScope()` step (before
  CSRF, after CSRF, after refresh), so an obsolete refresh cannot overwrite a session whose
  identity changed mid-flight.
- Refresh flights carry a scope key `${epoch}:${identityEpoch}:${token}`; a different session starts
  its own flight instead of joining an obsolete one.

### New deterministic tests (`frontend/tests/httpClientRefreshEpoch.test.mjs`, 15 cases)

| Case | Assertion |
|---|---|
| A | two concurrent GETs share one refresh, both recover, no logout |
| B | a GET that succeeds after a verified refresh is not `SESSION_CHANGED` |
| C | a confirmed mutation returns its result; exactly one POST, never replayed |
| D | POST + 401 still yields `AUTH_RETRY_REQUIRED` with `sessionRecovered` |
| E | account replacement rejects the stale result |
| F | role revoked then restored still rejects (identity epoch moved) |
| G | external abort during a shared refresh → `REQUEST_ABORTED`, no logout |
| H | **different actor with the same token** → `SESSION_CHANGED` |
| I | logout mid-flight rejects and does not resurrect the token |
| J | two verified refreshes in one session keep an in-flight request valid |
| K | externally replaced token after a verified refresh → `SESSION_CHANGED` |
| L | a delayed 401 after external replacement does **not** retry with the foreign token and does **not** trigger a second refresh |
| M | role revocation while CSRF/refresh is pending cannot overwrite the session |
| N | multiple waiters all reject when identity changes mid-refresh |
| O | a new session during a shared refresh does not reuse the obsolete flight |

### Fresh verification (this run, with exit codes)

| Suite | Command | Result |
|---|---|---|
| httpClient abort + refresh epoch | `node --test tests/httpClient*.test.mjs` | **32 tests, 32 pass, 0 fail**, exit 0 |
| Full frontend recursive | `npm test` | **209 tests, 209 pass, 0 fail**, exit 0 |
| WP-02 Chromium (all groups) | `WP02_CHROMIUM=… node tests/browser/wp02-browser.mjs` | **12 groups PASS**, exit 0 |
| PR #37 market groups | `PR37_BASE=<fixture preview> node e2e/pr37-validation.e2e.mjs --groups=g1,g2,g3,g13` | **4/4 groups**, exit 0 |
| Authenticated research authorization | same run, `g13_market_authorization` | **PASS** (needs the fixture-only dist from `e2e/pr37-preview.mjs`; g1–g3 alone do not cover it) |
| Account / login / navigation | `node e2e/pages-smoke.e2e.mjs` | PASS incl. responsive 390/768/1440, exit 0 |
| Vite production build | `npm run build` | PASS (2.97s) |

Note on scope: g1–g3 exercise anonymous market behaviour only. The authenticated research
authorization path is verified **by g13**, which requires the fixture-only build served by
`e2e/pr37-preview.mjs` (synthetic session entry), not the plain dev server.

---

## Refresh continuity — bounded generation model (supersedes the token Set)

**Defect in the previous fix:** `verifiedTokens.has(latest.token) && !verifiedTokens.has(snapshot.token)`
required the *old* token to be absent from the set, so a second legitimate refresh B→C was rejected
because B was already recorded. It also kept an unbounded history of access tokens.

**Replacement (still confined to `frontend/src/shared/lib/httpClient.js`):**

- **Bounded state**: `currentCredential` (the one credential this client installed) plus
  `credentialGen` (a counter). No history is retained.
- **Continuity rule** in `ensureCurrent`: a token change is tolerated only when the generation moved
  since the request started **and** the live token still equals `currentCredential`. This holds for
  any generation (A→B→C…), and fails as soon as the credential is not ours.
- **External replacement detection**: the synchronous session subscription compares the live token
  with `currentCredential`; our own writes are flagged so they are not misread. An external write
  nulls `currentCredential` and advances the generation, so continuity breaks immediately — even for
  the same actor, and even if the original token is later restored.
- **Session creation** (login, Google completion) invalidates the epoch and advances the generation;
  it is never counted as a rotation.
- **Flight ownership**: the `finally` block only clears the shared reference when the completing
  flight is still the owner, so an older flight finishing first cannot release a newer session's.
  Flights are keyed by `epoch:identityEpoch:token`.
- **Refresh result identity**: renewing an already-authenticated session rejects a refresh payload
  for a different account; only initial cookie restoration may establish a new identity.
- `rotate()` validates `identityEpoch` before CSRF, after CSRF and after the refresh response.

### Tests (`frontend/tests/httpClientRefreshEpoch.test.mjs`, 19 cases)

New/rewritten: **J** pending GET *and* POST started at generation B survive B→C (GET succeeds,
confirmed POST succeeds, one POST only, no `SESSION_CHANGED`, no logout) · **J2** a delayed 401 from
B after C is installed recovers with exactly two refreshes · **K** external replacement after a
verified refresh is rejected · **L** delayed 401 after external replacement neither retries with the
foreign token nor refreshes again · **M** revocation while CSRF/refresh pendings cannot overwrite
the session · **N** multiple waiters all reject when identity changes · **O** old refresh answers
late with the old actor while a new session's refresh answers with the new actor: the old request is
rejected, the **new request recovers**, and the final token/actor are the new session's · **P** only
the owning flight clears the shared reference, and a third request joins the surviving flight
(exactly one refresh for the new session) · **Q** renewing an authenticated session rejects a payload
for another account without installing it · **R** five consecutive rotations keep an in-flight
request valid with no retained history. A–I unchanged.

### Fresh verification (this run, exit codes)

| Suite | Result |
|---|---|
| `node --test tests/httpClient*.test.mjs` | **36 tests, 36 pass, 0 fail**, exit 0 |
| `npm test` | **213 tests, 213 pass, 0 fail**, exit 0 |
| WP-02 Chromium | **12 groups PASS**, exit 0 |
| PR #37 g1, g2, g3, g13 (fixture preview) | **4/4 groups**, exit 0 |
| Account / login / navigation smoke | PASS, exit 0 |
| Vite production build | PASS (2.26s) |

g1–g3 remain anonymous market checks; the authenticated research authorization path is covered by
**g13**, which needs the fixture-only dist from `e2e/pr37-preview.mjs`.
