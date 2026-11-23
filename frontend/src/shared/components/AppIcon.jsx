import { classNames } from "../lib/ui.js";
import React, { useRef } from "react";
function useAppIconState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const paths = {
    newspaper: "M4 4h16v16H4ZM7 8h4v4H7Zm7 0h3m-3 4h3M7 16h10",
    home: "m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z",
    properties: "M4 21V5l8-3 8 3v16M9 21v-5h6v5M8 7h1m6 0h1M8 11h1m6 0h1",
    projects: "M3 21V9h7v12m0-17h11v17M14 8h3m-3 4h3m-3 4h3",
    gis: "m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Zm6-3v15m6-12v15",
    market: "M4 3v18h17M8 16l4-5 4 2 5-8",
    tools: "M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm1 4h8M8 11h1m6 0h1m-8 4h1m6 0h1m-8 3h1m6 0h1",
    user: "M20 21a8 8 0 0 0-16 0M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8",
    heart: "M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z",
    bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4",
    messages: "M21 11a8 8 0 0 1-8 8H7l-5 3 2-6a8 8 0 0 1 7-13h2a8 8 0 0 1 8 8ZM7 10h10m-10 4h6",
    shield: "m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Zm-4 10 3 3 5-6",
    clock: "M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    email: "M3 5h18v14H3Zm0 1 9 7 9-7",
    report: "M6 2h9l4 4v16H5V2Zm3 7h6m-6 4h6m-6 4h4",
    briefcase: "M8 6V3h8v3M3 7h18v14H3Zm0 6h18M10 11v4h4v-4",
    camera: "M3 7h4l2-3h6l2 3h4v14H3Zm13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
    edit: "m14 4 6 6M3 21l5-1L21 7l-6-6L2 14Z",
    arrow: "M5 12h14m-6-6 6 6-6 6",
    logout: "M9 3H3v18h6m6-15 6 6-6 6m-8-6h14",
    lifestyle: "M12 21S2 15 2 8a5 5 0 0 1 10-1A5 5 0 0 1 22 8c0 7-10 13-10 13Z"
  };
  return {
    ...inputProps,
    paths,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["name", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AppIcon(props, ref) {
  const view = useAppIconState(props, ref);
  return <><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...view.rootAttributes} className={classNames(["size-5 shrink-0", view.rootAttributes.className])}>
      <path d={view.paths[view.name] || view.paths.user} />
    </svg></>;
});
