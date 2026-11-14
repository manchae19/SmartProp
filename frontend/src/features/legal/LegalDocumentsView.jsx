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
import { ref, watch, onBeforeUnmount } from "../../shared/state/store.js";
import { useRoute } from "../../shared/routing/router.jsx";
import { api, session, errorText } from "../auth/api.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
import LegalDocuments from "./LegalDocuments.jsx";
function setup(__props) {
  const route = useRoute(),
    managed = ref(null),
    error = ref(""),
    busy = ref(false);
  let sequence = 0;
  async function load() {
    const run = ++sequence;
    managed.value = null;
    error.value = "";
    busy.value = true;
    try {
      const result = await api(
        (session.user?.role === "ADMIN"
          ? "/admin/properties/"
          : "/users/me/properties/") + route.params.id,
      );
      if (run === sequence) managed.value = result;
    } catch (e) {
      if (run === sequence) error.value = errorText(e);
    } finally {
      if (run === sequence) busy.value = false;
    }
  }
  watch(() => [route.params.id, session.user?.id], load, {
    immediate: true,
  });
  onBeforeUnmount(() => sequence++);
  return {
    ref,
    watch,
    onBeforeUnmount,
    useRoute,
    api,
    session,
    errorText,
    BusinessPage,
    LegalDocuments,
    route,
    managed,
    error,
    busy,
    sequence,
    load,
  };
}
export default React.forwardRef(function LegalDocumentsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <BusinessPage data-ui-view="LegalDocumentsView"
      {...mergeProps({
        title: "Quản lý hồ sơ pháp lý",
      })}
    >
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
          })}
        >
          {"Đang tải quyền quản lý tin…"}
        </p>
      ) : null}
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
          })}
        >
          {display(ctx.error)}{" "}
          <button
            {...mergeProps({
              onClick: ($event) => {
                return ctx.load?.($event);
              },
            })}
          >
            {"Thử lại"}
          </button>
        </p>
      ) : null}
      {ctx.managed ? (
        <React.Fragment {...mergeProps({})}>
          <h2 {...mergeProps({})}>{display(ctx.managed.property.title)}</h2>
          <LegalDocuments
            key={ctx.managed.property.id}
            {...mergeProps({
              propertyId: ctx.managed.property.id,
              ownerId: ctx.managed.ownerId,
            })}
          />
        </React.Fragment>
      ) : null}
    </BusinessPage>,
  ]);
});
