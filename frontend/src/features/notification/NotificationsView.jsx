import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { api } from "../auth/api.js";
import { refreshUnread } from "./notifications.js";
import { useCollection } from "../../shared/hooks/useCollection.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import { date } from "../property/property.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function useNotificationsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const [unread] = useState(() => createStateStore(false)),
    state = useCollection("/users/me/notifications", null, () => ({
      unread: unread.getSnapshot()
    }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  useSyncExternalStore(unread.subscribe, unread.getSnapshot);
  async function mark(item) {
    await _stateLatest.current.run(async () => {
      await api("/users/me/notifications/" + item.id + "/read", {
        method: "PATCH"
      });
      await Promise.all([_stateLatest.current.load(_stateLatest.current.page), refreshUnread()]);
    });
  }
  async function all() {
    await _stateLatest.current.run(async () => {
      await api("/users/me/notifications/read-all", {
        method: "POST"
      });
      await Promise.all([_stateLatest.current.load(_stateLatest.current.page), refreshUnread()]);
    });
  }
  return {
    ...inputProps,
    date,
    unread: unread.getSnapshot(),
    state,
    mark,
    all,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateUnreadValue: unread.set
  };
}
export default React.forwardRef(function NotificationsView(props, ref) {
  const view = useNotificationsViewState(props, ref);
  return <><BusinessPage data-ui-view="NotificationsView" title="Trung tâm thông báo" {...view.rootAttributes}>
      <label>
        <input type="checkbox" checked={Array.isArray(view.unread) ? view.unread.includes("on") : !!view.unread} onChange={event => ($value => {
          view.updateUnreadValue($value);
        })(Array.isArray(view.unread) ? event.target.checked ? [...view.unread, "on"] : view.unread.filter(item => item !== "on") : event.target.checked)} />
        {" Chỉ chưa đọc"}
      </label>
      <button disabled={view.state.busy} onClick={$event => {
        return view.all?.($event);
      }}>
        {"Đánh dấu tất cả đã đọc"}
      </button>
      <ResourceState state={view.state} />
      <p>
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
        {" kết quả theo bộ lọc"}
      </p>
      {!view.state.busy && !view.state.items.length ? <p>{"Chưa có thông báo phù hợp."}</p> : null}
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.items, item => <section key={item.id}>
          <h2>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.title)}</h2>
          <p className="whitespace-pre-wrap">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.body)}
          </p>
          <p>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(item.createdAt))}
            {" · "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.readAt ? "Đã đọc" : "Chưa đọc")}
          </p>
          {!item.readAt ? <button disabled={view.state.busy} onClick={$event => {
          view.mark(item);
        }}>
              {"Đánh dấu đã đọc"}
            </button> : null}
          {item.propertyId ? <SiteLink to={"/listing/" + item.propertyId} className="underline">
              {"Xem tin"}
            </SiteLink> : null}
          {item.reportId ? <SiteLink to="/account/reports" className="ml-3 underline">
              {"Xem báo cáo của tôi"}
            </SiteLink> : null}
        </section>)}
      <Pagination state={view.state} />
    </BusinessPage></>;
});
