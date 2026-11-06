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
import { computed } from "../state/store.js";
import "./AmenityEvidence.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    evidence: {
      type: Object,
      default: null,
    },
    compact: {
      type: Boolean,
      default: false,
    },
    area: {
      type: Boolean,
      default: false,
    },
  });
  const num = (value) =>
    Number.isFinite(value)
      ? new Intl.NumberFormat("vi-VN", {
          maximumFractionDigits: 1,
        }).format(value)
      : null;
  const categories = computed(() => {
    const scores = props.evidence?.categoryScores;
    if (!scores) return [];
    return [
      {
        key: "essentials",
        icon: "🛒",
        label: "Chợ & siêu thị",
        score: scores.essentials,
      },
      {
        key: "education",
        icon: "🎓",
        label: "Trường học",
        score: scores.education,
      },
      {
        key: "healthcare",
        icon: "🏥",
        label: "Y tế",
        score: scores.healthcare,
      },
      {
        key: "transit",
        icon: "🚌",
        label: "Giao thông công cộng",
        score: scores.transit,
      },
      {
        key: "recreation",
        icon: "🌳",
        label: "Công viên & biển",
        score: scores.recreation,
      },
    ].filter((c) => Number.isFinite(c.score));
  });
  const basisLabel = computed(
    () =>
      ({
        DIRECT_WARD_EVIDENCE: "Theo đúng phường/xã của bất động sản",
        DISTRICT_SHARED_AMENITY: "Theo quận/huyện (tiện ích dùng chung)",
        NO_AREA_MATCH: "Chưa xác định được địa bàn",
      })[props.evidence?.evidenceBasis] || "Chưa xác định",
  );
  const hasProfile = computed(
    () => props.evidence != null && props.evidence.areaAmenityScore != null,
  );
  const visibleEvidence = computed(() =>
    (props.evidence?.poiEvidence || []).slice(0, props.compact ? 4 : 8),
  );
  return {
    computed,
    props,
    num,
    categories,
    basisLabel,
    hasProfile,
    visibleEvidence,
  };
}
export default React.forwardRef(function AmenityEvidence(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        className: ["amenity-evidence", {
          compact: ctx.compact,
          "area-mode": ctx.area,
        }],
        
        "data-amenity-evidence": "",
        "data-sp-8b7e0c1f": "",
      })}
    >
      <header
        {...mergeProps({
          className: "ae-head",
          "data-sp-8b7e0c1f": "",
        })}
      >
        <div
          {...mergeProps({
            "data-sp-8b7e0c1f": "",
          })}
        >
          <p
            {...mergeProps({
              className: "ae-eyebrow",
              "data-sp-8b7e0c1f": "",
            })}
          >
            {display(
              ctx.area ? "TIỆN ÍCH KHU VỰC" : "TIỆN ÍCH KHU VỰC SINH SỐNG",
            )}
          </p>
          {ctx.hasProfile ? (
            <h4
              {...mergeProps({
                "data-sp-8b7e0c1f": "",
              })}
            >
              {display(ctx.num(ctx.evidence.areaAmenityScore))}
              <small
                {...mergeProps({
                  "data-sp-8b7e0c1f": "",
                })}
              >
                {"/100"}
              </small>{" "}
              <span
                {...mergeProps({
                  className: "ae-name",
                  "data-sp-8b7e0c1f": "",
                })}
              >
                {display(ctx.evidence.areaName)}
              </span>
            </h4>
          ) : (
            <h4
              {...mergeProps({
                className: "ae-na",
                "data-sp-8b7e0c1f": "",
              })}
            >
              {"Chưa có điểm tiện ích"}
            </h4>
          )}
        </div>
        {ctx.hasProfile && Number.isFinite(ctx.evidence.confidence) ? (
          <span
            {...mergeProps({
              className: "ae-confidence",
              title: ctx.basisLabel,
              "data-sp-8b7e0c1f": "",
            })}
          >
            {"Tin cậy "}
            {display(Math.round(ctx.evidence.confidence * 100))}
            {"%"}
          </span>
        ) : null}
      </header>
      <p
        {...mergeProps({
          className: "ae-basis",
          "data-sp-8b7e0c1f": "",
        })}
      >
        {display(ctx.basisLabel)}
        {" · "}
        {display(
          ctx.evidence.areaLevel === "WARD"
            ? "cấp phường/xã"
            : ctx.evidence.areaLevel === "DISTRICT"
              ? "cấp quận/huyện"
              : "không xác định",
        )}
      </p>
      {ctx.categories.length ? (
        <ul
          {...mergeProps({
            className: "ae-bars",
            "data-sp-8b7e0c1f": "",
          })}
        >
          {renderList(ctx.categories, (c) => (
            <li
              key={c.key}
              {...mergeProps({
                "data-sp-8b7e0c1f": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "ae-label",
                  "data-sp-8b7e0c1f": "",
                })}
              >
                <span
                  {...mergeProps({
                    "aria-hidden": "true",
                    "data-sp-8b7e0c1f": "",
                  })}
                >
                  {display(c.icon)}
                </span>{" "}
                {display(c.label)}
              </span>
              <span
                {...mergeProps({
                  className: "ae-track",
                  role: "meter",
                  "aria-label": c.label,
                  "aria-valuemin": "0",
                  "aria-valuemax": "100",
                  "aria-valuenow": c.score,
                  "data-sp-8b7e0c1f": "",
                })}
              >
                <span
                  {...mergeProps({
                    style: {
                      width: c.score + "%",
                    },
                    "data-sp-8b7e0c1f": "",
                  })}
                />
              </span>
              <span
                {...mergeProps({
                  className: "ae-value",
                  "data-sp-8b7e0c1f": "",
                })}
              >
                {display(ctx.num(c.score))}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      {ctx.visibleEvidence.length ? (
        <div
          {...mergeProps({
            className: "ae-pois",
            "data-sp-8b7e0c1f": "",
          })}
        >
          <p
            {...mergeProps({
              className: "ae-pois-title",
              "data-sp-8b7e0c1f": "",
            })}
          >
            {"Tiện ích đã số hóa trong khu vực"}
          </p>
          <ul
            {...mergeProps({
              "data-sp-8b7e0c1f": "",
            })}
          >
            {renderList(ctx.visibleEvidence, (poi) => (
              <li
                key={poi.name + poi.category}
                {...mergeProps({
                  "data-sp-8b7e0c1f": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "ae-poi-name",
                    "data-sp-8b7e0c1f": "",
                  })}
                >
                  {display(poi.name)}
                </span>
                <span
                  {...mergeProps({
                    className: "ae-poi-cat",
                    "data-sp-8b7e0c1f": "",
                  })}
                >
                  {display(poi.category)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : ctx.hasProfile ? (
        <p
          {...mergeProps({
            className: "ae-note",
            "data-sp-8b7e0c1f": "",
          })}
        >
          {"Hồ sơ khu vực không kèm tên tiện ích cụ thể."}
        </p>
      ) : null}
      {renderList(
        (ctx.evidence?.dataLimitations || []).slice(0, ctx.compact ? 1 : 3),
        (limitation) => (
          <p
            key={limitation}
            {...mergeProps({
              className: "ae-note",
              "data-sp-8b7e0c1f": "",
            })}
          >
            {display(limitation)}
          </p>
        ),
      )}
      {ctx.hasProfile ? (
        <p
          {...mergeProps({
            className: "ae-note ae-note-strong",
            "data-sp-8b7e0c1f": "",
          })}
        >
          {display(ctx.evidence.note)}
        </p>
      ) : null}
    </section>,
  ]);
});
