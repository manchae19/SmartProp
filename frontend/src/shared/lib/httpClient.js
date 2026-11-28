function abortError() {
  return Object.assign(Error("Yêu cầu đã bị hủy."), { name: "AbortError", code: "REQUEST_ABORTED" });
}

function sessionChanged() {
  return Object.assign(Error("Phiên đã thay đổi."), { code: "SESSION_CHANGED" });
}

function authorityOf(user) {
  return JSON.stringify([user?.id ?? user?.userId ?? user?.sub ?? user?.email, user?.role, user?.status]);
}

function sameActor(previous, next) {
  return previous.status === next.status && authorityOf(previous.user) === authorityOf(next.user);
}

// Claims from the auth response fence UI continuity. The backend validates the JWT and access.
function accessSession(token) {
  if (typeof token !== "string" || !token) return null;
  const parts = token.split(".");
  if (parts.length !== 3 || !parts.every(part => part.length % 4 !== 1 && /^[A-Za-z0-9_-]+$/.test(part))) return null;
  try {
    const decode = part => JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/")));
    const header = decode(parts[0]);
    if (typeof header?.alg !== "string" || !header.alg || header.alg === "none") return null;
    const payload = decode(parts[1]);
    const { iss, sub, jti, ver } = payload || {};
    if (iss === "smartprop" && typeof sub === "string" && sub
      && typeof jti === "string" && jti && Number.isSafeInteger(ver) && ver >= 0) {
      return { sub, jti, ver };
    }
  } catch {
    // opaque or malformed token: no claims to compare
  }
  return null;
}

function identityOf(snapshot) {
  return JSON.stringify([
    snapshot?.status ?? null,
    // PR48 keeps a session generation on the store; including it makes a same-account new session
    // a different identity, which is exactly what the shared contract requires.
    snapshot?.authGeneration ?? null,
    snapshot?.authTransition === true,
    authorityOf(snapshot?.user),
  ]);
}

async function waitForRefresh(flight, signal) {
  if (!signal) return flight;
  if (signal.aborted) throw abortError();
  let onAbort;
  try {
    return await Promise.race([
      flight,
      new Promise((_, reject) => {
        onAbort = () => reject(abortError());
        signal.addEventListener("abort", onAbort, { once: true });
      })
    ]);
  } finally {
    signal.removeEventListener("abort", onAbort);
  }
}

