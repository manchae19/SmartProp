import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "./rendering.js";
import { RouterLink, RouterView } from "../routing/router.jsx";
import AppIcon from "./AppIcon.jsx";
import "./ChatSessionPanel.css";
function setup(__props) {
  propsForSetup(__props, {
    preview: String,
    locked: Boolean,
  });
  const emit = emitForProps(__props, ["choose", "current"]);
  const prompts = [
    {
      label: "Tìm nhà theo ngân sách",
      text: "Tôi có 10 tỷ, gợi ý bất động sản phù hợp và giải thích điểm đề xuất.",
    },
    {
      label: "Khám phá tiện ích khu vực",
      text: "Ở Hải Châu có những bệnh viện nào?",
    },
    {
      label: "Kiểm tra lựa chọn dưới 2 tỷ",
      text: "Tôi có 2 tỷ, có bất động sản công khai phù hợp không?",
    },
  ];
  return {
    AppIcon,
    emit,
    prompts,
  };
}
export default React.forwardRef(function ChatSessionPanel(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="ChatSessionPanel"
      {...mergeProps({
        className: "session-panel",
        "data-sp-57e2adde": "",
      })}
    >
      <p
        {...mergeProps({
          className: "panel-eyebrow",
          "data-sp-57e2adde": "",
        })}
      >
        {"TRONG TAB NÀY"}
      </p>
      <button
        {...mergeProps({
          className: "current-conversation",
          type: "button",
          "aria-current": "true",
          onClick: ($event) => {
            ctx.emit("current");
          },
          "data-sp-57e2adde": "",
        })}
      >
        <span
          {...mergeProps({
            className: "session-avatar",
            "aria-hidden": "true",
            "data-sp-57e2adde": "",
          })}
        >
          {"S"}
        </span>
        <span
          {...mergeProps({
            "data-sp-57e2adde": "",
          })}
        >
          <strong
            {...mergeProps({
              "data-sp-57e2adde": "",
            })}
          >
            {"SmartProp AI Advisor"}
          </strong>
          <small
            {...mergeProps({
              "data-sp-57e2adde": "",
            })}
          >
            {display(ctx.preview || "Bắt đầu từ nhu cầu của bạn")}
          </small>
        </span>
      </button>
      <div
        {...mergeProps({
          className: "panel-prompts",
          "data-sp-57e2adde": "",
        })}
      >
        <h2
          {...mergeProps({
            "data-sp-57e2adde": "",
          })}
        >
          {"Gợi ý bắt đầu"}
        </h2>
        {renderList(ctx.prompts, (prompt) => (
          <button
            key={prompt.label}
            {...mergeProps({
              type: "button",
              disabled: ctx.locked,
              onClick: ($event) => {
                ctx.emit("choose", prompt.text);
              },
              "data-sp-57e2adde": "",
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "messages",
                "data-sp-57e2adde": "",
              })}
            />
            <span
              {...mergeProps({
                "data-sp-57e2adde": "",
              })}
            >
              {display(prompt.label)}
            </span>
            <AppIcon
              {...mergeProps({
                name: "arrow",
                "data-sp-57e2adde": "",
              })}
            />
          </button>
        ))}
      </div>
      <RouterLink
        {...mergeProps({
          to: "/advisor",
          className: "filter-link",
          "data-sp-57e2adde": "",
        })}
      >
        {"Tìm bằng bộ lọc "}
        <AppIcon
          {...mergeProps({
            name: "arrow",
            "data-sp-57e2adde": "",
          })}
        />
      </RouterLink>
    </div>,
  ]);
});
