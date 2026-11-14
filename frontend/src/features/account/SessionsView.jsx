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
import { useRouter } from "../../shared/routing/router.jsx";
import { api, clearSession } from "../auth/api.js";
import { useCollection } from "../home/useCollection.js";
import { LegacyState, LegacyPager, date } from "../../shared/lib/legacy.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function setup(__props) {
  const router = useRouter(),
    state = useCollection("/users/me/sessions", null, () => ({}));
  async function revoke(item) {
    await state.run(async () => {
      await api("/users/me/sessions/" + item.id, {
        method: "DELETE",
      });
      if (item.current) {
        clearSession();
        await router.replace("/login");
      } else await state.load(state.page);
    });
  }
  async function all() {
    await state.run(async () => {
      await api("/users/me/sessions", {
        method: "DELETE",
      });
      clearSession();
      await router.replace("/login");
    });
  }
  return {
    useRouter,
    api,
    clearSession,
    useCollection,
    LegacyState,
    LegacyPager,
    date,
    BusinessPage,
    router,
    state,
    revoke,
    all,
  };
}
export default React.forwardRef(function SessionsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <BusinessPage data-ui-view="SessionsView"
      {...mergeProps({
        title: "Phiên đăng nhập",
      })}
    >
      <LegacyState
        {...mergeProps({
          state: ctx.state,
        })}
      />
      <button
        {...mergeProps({
          disabled: ctx.state.busy,
          onClick: ($event) => {
            return ctx.all?.($event);
          },
        })}
      >
        {"Thu hồi mọi phiên và đăng xuất"}
      </button>
      {!ctx.state.busy && !ctx.state.items.length ? (
        <p {...mergeProps({})}>{"Không có phiên để hiển thị."}</p>
      ) : null}
      {renderList(ctx.state.items, (item) => (
        <section key={item.id} {...mergeProps({})}>
          <h2 {...mergeProps({})}>
            {display(item.current ? "Phiên hiện tại" : "Phiên khác")}
          </h2>
          <p {...mergeProps({})}>
            {display(item.userAgent || "Thiết bị không xác định")}
          </p>
          <p {...mergeProps({})}>
            {"Tạo: "}
            {display(ctx.date(item.createdAt))}
            {" · Hết hạn: "}
            {display(ctx.date(item.expiresAt))}
            {" · "}
            {display(item.revoked ? "Đã thu hồi" : "Đang hoạt động")}
          </p>
          {!item.revoked ? (
            <button
              {...mergeProps({
                disabled: ctx.state.busy,
                onClick: ($event) => {
                  ctx.revoke(item);
                },
              })}
            >
              {"Thu hồi phiên"}
            </button>
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
