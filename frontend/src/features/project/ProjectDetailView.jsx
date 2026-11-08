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
  ref,
  computed,
  watch,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRoute } from "../../shared/routing/router.jsx";
import { api, errorText } from "../auth/api.js";
import { googlePointUrl } from "../map/googleMapsLocation.js";
function setup(__props) {
  const route = useRoute(),
    project = ref(null),
    busy = ref(false),
    error = ref("");
  let sequence = 0;
  async function load() {
    const run = ++sequence;
    busy.value = true;
    error.value = "";
    project.value = null;
    try {
      const result = await api(
        "/projects/" + encodeURIComponent(String(route.params.id)),
        {
          authenticated: false,
        },
      );
      if (run === sequence) project.value = result;
    } catch (failure) {
      if (run === sequence)
        error.value =
          failure.status === 404
            ? "Dự án không tồn tại hoặc chưa được công bố."
            : errorText(failure);
    } finally {
      if (run === sequence) busy.value = false;
    }
  }
  watch(() => route.params.id, load, {
    immediate: true,
  });
  onBeforeUnmount(() => sequence++);
  const mapLink = computed(() =>
    project.value
      ? googlePointUrl(project.value.latitude, project.value.longitude)
      : "",
  );
  return {
    ref,
    computed,
    watch,
    onBeforeUnmount,
    useRoute,
    api,
    errorText,
    googlePointUrl,
    route,
    project,
    busy,
    error,
    sequence,
    load,
    mapLink,
  };
}
export default React.forwardRef(function ProjectDetailView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ProjectDetailView"
      {...mergeProps({
        className: "sp-container py-10 sm:py-14",
        "data-project-detail": "",
      })}
    >
      <RouterLink
        {...mergeProps({
          to: "/projects",
          className: "text-sm font-semibold text-brand-accent",
        })}
      >
        {"← Danh sách dự án"}
      </RouterLink>
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-8 text-sm text-brand-muted",
          })}
        >
          {"Đang tải dự án…"}
        </p>
      ) : ctx.error ? (
        <div
          {...mergeProps({
            role: "alert",
            className:
              "mt-8 rounded-panel border border-[var(--ui-error-border)] bg-[var(--ui-error-bg)] p-6 text-sm text-[var(--ui-error-text)]",
          })}
        >
          {display(ctx.error)}
          <button
            {...mergeProps({
              type: "button",
              className: "ml-3 font-semibold underline",
              onClick: ($event) => {
                return ctx.load?.($event);
              },
            })}
          >
            {"Thử lại"}
          </button>
        </div>
      ) : ctx.project ? (
        <article
          {...mergeProps({
            className: "mt-8",
          })}
        >
          <p
            {...mergeProps({
              className:
                "text-xs font-semibold tracking-[.2em] text-brand-accent",
            })}
          >
            {"DỮ LIỆU TỪ SMARTPROP"}
          </p>
          <h1
            {...mergeProps({
              className:
                "mt-3 max-w-4xl break-words text-3xl font-semibold tracking-tight sm:text-5xl",
            })}
          >
            {display(ctx.project.name)}
          </h1>
          <p
            {...mergeProps({
              className: "mt-4 text-sm leading-7 text-brand-muted",
            })}
          >
            {
              "Chưa có ảnh dự án."
            }
          </p>
          <dl
            {...mergeProps({
              className:
                "mt-8 grid gap-5 rounded-panel border border-brand-line bg-brand-card p-6 sm:grid-cols-2 sm:p-8",
            })}
          >
            {renderList(
              {
                developer: "Chủ đầu tư",
                address: "Địa chỉ",
                scale: "Quy mô",
                handoverYear: "Năm bàn giao",
              },
              (label, key) => (
                <div
                  key={key}
                  {...mergeProps({
                    className: "min-w-0",
                  })}
                >
                  <dt
                    {...mergeProps({
                      className: "text-xs text-brand-muted",
                    })}
                  >
                    {display(label)}
                  </dt>
                  <dd
                    {...mergeProps({
                      className: "mt-2 break-words text-base font-medium",
                    })}
                  >
                    {display(ctx.project[key] || "Chưa cung cấp")}
                  </dd>
                </div>
              ),
            )}
            <div
              {...mergeProps({
                className: "sm:col-span-2",
              })}
            >
              <dt
                {...mergeProps({
                  className: "text-xs text-brand-muted",
                })}
              >
                {"Tiện ích theo hồ sơ dự án"}
              </dt>
              <dd
                {...mergeProps({
                  className: "mt-2 text-sm leading-7",
                })}
              >
                {display(ctx.project.amenities?.join(", ") || "Chưa cung cấp")}
              </dd>
            </div>
          </dl>
          {ctx.mapLink ? (
            <a
              {...mergeProps({
                href: ctx.mapLink,
                target: "_blank",
                rel: "noopener noreferrer",
                className: "sp-button sp-button-secondary mt-6",
              })}
            >
              {"Mở tọa độ dự án trên Google Maps ↗"}
            </a>
          ) : null}
        </article>
      ) : null}
    </div>,
  ]);
});
