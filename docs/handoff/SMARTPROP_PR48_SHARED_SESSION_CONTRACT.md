# PR48 shared session contract (handoff, not merged)

**PR37 HEAD:** `0fdf48f` → this change · **PR48 reviewed SHA:** `287b4b2` · **main:** `1c67a27`

PR48 is **not** merged into PR37 and its branch was not modified. This document defines the single
bounded session architecture both branches must share, and records the compatibility tests that
already pass against PR37's client using synthetic tokens only.

## 1. One implementation, two responsibilities

| Concern | Owner |
|---|---|
| Bounded session/credential scope, request continuity, refresh flights, abort, write replay policy | `frontend/src/shared/lib/httpClient.js` (PR37) |
| Google linking flow, `authGeneration` bookkeeping, JWT `sub/jti/ver` decoding for UI | PR48 |

There must not be a second session implementation. PR48 should keep using `createHttpClient` and
store its generation on the same `session` store.

## 2. State kept by the client (bounded, no token history)

```
epoch            session replacement / logout
identityEpoch    status, actor id, role, account status, authGeneration
credentialGen    verified credential renewals (refresh only, never session creation)
scopeGen         every credential write the client did not perform (discontinuity)
currentCredential the single credential the client installed (or null after an external write)
```

`client.sessionScope()` returns exactly those values plus `token`/`authenticated`, so PR48 can assert
alignment instead of guessing. It never exposes history.

## 3. Contract rules

1. **Continuity** requires the credential generation to have moved *and* the live token to equal
   `currentCredential`. Holds across A→B→C→…; fails for any credential this client did not install.
2. **External replacement is terminal for in-flight work.** The synchronous store subscription
   detects it, nulls `currentCredential` and bumps `scopeGen`, so A→X→A (same token restored) is
   still `SESSION_CHANGED`, and a later valid refresh cannot re-validate an obsolete scope.
3. **Session creation** (login, Google completion, and PR48's `authGeneration` bump) invalidates the
   epoch/identity: requests from the previous session never survive, even for the same account.
4. **Renewal vs new session.** A refresh keeps `authGeneration`; a new session increments it. The
   client treats `authGeneration` as part of identity, which is what gives same-account new-session
   isolation without a second implementation.
5. **Refresh result identity.** Renewing an authenticated session rejects a payload for a different
   `sub`; only initial cookie restoration may establish an identity.
6. **Flight ownership.** A flight is keyed by `epoch:identityEpoch:token`; only the owning flight
   clears the shared reference, so an older flight finishing first cannot release a newer one.
7. **JWT is UI-only.** `sub/jti/ver` are decoded for continuity and display; authorization remains
   server-authoritative. `ver` changes that accompany a role/status change invalidate restricted
   responses via `identityEpoch`.
8. **Writes are never replayed.** A POST that hits 401 still returns `AUTH_RETRY_REQUIRED`.
9. **Abort** stays external-signal driven; cancellation never logs out.
10. **JWT continuity (implemented)**: `sub` change or `jti` change inside a renewal is a different
    session; a `ver` change is a legitimate server re-issue. Opaque tokens keep the structural checks.
11. **Credential privacy (implemented)**: `sessionScope()` returns generations and flags only, never
    the token, and no token history is retained.
12. **Open**: `authTransition` must be raised before the login round-trip, pending linking responses
    must be retired at that instant, and a late response must never expire a session that a later
    refresh already renewed.

## 4. Compatibility tests (synthetic fixtures, no PR48 code imported)

`frontend/tests/googleLinkSessionContract.test.mjs` builds unsigned fixtures of the PR48 payload
shape (`{iss:'smartprop', sub, jti, ver, iat}`) and asserts:

- `authGeneration` participates in identity: same account + new generation ⇒ `SESSION_CHANGED`.
- A new `jti` inside the same generation is still an external replacement ⇒ `SESSION_CHANGED`.
- A `ver` bump with a role change invalidates a restricted in-flight response.
- A verified refresh keeps `jti` and `authGeneration` (renewal ≠ new session).
- `sessionScope()` exposes one bounded scope and no token history.
- Logout clears the credential and invalidates pending work.

## 5. Integration steps for PR48 (when it merges)

1. Keep `createHttpClient` as the only session/HTTP implementation.
2. Store the server-issued `authGeneration` on the same `session` store; bump it on login, Google
   completion and cross-tab session replacement.
3. Do not decode the JWT for authorization decisions; keep the backend authoritative.
4. Re-run `frontend/tests/googleLinkSessionContract.test.mjs` plus `httpClient*` suites after rebase.
5. Anything that needs a "new session, same user" signal should use `authGeneration`, not a token
   comparison.

## 6. Known limitations

- Cross-tab coordination still relies on the store subscription; there is no BroadcastChannel
  handshake, and this contract does not add one.
- `authGeneration` is only honoured when PR48 actually writes it; with PR37 alone the client behaves
  exactly as before.
