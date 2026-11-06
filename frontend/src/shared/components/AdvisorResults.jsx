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
import { computed, nextTick, ref } from "../state/store.js";
import BrowseTileMap from "../../features/map/BrowseTileMap.jsx";
import AmenityEvidence from "./AmenityEvidence.jsx";
import {
  advisorListingUrl,
  advisorWarning,
} from "../../features/prediction/advisor.js";
import "./AdvisorResults.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    result: {
      type: Object,
      required: true,
    },
    points: {
      type: Array,
      default: () => [],
    },
    selectedId: String,
    mapBusy: Boolean,
    mapFailures: Number,
  });
  const emit = emitForProps(__props, ["select", "area", "adjust", "retry-map"]);
  const cards = new Map(),
    mapHost = ref(null);
  const located = computed(() => new Set(props.points.map((p) => p.id)));
  const pointById = computed(() => new Map(props.points.map((p) => [p.id, p])));
  const isResearch = computed(() => props.result.mode === "INTERNAL_DEMO");
  const isV11 = computed(() => props.result.method === "HEURISTIC_V1_1");
  const breakdownLabels = {
    budgetFit: "Ngân sách",
    areaFit: "Diện tích",
    propertyTypeFit: "Loại BĐS",
    amenityFit: "Tiện ích khu vực",
  };
  const typeLabel = (type) =>
    ({
      HOUSE: "Nhà ở",
      APARTMENT: "Căn hộ",
      LAND: "Đất",
      VILLA: "Biệt thự/nhà liền kề",
    })[type] || type;
  const money = (value) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
      maximumFractionDigits: 0,
    }).format(value);
  const score = (value) =>
    new Intl.NumberFormat("vi-VN", {
      maximumFractionDigits: 1,
    }).format(value);
  const scrollBehavior = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "instant"
      : "smooth";
  async function selectFromMap(id) {
    emit("select", id);
    await nextTick();
    cards.get(id)?.scrollIntoView({
      behavior: scrollBehavior(),
      block: "center",
    });
    cards.get(id)?.focus({
      preventScroll: true,
    });
  }
  async function selectFromCard(id) {
    emit("select", id);
    await nextTick();
    mapHost.value?.scrollIntoView({
      behavior: scrollBehavior(),
      block: "center",
    });
    mapHost.value?.querySelector('[role="region"]')?.focus({
      preventScroll: true,
    });
  }
  return {
    computed,
    nextTick,
    ref,
    BrowseTileMap,
    AmenityEvidence,
    advisorListingUrl,
    advisorWarning,
    props,
    emit,
    cards,
    mapHost,
    located,
    pointById,
    isResearch,
    isV11,
    breakdownLabels,
    typeLabel,
    money,
    score,
    scrollBehavior,
    selectFromMap,
    selectFromCard,
  };
}
export default React.forwardRef(function AdvisorResults(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "advisor-output",
        "data-sp-c098318d": "",
      })}
    >
      <div
        {...mergeProps({
          className: "section-heading",
          "data-sp-c098318d": "",
        })}
      >
        <div
          {...mergeProps({
            "data-sp-c098318d": "",
          })}
        >
          <p
            {...mergeProps({
              className: "eyebrow",
              "data-sp-c098318d": "",
            })}
          >
            {"TOP KHU VỰC"}
          </p>
          <h2
            {...mergeProps({
              "data-sp-c098318d": "",
            })}
          >
            {"Khu vực phù hợp với nhu cầu"}
          </h2>
        </div>
        <p
          {...mergeProps({
            "data-sp-c098318d": "",
          })}
        >
          {"Tối đa 5 khu vực · "}
          {display(ctx.result.eligibleCandidateCount)}
          {" ứng viên đủ điều kiện"}
        </p>
      </div>
      {ctx.result.topAreas.length ? (
        <div
          {...mergeProps({
            className: "area-grid",
            "data-sp-c098318d": "",
          })}
        >
          {renderList(ctx.result.topAreas, (area, i) => (
            <article
              key={area.district + ":" + area.ward}
              {...mergeProps({
                className: "area-card",
                "data-advisor-area": "",
                "data-sp-c098318d": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "area-top",
                  "data-sp-c098318d": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "rank",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(String(i + 1).padStart(2, "0"))}
                </span>
                <span
                  {...mergeProps({
                    className: "area-score",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(ctx.score(area.score))}
                  {"/100"}
                </span>
              </div>
              <h3
                {...mergeProps({
                  "data-sp-c098318d": "",
                })}
              >
                {display(area.district)}
                {area.ward ? (
                  <span
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {" · "}
                    {display(area.ward)}
                  </span>
                ) : null}
              </h3>
              <p
                {...mergeProps({
                  "data-sp-c098318d": "",
                })}
              >
                {display(area.candidateCount)}
                {" tin đủ điều kiện · Giá rao bình quân "}
                <strong
                  {...mergeProps({
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(ctx.money(area.averageAskingPriceVnd))}
                </strong>
              </p>
              {area.amenityScore != null ? (
                <p
                  {...mergeProps({
                    className: "area-amenity",
                    "data-area-amenity": "",
                    "data-sp-c098318d": "",
                  })}
                >
                  {"Tiện ích khu vực "}
                  <strong
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(ctx.score(area.amenityScore))}
                    {"/100"}
                  </strong>
                  {area.amenityConfidence != null ? (
                    <span
                      {...mergeProps({
                        "data-sp-c098318d": "",
                      })}
                    >
                      {" · tin cậy "}
                      {display(Math.round(area.amenityConfidence * 100))}
                      {"%"}
                    </span>
                  ) : null}
                  <span
                    {...mergeProps({
                      className: "area-amenity-basis",
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(
                      area.amenityEvidenceBasis === "DIRECT_WARD_EVIDENCE"
                        ? "cấp phường/xã"
                        : "cấp quận/huyện",
                    )}
                  </span>
                </p>
              ) : ctx.isV11 ? (
                <p
                  {...mergeProps({
                    className: "area-amenity muted",
                    "data-area-amenity-missing": "",
                    "data-sp-c098318d": "",
                  })}
                >
                  {"Chưa có hồ sơ tiện ích cho khu vực này."}
                </p>
              ) : null}
              {area.poiEvidence?.length ? (
                <ul
                  {...mergeProps({
                    className: "area-pois",
                    "data-sp-c098318d": "",
                  })}
                >
                  {renderList(area.poiEvidence, (poi) => (
                    <li
                      key={poi.name + poi.category}
                      {...mergeProps({
                        "data-sp-c098318d": "",
                      })}
                    >
                      {display(poi.name)}{" "}
                      <span
                        {...mergeProps({
                          "data-sp-c098318d": "",
                        })}
                      >
                        {display(poi.category)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              <ul
                {...mergeProps({
                  "data-sp-c098318d": "",
                })}
              >
                {renderList(area.explanations, (reason) => (
                  <li
                    key={reason}
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(reason)}
                  </li>
                ))}
              </ul>
              <p
                {...mergeProps({
                  className: "source",
                  "data-sp-c098318d": "",
                })}
              >
                {"Nguồn: "}
                {display(area.sources.join(", "))}
              </p>
              {renderList(area.warnings, (warning) => (
                <p
                  key={warning}
                  {...mergeProps({
                    className: "quality-note",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(ctx.advisorWarning(warning))}
                </p>
              ))}
              <button
                {...mergeProps({
                  type: "button",
                  className: "text-action",
                  onClick: ($event) => {
                    ctx.emit("area", area);
                  },
                  "data-sp-c098318d": "",
                })}
              >
                {"Tìm trong khu vực này "}
                <span
                  {...mergeProps({
                    "aria-hidden": "true",
                    "data-sp-c098318d": "",
                  })}
                >
                  {"→"}
                </span>
              </button>
            </article>
          ))}
        </div>
      ) : ctx.result.topProperties.length ? (
        <p
          {...mergeProps({
            className: "muted",
            "data-sp-c098318d": "",
          })}
        >
          {
            "Chưa đủ thông tin để xếp hạng khu vực. Bạn vẫn có thể xem các tin phù hợp bên dưới."
          }
        </p>
      ) : null}
      {!ctx.result.topProperties.length ? (
        <div
          {...mergeProps({
            className: "advisor-empty",
            role: "status",
            "data-advisor-empty": "",
            "data-sp-c098318d": "",
          })}
        >
          <span
            {...mergeProps({
              className: "empty-icon",
              "aria-hidden": "true",
              "data-sp-c098318d": "",
            })}
          >
            {"⌕"}
          </span>
          <h3
            {...mergeProps({
              "data-sp-c098318d": "",
            })}
          >
            {display(
              ctx.isResearch
                ? "Chưa có bản ghi nghiên cứu phù hợp"
                : "Chưa có gợi ý công khai phù hợp",
            )}
          </h3>
          <p
            {...mergeProps({
              "data-sp-c098318d": "",
            })}
          >
            {
              "Có thể chưa có tin khớp bộ lọc hoặc nguồn chưa đủ điều kiện công khai. Thử tăng ngân sách, giảm diện tích tối thiểu hoặc bỏ lọc khu vực."
            }
          </p>
          <p
            {...mergeProps({
              "data-sp-c098318d": "",
            })}
          >
            {
              "Tin chưa xác minh không được đưa vào kết quả để lấp đầy danh sách."
            }
          </p>
          <button
            {...mergeProps({
              type: "button",
              className: "sp-button sp-button-secondary",
              onClick: ($event) => {
                ctx.emit("adjust");
              },
              "data-sp-c098318d": "",
            })}
          >
            {"Điều chỉnh bộ lọc"}
          </button>
        </div>
      ) : null}
      <div
        {...mergeProps({
          className: "result-grid",
          "data-sp-c098318d": "",
        })}
      >
        <section
          {...mergeProps({
            "aria-labelledby": "property-title",
            "data-sp-c098318d": "",
          })}
        >
          <div
            {...mergeProps({
              className: "section-heading",
              "data-sp-c098318d": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-c098318d": "",
              })}
            >
              <p
                {...mergeProps({
                  className: "eyebrow",
                  "data-sp-c098318d": "",
                })}
              >
                {"TOP BẤT ĐỘNG SẢN"}
              </p>
              <h2
                {...mergeProps({
                  id: "property-title",
                  "data-sp-c098318d": "",
                })}
              >
                {display(ctx.result.topProperties.length)}
                {" tin được đề xuất"}
              </h2>
            </div>
          </div>
          {!ctx.result.topProperties.length ? (
            <p
              {...mergeProps({
                className: "muted",
                "data-sp-c098318d": "",
              })}
            >
              {"Kết quả sẽ xuất hiện tại đây khi có tin phù hợp."}
            </p>
          ) : null}
          {renderList(ctx.result.topProperties, (property) => (
            <article
              key={property.id}
              {...mergeProps({
                ref: (el) =>
                  el
                    ? ctx.cards.set(property.id, el)
                    : ctx.cards.delete(property.id),
                tabIndex: "-1",
                className: ["property-card", {
                  selected: ctx.selectedId === property.id,
                }],
                
                "data-advisor-property": property.id,
                "data-sp-c098318d": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "property-top",
                  "data-sp-c098318d": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "source-badge",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(
                    property.source.kind === "TINIX_AI"
                      ? "Dữ liệu nghiên cứu TiniX AI — chưa xác minh"
                      : property.source.kind === "PROPERTY"
                        ? "Tin công khai SmartProp"
                        : "Nguồn đã xác minh",
                  )}
                </span>
                <span
                  {...mergeProps({
                    className: "fit-score",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(ctx.score(property.score))}
                  <small
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {"/100"}
                  </small>
                </span>
              </div>
              {property.source.kind === "TINIX_AI" ? (
                <p
                  {...mergeProps({
                    className: "source",
                    "data-sp-c098318d": "",
                  })}
                >
                  {"ID nội bộ: "}
                  {display(property.source.recordKey)}
                  {" · "}
                  {display(ctx.typeLabel(property.propertyType))}
                  {" · Lịch sử, chưa biết còn bán"}
                </p>
              ) : null}
              <p
                {...mergeProps({
                  className: "score-label",
                  "data-sp-c098318d": "",
                })}
              >
                {"Điểm phù hợp theo nhu cầu"}
              </p>
              <div
                {...mergeProps({
                  className: "score-track",
                  role: "meter",
                  "aria-label": "Điểm phù hợp: " + property.title,
                  "aria-valuemin": "0",
                  "aria-valuemax": "100",
                  "aria-valuenow": property.score,
                  "data-sp-c098318d": "",
                })}
              >
                <span
                  {...mergeProps({
                    style: {
                      width: property.score + "%",
                    },
                    "data-sp-c098318d": "",
                  })}
                />
              </div>
              {ctx.isV11 && property.scoreBreakdown ? (
                <ul
                  {...mergeProps({
                    className: "breakdown",
                    "data-score-breakdown": "",
                    "data-sp-c098318d": "",
                  })}
                >
                  {renderList(property.scoreBreakdown, (value, key) => (
                    <li
                      key={key}
                      {...mergeProps(
                        {
                          "data-sp-c098318d": "",
                        },
                        {
                          style: {
                            display: ctx.breakdownLabels[key]
                              ? undefined
                              : "none",
                          },
                        },
                      )}
                    >
                      <span
                        {...mergeProps({
                          "data-sp-c098318d": "",
                        })}
                      >
                        {display(ctx.breakdownLabels[key])}
                      </span>
                      <strong
                        {...mergeProps({
                          "data-sp-c098318d": "",
                        })}
                      >
                        {display(ctx.score(value))}
                      </strong>
                    </li>
                  ))}
                </ul>
              ) : null}
              <h3
                {...mergeProps({
                  "data-sp-c098318d": "",
                })}
              >
                {ctx.advisorListingUrl(property) ? (
                  <a
                    {...mergeProps({
                      href: ctx.advisorListingUrl(property),
                      target:
                        property.source.kind === "EXTERNAL"
                          ? "_blank"
                          : undefined,
                      rel: "noopener noreferrer",
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(property.title)}
                    {property.source.kind === "EXTERNAL" ? (
                      <span
                        {...mergeProps({
                          className: "sr-only",
                          "data-sp-c098318d": "",
                        })}
                      >
                        {" (mở nguồn trong thẻ mới)"}
                      </span>
                    ) : null}
                  </a>
                ) : (
                  <span
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(property.title)}
                  </span>
                )}
              </h3>
              <p
                {...mergeProps({
                  className: "price",
                  "data-sp-c098318d": "",
                })}
              >
                {display(ctx.money(property.priceVnd))}{" "}
                <span
                  {...mergeProps({
                    "data-sp-c098318d": "",
                  })}
                >
                  {"· "}
                  {display(property.areaSqm.toLocaleString("vi-VN"))}
                  {" m²"}
                </span>
              </p>
              <p
                {...mergeProps({
                  className: "location",
                  "data-sp-c098318d": "",
                })}
              >
                {display(property.district || "Chưa có địa bàn")}
                {property.ward ? (
                  <span
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {" · "}
                    {display(property.ward)}
                  </span>
                ) : null}
              </p>
              {ctx.pointById.get(property.id)?.locationLabel ? (
                <p
                  {...mergeProps({
                    className: "source",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(ctx.pointById.get(property.id).locationLabel)}
                </p>
              ) : null}
              {ctx.isV11 && property.amenityEvidence ? (
                <AmenityEvidence
                  {...mergeProps({
                    evidence: property.amenityEvidence,
                    compact: true,
                    "data-sp-c098318d": "",
                  })}
                />
              ) : null}
              <h4
                {...mergeProps({
                  "data-sp-c098318d": "",
                })}
              >
                {"Vì sao phù hợp?"}
              </h4>
              <ul
                {...mergeProps({
                  "data-sp-c098318d": "",
                })}
              >
                {renderList(property.explanations, (reason) => (
                  <li
                    key={reason}
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(reason)}
                  </li>
                ))}
              </ul>
              {renderList(property.warnings, (warning) => (
                <p
                  key={warning}
                  {...mergeProps({
                    className: "quality-note",
                    "data-sp-c098318d": "",
                  })}
                >
                  {display(ctx.advisorWarning(warning))}
                </p>
              ))}
              <div
                {...mergeProps({
                  className: "property-footer",
                  "data-sp-c098318d": "",
                })}
              >
                <span
                  {...mergeProps({
                    "data-sp-c098318d": "",
                  })}
                >
                  {"Nguồn: "}
                  <strong
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(property.source.name)}
                  </strong>
                </span>
                {ctx.located.has(property.id) ? (
                  <button
                    {...mergeProps({
                      type: "button",
                      className: "text-action",
                      "aria-pressed": ctx.selectedId === property.id,
                      onClick: ($event) => {
                        ctx.selectFromCard(property.id);
                      },
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(
                      ctx.selectedId === property.id
                        ? "Đang chọn trên bản đồ"
                        : "Xem trên bản đồ",
                    )}
                  </button>
                ) : (
                  <span
                    {...mergeProps({
                      "data-sp-c098318d": "",
                    })}
                  >
                    {display(
                      ctx.mapBusy
                        ? "Đang tải vị trí…"
                        : "Chưa có tọa độ công khai",
                    )}
                  </span>
                )}
              </div>
            </article>
          ))}
        </section>
        <aside
          {...mergeProps({
            ref: bindRef(ctx, "mapHost"),
            className: "gis",
            "aria-labelledby": "advisor-map-title",
            "data-sp-c098318d": "",
          })}
        >
          <p
            {...mergeProps({
              className: "eyebrow",
              "data-sp-c098318d": "",
            })}
          >
            {"BẢN ĐỒ GIS"}
          </p>
          <h2
            {...mergeProps({
              id: "advisor-map-title",
              "data-sp-c098318d": "",
            })}
          >
            {"Danh sách và vị trí cùng một nơi"}
          </h2>
          <p
            {...mergeProps({
              role: "status",
              "data-sp-c098318d": "",
            })}
          >
            {display(
              ctx.mapBusy
                ? "Đang tải vị trí công khai…"
                : ctx.points.length +
                    "/" +
                    ctx.result.topProperties.length +
                    " tin có tọa độ công khai hợp lệ.",
            )}
          </p>
          <div
            {...mergeProps({
              className: "advisor-map",
              "aria-busy": ctx.mapBusy,
              "data-sp-c098318d": "",
            })}
          >
            <BrowseTileMap
              {...mergeProps({
                points: ctx.points,
                selectedId: ctx.selectedId,
                onSelect: ($event) => {
                  return ctx.selectFromMap?.($event);
                },
                "data-sp-c098318d": "",
              })}
            />
          </div>
          {ctx.mapFailures ? (
            <p
              {...mergeProps({
                className: "map-warning",
                role: "status",
                "data-sp-c098318d": "",
              })}
            >
              {"Chưa tải được một số vị trí. Danh sách gợi ý vẫn dùng được. "}
              <button
                {...mergeProps({
                  type: "button",
                  className: "text-action",
                  disabled: ctx.mapBusy,
                  onClick: ($event) => {
                    ctx.emit("retry-map");
                  },
                  "data-sp-c098318d": "",
                })}
              >
                {"Tải lại vị trí"}
              </button>
            </p>
          ) : null}
          <p
            {...mergeProps({
              className: "map-note",
              "data-sp-c098318d": "",
            })}
          >
            {
              "Chọn ghim để tìm thẻ tin tương ứng; chọn “Xem trên bản đồ” để định vị tin. Chỉ đặt ghim từ tọa độ công khai của chính bất động sản; không dùng tâm khu vực thay thế."
            }
          </p>
        </aside>
      </div>
      <details
        {...mergeProps({
          className: "result-notes",
          "data-sp-c098318d": "",
        })}
      >
        <summary
          {...mergeProps({
            "data-sp-c098318d": "",
          })}
        >
          {"Cách hiểu kết quả và giới hạn dữ liệu"}
        </summary>
        {renderList(ctx.result.warnings, (warning) => (
          <p
            key={warning}
            {...mergeProps({
              "data-sp-c098318d": "",
            })}
          >
            {display(ctx.advisorWarning(warning))}
          </p>
        ))}
        <p
          {...mergeProps({
            "data-sp-c098318d": "",
          })}
        >
          {
            "Điểm phù hợp không phải độ chính xác định giá. Giá hiển thị là tổng giá rao bán; hãy kiểm tra nguồn và tình trạng bất động sản trước khi quyết định."
          }
        </p>
      </details>
    </div>,
  ]);
});
