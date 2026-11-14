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
import { ref, onBeforeUnmount } from "../../shared/state/store.js";
import {
  avatar,
  uploadAvatar,
  removeAvatar,
  validateAvatar,
  loadAvatar,
} from "./avatar.js";
import { errorText } from "../auth/api.js";
import AppIcon from "../../shared/components/AppIcon.jsx";
function setup(__props) {
  const picker = ref(null),
    selected = ref(null),
    preview = ref(""),
    busy = ref(false),
    error = ref(""),
    message = ref("");
  let revision = 0;
  function reset() {
    revision++;
    selected.value = null;
    if (preview.value) URL.revokeObjectURL(preview.value);
    preview.value = "";
    if (picker.value) picker.value.value = "";
  }
  async function choose(event) {
    const file = event.target.files?.[0];
    reset();
    error.value = message.value = "";
    if (!file) return;
    const run = revision;
    try {
      await validateAvatar(file);
      if (run !== revision) return;
      selected.value = file;
      preview.value = URL.createObjectURL(file);
    } catch (e) {
      error.value = e.message;
    }
  }
  async function save() {
    if (!selected.value || busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      await uploadAvatar(selected.value);
      reset();
      message.value = "Đã cập nhật ảnh đại diện.";
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  async function remove() {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    try {
      await removeAvatar();
      reset();
      message.value = "Đã trở về ảnh đại diện mặc định.";
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  onBeforeUnmount(reset);
  return {
    ref,
    onBeforeUnmount,
    avatar,
    uploadAvatar,
    removeAvatar,
    validateAvatar,
    loadAvatar,
    errorText,
    AppIcon,
    picker,
    selected,
    preview,
    busy,
    error,
    message,
    revision,
    reset,
    choose,
    save,
    remove,
  };
}
export default React.forwardRef(function AvatarEditor(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "avatar-editor",
      })}
    >
      <input
        {...mergeProps({
          ref: bindRef(ctx, "picker"),
          type: "file",
          accept: "image/jpeg,image/png,image/webp",
          className: "sr-only",
          "aria-label": "Chọn ảnh đại diện",
          disabled: !ctx.avatar.enabled || ctx.busy,
          onChange: ($event) => {
            return ctx.choose?.($event);
          },
        })}
      />
      <button
        {...mergeProps({
          type: "button",
          className: "sp-button sp-button-secondary w-full",
          disabled: !ctx.avatar.enabled || ctx.busy || ctx.avatar.loading,
          onClick: ($event) => {
            ctx.picker?.click();
          },
        })}
      >
        <AppIcon
          {...mergeProps({
            name: "camera",
          })}
        />
        {"Đổi ảnh đại diện"}
      </button>
      {ctx.avatar.loading ? (
        <p
          {...mergeProps({
            className: "mt-2 text-[13px] text-brand-muted",
            role: "status",
          })}
        >
          {"Đang tải ảnh…"}
        </p>
      ) : !ctx.avatar.enabled ? (
        <p
          {...mergeProps({
            className: "mt-2 max-w-64 text-[13px] leading-5 text-brand-muted",
          })}
        >
          {"Ảnh đại diện chưa được bật trên hệ thống. "}
          {ctx.avatar.error ? (
            <button
              {...mergeProps({
                type: "button",
                className: "underline",
                onClick: ($event) => {
                  return ctx.loadAvatar?.($event);
                },
              })}
            >
              {"Thử lại"}
            </button>
          ) : null}
        </p>
      ) : (
        <p
          {...mergeProps({
            className: "mt-2 max-w-64 text-[13px] leading-5 text-brand-muted",
          })}
        >
          {"JPG, PNG hoặc WebP · tối đa 5 MB."}
        </p>
      )}
      {ctx.preview ? (
        <div
          {...mergeProps({
            className:
              "mt-4 rounded-2xl border border-brand-line bg-brand-surface p-4",
          })}
        >
          <img
            {...mergeProps({
              src: ctx.preview,
              alt: "Xem trước ảnh đại diện mới",
              className: "mx-auto size-28 rounded-full object-cover",
            })}
          />
          <p
            {...mergeProps({
              className: "mt-3 text-center text-[13px]",
            })}
          >
            {"Xem trước · ảnh được cắt vuông ở giữa."}
          </p>
          <div
            {...mergeProps({
              className: "mt-3 flex flex-wrap justify-center gap-2",
            })}
          >
            <button
              {...mergeProps({
                type: "button",
                className: "sp-button sp-button-primary",
                disabled: ctx.busy,
                onClick: ($event) => {
                  return ctx.save?.($event);
                },
              })}
            >
              {display(ctx.busy ? "Đang lưu…" : "Lưu ảnh")}
            </button>
            <button
              {...mergeProps({
                type: "button",
                className: "sp-button sp-button-secondary",
                disabled: ctx.busy,
                onClick: ($event) => {
                  return ctx.reset?.($event);
                },
              })}
            >
              {"Hủy"}
            </button>
          </div>
        </div>
      ) : null}
      {ctx.avatar.available && !ctx.preview ? (
        <button
          {...mergeProps({
            type: "button",
            className: "mt-3 text-[13px] text-brand-muted underline",
            disabled: ctx.busy,
            onClick: ($event) => {
              return ctx.remove?.($event);
            },
          })}
        >
          {"Xóa ảnh đại diện"}
        </button>
      ) : null}
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className: "mt-3 max-w-72 text-sm leading-6 text-[var(--ui-error-text)]",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      {ctx.message ? (
        <p
          {...mergeProps({
            role: "status",
            className: "mt-3 max-w-72 text-sm leading-6 text-[var(--ui-success-text)]",
          })}
        >
          {display(ctx.message)}
        </p>
      ) : null}
    </div>,
  ]);
});
