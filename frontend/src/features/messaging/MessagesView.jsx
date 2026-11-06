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
  reactive,
  watch,
  onMounted,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRoute, useRouter } from "../../shared/routing/router.jsx";
import { api, session } from "../auth/api.js";
import { createThread } from "./thread.js";
import { useCollection } from "../home/useCollection.js";
import { LegacyState, LegacyPager, date } from "../../shared/lib/legacy.js";
import BusinessPage from "../../shared/components/BusinessPage.jsx";
function setup(__props) {
  const route = useRoute(),
    router = useRouter(),
    conversations = useCollection("/users/me/conversations", null, () => ({})),
    thread = createThread(api, undefined, reactive),
    state = thread.state,
    text = ref("");
  let timer;
  async function select(id) {
    if (
      state.pending &&
      !confirm("Tin nhắn chưa được xác nhận. Rời hội thoại này?")
    )
      return;
    await router.replace({
      query: {
        conversation: id,
      },
    });
  }
  async function poll() {
    if (document.hidden || !route.query.conversation) return;
    await thread.load();
    if (!state.error)
      try {
        await thread.markRead();
      } catch {
        state.error = "Chưa cập nhật được trạng thái đã đọc.";
      }
  }
  watch(
    () => route.query.conversation,
    async (id) => {
      thread.reset(typeof id === "string" ? id : null);
      text.value = "";
      await poll();
    },
    {
      immediate: true,
    },
  );
  async function send() {
    if (await thread.send(text.value)) {
      text.value = "";
      await poll();
      await conversations.load(conversations.page);
    }
  }
  onMounted(() => (timer = setInterval(poll, 5000)));
  onBeforeUnmount(() => {
    clearInterval(timer);
    thread.dispose();
  });
  return {
    ref,
    reactive,
    watch,
    onMounted,
    onBeforeUnmount,
    useRoute,
    useRouter,
    api,
    session,
    createThread,
    useCollection,
    LegacyState,
    LegacyPager,
    date,
    BusinessPage,
    route,
    router,
    conversations,
    thread,
    state,
    text,
    timer,
    select,
    poll,
    send,
  };
}
export default React.forwardRef(function MessagesView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <BusinessPage data-ui-view="MessagesView"
      {...mergeProps({
        title: "Tin nhắn",
      })}
    >
      <p
        {...mergeProps({
          className: "text-sm",
        })}
      >
        {"Tin nhắn riêng giữa hai bên · cập nhật định kỳ bằng REST."}
      </p>
      <div
        {...mergeProps({
          className: "grid gap-6 md:grid-cols-[280px_1fr]",
        })}
      >
        <aside {...mergeProps({})}>
          <LegacyState
            {...mergeProps({
              state: ctx.conversations,
            })}
          />
          {!ctx.conversations.busy && !ctx.conversations.items.length ? (
            <p {...mergeProps({})}>{"Chưa có hội thoại."}</p>
          ) : null}
          {renderList(ctx.conversations.items, (c) => (
            <section key={c.id} {...mergeProps({})}>
              <button
                {...mergeProps({
                  "aria-current":
                    ctx.route.query.conversation === c.id ? "page" : undefined,
                  onClick: ($event) => {
                    ctx.select(c.id);
                  },
                })}
              >
                {"Tin "}
                {display(c.propertyId.slice(0, 8))}
                {" · "}
                {display(c.unreadCount)}
                {" chưa đọc"}
              </button>
              <p {...mergeProps({})}>{display(ctx.date(c.updatedAt))}</p>
            </section>
          ))}
          <LegacyPager
            {...mergeProps({
              state: ctx.conversations,
            })}
          />
        </aside>
        {ctx.route.query.conversation ? (
          <section
            {...mergeProps({
              "aria-label": "Nội dung hội thoại",
            })}
          >
            {ctx.state.error ? (
              <p
                {...mergeProps({
                  role: "alert",
                })}
              >
                {display(ctx.state.error)}
              </p>
            ) : null}
            <button
              {...mergeProps({
                disabled: ctx.state.busy,
                onClick: ($event) => {
                  return ctx.poll?.($event);
                },
              })}
            >
              {display(
                ctx.state.busy ? "Đang tải…" : "Tải tin tiếp / cập nhật",
              )}
            </button>
            {!ctx.state.busy && !ctx.state.items.length ? (
              <p {...mergeProps({})}>{"Chưa có tin nhắn."}</p>
            ) : null}
            <ol
              {...mergeProps({
                "aria-live": "polite",
              })}
            >
              {renderList(ctx.state.items, (m) => (
                <li
                  key={m.id}
                  {...mergeProps({
                    className: "my-3 rounded-xl bg-[var(--ui-surface)] p-3",
                  })}
                >
                  <strong {...mergeProps({})}>
                    {display(
                      m.senderId === ctx.session.user?.id
                        ? "Bạn"
                        : "Người tham gia",
                    )}
                  </strong>
                  <p
                    {...mergeProps({
                      className: "whitespace-pre-wrap",
                    })}
                  >
                    {display(m.body)}
                  </p>
                  <small {...mergeProps({})}>
                    {display(ctx.date(m.createdAt))}
                  </small>
                </li>
              ))}
            </ol>
            {ctx.state.hasMore ? (
              <p {...mergeProps({})}>{"Còn tin tiếp theo; bấm tải để xem."}</p>
            ) : null}
            <form
              {...mergeProps({
                onSubmit: ($event) => {
                  $event.preventDefault();
                  return ctx.send?.($event);
                },
              })}
            >
              <label {...mergeProps({})}>
                {"Nội dung "}
                <textarea
                  {...mergeProps(
                    {
                      maxLength: "4000",
                      required: true,
                      readOnly: ctx.state.sendBusy,
                    },
                    modelProps(
                      ctx.text,
                      ($value) => {
                        ctx.text = $value;
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
              {ctx.state.pending ? (
                <p {...mergeProps({})}>
                  {
                    "Tin trước chưa được server xác nhận. Thử lại cùng nội dung sẽ dùng cùng mã tin."
                  }
                </p>
              ) : null}
              <button
                {...mergeProps({
                  disabled: ctx.state.sendBusy || !ctx.text.trim(),
                })}
              >
                {display(
                  ctx.state.sendBusy
                    ? "Đang gửi…"
                    : ctx.state.pending
                      ? "Thử gửi lại"
                      : "Gửi tin nhắn",
                )}
              </button>
            </form>
          </section>
        ) : (
          <p {...mergeProps({})}>
            {"Chọn một hội thoại hoặc mở “Nhắn tin” từ tin bất động sản."}
          </p>
        )}
      </div>
    </BusinessPage>,
  ]);
});
