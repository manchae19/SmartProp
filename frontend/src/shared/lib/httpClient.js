function abortError() {
  return Object.assign(Error("Yêu cầu đã bị hủy."), { name: "AbortError", code: "REQUEST_ABORTED" });
}

function sessionChanged() {
  return Object.assign(Error("Phiên đã thay đổi."), { code: "SESSION_CHANGED" });
}

function sameActor(previous, next) {
  const identity = user => user?.id ?? user?.userId ?? user?.sub ?? user?.email;
  return previous.status === next.status
    && identity(previous.user) === identity(next.user)
    && previous.user?.role === next.user?.role
    && previous.user?.status === next.user?.status;
}

/**
 * Server-issued session claims, used ONLY to keep the UI consistent. Authorization stays with the
 * server: every request is still authorized by the backend, and nothing here grants access.
 *
 * Returns a stable "sub|jti|ver" string, or null when the token is opaque/unparseable.
 */
function accessSession(token) {
  if (typeof token !== "string" || !token) return null;
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    const { iss, sub, jti, ver } = payload || {};
    if (iss === "smartprop" && typeof sub === "string" && sub
      && typeof jti === "string" && jti && Number.isInteger(ver)) {
      return JSON.stringify([sub, jti, ver]);
    }
  } catch {
    // opaque or malformed token: no claims to compare
  }
  return null;
}

/** Same user and same server session (jti), regardless of ver. */
function sameServerSession(left, right) {
  if (!left || !right) return null;
  try {
    const a = JSON.parse(left);
    const b = JSON.parse(right);
    return a[0] === b[0] && a[1] === b[1];
  } catch {
    return null;
  }
}

