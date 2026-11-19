import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import ValuationPanel from "./ValuationPanel.jsx";
import ValuationHistory from "./ValuationHistory.jsx";
function useValuationViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const [history] = useState(() => createStateStore(null)),
    [refreshKey] = useState(() => createStateStore(0));
  useSyncExternalStore(refreshKey.subscribe, refreshKey.getSnapshot);
  useSyncExternalStore(history.subscribe, history.getSnapshot);
  return {
    ...inputProps,
    history: history.getSnapshot(),
    refreshKey: refreshKey.getSnapshot(),
    updateHistoryValue: history.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateRefreshKeyValue: refreshKey.set
  };
}
export default React.forwardRef(function ValuationView(props, ref) {
  const view = useValuationViewState(props, ref);
  return <><main data-ui-view="ValuationView" {...view.rootAttributes} className={classNames(["min-h-screen bg-[var(--ui-surface)] text-[var(--ui-accent)] px-5 py-8 sm:py-12", view.rootAttributes.className])}>
      <div className="max-w-3xl mx-auto">
        <nav className="flex flex-wrap justify-between gap-4 mb-8 text-sm">
          <SiteLink to="/home" className="font-semibold">
            {"SmartProp"}
          </SiteLink>
          <SiteLink to="/listings" className="underline underline-offset-4">
            {"Xem tin bất động sản"}
          </SiteLink>
        </nav>
        <header className="page-intro-banner">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          {"Tham khảo giá trước khi quyết định"}
        </h1>
        <p className="mt-4 mb-8 text-sm leading-6 text-[var(--ui-accent)]">
          {"Ước tính tổng giá rao nhà ở, đất nền và căn hộ tại các địa bàn Đà Nẵng mà mô hình hỗ trợ."}
        </p>
        </header>
        <ValuationPanel historyEnabled={true} onSaved={$event => {
          view.updateRefreshKeyValue(view.refreshKey + 1);
        }} onOptionsLoaded={$event => {
          view.history?.setLabels($event);
        }} />
        <ValuationHistory ref={view.updateHistoryValue} refreshKey={view.refreshKey} />
      </div>
    </main></>;
});
