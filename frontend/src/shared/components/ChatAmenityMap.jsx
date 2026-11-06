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
import { computed, ref, nextTick } from "../state/store.js";
import BrowseTileMap from "../../features/map/BrowseTileMap.jsx";
import PoiIcon from "./PoiIcon.jsx";
import { amenityCategories } from "../../features/prediction/chatAmenities.js";
import { poiColor } from "../../features/map/nearbyPlaces.js";
import "./ChatAmenityMap.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    data: Object,
    status: String,
    message: String,
  });
  const emit = emitForProps(__props, ["retry", "reading"]);
  const selected = ref(null),
    expanded = ref(false),
    host = ref(null);
  const items = computed(() => props.data?.items || []);
  const points = computed(() =>
    items.value.map((p) => ({
      ...p,
      categoryLabel: amenityCategories[p.category],
    })),
  );
  const cards = computed(() =>
    expanded.value ? items.value : items.value.slice(0, 6),
  );
  const categories = computed(() => [
    ...new Set(items.value.map((p) => p.category)),
  ]);
  function select(id) {
    selected.value = id;
    emit("reading");
    // In a conversation the map may be partly above the reading viewport. Bring
    // the actual map (not just a focused pin) into view so its popup stays readable.
    if (id)
      nextTick(() =>
        host.value?.querySelector(".browse-map")?.scrollIntoView({
          block: "center",
          inline: "nearest",
        }),
      );
  }
  return {
    computed,
    ref,
    nextTick,
    BrowseTileMap,
    PoiIcon,
    amenityCategories,
    poiColor,
    props,
    emit,
    selected,
    expanded,
    host,
    items,
    points,
    cards,
    categories,
    select,
  };
}
export default React.forwardRef(function ChatAmenityMap(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        ref: bindRef(ctx, "host"),
        className: "chat-amenity",
        "data-chat-amenities": "",
        "aria-label": "Tiện ích trên bản đồ",
        "data-sp-6a8bc544": "",
      })}
    >
      {ctx.status === "loading" ? (
        <p
          {...mergeProps({
            className: "map-state",
            role: "status",
            "data-amenity-loading": "",
            "data-sp-6a8bc544": "",
          })}
        >
          {"Đang tìm tiện ích trên bản đồ…"}
        </p>
      ) : ctx.status === "error" ? (
        <p
          {...mergeProps({
            className: "map-state map-error",
            role: "status",
            "data-amenity-error": "",
            "data-sp-6a8bc544": "",
          })}
        >
          {
            "Chưa tải được bản đồ tiện ích. Câu trả lời phía trên vẫn được giữ. "
          }
          <button
            {...mergeProps({
              type: "button",
              onClick: ($event) => {
                ctx.emit("retry");
              },
              "data-sp-6a8bc544": "",
            })}
          >
            {"Thử lại bản đồ"}
          </button>
        </p>
      ) : ctx.items.length || ctx.data?.boundary ? (
        <React.Fragment {...mergeProps({})}>
          <div
            {...mergeProps({
              className: "amenity-map-card",
              "data-chat-map": "",
              "data-sp-6a8bc544": "",
            })}
          >
            <div
              {...mergeProps({
                className: "map-heading",
                "data-sp-6a8bc544": "",
              })}
            >
              <h3
                {...mergeProps({
                  "data-sp-6a8bc544": "",
                })}
              >
                {"Tiện ích · "}
                {display(ctx.data.district)}
              </h3>
              <span
                {...mergeProps({
                  "data-sp-6a8bc544": "",
                })}
              >
                {display(
                  ctx.items.length
                    ? ctx.items.length + " địa điểm"
                    : "Ranh giới khu vực",
                )}
              </span>
            </div>
            <BrowseTileMap
              {...mergeProps({
                className: "chat-poi-map",
                poiItems: ctx.points,
                boundary: ctx.data.boundary?.geometry,
                selectedPoiId: ctx.selected,
                mapLabel:
                  "Bản đồ tiện ích: kéo để di chuyển, phím mũi tên và cộng trừ để điều khiển",
                onSelectPoi: ($event) => {
                  return ctx.select?.($event);
                },
                "data-sp-6a8bc544": "",
              })}
            />
            {!ctx.items.length ? (
              <p
                {...mergeProps({
                  className: "map-note",
                  "data-amenity-area-only": "",
                  "data-sp-6a8bc544": "",
                })}
              >
                {
                  "Chỉ có ranh giới khu vực lịch sử. Chưa có tọa độ tiện ích đủ điều kiện cho yêu cầu này; không đặt ghim ước lượng."
                }
              </p>
            ) : null}
            <div
              {...mergeProps({
                className: "map-legend",
                "aria-label": "Loại tiện ích",
                "data-sp-6a8bc544": "",
              })}
            >
              {renderList(ctx.categories, (cat) => (
                <span
                  key={cat}
                  {...mergeProps({
                    "data-sp-6a8bc544": "",
                  })}
                >
                  <i
                    {...mergeProps({
                      style: {
                        background: ctx.poiColor(cat),
                      },
                      "aria-hidden": "true",
                      "data-sp-6a8bc544": "",
                    })}
                  />
                  {display(ctx.amenityCategories[cat])}
                </span>
              ))}
            </div>
            <p
              {...mergeProps({
                className: "map-note",
                "data-sp-6a8bc544": "",
              })}
            >
              {
                "Điểm theo dữ liệu OpenStreetMap, chưa xác minh thực địa. Ghim vùng đại diện cho đối tượng bản đồ, không phải cổng vào. Không xác định khoảng cách tới căn nhà."
              }
            </p>
            {ctx.data.truncated ? (
              <p
                {...mergeProps({
                  className: "map-note",
                  "data-sp-6a8bc544": "",
                })}
              >
                {
                  "Đang hiển thị một phần địa điểm, tối đa 8 mỗi loại khi xem nhiều loại tiện ích."
                }
              </p>
            ) : null}
          </div>
          <div
            {...mergeProps({
              className: "amenity-cards",
              "data-amenity-cards": "",
              "data-sp-6a8bc544": "",
            })}
          >
            {renderList(ctx.cards, (p) => (
              <article
                key={p.id}
                {...mergeProps({
                  "data-amenity-card": p.id,
                  className: {
                    active: ctx.selected === p.id,
                  },
                  "data-sp-6a8bc544": "",
                })}
              >
                <button
                  {...mergeProps({
                    type: "button",
                    className: "amenity-select",
                    onClick: ($event) => {
                      ctx.select(p.id);
                    },
                    "data-sp-6a8bc544": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "amenity-icon",
                      style: {
                        color: ctx.poiColor(p.category),
                      },
                      "data-sp-6a8bc544": "",
                    })}
                  >
                    <PoiIcon
                      {...mergeProps({
                        category: p.category,
                        "data-sp-6a8bc544": "",
                      })}
                    />
                  </span>
                  <span
                    {...mergeProps({
                      "data-sp-6a8bc544": "",
                    })}
                  >
                    <strong
                      {...mergeProps({
                        "data-sp-6a8bc544": "",
                      })}
                    >
                      {display(p.name)}
                    </strong>
                    <small
                      {...mergeProps({
                        "data-sp-6a8bc544": "",
                      })}
                    >
                      {display(ctx.amenityCategories[p.category])}
                      {" · "}
                      {display(p.district)}
                    </small>
                  </span>
                </button>
                <div
                  {...mergeProps({
                    className: "amenity-source",
                    "data-sp-6a8bc544": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      "data-sp-6a8bc544": "",
                    })}
                  >
                    {display(
                      p.coordinateBasis === "OSM_NODE"
                        ? "Điểm ghi trong OSM"
                        : "Điểm đại diện đối tượng OSM",
                    )}
                  </span>
                  <a
                    {...mergeProps({
                      href: p.sourceUrl,
                      target: "_blank",
                      rel: "noopener noreferrer",
                      "data-sp-6a8bc544": "",
                    })}
                  >
                    {"Nguồn OSM ↗"}
                  </a>
                </div>
              </article>
            ))}
          </div>
          {ctx.items.length > 6 ? (
            <button
              {...mergeProps({
                type: "button",
                className: "more-amenities",
                "aria-expanded": ctx.expanded,
                onClick: ($event) => {
                  ctx.expanded = !ctx.expanded;
                  ctx.emit("reading");
                },
                "data-sp-6a8bc544": "",
              })}
            >
              {display(
                ctx.expanded
                  ? "Thu gọn tiện ích"
                  : "Xem tất cả " + ctx.items.length + " tiện ích",
              )}
            </button>
          ) : null}
          <details
            {...mergeProps({
              className: "map-provenance",
              onToggle: ($event) => {
                return ((event) => event.target.open && ctx.emit("reading"))?.(
                  $event,
                );
              },
              "data-sp-6a8bc544": "",
            })}
          >
            <summary
              {...mergeProps({
                "data-sp-6a8bc544": "",
              })}
            >
              {"Nguồn bản đồ ("}
              {display(ctx.items.length || 1)}
              {")"}
            </summary>
            {ctx.items.length ? (
              <p
                {...mergeProps({
                  "data-sp-6a8bc544": "",
                })}
              >
                {display(ctx.items[0].attribution)}
                {" · "}
                {display(ctx.items[0].sourceLicense)}
              </p>
            ) : null}
            {ctx.data.boundary ? (
              <p
                {...mergeProps({
                  "data-sp-6a8bc544": "",
                })}
              >
                <a
                  {...mergeProps({
                    href: ctx.data.boundary.sourceUrl,
                    target: "_blank",
                    rel: "noopener noreferrer",
                    "data-sp-6a8bc544": "",
                  })}
                >
                  {"Ranh giới lịch sử · "}
                  {display(ctx.data.boundary.attribution)}
                  {" · "}
                  {display(ctx.data.boundary.license)}
                </a>
              </p>
            ) : null}
            {renderList(ctx.data.dataLimitations, (line) => (
              <p
                key={line}
                {...mergeProps({
                  "data-sp-6a8bc544": "",
                })}
              >
                {display(line)}
              </p>
            ))}
          </details>
        </React.Fragment>
      ) : (
        <p
          {...mergeProps({
            className: "map-state",
            "data-amenity-empty": "",
            "data-sp-6a8bc544": "",
          })}
        >
          {display(
            ctx.message ||
              "Chưa có tọa độ tiện ích đủ điều kiện hiển thị; không đặt ghim ước lượng trên bản đồ.",
          )}
        </p>
      )}
    </section>,
  ]);
});
