import { classNames } from "../../lib/ui.js";
import React, { useSyncExternalStore, useRef } from "react";
import { SiteLink } from "../../../app/navigation.jsx";
import { useRouteState } from "../../../app/navigation.jsx";
import { listingLink, normalizeFilters } from "../../../features/property/listingFilters.js";
import { session } from "../../../features/auth/api.js";
function useAppFooterState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useRouteState(),
    getFilters = () => normalizeFilters(_routeLatest.current.query);
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  return {
    ...inputProps,
    listingLink,
    session: session.getSnapshot(),
    filters: getFilters(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AppFooter(props, ref) {
  const view = useAppFooterState(props, ref);
  return <><footer id="account" {...view.rootAttributes} className={classNames(["app-footer mt-auto bg-brand-raised py-10 pb-36 text-brand-navy", view.rootAttributes.className])}>
      <div className="sp-container grid gap-8 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <SiteLink to={view.listingLink("/home", view.filters)} className="text-2xl font-bold tracking-tight">
            {"SmartProp"}
            <span className="text-brand-highlight">
              {"."}
            </span>
          </SiteLink>
          <p className="mt-3 max-w-sm text-sm leading-7 text-brand-navy">
            {"Khám phá bất động sản và không gian sống tại Đà Nẵng."}
          </p>
        </div>
        <nav aria-label="Khám phá cuối trang" className="grid content-start gap-3 text-sm text-brand-navy">
          <SiteLink to={view.listingLink("/listings", view.filters)}>
            {"Bất động sản"}
          </SiteLink>
          <SiteLink to="/projects">
            {"Dự án"}
          </SiteLink>
          <SiteLink to={view.listingLink("/map", view.filters)}>
            {"Bản đồ GIS"}
          </SiteLink>
        </nav>
        <nav aria-label="Tiện ích cuối trang" className="grid content-start gap-3 text-sm text-brand-navy">
          <SiteLink to="/market">
            {"Dữ liệu thị trường"}
          </SiteLink>
          <SiteLink to={{
            ...view.listingLink("/home", view.filters),
            hash: "#finance"
          }}>
            {"Công cụ tài chính"}
          </SiteLink>
          <SiteLink to={view.session.token ? "/account" : "/login"}>
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.session.token ? "Hồ sơ cá nhân" : "Đăng nhập / Tạo tài khoản")}
          </SiteLink>
        </nav>
      </div>
    </footer></>;
});
