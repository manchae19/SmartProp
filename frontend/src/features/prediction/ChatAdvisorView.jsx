import { afterPaint, classNames, inlineStyle } from "../../shared/lib/ui.js";
import { createStateStore, stateKey } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { chatSession } from "./chatRuntime.js";
import { isNearChatBottom } from "./chatPresentation.js";
import ChatAnswer from "../../shared/components/ChatAnswer.jsx";
import ChatSessionPanel from "../../shared/components/ChatSessionPanel.jsx";
import MobileDrawer from "../../shared/components/layout/MobileDrawer.jsx";
import AppIcon from "../../shared/components/AppIcon.jsx";
import "./ChatAdvisorView.css";
function useChatAdvisorViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(chatSession.subscribe, chatSession.getSnapshot);
  const {
    state
  } = chatSession.getSnapshot();
  const [draft] = useState(() => createStateStore("")),
    [input] = useState(() => createStateStore(null)),
    [thread] = useState(() => createStateStore(null)),
    [clock] = useState(() => createStateStore(Date.now())),
    [viewportHeight] = useState(() => createStateStore(null));
  useSyncExternalStore(viewportHeight.subscribe, viewportHeight.getSnapshot);
  useSyncExternalStore(clock.subscribe, clock.getSnapshot);
  useSyncExternalStore(thread.subscribe, thread.getSnapshot);
  useSyncExternalStore(input.subscribe, input.getSnapshot);
  useSyncExternalStore(draft.subscribe, draft.getSnapshot);
  const [sidebar] = useState(() => createStateStore(true)),
    [drawer] = useState(() => createStateStore(false)),
    [smallScreen] = useState(() => createStateStore(false)),
    [menuButton] = useState(() => createStateStore(null));
  useSyncExternalStore(menuButton.subscribe, menuButton.getSnapshot);
  useSyncExternalStore(smallScreen.subscribe, smallScreen.getSnapshot);
  useSyncExternalStore(drawer.subscribe, drawer.getSnapshot);
  useSyncExternalStore(sidebar.subscribe, sidebar.getSnapshot);
  const [follow] = useState(() => createStateStore(true)),
    [unread] = useState(() => createStateStore(false));
  useSyncExternalStore(unread.subscribe, unread.getSnapshot);
  useSyncExternalStore(follow.subscribe, follow.getSnapshot);
  const _focusAfterDrawerRef = useRef("menu");
  const _timerRef = useRef(undefined),
    _mediaRef = useRef(undefined);
  const getElapsed = () => Math.max(0, Math.floor((clock.getSnapshot() - chatSession.getSnapshot().state.startedAt) / 1000));
  const getWaitSeconds = () => Math.max(0, Math.ceil((chatSession.getSnapshot().state.retryAt - clock.getSnapshot()) / 1000));
  const getLocked = () => chatSession.getSnapshot().state.busy || getWaitSeconds() > 0;
  const getPreview = () => chatSession.getSnapshot().state.messages.findLast(m => m.role === "user")?.text || "";
  function resizeInput() {
    if (!input.getSnapshot()) return;
    input.edit(draftValue => draftValue["style"]["height"] = "auto");
    input.edit(draftValue => draftValue["style"]["height"] = Math.min(128, input.getSnapshot().scrollHeight) + "px");
    input.edit(draftValue => draftValue["style"]["overflowY"] = input.getSnapshot().scrollHeight > 128 ? "auto" : "hidden");
  }
  function scrollLatest() {
    follow.set(true);
    unread.set(false);
    if (thread.getSnapshot()) thread.edit(draftValue => draftValue["scrollTop"] = thread.getSnapshot().scrollHeight);
  }
  function onScroll() {
    follow.set(isNearChatBottom(thread.getSnapshot()));
    if (follow.getSnapshot()) unread.set(false);
  }
  function reading() {
    follow.set(false);
  }
  function answerResized() {
    if (follow.getSnapshot()) afterPaint(scrollLatest);else unread.set(true);
  }
  function questionFor(messageId) {
    const index = chatSession.getSnapshot().state.messages.findIndex(m => m.id === messageId);
    return chatSession.getSnapshot().state.messages.slice(0, index).findLast(m => m.role === "user")?.text || "";
  }
  function syncViewport() {
    if (typeof window === "undefined") return;
    const view = window.visualViewport;
    const top = document.querySelector(".app-header")?.getBoundingClientRect().bottom || 0;
    // visualViewport follows the mobile keyboard; composer stays inside the visible frame.
    viewportHeight.set(Math.max(180, (view?.height || window.innerHeight) - Math.max(0, top - (view?.offsetTop || 0))));
    if (follow.getSnapshot()) afterPaint(scrollLatest);
  }
  function screenChanged() {
    smallScreen.set(_mediaRef.current.matches);
    if (!_mediaRef.current.matches) drawer.set(false);
    syncViewport();
  }
  function togglePanel() {
    if (smallScreen.getSnapshot()) {
      _focusAfterDrawerRef.current = "menu";
      drawer.set(true);
    } else sidebar.set(!sidebar.getSnapshot());
  }
  async function drawerClosed() {
    await afterPaint();
    (_focusAfterDrawerRef.current === "input" ? input.getSnapshot() : menuButton.getSnapshot())?.focus({
      preventScroll: true
    });
  }
  async function choose(question) {
    if (getLocked()) return;
    draft.set(question);
    _focusAfterDrawerRef.current = "input";
    drawer.set(false);
    await afterPaint();
    resizeInput();
    input.getSnapshot()?.focus();
  }
  function currentConversation() {
    _focusAfterDrawerRef.current = "input";
    drawer.set(false);
    afterPaint(() => input.getSnapshot()?.focus());
  }
  function newConversation() {
    if (getLocked()) return;
    chatSession.getSnapshot().clear();
    draft.set("");
    scrollLatest();
    afterPaint(() => {
      resizeInput();
      input.getSnapshot()?.focus();
    });
  }
  async function submit() {
    if (getLocked() || !draft.getSnapshot().trim()) return;
    follow.set(true);
    const pending = chatSession.getSnapshot().submit(draft.getSnapshot());
    if (chatSession.getSnapshot().state.busy) draft.set("");
    await afterPaint();
    resizeInput();
    scrollLatest();
    await pending;
  }
  async function quickReply(question) {
    await choose(question);
    await submit();
  }
  function retry() {
    if (getLocked()) return;
    follow.set(true);
    chatSession.getSnapshot().retry();
  }
  function keydown(event) {
    if (!event.shiftKey && !event.isComposing) {
      event.preventDefault();
      submit();
    }
  }
  const _watched = draft.getSnapshot();
  const _previous = useRef(_watched),
    _initialized = useRef(false);
  useEffect(() => {
    const previousValue = _previous.current;
    _previous.current = _watched;
    let dispose;
    if (!_initialized.current) {
      _initialized.current = true;
      return;
    }
    const result = (() => afterPaint(resizeInput))(_watched, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched)]);
  const _watched2 = (() => [chatSession.getSnapshot().state.messages.length, chatSession.getSnapshot().state.busy, chatSession.getSnapshot().state.error])();
  const _previous2 = useRef(_watched2),
    _initialized2 = useRef(false);
  useEffect(() => {
    const previousValue = _previous2.current;
    _previous2.current = _watched2;
    let dispose;
    if (!_initialized2.current) {
      _initialized2.current = true;
      return;
    }
    const result = (async () => {
      const shouldFollow = follow.getSnapshot();
      await afterPaint();
      if (shouldFollow) scrollLatest();else unread.set(true);
    })(_watched2, previousValue, fn => dispose = fn);
    result?.catch?.(console.error);
    return () => dispose?.();
  }, [stateKey(_watched2)]);
  useEffect(() => {
    const result = (() => {
      _timerRef.current = setInterval(() => {
        clock.set(Date.now());
      }, 1000);
      _mediaRef.current = window.matchMedia("(max-width: 760px)");
      screenChanged();
      _mediaRef.current.addEventListener("change", screenChanged);
      window.addEventListener("resize", syncViewport);
      window.visualViewport?.addEventListener("resize", syncViewport);
      window.visualViewport?.addEventListener("scroll", syncViewport);
      afterPaint(() => {
        resizeInput();
        scrollLatest();
      });
    })();
    if (result && typeof result.then === "function") result.catch(console.error);
    return typeof result === "function" ? result : undefined;
  }, []);
  useEffect(() => () => (() => {
    clearInterval(_timerRef.current);
    _mediaRef.current?.removeEventListener("change", screenChanged);
    window.removeEventListener("resize", syncViewport);
    window.visualViewport?.removeEventListener("resize", syncViewport);
    window.visualViewport?.removeEventListener("scroll", syncViewport);
  })(), []);
  return {
    ...inputProps,
    state: chatSession.getSnapshot().state,
    draft: draft.getSnapshot(),
    viewportHeight: viewportHeight.getSnapshot(),
    sidebar: sidebar.getSnapshot(),
    drawer: drawer.getSnapshot(),
    smallScreen: smallScreen.getSnapshot(),
    unread: unread.getSnapshot(),
    elapsed: getElapsed(),
    waitSeconds: getWaitSeconds(),
    locked: getLocked(),
    preview: getPreview(),
    scrollLatest,
    onScroll,
    reading,
    answerResized,
    questionFor,
    togglePanel,
    drawerClosed,
    choose,
    currentConversation,
    newConversation,
    submit,
    quickReply,
    retry,
    keydown,
    updateInputValue: input.set,
    updateThreadValue: thread.set,
    updateMenuButtonValue: menuButton.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateDraftValue: draft.set,
    updateDrawerValue: drawer.set
  };
}
export default React.forwardRef(function ChatAdvisorView(props, ref) {
  const view = useChatAdvisorViewState(props, ref);
  return <><section data-ui-view="ChatAdvisorView" aria-labelledby="chat-title" style={inlineStyle(view.viewportHeight ? {
      height: view.viewportHeight + "px"
    } : undefined)} data-sp-b5f8ab84="" {...view.rootAttributes} className={classNames(["messenger-page", view.rootAttributes.className])}>
      <div className={classNames(["messenger-shell", {
        "sidebar-collapsed": !view.sidebar
      }])} data-sp-b5f8ab84="">
        {view.sidebar ? <aside className="desktop-chat-panel" aria-label="Hội thoại trong tab" data-sp-b5f8ab84="">
            <div className="panel-title" data-sp-b5f8ab84="">
              <h2 data-sp-b5f8ab84="">
                {"Tin nhắn"}
              </h2>
              <span data-sp-b5f8ab84="">
                {"SmartProp"}
              </span>
            </div>
            <ChatSessionPanel preview={view.preview} locked={view.locked} onChoose={$event => {
            return view.choose?.($event);
          }} onCurrent={$event => {
            return view.currentConversation?.($event);
          }} data-sp-b5f8ab84="" />
          </aside> : null}
        <div className="conversation" data-sp-b5f8ab84="">
          <header className="conversation-header" data-sp-b5f8ab84="">
            <button ref={view.updateMenuButtonValue} type="button" className="chat-icon-button panel-toggle" aria-label={view.smallScreen ? "Mở hội thoại và gợi ý" : view.sidebar ? "Thu gọn danh sách hội thoại" : "Mở danh sách hội thoại"} aria-expanded={view.smallScreen ? view.drawer : view.sidebar} onClick={$event => {
              return view.togglePanel?.($event);
            }} data-sp-b5f8ab84="">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true" data-sp-b5f8ab84="">
                <rect x="3" y="4" width="18" height="16" rx="3" data-sp-b5f8ab84="" />
                <path d="M9 4v16" data-sp-b5f8ab84="" />
              </svg>
            </button>
            <span className="conversation-avatar" aria-hidden="true" data-sp-b5f8ab84="">
              {"S"}
              <span data-sp-b5f8ab84="">
                {"AI"}
              </span>
            </span>
            <div className="conversation-name" data-sp-b5f8ab84="">
              <h1 id="chat-title" data-sp-b5f8ab84="">
                {"SmartProp AI Advisor"}
              </h1>
              <p data-sp-b5f8ab84="">
                {"Trợ lý tư vấn bất động sản"}
              </p>
            </div>
            <button type="button" className="chat-icon-button new-chat" disabled={view.locked || !view.state.messages.length} aria-label="Tạo hội thoại mới" title="Bắt đầu lại sẽ xóa hội thoại hiện tại trong tab" onClick={$event => {
              return view.newConversation?.($event);
            }} data-sp-b5f8ab84="">
              <AppIcon name="edit" data-sp-b5f8ab84="" />
              <span data-sp-b5f8ab84="">
                {"Hội thoại mới"}
              </span>
            </button>
          </header>
          <div className="thread-host" data-sp-b5f8ab84="">
            <div ref={view.updateThreadValue} className="chat-thread" role="log" aria-labelledby="chat-title" aria-live="polite" aria-relevant="additions" aria-busy={view.state.busy} tabIndex="0" onScroll={$event => {
              return view.onScroll?.($event);
            }} data-sp-b5f8ab84="">
              <div className="thread-date" data-sp-b5f8ab84="">
                <span data-sp-b5f8ab84="">
                  {"Hội thoại trong tab này"}
                </span>
              </div>
              {!view.state.messages.length ? <div className="chat-welcome" data-sp-b5f8ab84="">
                  <span className="welcome-avatar" aria-hidden="true" data-sp-b5f8ab84="">
                    {"S"}
                  </span>
                  <h2 data-sp-b5f8ab84="">
                    {"Chào bạn, mình là SmartProp."}
                  </h2>
                  <p data-sp-b5f8ab84="">
                    {"Bạn đang tìm một nơi để ở hay muốn khám phá khu vực? Hãy bắt đầu từ ngân sách và nhu cầu của bạn."}
                  </p>
                  <div className="welcome-prompts" data-sp-b5f8ab84="">
                    <button type="button" disabled={view.locked} onClick={$event => {
                    view.choose("Tôi có 10 tỷ, gợi ý bất động sản phù hợp.");
                  }} data-sp-b5f8ab84="">
                      {"Tìm BĐS theo ngân sách"}
                      <AppIcon name="arrow" data-sp-b5f8ab84="" />
                    </button>
                    <button type="button" disabled={view.locked} onClick={$event => {
                    view.choose("Ở Hải Châu có những bệnh viện nào?");
                  }} data-sp-b5f8ab84="">
                      {"Hỏi tiện ích khu vực"}
                      <AppIcon name="arrow" data-sp-b5f8ab84="" />
                    </button>
                  </div>
                  <p className="welcome-note" data-sp-b5f8ab84="">
                    {"Nhập nhu cầu tìm nhà của bạn để bắt đầu."}
                  </p>
                </div> : null}
              {view.state.trimmed ? <p className="trimmed-note" data-sp-b5f8ab84="">
                  {"Đang hiển thị 24 tin nhắn gần nhất trong tab."}
                </p> : null}
              {((items, render) => typeof items === "number" ? Array.from({
                length: Math.max(0, items)
              }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.state.messages, message => <article key={message.id} className={classNames(message.role === "user" ? "user-message" : "assistant-message")} data-chat-message={message.role} data-sp-b5f8ab84="">
                  {message.role === "user" ? <React.Fragment>
                      <span className="sr-only" data-sp-b5f8ab84="">
                        {"Bạn:"}
                      </span>
                      <p className="user-bubble" data-sp-b5f8ab84="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(message.text)}
                      </p>
                    </React.Fragment> : <React.Fragment>
                      <span className="message-avatar" aria-hidden="true" data-sp-b5f8ab84="">
                        {"S"}
                      </span>
                      <div className="answer-with-actions">
                        {message.response.evidence?.needs?.summary?.length ? <aside className="chat-needs-summary" aria-label="Tiêu chí đang dùng">
                            <strong>Tiêu chí đang dùng</strong>
                            <ul>{message.response.evidence.needs.summary.map((item, index) => <li key={index}>{item}</li>)}</ul>
                            <small>Bạn có thể gõ để sửa ngân sách, khu vực hoặc thứ tự ưu tiên.</small>
                          </aside> : null}
                      <ChatAnswer result={message.response} messageId={message.id} question={view.questionFor(message.id)} onReading={$event => {
                      return view.reading?.($event);
                    }} onResized={$event => {
                      return view.answerResized?.($event);
                    }} data-sp-b5f8ab84="" />
                        {message.id === view.state.messages.at(-1)?.id && message.response.evidence?.quickReplies?.length ? <div className="chat-quick-replies" role="group" aria-label="Lựa chọn trả lời nhanh">
                            {message.response.evidence.quickReplies.map(choice => <button key={choice} type="button" disabled={view.locked} onClick={() => view.quickReply(choice)}>{choice}</button>)}
                          </div> : null}
                      </div>
                    </React.Fragment>}
                </article>)}
              {view.state.busy ? <div className="assistant-message typing-message" role="status" data-chat-loading="" data-sp-b5f8ab84="">
                  <span className="message-avatar" aria-hidden="true" data-sp-b5f8ab84="">
                    {"S"}
                  </span>
                  <div data-sp-b5f8ab84="">
                    <div className="typing-bubble" aria-hidden="true" data-sp-b5f8ab84="">
                      <i data-sp-b5f8ab84="" />
                      <i data-sp-b5f8ab84="" />
                      <i data-sp-b5f8ab84="" />
                    </div>
                    <p className="typing-label" data-sp-b5f8ab84="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.elapsed >= 30 ? "SmartProp vẫn đang xử lý. Bạn không cần gửi lại." : "SmartProp đang tìm kiếm và phân tích…")}
                    </p>
                    <span className="sr-only" data-sp-b5f8ab84="">
                      {"Câu trả lời sẽ xuất hiện khi xử lý hoàn tất."}
                    </span>
                  </div>
                </div> : null}
              {view.state.error ? <div className="assistant-message" role="alert" data-chat-error="" data-sp-b5f8ab84="">
                  <span className="message-avatar" aria-hidden="true" data-sp-b5f8ab84="">
                    {"S"}
                  </span>
                  <div className="error-bubble" data-sp-b5f8ab84="">
                    <p data-sp-b5f8ab84="">
                      {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.error.text)}
                    </p>
                    {view.state.error.retry ? <button type="button" disabled={view.locked} onClick={$event => {
                    return view.retry?.($event);
                  }} data-sp-b5f8ab84="">
                        {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.waitSeconds ? "Chờ " + view.waitSeconds + " giây" : "Thử lại")}
                        <AppIcon name="arrow" data-sp-b5f8ab84="" />
                      </button> : null}
                  </div>
                </div> : null}
              <div className="thread-bottom" aria-hidden="true" data-sp-b5f8ab84="" />
            </div>
            {view.unread ? <button type="button" className="new-message-button" onClick={$event => {
              return view.scrollLatest?.($event);
            }} data-sp-b5f8ab84="">
                {"Tin nhắn mới "}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true" data-sp-b5f8ab84="">
                  <path d="M12 4v16m-6-6 6 6 6-6" data-sp-b5f8ab84="" />
                </svg>
              </button> : null}
          </div>
          <footer className="composer-dock" data-sp-b5f8ab84="">
            <form className="chat-composer" aria-busy={view.state.busy} onSubmit={$event => {
              $event.preventDefault();
              return view.submit?.($event);
            }} data-sp-b5f8ab84="">
              <label className="sr-only" htmlFor="chat-question" data-sp-b5f8ab84="">
                {"Câu hỏi của bạn"}
              </label>
              <div className="composer-field" data-sp-b5f8ab84="">
                <textarea id="chat-question" ref={view.updateInputValue} disabled={view.locked} rows="1" maxLength="2000" required={true} placeholder="Nhắn tin cho SmartProp AI..." aria-describedby="chat-input-hint" onKeyDown={$event => {
                  if ($event.key !== "Enter") return;
                  return view.keydown?.($event);
                }} data-sp-b5f8ab84="" value={view.draft ?? ""} onChange={event => ($value => {
                  view.updateDraftValue($value);
                })(event.target.value)} />
                {view.draft.length > 1700 ? <span className="input-count" aria-hidden="true" data-sp-b5f8ab84="">
                    {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.draft.length)}
                    {"/2.000"}
                  </span> : null}
              </div>
              <button type="submit" className="send-button" disabled={view.locked || !view.draft.trim()} aria-label={view.state.busy ? "Đang xử lý câu hỏi" : "Gửi câu hỏi"} title={view.state.busy ? "Đang xử lý câu hỏi" : "Gửi câu hỏi"} data-sp-b5f8ab84="">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" data-sp-b5f8ab84="">
                  <path d="m5 12 14-8-4 16-4-6-6-2Zm6 2 8-10" data-sp-b5f8ab84="" />
                </svg>
              </button>
            </form>
            <p id="chat-input-hint" className="composer-note" data-sp-b5f8ab84="">
              <span data-sp-b5f8ab84="">
                {"Enter để gửi · Shift + Enter xuống dòng."}
              </span>
              <span data-sp-b5f8ab84="">
                {"Thông tin tham khảo · không thay thế kiểm tra thực tế."}
              </span>
            </p>
          </footer>
        </div>
      </div>
      <MobileDrawer title="Hội thoại và gợi ý" onClosed={$event => {
        return view.drawerClosed?.($event);
      }} data-sp-b5f8ab84="" open={view.drawer} onUpdateOpen={$value => {
        view.updateDrawerValue($value);
      }}>
        <ChatSessionPanel preview={view.preview} locked={view.locked} onChoose={$event => {
          return view.choose?.($event);
        }} onCurrent={$event => {
          return view.currentConversation?.($event);
        }} data-sp-b5f8ab84="" />
      </MobileDrawer>
    </section></>;
});
