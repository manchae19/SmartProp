import { classNames } from "../lib/ui.js";
import React, { useRef } from "react";
import { poiSvgPath } from "../../features/map/nearbyPlaces.js";
function usePoiIconState(inputProps, forwardedRef) {
  inputProps = {
    category: "",
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const props = {
    category: "",
    ...inputProps
  };
  const _props = useRef(props);
  _props.current = props;
  const getPath = () => poiSvgPath(_props.current.category);
  return {
    ...inputProps,
    path: getPath(),
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["category", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function PoiIcon(props, ref) {
  const view = usePoiIconState(props, ref);
  return <><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...view.rootAttributes} className={classNames(["shrink-0", view.rootAttributes.className])}>
      <path d={view.path} />
    </svg></>;
});
