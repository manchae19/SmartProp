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
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
} from "../../shared/state/store.js";
import { useRouter, useRoute } from "../../shared/routing/router.jsx";
import { api, session, errorText } from "../auth/api.js";
import {
  useList,
  adapt,
  money,
  LegacyState,
  LegacyPager,
  PrivateImage,
  types,
  states,
  reasons as reasonLabels,
  date,
  mapUrl,
} from "../../shared/lib/legacy.js";
import "./UsersView.css";
function setup(__props) {
  const state = useList("/admin/users"),
    target = ref(null),
    reason = ref(""),
    usersList = computed(() =>
      state.items.map((u) => ({
        ...u,
        name: u.fullName,
        avatarLetter: u.fullName.slice(0, 1),
        roleText: u.role,
        roleClass: u.role === "ADMIN" ? "role-admin" : "role-user",
        postsCount: "—",
        statusText: states[u.status],
        statusClass: u.status === "LOCKED" ? "status-locked" : "status-active",
        joinedDate: date(u.createdAt),
        isLocked: u.status === "LOCKED",
      })),
    );
  function toggleLockUser(id) {
    target.value = state.items.find((u) => u.id === id);
    reason.value = "";
  }
  async function saveStatus() {
    if (!reason.value.trim()) {
      state.error = "Nhập lý do thay đổi trạng thái.";
      return;
    }
    await state.run(async () => {
      await api("/admin/users/" + target.value.id + "/status", {
        method: "PATCH",
        body: {
          status: target.value.status === "LOCKED" ? "ACTIVE" : "LOCKED",
          reason: reason.value,
        },
      });
      target.value = null;
      await state.load(state.page);
    });
  }
  return {
    ref,
    computed,
    watch,
    onMounted,
    onBeforeUnmount,
    useRouter,
    useRoute,
    api,
    session,
    errorText,
    useList,
    adapt,
    money,
    LegacyState,
    LegacyPager,
    PrivateImage,
    types,
    states,
    reasonLabels,
    date,
    mapUrl,
    state,
    target,
    reason,
    usersList,
    toggleLockUser,
    saveStatus,
  };
}
export default React.forwardRef(function UsersView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="UsersView"
      {...mergeProps({
        className: "main",
        "data-sp-a71debef": "",
      })}
    >
      <LegacyState
        {...mergeProps({
          state: ctx.state,
          "data-sp-a71debef": "",
        })}
      />
      <div
        {...mergeProps({
          className: "section-title",
          "data-sp-a71debef": "",
        })}
      >
        <div
          {...mergeProps({
            className: "danh-s-ch-ng-i-d-ng",
            "data-sp-a71debef": "",
          })}
        >
          {"Danh sách người dùng"}
        </div>
      </div>
      <div
        {...mergeProps({
          className: "users-list",
          "data-sp-a71debef": "",
        })}
      >
        {renderList(ctx.usersList, (user) => (
          <div
            key={user.id}
            {...mergeProps({
              className: "user-card",
              "data-sp-a71debef": "",
            })}
          >
            <div
              {...mergeProps({
                className: "user-avatar",
                "data-sp-a71debef": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "avatar-letter",
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.avatarLetter)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "user-info",
                "data-sp-a71debef": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "user-name",
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.name)}
              </div>
              <div
                {...mergeProps({
                  className: "user-email",
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.email)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["user-role", user.roleClass],
                "data-sp-a71debef": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "role-text",
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.roleText)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "user-posts-count",
                "data-sp-a71debef": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "posts-text",
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.postsCount)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["user-status", user.statusClass],
                "data-sp-a71debef": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "status-text",
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.statusText)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "user-joined-date",
                "data-sp-a71debef": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "joined-text",
                  "data-sp-a71debef": "",
                })}
              >
                {"Tham gia "}
                {display(user.joinedDate)}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "user-actions",
                "data-sp-a71debef": "",
              })}
            >
              <button
                {...mergeProps({
                  className: user.isLocked ? "btn-unlock" : "btn-lock",
                  onClick: ($event) => {
                    ctx.toggleLockUser(user.id);
                  },
                  "data-sp-a71debef": "",
                })}
              >
                {display(user.isLocked ? "Mở khóa" : "Khóa tài khoản")}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>,
    ctx.target ? (
      <section
        {...mergeProps({
          className: "bg-brand-card rounded-2xl p-6",
          "data-sp-a71debef": "",
        })}
      >
        <h3
          {...mergeProps({
            "data-sp-a71debef": "",
          })}
        >
          {display(ctx.target.fullName)}
        </h3>
        <label
          {...mergeProps({
            className: "block text-xs mt-3",
            "data-sp-a71debef": "",
          })}
        >
          {"Lý do"}
          <textarea
            {...mergeProps(
              {
                maxLength: "4000",
                className: "block w-full border rounded-xl p-3 my-3",
                "data-sp-a71debef": "",
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
        <button
          {...mergeProps({
            onClick: ($event) => {
              return ctx.saveStatus?.($event);
            },
            className: "bg-[var(--ui-soft)] text-brand-navy rounded-full px-5 py-2 text-xs",
            "data-sp-a71debef": "",
          })}
        >
          {"Xác nhận"}
        </button>
      </section>
    ) : null,
    <LegacyPager
      {...mergeProps({
        state: ctx.state,
        "data-sp-a71debef": "",
      })}
    />,
  ]);
});
