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
import { onBeforeUnmount, ref, watch } from "../../shared/state/store.js";
import { session, errorText } from "../auth/api.js";
import { createHistoryClient } from "./history.js";
import { formatPrice, locationLabel } from "./valuation.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    refreshKey: Number,
  });
  const client = createHistoryClient();
  const items = ref([]),
    busy = ref(false),
    error = ref(""),
    page = ref(0),
    pages = ref(0);
  const removing = ref(""),
    labels = ref({});
  let revision = 0;
  async function load() {
    const current = ++revision;
    items.value = [];
    error.value = "";
    busy.value = false;
    if (!session.token) return;
    busy.value = true;
    try {
      const result = await client.list(page.value);
      if (current !== revision) return;
      items.value = result.items;
      pages.value = result.totalPages;
    } catch (failure) {
      if (current === revision)
        error.value =
          failure.code === "HISTORY_UNAVAILABLE"
            ? "Lịch sử định giá hiện chưa khả dụng. Bạn vẫn có thể thực hiện ước tính mới."
            : errorText(failure);
    } finally {
      if (current === revision) busy.value = false;
    }
  }
  async function remove(id) {
    if (removing.value) return;
    const current = revision;
    removing.value = id;
    error.value = "";
    try {
      await client.remove(id);
      if (current !== revision) return;
      page.value = 0;
      await load();
    } catch (failure) {
      if (current === revision) error.value = errorText(failure);
    } finally {
      removing.value = "";
    }
  }
  function setLabels(value) {
    labels.value = value;
  }
  exposeForSetup({
    setLabels,
  });
  watch(
    () => session.token,
    () => {
      page.value = 0;
      load();
    },
    {
      immediate: true,
    },
  );
  watch(
    () => props.refreshKey,
    () => {
      page.value = 0;
      load();
    },
  );
  onBeforeUnmount(() => {
    revision++;
  });
  return {
    onBeforeUnmount,
    ref,
    watch,
    session,
    errorText,
    createHistoryClient,
    formatPrice,
    locationLabel,
    props,
    client,
    items,
    busy,
    error,
    page,
    pages,
    removing,
    labels,
    revision,
    load,
    remove,
    setLabels,
  };
}
export default React.forwardRef(function ValuationHistory(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        className:
          "mt-8 rounded-3xl border border-[var(--ui-border)]/20 bg-brand-card p-6 sm:p-8",
        "aria-labelledby": "history-heading",
      })}
    >
      <div
        {...mergeProps({
          className: "flex flex-wrap justify-between gap-3",
        })}
      >
        <h2
          {...mergeProps({
            id: "history-heading",
            className: "text-xl font-semibold sm:text-2xl",
          })}
        >
          {"Lịch sử định giá"}
        </h2>
        <RouterLink
          {...mergeProps({
            to: "/valuation",
            className: "text-sm underline",
          })}
        >
          {"Ước tính giá rao mới ↗"}
        </RouterLink>
      </div>
      {!ctx.session.token ? (
        <p
          {...mergeProps({
            className: "mt-3 text-sm leading-6",
          })}
        >
          <RouterLink
            {...mergeProps({
              to: "/login?next=/valuation",
              className: "underline",
            })}
          >
            {"Đăng nhập"}
          </RouterLink>
          {" để lưu và xem lại kết quả của bạn. "}
        </p>
      ) : (
        <React.Fragment {...mergeProps({})}>
          <p
            {...mergeProps({
              className: "mt-2 text-sm text-[var(--ui-accent)]",
            })}
          >
            {"Kết quả đã lưu của "}
            {display(ctx.session.user?.fullName || "tài khoản hiện tại")}
            {". Giá được giữ theo thời điểm ước tính."}
          </p>
          {ctx.busy ? (
            <p
              {...mergeProps({
                role: "status",
                className: "mt-4",
              })}
            >
              {"Đang tải lịch sử…"}
            </p>
          ) : null}
          {ctx.error ? (
            <div
              {...mergeProps({
                role: "alert",
                className: "mt-4 rounded-xl bg-[var(--ui-surface)] p-3 text-sm",
              })}
            >
              {display(ctx.error)}{" "}
              <button
                {...mergeProps({
                  className: "underline ml-2",
                  onClick: ($event) => {
                    return ctx.load?.($event);
                  },
                })}
              >
                {"Tải lại lịch sử"}
              </button>
            </div>
          ) : null}
          {!ctx.busy && !ctx.error && !ctx.items.length ? (
            <div
              {...mergeProps({
                className:
                  "mt-5 rounded-2xl border border-dashed border-brand-line bg-brand-cream p-6 text-center",
              })}
            >
              <h3
                {...mergeProps({
                  className: "text-base font-semibold",
                })}
              >
                {"Chưa có phân tích đã lưu"}
              </h3>
              <p
                {...mergeProps({
                  className:
                    "mx-auto mt-2 max-w-md text-sm leading-7 text-brand-muted",
                })}
              >
                {
                  "Khi bạn lưu một kết quả ước tính, kết quả đó sẽ xuất hiện tại đây."
                }
              </p>
              <RouterLink
                {...mergeProps({
                  to: "/valuation",
                  className: "sp-button sp-button-secondary mt-4",
                })}
              >
                {"Thực hiện đánh giá mới ↗"}
              </RouterLink>
            </div>
          ) : null}
          <ol
            {...mergeProps({
              className: "mt-4 space-y-3",
            })}
          >
            {renderList(ctx.items, (item) => (
              <li
                key={item.id}
                {...mergeProps({
                  className: "rounded-xl bg-[var(--ui-surface)]/60 p-4",
                  "data-testid": "history-item",
                })}
              >
                <div
                  {...mergeProps({
                    className:
                      "flex flex-wrap items-start justify-between gap-3",
                  })}
                >
                  <div {...mergeProps({})}>
                    <p
                      {...mergeProps({
                        className: "font-semibold",
                      })}
                    >
                      {display(
                        ctx.formatPrice(
                          item.prediction.predicted_asking_price_vnd,
                        ),
                      )}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-sm mt-1",
                      })}
                    >
                      {display(item.input.category)}
                      {" · "}
                      {display(item.input.area_sqm)}
                      {" m² · "}
                      {display(
                        ctx.locationLabel(
                          item.input.location_feature,
                          ctx.labels,
                        ),
                      )}
                    </p>
                    <p
                      {...mergeProps({
                        className: "text-xs mt-2 text-[var(--ui-accent)]",
                      })}
                    >
                      {display(
                        new Intl.DateTimeFormat("vi-VN", {
                          dateStyle: "short",
                          timeStyle: "short",
                        }).format(new Date(item.createdAt)),
                      )}
                      {" · Giá rao tham khảo"}
                    </p>
                  </div>
                  <button
                    {...mergeProps({
                      type: "button",
                      disabled: !!ctx.removing,
                      className: "text-sm underline disabled:opacity-50",
                      "aria-label": `Xóa kết quả ${ctx.formatPrice(item.prediction.predicted_asking_price_vnd)}`,
                      onClick: ($event) => {
                        ctx.remove(item.id);
                      },
                    })}
                  >
                    {display(ctx.removing === item.id ? "Đang xóa…" : "Xóa")}
                  </button>
                </div>
              </li>
            ))}
          </ol>
          {ctx.pages > 1 ? (
            <nav
              {...mergeProps({
                className: "mt-4 flex items-center gap-4 text-sm",
                "aria-label": "Trang lịch sử",
              })}
            >
              <button
                {...mergeProps({
                  disabled: ctx.busy || ctx.page === 0,
                  className: "underline disabled:opacity-40",
                  onClick: ($event) => {
                    ctx.page--;
                    ctx.load();
                  },
                })}
              >
                {"Trang trước"}
              </button>
              <span {...mergeProps({})}>
                {display(ctx.page + 1)}
                {" / "}
                {display(ctx.pages)}
              </span>
              <button
                {...mergeProps({
                  disabled: ctx.busy || ctx.page + 1 >= ctx.pages,
                  className: "underline disabled:opacity-40",
                  onClick: ($event) => {
                    ctx.page++;
                    ctx.load();
                  },
                })}
              >
                {"Trang sau"}
              </button>
            </nav>
          ) : null}
        </React.Fragment>
      )}
    </section>,
  ]);
});
