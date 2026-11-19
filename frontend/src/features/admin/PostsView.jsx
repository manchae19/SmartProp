import { classNames, chainHandlers } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import { useAppNavigation } from "../../app/navigation.jsx";
import { api, session } from "../auth/api.js";
import { useList } from "../../shared/hooks/useList.js";
import { adapt } from "../property/listingPresentation.js";
import { money } from "../property/listingPresentation.js";
import ResourceState from "../../shared/components/ResourceState.jsx";
import Pagination from "../../shared/components/Pagination.jsx";
import PrivateImage from "../../shared/components/PrivateImage.jsx";
import { states } from "../property/property.js";
import { date } from "../property/property.js";
import "./PostsView.css";
function usePostsViewState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(session.subscribe, session.getSnapshot);
  const [statusFilter] = useState(() => createStateStore("PENDING"));
  useSyncExternalStore(statusFilter.subscribe, statusFilter.getSnapshot);
  const router = useAppNavigation(),
    state = useList("/admin/properties", () => ({
      status: statusFilter.getSnapshot()
    })),
    [selected] = useState(() => createStateStore(null)),
    [reason] = useState(() => createStateStore("")),
    getPendingPosts = () => _stateLatest.current.items.map(m => ({
      ...adapt(m),
      location: adapt(m).location,
      time: date(m.property.createdAt),
      badgeText: states[m.property.status],
      badgeClass: "badge-info"
    }));
  const _stateLatest = useRef(state);
  _stateLatest.current = state;
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  useSyncExternalStore(reason.subscribe, reason.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  const handleViewDetail = id => {
    selected.set(_stateLatest.current.items.find(m => m.property.id === id));
    reason.set("");
  };
  async function moderate(id, action) {
    if (!selected.getSnapshot() || selected.getSnapshot().property.id !== id) {
      handleViewDetail(id);
      return;
    }
    if (!reason.getSnapshot().trim()) {
      _stateLatest.current.updateState(draftValue => draftValue["error"] = "Nhập lý do trước khi xử lý.");
      return;
    }
    await _stateLatest.current.run(async () => {
      await api("/admin/properties/" + id + "/moderation", {
        method: "POST",
        body: {
          action,
          expectedVersion: selected.getSnapshot().property.contentVersion,
          reason: reason.getSnapshot()
        }
      });
      selected.set(null);
      await _stateLatest.current.load(_stateLatest.current.page);
    });
  }
  const handleApprove = id => moderate(id, "APPROVE"),
    handleReject = id => moderate(id, "REJECT");
  return {
    ...inputProps,
    money,
    states,
    statusFilter: statusFilter.getSnapshot(),
    state,
    selected: selected.getSnapshot(),
    reason: reason.getSnapshot(),
    pendingPosts: getPendingPosts(),
    handleViewDetail,
    moderate,
    handleApprove,
    handleReject,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key)))),
    updateSelectedValue: selected.set,
    updateStatusFilterValue: statusFilter.set,
    updateReasonValue: reason.set
  };
}
export default React.forwardRef(function PostsView(props, ref) {
  const view = usePostsViewState(props, ref);
  return <><div data-ui-view="PostsView" data-sp-e7925a7a="" {...view.rootAttributes} className={classNames(["main", view.rootAttributes.className])}>
      <ResourceState state={view.state} data-sp-e7925a7a="" />
      <div className="section-title" data-sp-e7925a7a="">
        <div className="_18-tin-ang-ch-duy-t" data-sp-e7925a7a="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.state.totalElements)}
          {" tin đăng"}
        </div>
      </div>
      <select className="bg-brand-card border rounded-lg p-2 text-sm" data-sp-e7925a7a="" value={view.statusFilter ?? ""} onChange={chainHandlers($event => {
        view.updateSelectedValue(null);
        view.state.load(0);
      }, event => ($value => {
        view.updateStatusFilterValue($value);
      })(event.target.value))}>
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(["PENDING", "PUBLISHED", "HIDDEN", "REJECTED", "DRAFT", "EXPIRED", "CLOSED"], key => <option key={key} value={key} data-sp-e7925a7a="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.states[key])}
            </option>)}
      </select>
      <div className="posts-list" data-sp-e7925a7a="">
        {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.pendingPosts, post => <div key={post.id} className="post-card" data-sp-e7925a7a="">
            <PrivateImage src={post.image} alt="Ảnh tin đăng" className="post-thumb object-cover" data-sp-e7925a7a="" />
            <div className="post-info" data-sp-e7925a7a="">
              <span className="listing-code" data-sp-e7925a7a="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(post.listingCode || "Chưa cấp mã")}
              </span>
              <div className="post-title" data-sp-e7925a7a="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(post.title)}
              </div>
              <div className="post-meta" data-sp-e7925a7a="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(post.location)}
                {" · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(post.price)}
                {" · gửi "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(post.time)}
              </div>
            </div>
            <div className={classNames(["post-badge", post.badgeClass])} data-sp-e7925a7a="">
              <div className="badge-text" data-sp-e7925a7a="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(post.badgeText)}
              </div>
            </div>
            <div className="post-actions" data-sp-e7925a7a="">
              {post.raw.status === "PENDING" ? <button className="btn-approve" onClick={$event => {
              view.handleApprove(post.id);
            }} data-sp-e7925a7a="">
                  {"Duyệt"}
                </button> : null}
              {post.raw.status === "PENDING" ? <button className="btn-reject" onClick={$event => {
              view.handleReject(post.id);
            }} data-sp-e7925a7a="">
                  {"Từ chối"}
                </button> : null}
              {post.raw.status === "PUBLISHED" ? <button className="btn-reject" onClick={$event => {
              view.moderate(post.id, "HIDE");
            }} data-sp-e7925a7a="">
                  {"Ẩn tin"}
                </button> : null}
              {post.raw.status === "HIDDEN" ? <button className="btn-approve" onClick={$event => {
              view.moderate(post.id, "RESTORE");
            }} data-sp-e7925a7a="">
                  {"Khôi phục"}
                </button> : null}
              <button className="btn-detail" onClick={$event => {
              view.handleViewDetail(post.id);
            }} data-sp-e7925a7a="">
                {"Xem chi tiết ›"}
              </button>
            </div>
          </div>)}
      </div>
    </div>{view.selected ? <section className="bg-brand-card rounded-2xl p-6" data-sp-e7925a7a="">
        <p className="listing-code" data-sp-e7925a7a="">
          {"Mã tin: "}
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.listingCode || "Chưa cấp mã")}
        </p>
        <h3 className="font-semibold" data-sp-e7925a7a="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.title)}
        </h3>
        <p className="text-xs py-3 whitespace-pre-wrap" data-sp-e7925a7a="">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.description)}
        </p>
        <dl className="grid gap-2 text-sm mb-4" data-sp-e7925a7a="">
          <div data-sp-e7925a7a="">
            {"Người đăng: #"}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.ownerId)}
          </div>
          <div data-sp-e7925a7a="">
            {"Giá: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.money(view.selected.property))}
            {" · Diện tích: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.areaSqm)}
            {" m²"}
          </div>
          <div data-sp-e7925a7a="">
            {"Địa chỉ: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.address)}
            {", "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.district)}
            {", "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.city)}
          </div>
          <div data-sp-e7925a7a="">
            {"Vị trí: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.latitude)}
            {", "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.property.longitude)}
          </div>
          <div data-sp-e7925a7a="">
            {"Liên hệ khai báo: "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.contactName)}
            {" · "}
            {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.selected.contactPhone)}
          </div>
        </dl>
        <div className="grid grid-cols-3 gap-3" data-sp-e7925a7a="">
          {((items, render) => typeof items === "number" ? Array.from({
          length: Math.max(0, items)
        }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.selected.property.images, image => <PrivateImage key={image.id} src={image.url} alt="Ảnh tin chờ duyệt" className="h-32 w-full object-cover rounded-xl" data-sp-e7925a7a="" />)}
        </div>
        <label className="block text-xs mt-4" data-sp-e7925a7a="">
          {"Lý do"}
          <textarea className="w-full mt-2 p-3 border rounded-xl" maxLength="4000" data-sp-e7925a7a="" value={view.reason ?? ""} onChange={event => ($value => {
          view.updateReasonValue($value);
        })(event.target.value)} />
        </label>
        {view.selected.property.status === "PENDING" ? <button className="px-4 py-2 rounded-full bg-[var(--ui-soft)] text-brand-navy text-xs" onClick={$event => {
        view.handleApprove(view.selected.property.id);
      }} data-sp-e7925a7a="">
            {"Duyệt tin"}
          </button> : null}
        {view.selected.property.status === "PENDING" ? <button className="px-4 py-2 rounded-full border ml-2 text-xs" onClick={$event => {
        view.handleReject(view.selected.property.id);
      }} data-sp-e7925a7a="">
            {"Từ chối"}
          </button> : null}
        {view.selected.property.status === "PUBLISHED" ? <button className="px-4 py-2 rounded-full border text-xs" onClick={$event => {
        view.moderate(view.selected.property.id, "HIDE");
      }} data-sp-e7925a7a="">
            {"Ẩn tin"}
          </button> : null}
        {view.selected.property.status === "HIDDEN" ? <button className="px-4 py-2 rounded-full border text-xs" onClick={$event => {
        view.moderate(view.selected.property.id, "RESTORE");
      }} data-sp-e7925a7a="">
            {"Khôi phục"}
          </button> : null}
      </section> : null}<Pagination state={view.state} data-sp-e7925a7a="" {...view.rootAttributes} /></>;
});
