import { classNames } from "../../shared/lib/ui.js";
import React, { useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState } from "../../app/navigation.jsx";
import { postSteps } from "./postForm.js";
function usePostStepNavState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  return {
    ...inputProps,
    postSteps,
    route,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["current", "busy", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function PostStepNav(props, ref) {
  const view = usePostStepNavState(props, ref);
  return <><nav aria-label="Các bước đăng tin" {...view.rootAttributes} className={classNames(["grid grid-cols-3 gap-3 py-6", view.rootAttributes.className])}>
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.postSteps, item => <SiteLink key={item.step} to={{
        path: item.path,
        query: view.route.query
      }} aria-current={view.current === item.step ? "step" : undefined} aria-disabled={view.busy || undefined} onClick={$event => {
        view.busy && $event.preventDefault();
      }} className={classNames(["post-step", view.busy ? "pointer-events-none opacity-60" : ""])}>
          <span className="post-step-number" aria-hidden="true">{String(item.step).padStart(2, "0")}</span>
          <span className="post-step-label"><span className="sr-only">Bước {item.step} · </span>{item.label}</span>
        </SiteLink>)}
    </nav></>;
});
