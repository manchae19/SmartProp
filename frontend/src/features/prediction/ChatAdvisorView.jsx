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
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "../../shared/state/store.js";
import { chatSession } from "./chatRuntime.js";
import { isNearChatBottom } from "./chatPresentation.js";
import ChatAnswer from "../../shared/components/ChatAnswer.jsx";
import ChatSessionPanel from "../../shared/components/ChatSessionPanel.jsx";
import MobileDrawer from "../../shared/components/layout/MobileDrawer.jsx";
import AppIcon from "../../shared/components/AppIcon.jsx";
import "./ChatAdvisorView.css";
function setup(__props) {
  const { state } = chatSession;
  const draft = ref(""),
    input = ref(null),
    thread = ref(null),
    clock = ref(Date.now()),
    viewportHeight = ref(null);
  const sidebar = ref(true),
    drawer = ref(false),
    smallScreen = ref(false),
    menuButton = ref(null);
  const follow = ref(true),
    unread = ref(false);
  let focusAfterDrawer = "menu";
  let timer, media;
  const elapsed = computed(() =>
    Math.max(0, Math.floor((clock.value - state.startedAt) / 1000)),
  );
  const waitSeconds = computed(() =>
    Math.max(0, Math.ceil((state.retryAt - clock.value) / 1000)),
  );
  const locked = computed(() => state.busy || waitSeconds.value > 0);
  const preview = computed(
    () => state.messages.findLast((m) => m.role === "user")?.text || "",
  );
  function resizeInput() {
    if (!input.value) return;
    input.value.style.height = "auto";
    input.value.style.height = Math.min(128, input.value.scrollHeight) + "px";
    input.value.style.overflowY =
      input.value.scrollHeight > 128 ? "auto" : "hidden";
  }
  function scrollLatest() {
    follow.value = true;
    unread.value = false;
    if (thread.value) thread.value.scrollTop = thread.value.scrollHeight;
  }
  function onScroll() {
    follow.value = isNearChatBottom(thread.value);
    if (follow.value) unread.value = false;
  }
  function reading() {
    follow.value = false;
  }
  function answerResized() {
    if (follow.value) nextTick(scrollLatest);
    else unread.value = true;
  }
  function questionFor(messageId) {
    const index = state.messages.findIndex((m) => m.id === messageId);
    return (
      state.messages.slice(0, index).findLast((m) => m.role === "user")?.text ||
      ""
    );
  }
  function syncViewport() {
    if (typeof window === "undefined") return;
    const view = window.visualViewport;
    const top =
      document.querySelector(".app-header")?.getBoundingClientRect().bottom ||
      0;
    // visualViewport follows the mobile keyboard; composer stays inside the visible frame.
    viewportHeight.value = Math.max(
      180,
      (view?.height || window.innerHeight) -
        Math.max(0, top - (view?.offsetTop || 0)),
    );
    if (follow.value) nextTick(scrollLatest);
  }
  function screenChanged() {
    smallScreen.value = media.matches;
    if (!media.matches) drawer.value = false;
    syncViewport();
  }
  function togglePanel() {
    if (smallScreen.value) {
      focusAfterDrawer = "menu";
      drawer.value = true;
    } else sidebar.value = !sidebar.value;
  }
  async function drawerClosed() {
    await nextTick();
    (focusAfterDrawer === "input" ? input.value : menuButton.value)?.focus({
      preventScroll: true,
    });
  }
  async function choose(question) {
    if (locked.value) return;
    draft.value = question;
    focusAfterDrawer = "input";
    drawer.value = false;
    await nextTick();
    resizeInput();
    input.value?.focus();
  }
  function currentConversation() {
    focusAfterDrawer = "input";
    drawer.value = false;
    nextTick(() => input.value?.focus());
  }
  function newConversation() {
    if (locked.value) return;
    chatSession.clear();
    draft.value = "";
    scrollLatest();
    nextTick(() => {
      resizeInput();
      input.value?.focus();
    });
  }
  async function submit() {
    if (locked.value || !draft.value.trim()) return;
    follow.value = true;
    const pending = chatSession.submit(draft.value);
    if (state.busy) draft.value = "";
    await nextTick();
    resizeInput();
    scrollLatest();
    await pending;
  }
  async function quickReply(question) {
    await choose(question);
    await submit();
  }
  function retry() {
    if (locked.value) return;
    follow.value = true;
    chatSession.retry();
  }
  function keydown(event) {
    if (!event.shiftKey && !event.isComposing) {
      event.preventDefault();
      submit();
    }
  }
  watch(draft, () => nextTick(resizeInput));
  watch(
    () => [state.messages.length, state.busy, state.error],
    async () => {
      const shouldFollow = follow.value;
      await nextTick();
      if (shouldFollow) scrollLatest();
      else unread.value = true;
    },
  );
  onMounted(() => {
    timer = setInterval(() => {
      clock.value = Date.now();
    }, 1000);
    media = window.matchMedia("(max-width: 760px)");
    screenChanged();
    media.addEventListener("change", screenChanged);
    window.addEventListener("resize", syncViewport);
    window.visualViewport?.addEventListener("resize", syncViewport);
    window.visualViewport?.addEventListener("scroll", syncViewport);
    nextTick(() => {
      resizeInput();
      scrollLatest();
    });
  });
  onBeforeUnmount(() => {
    clearInterval(timer);
    media?.removeEventListener("change", screenChanged);
    window.removeEventListener("resize", syncViewport);
    window.visualViewport?.removeEventListener("resize", syncViewport);
    window.visualViewport?.removeEventListener("scroll", syncViewport);
  });
  return {
    computed,
    nextTick,
    onBeforeUnmount,
    onMounted,
    ref,
    watch,
    chatSession,
    isNearChatBottom,
    ChatAnswer,
    ChatSessionPanel,
    MobileDrawer,
    AppIcon,
    state,
    draft,
    input,
    thread,
    clock,
    viewportHeight,
    sidebar,
    drawer,
    smallScreen,
    menuButton,
    follow,
    unread,
    focusAfterDrawer,
    timer,
    media,
    elapsed,
    waitSeconds,
    locked,
    preview,
    resizeInput,
    scrollLatest,
    onScroll,
    reading,
    answerResized,
    questionFor,
    syncViewport,
    screenChanged,
    togglePanel,
    drawerClosed,
    choose,
    currentConversation,
    newConversation,
    submit,
    quickReply,
    retry,
    keydown,
  };
}
export default React.forwardRef(function ChatAdvisorView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section data-ui-view="ChatAdvisorView"
      {...mergeProps({
        className: "messenger-page",
        "aria-labelledby": "chat-title",
        style: ctx.viewportHeight
          ? {
              height: ctx.viewportHeight + "px",
            }
          : undefined,
        "data-sp-b5f8ab84": "",
      })}
    >
      <div
        {...mergeProps({
          className: ["messenger-shell", {
            "sidebar-collapsed": !ctx.sidebar,
          }],
          
          "data-sp-b5f8ab84": "",
        })}
      >
        {ctx.sidebar ? (
          <aside
            {...mergeProps({
              className: "desktop-chat-panel",
              "aria-label": "Hội thoại trong tab",
              "data-sp-b5f8ab84": "",
            })}
          >
            <div
              {...mergeProps({
                className: "panel-title",
                "data-sp-b5f8ab84": "",
              })}
            >
              <h2
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Tin nhắn"}
              </h2>
              <span
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"SmartProp"}
              </span>
            </div>
            <ChatSessionPanel
              {...mergeProps({
                preview: ctx.preview,
                locked: ctx.locked,
                onChoose: ($event) => {
                  return ctx.choose?.($event);
                },
                onCurrent: ($event) => {
                  return ctx.currentConversation?.($event);
                },
                "data-sp-b5f8ab84": "",
              })}
            />
          </aside>
        ) : null}
        <div
          {...mergeProps({
            className: "conversation",
            "data-sp-b5f8ab84": "",
          })}
        >
          <header
            {...mergeProps({
              className: "conversation-header",
              "data-sp-b5f8ab84": "",
            })}
          >
            <button
              {...mergeProps({
                ref: bindRef(ctx, "menuButton"),
                type: "button",
                className: "chat-icon-button panel-toggle",
                "aria-label": ctx.smallScreen
                  ? "Mở hội thoại và gợi ý"
                  : ctx.sidebar
                    ? "Thu gọn danh sách hội thoại"
                    : "Mở danh sách hội thoại",
                "aria-expanded": ctx.smallScreen ? ctx.drawer : ctx.sidebar,
                onClick: ($event) => {
                  return ctx.togglePanel?.($event);
                },
                "data-sp-b5f8ab84": "",
              })}
            >
              <svg
                {...mergeProps({
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: "1.7",
                  "aria-hidden": "true",
                  "data-sp-b5f8ab84": "",
                })}
              >
                <rect
                  {...mergeProps({
                    x: "3",
                    y: "4",
                    width: "18",
                    height: "16",
                    rx: "3",
                    "data-sp-b5f8ab84": "",
                  })}
                />
                <path
                  {...mergeProps({
                    d: "M9 4v16",
                    "data-sp-b5f8ab84": "",
                  })}
                />
              </svg>
            </button>
            <span
              {...mergeProps({
                className: "conversation-avatar",
                "aria-hidden": "true",
                "data-sp-b5f8ab84": "",
              })}
            >
              {"S"}
              <span
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"AI"}
              </span>
            </span>
            <div
              {...mergeProps({
                className: "conversation-name",
                "data-sp-b5f8ab84": "",
              })}
            >
              <h1
                {...mergeProps({
                  id: "chat-title",
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"SmartProp AI Advisor"}
              </h1>
              <p
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Trợ lý tư vấn bất động sản"}
              </p>
            </div>
            <button
              {...mergeProps({
                type: "button",
                className: "chat-icon-button new-chat",
                disabled: ctx.locked || !ctx.state.messages.length,
                "aria-label": "Tạo hội thoại mới",
                title: "Bắt đầu lại sẽ xóa hội thoại hiện tại trong tab",
                onClick: ($event) => {
                  return ctx.newConversation?.($event);
                },
                "data-sp-b5f8ab84": "",
              })}
            >
              <AppIcon
                {...mergeProps({
                  name: "edit",
                  "data-sp-b5f8ab84": "",
                })}
              />
              <span
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Hội thoại mới"}
              </span>
            </button>
          </header>
          <div
            {...mergeProps({
              className: "thread-host",
              "data-sp-b5f8ab84": "",
            })}
          >
            <div
              {...mergeProps({
                ref: bindRef(ctx, "thread"),
                className: "chat-thread",
                role: "log",
                "aria-labelledby": "chat-title",
                "aria-live": "polite",
                "aria-relevant": "additions",
                "aria-busy": ctx.state.busy,
                tabIndex: "0",
                onScroll: ($event) => {
                  return ctx.onScroll?.($event);
                },
                "data-sp-b5f8ab84": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "thread-date",
                  "data-sp-b5f8ab84": "",
                })}
              >
                <span
                  {...mergeProps({
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  {"Hội thoại trong tab này"}
                </span>
              </div>
              {!ctx.state.messages.length ? (
                <div
                  {...mergeProps({
                    className: "chat-welcome",
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "welcome-avatar",
                      "aria-hidden": "true",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {"S"}
                  </span>
                  <h2
                    {...mergeProps({
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {"Chào bạn, mình là SmartProp."}
                  </h2>
                  <p
                    {...mergeProps({
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {
                      "Bạn đang tìm một nơi để ở hay muốn khám phá khu vực? Hãy bắt đầu từ ngân sách và nhu cầu của bạn."
                    }
                  </p>
                  <div
                    {...mergeProps({
                      className: "welcome-prompts",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    <button
                      {...mergeProps({
                        type: "button",
                        disabled: ctx.locked,
                        onClick: ($event) => {
                          ctx.choose(
                            "Tôi có 10 tỷ, gợi ý bất động sản phù hợp.",
                          );
                        },
                        "data-sp-b5f8ab84": "",
                      })}
                    >
                      {"Tìm BĐS theo ngân sách"}
                      <AppIcon
                        {...mergeProps({
                          name: "arrow",
                          "data-sp-b5f8ab84": "",
                        })}
                      />
                    </button>
                    <button
                      {...mergeProps({
                        type: "button",
                        disabled: ctx.locked,
                        onClick: ($event) => {
                          ctx.choose("Ở Hải Châu có những bệnh viện nào?");
                        },
                        "data-sp-b5f8ab84": "",
                      })}
                    >
                      {"Hỏi tiện ích khu vực"}
                      <AppIcon
                        {...mergeProps({
                          name: "arrow",
                          "data-sp-b5f8ab84": "",
                        })}
                      />
                    </button>
                  </div>
                  <p
                    {...mergeProps({
                      className: "welcome-note",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {
                      "Nhập nhu cầu tìm nhà của bạn để bắt đầu."
                    }
                  </p>
                </div>
              ) : null}
              {ctx.state.trimmed ? (
                <p
                  {...mergeProps({
                    className: "trimmed-note",
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  {"Đang hiển thị 24 tin nhắn gần nhất trong tab."}
                </p>
              ) : null}
              {renderList(ctx.state.messages, (message) => (
                <article
                  key={message.id}
                  {...mergeProps({
                    className:
                      message.role === "user"
                        ? "user-message"
                        : "assistant-message",
                    "data-chat-message": message.role,
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  {message.role === "user" ? (
                    <React.Fragment {...mergeProps({})}>
                      <span
                        {...mergeProps({
                          className: "sr-only",
                          "data-sp-b5f8ab84": "",
                        })}
                      >
                        {"Bạn:"}
                      </span>
                      <p
                        {...mergeProps({
                          className: "user-bubble",
                          "data-sp-b5f8ab84": "",
                        })}
                      >
                        {display(message.text)}
                      </p>
                    </React.Fragment>
                  ) : (
                    <React.Fragment {...mergeProps({})}>
                      <span
                        {...mergeProps({
                          className: "message-avatar",
                          "aria-hidden": "true",
                          "data-sp-b5f8ab84": "",
                        })}
                      >
                        {"S"}
                      </span>
                      <div className="answer-with-actions">
                        {message.response.evidence?.needs?.summary?.length ? (
                          <aside className="chat-needs-summary" aria-label="Tiêu chí đang dùng">
                            <strong>Tiêu chí đang dùng</strong>
                            <ul>{message.response.evidence.needs.summary.map((item, index) => <li key={index}>{item}</li>)}</ul>
                            <small>Bạn có thể gõ để sửa ngân sách, khu vực hoặc thứ tự ưu tiên.</small>
                          </aside>
                        ) : null}
                      <ChatAnswer
                        {...mergeProps({
                          result: message.response,
                          messageId: message.id,
                          question: ctx.questionFor(message.id),
                          onReading: ($event) => {
                            return ctx.reading?.($event);
                          },
                          onResized: ($event) => {
                            return ctx.answerResized?.($event);
                          },
                          "data-sp-b5f8ab84": "",
                        })}
                      />
                        {message.id === ctx.state.messages.at(-1)?.id && message.response.evidence?.quickReplies?.length ? (
                          <div className="chat-quick-replies" role="group" aria-label="Lựa chọn trả lời nhanh">
                            {message.response.evidence.quickReplies.map(choice => (
                              <button key={choice} type="button" disabled={ctx.locked} onClick={() => ctx.quickReply(choice)}>{choice}</button>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </React.Fragment>
                  )}
                </article>
              ))}
              {ctx.state.busy ? (
                <div
                  {...mergeProps({
                    className: "assistant-message typing-message",
                    role: "status",
                    "data-chat-loading": "",
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "message-avatar",
                      "aria-hidden": "true",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {"S"}
                  </span>
                  <div
                    {...mergeProps({
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    <div
                      {...mergeProps({
                        className: "typing-bubble",
                        "aria-hidden": "true",
                        "data-sp-b5f8ab84": "",
                      })}
                    >
                      <i
                        {...mergeProps({
                          "data-sp-b5f8ab84": "",
                        })}
                      />
                      <i
                        {...mergeProps({
                          "data-sp-b5f8ab84": "",
                        })}
                      />
                      <i
                        {...mergeProps({
                          "data-sp-b5f8ab84": "",
                        })}
                      />
                    </div>
                    <p
                      {...mergeProps({
                        className: "typing-label",
                        "data-sp-b5f8ab84": "",
                      })}
                    >
                      {display(
                        ctx.elapsed >= 30
                          ? "SmartProp vẫn đang xử lý. Bạn không cần gửi lại."
                          : "SmartProp đang tìm kiếm và phân tích…",
                      )}
                    </p>
                    <span
                      {...mergeProps({
                        className: "sr-only",
                        "data-sp-b5f8ab84": "",
                      })}
                    >
                      {"Câu trả lời sẽ xuất hiện khi xử lý hoàn tất."}
                    </span>
                  </div>
                </div>
              ) : null}
              {ctx.state.error ? (
                <div
                  {...mergeProps({
                    className: "assistant-message",
                    role: "alert",
                    "data-chat-error": "",
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  <span
                    {...mergeProps({
                      className: "message-avatar",
                      "aria-hidden": "true",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {"S"}
                  </span>
                  <div
                    {...mergeProps({
                      className: "error-bubble",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    <p
                      {...mergeProps({
                        "data-sp-b5f8ab84": "",
                      })}
                    >
                      {display(ctx.state.error.text)}
                    </p>
                    {ctx.state.error.retry ? (
                      <button
                        {...mergeProps({
                          type: "button",
                          disabled: ctx.locked,
                          onClick: ($event) => {
                            return ctx.retry?.($event);
                          },
                          "data-sp-b5f8ab84": "",
                        })}
                      >
                        {display(
                          ctx.waitSeconds
                            ? "Chờ " + ctx.waitSeconds + " giây"
                            : "Thử lại",
                        )}
                        <AppIcon
                          {...mergeProps({
                            name: "arrow",
                            "data-sp-b5f8ab84": "",
                          })}
                        />
                      </button>
                    ) : null}
                  </div>
                </div>
              ) : null}
              <div
                {...mergeProps({
                  className: "thread-bottom",
                  "aria-hidden": "true",
                  "data-sp-b5f8ab84": "",
                })}
              />
            </div>
            {ctx.unread ? (
              <button
                {...mergeProps({
                  type: "button",
                  className: "new-message-button",
                  onClick: ($event) => {
                    return ctx.scrollLatest?.($event);
                  },
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Tin nhắn mới "}
                <svg
                  {...mergeProps({
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "1.7",
                    "aria-hidden": "true",
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  <path
                    {...mergeProps({
                      d: "M12 4v16m-6-6 6 6 6-6",
                      "data-sp-b5f8ab84": "",
                    })}
                  />
                </svg>
              </button>
            ) : null}
          </div>
          <footer
            {...mergeProps({
              className: "composer-dock",
              "data-sp-b5f8ab84": "",
            })}
          >
            <form
              {...mergeProps({
                className: "chat-composer",
                "aria-busy": ctx.state.busy,
                onSubmit: ($event) => {
                  $event.preventDefault();
                  return ctx.submit?.($event);
                },
                "data-sp-b5f8ab84": "",
              })}
            >
              <label
                {...mergeProps({
                  className: "sr-only",
                  htmlFor: "chat-question",
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Câu hỏi của bạn"}
              </label>
              <div
                {...mergeProps({
                  className: "composer-field",
                  "data-sp-b5f8ab84": "",
                })}
              >
                <textarea
                  {...mergeProps(
                    {
                      id: "chat-question",
                      ref: bindRef(ctx, "input"),
                      disabled: ctx.locked,
                      rows: "1",
                      maxLength: "2000",
                      required: true,
                      placeholder: "Nhắn tin cho SmartProp AI...",
                      "aria-describedby": "chat-input-hint",
                      onKeyDown: ($event) => {
                        if ($event.key !== "Enter") return;
                        return ctx.keydown?.($event);
                      },
                      "data-sp-b5f8ab84": "",
                    },
                    modelProps(
                      ctx.draft,
                      ($value) => {
                        ctx.draft = $value;
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
                {ctx.draft.length > 1700 ? (
                  <span
                    {...mergeProps({
                      className: "input-count",
                      "aria-hidden": "true",
                      "data-sp-b5f8ab84": "",
                    })}
                  >
                    {display(ctx.draft.length)}
                    {"/2.000"}
                  </span>
                ) : null}
              </div>
              <button
                {...mergeProps({
                  type: "submit",
                  className: "send-button",
                  disabled: ctx.locked || !ctx.draft.trim(),
                  "aria-label": ctx.state.busy
                    ? "Đang xử lý câu hỏi"
                    : "Gửi câu hỏi",
                  title: ctx.state.busy ? "Đang xử lý câu hỏi" : "Gửi câu hỏi",
                  "data-sp-b5f8ab84": "",
                })}
              >
                <svg
                  {...mergeProps({
                    viewBox: "0 0 24 24",
                    fill: "none",
                    stroke: "currentColor",
                    strokeWidth: "1.9",
                    strokeLinecap: "round",
                    strokeLinejoin: "round",
                    "aria-hidden": "true",
                    "data-sp-b5f8ab84": "",
                  })}
                >
                  <path
                    {...mergeProps({
                      d: "m5 12 14-8-4 16-4-6-6-2Zm6 2 8-10",
                      "data-sp-b5f8ab84": "",
                    })}
                  />
                </svg>
              </button>
            </form>
            <p
              {...mergeProps({
                id: "chat-input-hint",
                className: "composer-note",
                "data-sp-b5f8ab84": "",
              })}
            >
              <span
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Enter để gửi · Shift + Enter xuống dòng."}
              </span>
              <span
                {...mergeProps({
                  "data-sp-b5f8ab84": "",
                })}
              >
                {"Thông tin tham khảo · không thay thế kiểm tra thực tế."}
              </span>
            </p>
          </footer>
        </div>
      </div>
      <MobileDrawer
        {...mergeProps(
          {
            title: "Hội thoại và gợi ý",
            onClosed: ($event) => {
              return ctx.drawerClosed?.($event);
            },
            "data-sp-b5f8ab84": "",
          },
          {
            open: ctx.drawer,
            onUpdateOpen: ($value) => {
              ctx.drawer = $value;
            },
          },
        )}
      >
        <ChatSessionPanel
          {...mergeProps({
            preview: ctx.preview,
            locked: ctx.locked,
            onChoose: ($event) => {
              return ctx.choose?.($event);
            },
            onCurrent: ($event) => {
              return ctx.currentConversation?.($event);
            },
            "data-sp-b5f8ab84": "",
          })}
        />
      </MobileDrawer>
    </section>,
  ]);
});
