import { classNames } from "../../shared/lib/ui.js";
import React, { useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import ProjectDirectory from "./ProjectDirectory.jsx";
import { usePublicProjects } from "./usePublicProjects.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
function useProjectsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const state = usePublicProjects();
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  return {
    ...inputProps,
    state,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ProjectsView(props, ref) {
  const view = useProjectsViewState(props, ref);
  return <><div data-ui-view="ProjectsView" data-projects-page="" {...view.rootAttributes} className={classNames(["sp-container py-10 sm:py-14", view.rootAttributes.className])}>
      <header className="page-intro-banner">
      <p className="mb-3 text-xs font-semibold tracking-[.24em] text-brand-accent">
        {"PROJECTS · ĐÀ NẴNG"}
      </p>
      <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">
        {"Dự án bất động sản"}
      </h1>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-brand-muted">
        {"Khám phá các dự án giới thiệu qua website chính thức và các dự án được công bố trên SmartProp."}
      </p>
      </header>
      <section aria-labelledby="project-directory-heading" className="mt-10">
        <h2 id="project-directory-heading" className="mb-3 text-2xl font-semibold">
          {"Danh mục giới thiệu"}
        </h2>
        <p className="mb-6 text-sm leading-7 text-brand-muted">
          {"Website chủ đầu tư và đơn vị phát triển."}
        </p>
        <ProjectDirectory />
      </section>
      <section aria-labelledby="backend-projects-heading" className="mt-12 border-t border-brand-line pt-10">
        <h2 id="backend-projects-heading" className="text-2xl font-semibold">
          {"Dự án trên SmartProp"}
        </h2>

        <ResourceState state={view.state} />
        {view.state.busy ? <div className="mt-6 grid gap-5 md:grid-cols-3" aria-hidden="true">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(3, n => <div key={n} className="h-48 rounded-panel bg-brand-surface" />)}
          </div> : view.state.items.length ? <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {((items, render) => typeof items === "number" ? Array.from({
            length: Math.max(0, items)
          }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.items, project => <SiteLink key={project.id} to={"/projects/" + project.id} className="flex min-w-0 flex-col gap-3 rounded-panel border border-brand-line bg-brand-card p-6 transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-gold" data-project-card={project.id}>
                <span className="text-xs text-brand-accent">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.developer || "Chưa cung cấp chủ đầu tư")}
                </span>
                <h3 className="break-words text-xl font-semibold">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.name)}
                </h3>
                <p className="text-sm leading-7 text-brand-muted">
                  {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.address || "Chưa cung cấp địa chỉ")}
                </p>
                <span className="mt-auto pt-2 text-xs font-semibold">
                  {"Xem thông tin dự án ↗"}
                </span>
              </SiteLink>)}
          </div> : !view.state.error ? <div className="projects-empty mt-6 rounded-panel border border-brand-line bg-brand-card p-8 text-sm text-brand-muted">
            <span className="projects-empty-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M4 21V5h10v16M14 10h6v11M2 21h20M8 9h2M8 13h2M8 17h2M17 14h1M17 18h1" /></svg>
            </span>
            <h3>Chưa có dự án được công bố trên SmartProp</h3>
          </div> : null}
        <Pagination state={view.state} />
      </section>
    </div></>;
});
