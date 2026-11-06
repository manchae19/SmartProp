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
import { ref } from "../../shared/state/store.js";
import { api, errorText } from "../auth/api.js";
import { states, reasons, date, validateFiles } from "../property/property.js";
function setup(__props) {
  const props = propsForSetup(__props, {
    report: Object,
    admin: Boolean,
  });
  const emit = emitForProps(__props, ["updated"]);
  const busy = ref(false),
    error = ref("");
  async function attach(event) {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    busy.value = true;
    error.value = "";
    try {
      validateFiles([file], true);
      const data = new FormData();
      data.append("file", file);
      emit(
        "updated",
        await api("/reports/" + props.report.id + "/attachments", {
          method: "POST",
          body: data,
        }),
      );
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  async function download(file) {
    busy.value = true;
    error.value = "";
    let url;
    try {
      const blob = await api(file.url.replace(/^\/api\/v1/, ""), {
        responseType: "blob",
      });
      url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download =
        "bang-chung-" +
        file.id +
        ({
          "image/png": ".png",
          "image/jpeg": ".jpg",
          "application/pdf": ".pdf",
        }[file.mimeType] || "");
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busy.value = false;
    }
  }
  return {
    ref,
    api,
    errorText,
    states,
    reasons,
    date,
    validateFiles,
    props,
    emit,
    busy,
    error,
    attach,
    download,
  };
}
export default React.forwardRef(function ReportDetails(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        className: "sp-panel",
      })}
    >
      <h2 {...mergeProps({})}>
        {display(ctx.reasons[ctx.report.reasonCode] || ctx.report.reasonCode)}
      </h2>
      <p
        {...mergeProps({
          className: "sp-muted",
        })}
      >
        {"Mã báo cáo: "}
        {display(ctx.report.id)}
        {" · "}
        {display(ctx.date(ctx.report.createdAt))}
      </p>
      <span
        {...mergeProps({
          className: "sp-tag",
        })}
      >
        {display(ctx.states[ctx.report.status])}
      </span>
      <p
        {...mergeProps({
          className: "sp-pre",
        })}
      >
        {display(ctx.report.description)}
      </p>
      {ctx.report.contactEmail ? (
        <p {...mergeProps({})}>
          {"Email liên hệ: "}
          {display(ctx.report.contactEmail)}
        </p>
      ) : null}
      {ctx.report.resolutionNote ? (
        <p
          {...mergeProps({
            className: "sp-pre",
          })}
        >
          {"Kết quả xử lý: "}
          {display(ctx.report.resolutionNote)}
          {" · "}
          {display(ctx.date(ctx.report.resolvedAt))}
        </p>
      ) : null}
      <h3 {...mergeProps({})}>{"Bằng chứng"}</h3>
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className: "sp-error",
          })}
        >
          {display(ctx.error)}
        </p>
      ) : null}
      <div
        {...mergeProps({
          className: "sp-row",
        })}
      >
        {renderList(ctx.report.attachments, (file, index) => (
          <button
            key={file.id}
            {...mergeProps({
              disabled: ctx.busy,
              onClick: ($event) => {
                ctx.download(file);
              },
            })}
          >
            {"Tải tệp "}
            {display(index + 1)}
            {" · "}
            {display(file.mimeType)}
            {" · "}
            {display(Math.ceil(file.byteSize / 1024))}
            {" KB"}
          </button>
        ))}
        {!ctx.report.attachments.length ? (
          <p
            {...mergeProps({
              className: "sp-muted",
            })}
          >
            {"Chưa có tệp đính kèm."}
          </p>
        ) : null}
      </div>
      {!ctx.admin && !["RESOLVED", "REJECTED"].includes(ctx.report.status) ? (
        <label
          {...mergeProps({
            className: "sp-label",
            style: "margin-top:16px",
          })}
        >
          {"Thêm bằng chứng (tối đa 10 tệp, 10 MB/tệp)"}
          <input
            {...mergeProps({
              type: "file",
              accept: "image/jpeg,image/png,application/pdf",
              disabled: ctx.busy || ctx.report.attachments.length >= 10,
              onChange: ($event) => {
                return ctx.attach?.($event);
              },
            })}
          />
        </label>
      ) : null}
      {ctx.$children ?? null}
    </section>,
  ]);
});
