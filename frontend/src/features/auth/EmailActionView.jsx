import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useEffect, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { api, errorText, clearSession, session } from "./api.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function useEmailActionViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState(),
    router = useAppNavigation(),
    kind = route.path === "/reset-password" ? "reset" : route.path === "/verify-email" ? "verify" : "request";
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const [token] = useState(() => createStateStore(new URLSearchParams(_routeLatest.current.hash.slice(1)).get("token") || ""));
  useSyncExternalStore(token.subscribe, token.getSnapshot);
  useEffect(() => {
    if (route.hash) router.replace({
      path: route.path,
      query: route.query,
      hash: ""
    });
  }, [route.hash]);
  const [password] = useState(() => createStateStore("")),
    [confirmation] = useState(() => createStateStore("")),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [message] = useState(() => createStateStore("")),
    [done] = useState(() => createStateStore(false));
  useSyncExternalStore(done.subscribe, done.getSnapshot);
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(confirmation.subscribe, confirmation.getSnapshot);
  useSyncExternalStore(password.subscribe, password.getSnapshot);
  const getTitle = () => kind === "reset" ? "Đặt lại mật khẩu" : kind === "verify" ? "Xác nhận email" : "Xác minh email tài khoản";
  async function submit() {
    if (busy.getSnapshot() || done.getSnapshot()) return;
    error.set("");
    message.set("");
    if (kind === "reset" && (password.getSnapshot() !== confirmation.getSnapshot() || new TextEncoder().encode(password.getSnapshot()).length > 72)) {
      error.set("Mật khẩu xác nhận phải khớp, tối đa 72 byte UTF-8.");
      return;
    }
    busy.set(true);
    try {
      if (kind === "request") {
        await api("/auth/email-verification/request", {
          method: "POST"
        });
        message.set("Nếu tài khoản đủ điều kiện, yêu cầu đã được tiếp nhận. Vui lòng kiểm tra email.");
      } else {
        await api("/auth/" + (kind === "reset" ? "password/reset" : "email-verification/confirm"), {
          method: "POST",
          authenticated: false,
          body: kind === "reset" ? {
            token: token.getSnapshot(),
            newPassword: password.getSnapshot()
          } : {
            token: token.getSnapshot()
          }
        });
        if (kind === "reset") clearSession();
        done.set(true);
        token.set("");
        password.set(confirmation.set(""));
        message.set(kind === "reset" ? "Đã đặt lại mật khẩu. Hãy đăng nhập bằng mật khẩu mới." : "Email đã được xác nhận.");
      }
    } catch (e) {
      error.set(e.code === "INVALID_OR_EXPIRED_TOKEN" ? "Liên kết không hợp lệ, đã hết hạn hoặc đã được sử dụng. Vui lòng yêu cầu liên kết mới." : errorText(e));
    } finally {
      busy.set(false);
    }
  }
  useEffect(() => () => (() => {
    token.set("");
    password.set(confirmation.set(""));
  })(), []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    kind,
    token: token.getSnapshot(),
    password: password.getSnapshot(),
    confirmation: confirmation.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    message: message.getSnapshot(),
    done: done.getSnapshot(),
    title: getTitle(),
    submit,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updatePasswordValue: password.set,
    updateConfirmationValue: confirmation.set
  };
}
export default React.forwardRef(function EmailActionView(props, ref) {
  const view = useEmailActionViewState(props, ref);
  return <><BusinessPage data-ui-view="EmailActionView" title={view.title} {...view.rootAttributes}>
      {view.error ? <p role="alert">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      {view.message ? <p role="status">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}
        </p> : null}
      {!view.done ? <form onSubmit={$event => {
        $event.preventDefault();
        return view.submit?.($event);
      }}>
          {view.kind === "reset" ? <React.Fragment>
              <label>
                {"Mật khẩu mới "}
                <input type="password" autoComplete="new-password" minLength="8" required={true} value={view.password ?? ""} onChange={event => ($value => {
              view.updatePasswordValue($value);
            })(event.target.value)} />
              </label>
              <label>
                {"Nhập lại mật khẩu "}
                <input type="password" autoComplete="new-password" minLength="8" required={true} value={view.confirmation ?? ""} onChange={event => ($value => {
              view.updateConfirmationValue($value);
            })(event.target.value)} />
              </label>
            </React.Fragment> : null}
          {view.kind === "request" ? <p>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.user?.emailVerifiedAt ? "Email đã được xác minh." : "Gửi liên kết xác minh đến email tài khoản của bạn.")}
            </p> : null}
          {view.kind !== "request" && !view.token ? <p role="alert">
              {"Thiếu token trong liên kết. Hãy yêu cầu email mới."}
            </p> : null}
          <button disabled={view.busy || view.kind !== "request" && !view.token}>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang xử lý…" : view.kind === "request" ? "Gửi email xác minh" : "Xác nhận")}
          </button>
        </form> : null}
      <SiteLink to="/login" className="underline">
        {"Về đăng nhập / yêu cầu khôi phục"}
      </SiteLink>
    </BusinessPage></>;
});