// Access tokens stay in memory. Refresh credentials are sent only as HttpOnly cookies.
export function createHttpClient({
  baseUrl,
  session,
  refreshEnabled = false,
  fetcher = (...args) => fetch(...args),
  expired = () => {},
  clear = () => {},
  lock = null,
  onState = () => {},
  activity = () => false,
  timeoutForPath = path => path === "/recommendations/research" ? 180000 : path === "/geocoding/search" ? 20000 : 15000
}) {
  let refreshFlight = null,
    initialization = null,
    initialized = false,
    epoch = 0,
    // Bounded credential state: the credential this client currently trusts plus a generation
    // counter. No history of past tokens is kept. A request may survive a token change only when
    // the credential generation moved AND the live token still equals the credential we installed;
    // an external replacement (even for the same actor, even if the old token is later restored)
    // drops `currentCredential`, so nothing matches and continuity is broken immediately.
    currentCredential = session.getSnapshot().token || null,
    lastObservedToken = currentCredential,
    credentialGen = 0,
    // Incremented on every credential write this client did not perform. Requests capture it and
    // reject when it moved, so an external A -> X -> A round-trip cannot restore continuity even
    // though the final token equals the original one.
    scopeGen = 0,
    // identityEpoch: incremented whenever the actor/role/status changes, so a revocation that is
    // briefly restored cannot make a restricted response look current again.
    identityEpoch = 0,
    lastIdentity = identityOf(session.getSnapshot()),
    lastAuthority = authorityOf(session.getSnapshot().user),
    lastGeneration = session.getSnapshot().authGeneration;
  // Set while this client itself writes the credential, so our own refresh is not mistaken for an
  // external replacement. The subscription is synchronous, so the check happens in the same tick.
  let applyingInternalCredential = false;
  function installCredential(token, edit) {
    currentCredential = token;
    lastObservedToken = token;
    applyingInternalCredential = true;
    try {
      session.edit(draft => {
        draft.token = token;
        edit(draft);
      });
    } finally {
      applyingInternalCredential = false;
    }
  }
  if (typeof session.subscribe === "function") {
    session.subscribe(() => {
      const snapshot = session.getSnapshot();
      const next = identityOf(snapshot);
      if (next !== lastIdentity) {
        lastIdentity = next;
        identityEpoch += 1;
      }
      const token = snapshot.token || null;
      const authority = authorityOf(snapshot.user);
      const external = !applyingInternalCredential;
      const replacedToken = external && token !== lastObservedToken;
      const replacedAuthority = external && authority !== lastAuthority;
      const needsGeneration = (replacedToken || replacedAuthority) && lastGeneration === snapshot.authGeneration;
      if (replacedToken) {
        // Someone else wrote the credential: stop trusting it for continuity and mark the whole
        // scope as discontinuous. A later internal refresh does not undo this.
        currentCredential = null;
        credentialGen += 1;
        scopeGen += 1;
      }
      lastObservedToken = token;
      lastAuthority = authority;
      lastGeneration = snapshot.authGeneration;
      if (needsGeneration) session.edit(advanceGeneration);
    });
  }
  const state = (status, error = null) => {
    session.edit(draft => {
      draft.status = status;
      draft.error = error;
    });
    onState(status, error);
  };
  const terminal = e => e?.status === 401 && e?.code !== "AUTH_RETRY_REQUIRED" || e?.status === 403 && e?.code === "ACCOUNT_LOCKED";
  function advanceGeneration(draft) {
    draft.authGeneration = (draft.authGeneration ?? 0) + 1;
  }
  function invalidate() {
    epoch++;
    initialized = false;
    session.edit(draft => {
      advanceGeneration(draft);
      draft.authTransition = false;
    });
  }
  function beginAuthChange() {
    epoch++;
    session.edit(draft => {
      advanceGeneration(draft);
      draft.authTransition = true;
    });
    return epoch;
  }
  function finishAuthChange(current) {
    if (current === epoch) session.edit(draft => { draft.authTransition = false; });
  }
  function expire(redirect = true, { reinitialize = false } = {}) {
    epoch++;
    initialized = !reinitialize;
    installCredential(null, draft => {
      draft.user = null;
      draft.status = "UNAUTHENTICATED";
      draft.error = null;
      advanceGeneration(draft);
      draft.authTransition = false;
    });
    clear();
    onState("UNAUTHENTICATED", null);
    if (redirect) expired();
  }
  function unavailable(e) {
    state("UNAVAILABLE", e?.message || "Không thể kiểm tra phiên. Vui lòng thử lại.");
  }
  function accept(result, current, { replaceScope = false } = {}) {
    if (current !== epoch) throw sessionChanged();
    if (replaceScope) epoch++;
    credentialGen++;
    initialized = true;
    installCredential(result.accessToken, draft => {
      draft.user = result.user;
      draft.status = "AUTHENTICATED";
      draft.error = null;
      if (replaceScope) advanceGeneration(draft);
    });
    onState("AUTHENTICATED", null);
    return result;
  }
  async function send(path, {
    method = "GET",
    body,
    authenticated = true,
    responseType = "json",
    headers: extra = {},
    signal: externalSignal = null
  } = {}) {
    if (externalSignal?.aborted) throw abortError();
    const headers = {
        Accept: "application/json",
        ...extra
      },
      multipart = typeof FormData !== "undefined" && body instanceof FormData;
    if (body !== undefined && !multipart) headers["Content-Type"] = "application/json";
    if (authenticated && session.getSnapshot().token) headers.Authorization = "Bearer " + session.getSnapshot().token;
    if ((authenticated && session.getSnapshot().token || path === "/auth/refresh") && activity()) headers["X-Session-Activity"] = "true";
    const duration = timeoutForPath(path);
    if (!Number.isFinite(duration) || duration < 1 || duration > 180000) throw Error("Invalid bounded request timeout");
    const controller = new AbortController(),
      onExternalAbort = () => controller.abort();
    externalSignal?.addEventListener("abort", onExternalAbort, { once: true });
    const timeout = setTimeout(() => controller.abort(), duration);
    try {
      const response = await fetcher(baseUrl + path, {
        method,
        headers,
        body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
        signal: controller.signal,
        ...(refreshEnabled ? {
          credentials: "include"
        } : {})
      });
      if (controller.signal.aborted) throw controller.signal.reason;
      const data = response.status === 204 ? null : response.ok && responseType === "blob" ? await response.blob() : await response.json().catch(() => null);
      if (controller.signal.aborted) throw controller.signal.reason;
      if (!response.ok) {
        const e = Error(data?.message || "Yêu cầu thất bại (" + response.status + ")");
        e.status = response.status;
        e.code = data?.code;
        e.fields = data?.fields || {};
        const retry = response.headers.get("Retry-After");
        e.retryAfter = retry && /^\d+$/.test(retry) ? Number(retry) : undefined;
        throw e;
      }
      return data;
    } catch (e) {
      if (externalSignal?.aborted) throw abortError();
      if (e?.status && !controller.signal.aborted) throw e;
      const timedOut = controller.signal.aborted || e?.name === "AbortError";
      throw Object.assign(Error(timedOut ? "Yêu cầu quá thời gian. Vui lòng thử lại." : "Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối."), {
        code: timedOut ? "REQUEST_TIMEOUT" : "NETWORK_ERROR"
      });
    } finally {
      clearTimeout(timeout);
      if (externalSignal) externalSignal.removeEventListener("abort", onExternalAbort);
    }
  }
  const csrf = () => send("/auth/csrf", {
    authenticated: false
  });
  /**
   * @param {{allowNewIdentity?: boolean}} options allowNewIdentity is true only for the initial
   *   cookie-based restoration, where the session is created rather than renewed.
   */
  function rotate({ allowNewIdentity = false } = {}) {
    const startedSnapshot = session.getSnapshot();
    if (startedSnapshot.authTransition) return Promise.reject(sessionChanged());
    // A flight is only reusable inside the exact session scope it was started in; a new session
    // must never join an obsolete refresh that belongs to the previous one.
    const flightKey = `${epoch}:${identityEpoch}:${scopeGen}:${credentialGen}:${allowNewIdentity}`;
    if (refreshFlight?.key === flightKey) return refreshFlight.promise;
    const current = epoch,
      startedIdentity = identityEpoch,
      startedScopeGen = scopeGen,
      started = startedSnapshot,
      ensureRefreshScope = () => {
        const latest = session.getSnapshot();
        if (current !== epoch || identityEpoch !== startedIdentity) throw sessionChanged();
        // An external A -> X -> A round-trip leaves the token unchanged but breaks the scope.
        if (scopeGen !== startedScopeGen) throw sessionChanged();
        if (started.token !== latest.token || !sameActor(started, latest)) throw sessionChanged();
      },
      run = async () => {
        ensureRefreshScope();
        const c = await csrf();
        ensureRefreshScope();
        const result = await send("/auth/refresh", {
          method: "POST",
          authenticated: false,
          headers: {
            [c.headerName]: c.token
          }
        });
        ensureRefreshScope();
        if (allowNewIdentity) return accept(result, current, { replaceScope: true });
        const before = accessSession(started.token);
        const after = accessSession(result?.accessToken);
        const actor = result?.user?.id ?? result?.user?.userId ?? result?.user?.sub;
        if (!before || !after || before.sub !== after.sub || before.jti !== after.jti
            || actor == null || String(actor) !== after.sub) {
          // A different or unprovable session requires an explicit initialization of the cookie.
          expire(false, { reinitialize: true });
          throw sessionChanged();
        }
        const accessChanged = before.ver !== after.ver || !sameActor(started, { ...started, user: result.user });
        return accept(result, current, { replaceScope: accessChanged });
      };
    const flight = { key: flightKey };
    flight.promise = Promise.resolve().then(() => lock ? lock(run) : run()).finally(() => {
      // Only the owning flight may clear the shared reference; a newer session's flight must
      // survive an older one finishing first.
      if (refreshFlight === flight) refreshFlight = null;
    });
    refreshFlight = flight;
    return flight.promise;
  }
  async function request(path, options = {}) {
    const started = session.getSnapshot();
    const current = epoch;
    const startedIdentity = identityEpoch;
    const startedCredentialGen = credentialGen;
    const startedScopeGen = scopeGen;
    const authenticated = options.authenticated !== false;
    const redirect = options.redirectOnSessionExpiry !== false;
    if (authenticated && started.authTransition) throw sessionChanged();
    /**
     * A response is stale when the session was replaced, the actor/role/status changed, or the
     * token was replaced by something this client did not refresh itself. A token that changed
     * because of our own verified refresh keeps the request valid - that is a credential renewal,
     * not a different session.
     */
    const ensureCurrent = snapshot => {
      if (options.signal?.aborted) throw abortError();
      const latest = session.getSnapshot();
      if (!authenticated) return;
      if (current !== epoch || identityEpoch !== startedIdentity) throw sessionChanged();
      if (scopeGen !== startedScopeGen) throw sessionChanged();
      if (!sameActor(snapshot, latest)) throw sessionChanged();
      if (snapshot.token !== latest.token) {
        // Continuity requires (a) a verified refresh happened since this request started and
        // (b) the live token is still exactly the credential this client installed. That holds for
        // any generation (A->B->C), and fails for an external replacement because it nulls
        // `currentCredential`, even when the actor is unchanged or the old token returns.
        const renewedByUs = credentialGen !== startedCredentialGen
          && currentCredential !== null
          && latest.token === currentCredential;
        if (!renewedByUs) throw sessionChanged();
      }
    };
    try {
      const result = await send(path, options);
      ensureCurrent(started);
      return result;
    } catch (e) {
      ensureCurrent(started);
      if (authenticated && terminal(e)) {
        // ensureCurrent has already verified that any changed credential came from our own refresh.
        const alreadyRotated = started.token !== session.getSnapshot().token;
        if (refreshEnabled && started.token && e.status === 401 && (alreadyRotated || !path.startsWith("/auth/"))) {
          try {
            if (!alreadyRotated) await waitForRefresh(rotate(), options.signal);
          } catch (next) {
            if (next.code !== "REQUEST_ABORTED" && next.code !== "SESSION_CHANGED") {
              ensureCurrent(started);
              if (terminal(next)) expire(redirect);else unavailable(next);
            }
            throw next;
          }
          const retryScope = session.getSnapshot();
          ensureCurrent(started);
          // Renew credentials but require explicit resubmission for writes; never duplicate an uncertain mutation.
          if (!["GET", "HEAD", "OPTIONS"].includes((options.method || "GET").toUpperCase())) throw Object.assign(Error("Phiên đã được gia hạn. Vui lòng thực hiện lại thao tác vừa gửi."), {
            status: 401,
            code: "AUTH_RETRY_REQUIRED",
            sessionRecovered: true
          });
          try {
            const result = await send(path, options);
            ensureCurrent(retryScope);
            return result;
          } catch (next) {
            ensureCurrent(retryScope);
            if (terminal(next) && retryScope.token === session.getSnapshot().token) expire(redirect);
            throw next;
          }
        }
        if (!alreadyRotated) expire(redirect);
      }
      throw e;
    }
  }
  function initialize({
    force = false
  } = {}) {
    if (session.getSnapshot().authTransition) return Promise.resolve(session.getSnapshot().status);
    if (initialization?.stillCurrent()) return initialization.promise;
    if (initialized && !force) return Promise.resolve(session.getSnapshot().status);
    state("INITIALIZING");
    const current = epoch;
    // Captured before any async work: `started` used to be an undeclared rotate()-local name.
    const startedSnapshot = session.getSnapshot();
    const startedIdentity = identityEpoch;
    const startedScopeGen = scopeGen;
    const startedToken = startedSnapshot.token;
    /** An obsolete initialization must not commit, expire, or overwrite a newer session. */
    const stillCurrent = () => current === epoch
      && identityEpoch === startedIdentity
      && scopeGen === startedScopeGen
      && (session.getSnapshot().token ?? null) === (startedToken ?? null);
    const flight = { stillCurrent };
    flight.promise = (async () => {
      try {
        if (startedToken) {
          try {
            const profile = await send("/users/me");
            if (stillCurrent()) {
              session.edit(draft => {
                draft.user = profile;
                draft.status = "AUTHENTICATED";
                draft.error = null;
              });
              initialized = true;
              onState("AUTHENTICATED", null);
            }
          } catch (e) {
            if (!terminal(e) || !refreshEnabled) throw e;
            if (!stillCurrent()) throw sessionChanged();
            // An existing access token means an existing session: the renewal must not adopt a
            // different account. Without a token this is cookie-based restoration.
            await rotate();
          }
        } else if (refreshEnabled) await rotate({ allowNewIdentity: true });
        else if (stillCurrent()) {
          initialized = true;
          state("UNAUTHENTICATED");
        }
      } catch (e) {
        if (stillCurrent()) {
          if (terminal(e)) expire(false);else if (e.code !== "SESSION_CHANGED") unavailable(e);
        }
      } finally {
        if (stillCurrent()) initialized = true;
      }
      return session.getSnapshot().status;
    })().finally(() => {
      // only the owning initialization may clear the shared reference
      if (initialization === flight) initialization = null;
    });
    initialization = flight;
    return flight.promise;
  }
  async function changeAuthentication(operation) {
    const current = beginAuthChange();
    const ensureOwner = () => {
      if (current !== epoch) throw sessionChanged();
    };
    const run = () => {
      ensureOwner();
      return operation(current, ensureOwner);
    };
    try {
      // Cookie mutations share the existing refresh lock when the browser supports it.
      return await (lock ? lock(run) : run());
    } finally {
      finishAuthChange(current);
    }
  }
  function login(body) {
    return changeAuthentication(async current => accept(await send("/auth/login", {
      method: "POST",
      authenticated: false,
      body,
      headers: refreshEnabled ? { "X-Refresh-Session": "true" } : {}
    }), current));
  }
  function logout() {
    return changeAuthentication(async (_, ensureOwner) => {
      if (refreshEnabled) {
        const c = await csrf();
        ensureOwner();
        const options = {
          method: "POST",
          headers: { [c.headerName]: c.token }
        };
        try {
          await send("/auth/logout", options);
        } catch (e) {
          if (e.status !== 401) throw e;
          ensureOwner();
          await send("/auth/logout", { ...options, authenticated: false });
        }
      } else await send("/auth/logout", { method: "POST" });
      ensureOwner();
      expire(false);
      return true;
    });
  }
  function google() {
    return changeAuthentication(async (current, ensureOwner) => {
      const c = await csrf();
      ensureOwner();
      return accept(await send("/auth/oauth2/complete", {
        method: "POST",
        authenticated: false,
        headers: { [c.headerName]: c.token }
      }), current);
    });
  }
  /** Read-only bounded scope, for the shared-session contract and diagnostics. */
  function sessionScope() {
    const snapshot = session.getSnapshot();
    return {
      epoch,
      identityEpoch,
      credentialGen,
      scopeGen,
      authGeneration: snapshot.authGeneration ?? null,
      // never expose the credential itself
      authenticated: Boolean(snapshot.token),
    };
  }
  return {
    request,
    sessionScope,
    login,
    google,
    logout,
    invalidate,
    clearSession: () => expire(false, { reinitialize: true }),
    initialize,
    unavailable,
    restore: async () => {
      await initialize({
        force: true
      });
      return session.getSnapshot().status === "AUTHENTICATED";
    }
  };
}
