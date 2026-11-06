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
  watch,
  onMounted,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRouter, useRoute } from "../../shared/routing/router.jsx";
import { api, session, errorText } from "../auth/api.js";
import {
  useList,
  adapt,
  money,
  LegacyState,
  LegacyPager,
  PrivateImage,
  types,
  states,
  reasons as reasonLabels,
  date,
  mapUrl,
} from "../../shared/lib/legacy.js";
import "./PostsView.css";
function setup(__props) {
  const statusFilter = ref("PENDING");
  const router = useRouter(),
    state = useList("/admin/properties", () => ({
      status: statusFilter.value,
    })),
    selected = ref(null),
    reason = ref(""),
    pendingPosts = computed(() =>
      state.items.map((m) => ({
        ...adapt(m),
        location: adapt(m).location,
        time: date(m.property.createdAt),
        badgeText: states[m.property.status],
        badgeClass: "badge-info",
      })),
    );
  const handleViewDetail = (id) => {
    selected.value = state.items.find((m) => m.property.id === id);
    reason.value = "";
  };
  async function moderate(id, action) {
    if (!selected.value || selected.value.property.id !== id) {
      handleViewDetail(id);
      return;
    }
    if (!reason.value.trim()) {
      state.error = "Nhập lý do trước khi xử lý.";
      return;
    }
    await state.run(async () => {
      await api("/admin/properties/" + id + "/moderation", {
        method: "POST",
        body: {
          action,
          expectedVersion: selected.value.property.contentVersion,
          reason: reason.value,
        },
      });
      selected.value = null;
      await state.load(state.page);
    });
  }
  const handleApprove = (id) => moderate(id, "APPROVE"),
    handleReject = (id) => moderate(id, "REJECT");
  return {
    ref,
    computed,
    watch,
    onMounted,
    onBeforeUnmount,
    useRouter,
    useRoute,
    api,
    session,
    errorText,
    useList,
    adapt,
    money,
    LegacyState,
    LegacyPager,
    PrivateImage,
    types,
    states,
    reasonLabels,
    date,
    mapUrl,
    statusFilter,
    router,
    state,
    selected,
    reason,
    pendingPosts,
    handleViewDetail,
    moderate,
    handleApprove,
    handleReject,
  };
}
export default React.forwardRef(function PostsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="PostsView"
      {...mergeProps({
        className: "main",
        "data-sp-e7925a7a": "",
      })}
    >
      <LegacyState
        {...mergeProps({
          state: ctx.state,
          "data-sp-e7925a7a": "",
        })}
      />
      <div
        {...mergeProps({
          className: "section-title",
          "data-sp-e7925a7a": "",
        })}
      >
        <div
          {...mergeProps({
            className: "_18-tin-ang-ch-duy-t",
            "data-sp-e7925a7a": "",
          })}
        >
          {display(ctx.state.totalElements)}
          {" tin đăng"}
        </div>
      </div>
      <select
        {...mergeProps(
          {
            onChange: ($event) => {
              ctx.selected = null;
              ctx.state.load(0);
            },
            className: "bg-brand-card border rounded-lg p-2 text-sm",
            "data-sp-e7925a7a": "",
          },
          modelProps(
            ctx.statusFilter,
            ($value) => {
              ctx.statusFilter = $value;
            },
            {
              kind: "text",
              value: "on",
              number: false,
              multiple: false,
            },
          ),
        )}
      >
        {renderList(
          [
            "PENDING",
            "PUBLISHED",
            "HIDDEN",
            "REJECTED",
            "DRAFT",
            "EXPIRED",
            "CLOSED",
          ],
          (key) => (
            <option
              key={key}
              {...mergeProps({
                value: key,
                "data-sp-e7925a7a": "",
              })}
            >
              {display(ctx.states[key])}
            </option>
          ),
        )}
      </select>
      <div
        {...mergeProps({
          className: "posts-list",
          "data-sp-e7925a7a": "",
        })}
      >
        {renderList(ctx.pendingPosts, (post) => (
          <div
            key={post.id}
            {...mergeProps({
              className: "post-card",
              "data-sp-e7925a7a": "",
            })}
          >
            <PrivateImage
              {...mergeProps({
                src: post.image,
                alt: "Ảnh tin đăng",
                className: "post-thumb object-cover",
                "data-sp-e7925a7a": "",
              })}
            />
            <div
              {...mergeProps({
                className: "post-info",
                "data-sp-e7925a7a": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "listing-code",
                  "data-sp-e7925a7a": "",
                })}
              >
                {display(post.listingCode || "Chưa cấp mã")}
              </span>
              <div
                {...mergeProps({
                  className: "post-title",
                  "data-sp-e7925a7a": "",
                })}
              >
                {display(post.title)}
              </div>
              <div
                {...mergeProps({
                  className: "post-meta",
                  "data-sp-e7925a7a": "",
                })}
              >
                {display(post.location)}
                {" · "}
                {display(post.price)}
                {" · gửi "}
                {display(post.time)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["post-badge", post.badgeClass],
                "data-sp-e7925a7a": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "badge-text",
                  "data-sp-e7925a7a": "",
                })}
              >
                {display(post.badgeText)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "post-actions",
                "data-sp-e7925a7a": "",
              })}
            >
              {post.raw.status === "PENDING" ? (
                <button
                  {...mergeProps({
                    className: "btn-approve",
                    onClick: ($event) => {
                      ctx.handleApprove(post.id);
                    },
                    "data-sp-e7925a7a": "",
                  })}
                >
                  {"Duyệt"}
                </button>
              ) : null}
              {post.raw.status === "PENDING" ? (
                <button
                  {...mergeProps({
                    className: "btn-reject",
                    onClick: ($event) => {
                      ctx.handleReject(post.id);
                    },
                    "data-sp-e7925a7a": "",
                  })}
                >
                  {"Từ chối"}
                </button>
              ) : null}
              {post.raw.status === "PUBLISHED" ? (
                <button
                  {...mergeProps({
                    className: "btn-reject",
                    onClick: ($event) => {
                      ctx.moderate(post.id, "HIDE");
                    },
                    "data-sp-e7925a7a": "",
                  })}
                >
                  {"Ẩn tin"}
                </button>
              ) : null}
              {post.raw.status === "HIDDEN" ? (
                <button
                  {...mergeProps({
                    className: "btn-approve",
                    onClick: ($event) => {
                      ctx.moderate(post.id, "RESTORE");
                    },
                    "data-sp-e7925a7a": "",
                  })}
                >
                  {"Khôi phục"}
                </button>
              ) : null}
              <button
                {...mergeProps({
                  className: "btn-detail",
                  onClick: ($event) => {
                    ctx.handleViewDetail(post.id);
                  },
                  "data-sp-e7925a7a": "",
                })}
              >
                {"Xem chi tiết ›"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>,
    ctx.selected ? (
      <section
        {...mergeProps({
          className: "bg-brand-card rounded-2xl p-6",
          "data-sp-e7925a7a": "",
        })}
      >
        <p
          {...mergeProps({
            className: "listing-code",
            "data-sp-e7925a7a": "",
          })}
        >
          {"Mã tin: "}
          {display(ctx.selected.property.listingCode || "Chưa cấp mã")}
        </p>
        <h3
          {...mergeProps({
            className: "font-semibold",
            "data-sp-e7925a7a": "",
          })}
        >
          {display(ctx.selected.property.title)}
        </h3>
        <p
          {...mergeProps({
            className: "text-xs py-3 whitespace-pre-wrap",
            "data-sp-e7925a7a": "",
          })}
        >
          {display(ctx.selected.property.description)}
        </p>
        <dl
          {...mergeProps({
            className: "grid gap-2 text-sm mb-4",
            "data-sp-e7925a7a": "",
          })}
        >
          <div
            {...mergeProps({
              "data-sp-e7925a7a": "",
            })}
          >
            {"Người đăng: #"}
            {display(ctx.selected.ownerId)}
          </div>
          <div
            {...mergeProps({
              "data-sp-e7925a7a": "",
            })}
          >
            {"Giá: "}
            {display(ctx.money(ctx.selected.property))}
            {" · Diện tích: "}
            {display(ctx.selected.property.areaSqm)}
            {" m²"}
          </div>
          <div
            {...mergeProps({
              "data-sp-e7925a7a": "",
            })}
          >
            {"Địa chỉ: "}
            {display(ctx.selected.property.address)}
            {", "}
            {display(ctx.selected.property.district)}
            {", "}
            {display(ctx.selected.property.city)}
          </div>
          <div
            {...mergeProps({
              "data-sp-e7925a7a": "",
            })}
          >
            {"Vị trí: "}
            {display(ctx.selected.property.latitude)}
            {", "}
            {display(ctx.selected.property.longitude)}
          </div>
          <div
            {...mergeProps({
              "data-sp-e7925a7a": "",
            })}
          >
            {"Liên hệ khai báo: "}
            {display(ctx.selected.contactName)}
            {" · "}
            {display(ctx.selected.contactPhone)}
          </div>
        </dl>
        <div
          {...mergeProps({
            className: "grid grid-cols-3 gap-3",
            "data-sp-e7925a7a": "",
          })}
        >
          {renderList(ctx.selected.property.images, (image) => (
            <PrivateImage
              key={image.id}
              {...mergeProps({
                src: image.url,
                alt: "Ảnh tin chờ duyệt",
                className: "h-32 w-full object-cover rounded-xl",
                "data-sp-e7925a7a": "",
              })}
            />
          ))}
        </div>
        <label
          {...mergeProps({
            className: "block text-xs mt-4",
            "data-sp-e7925a7a": "",
          })}
        >
          {"Lý do"}
          <textarea
            {...mergeProps(
              {
                className: "w-full mt-2 p-3 border rounded-xl",
                maxLength: "4000",
                "data-sp-e7925a7a": "",
              },
              modelProps(
                ctx.reason,
                ($value) => {
                  ctx.reason = $value;
                },
                {
                  kind: "text",
                  value: "on",
                  number: false,
                  multiple: false,
                },
              ),
            )}
          />
        </label>
        {ctx.selected.property.status === "PENDING" ? (
          <button
            {...mergeProps({
              className:
                "px-4 py-2 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs",
              onClick: ($event) => {
                ctx.handleApprove(ctx.selected.property.id);
              },
              "data-sp-e7925a7a": "",
            })}
          >
            {"Duyệt tin"}
          </button>
        ) : null}
        {ctx.selected.property.status === "PENDING" ? (
          <button
            {...mergeProps({
              className: "px-4 py-2 rounded-full border ml-2 text-xs",
              onClick: ($event) => {
                ctx.handleReject(ctx.selected.property.id);
              },
              "data-sp-e7925a7a": "",
            })}
          >
            {"Từ chối"}
          </button>
        ) : null}
        {ctx.selected.property.status === "PUBLISHED" ? (
          <button
            {...mergeProps({
              className: "px-4 py-2 rounded-full border text-xs",
              onClick: ($event) => {
                ctx.moderate(ctx.selected.property.id, "HIDE");
              },
              "data-sp-e7925a7a": "",
            })}
          >
            {"Ẩn tin"}
          </button>
        ) : null}
        {ctx.selected.property.status === "HIDDEN" ? (
          <button
            {...mergeProps({
              className: "px-4 py-2 rounded-full border text-xs",
              onClick: ($event) => {
                ctx.moderate(ctx.selected.property.id, "RESTORE");
              },
              "data-sp-e7925a7a": "",
            })}
          >
            {"Khôi phục"}
          </button>
        ) : null}
      </section>
    ) : null,
    <LegacyPager
      {...mergeProps({
        state: ctx.state,
        "data-sp-e7925a7a": "",
      })}
    />,
  ]);
});
