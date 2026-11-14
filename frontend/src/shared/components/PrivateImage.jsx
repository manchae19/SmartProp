import { createStateStore, stateKey } from "../state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { api, session } from "../../features/auth/api.js";
import "./PrivateImage.css";
function usePrivateImageState(inputProps, forwardedRef) {
  inputProps = {
    alt: "",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const props = {
    alt: "",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const [url] = useState(() => createStateStore("")),
    [failed] = useState(() => createStateStore(false));
  useSyncExternalStore(failed.subscribe, failed.getSnapshot);
  useSyncExternalStore(url.subscribe, url.getSnapshot);
  const _serialRef = useRef(0);
  function release() {
    if (url.getSnapshot()) URL.revokeObjectURL(url.getSnapshot());
    url.set("");
  }
  const _watched = (() => [_props.current.src, session.getSnapshot().token])();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    _initialized.current = true;
    const result = (async () => {
      const run = ++_serialRef.current;
      release();
      failed.set(false);
      if (!_props.current.src) return;
      try {
        const blob = await api(_props.current.src.replace(/^\/api\/v1/, ""), {
          responseType: "blob",
          authenticated: !!session.getSnapshot().token
        });
        if (run === _serialRef.current) url.set(URL.createObjectURL(blob));
      } catch {
        if (run === _serialRef.current) failed.set(true);
      }
    })(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  useEffect(() => () => (() => {
    _serialRef.current++;
    release();
  })(), []);
  return {
    ...inputProps,
    url: url.getSnapshot(),
    failed: failed.getSnapshot(),
    release,
    updateFailedValue: failed.set
  };
}
export default React.forwardRef(function PrivateImage(props, ref) {
  const view = usePrivateImageState(props, ref);
  return <>{view.url ? <img className={props.className} style={props.style} src={view.url} alt={view.alt} loading="lazy" onError={$event => {
      view.release();
      view.updateFailedValue(true);
    }} data-sp-55ccf5d3="" /> : <div className={["sp-placeholder", props.className].filter(Boolean).join(" ")} style={props.style} role="img" aria-label={view.alt} data-sp-55ccf5d3="">
        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.failed ? "Không tải được ảnh" : view.src ? "Đang tải ảnh…" : "Chưa có ảnh")}
      </div>}</>;
});
