import React, { useRef } from "react";
function useResourceStateState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  return {
    ...inputProps
  };
}
export default React.forwardRef(function ResourceState(props, ref) {
  const view = useResourceStateState(props, ref);
  return <>{view.state.error ? <div role="alert" className="my-4 rounded-xl bg-[var(--ui-error-bg)] text-[var(--ui-error-text)] p-4 text-xs">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.error)}{" "}
        <button className="underline ml-3" disabled={view.state.busy} onClick={$event => {
        view.state.load?.(view.state.page || 0);
      }}>
          {"Thử lại"}
        </button>
      </div> : null}{view.state.busy ? <p role="status" className="my-4 text-xs text-brand-muted">
        {"Đang xử lý…"}
      </p> : null}{view.state.notice ? <p role="status" className="my-4 rounded-xl bg-[var(--ui-success-bg)] text-[var(--ui-success-text)] p-4 text-xs">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.notice)}
      </p> : null}</>;
});
