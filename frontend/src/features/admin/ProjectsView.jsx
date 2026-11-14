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
import BusinessPage from "../../shared/components/BusinessPage.jsx";
import { reactive, ref } from "../../shared/state/store.js";
import { api } from "../auth/api.js";
import { useCollection } from "../home/useCollection.js";
import { LegacyState, LegacyPager } from "../../shared/lib/legacy.js";
function setup(__props) {
  const archived = ref(false),
    state = useCollection("/admin/projects", null, () => ({
      archived: archived.value,
    })),
    selected = ref(null),
    conflict = ref(false);
  const blank = () => ({
      name: "",
      developer: "",
      handoverYear: "",
      scale: "",
      address: "",
      latitude: "",
      longitude: "",
      amenities: "",
    }),
    form = reactive(blank());
  function fill(m) {
    selected.value = m;
    const p = m?.project;
    Object.assign(
      form,
      p
        ? {
            ...p,
            developer: p.developer || "",
            scale: p.scale || "",
            address: p.address || "",
            handoverYear: p.handoverYear ?? "",
            latitude: p.latitude ?? "",
            longitude: p.longitude ?? "",
            amenities: (p.amenities || []).join("\n"),
          }
        : blank(),
    );
    conflict.value = false;
  }
  async function edit(m) {
    await state.run(async () =>
      fill(await api("/admin/projects/" + m.project.id)),
    );
  }
  async function reload() {
    if (!selected.value) return;
    await edit(selected.value);
  }
  async function save() {
    await state.run(async () => {
      if ((form.latitude === "") !== (form.longitude === ""))
        throw Error("Cần cả vĩ độ và kinh độ hoặc để trống cả hai.");
      const body = {
        name: form.name.trim(),
        developer: form.developer.trim() || null,
        handoverYear:
          form.handoverYear === "" ? null : Number(form.handoverYear),
        scale: form.scale.trim() || null,
        address: form.address.trim() || null,
        latitude: form.latitude === "" ? null : Number(form.latitude),
        longitude: form.longitude === "" ? null : Number(form.longitude),
        amenities: form.amenities
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      try {
        const result = await api(
          "/admin/projects" +
            (selected.value
              ? "/" +
                selected.value.project.id +
                "?expectedVersion=" +
                selected.value.contentVersion
              : ""),
          {
            method: selected.value ? "PATCH" : "POST",
            body,
          },
        );
        fill(result);
        state.notice = "Đã lưu dự án trên server.";
        await state.load(state.page);
      } catch (e) {
        if (e.status === 409) conflict.value = true;
        throw e;
      }
    });
  }
  async function archive(m) {
    if (!confirm("Lưu trữ mềm dự án này? Các tin liên quan vẫn được giữ."))
      return;
    await state.run(async () => {
      try {
        await api(
          "/admin/projects/" +
            m.project.id +
            "?expectedVersion=" +
            m.contentVersion,
          {
            method: "DELETE",
          },
        );
        if (selected.value?.project.id === m.project.id) fill(null);
        await state.load(state.page);
      } catch (e) {
        if (e.status === 409) conflict.value = true;
        throw e;
      }
    });
  }
  return {
    BusinessPage,
    reactive,
    ref,
    api,
    useCollection,
    LegacyState,
    LegacyPager,
    archived,
    state,
    selected,
    conflict,
    blank,
    form,
    fill,
    edit,
    reload,
    save,
    archive,
  };
}
export default React.forwardRef(function ProjectsView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <BusinessPage data-ui-view="ProjectsView"
      {...mergeProps({
        title: "Quản lý dự án",
      })}
    >
      <label {...mergeProps({})}>
        <input
          {...mergeProps(
            {
              type: "checkbox",
            },
            modelProps(
              ctx.archived,
              ($value) => {
                ctx.archived = $value;
              },
              {
                kind: "checkbox",
                value: "on",
                number: false,
                multiple: false,
              },
            ),
          )}
        />
        {" Dự án đã lưu trữ"}
      </label>
      <button
        {...mergeProps({
          onClick: ($event) => {
            ctx.fill(null);
          },
          disabled: ctx.state.busy,
        })}
      >
        {"Tạo dự án"}
      </button>
      <LegacyState
        {...mergeProps({
          state: ctx.state,
        })}
      />
      {ctx.conflict ? (
        <p
          {...mergeProps({
            role: "alert",
          })}
        >
          {
            "Phiên bản đã thay đổi. Tải lại dự án để kiểm tra trước khi lưu tiếp. "
          }
          <button
            {...mergeProps({
              onClick: ($event) => {
                return ctx.reload?.($event);
              },
              disabled: ctx.state.busy,
            })}
          >
            {"Tải lại dự án"}
          </button>
        </p>
      ) : null}
      {!ctx.state.busy && !ctx.state.items.length ? (
        <p {...mergeProps({})}>{"Chưa có dự án phù hợp."}</p>
      ) : null}
      {renderList(ctx.state.items, (m) => (
        <section key={m.project.id} {...mergeProps({})}>
          <h2 {...mergeProps({})}>{display(m.project.name)}</h2>
          <p {...mergeProps({})}>
            {display(m.project.address)}
            {" · phiên bản "}
            {display(m.contentVersion)}
            {" · "}
            {display(m.deletedAt ? "Đã lưu trữ" : "Hoạt động")}
          </p>
          <button
            {...mergeProps({
              disabled: ctx.state.busy,
              onClick: ($event) => {
                ctx.edit(m);
              },
            })}
          >
            {"Xem / sửa dự án"}
          </button>
          {!m.deletedAt ? (
            <button
              {...mergeProps({
                disabled: ctx.state.busy,
                onClick: ($event) => {
                  ctx.archive(m);
                },
              })}
            >
              {"Lưu trữ dự án"}
            </button>
          ) : null}
        </section>
      ))}
      <LegacyPager
        {...mergeProps({
          state: ctx.state,
        })}
      />
      <section {...mergeProps({})}>
        <h2 {...mergeProps({})}>
          {display(ctx.selected ? "Chi tiết dự án" : "Dự án mới")}
        </h2>
        <form
          {...mergeProps({
            onSubmit: ($event) => {
              $event.preventDefault();
              return ctx.save?.($event);
            },
          })}
        >
          <fieldset
            {...mergeProps({
              disabled: ctx.state.busy || !!ctx.selected?.deletedAt,
            })}
          >
            <label {...mergeProps({})}>
              {"Tên dự án "}
              <input
                {...mergeProps(
                  {
                    required: true,
                    maxLength: "255",
                  },
                  modelProps(
                    ctx.form.name,
                    ($value) => {
                      ctx.form.name = $value;
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
            <label {...mergeProps({})}>
              {"Chủ đầu tư "}
              <input
                {...mergeProps(
                  {
                    maxLength: "255",
                  },
                  modelProps(
                    ctx.form.developer,
                    ($value) => {
                      ctx.form.developer = $value;
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
            <label {...mergeProps({})}>
              {"Năm bàn giao "}
              <input
                {...mergeProps(
                  {
                    type: "number",
                    min: "1900",
                    max: "2200",
                    step: "1",
                  },
                  modelProps(
                    ctx.form.handoverYear,
                    ($value) => {
                      ctx.form.handoverYear = $value;
                    },
                    {
                      kind: "number",
                      value: "on",
                      number: false,
                      multiple: false,
                    },
                  ),
                )}
              />
            </label>
            <label {...mergeProps({})}>
              {"Quy mô "}
              <textarea
                {...mergeProps(
                  {
                    maxLength: "4000",
                  },
                  modelProps(
                    ctx.form.scale,
                    ($value) => {
                      ctx.form.scale = $value;
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
            <label {...mergeProps({})}>
              {"Địa chỉ "}
              <textarea
                {...mergeProps(
                  {
                    maxLength: "4000",
                  },
                  modelProps(
                    ctx.form.address,
                    ($value) => {
                      ctx.form.address = $value;
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
            <label {...mergeProps({})}>
              {"Vĩ độ đã xác minh "}
              <input
                {...mergeProps(
                  {
                    type: "number",
                    min: "-90",
                    max: "90",
                    step: "any",
                  },
                  modelProps(
                    ctx.form.latitude,
                    ($value) => {
                      ctx.form.latitude = $value;
                    },
                    {
                      kind: "number",
                      value: "on",
                      number: false,
                      multiple: false,
                    },
                  ),
                )}
              />
            </label>
            <label {...mergeProps({})}>
              {"Kinh độ đã xác minh "}
              <input
                {...mergeProps(
                  {
                    type: "number",
                    min: "-179.999999",
                    max: "180",
                    step: "any",
                  },
                  modelProps(
                    ctx.form.longitude,
                    ($value) => {
                      ctx.form.longitude = $value;
                    },
                    {
                      kind: "number",
                      value: "on",
                      number: false,
                      multiple: false,
                    },
                  ),
                )}
              />
            </label>
            <label {...mergeProps({})}>
              {"Tiện ích (mỗi dòng một mục, tối đa100) "}
              <textarea
                {...mergeProps(
                  {},
                  modelProps(
                    ctx.form.amenities,
                    ($value) => {
                      ctx.form.amenities = $value;
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
            <button
              {...mergeProps({
                disabled: ctx.conflict,
              })}
            >
              {"Lưu dự án"}
            </button>
          </fieldset>
        </form>
      </section>
    </BusinessPage>,
  ]);
});
