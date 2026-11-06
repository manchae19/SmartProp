import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import {
  ref,
  computed,
  onBeforeUnmount,
  nextTick,
  watch,
} from "../../shared/state/store.js";
import LeafletNearbyMap from "./LeafletNearbyMap.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import ContactPanel from "../property/ContactPanel.jsx";
import { publicMapPoint, locationLabel } from "./locationDisplay.js";
import {
  compactPrice,
  price,
  types,
  displayDecimal,
} from "../property/property.js";
import {
  POI_GROUPS,
  DEFAULT_GROUPS,
  RADII,
  filteredPlaces,
  distanceLabel,
} from "./nearbyExplorer.js";
import { useNearbyPlaces } from "./useNearbyPlaces.js";
import "./PropertyExplorer.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    items: {
      type: Array,
      default: () => [],
    },
    selectedId: String,
    allowNearby: {
      type: Boolean,
      default: true,
    },
    compact: Boolean,
    preview: Boolean,
    exploreLink: Object,
  });
  const emit = emitForProps(__props, ["select"]);
  const radius = ref(1000),
    groups = ref([...DEFAULT_GROUPS]),
    showProperty = ref(true),
    showRadius = ref(!props.preview),
    activePoi = ref(null),
    expanded = ref(false),
    panel = ref(null),
    expandButton = ref(null);
  const property = computed(
    () => props.items.find((p) => p.id === props.selectedId) || null,
  );
  const origin = computed(() =>
    publicMapPoint(property.value) ? property.value : null,
  );
  const nearby = useNearbyPlaces(
    () => origin.value,
    () => radius.value,
    () => groups.value,
    () => props.allowNearby,
  );
  const places = computed(() =>
    filteredPlaces(
      nearby.data.value?.items,
      origin.value,
      radius.value,
      groups.value,
    ),
  );
  const featuredPlaces = computed(() =>
    props.preview ? places.value.slice(0, 4) : places.value,
  );
  const image = computed(
    () =>
      property.value?.images?.find((i) => i.cover || i.isCover)?.url ||
      property.value?.images?.[0]?.url ||
      property.value?.coverImageUrl ||
      "",
  );
  const groupLabel = (id) =>
    POI_GROUPS.find((g) => g.id === id)?.label || "Tiện ích";
  let previousOverflow = "",
    previousFocus;
  async function toggleExpanded() {
    expanded.value = !expanded.value;
    if (expanded.value) {
      previousOverflow = document.body.style.overflow;
      previousFocus = document.activeElement;
      document.body.style.overflow = "hidden";
      await nextTick();
      panel.value?.focus();
    } else {
      document.body.style.overflow = previousOverflow;
      await nextTick();
      previousFocus?.focus();
    }
  }
  function keyboard(e) {
    if (e.key === "Escape" && expanded.value) {
      e.preventDefault();
      toggleExpanded();
    }
    if (e.key !== "Tab" || !expanded.value) return;
    const elements = [
      ...panel.value.querySelectorAll(
        'button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),[tabindex="0"]',
      ),
    ].filter((el) => el.getClientRects().length);
    const first = elements[0],
      last = elements.at(-1);
    if (
      e.shiftKey &&
      (document.activeElement === first ||
        document.activeElement === panel.value)
    ) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first?.focus();
    }
  }
  watch(
    () => props.selectedId,
    () => {
      activePoi.value = null;
    },
  );
  onBeforeUnmount(() => {
    if (expanded.value) document.body.style.overflow = previousOverflow;
  });
  return {
    ref,
    computed,
    onBeforeUnmount,
    nextTick,
    watch,
    LeafletNearbyMap,
    PrivateImage,
    ContactPanel,
    publicMapPoint,
    locationLabel,
    compactPrice,
    price,
    types,
    displayDecimal,
    POI_GROUPS,
    DEFAULT_GROUPS,
    RADII,
    filteredPlaces,
    distanceLabel,
    useNearbyPlaces,
    props,
    emit,
    radius,
    groups,
    showProperty,
    showRadius,
    activePoi,
    expanded,
    panel,
    expandButton,
    property,
    origin,
    nearby,
    places,
    featuredPlaces,
    image,
    groupLabel,
    previousOverflow,
    previousFocus,
    toggleExpanded,
    keyboard,
  };
}
export default React.forwardRef(function PropertyExplorer(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <Teleport
      {...mergeProps({
        to: "body",
        disabled: !ctx.expanded,
        "data-sp-c46b683d": "",
      })}
    >
      <section
        {...mergeProps({
          ref: bindRef(ctx, "panel"),
          tabIndex: "-1",
          className: ["property-explorer", {
            "is-expanded": ctx.expanded,
            "is-compact": ctx.compact,
            "is-preview": ctx.preview,
          }],
          
          role: ctx.expanded ? "dialog" : undefined,
          "aria-modal": ctx.expanded ? "true" : undefined,
          "aria-label": "Bản đồ và tiện ích bất động sản",
          onKeyDown: ($event) => {
            return ctx.keyboard?.($event);
          },
          "data-sp-c46b683d": "",
        })}
      >
        <aside
          {...mergeProps({
            className: "explorer-sidebar",
            "data-sp-c46b683d": "",
          })}
        >
          {!ctx.preview ? (
            <RouterLink
              {...mergeProps({
                to: "/listings",
                className: "explorer-back",
                "data-sp-c46b683d": "",
              })}
            >
              {"← Quay lại kết quả tìm kiếm"}
            </RouterLink>
          ) : null}
          {ctx.items.length > 1 ? (
            <div
              {...mergeProps({
                className: "explorer-picker",
                "data-sp-c46b683d": "",
              })}
            >
              <label
                {...mergeProps({
                  htmlFor: "explorer-property",
                  "data-sp-c46b683d": "",
                })}
              >
                {"Tin đăng đang xem"}
              </label>
              <select
                {...mergeProps({
                  id: "explorer-property",
                  value: ctx.selectedId || "",
                  onChange: ($event) => {
                    ctx.emit("select", $event.target.value);
                  },
                  "data-sp-c46b683d": "",
                })}
              >
                <option
                  {...mergeProps({
                    value: "",
                    disabled: true,
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Chọn tin đăng"}
                </option>
                {renderList(ctx.items, (p) => (
                  <option
                    key={p.id}
                    {...mergeProps({
                      value: p.id,
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {display(p.title)}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          {ctx.property ? (
            <React.Fragment {...mergeProps({})}>
              <h2
                {...mergeProps({
                  "data-sp-c46b683d": "",
                })}
              >
                {display(ctx.property.title)}
              </h2>
              <div
                {...mergeProps({
                  className: "explorer-price",
                  title: ctx.price(ctx.property),
                  "data-sp-c46b683d": "",
                })}
              >
                {display(ctx.compactPrice(ctx.property))}
              </div>
              {!ctx.preview ? (
                <details
                  {...mergeProps({
                    className: "explorer-exact",
                    "data-sp-c46b683d": "",
                  })}
                >
                  <summary
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {"Giá đầy đủ"}
                  </summary>
                  {display(ctx.price(ctx.property))}
                </details>
              ) : null}
              <div
                {...mergeProps({
                  className: "explorer-photo",
                  "data-sp-c46b683d": "",
                })}
              >
                <PrivateImage
                  key={ctx.property.id}
                  {...mergeProps({
                    src: ctx.image,
                    alt: ctx.property.title,
                    "data-sp-c46b683d": "",
                  })}
                />
              </div>
              <div
                {...mergeProps({
                  className: "explorer-facts",
                  "data-sp-c46b683d": "",
                })}
              >
                <div
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  <strong
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {display(ctx.displayDecimal(ctx.property.areaSqm))}
                    {" m²"}
                  </strong>
                  <span
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {"Diện tích"}
                  </span>
                </div>
                <div
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  <strong
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {display(ctx.types[ctx.property.propertyType] || "Chưa rõ")}
                  </strong>
                  <span
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {"Loại hình"}
                  </span>
                </div>
                {ctx.property.bedrooms != null ? (
                  <div
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    <strong
                      {...mergeProps({
                        "data-sp-c46b683d": "",
                      })}
                    >
                      {display(ctx.property.bedrooms)}
                    </strong>
                    <span
                      {...mergeProps({
                        "data-sp-c46b683d": "",
                      })}
                    >
                      {"Phòng ngủ"}
                    </span>
                  </div>
                ) : null}
              </div>
              <h3
                {...mergeProps({
                  "data-sp-c46b683d": "",
                })}
              >
                {display(
                  ctx.preview ? "Tiện ích nổi bật" : "Vị trí & khoảng cách",
                )}
              </h3>
              {!ctx.preview ? (
                <p
                  {...mergeProps({
                    className: "explorer-address",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"⌖ "}
                  {display(
                    [
                      ctx.property.address,
                      ctx.property.ward,
                      ctx.property.district,
                      ctx.property.city,
                    ]
                      .filter(Boolean)
                      .join(", ") || "Chưa có địa chỉ công bố",
                  )}
                </p>
              ) : null}
              {!ctx.preview ? (
                <p
                  {...mergeProps({
                    className: "explorer-location-note",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {display(ctx.locationLabel(ctx.property))}
                </p>
              ) : null}
              {!ctx.origin ? (
                <p
                  {...mergeProps({
                    className: "explorer-notice",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {
                    "Tin chưa có vị trí công khai phù hợp. Không đặt ghim thay thế."
                  }
                </p>
              ) : !ctx.allowNearby ? (
                <p
                  {...mergeProps({
                    className: "explorer-notice",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Tiện ích chỉ được truy vấn cho tin đang công khai."}
                </p>
              ) : null}
              {ctx.nearby.busy.value ? (
                <p
                  {...mergeProps({
                    role: "status",
                    className: "explorer-notice",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Đang tìm tiện ích trong "}
                  {display(ctx.distanceLabel(ctx.radius))}
                  {"…"}
                </p>
              ) : null}
              {ctx.nearby.error.value ? (
                <div
                  {...mergeProps({
                    role: "alert",
                    className: "explorer-warning",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {display(ctx.nearby.error.value)}{" "}
                  <button
                    {...mergeProps({
                      type: "button",
                      onClick: ($event) => {
                        return ctx.nearby.retry?.($event);
                      },
                      "data-sp-c46b683d": "",
                    })}
                  >
                    {"Thử lại"}
                  </button>
                </div>
              ) : ctx.origin &&
                ctx.allowNearby &&
                !ctx.nearby.busy.value &&
                ctx.groups.length &&
                ctx.nearby.data.value &&
                !ctx.places.length ? (
                <p
                  {...mergeProps({
                    className: "explorer-notice",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Chưa tìm thấy tiện ích phù hợp trong phạm vi đã chọn."}
                </p>
              ) : null}
              {!ctx.groups.length ? (
                <p
                  {...mergeProps({
                    className: "explorer-notice",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Bật một nhóm tiện ích để tìm quanh tin đăng."}
                </p>
              ) : null}
              <ol
                {...mergeProps({
                  className: "explorer-pois",
                  "data-sp-c46b683d": "",
                })}
              >
                {renderList(ctx.featuredPlaces, (p) => (
                  <li
                    key={p.id}
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    <button
                      {...mergeProps({
                        type: "button",
                        className: {
                          active: ctx.activePoi === p.id,
                        },
                        onClick: ($event) => {
                          ctx.activePoi = p.id;
                        },
                        "data-sp-c46b683d": "",
                      })}
                    >
                      <span
                        {...mergeProps({
                          className: "poi-dot",
                          style: {
                            background: ctx.POI_GROUPS.find(
                              (g) => g.id === p.category,
                            )?.color,
                          },
                          "data-sp-c46b683d": "",
                        })}
                      >
                        {display(
                          ctx.POI_GROUPS.find((g) => g.id === p.category)?.icon,
                        )}
                      </span>
                      <span
                        {...mergeProps({
                          "data-sp-c46b683d": "",
                        })}
                      >
                        <strong
                          {...mergeProps({
                            "data-sp-c46b683d": "",
                          })}
                        >
                          {display(p.name)}
                        </strong>
                        <small
                          {...mergeProps({
                            "data-sp-c46b683d": "",
                          })}
                        >
                          {display(ctx.groupLabel(p.category))}
                        </small>
                      </span>
                      {!ctx.preview ? (
                        <b
                          {...mergeProps({
                            "data-sp-c46b683d": "",
                          })}
                        >
                          {display(ctx.distanceLabel(p.distanceMeters))}
                        </b>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ol>
              {!ctx.preview && ctx.nearby.data.value ? (
                <p
                  {...mergeProps({
                    className: "explorer-source",
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Đường chim bay · "}
                  {display(ctx.places.length)}
                  {" tiện ích · Dữ liệu có thể chưa đầy đủ"}
                  {display(
                    ctx.nearby.data.value.truncated
                      ? " (đã giới hạn kết quả)"
                      : "",
                  )}
                  {"."}
                  <br
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  />
                  {"Cập nhật truy vấn: "}
                  {display(
                    new Date(ctx.nearby.data.value.fetchedAt).toLocaleString(
                      "vi-VN",
                    ),
                  )}
                  {display(
                    ctx.nearby.data.value.cacheHit ? " · Bộ nhớ đệm" : "",
                  )}
                </p>
              ) : null}
              <RouterLink
                {...mergeProps({
                  to: "/listing/" + ctx.property.id,
                  className: "explorer-detail",
                  "data-sp-c46b683d": "",
                })}
              >
                {"Xem chi tiết tin →"}
              </RouterLink>
              {ctx.allowNearby && !ctx.preview ? (
                <ContactPanel
                  {...mergeProps({
                    propertyId: ctx.property.id,
                    "data-sp-c46b683d": "",
                  })}
                />
              ) : null}
            </React.Fragment>
          ) : (
            <p
              {...mergeProps({
                className: "explorer-notice",
                "data-sp-c46b683d": "",
              })}
            >
              {"Chọn một tin đăng có tọa độ để khám phá tiện ích xung quanh."}
            </p>
          )}
        </aside>
        <div
          {...mergeProps({
            className: "explorer-map-column",
            "data-sp-c46b683d": "",
          })}
        >
          <header
            {...mergeProps({
              className: "explorer-map-toolbar",
              "data-sp-c46b683d": "",
            })}
          >
            <div
              {...mergeProps({
                "data-sp-c46b683d": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "gis-dot",
                  "data-sp-c46b683d": "",
                })}
              />
              <strong
                {...mergeProps({
                  "data-sp-c46b683d": "",
                })}
              >
                {display(
                  ctx.preview ? "Khám phá không gian sống" : "GIS Explorer",
                )}
              </strong>
              <span
                {...mergeProps({
                  className: "explorer-subtitle",
                  "data-sp-c46b683d": "",
                })}
              >
                {display(
                  ctx.preview
                    ? "Chạm vào ghim để xem tin đăng"
                    : "Bất động sản & tiện ích quanh bạn",
                )}
              </span>
            </div>
            {ctx.preview ? (
              <RouterLink
                {...mergeProps({
                  to: ctx.exploreLink || {
                    path: "/map",
                    query: ctx.selectedId
                      ? {
                          propertyId: ctx.selectedId,
                        }
                      : {},
                  },
                  className: "explorer-launch",
                  "data-sp-c46b683d": "",
                })}
              >
                {"Khám phá GIS đầy đủ ↗"}
              </RouterLink>
            ) : (
              <button
                {...mergeProps({
                  ref: bindRef(ctx, "expandButton"),
                  type: "button",
                  onClick: ($event) => {
                    return ctx.toggleExpanded?.($event);
                  },
                  "aria-expanded": ctx.expanded,
                  "data-sp-c46b683d": "",
                })}
              >
                {display(ctx.expanded ? "✕ Thu nhỏ" : "⛶ Mở rộng")}
              </button>
            )}
          </header>
          <div
            {...mergeProps({
              className: "explorer-map-content",
              "data-sp-c46b683d": "",
            })}
          >
            <LeafletNearbyMap
              {...mergeProps({
                simple: ctx.preview,
                items: ctx.items,
                selectedId: ctx.origin?.id,
                places: ctx.featuredPlaces,
                radius: ctx.radius,
                showProperty: ctx.showProperty,
                showRadius: ctx.showRadius,
                activePoi: ctx.activePoi,
                onSelect: ($event) => {
                  ctx.emit("select", $event);
                },
                onSelectPoi: ($event) => {
                  ctx.activePoi = $event;
                },
                "data-sp-c46b683d": "",
              })}
            />
            {!ctx.preview ? (
              <div
                {...mergeProps({
                  className: "explorer-layers",
                  "data-sp-c46b683d": "",
                })}
              >
                <h3
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Lớp hiển thị"}
                </h3>
                <label
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  <input
                    {...mergeProps(
                      {
                        type: "checkbox",
                        "data-sp-c46b683d": "",
                      },
                      modelProps(
                        ctx.showProperty,
                        ($value) => {
                          ctx.showProperty = $value;
                        },
                        {
                          kind: "checkbox",
                          value: "on",
                          number: false,
                          multiple: false,
                        },
                      ),
                    )}
                  />
                  {" Bất động sản"}
                </label>
                {renderList(ctx.POI_GROUPS, (group) => (
                  <label
                    key={group.id}
                    {...mergeProps({
                      "data-sp-c46b683d": "",
                    })}
                  >
                    <input
                      {...mergeProps(
                        {
                          value: group.id,
                          "aria-label": group.label,
                          type: "checkbox",
                          "data-sp-c46b683d": "",
                        },
                        modelProps(
                          ctx.groups,
                          ($value) => {
                            ctx.groups = $value;
                          },
                          {
                            kind: "checkbox",
                            value: group.id,
                            number: false,
                            multiple: false,
                          },
                        ),
                      )}
                    />
                    <span
                      {...mergeProps({
                        "aria-hidden": "true",
                        style: {
                          color: group.color,
                        },
                        "data-sp-c46b683d": "",
                      })}
                    >
                      {display(group.icon)}
                    </span>{" "}
                    {display(group.label)}
                  </label>
                ))}
                <label
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  <input
                    {...mergeProps(
                      {
                        type: "checkbox",
                        "data-sp-c46b683d": "",
                      },
                      modelProps(
                        ctx.showRadius,
                        ($value) => {
                          ctx.showRadius = $value;
                        },
                        {
                          kind: "checkbox",
                          value: "on",
                          number: false,
                          multiple: false,
                        },
                      ),
                    )}
                  />
                  {" Vùng tìm tiện ích"}
                </label>
              </div>
            ) : null}
            {!ctx.preview ? (
              <div
                {...mergeProps({
                  className: "explorer-radius",
                  "data-sp-c46b683d": "",
                })}
              >
                <label
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  {"Bán kính tìm kiếm "}
                  <select
                    {...mergeProps(
                      {
                        "aria-label": "Bán kính tìm tiện ích",
                        "data-sp-c46b683d": "",
                      },
                      modelProps(
                        ctx.radius,
                        ($value) => {
                          ctx.radius = $value;
                        },
                        {
                          kind: "text",
                          value: "on",
                          number: true,
                          multiple: false,
                        },
                      ),
                    )}
                  >
                    {renderList(ctx.RADII, (r) => (
                      <option
                        key={r}
                        {...mergeProps({
                          value: r,
                          "data-sp-c46b683d": "",
                        })}
                      >
                        {display(ctx.distanceLabel(r))}
                      </option>
                    ))}
                  </select>
                </label>
                <small
                  {...mergeProps({
                    "data-sp-c46b683d": "",
                  })}
                >
                  {
                    "Vòng tròn tìm kiếm, không phải ranh giới hay sai số vị trí."
                  }
                </small>
              </div>
            ) : null}
          </div>
          <footer
            {...mergeProps({
              className: "explorer-credits",
              "data-sp-c46b683d": "",
            })}
          >
            <a
              {...mergeProps({
                href: "https://www.openstreetmap.org/copyright",
                target: "_blank",
                rel: "noopener noreferrer",
                "data-sp-c46b683d": "",
              })}
            >
              {"© OpenStreetMap contributors"}
            </a>
            <span
              {...mergeProps({
                "data-sp-c46b683d": "",
              })}
            >
              {" · "}
            </span>
            <a
              {...mergeProps({
                href: "https://www.geoapify.com/",
                target: "_blank",
                rel: "noopener noreferrer",
                "data-sp-c46b683d": "",
              })}
            >
              {"Powered by Geoapify"}
            </a>
            {!ctx.preview ? (
              <span
                {...mergeProps({
                  "data-sp-c46b683d": "",
                })}
              >
                {
                  " · Khoảng cách đường chim bay, không phải quãng đường di chuyển."
                }
              </span>
            ) : null}
          </footer>
        </div>
      </section>
    </Teleport>,
  ]);
});
