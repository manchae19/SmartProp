import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useRef, useState, useSyncExternalStore, useEffect } from "react";
import { avatar, uploadAvatar, removeAvatar, validateAvatar, loadAvatar } from "./avatar.js";
import { errorText } from "../auth/api.js";
import AppIcon from "../../shared/components/AppIcon.jsx";
function useAvatarEditorState(inputProps, forwardedRef) {
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  useSyncExternalStore(avatar.subscribe, avatar.getSnapshot);
  const [picker] = useState(() => createStateStore(null)),
    [selected] = useState(() => createStateStore(null)),
    [preview] = useState(() => createStateStore("")),
    [busy] = useState(() => createStateStore(false)),
    [error] = useState(() => createStateStore("")),
    [message] = useState(() => createStateStore(""));
  useSyncExternalStore(message.subscribe, message.getSnapshot);
  useSyncExternalStore(error.subscribe, error.getSnapshot);
  useSyncExternalStore(busy.subscribe, busy.getSnapshot);
  useSyncExternalStore(preview.subscribe, preview.getSnapshot);
  useSyncExternalStore(selected.subscribe, selected.getSnapshot);
  useSyncExternalStore(picker.subscribe, picker.getSnapshot);
  const _revisionRef = useRef(0);
  function reset() {
    _revisionRef.current++;
    selected.set(null);
    if (preview.getSnapshot()) URL.revokeObjectURL(preview.getSnapshot());
    preview.set("");
    if (picker.getSnapshot()) picker.edit(draftValue => draftValue["value"] = "");
  }
  async function choose(event) {
    const file = event.target.files?.[0];
    reset();
    error.set(message.set(""));
    if (!file) return;
    const run = _revisionRef.current;
    try {
      await validateAvatar(file);
      if (run !== _revisionRef.current) return;
      selected.set(file);
      preview.set(URL.createObjectURL(file));
    } catch (e) {
      error.set(e.message);
    }
  }
  async function save() {
    if (!selected.getSnapshot() || busy.getSnapshot()) return;
    busy.set(true);
    error.set("");
    try {
      await uploadAvatar(selected.getSnapshot());
      reset();
      message.set("Đã cập nhật ảnh đại diện.");
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  async function remove() {
    if (busy.getSnapshot()) return;
    busy.set(true);
    error.set("");
    try {
      await removeAvatar();
      reset();
      message.set("Đã trở về ảnh đại diện mặc định.");
    } catch (e) {
      error.set(errorText(e));
    } finally {
      busy.set(false);
    }
  }
  useEffect(() => () => reset(), []);
  return {
    ...inputProps,
    avatar: avatar.getSnapshot(),
    loadAvatar,
    picker: picker.getSnapshot(),
    preview: preview.getSnapshot(),
    busy: busy.getSnapshot(),
    error: error.getSnapshot(),
    message: message.getSnapshot(),
    reset,
    choose,
    save,
    remove,
    updatePickerValue: picker.set,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function AvatarEditor(props, ref) {
  const view = useAvatarEditorState(props, ref);
  return <><div {...view.rootAttributes} className={classNames(["avatar-editor", view.rootAttributes.className])}>
      <input ref={view.updatePickerValue} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Chọn ảnh đại diện" disabled={!view.avatar.enabled || view.busy} onChange={$event => {
        return view.choose?.($event);
      }} />
      <button type="button" className="sp-button sp-button-secondary w-full" disabled={!view.avatar.enabled || view.busy || view.avatar.loading} onClick={$event => {
        view.picker?.click();
      }}>
        <AppIcon name="camera" />
        {"Đổi ảnh đại diện"}
      </button>
      {view.avatar.loading ? <p className="mt-2 text-[13px] text-brand-muted" role="status">
          {"Đang tải ảnh…"}
        </p> : !view.avatar.enabled ? <p className="mt-2 max-w-64 text-[13px] leading-5 text-brand-muted">
          {"Ảnh đại diện chưa được bật trên hệ thống. "}
          {view.avatar.error ? <button type="button" className="underline" onClick={$event => {
          return view.loadAvatar?.($event);
        }}>
              {"Thử lại"}
            </button> : null}
        </p> : <p className="mt-2 max-w-64 text-[13px] leading-5 text-brand-muted">
          {"JPG, PNG hoặc WebP · tối đa 5 MB."}
        </p>}
      {view.preview ? <div className="mt-4 rounded-2xl border border-brand-line bg-brand-surface p-4">
          <img src={view.preview} alt="Xem trước ảnh đại diện mới" className="mx-auto size-28 rounded-full object-cover" />
          <p className="mt-3 text-center text-[13px]">
            {"Xem trước · ảnh được cắt vuông ở giữa."}
          </p>
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <button type="button" className="sp-button sp-button-primary" disabled={view.busy} onClick={$event => {
            return view.save?.($event);
          }}>
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.busy ? "Đang lưu…" : "Lưu ảnh")}
            </button>
            <button type="button" className="sp-button sp-button-secondary" disabled={view.busy} onClick={$event => {
            return view.reset?.($event);
          }}>
              {"Hủy"}
            </button>
          </div>
        </div> : null}
      {view.avatar.available && !view.preview ? <button type="button" className="mt-3 text-[13px] text-brand-muted underline" disabled={view.busy} onClick={$event => {
        return view.remove?.($event);
      }}>
          {"Xóa ảnh đại diện"}
        </button> : null}
      {view.error ? <p role="alert" className="mt-3 max-w-72 text-sm leading-6 text-[var(--ui-error-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.error)}
        </p> : null}
      {view.message ? <p role="status" className="mt-3 max-w-72 text-sm leading-6 text-[var(--ui-success-text)]">
          {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(view.message)}
        </p> : null}
    </div></>;
});
