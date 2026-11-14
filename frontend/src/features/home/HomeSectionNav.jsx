import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "../../shared/state/store.js";
import { scrollHomeSection } from "../../shared/lib/siteNavigation.js";
import AppIcon from "../../shared/components/AppIcon.jsx";
import "./HomeSectionNav.css";
function setup(__props) {
  propsForSetup(__props, {
    district: String,
    filters: Object,
  });
  const sections = [
    {
      id: "search",
      label: "Bất động sản",
      icon: "properties",
    },
    {
      id: "gis",
      label: "GIS Explorer",
      icon: "gis",
    },
    {
      id: "lifestyle",
      label: "Phong cách sống",
      icon: "lifestyle",
    },
    {
      id: "market",
      label: "Thị trường",
      icon: "market",
    },
    {
      id: "projects",
      label: "Dự án",
      icon: "projects",
    },
  ];
  const bar = ref(null);
  const list = ref(null);
  const pinned = ref(false);
  const active = ref("");
  let frame = 0;
  let observer;
  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
  function update() {
    frame = 0;
    if (!bar.value) return;
    const headerHeight =
      document.querySelector(".app-header")?.offsetHeight || 0;
    pinned.value = bar.value.getBoundingClientRect().top <= headerHeight + 1;
    const boundary = headerHeight + bar.value.offsetHeight + 64;
    let current = "";
    for (const section of sections) {
      const target = document.getElementById(section.id);
      if (target && target.getBoundingClientRect().top <= boundary)
        current = section.id;
    }
    active.value = current;
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(update);
  }
  function navigate(id) {
    scrollHomeSection(id);
  }
  watch(active, async (id) => {
    await nextTick();
    const link = list.value?.querySelector(`[href="#${id}"]`);
    if (!link || !list.value) return;
    const bounds = link.getBoundingClientRect();
    const viewport = list.value.getBoundingClientRect();
    if (bounds.left < viewport.left || bounds.right > viewport.right) {
      list.value.scrollTo({
        left:
          list.value.scrollLeft +
          bounds.left -
          viewport.left -
          (viewport.width - bounds.width) / 2,
        behavior: reducedMotion() ? "instant" : "smooth",
      });
    }
  });
  onMounted(() => {
    window.addEventListener("scroll", schedule, {
      passive: true,
    });
    window.addEventListener("resize", schedule);
    observer = new ResizeObserver(schedule);
    observer.observe(bar.value);
    for (const section of sections) {
      const target = document.getElementById(section.id);
      if (target) observer.observe(target);
    }
    schedule();
    const initial = window.location.hash.slice(1);
    if (sections.some((section) => section.id === initial))
      requestAnimationFrame(() => navigate(initial));
  });
  onBeforeUnmount(() => {
    window.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", schedule);
    observer?.disconnect();
    if (frame) cancelAnimationFrame(frame);
  });
  return {
    nextTick,
    onBeforeUnmount,
    onMounted,
    ref,
    watch,
    scrollHomeSection,
    AppIcon,
    sections,
    bar,
    list,
    pinned,
    active,
    frame,
    observer,
    reducedMotion,
    update,
    schedule,
    navigate,
  };
}
export default React.forwardRef(function HomeSectionNav(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        ref: bindRef(ctx, "bar"),
        className: ["home-section-nav sticky top-[var(--sp-header-height)] z-40 bg-brand-cream/95 text-brand-navy backdrop-blur-xl", {
          "shadow-lg shadow-[#142B4F]/5": ctx.pinned,
        }],
        
        "data-pinned": ctx.pinned,
        "data-sp-7582756e": "",
      })}
    >
      <div
        {...mergeProps({
          className:
            "sp-container flex h-[var(--sp-section-nav-height)] items-center gap-3",
          "data-sp-7582756e": "",
        })}
      >
        <nav
          {...mergeProps({
            ref: bindRef(ctx, "list"),
            "aria-label": "Điều hướng các mục trang chủ",
            className:
              "mx-auto min-w-0 max-w-[1040px] flex-1 overflow-x-auto overscroll-x-contain",
            "data-sp-7582756e": "",
          })}
        >
          <div
            {...mergeProps({
              className: "mx-auto flex w-max items-center gap-1 p-1.5",
              "data-sp-7582756e": "",
            })}
          >
            {renderList(ctx.sections, (section) => (
              <a
                key={section.id}
                {...mergeProps({
                  href: "#" + section.id,
                  "aria-current":
                    ctx.active === section.id ? "location" : undefined,
                  className: ["inline-flex min-h-10 items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ui-border)] sm:text-[13px]", ctx.active === section.id
                      ? "bg-[var(--ui-soft)] text-brand-navy shadow-sm"
                      : "text-[var(--ui-accent)] hover:bg-[var(--ui-surface)] hover:text-[var(--ui-accent)]"],
                  
                  onClick: ($event) => {
                    $event.preventDefault();
                    ctx.navigate(section.id);
                  },
                  "data-sp-7582756e": "",
                })}
              >
                <AppIcon
                  {...mergeProps({
                    name: section.icon,
                    className: "!size-4",
                    "data-sp-7582756e": "",
                  })}
                />
                <span
                  {...mergeProps({
                    "data-sp-7582756e": "",
                  })}
                >
                  {display(section.label)}
                </span>
              </a>
            ))}
          </div>
        </nav>
      </div>
    </div>,
  ]);
});