function identityOf(snapshot) {
  return JSON.stringify([
    snapshot?.status ?? null,
    // PR48 keeps a session generation on the store; including it makes a same-account new session
    // a different identity, which is exactly what the shared contract requires.
    snapshot?.authGeneration ?? null,
    snapshot?.user?.id ?? snapshot?.user?.userId ?? snapshot?.user?.sub ?? snapshot?.user?.email ?? null,
    snapshot?.user?.role ?? null,
    snapshot?.user?.status ?? null,
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
    refreshFlightKey = null,
    initialization = null,
    initialized = false,
    epoch = 0,
    // Bounded credential state: the credential this client currently trusts plus a generation
    // counter. No history of past tokens is kept. A request may survive a token change only when
    // the credential generation moved AND the live token still equals the credential we installed;
    // an external replacement (even for the same actor, even if the old token is later restored)
    // drops `currentCredential`, so nothing matches and continuity is broken immediately.
    currentCredential = session.getSnapshot().token || null,
    credentialGen = 0,
    // Incremented on every credential write this client did not perform. Requests capture it and
    // reject when it moved, so an external A -> X -> A round-trip cannot restore continuity even
    // though the final token equals the original one.
    scopeGen = 0,
    // rotations: monotonic count of verified refreshes (refreshes only - never session creation).
    rotations = 0,
    // identityEpoch: incremented whenever the actor/role/status changes, so a revocation that is
    // briefly restored cannot make a restricted response look current again.
    identityEpoch = 0,
    lastIdentity = identityOf(session.getSnapshot());
  // Set while this client itself writes the credential, so our own refresh is not mistaken for an
  // external replacement. The subscription is synchronous, so the check happens in the same tick.
  let applyingInternalCredential = false;
  function installCredential(token) {
    applyingInternalCredential = true;
    try {
      session.edit(draft => draft.token = token);
    } finally {
      applyingInternalCredential = false;
    }
    currentCredential = token;
  }
  if (typeof session.subscribe === "function") {
    session.subscribe(() => {
      const snapshot = session.getSnapshot();
      const next = identityOf(snapshot);
      if (next !== lastIdentity) {
        lastIdentity = next;
        identityEpoch += 1;
      }
      if (!applyingInternalCredential && snapshot.token !== currentCredential) {
        // Someone else wrote the credential: stop trusting it for continuity and mark the whole
        // scope as discontinuous. A later internal refresh does not undo this.
        currentCredential = null;
        credentialGen += 1;
        scopeGen += 1;
      }
    });
  }
  const state = (status, error = null) => {
    session.edit(draft => draft.status = status);
    session.edit(draft => draft.error = error);
    onState(status, error);
  };
  const terminal = e => e?.status === 401 && e?.code !== "AUTH_RETRY_REQUIRED" || e?.status === 403 && e?.code === "ACCOUNT_LOCKED";
  function invalidate() {
    epoch++;
    // PR48 reads authGeneration/authTransition from the same store for UI continuity.
    session.edit(draft => { draft.authGeneration = epoch; });
  }
  function beginAuthChange() {
    epoch++;
    session.edit(draft => {
      draft.authGeneration = epoch;
      draft.authTransition = true;
    });
  }
  function finishAuthChange(current) {
    if (current === epoch) session.edit(draft => { draft.authTransition = false; });
  }
  function expire(redirect = true) {
    invalidate();
    clear();
    session.edit(draft => draft.token = null);
    session.edit(draft => {
      draft.user = null;
      draft.authGeneration = epoch;
      draft.authTransition = false;
    });
    initialized = true;
    state("UNAUTHENTICATED");
    if (redirect) expired();
  }
  function unavailable(e) {
    state("UNAVAILABLE", e?.message || "Không thể kiểm tra phiên. Vui lòng thử lại.");
  }
  /**
   * @param {boolean} verified true only for a refresh this client performed and scope-checked.
   *   Session creation (login, Google completion) is NOT a rotation: it starts a new session, so
   *   it invalidates the epoch and clears the verified chain instead of extending it.
   */
  function accept(result, current, { verified = false } = {}) {
    if (current !== epoch) throw sessionChanged();
    installCredential(result.accessToken);
    session.edit(draft => draft.user = result.user);
    if (verified) {
      credentialGen += 1;
      rotations += 1;
    } else {
      // Session creation starts a new scope: nothing from the previous session may be reused.
      invalidate();
      credentialGen += 1;
    }
    session.edit(draft => {
      // a verified renewal stays inside the same session generation
      if (!verified) draft.authGeneration = epoch;
      draft.authTransition = false;
    });
    state("AUTHENTICATED");
    initialized = true;
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
    // A flight is only reusable inside the exact session scope it was started in; a new session
    // must never join an obsolete refresh that belongs to the previous one.
    const flightKey = `${epoch}:${identityEpoch}:${scopeGen}:${startedSnapshot.token}`;
    if (refreshFlight && refreshFlightKey === flightKey) return refreshFlight;
    let claimsVerChanged = false;
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
        // Renewing an existing authenticated session must not install a response that belongs to
        // a different account. Initial restoration is allowed to establish the identity.
        if (!allowNewIdentity && started.user) {
          const mine = identityOf({ status: "AUTHENTICATED", user: started.user });
          const theirs = identityOf({ status: "AUTHENTICATED", user: result.user });
          if (mine !== theirs) throw sessionChanged();
        }
        // A renewal may rotate the access token, but it must stay inside the same server session.
        // A different `sub` is another account; a different `jti` is another session for the same
        // account. Neither is an ordinary credential renewal. A changed `ver` IS legitimate: the
        // server re-issued the claims (e.g. role change), so the identity epoch must move.
        if (!allowNewIdentity) {
          const before = accessSession(started.token);
          const after = accessSession(result.accessToken);
          if (before && after) {
            const [oldSub, oldJti, oldVer] = JSON.parse(before);
            const [newSub, newJti, newVer] = JSON.parse(after);
            if (oldSub !== newSub) throw sessionChanged();
            if (oldJti !== newJti) throw sessionChanged();
            if (oldVer !== newVer) claimsVerChanged = true;
          }
        }
        return accept(result, current, { verified: true });
      };
    refreshFlightKey = flightKey;
    const flight = Promise.resolve().then(() => lock ? lock(run) : run()).finally(() => {
      // Only the owning flight may clear the shared reference; a newer session's flight must
      // survive an older one finishing first.
      if (refreshFlight === flight) {
        refreshFlight = null;
        refreshFlightKey = null;
      }
    });
    refreshFlight = flight;
    return flight;
  }
  async function request(path, options = {}) {
    const started = session.getSnapshot();
    const current = epoch;
    const startedIdentity = identityEpoch;
    const startedCredentialGen = credentialGen;
    const startedScopeGen = scopeGen;
    const authenticated = options.authenticated !== false;
    const redirect = options.redirectOnSessionExpiry !== false;
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
        if (refreshEnabled && started.token && e.status === 401 && !path.startsWith("/auth/")) {
          let refreshed = null;
          // Another request may already have completed the refresh while this response was in
          // flight; in that case reuse it instead of rotating a second time.
          const latestSnapshot = session.getSnapshot();
          const alreadyRotated = credentialGen !== startedCredentialGen
            && latestSnapshot.token !== started.token
            && latestSnapshot.token === currentCredential
            && sameActor(started, latestSnapshot);
          try {
            if (!alreadyRotated) refreshed = await waitForRefresh(rotate(), options.signal);
          } catch (next) {
            if (next.code !== "REQUEST_ABORTED" && next.code !== "SESSION_CHANGED") {
              ensureCurrent(started);
              if (terminal(next)) expire(redirect);else unavailable(next);
            }
            throw next;
          }
          const retryScope = session.getSnapshot();
          ensureCurrent(retryScope);
          if (refreshed && retryScope.token !== refreshed.accessToken) throw sessionChanged();
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
            if (terminal(next)) expire(redirect);
            throw next;
          }
        }
        expire(redirect);
      }
      throw e;
    }
  }
  function initialize({
    force = false
  } = {}) {
    if (initialization) return initialization;
    if (initialized && !force) return Promise.resolve(session.getSnapshot().status);
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
    state("INITIALIZING");
    const initializationFlight = (async () => {
      try {
        if (session.getSnapshot().token) {
          try {
            const profile = await send("/users/me");
            if (stillCurrent()) {
              session.edit(draft => draft.user = profile);
              state("AUTHENTICATED");
            }
          } catch (e) {
            if (!terminal(e) || !refreshEnabled) throw e;
            if (!stillCurrent()) throw sessionChanged();
            // An existing access token means an existing session: the renewal must not adopt a
            // different account. Without a token this is cookie-based restoration.
            await rotate({ allowNewIdentity: !startedSnapshot.token });
          }
        } else if (refreshEnabled) await rotate({ allowNewIdentity: true });
        else if (current === epoch) state("UNAUTHENTICATED");
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
      if (initialization === initializationFlight) initialization = null;
    });
    initialization = initializationFlight;
    return initialization;
  }
  async function login(body) {
    invalidate();
    const current = epoch;
    return accept(await send("/auth/login", {
      method: "POST",
      authenticated: false,
      body,
      headers: refreshEnabled ? {
        "X-Refresh-Session": "true"
      } : {}
    }), current);
  }
  async function logout() {
    if (refreshEnabled) {
      const c = await csrf(),
        options = {
          method: "POST",
          headers: {
            [c.headerName]: c.token
          }
        };
      try {
        await send("/auth/logout", options);
      } catch (e) {
        if (e.status !== 401) throw e;
        await send("/auth/logout", {
          ...options,
          authenticated: false
        });
      }
    } else await send("/auth/logout", {
      method: "POST"
    });
    expire(false);
    initialized = true;
  }
  async function google() {
    invalidate();
    const current = epoch,
      c = await csrf();
    return accept(await send("/auth/oauth2/complete", {
      method: "POST",
      authenticated: false,
      headers: {
        [c.headerName]: c.token
      }
    }), current);
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
