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
import {
  nextTick,
  onBeforeUnmount,
  ref,
  useId,
  watch,
} from "../../state/store.js";
import "./MobileDrawer.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    open: Boolean,
    title: {
      type: String,
      default: "Khám phá SmartProp",
    },
  });
  const emit = emitForProps(__props, ["update:open", "closed"]);
  const panel = ref(null),
    closeButton = ref(null),
    titleId = useId();
  let previousOverflow,
    locked = false,
    pendingCloses = 0;
  function unlock() {
    if (locked) {
      document.body.style.overflow = previousOverflow;
      locked = false;
    }
  }
  function close() {
    emit("update:open", false);
  }
  function closePanel() {
    if (panel.value?.open) {
      pendingCloses++;
      panel.value.close();
    }
    unlock();
  }
  function closed() {
    if (pendingCloses) {
      pendingCloses--;
      if (!props.open && !panel.value?.open) emit("closed");
      return;
    }
    if (panel.value?.open) return;
    unlock();
    emit("update:open", false);
    emit("closed");
  }
  function backdrop(event) {
    if (event.target !== panel.value) return;
    const box = panel.value.getBoundingClientRect();
    if (
      event.clientX < box.left ||
      event.clientX > box.right ||
      event.clientY < box.top ||
      event.clientY > box.bottom
    )
      close();
  }
  function trapTab(event) {
    if (event.key !== "Tab" || !panel.value?.open) return;
    const items = [
      ...panel.value.querySelectorAll(
        'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])',
      ),
    ].filter(
      (element) =>
        element.getClientRects().length && !element.closest("[inert]"),
    );
    const first = items[0],
      last = items.at(-1);
    if (!first) {
      event.preventDefault();
      panel.value.focus();
      return;
    }
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  watch(
    () => props.open,
    async (value) => {
      await nextTick();
      if (!panel.value || props.open !== value) return;
      if (value) {
        if (!panel.value.open) panel.value.showModal();
        if (!locked) {
          previousOverflow = document.body.style.overflow;
          locked = true;
          document.body.style.overflow = "hidden";
        }
        closeButton.value?.focus();
      } else closePanel();
    },
  );
  onBeforeUnmount(closePanel);
  exposeForSetup({
    id: titleId,
  });
  return {
    nextTick,
    onBeforeUnmount,
    ref,
    useId,
    watch,
    props,
    emit,
    panel,
    closeButton,
    titleId,
    previousOverflow,
    locked,
    pendingCloses,
    unlock,
    close,
    closePanel,
    closed,
    backdrop,
    trapTab,
  };
}
export default React.forwardRef(function MobileDrawer(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <dialog
      {...mergeProps({
        ref: bindRef(ctx, "panel"),
        "aria-labelledby": ctx.titleId,
        className:
          "mobile-drawer fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-[min(25rem,calc(100vw-1.25rem))] max-w-none border-0 bg-brand-card p-0 text-brand-navy shadow-2xl",
        onCancel: ($event) => {
          $event.preventDefault();
          return ctx.close?.($event);
        },
        onClose: ($event) => {
          return ctx.closed?.($event);
        },
        onClick: ($event) => {
          return ctx.backdrop?.($event);
        },
        onKeyDown: ($event) => {
          return ctx.trapTab?.($event);
        },
        "data-sp-16c95175": "",
      })}
    >
      <div
        {...mergeProps({
          className: "flex h-full flex-col",
          "data-sp-16c95175": "",
        })}
      >
        <div
          {...mergeProps({
            className:
              "drawer-heading flex shrink-0 items-center justify-between gap-4 px-5 py-5",
            "data-sp-16c95175": "",
          })}
        >
          <div>
            <p className="drawer-eyebrow">SMARTPROP · ĐÀ NẴNG</p>
          <h2
            {...mergeProps({
              id: ctx.titleId,
              className: "text-lg font-semibold",
              "data-sp-16c95175": "",
            })}
          >
            {display(ctx.title)}
          </h2>
          </div>
          <button
            {...mergeProps({
              ref: bindRef(ctx, "closeButton"),
              type: "button",
              className: "sp-icon-button",
              "aria-label": "Đóng menu",
              onClick: ($event) => {
                return ctx.close?.($event);
              },
              "data-sp-16c95175": "",
            })}
          >
            <svg
              {...mergeProps({
                className: "size-5",
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                strokeWidth: "1.7",
                "aria-hidden": "true",
                "data-sp-16c95175": "",
              })}
            >
              <path
                {...mergeProps({
                  d: "m6 6 12 12M6 18 18 6",
                  "data-sp-16c95175": "",
                })}
              />
            </svg>
          </button>
        </div>
        {ctx.open ? (
          <div
            {...mergeProps({
              className:
                "drawer-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain p-5",
              "data-sp-16c95175": "",
            })}
          >
            {ctx.$children ?? null}
          </div>
        ) : null}
      </div>
    </dialog>,
  ]);
});
