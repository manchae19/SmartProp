import { classNames } from "../../lib/ui.js";
import React, { useRef } from "react";
import { SiteLink } from "../../../app/navigation.jsx";
import { useRouteState } from "../../../app/navigation.jsx";
import { normalizeFilters } from "../../../features/property/listingFilters.js";
import { activeNavigation, siteNavigation, scrollHomeSection } from "../../lib/siteNavigation.js";
import AppIcon from "../AppIcon.jsx";
function useAppNavigationState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const getItems = () => siteNavigation(normalizeFilters(_routeLatest.current.query));
  function navigate(item) {
    if (item.key === "home" && _routeLatest.current.path === "/home") scrollHomeSection("home");
    _propsLatest.current.onNavigate?.();
  }
  return {
    ...inputProps,
    activeNavigation,
    route,
    items: getItems(),
    navigate,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["vertical", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AppNavigation(props, ref) {
  const view = useAppNavigationState(props, ref);
  return <><nav aria-label={view.vertical ? "Điều hướng website trong menu" : "Điều hướng website"} {...view.rootAttributes} className={classNames([classNames(view.vertical ? "grid gap-1.5" : "flex items-center gap-1"), view.rootAttributes.className])}>
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.items, item => <SiteLink key={item.key} to={item.to} aria-current={view.activeNavigation(item.key, view.route) ? "page" : undefined} className={classNames(["flex min-h-12 items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold", view.activeNavigation(item.key, view.route) ? "bg-brand-raised text-brand-navy" : "text-brand-navy hover:bg-brand-surface"])} onClick={$event => {
        view.navigate(item);
      }}>
          <AppIcon name={item.key === "home" ? "home" : item.key === "advisor" ? "tools" : item.key} />
          <span>{(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(item.label)}</span>
          {view.vertical && <span className="drawer-chevron" aria-hidden="true">›</span>}
        </SiteLink>)}
    </nav></>;
});
