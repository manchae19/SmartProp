import { classNames } from "../lib/ui.js";
import React, { useSyncExternalStore, useRef } from "react";
import { avatar } from "../../features/account/avatar.js";
import { session } from "../../features/auth/api.js";
import PrivateImage from "./PrivateImage.jsx";
import "./UserAvatar.css";
function useUserAvatarState(inputProps, forwardedRef) {
  inputProps = {
    size: 44,
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(avatar.subscribe, avatar.getSnapshot);
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const props = {
    size: 44,
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const getInitials = () => String(_props.current.name || "").trim().split(/\s+/).filter(Boolean).slice(-2).map(word => word[0]).join("").toUpperCase() || "S";
  const getImage = () => avatar.getSnapshot().available && avatar.getSnapshot().owner === session.getSnapshot().user?.id ? avatar.getSnapshot().url : null;
  return {
    ...inputProps,
    initials: getInitials(),
    image: getImage(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["name", "size", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function UserAvatar(props, ref) {
  const view = useUserAvatarState(props, ref);
  return <><span style={{
      width: view.size + "px",
      height: view.size + "px",
      fontSize: Math.max(14, Math.round(view.size * 0.3)) + "px"
    }} role="img" aria-label={view.name ? "Ảnh đại diện của " + view.name : "SmartProp"} data-sp-d9f157e1="" {...view.rootAttributes} className={classNames(["user-avatar", view.rootAttributes.className])}>
      {view.image ? <PrivateImage src={view.image} alt={"Ảnh đại diện của " + view.name} data-sp-d9f157e1="" /> : <span data-sp-d9f157e1="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.initials)}
        </span>}
    </span></>;
});
