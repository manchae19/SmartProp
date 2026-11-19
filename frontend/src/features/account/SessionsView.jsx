import React, { useRef } from "react";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api, clearSession } from "../auth/api.js";
import { useCollection } from "../../shared/hooks/useCollection.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import { date } from "../property/property.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function useSessionsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const router = useAppNavigation(),
    state = useCollection("/users/me/sessions", null, () => ({}));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  async function revoke(item) {
    await _stateLatest.current.run(async () => {
      await api("/users/me/sessions/" + item.id, {
        method: "DELETE"
      });
      if (item.current) {
        clearSession();
        await _routerLatest.current.replace("/login");
      } else await _stateLatest.current.load(_stateLatest.current.page);
    });
  }
  async function all() {
    await _stateLatest.current.run(async () => {
      await api("/users/me/sessions", {
        method: "DELETE"
      });
      clearSession();
      await _routerLatest.current.replace("/login");
    });
  }
  return {
    ...inputProps,
    date,
    state,
    revoke,
    all,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function SessionsView(props, ref) {
  const view = useSessionsViewState(props, ref);
  return <><BusinessPage data-ui-view="SessionsView" title="Phiên đăng nhập" {...view.rootAttributes}>
      <ResourceState state={view.state} />
      <button disabled={view.state.busy} onClick={$event => {
        return view.all?.($event);
      }}>
        {"Thu hồi mọi phiên và đăng xuất"}
      </button>
      {!view.state.busy && !view.state.items.length ? <p>{"Không có phiên để hiển thị."}</p> : null}
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.items, item => <section key={item.id}>
          <h2>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.current ? "Phiên hiện tại" : "Phiên khác")}
          </h2>
          <p>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.userAgent || "Thiết bị không xác định")}
          </p>
          <p>
            {"Tạo: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(item.createdAt))}
            {" · Hết hạn: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(item.expiresAt))}
            {" · "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.revoked ? "Đã thu hồi" : "Đang hoạt động")}
          </p>
          {!item.revoked ? <button disabled={view.state.busy} onClick={$event => {
          view.revoke(item);
        }}>
              {"Thu hồi phiên"}
            </button> : null}
        </section>)}
      <Pagination state={view.state} />
    </BusinessPage></>;
});
