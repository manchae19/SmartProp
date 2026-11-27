import { afterPaint, classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef, useEffect } from "react";
import { SiteLink, Outlet } from "../../app/navigation.jsx";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { api } from "../auth/api.js";
import AppHeader from "../../shared/components/layout/AppHeader.jsx";
import "./AdminLayout.css";
function useAdminLayoutState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const router = useAppNavigation(),
    route = useRouteState(),
    [pending] = useState(() => createStateStore("—")),
    [openReports] = useState(() => createStateStore("—"));
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  useSyncExternalStore(openReports.subscribe, openReports.getSnapshot);
  useSyncExternalStore(pending.subscribe, pending.getSnapshot);
  useEffect(() => {
    api("/admin/dashboard").then(s => {
      pending.set(s.pendingProperties);
      openReports.set(s.openReports);
    }).catch(() => {});
  }, []);
  const _watched = (() => _routeLatest.current.path)();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    if (!_initialized.current) {
      _initialized.current = true;
      return;
    }
    const result = (async () => {
      await afterPaint();
      document.getElementById("page-content")?.focus({
        preventScroll: true
      });
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  return {
    ...inputProps,
    router,
    pending: pending.getSnapshot(),
    openReports: openReports.getSnapshot(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AdminLayout(props, ref) {
  const view = useAdminLayoutState(props, ref);
  return <><div data-ui-view="AdminLayout" data-sp-87e8ba60="" {...view.rootAttributes} className={classNames(["admin-layout", view.rootAttributes.className])}>
      <a href="#page-content" className="fixed -top-20 left-4 z-[100] rounded-control bg-brand-card px-5 py-3 text-sm font-semibold shadow-lg focus:top-3" data-sp-87e8ba60="">
        {"Đến nội dung chính"}
      </a>
      <AppHeader data-sp-87e8ba60="" />
      <div className="section" data-sp-87e8ba60="">
        <div className="header" data-sp-87e8ba60="">
          <video autoPlay={true} muted={true} loop={true} playsInline={true} className="header-video" data-sp-87e8ba60="">
            <source src="/background.mp4" type="video/mp4" data-sp-87e8ba60="" />
            {" Trình duyệt của bạn không hỗ trợ thẻ video. "}
          </video>
          <div className="video-overlay" data-sp-87e8ba60="" />
          <div className="hcontent" data-sp-87e8ba60="">
            <div className="left" data-sp-87e8ba60="">
              <div className="badge" data-sp-87e8ba60="">
                <div className="qu-n-tr" data-sp-87e8ba60="">
                  {"QUẢN TRỊ"}
                </div>
              </div>
              <div className="b-ng-i-u-khi-n" data-sp-87e8ba60="">
                {"Bảng điều khiển"}
              </div>
              <div className="theo-d-i-tin-ng-n" data-sp-87e8ba60="">
                {" Theo dõi tin đăng, người dùng và trạng thái xử lý AI trong toàn hệ thống. "}
              </div>
            </div>
            <button type="button" className="postbtn" onClick={$event => {
              view.router.push("/post");
            }} data-sp-87e8ba60="">
              <div className="ng-tin" data-sp-87e8ba60="">
                {"Đăng tin"}
              </div>
              <div className="div" data-sp-87e8ba60="">
                {"+"}
              </div>
            </button>
          </div>
        </div>
        <div className="body-layout" data-sp-87e8ba60="">
          <aside className="sidebar" aria-label="Điều hướng quản trị" data-sp-87e8ba60="">
            <div className="m-c-qu-n-tr" data-sp-87e8ba60="">
              {"MỤC QUẢN TRỊ"}
            </div>
            <SiteLink to="/admin/dashboard" className="nav" activeClass="active-nav" data-sp-87e8ba60="">
              <div className="th-ng-k-t-ng-quan" data-sp-87e8ba60="">
                {"Thống kê tổng quan"}
              </div>
            </SiteLink>
            <SiteLink to="/admin/posts" className="nav2" activeClass="active-nav" data-sp-87e8ba60="">
              <div className="tin-ch-duy-t" data-sp-87e8ba60="">
                {"Tin chờ duyệt"}
              </div>
              <div className="count" data-sp-87e8ba60="">
                <div className="_18" data-sp-87e8ba60="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.pending)}
                </div>
              </div>
            </SiteLink>
            <SiteLink to="/admin/broker-applications" className="nav2" activeClass="active-nav" data-sp-87e8ba60="">
              <div data-sp-87e8ba60="">
                {"Duyệt quyền đăng tin"}
              </div>
            </SiteLink>
            <SiteLink to="/admin/users" className="nav2" activeClass="active-nav" data-sp-87e8ba60="">
              <div className="ng-i-d-ng" data-sp-87e8ba60="">
                {"Người dùng"}
              </div>
            </SiteLink>
            <SiteLink to="/admin/reports" className="nav2" activeClass="active-nav" data-sp-87e8ba60="">
              <div className="b-o-c-o-tin-ng" data-sp-87e8ba60="">
                {"Báo cáo tin đăng"}
              </div>
              <div className="count" data-sp-87e8ba60="">
                <div className="_7" data-sp-87e8ba60="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.openReports)}
                </div>
              </div>
            </SiteLink>
            <SiteLink to="/admin/coordinate-review" className="nav2" activeClass="active-nav" data-sp-87e8ba60="">
              <div data-sp-87e8ba60="">
                {"Xác minh tọa độ"}
              </div>
            </SiteLink>
            <SiteLink to="/admin/audit-logs" className="nav" activeClass="active-nav" data-sp-87e8ba60="">
              <div className="nh-t-ký-ki-m-to-n" data-sp-87e8ba60="">
                {"Nhật ký kiểm toán"}
              </div>
            </SiteLink>
            <SiteLink to="/admin/projects" className="nav" activeClass="active-nav" data-sp-87e8ba60="">
              <div data-sp-87e8ba60="">
                {"Dự án"}
              </div>
            </SiteLink>
            <SiteLink to="/admin/ai-config" className="nav" activeClass="active-nav" data-sp-87e8ba60="">
              <div className="c-u-h-nh-ai" data-sp-87e8ba60="">
                {"Cấu hình AI"}
              </div>
            </SiteLink>
          </aside>
          <main id="page-content" tabIndex="-1" className="main-content-area outline-none" data-sp-87e8ba60="">
            <Outlet data-sp-87e8ba60="" />
          </main>
        </div>
      </div>
    </div></>;
});
