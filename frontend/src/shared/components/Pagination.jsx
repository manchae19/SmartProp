import React, { useRef } from "react";
function usePaginationState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  return {
    ...inputProps
  };
}
export default React.forwardRef(function Pagination(props, ref) {
  const view = usePaginationState(props, ref);
  return <>{view.state.totalPages > 1 ? <div className="listing-pagination flex justify-center items-center gap-5 py-6 text-xs text-[var(--ui-accent)]">
        <button disabled={view.state.busy || !view.state.page} className="rounded-full border px-4 py-2 bg-brand-card disabled:opacity-40" onClick={$event => {
        view.state.load(view.state.page - 1);
      }}>
          {"← Trước"}
        </button>
        <span>
          {"Trang "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.page + 1)}
          {" / "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalPages)}
          {" · "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" kết quả"}
        </span>
        <button disabled={view.state.busy || view.state.page + 1 >= view.state.totalPages} className="rounded-full border px-4 py-2 bg-brand-card disabled:opacity-40" onClick={$event => {
        view.state.load(view.state.page + 1);
      }}>
          {"Sau →"}
        </button>
      </div> : null}</>;
});
