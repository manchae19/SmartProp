import React, { useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import { useRouteState } from "../../app/navigation.jsx";
import { postSteps } from "./postForm.js";
function usePostValidationSummaryState(inputProps, forwardedRef) {
  inputProps = {
    issues: (() => [])(),
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  ({
    issues: (() => [])(),
    ...inputProps
  });
  const route = useRouteState();
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  return {
    ...inputProps,
    postSteps,
    route
  };
}
export default React.forwardRef(function PostValidationSummary(props, ref) {
  const view = usePostValidationSummaryState(props, ref);
  return <>{view.issues.length ? <section role="alert" aria-label="Thông tin cần sửa" className="my-4 rounded-xl bg-[var(--ui-error-bg)] p-4 text-xs text-[var(--ui-error-text)]">
        <p className="font-semibold">
          {"Vui lòng kiểm tra thông tin sau. Bấm vào lỗi để đến đúng bước cần sửa:"}
        </p>
        <ul className="mt-2 space-y-2">
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.issues, (issue, index) => <li key={issue.field + index}>
              <SiteLink to={{
            path: view.postSteps[issue.step - 1].path,
            query: view.route.query,
            hash: "#post-" + issue.field
          }} className="underline underline-offset-2">
                {"Bước "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(issue.step)}
                {" · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(issue.label)}
                {": "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(issue.message)}
              </SiteLink>
            </li>)}
        </ul>
      </section> : null}</>;
});
