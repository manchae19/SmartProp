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
import { onBeforeUnmount, onMounted, ref } from "../../shared/state/store.js";
function setup(__props) {
  const video = ref(null);
  const playing = ref(false);
  const failed = ref(false);
  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const reduced = ref(motion.matches);
  async function play() {
    if (!video.value) return;
    video.value.muted = true;
    try {
      await video.value.play();
    } catch {
      playing.value = false;
    }
  }
  function toggle() {
    if (playing.value) video.value?.pause();
    else play();
  }
  function motionChanged(event) {
    reduced.value = event.matches;
    if (event.matches) video.value?.pause();
    else play();
  }
  onMounted(() => {
    motion.addEventListener("change", motionChanged);
    if (!reduced.value) play();
  });
  onBeforeUnmount(() => motion.removeEventListener("change", motionChanged));
  return {
    onBeforeUnmount,
    onMounted,
    ref,
    video,
    playing,
    failed,
    motion,
    reduced,
    play,
    toggle,
    motionChanged,
  };
}
export default React.forwardRef(function HeroBackground(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "absolute inset-0",
      })}
    >
      <video
        {...mergeProps({
          ref: bindRef(ctx, "video"),
          autoPlay: !ctx.reduced,
          muted: true,
          loop: true,
          playsInline: true,
          preload: "metadata",
          poster: "/images/home/banner.png",
          "aria-label": "Video nền trang chủ SmartProp",
          className: "absolute inset-0 h-full w-full object-cover",
          onPlaying: ($event) => {
            ctx.playing = true;
          },
          onPause: ($event) => {
            ctx.playing = false;
          },
          onError: ($event) => {
            ctx.failed = true;
          },
        })}
      >
        <source
          {...mergeProps({
            src: "/background.mp4",
            type: "video/mp4",
          })}
        />
      </video>
      {!ctx.failed ? (
        <button
          {...mergeProps({
            type: "button",
            "aria-label": ctx.playing ? "Tạm dừng video nền" : "Phát video nền",
            className:
              "absolute right-4 top-4 z-20 flex cursor-pointer items-center gap-2 rounded-full border border-brand-line/30 bg-[var(--ui-soft)]/35 px-3 py-2 text-xs font-medium text-brand-navy/90 backdrop-blur-md transition hover:bg-[var(--ui-soft)]/65 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--ui-border)] md:right-10",
            onClick: ($event) => {
              return ctx.toggle?.($event);
            },
          })}
        >
          <svg
            {...mergeProps({
              width: "12",
              height: "12",
              viewBox: "0 0 16 16",
              fill: "currentColor",
              "aria-hidden": "true",
            })}
          >
            {ctx.playing ? (
              <path
                {...mergeProps({
                  d: "M4 2h3v12H4zm5 0h3v12H9z",
                })}
              />
            ) : (
              <path
                {...mergeProps({
                  d: "M4 2v12l10-6z",
                })}
              />
            )}
          </svg>{" "}
          {display(ctx.playing ? "Tạm dừng video" : "Phát video nền")}
        </button>
      ) : null}
    </div>,
  ]);
});
