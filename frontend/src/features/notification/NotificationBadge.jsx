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
import { watch, onMounted, onBeforeUnmount } from "../../shared/state/store.js";
import { session } from "../auth/api.js";
import { notifications, refreshUnread } from "./notifications.js";
function setup(__props) {
  let timer;
  const refresh = () => {
    if (session.token && !document.hidden) refreshUnread();
  };
  watch(() => session.user?.id, refresh);
  onMounted(() => {
    refresh();
    timer = setInterval(refresh, 30000);
  });
  onBeforeUnmount(() => clearInterval(timer));
  return {
    watch,
    onMounted,
    onBeforeUnmount,
    session,
    notifications,
    refreshUnread,
    timer,
    refresh,
  };
}
export default React.forwardRef(function NotificationBadge(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    ctx.session.token ? (
      <RouterLink
        {...mergeProps({
          to: "/account/notifications",
          "aria-label":
            "Thông báo: " +
            (ctx.notifications.count ?? "chưa tải") +
            " chưa đọc",
        })}
      >
        {"Thông báo"}
        {ctx.notifications.count !== null ? (
          <span {...mergeProps({})}>
            {" ("}
            {display(ctx.notifications.count)}
            {")"}
          </span>
        ) : null}
        {ctx.notifications.error ? (
          <span {...mergeProps({})}>{" · chưa tải"}</span>
        ) : null}
      </RouterLink>
    ) : null,
  ]);
});
