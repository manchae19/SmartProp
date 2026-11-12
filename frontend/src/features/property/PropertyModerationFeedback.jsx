import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { api, errorText } from "../auth/api.js";
function usePropertyModerationFeedbackState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [items] = useState(() => createStateStore(null)),
    [error] = useState(() => createStateStore("")),
    [busy] = useState(() => createStateStore(false)),
    [open] = useState(() => createStateStore(false));
  useSyncExternalStore(open.subscribe, open.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(items.subscribe, items.getSnapshot);
  async function toggle() {
    open.set(!open.getSnapshot());
    if (!open.getSnapshot() || busy.getSnapshot()) return;
    busy.set(true);
    error.set("");
    try {
      items.set(await api("/users/me/properties/" + encodeURIComponent(_props.current.id) + "/moderation"));
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  return {
    ...inputProps,
    items: items.getSnapshot(),
    error: error.getSnapshot(),
    busy: busy.getSnapshot(),
    open: open.getSnapshot(),
    toggle,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["id", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function PropertyModerationFeedback(props, ref) {
  const view = usePropertyModerationFeedbackState(props, ref);
  return <><div {...view.rootAttributes} className={classNames(["mt-4 border-t border-brand-line pt-3 text-sm", view.rootAttributes.className])}>
        <button type="button" className="font-semibold underline" aria-expanded={view.open} disabled={view.busy} onClick={$event => {
        return view.toggle?.($event);
      }}>
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.open ? "Thu gọn phản hồi" : "Xem phản hồi kiểm duyệt")}
        </button>
        {view.open ? <div className="mt-3 grid gap-3">
            {view.busy ? <p role="status">
                {"Đang tải…"}
              </p> : null}
            {view.error ? <p role="alert" className="text-[var(--ui-error-text)]">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
              </p> : null}
            {view.items && !view.items.length ? <p>{"Chưa có phản hồi kiểm duyệt."}</p> : null}
            {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.items, (item, index) => <article key={index} className="rounded-control bg-brand-surface p-3">
                <p className="text-xs text-brand-muted">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.newStatus)}
                  {" · "}
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(new Date(item.createdAt).toLocaleString("vi-VN"))}
                </p>
                <p className="mt-1 whitespace-pre-wrap leading-6">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.reason)}
                </p>
              </article>)}
          </div> : null}
      </div></>;
});
