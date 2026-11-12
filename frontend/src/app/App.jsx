import { useSyncExternalStore } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { session } from "../features/auth/api.js";
import SessionRecovery from "../features/auth/SessionRecovery.jsx";
import PageLayout from "../shared/components/layout/PageLayout.jsx";
import { RouteScroll } from "./navigation.jsx";
import WelcomeNotice from "../shared/components/WelcomeNotice.jsx";
import ComparisonTray from "../features/property/ComparisonTray.jsx";
import { usesPageLayout } from "../shared/lib/siteNavigation.js";
export default function App() {
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const route = useLocation();
  if (session.getSnapshot().status === "INITIALIZING") return <div role="status" className="grid min-h-screen place-items-center bg-brand-cream text-brand-navy">
        Đang khôi phục phiên đăng nhập…
      </div>;
  if (session.getSnapshot().status === "UNAVAILABLE") return <SessionRecovery />;
  return <>
      {usesPageLayout(route.pathname) ? <PageLayout>
          <Outlet />
        </PageLayout> : <Outlet />}
      <RouteScroll /><ComparisonTray />
      <WelcomeNotice />
    </>;
}
