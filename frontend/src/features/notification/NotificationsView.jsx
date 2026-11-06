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
import { api } from "../auth/api.js";
import { refreshUnread } from "./notifications.js";
import { useCollection } from "../home/useCollection.js";
import { LegacyState, LegacyPager, date } from "../../shared/lib/legacy.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function setup(__props) {
  const unread = ref(false),
    state = useCollection("/users/me/notifications", null, () => ({
      unread: unread.value,
    }));
  async function mark(item) {
    await state.run(async () => {
      await api("/users/me/notifications/" + item.id + "/read", {
        method: "PATCH",
      });
      await Promise.all([state.load(state.page), refreshUnread()]);
    });
  }
  async function all() {
    await state.run(async () => {
      await api("/users/me/notifications/read-all", {
        method: "POST",
      });
      await Promise.all([state.load(state.page), refreshUnread()]);
    });
  }
  return {
    ref,
    api,
    refreshUnread,
    useCollection,
    LegacyState,
    LegacyPager,
    date,
    BusinessPage,
    unread,
    state,
    mark,
    all,
  };
}
export default React.forwardRef(function NotificationsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <BusinessPage data-ui-view="NotificationsView"
      {...mergeProps({
        title: "Trung tâm thông báo",
      })}
    >
      <label {...mergeProps({})}>
        <input
          {...mergeProps(
            {
              type: "checkbox",
            },
            modelProps(
              ctx.unread,
              ($value) => {
                ctx.unread = $value;
              },
              {
                kind: "checkbox",
                value: "on",
                number: false,
                multiple: false,
              },
            ),
          )}
        />
        {" Chỉ chưa đọc"}
      </label>
      <button
        {...mergeProps({
          disabled: ctx.state.busy,
          onClick: ($event) => {
            return ctx.all?.($event);
          },
        })}
      >
        {"Đánh dấu tất cả đã đọc"}
      </button>
      <LegacyState
        {...mergeProps({
          state: ctx.state,
        })}
      />
      <p {...mergeProps({})}>
        {display(ctx.state.totalElements)}
        {" kết quả theo bộ lọc"}
      </p>
      {!ctx.state.busy && !ctx.state.items.length ? (
        <p {...mergeProps({})}>{"Chưa có thông báo phù hợp."}</p>
      ) : null}
      {renderList(ctx.state.items, (item) => (
        <section key={item.id} {...mergeProps({})}>
          <h2 {...mergeProps({})}>{display(item.title)}</h2>
          <p
            {...mergeProps({
              className: "whitespace-pre-wrap",
            })}
          >
            {display(item.body)}
          </p>
          <p {...mergeProps({})}>
            {display(ctx.date(item.createdAt))}
            {" · "}
            {display(item.readAt ? "Đã đọc" : "Chưa đọc")}
          </p>
          {!item.readAt ? (
            <button
              {...mergeProps({
                disabled: ctx.state.busy,
                onClick: ($event) => {
                  ctx.mark(item);
                },
              })}
            >
              {"Đánh dấu đã đọc"}
            </button>
          ) : null}
          {item.propertyId ? (
            <RouterLink
              {...mergeProps({
                to: "/listing/" + item.propertyId,
                className: "underline",
              })}
            >
              {"Xem tin"}
            </RouterLink>
          ) : null}
          {item.reportId ? (
            <RouterLink
              {...mergeProps({
                to: "/account/reports",
                className: "ml-3 underline",
              })}
            >
              {"Xem báo cáo của tôi"}
            </RouterLink>
          ) : null}
        </section>
      ))}
      <LegacyPager
        {...mergeProps({
          state: ctx.state,
        })}
      />
    </BusinessPage>,
  ]);
});
