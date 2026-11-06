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
import { computed } from "../state/store.js";
import { avatar } from "../../features/account/avatar.js";
import { session } from "../../features/auth/api.js";
import PrivateImage from "./PrivateImage.jsx";
import "./UserAvatar.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    name: String,
    size: {
      type: Number,
      default: 44,
    },
  });
  const initials = computed(
    () =>
      String(props.name || "")
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(-2)
        .map((word) => word[0])
        .join("")
        .toUpperCase() || "S",
  );
  const image = computed(() =>
    avatar.available && avatar.owner === session.user?.id ? avatar.url : null,
  );
  return {
    computed,
    avatar,
    session,
    PrivateImage,
    props,
    initials,
    image,
  };
}
export default React.forwardRef(function UserAvatar(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <span
      {...mergeProps({
        className: "user-avatar",
        style: {
          width: ctx.size + "px",
          height: ctx.size + "px",
          fontSize: Math.max(14, Math.round(ctx.size * 0.3)) + "px",
        },
        role: "img",
        "aria-label": ctx.name ? "Ảnh đại diện của " + ctx.name : "SmartProp",
        "data-sp-d9f157e1": "",
      })}
    >
      {ctx.image ? (
        <PrivateImage
          {...mergeProps({
            src: ctx.image,
            alt: "Ảnh đại diện của " + ctx.name,
            "data-sp-d9f157e1": "",
          })}
        />
      ) : (
        <span
          {...mergeProps({
            "data-sp-d9f157e1": "",
          })}
        >
          {display(ctx.initials)}
        </span>
      )}
    </span>,
  ]);
});
