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
    epoch = 0;
  const state = (status, error = null) => {
    session.edit(draft => draft.status = status);
    session.edit(draft => draft.error = error);
    onState(status, error);
  };
  const terminal = e => e?.status === 401 && e?.code !== "AUTH_RETRY_REQUIRED" || e?.status === 403 && e?.code === "ACCOUNT_LOCKED";
  function invalidate() {
    epoch++;
  }
  function expire(redirect = true) {
    invalidate();
    clear();
    session.edit(draft => draft.token = null);
    session.edit(draft => draft.user = null);
    initialized = true;
    state("UNAUTHENTICATED");
    if (redirect) expired();
  }
  function unavailable(e) {
    state("UNAVAILABLE", e?.message || "Không thể kiểm tra phiên. Vui lòng thử lại.");
  }
  function accept(result, current) {
    if (current !== epoch) throw Object.assign(Error("Phiên đã thay đổi."), {
      code: "SESSION_CHANGED"
    });
    session.edit(draft => draft.token = result.accessToken);
    session.edit(draft => draft.user = result.user);
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
    if (externalSignal) {
      if (externalSignal.aborted) controller.abort();
      else externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
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
      const data = response.status === 204 ? null : response.ok && responseType === "blob" ? await response.blob() : await response.json().catch(() => null);
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
      if (e.status) throw e;
      if (externalSignal?.aborted) {
        throw Object.assign(Error("Yêu cầu đã bị hủy."), {
          name: "AbortError",
          code: "REQUEST_ABORTED"
        });
      }
      throw Object.assign(Error(e.name === "AbortError" ? "Yêu cầu quá thời gian. Vui lòng thử lại." : "Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối."), {
        code: e.name === "AbortError" ? "REQUEST_TIMEOUT" : "NETWORK_ERROR"
      });
    } finally {
      clearTimeout(timeout);
      if (externalSignal) externalSignal.removeEventListener("abort", onExternalAbort);
    }
  }
  const csrf = () => send("/auth/csrf", {
    authenticated: false
  });
  function rotate() {
    if (refreshFlight) return refreshFlight;
    const current = epoch,
      run = async () => {
        const c = await csrf();
        return accept(await send("/auth/refresh", {
          method: "POST",
          authenticated: false,
          headers: {
            [c.headerName]: c.token
          }
        }), current);
      };
    refreshFlight = Promise.resolve().then(() => lock ? lock(run) : run()).finally(() => {
      refreshFlight = null;
    });
    return refreshFlight;
  }
  async function request(path, options = {}) {
    const sentToken = session.getSnapshot().token,
      current = epoch;
    try {
      const result = await send(path, options);
      if (options.authenticated !== false && sentToken && current !== epoch) throw Object.assign(Error("Phiên đã thay đổi."), {
        code: "SESSION_CHANGED"
      });
      return result;
    } catch (e) {
      if (options.authenticated !== false && terminal(e)) {
        if (refreshEnabled && sentToken && current === epoch && !path.startsWith("/auth/")) {
          try {
            if (session.getSnapshot().token === sentToken) await rotate();
            if (current !== epoch) throw Object.assign(Error("Phiên đã thay đổi."), {
              code: "SESSION_CHANGED"
            });
          } catch (next) {
            if (current === epoch) {
              if (terminal(next)) expire();else if (next.code !== "SESSION_CHANGED") unavailable(next);
            }
            throw next;
          }
          // Renew credentials but require explicit resubmission for writes; never duplicate an uncertain mutation.
          if (!["GET", "HEAD", "OPTIONS"].includes((options.method || "GET").toUpperCase())) throw Object.assign(Error("Phiên đã được gia hạn. Vui lòng thực hiện lại thao tác vừa gửi."), {
            status: 401,
            code: "AUTH_RETRY_REQUIRED",
            sessionRecovered: true
          });
          try {
            return await send(path, options);
          } catch (next) {
            if (current === epoch && terminal(next)) expire();
            throw next;
          }
        }
        if (current === epoch) expire();
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
    state("INITIALIZING");
    initialization = (async () => {
      try {
        if (session.getSnapshot().token) {
          try {
            const profile = await send("/users/me");
            if (current === epoch) {
              session.edit(draft => draft.user = profile);
              state("AUTHENTICATED");
            }
          } catch (e) {
            if (!terminal(e) || !refreshEnabled) throw e;
            await rotate();
          }
        } else if (refreshEnabled) await rotate();else if (current === epoch) state("UNAUTHENTICATED");
      } catch (e) {
        if (current === epoch) {
          if (terminal(e)) expire(false);else if (e.code !== "SESSION_CHANGED") unavailable(e);
        }
      } finally {
        if (current === epoch) initialized = true;
      }
      return session.getSnapshot().status;
    })().finally(() => {
      initialization = null;
    });
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
  return {
    request,
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
