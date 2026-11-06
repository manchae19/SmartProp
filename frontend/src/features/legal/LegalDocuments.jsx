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
  computed,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { api, session, errorText } from "../auth/api.js";
import "./LegalDocuments.css";
function setup(__props) {
  const props = propsForSetup(__props, {
    propertyId: {
      type: String,
      required: true,
    },
    ownerId: [Number, String],
  });
  const own = computed(
      () => String(props.ownerId) === String(session.user?.id),
    ),
    admin = computed(() => session.user?.role === "ADMIN");
  const rows = ref([]),
    busy = ref(false),
    error = ref(""),
    notice = ref(""),
    selected = ref(null),
    file = ref(null),
    reason = ref("");
  let sequence = 0;
  const blank = () => ({
      documentType: "OTHER",
      ownerName: "",
      documentNumber: "",
      issueDate: "",
    }),
    form = reactive(blank());
  async function load() {
    const run = ++sequence;
    busy.value = true;
    error.value = "";
    rows.value = [];
    try {
      const r = await api(
        "/properties/" + props.propertyId + "/legal-documents?page=0&size=20",
      );
      if (run === sequence) rows.value = r.items || [];
    } catch (e) {
      if (run === sequence) error.value = errorText(e);
    } finally {
      if (run === sequence) busy.value = false;
    }
  }
  onBeforeUnmount(() => sequence++);
  watch(
    () => [props.propertyId, session.user?.id],
    () => {
      selected.value = null;
      file.value = null;
      Object.assign(form, blank());
      load();
    },
    {
      immediate: true,
    },
  );
  function edit(doc) {
    selected.value = doc;
    Object.assign(form, {
      documentType: doc.documentType,
      ownerName: doc.ownerName,
      documentNumber: doc.documentNumber || "",
      issueDate: doc.issueDate || "",
    });
    notice.value = "Sửa metadata sẽ yêu cầu duyệt lại.";
  }
  function choose(e) {
    file.value = e.target.files?.[0] || null;
    e.target.value = "";
    if (
      file.value &&
      (!["image/jpeg", "image/png", "application/pdf"].includes(
        file.value.type,
      ) ||
        file.value.size > 10 * 1024 * 1024)
    ) {
      file.value = null;
      error.value = "Chỉ JPEG/PNG/PDF, tối đa 10 MiB mỗi tệp.";
    }
  }
  async function run(fn) {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    notice.value = "";
    try {
      await fn();
      await load();
    } catch (e) {
      error.value =
        e.status === 409
          ? "Hồ sơ đã thay đổi hoặc vượt quota. Hãy tải lại trước khi thao tác."
          : errorText(e);
    } finally {
      busy.value = false;
    }
  }
  async function save() {
    if (!own.value) return;
    await run(async () => {
      const metadata = {
          documentType: form.documentType,
          ownerName: form.ownerName.trim(),
          documentNumber: form.documentNumber.trim() || null,
          issueDate: form.issueDate || null,
        },
        base = "/properties/" + props.propertyId + "/legal-documents";
      if (selected.value)
        await api(
          base +
            "/" +
            selected.value.id +
            "?expectedVersion=" +
            selected.value.contentVersion,
          {
            method: "PATCH",
            body: metadata,
          },
        );
      else {
        if (!file.value) throw Error("Hãy chọn tệp bằng chứng.");
        const data = new FormData();
        data.append(
          "metadata",
          new Blob([JSON.stringify(metadata)], {
            type: "application/json",
          }),
          "metadata.json",
        );
        data.append("file", file.value);
        await api(base, {
          method: "POST",
          body: data,
        });
      }
      selected.value = null;
      file.value = null;
      Object.assign(form, blank());
      notice.value = "Hồ sơ đã lưu trên server và đang chờ duyệt.";
    });
  }
  async function remove(doc) {
    if (!confirm("Xóa mềm hồ sơ này?")) return;
    await run(() =>
      api(
        "/properties/" +
          props.propertyId +
          "/legal-documents/" +
          doc.id +
          "?expectedVersion=" +
          doc.contentVersion,
        {
          method: "DELETE",
        },
      ),
    );
  }
  async function download(doc) {
    await run(async () => {
      const blob = await api(
        "/properties/" +
          props.propertyId +
          "/legal-documents/" +
          doc.id +
          "/content",
        {
          responseType: "blob",
        },
      );
      const url = URL.createObjectURL(blob),
        a = document.createElement("a");
      a.href = url;
      a.download =
        "legal-document." +
        (doc.mimeType === "application/pdf"
          ? "pdf"
          : doc.mimeType === "image/png"
            ? "png"
            : "jpg");
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }
  async function review(doc, status) {
    if (!reason.value.trim()) {
      error.value = "Cần lý do duyệt/từ chối.";
      return;
    }
    await run(() =>
      api("/admin/legal-documents/" + doc.id + "/review", {
        method: "POST",
        body: {
          status,
          reason: reason.value.trim(),
          expectedVersion: doc.contentVersion,
        },
      }),
    );
  }
  return {
    ref,
    reactive,
    watch,
    computed,
    onBeforeUnmount,
    api,
    session,
    errorText,
    props,
    own,
    admin,
    rows,
    busy,
    error,
    notice,
    selected,
    file,
    reason,
    sequence,
    blank,
    form,
    load,
    edit,
    choose,
    run,
    save,
    remove,
    download,
    review,
  };
}
export default React.forwardRef(function LegalDocuments(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <section
      {...mergeProps({
        className: "rounded-[22px] bg-brand-card p-6",
        "aria-label": "Hồ sơ pháp lý trên server",
        "data-sp-373a33e8": "",
      })}
    >
      <h2
        {...mergeProps({
          className: "text-lg font-semibold",
          "data-sp-373a33e8": "",
        })}
      >
        {"Hồ sơ pháp lý"}
      </h2>
      <p
        {...mergeProps({
          className: "my-3 text-xs",
          "data-sp-373a33e8": "",
        })}
      >
        {
          "Tệp riêng tư chỉ chủ tin và quản trị viên được xem. Hồ sơ chỉ được lưu khi server xác nhận; tối đa 10 tệp, JPEG/PNG/PDF ≤10 MiB. Sửa thông tin sẽ đưa hồ sơ về chờ duyệt."
        }
      </p>
      {ctx.error ? (
        <p
          {...mergeProps({
            role: "alert",
            className: "my-3 text-sm text-[var(--ui-error-text)]",
            "data-sp-373a33e8": "",
          })}
        >
          {display(ctx.error)}{" "}
          <button
            {...mergeProps({
              disabled: ctx.busy,
              onClick: ($event) => {
                return ctx.load?.($event);
              },
              className: "underline",
              "data-sp-373a33e8": "",
            })}
          >
            {"Tải lại"}
          </button>
        </p>
      ) : null}
      {ctx.busy ? (
        <p
          {...mergeProps({
            role: "status",
            "data-sp-373a33e8": "",
          })}
        >
          {"Đang xử lý hồ sơ…"}
        </p>
      ) : null}
      {ctx.notice ? (
        <p
          {...mergeProps({
            role: "status",
            "data-sp-373a33e8": "",
          })}
        >
          {display(ctx.notice)}
        </p>
      ) : null}
      {!ctx.busy && !ctx.error && !ctx.rows.length ? (
        <p
          {...mergeProps({
            "data-sp-373a33e8": "",
          })}
        >
          {"Chưa có hồ sơ pháp lý trên server."}
        </p>
      ) : null}
      <ul
        {...mergeProps({
          "data-sp-373a33e8": "",
        })}
      >
        {renderList(ctx.rows, (doc) => (
          <li
            key={doc.id}
            {...mergeProps({
              className: "my-4 rounded-xl border p-4 text-sm",
              "data-sp-373a33e8": "",
            })}
          >
            <p
              {...mergeProps({
                "data-sp-373a33e8": "",
              })}
            >
              {display(doc.documentType)}
              {" · "}
              {display(doc.status)}
              {" · phiên bản "}
              {display(doc.contentVersion)}
            </p>
            <p
              {...mergeProps({
                "data-sp-373a33e8": "",
              })}
            >
              {display(doc.ownerName)}
              {" · "}
              {display(doc.documentNumber || "Chưa có số giấy")}
              {" · "}
              {display(doc.issueDate || "Chưa có ngày cấp")}
            </p>
            {doc.reviewReason ? (
              <p
                {...mergeProps({
                  "data-sp-373a33e8": "",
                })}
              >
                {"Kết quả: "}
                {display(doc.reviewReason)}
              </p>
            ) : null}
            <button
              {...mergeProps({
                disabled: ctx.busy,
                onClick: ($event) => {
                  ctx.download(doc);
                },
                className: "completion-button",
                "data-sp-373a33e8": "",
              })}
            >
              {"Tải tệp riêng"}
            </button>
            {ctx.own ? (
              <React.Fragment {...mergeProps({})}>
                <button
                  {...mergeProps({
                    disabled: ctx.busy,
                    onClick: ($event) => {
                      ctx.edit(doc);
                    },
                    className: "completion-button",
                    "data-sp-373a33e8": "",
                  })}
                >
                  {"Sửa thông tin"}
                </button>
                <button
                  {...mergeProps({
                    disabled: ctx.busy,
                    onClick: ($event) => {
                      ctx.remove(doc);
                    },
                    className: "completion-button",
                    "data-sp-373a33e8": "",
                  })}
                >
                  {"Xóa hồ sơ"}
                </button>
              </React.Fragment>
            ) : null}
            {ctx.admin && !ctx.own ? (
              <React.Fragment {...mergeProps({})}>
                <button
                  {...mergeProps({
                    disabled: ctx.busy,
                    onClick: ($event) => {
                      ctx.review(doc, "VERIFIED");
                    },
                    className: "completion-button",
                    "data-sp-373a33e8": "",
                  })}
                >
                  {"Xác minh"}
                </button>
                <button
                  {...mergeProps({
                    disabled: ctx.busy,
                    onClick: ($event) => {
                      ctx.review(doc, "REJECTED");
                    },
                    className: "completion-button",
                    "data-sp-373a33e8": "",
                  })}
                >
                  {"Từ chối"}
                </button>
              </React.Fragment>
            ) : null}
          </li>
        ))}
      </ul>
      {ctx.admin && !ctx.own ? (
        <label
          {...mergeProps({
            className: "block text-sm",
            "data-sp-373a33e8": "",
          })}
        >
          {"Lý do kiểm duyệt "}
          <textarea
            {...mergeProps(
              {
                maxLength: "4000",
                className: "completion-input w-full",
                "data-sp-373a33e8": "",
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
      ) : null}
      {ctx.admin && ctx.own ? (
        <p
          {...mergeProps({
            className: "text-xs",
            "data-sp-373a33e8": "",
          })}
        >
          {"Không được tự duyệt giấy tờ của mình."}
        </p>
      ) : null}
      {ctx.own ? (
        <form
          {...mergeProps({
            onSubmit: ($event) => {
              $event.preventDefault();
              return ctx.save?.($event);
            },
            className: "space-y-3",
            "data-sp-373a33e8": "",
          })}
        >
          <h3
            {...mergeProps({
              className: "font-semibold",
              "data-sp-373a33e8": "",
            })}
          >
            {display(ctx.selected ? "Chỉnh sửa hồ sơ" : "Thêm hồ sơ riêng tư")}
          </h3>
          <label
            {...mergeProps({
              className: "block text-sm",
              "data-sp-373a33e8": "",
            })}
          >
            {"Loại giấy tờ "}
            <select
              {...mergeProps(
                {
                  className: "completion-input",
                  "data-sp-373a33e8": "",
                },
                modelProps(
                  ctx.form.documentType,
                  ($value) => {
                    ctx.form.documentType = $value;
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
              <option
                {...mergeProps({
                  value: "LAND_USE_RIGHT",
                  "data-sp-373a33e8": "",
                })}
              >
                {"Quyền sử dụng đất"}
              </option>
              <option
                {...mergeProps({
                  value: "HOME_OWNERSHIP",
                  "data-sp-373a33e8": "",
                })}
              >
                {"Sở hữu nhà"}
              </option>
              <option
                {...mergeProps({
                  value: "SALE_CONTRACT",
                  "data-sp-373a33e8": "",
                })}
              >
                {"Hợp đồng mua bán"}
              </option>
              <option
                {...mergeProps({
                  value: "OTHER",
                  "data-sp-373a33e8": "",
                })}
              >
                {"Khác"}
              </option>
            </select>
          </label>
          <label
            {...mergeProps({
              className: "block text-sm",
              "data-sp-373a33e8": "",
            })}
          >
            {"Chủ sở hữu trên giấy tờ "}
            <input
              {...mergeProps(
                {
                  required: true,
                  maxLength: "150",
                  className: "completion-input",
                  "data-sp-373a33e8": "",
                },
                modelProps(
                  ctx.form.ownerName,
                  ($value) => {
                    ctx.form.ownerName = $value;
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
          <label
            {...mergeProps({
              className: "block text-sm",
              "data-sp-373a33e8": "",
            })}
          >
            {"Số giấy "}
            <input
              {...mergeProps(
                {
                  maxLength: "150",
                  className: "completion-input",
                  "data-sp-373a33e8": "",
                },
                modelProps(
                  ctx.form.documentNumber,
                  ($value) => {
                    ctx.form.documentNumber = $value;
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
          <label
            {...mergeProps({
              className: "block text-sm",
              "data-sp-373a33e8": "",
            })}
          >
            {"Ngày cấp "}
            <input
              {...mergeProps(
                {
                  type: "date",
                  max: new Date().toISOString().slice(0, 10),
                  className: "completion-input",
                  "data-sp-373a33e8": "",
                },
                modelProps(
                  ctx.form.issueDate,
                  ($value) => {
                    ctx.form.issueDate = $value;
                  },
                  {
                    kind: "date",
                    value: "on",
                    number: false,
                    multiple: false,
                  },
                ),
              )}
            />
          </label>
          {!ctx.selected ? (
            <label
              {...mergeProps({
                className: "block text-sm",
                "data-sp-373a33e8": "",
              })}
            >
              {"Tệp riêng tư "}
              <input
                {...mergeProps({
                  type: "file",
                  accept: "image/jpeg,image/png,application/pdf",
                  onChange: ($event) => {
                    return ctx.choose?.($event);
                  },
                  className: "completion-input",
                  "data-sp-373a33e8": "",
                })}
              />
              {display(ctx.file?.name)}
            </label>
          ) : null}
          <button
            {...mergeProps({
              disabled: ctx.busy || (!ctx.selected && ctx.rows.length >= 10),
              className: "completion-button",
              "data-sp-373a33e8": "",
            })}
          >
            {display(ctx.selected ? "Lưu metadata" : "Tải và lưu hồ sơ")}
          </button>
          {ctx.selected ? (
            <button
              {...mergeProps({
                type: "button",
                className: "completion-button",
                onClick: ($event) => {
                  ctx.selected = null;
                  Object.assign(ctx.form, ctx.blank());
                },
                "data-sp-373a33e8": "",
              })}
            >
              {"Hủy chỉnh sửa"}
            </button>
          ) : null}
        </form>
      ) : null}
    </section>,
  ]);
});
