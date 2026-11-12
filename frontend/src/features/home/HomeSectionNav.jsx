import { afterPaint, classNames } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { scrollHomeSection } from "../../shared/lib/siteNavigation.js";
import AppIcon from "../../shared/components/AppIcon.jsx";
import "./HomeSectionNav.css";
function useHomeSectionNavState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const sections = [{
    id: "search",
    label: "Bất động sản",
    icon: "properties"
  }, {
    id: "gis",
    label: "GIS Explorer",
    icon: "gis"
  }, {
    id: "lifestyle",
    label: "Phong cách sống",
    icon: "lifestyle"
  }, {
    id: "market",
    label: "Thị trường",
    icon: "market"
  }, {
    id: "projects",
    label: "Dự án",
    icon: "projects"
  }];
  const [bar] = useState(() => createStateStore(null));
  useSyncExternalStore(bar.subscribe, bar.getSnapshot);
  const [list] = useState(() => createStateStore(null));
  useSyncExternalStore(list.subscribe, list.getSnapshot);
  const [pinned] = useState(() => createStateStore(false));
  useSyncExternalStore(pinned.subscribe, pinned.getSnapshot);
  const [active] = useState(() => createStateStore(""));
  useSyncExternalStore(active.subscribe, active.getSnapshot);
  const _frameRef = useRef(0);
  const _observerRef = useRef(undefined);
  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
  function update() {
    _frameRef.current = 0;
    if (!bar.getSnapshot()) return;
    const headerHeight = document.querySelector(".app-header")?.offsetHeight || 0;
    pinned.set(bar.getSnapshot().getBoundingClientRect().top <= headerHeight + 1);
    const boundary = headerHeight + bar.getSnapshot().offsetHeight + 64;
    let current = "";
    for (const section of sections) {
      const target = document.getElementById(section.id);
      if (target && target.getBoundingClientRect().top <= boundary) current = section.id;
    }
    active.set(current);
  }
  function schedule() {
    if (!_frameRef.current) _frameRef.current = requestAnimationFrame(update);
  }
  function navigate(id) {
    scrollHomeSection(id);
  }
  const _watched = active.getSnapshot();
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
    const result = (async id => {
      await afterPaint();
      const link = list.getSnapshot()?.querySelector(`[href="#${id}"]`);
      if (!link || !list.getSnapshot()) return;
      const bounds = link.getBoundingClientRect();
      const viewport = list.getSnapshot().getBoundingClientRect();
      if (bounds.left < viewport.left || bounds.right > viewport.right) {
        list.getSnapshot().scrollTo({
          left: list.getSnapshot().scrollLeft + bounds.left - viewport.left - (viewport.width - bounds.width) / 2,
          behavior: reducedMotion() ? "instant" : "smooth"
        });
      }
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => {
    const result = (() => {
      window.addEventListener("scroll", schedule, {
        passive: true
      });
      window.addEventListener("resize", schedule);
      _observerRef.current = new ResizeObserver(schedule);
      _observerRef.current.observe(bar.getSnapshot());
      for (const section of sections) {
        const target = document.getElementById(section.id);
        if (target) _observerRef.current.observe(target);
      }
      schedule();
      const initial = window.location.hash.slice(1);
      if (sections.some(section => section.id === initial)) requestAnimationFrame(() => navigate(initial));
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    window.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", schedule);
    _observerRef.current?.disconnect();
    if (_frameRef.current) cancelAnimationFrame(_frameRef.current);
  })(), []);
  return {
    ...inputProps,
    sections,
    pinned: pinned.getSnapshot(),
    active: active.getSnapshot(),
    navigate,
    updateBarValue: bar.set,
    updateListValue: list.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["district", "filters", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function HomeSectionNav(props, ref) {
  const view = useHomeSectionNavState(props, ref);
  return <><div ref={view.updateBarValue} data-pinned={view.pinned} data-sp-7582756e="" {...view.rootAttributes} className={classNames([classNames(["home-section-nav sticky top-[var(--sp-header-height)] z-40 bg-brand-cream/95 text-brand-navy backdrop-blur-xl", {
      "shadow-lg shadow-[#142B4F]/5": view.pinned
    }]), view.rootAttributes.className])}>
      <div className="sp-container flex h-[var(--sp-section-nav-height)] items-center gap-3" data-sp-7582756e="">
        <nav ref={view.updateListValue} aria-label="Điều hướng các mục trang chủ" className="mx-auto min-w-0 max-w-[1040px] flex-1 overflow-x-auto overscroll-x-contain" data-sp-7582756e="">
          <div className="mx-auto flex w-max items-center gap-1 p-1.5" data-sp-7582756e="">
            {((items, render) => typeof items === "number" ? Array.from({
              length: Math.max(0, items)
            }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.sections, section => <a key={section.id} href={"#" + section.id} aria-current={view.active === section.id ? "location" : undefined} className={classNames(["inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ui-border)] sm:text-[13px]", view.active === section.id ? "bg-[var(--ui-soft)] text-brand-navy shadow-sm" : "text-[var(--ui-accent)] hover:bg-[var(--ui-surface)] hover:text-[var(--ui-accent)]"])} onClick={$event => {
              $event.preventDefault();
              view.navigate(section.id);
            }} data-sp-7582756e="">
                <AppIcon name={section.icon} className="!size-4" data-sp-7582756e="" />
                <span data-sp-7582756e="">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(section.label)}
                </span>
              </a>)}
          </div>
        </nav>
      </div>
    </div></>;
});
