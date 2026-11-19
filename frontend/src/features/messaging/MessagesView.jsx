import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import { createThread } from "./thread.js";
import { useCollection } from "../../shared/hooks/useCollection.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import { date } from "../property/property.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function useMessagesViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState(),
    router = useAppNavigation(),
    conversations = useCollection("/users/me/conversations", null, () => ({})),
    [thread] = useState(() => createThread(api, undefined)),
    state = thread.getSnapshot().state,
    [text] = useState(() => createStateStore(""));
  const _conversationsLatest = useRef(conversations);
  _conversationsLatest.current = conversations;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  useSyncExternalStore(thread.subscribe, thread.getSnapshot);
  useSyncExternalStore(text.subscribe, text.getSnapshot);
  const _timerRef = useRef(undefined);
  async function select(id) {
    if (thread.getSnapshot().state.pending && !confirm("Tin nhắn chưa được xác nhận. Rời hội thoại này?")) return;
    await _routerLatest.current.replace({
      query: {
        conversation: id
      }
    });
  }
  async function poll() {
    if (document.hidden || !_routeLatest.current.query.conversation) return;
    await thread.getSnapshot().load();
    if (!thread.getSnapshot().state.error) try {
      await thread.getSnapshot().markRead();
    } catch {
      thread.getSnapshot().updateState(draftValue => draftValue.error = "Chưa cập nhật được trạng thái đã đọc.");
    }
  }
  const _watched = (() => _routeLatest.current.query.conversation)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (async id => {
      thread.getSnapshot().reset(typeof id === "string" ? id : null);
      text.set("");
      await poll();
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  async function send() {
    if (await thread.getSnapshot().send(text.getSnapshot())) {
      text.set("");
      await poll();
      await _conversationsLatest.current.load(_conversationsLatest.current.page);
    }
  }
  useEffect(() => {
    const result = (() => _timerRef.current = setInterval(poll, 5000))();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    clearInterval(_timerRef.current);
    thread.getSnapshot().dispose();
  })(), []);
  return {
    ...inputProps,
    session: session.getSnapshot(),
    date,
    route,
    conversations,
    state: thread.getSnapshot().state,
    text: text.getSnapshot(),
    select,
    poll,
    send,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateTextValue: text.set
  };
}
export default React.forwardRef(function MessagesView(props, ref) {
  const view = useMessagesViewState(props, ref);
  return <><BusinessPage data-ui-view="MessagesView" title="Tin nhắn" {...view.rootAttributes}>
      <p className="text-sm">
        {"Tin nhắn riêng giữa hai bên · cập nhật định kỳ bằng REST."}
      </p>
      <div className="grid gap-6 md:grid-cols-[280px_1fr]">
        <aside>
          <ResourceState state={view.conversations} />
          {!view.conversations.busy && !view.conversations.items.length ? <p>{"Chưa có hội thoại."}</p> : null}
          {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.conversations.items, c => <section key={c.id}>
              <button aria-current={view.route.query.conversation === c.id ? "page" : undefined} onClick={$event => {
              view.select(c.id);
            }}>
                {"Tin "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(c.propertyId.slice(0, 8))}
                {" · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(c.unreadCount)}
                {" chưa đọc"}
              </button>
              <p>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(c.updatedAt))}</p>
            </section>)}
          <Pagination state={view.conversations} />
        </aside>
        {view.route.query.conversation ? <section aria-label="Nội dung hội thoại">
            {view.state.error ? <p role="alert">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.error)}
              </p> : null}
            <button disabled={view.state.busy} onClick={$event => {
            return view.poll?.($event);
          }}>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.busy ? "Đang tải…" : "Tải tin tiếp / cập nhật")}
            </button>
            {!view.state.busy && !view.state.items.length ? <p>{"Chưa có tin nhắn."}</p> : null}
            <ol aria-live="polite">
              {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.items, m => <li key={m.id} className="my-3 rounded-xl bg-[var(--ui-surface)] p-3">
                  <strong>
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(m.senderId === view.session.user?.id ? "Bạn" : "Người tham gia")}
                  </strong>
                  <p className="whitespace-pre-wrap">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(m.body)}
                  </p>
                  <small>
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.date(m.createdAt))}
                  </small>
                </li>)}
            </ol>
            {view.state.hasMore ? <p>{"Còn tin tiếp theo; bấm tải để xem."}</p> : null}
            <form onSubmit={$event => {
            $event.preventDefault();
            return view.send?.($event);
          }}>
              <label>
                {"Nội dung "}
                <textarea maxLength="4000" required={true} readOnly={view.state.sendBusy} value={view.text ?? ""} onChange={event => ($value => {
                view.updateTextValue($value);
              })(event.target.value)} />
              </label>
              {view.state.pending ? <p>
                  {"Tin trước chưa được server xác nhận. Thử lại cùng nội dung sẽ dùng cùng mã tin."}
                </p> : null}
              <button disabled={view.state.sendBusy || !view.text.trim()}>
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.sendBusy ? "Đang gửi…" : view.state.pending ? "Thử gửi lại" : "Gửi tin nhắn")}
              </button>
            </form>
          </section> : <p>
            {"Chọn một hội thoại hoặc mở “Nhắn tin” từ tin bất động sản."}
          </p>}
      </div>
    </BusinessPage></>;
});
