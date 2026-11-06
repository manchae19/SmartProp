import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import { ref } from "../../shared/state/store.js";
import { api, errorText } from "../auth/api.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    id: {
      type: String,
      required: true,
    },
  });
  const items = ref(null),
    error = ref(""),
    busy = ref(false),
    open = ref(false);
  async function toggle() {
    open.value = !open.value;
    if (!open.value || busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      items.value = await api(
        "/users/me/properties/" + encodeURIComponent(props.id) + "/moderation",
      );
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  return {
    ref,
    api,
    errorText,
    props,
    items,
    error,
    busy,
    open,
    toggle,
  };
}
export default React.forwardRef(
  function PropertyModerationFeedback(props, ref) {
    const ctx = useSetup(setup, props, ref);
    return rootProps(ctx, [
      <div
        {...mergeProps({
          className: "mt-4 border-t border-brand-line pt-3 text-sm",
        })}
      >
        <button
          {...mergeProps({
            type: "button",
            className: "font-semibold underline",
            "aria-expanded": ctx.open,
            disabled: ctx.busy,
            onClick: ($event) => {
              return ctx.toggle?.($event);
            },
          })}
        >
          {display(ctx.open ? "Thu gọn phản hồi" : "Xem phản hồi kiểm duyệt")}
        </button>
        {ctx.open ? (
          <div
            {...mergeProps({
              className: "mt-3 grid gap-3",
            })}
          >
            {ctx.busy ? (
              <p
                {...mergeProps({
                  role: "status",
                })}
              >
                {"Đang tải…"}
              </p>
            ) : null}
            {ctx.error ? (
              <p
                {...mergeProps({
                  role: "alert",
                  className: "text-[var(--ui-error-text)]",
                })}
              >
                {display(ctx.error)}
              </p>
            ) : null}
            {ctx.items && !ctx.items.length ? (
              <p {...mergeProps({})}>{"Chưa có phản hồi kiểm duyệt."}</p>
            ) : null}
            {renderList(ctx.items, (item, index) => (
              <article
                key={index}
                {...mergeProps({
                  className: "rounded-control bg-brand-surface p-3",
                })}
              >
                <p
                  {...mergeProps({
                    className: "text-xs text-brand-muted",
                  })}
                >
                  {display(item.newStatus)}
                  {" · "}
                  {display(new Date(item.createdAt).toLocaleString("vi-VN"))}
                </p>
                <p
                  {...mergeProps({
                    className: "mt-1 whitespace-pre-wrap leading-6",
                  })}
                >
                  {display(item.reason)}
                </p>
              </article>
            ))}
          </div>
        ) : null}
      </div>,
    ]);
  },
);
