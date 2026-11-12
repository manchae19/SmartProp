import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { api, session } from "../auth/api.js";
import { useList } from "../../shared/hooks/useList.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import { states } from "../property/property.js";
import { date } from "../property/property.js";
import "./UsersView.css";
function useUsersViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const state = useList("/admin/users"),
    [target] = useState(() => createStateStore(null)),
    [reason] = useState(() => createStateStore("")),
    getUsersList = () => _stateLatest.current.items.map(u => ({
      ...u,
      name: u.fullName,
      avatarLetter: u.fullName.slice(0, 1),
      roleText: u.role,
      roleClass: u.role === "ADMIN" ? "role-admin" : "role-user",
      postsCount: "—",
      statusText: states[u.status],
      statusClass: u.status === "LOCKED" ? "status-locked" : "status-active",
      joinedDate: date(u.createdAt),
      isLocked: u.status === "LOCKED"
    }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  useSyncExternalStore(reason.subscribe, reason.getSnapshot);
  useSyncExternalStore(target.subscribe, target.getSnapshot);
  function toggleLockUser(id) {
    target.set(_stateLatest.current.items.find(u => u.id === id));
    reason.set("");
  }
  async function saveStatus() {
    if (!reason.getSnapshot().trim()) {
      _stateLatest.current.updateState(draftValue => draftValue["error"] = "Nhập lý do thay đổi trạng thái.");
      return;
    }
    await _stateLatest.current.run(async () => {
      await api("/admin/users/" + target.getSnapshot().id + "/status", {
        method: "PATCH",
        body: {
          status: target.getSnapshot().status === "LOCKED" ? "ACTIVE" : "LOCKED",
          reason: reason.getSnapshot()
        }
      });
      target.set(null);
      await _stateLatest.current.load(_stateLatest.current.page);
    });
  }
  return {
    ...inputProps,
    state,
    target: target.getSnapshot(),
    reason: reason.getSnapshot(),
    usersList: getUsersList(),
    toggleLockUser,
    saveStatus,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateReasonValue: reason.set
  };
}
export default React.forwardRef(function UsersView(props, ref) {
  const view = useUsersViewState(props, ref);
  return <><div data-ui-view="UsersView" data-sp-a71debef="" {...view.rootAttributes} className={classNames(["main", view.rootAttributes.className])}>
      <ResourceState state={view.state} data-sp-a71debef="" />
      <div className="section-title" data-sp-a71debef="">
        <div className="danh-s-ch-ng-i-d-ng" data-sp-a71debef="">
          {"Danh sách người dùng"}
        </div>
      </div>
      <div className="users-list" data-sp-a71debef="">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.usersList, user => <div key={user.id} className="user-card" data-sp-a71debef="">
            <div className="user-avatar" data-sp-a71debef="">
              <div className="avatar-letter" data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.avatarLetter)}
              </div>
            </div>
            <div className="user-info" data-sp-a71debef="">
              <div className="user-name" data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.name)}
              </div>
              <div className="user-email" data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.email)}
              </div>
            </div>
            <div className={classNames(["user-role", user.roleClass])} data-sp-a71debef="">
              <div className="role-text" data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.roleText)}
              </div>
            </div>
            <div className="user-posts-count" data-sp-a71debef="">
              <div className="posts-text" data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.postsCount)}
              </div>
            </div>
            <div className={classNames(["user-status", user.statusClass])} data-sp-a71debef="">
              <div className="status-text" data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.statusText)}
              </div>
            </div>
            <div className="user-joined-date" data-sp-a71debef="">
              <div className="joined-text" data-sp-a71debef="">
                {"Tham gia "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.joinedDate)}
              </div>
            </div>
            <div className="user-actions" data-sp-a71debef="">
              <button className={classNames(user.isLocked ? "btn-unlock" : "btn-lock")} onClick={$event => {
              view.toggleLockUser(user.id);
            }} data-sp-a71debef="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(user.isLocked ? "Mở khóa" : "Khóa tài khoản")}
              </button>
            </div>
          </div>)}
      </div>
    </div>{view.target ? <section className="bg-brand-card rounded-2xl p-6" data-sp-a71debef="">
        <h3 data-sp-a71debef="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.target.fullName)}
        </h3>
        <label className="block text-xs mt-3" data-sp-a71debef="">
          {"Lý do"}
          <textarea maxLength="4000" className="block w-full border rounded-xl p-3 my-3" data-sp-a71debef="" value={view.reason ?? ""} onChange={event => ($value => {
          view.updateReasonValue($value);
        })(event.target.value)} />
        </label>
        <button onClick={$event => {
        return view.saveStatus?.($event);
      }} className="bg-[var(--ui-soft)] text-brand-navy rounded-full px-5 py-2 text-xs" data-sp-a71debef="">
          {"Xác nhận"}
        </button>
      </section> : null}<Pagination state={view.state} data-sp-a71debef="" {...view.rootAttributes} /></>;
});
