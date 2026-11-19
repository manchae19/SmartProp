import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import "./HomeGIS.css";
const PropertyExplorer = (() => {
  const Panel = React.lazy(() => import("./PropertyExplorer.jsx"));
  return React.forwardRef((props, ref) => React.createElement(React.Suspense, {
    fallback: React.createElement("span", {
      role: "status"
    }, "Loading...")
  }, React.createElement(Panel, {
    ...props,
    ref
  })));
})();
function useHomeGISState(inputProps, forwardedRef) {
  inputProps = {
    items: (() => [])(),
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    items: (() => [])(),
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const emit = undefined;
  const [host] = useState(() => createStateStore(null)),
    [activated] = useState(() => createStateStore(false));
  useSyncExternalStore(activated.subscribe, activated.getSnapshot);
  useSyncExternalStore(host.subscribe, host.getSnapshot);
  const getExploreLink = () => ({
    ...(_props.current.mapLink || {
      path: "/map"
    }),
    query: {
      ...(_props.current.mapLink?.query || {}),
      ...(_props.current.selectedId ? {
        propertyId: _props.current.selectedId
      } : {})
    }
  });
  const _observerRef = useRef(undefined);
  useEffect(() => {
    const result = (() => {
      if (!("IntersectionObserver" in window)) {
        activated.set(true);
        return;
      }
      _observerRef.current = new IntersectionObserver(entries => {
        if (entries.some(e => e.isIntersecting)) {
          activated.set(true);
          _observerRef.current.disconnect();
        }
      }, {
        rootMargin: "160px"
      });
      _observerRef.current.observe(host.getSnapshot());
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => _observerRef.current?.disconnect())(), []);
  return {
    ...inputProps,
    PropertyExplorer,
    props,
    emit,
    host: host.getSnapshot(),
    activated: activated.getSnapshot(),
    exploreLink: getExploreLink(),
    observer: _observerRef.current,
    updateHost: host.edit,
    updateHostValue: host.set,
    updateActivated: activated.edit,
    updateActivatedValue: activated.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["items", "selectedId", "total", "mapLink", "busy", "error", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function HomeGIS(props, ref) {
  const view = useHomeGISState(props, ref);
  return <><div ref={view.updateHostValue} data-sp-98ad1ee1="" {...view.rootAttributes} className={classNames(["home-gis", view.rootAttributes.className])}>
      {view.error ? <p role="alert" className="home-gis-message" data-sp-98ad1ee1="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}{" "}
          <button type="button" onClick={$event => {
          view.onRetry?.();
        }} data-sp-98ad1ee1="">
            {"Thử lại"}
          </button>
        </p> : null}
      {view.busy ? <p role="status" className="home-gis-message" data-sp-98ad1ee1="">
          {"Đang tải tin trên bản đồ…"}
        </p> : null}
      {view.activated ? <view.PropertyExplorer items={view.items} selectedId={view.selectedId} exploreLink={view.exploreLink} preview={true} onSelect={$event => {
        view.onUpdateSelectedId?.($event);
      }} data-sp-98ad1ee1="" /> : <button className="home-gis-activate" type="button" onClick={$event => {
        view.updateActivatedValue(true);
      }} data-sp-98ad1ee1="">
          {"⌖ Khám phá vị trí trên bản đồ"}
        </button>}
    </div></>;
});
