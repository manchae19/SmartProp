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
import { useRoute } from "../../shared/routing/router.jsx";
import { postSteps } from "./postForm.js";
function setup(__props) {
  propsForSetup(__props, {
    issues: {
      type: Array,
      default: () => [],
    },
  });
  const route = useRoute();
  return {
    useRoute,
    postSteps,
    route,
  };
}
export default React.forwardRef(function PostValidationSummary(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    ctx.issues.length ? (
      <section
        {...mergeProps({
          role: "alert",
          "aria-label": "Thông tin cần sửa",
          className: "my-4 rounded-xl bg-[var(--ui-error-bg)] p-4 text-xs text-[var(--ui-error-text)]",
        })}
      >
        <p
          {...mergeProps({
            className: "font-semibold",
          })}
        >
          {
            "Vui lòng kiểm tra thông tin sau. Bấm vào lỗi để đến đúng bước cần sửa:"
          }
        </p>
        <ul
          {...mergeProps({
            className: "mt-2 space-y-2",
          })}
        >
          {renderList(ctx.issues, (issue, index) => (
            <li key={issue.field + index} {...mergeProps({})}>
              <RouterLink
                {...mergeProps({
                  to: {
                    path: ctx.postSteps[issue.step - 1].path,
                    query: ctx.route.query,
                    hash: "#post-" + issue.field,
                  },
                  className: "underline underline-offset-2",
                })}
              >
                {"Bước "}
                {display(issue.step)}
                {" · "}
                {display(issue.label)}
                {": "}
                {display(issue.message)}
              </RouterLink>
            </li>
          ))}
        </ul>
      </section>
    ) : null,
  ]);
});
