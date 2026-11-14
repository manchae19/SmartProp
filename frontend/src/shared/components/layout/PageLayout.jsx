import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../rendering.js";
import { RouterLink, RouterView } from "../../routing/router.jsx";
import { computed, nextTick, watch } from "../../state/store.js";
import { useRoute } from "../../routing/router.jsx";
import AppHeader from "./AppHeader.jsx";
import AppFooter from "./AppFooter.jsx";
import "./PageLayout.css";
function setup(__props) {
  const route = useRoute();
  const messengerPage = computed(() => route.path === "/advisor/chat");
  watch(
    () => route.path,
    async () => {
      await nextTick();
      document.getElementById("page-content")?.focus({
        preventScroll: true,
      });
    },
  );
  return {
    computed,
    nextTick,
    watch,
    useRoute,
    AppHeader,
    AppFooter,
    route,
    messengerPage,
  };
}
export default React.forwardRef(function PageLayout(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: ["page-layout flex min-h-dvh flex-col bg-brand-cream text-brand-navy", {
          "messenger-layout": ctx.messengerPage,
        }],
        
        "data-sp-292ae0bf": "",
      })}
    >
      <a
        {...mergeProps({
          href: "#page-content",
          className:
            "fixed -top-20 left-4 z-[100] rounded-control bg-brand-card px-5 py-3 text-sm font-semibold shadow-lg focus:top-3",
          "data-sp-292ae0bf": "",
        })}
      >
        {"Đến nội dung chính"}
      </a>
      <AppHeader
        {...mergeProps({
          "data-sp-292ae0bf": "",
        })}
      />
      <main
        {...mergeProps({
          id: "page-content",
          tabIndex: "-1",
          className: ["min-w-0 flex-1 outline-none", {
            "messenger-main": ctx.messengerPage,
          }],
          
          "data-sp-292ae0bf": "",
        })}
      >
        {ctx.$children ?? null}
      </main>
      {!ctx.messengerPage ? (
        <AppFooter
          {...mergeProps({
            "data-sp-292ae0bf": "",
          })}
        />
      ) : null}
    </div>,
  ]);
});
