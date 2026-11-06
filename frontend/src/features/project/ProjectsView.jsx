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
import ProjectDirectory from "./ProjectDirectory.jsx";
import { usePublicProjects } from "./usePublicProjects.js";
import { LegacyState, LegacyPager } from "../../shared/lib/legacy.js";
function setup(__props) {
  const state = usePublicProjects();
  return {
    ProjectDirectory,
    usePublicProjects,
    LegacyState,
    LegacyPager,
    state,
  };
}
export default React.forwardRef(function ProjectsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ProjectsView"
      {...mergeProps({
        className: "sp-container py-10 sm:py-14",
        "data-projects-page": "",
      })}
    >
      <header className="page-intro-banner">
      <p
        {...mergeProps({
          className:
            "mb-3 text-xs font-semibold tracking-[.24em] text-brand-accent",
        })}
      >
        {"PROJECTS · ĐÀ NẴNG"}
      </p>
      <h1
        {...mergeProps({
          className: "text-3xl font-semibold tracking-tight sm:text-5xl",
        })}
      >
        {"Dự án bất động sản"}
      </h1>
      <p
        {...mergeProps({
          className: "mt-4 max-w-2xl text-sm leading-7 text-brand-muted",
        })}
      >
        {
          "Khám phá các dự án giới thiệu qua website chính thức và các dự án được công bố trên SmartProp."
        }
      </p>
      </header>
      <section
        {...mergeProps({
          "aria-labelledby": "project-directory-heading",
          className: "mt-10",
        })}
      >
        <h2
          {...mergeProps({
            id: "project-directory-heading",
            className: "mb-3 text-2xl font-semibold",
          })}
        >
          {"Danh mục giới thiệu"}
        </h2>
        <p
          {...mergeProps({
            className: "mb-6 text-sm leading-7 text-brand-muted",
          })}
        >
          {"Website chủ đầu tư và đơn vị phát triển."}
        </p>
        <ProjectDirectory {...mergeProps({})} />
      </section>
      <section
        {...mergeProps({
          "aria-labelledby": "backend-projects-heading",
          className: "mt-12 border-t border-brand-line pt-10",
        })}
      >
        <h2
          {...mergeProps({
            id: "backend-projects-heading",
            className: "text-2xl font-semibold",
          })}
        >
          {"Dự án trên SmartProp"}
        </h2>
        <p
          {...mergeProps({
            className: "mt-3 text-sm text-brand-muted",
          })}
        >
          {"Thông tin dự án được công bố từ Backend."}
        </p>
        <LegacyState
          {...mergeProps({
            state: ctx.state,
          })}
        />
        {ctx.state.busy ? (
          <div
            {...mergeProps({
              className: "mt-6 grid gap-5 md:grid-cols-3",
              "aria-hidden": "true",
            })}
          >
            {renderList(3, (n) => (
              <div
                key={n}
                {...mergeProps({
                  className: "h-48 rounded-panel bg-brand-surface",
                })}
              />
            ))}
          </div>
        ) : ctx.state.items.length ? (
          <div
            {...mergeProps({
              className: "mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3",
            })}
          >
            {renderList(ctx.state.items, (project) => (
              <RouterLink
                key={project.id}
                {...mergeProps({
                  to: "/projects/" + project.id,
                  className:
                    "flex min-w-0 flex-col gap-3 rounded-panel border border-brand-line bg-brand-card p-6 transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold",
                  "data-project-card": project.id,
                })}
              >
                <span
                  {...mergeProps({
                    className: "text-xs text-brand-accent",
                  })}
                >
                  {display(project.developer || "Chưa cung cấp chủ đầu tư")}
                </span>
                <h3
                  {...mergeProps({
                    className: "break-words text-xl font-semibold",
                  })}
                >
                  {display(project.name)}
                </h3>
                <p
                  {...mergeProps({
                    className: "text-sm leading-7 text-brand-muted",
                  })}
                >
                  {display(project.address || "Chưa cung cấp địa chỉ")}
                </p>
                <span
                  {...mergeProps({
                    className: "mt-auto pt-2 text-xs font-semibold",
                  })}
                >
                  {"Xem thông tin dự án ↗"}
                </span>
              </RouterLink>
            ))}
          </div>
        ) : !ctx.state.error ? (
          <div
            {...mergeProps({
              className:
                "mt-6 rounded-panel border border-brand-line bg-brand-card p-8 text-sm text-brand-muted",
            })}
          >
            {"Chưa có dự án được công bố trên SmartProp."}
          </div>
        ) : null}
        <LegacyPager
          {...mergeProps({
            state: ctx.state,
          })}
        />
      </section>
    </div>,
  ]);
});
