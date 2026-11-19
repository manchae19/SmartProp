import { classNames } from "../lib/ui.js";
import React, { useRef } from "react";
import "./BusinessPage.css";
function useBusinessPageState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  return {
    ...inputProps,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["title", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function BusinessPage(props, ref) {
  const view = useBusinessPageState(props, ref);
  return <><section data-ui-view="BusinessPage" {...view.rootAttributes} className={classNames(["completion-page", view.rootAttributes.className])}>
      <h1>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.title)}</h1>
      {view.children ?? null}
    </section></>;
});
