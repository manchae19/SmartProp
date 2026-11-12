import { classNames } from "../lib/ui.js";
import React, { useRef } from "react";
import { SiteLink } from "../../app/navigation.jsx";
import AppIcon from "./AppIcon.jsx";
import "./ChatSessionPanel.css";
function useChatSessionPanelState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  const prompts = [{
    label: "Tìm nhà theo ngân sách",
    text: "Tôi có 10 tỷ, gợi ý bất động sản phù hợp và giải thích điểm đề xuất."
  }, {
    label: "Khám phá tiện ích khu vực",
    text: "Ở Hải Châu có những bệnh viện nào?"
  }, {
    label: "Kiểm tra lựa chọn dưới 2 tỷ",
    text: "Tôi có 2 tỷ, có bất động sản công khai phù hợp không?"
  }];
  return {
    ...inputProps,
    prompts,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["preview", "locked", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ChatSessionPanel(props, ref) {
  const view = useChatSessionPanelState(props, ref);
  return <><div data-ui-view="ChatSessionPanel" data-sp-57e2adde="" {...view.rootAttributes} className={classNames(["session-panel", view.rootAttributes.className])}>
      <p className="panel-eyebrow" data-sp-57e2adde="">
        {"TRONG TAB NÀY"}
      </p>
      <button className="current-conversation" type="button" aria-current="true" onClick={$event => {
        view.onCurrent?.();
      }} data-sp-57e2adde="">
        <span className="session-avatar" aria-hidden="true" data-sp-57e2adde="">
          {"S"}
        </span>
        <span data-sp-57e2adde="">
          <strong data-sp-57e2adde="">
            {"SmartProp AI Advisor"}
          </strong>
          <small data-sp-57e2adde="">
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.preview || "Bắt đầu từ nhu cầu của bạn")}
          </small>
        </span>
      </button>
      <div className="panel-prompts" data-sp-57e2adde="">
        <h2 data-sp-57e2adde="">
          {"Gợi ý bắt đầu"}
        </h2>
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.prompts, prompt => <button key={prompt.label} type="button" disabled={view.locked} onClick={$event => {
          view.onChoose?.(prompt.text);
        }} data-sp-57e2adde="">
            <AppIcon name="messages" data-sp-57e2adde="" />
            <span data-sp-57e2adde="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(prompt.label)}
            </span>
            <AppIcon name="arrow" data-sp-57e2adde="" />
          </button>)}
      </div>
      <SiteLink to="/advisor" className="filter-link" data-sp-57e2adde="">
        {"Tìm bằng bộ lọc "}
        <AppIcon name="arrow" data-sp-57e2adde="" />
      </SiteLink>
    </div></>;
});
