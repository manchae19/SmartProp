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
import {
  computed,
  ref,
  onMounted,
  onBeforeUnmount,
  nextTick,
} from "../state/store.js";
import { chatPresentation } from "../../features/prediction/chatPresentation.js";
import {
  amenityIntent,
  loadAmenityMap,
  amenitySummary,
} from "../../features/prediction/chatAmenities.js";
import ChatAmenityMap from "./ChatAmenityMap.jsx";
import AppIcon from "./AppIcon.jsx";
import "./ChatAnswer.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    result: {
      type: Object,
      required: true,
    },
    messageId: {
      type: Number,
      required: true,
    },
    question: {
      type: String,
      default: "",
    },
  });
  const emit = emitForProps(__props, ["reading", "resized"]);
  const expanded = ref(false);
  const view = computed(() => chatPresentation(props.result));
  const intent = computed(() => amenityIntent(props.question, props.result));
  const mapData = ref(null),
    mapStatus = ref("idle");
  const summary = computed(() =>
    intent.value.requested && mapData.value
      ? amenitySummary(mapData.value)
      : view.value.summary,
  );
  let disposed = false;
  async function loadMap() {
    if (!intent.value.enabled || mapStatus.value === "loading") return;
    mapStatus.value = "loading";
    try {
      const data = await loadAmenityMap(intent.value);
      if (!disposed) {
        mapData.value = data;
        mapStatus.value = "ready";
      }
    } catch {
      if (!disposed) mapStatus.value = "error";
    }
    if (!disposed) {
      await nextTick();
      emit("resized");
    }
  }
  onMounted(loadMap);
  onBeforeUnmount(() => {
    disposed = true;
  });
  const visibleCards = computed(() =>
    expanded.value ? view.value.cards : view.value.cards.slice(0, 3),
  );
  function expand() {
    emit("reading");
    expanded.value = !expanded.value;
  }
  function reading(event) {
    if (event.target.open) emit("reading");
  }
  return {
    computed,
    ref,
    onMounted,
    onBeforeUnmount,
    nextTick,
    chatPresentation,
    amenityIntent,
    loadAmenityMap,
    amenitySummary,
    ChatAmenityMap,
    AppIcon,
    props,
    emit,
    expanded,
    view,
    intent,
    mapData,
    mapStatus,
    summary,
    disposed,
    loadMap,
    visibleCards,
    expand,
    reading,
  };
}
export default React.forwardRef(function ChatAnswer(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "chat-answer",
        "data-chat-answer": "",
        "data-generation-mode": ctx.result.generationMode,
        "data-sp-73584f77": "",
      })}
    >
      <div
        {...mergeProps({
          className: "ai-bubble",
          "data-chat-empty":
            !ctx.view.cards.length &&
            !ctx.view.clarification &&
            ctx.result.evidence.criteria?.budgetVnd
              ? ""
              : undefined,
          "data-sp-73584f77": "",
        })}
      >
        <p
          {...mergeProps({
            className: "ai-summary",
            "data-chat-summary": "",
            "data-sp-73584f77": "",
          })}
        >
          {display(ctx.summary)}
        </p>
        {ctx.view.clarification ? (
          <p
            {...mergeProps({
              className: "clarification-note",
              role: "status",
              "data-chat-clarification": "",
              "data-sp-73584f77": "",
            })}
          >
            {display(ctx.view.clarification)}
          </p>
        ) : null}
        {ctx.view.fallback ? (
          <p
            {...mergeProps({
              className: "fallback-note",
              role: "status",
              "data-chat-fallback": "",
              "data-sp-73584f77": "",
            })}
          >
            {
              "Kết quả tham khảo từ dữ liệu hiện có."
            }
          </p>
        ) : null}
        {ctx.view.noMatches ? (
          <p
            {...mergeProps({
              className: "empty-followup",
              "data-sp-73584f77": "",
            })}
          >
            {
              "Hãy nhắc lại ngân sách, loại BĐS và địa bàn trong câu hỏi tiếp theo. "
            }
            <RouterLink
              {...mergeProps({
                to: "/advisor",
                "data-sp-73584f77": "",
              })}
            >
              {"Mở bộ lọc"}
            </RouterLink>
          </p>
        ) : null}
        <p
          {...mergeProps({
            className: "answer-basis",
            "data-sp-73584f77": "",
          })}
        >
          {display(
            ctx.view.clarification
              ? "Cần bạn xác nhận trước khi tra cứu"
              : ctx.view.noMatches
                ? "Kết quả tra cứu dữ liệu công khai"
                : "Tổng hợp từ nguồn công khai · mở Nguồn để đối chiếu",
          )}
        </p>
      </div>
      {ctx.intent.enabled || ctx.intent.requested ? (
        <ChatAmenityMap
          {...mergeProps({
            data: ctx.mapData,
            status: ctx.mapStatus,
            message: ctx.intent.message,
            onRetry: ($event) => {
              return ctx.loadMap?.($event);
            },
            onReading: ($event) => {
              ctx.emit("reading");
            },
            "data-sp-73584f77": "",
          })}
        />
      ) : null}
      {ctx.view.cards.length ? (
        <section
          {...mergeProps({
            className: "chat-properties",
            "aria-label":
              "Bất động sản đề xuất trong phản hồi " + ctx.messageId,
            "data-chat-properties": "",
            "data-sp-73584f77": "",
          })}
        >
          {renderList(ctx.visibleCards, (card, index) => (
            <article
              key={card.id}
              {...mergeProps({
                className: "chat-property",
                "data-chat-property": card.id,
                "data-sp-73584f77": "",
              })}
            >
              {card.imageUrl ? (
                <img
                  {...mergeProps({
                    src: card.imageUrl,
                    alt: "",
                    loading: "lazy",
                    className: "chat-property-image",
                    "data-chat-image": "",
                    "data-sp-73584f77": "",
                  })}
                />
              ) : null}
              <div
                {...mergeProps({
                  className: "card-heading",
                  "data-sp-73584f77": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "card-rank",
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(String(index + 1).padStart(2, "0"))}
                </span>
                <p
                  {...mergeProps({
                    className: "card-location",
                    "data-sp-73584f77": "",
                  })}
                >
                  <AppIcon
                    {...mergeProps({
                      name: "gis",
                      "data-sp-73584f77": "",
                    })}
                  />
                  {display(card.location)}
                </p>
              </div>
              <h3
                {...mergeProps({
                  "data-sp-73584f77": "",
                })}
              >
                {display(card.title)}
              </h3>
              {card.listingCode ? (
                <p className="card-listing-code" data-chat-listing-code="">
                  {"Mã tin: "}{display(card.listingCode)}
                </p>
              ) : null}
              {card.description ? (
                <p className="card-description" data-chat-description="">
                  {display(card.description)}
                </p>
              ) : null}
              {card.project ? (
                <p className="card-project" data-chat-project="">
                  {"Dự án: "}{display(card.project.name)}
                  {card.project.developer ? " · " + display(card.project.developer) : ""}
                </p>
              ) : null}
              {card.legal ? (
                <p className="card-legal" data-chat-legal="">
                  {card.legal.verified > 0
                    ? "Hồ sơ pháp lý đã duyệt: " + display(String(card.legal.verified)) + ". Chỉ là trạng thái duyệt hồ sơ, không thay thế kiểm tra pháp lý."
                    : card.legal.pending > 0
                      ? "Hồ sơ pháp lý đang chờ duyệt: " + display(String(card.legal.pending)) + "; chưa được coi là đã xác minh."
                      : "Chưa có hồ sơ pháp lý công khai; thông tin người dùng khai báo không được coi là đã xác minh."}
                </p>
              ) : null}
              <div
                {...mergeProps({
                  className: "card-facts",
                  "data-sp-73584f77": "",
                })}
              >
                <p
                  {...mergeProps({
                    className: "card-price",
                    title: card.price.exact,
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(card.price.text)}
                </p>
                <span
                  {...mergeProps({
                    "aria-hidden": "true",
                    "data-sp-73584f77": "",
                  })}
                >
                  {"·"}
                </span>
                <p
                  {...mergeProps({
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(card.area)}
                  {" m²"}
                </p>
              </div>
              {card.distanceMeters !== null && card.distanceMeters !== undefined ? (
                <p
                  {...mergeProps({
                    className: "card-distance",
                    "data-chat-distance": "",
                    "data-sp-73584f77": "",
                  })}
                >
                  {"Cách vị trí đã xác nhận "}
                  {Math.round(card.distanceMeters)}
                  {" m (đường chim bay)"}
                </p>
              ) : null}
              {card.reasons?.length ? (
                <ul
                  {...mergeProps({
                    className: "card-reasons",
                    "data-chat-reasons": "",
                    "data-sp-73584f77": "",
                  })}
                >
                  {renderList(card.reasons, (reason, index) => (
                    <li key={index} {...mergeProps({ "data-sp-73584f77": "" })}>
                      {display(reason)}
                    </li>
                  ))}
                </ul>
              ) : card.reason ? (
                <p
                  {...mergeProps({
                    className: "card-reason",
                    title: card.reason,
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(card.reason)}
                </p>
              ) : null}
              {card.nearbyPois?.length ? (
                <div
                  {...mergeProps({
                    className: "card-pois",
                    "data-chat-pois": "",
                    "data-sp-73584f77": "",
                  })}
                >
                  <strong>{"Tiện ích gần nhất"}</strong>
                  <ul>
                    {renderList(card.nearbyPois, (poi, index) => (
                      <li key={index} {...mergeProps({ "data-sp-73584f77": "" })}>
                        {display(poi.name)}
                        {" · "}
                        {display(poi.label)}
                        {" · "}
                        {display(poi.distance)}
                      </li>
                    ))}
                  </ul>
                  <small>{display(card.nearbyPoisNote)}</small>
                </div>
              ) : card.nearbyPoisStatus && card.nearbyPoisStatus !== "NOT_APPLICABLE" ? (
                <p
                  {...mergeProps({
                    className: "card-poi-note",
                    "data-chat-poi-status": card.nearbyPoisStatus,
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(card.nearbyPoisNote)}
                </p>
              ) : null}
              <div
                {...mergeProps({
                  className: "card-footer",
                  "data-sp-73584f77": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "card-score",
                    "data-sp-73584f77": "",
                  })}
                >
                  <strong
                    {...mergeProps({
                      "data-sp-73584f77": "",
                    })}
                  >
                    {display(card.score)}
                  </strong>
                  {"/100 "}
                  <span
                    {...mergeProps({
                      "data-sp-73584f77": "",
                    })}
                  >
                    {"phù hợp"}
                  </span>
                </span>
                {card.href && card.platform ? (
                  <RouterLink
                    {...mergeProps({
                      to: card.href,
                      className: "card-link",
                      "data-sp-73584f77": "",
                    })}
                  >
                    {"Xem chi tiết "}
                    <AppIcon
                      {...mergeProps({
                        name: "arrow",
                        "data-sp-73584f77": "",
                      })}
                    />
                  </RouterLink>
                ) : card.href ? (
                  <a
                    {...mergeProps({
                      href: card.href,
                      target: "_blank",
                      rel: "noopener noreferrer",
                      className: "card-link",
                      "data-sp-73584f77": "",
                    })}
                  >
                    {"Xem chi tiết "}
                    <AppIcon
                      {...mergeProps({
                        name: "arrow",
                        "data-sp-73584f77": "",
                      })}
                    />
                  </a>
                ) : (
                  <span
                    {...mergeProps({
                      className: "no-link",
                      "data-sp-73584f77": "",
                    })}
                  >
                    {"Chưa có đường dẫn nguồn"}
                  </span>
                )}
              </div>
              {card.warnings.length ? (
                <p
                  {...mergeProps({
                    className: "quality-note",
                    "data-sp-73584f77": "",
                  })}
                >
                  {"Thông tin nguồn cần được đối chiếu trước khi quyết định."}
                </p>
              ) : null}
            </article>
          ))}
          {ctx.view.cards.length > 3 ? (
            <button
              {...mergeProps({
                type: "button",
                className: "expand-properties",
                "aria-expanded": ctx.expanded,
                onClick: ($event) => {
                  return ctx.expand?.($event);
                },
                "data-chat-expand": "",
                "data-sp-73584f77": "",
              })}
            >
              {display(
                ctx.expanded
                  ? "Thu gọn danh sách"
                  : "Xem tất cả " + ctx.view.cards.length + " bất động sản",
              )}
              <svg
                {...mergeProps({
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "1.7",
                  "aria-hidden": "true",
                  className: {
                    rotated: ctx.expanded,
                  },
                  "data-sp-73584f77": "",
                })}
              >
                <path
                  {...mergeProps({
                    d: "m6 9 6 6 6-6",
                    "data-sp-73584f77": "",
                  })}
                />
              </svg>
            </button>
          ) : null}
        </section>
      ) : null}
      {ctx.view.citations.length ? (
        <details
          {...mergeProps({
            className: "citation-panel",
            "data-chat-sources": "",
            onToggle: ($event) => {
              return ctx.reading?.($event);
            },
            "data-sp-73584f77": "",
          })}
        >
          <summary
            {...mergeProps({
              "data-sp-73584f77": "",
            })}
          >
            <AppIcon
              {...mergeProps({
                name: "report",
                "data-sp-73584f77": "",
              })}
            />
            <span
              {...mergeProps({
                "data-sp-73584f77": "",
              })}
            >
              {"Nguồn ("}
              {display(ctx.view.citations.length)}
              {")"}
            </span>
            <svg
              {...mergeProps({
                viewBox: "0 0 24 24",
                fill: "none",
                stroke: "currentColor",
                strokeWidth: "1.7",
                "aria-hidden": "true",
                className: "source-chevron",
                "data-sp-73584f77": "",
              })}
            >
              <path
                {...mergeProps({
                  d: "m6 9 6 6 6-6",
                  "data-sp-73584f77": "",
                })}
              />
            </svg>
          </summary>
          <ol
            {...mergeProps({
              className: "source-list",
              "data-sp-73584f77": "",
            })}
          >
            {renderList(ctx.view.citations, (source) => (
              <li
                key={source.sourceId}
                {...mergeProps({
                  "data-sp-73584f77": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "source-number",
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(source.number)}
                </span>
                <div
                  {...mergeProps({
                    className: "source-body",
                    "data-sp-73584f77": "",
                  })}
                >
                  <a
                    {...mergeProps({
                      href: source.href,
                      target: "_blank",
                      rel: "noopener noreferrer",
                      "data-chat-citation": "",
                      "data-sp-73584f77": "",
                    })}
                  >
                    {display(source.label)}
                  </a>
                  <p
                    {...mergeProps({
                      "data-sp-73584f77": "",
                    })}
                  >
                    {display(source.basis)}
                  </p>
                  <details
                    {...mergeProps({
                      className: "technical-source",
                      onToggle: ($event) => {
                        return ctx.reading?.($event);
                      },
                      "data-sp-73584f77": "",
                    })}
                  >
                    <summary
                      {...mergeProps({
                        "data-sp-73584f77": "",
                      })}
                    >
                      {"Thông tin đối chiếu"}
                    </summary>
                    <dl
                      {...mergeProps({
                        "data-sp-73584f77": "",
                      })}
                    >
                      <dt
                        {...mergeProps({
                          "data-sp-73584f77": "",
                        })}
                      >
                        {"Nguồn"}
                      </dt>
                      <dd
                        {...mergeProps({
                          "data-sp-73584f77": "",
                        })}
                      >
                        {display(source.sourceId)}
                      </dd>
                      <dt
                        {...mergeProps({
                          "data-sp-73584f77": "",
                        })}
                      >
                        {"Phiên bản"}
                      </dt>
                      <dd
                        {...mergeProps({
                          "data-sp-73584f77": "",
                        })}
                      >
                        {display(source.version)}
                      </dd>
                      <dt
                        {...mergeProps({
                          "data-sp-73584f77": "",
                        })}
                      >
                        {"SHA-256"}
                      </dt>
                      <dd
                        {...mergeProps({
                          "data-sp-73584f77": "",
                        })}
                      >
                        {display(source.contentHash)}
                      </dd>
                    </dl>
                  </details>
                </div>
              </li>
            ))}
          </ol>
          <details
            {...mergeProps({
              className: "original-evidence",
              onToggle: ($event) => {
                return ctx.reading?.($event);
              },
              "data-sp-73584f77": "",
            })}
          >
            <summary
              {...mergeProps({
                "data-sp-73584f77": "",
              })}
            >
              {display(
                ctx.view.generated
                  ? "Xem câu trả lời đầy đủ"
                  : "Xem nội dung đầy đủ",
              )}
            </summary>
            <p
              {...mergeProps({
                className: "original-answer",
                "data-chat-original": "",
                "data-sp-73584f77": "",
              })}
            >
              {display(ctx.view.originalAnswer)}
            </p>
          </details>
          {ctx.result.recommendedProperties.length ? (
            <details
              {...mergeProps({
                className: "original-evidence",
                onToggle: ($event) => {
                  return ctx.reading?.($event);
                },
                "data-sp-73584f77": "",
              })}
            >
              <summary
                {...mergeProps({
                  "data-sp-73584f77": "",
                })}
              >
                {"Chi tiết giá và thông tin nguồn"}
              </summary>
              {renderList(ctx.result.recommendedProperties, (property) => (
                <div
                  key={property.id}
                  {...mergeProps({
                    className: "property-audit",
                    "data-sp-73584f77": "",
                  })}
                >
                  <strong
                    {...mergeProps({
                      "data-sp-73584f77": "",
                    })}
                  >
                    {display(property.title)}
                  </strong>
                  <p
                    {...mergeProps({
                      "data-sp-73584f77": "",
                    })}
                  >
                    {display(
                      ctx.view.cards.find((c) => c.id === property.id).price
                        .exact,
                    )}
                    {" · Nguồn "}
                    {display(property.source.name)}
                  </p>
                  {renderList(property.explanations, (line) => (
                    <p
                      key={line}
                      {...mergeProps({
                        "data-sp-73584f77": "",
                      })}
                    >
                      {display(line)}
                    </p>
                  ))}
                  {renderList(property.warnings, (warning) => (
                    <p
                      key={warning}
                      {...mergeProps({
                        "data-sp-73584f77": "",
                      })}
                    >
                      {display(warning)}
                    </p>
                  ))}
                  <code
                    {...mergeProps({
                      "data-sp-73584f77": "",
                    })}
                  >
                    {display(property.id)}
                  </code>
                </div>
              ))}
            </details>
          ) : null}
          <details
            {...mergeProps({
              className: "original-evidence",
              onToggle: ($event) => {
                return ctx.reading?.($event);
              },
              "data-sp-73584f77": "",
            })}
          >
            <summary
              {...mergeProps({
                "data-sp-73584f77": "",
              })}
            >
              {"Giới hạn dữ liệu"}
            </summary>
            <ul
              {...mergeProps({
                "data-sp-73584f77": "",
              })}
            >
              {renderList(ctx.view.limitations, (item) => (
                <li
                  key={item}
                  {...mergeProps({
                    "data-sp-73584f77": "",
                  })}
                >
                  {display(item)}
                </li>
              ))}
            </ul>
          </details>
        </details>
      ) : null}
      {ctx.view.citations.length ? (
        <p
          {...mergeProps({
            className: "answer-caution",
            "data-sp-73584f77": "",
          })}
        >
          {
            "Giá rao và điểm phù hợp để tham khảo. Bằng chứng khu vực không chứng minh khoảng cách từ căn nhà."
          }
        </p>
      ) : null}
    </div>,
  ]);
});
