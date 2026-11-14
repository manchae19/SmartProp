import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "./rendering.js";
import { RouterLink, RouterView } from "../routing/router.jsx";
import { ref, watch, onBeforeUnmount } from "../state/store.js";
import { api, session } from "../../features/auth/api.js";
import "./PrivateImage.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    src: String,
    alt: {
      type: String,
      default: "",
    },
  });
  const url = ref(""),
    failed = ref(false);
  let serial = 0;
  function release() {
    if (url.value) URL.revokeObjectURL(url.value);
    url.value = "";
  }
  watch(
    () => [props.src, session.token],
    async () => {
      const run = ++serial;
      release();
      failed.value = false;
      if (!props.src) return;
      try {
        const blob = await api(props.src.replace(/^\/api\/v1/, ""), {
          responseType: "blob",
          authenticated: !!session.token,
        });
        if (run === serial) url.value = URL.createObjectURL(blob);
      } catch {
        if (run === serial) failed.value = true;
      }
    },
    {
      immediate: true,
    },
  );
  onBeforeUnmount(() => {
    serial++;
    release();
  });
  return {
    ref,
    watch,
    onBeforeUnmount,
    api,
    session,
    props,
    url,
    failed,
    serial,
    release,
  };
}
export default React.forwardRef(function PrivateImage(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    ctx.url ? (
      <img
        {...mergeProps({
          src: ctx.url,
          alt: ctx.alt,
          loading: "lazy",
          onError: ($event) => {
            ctx.release();
            ctx.failed = true;
          },
          "data-sp-55ccf5d3": "",
        })}
      />
    ) : (
      <div
        {...mergeProps({
          className: "sp-placeholder",
          role: "img",
          "aria-label": ctx.alt,
          "data-sp-55ccf5d3": "",
        })}
      >
        {display(
          ctx.failed
            ? "Không tải được ảnh"
            : ctx.src
              ? "Đang tải ảnh…"
              : "Chưa có ảnh",
        )}
      </div>
    ),
  ]);
});
