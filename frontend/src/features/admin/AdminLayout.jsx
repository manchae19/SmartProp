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
import { ref, nextTick, watch } from "../../shared/state/store.js";
import { useRoute, useRouter } from "../../shared/routing/router.jsx";
import { api } from "../auth/api.js";
import AppHeader from "../../shared/components/layout/AppHeader.jsx";
import "./AdminLayout.css";
function setup(__props) {
  const router = useRouter(),
    route = useRoute(),
    pending = ref("—"),
    openReports = ref("—");
  api("/admin/dashboard")
    .then((s) => {
      pending.value = s.pendingProperties;
      openReports.value = s.openReports;
    })
    .catch(() => {});
  watch(
    () => route.path,
    async () => {
      await nextTick();
      document.getElementById("page-content")?.focus({
        preventScroll: true,
      });
    },
  );
  return {
    ref,
    nextTick,
    watch,
    useRoute,
    useRouter,
    api,
    AppHeader,
    router,
    route,
    pending,
    openReports,
  };
}
export default React.forwardRef(function AdminLayout(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="AdminLayout"
      {...mergeProps({
        className: "admin-layout",
        "data-sp-87e8ba60": "",
      })}
    >
      <a
        {...mergeProps({
          href: "#page-content",
          className:
            "fixed -top-20 left-4 z-[100] rounded-control bg-brand-card px-5 py-3 text-sm font-semibold shadow-lg focus:top-3",
          "data-sp-87e8ba60": "",
        })}
      >
        {"Đến nội dung chính"}
      </a>
      <AppHeader
        {...mergeProps({
          "data-sp-87e8ba60": "",
        })}
      />
      <div
        {...mergeProps({
          className: "section",
          "data-sp-87e8ba60": "",
        })}
      >
        <div
          {...mergeProps({
            className: "header",
            "data-sp-87e8ba60": "",
          })}
        >
          <video
            {...mergeProps({
              autoPlay: true,
              muted: true,
              loop: true,
              playsInline: true,
              className: "header-video",
              "data-sp-87e8ba60": "",
            })}
          >
            <source
              {...mergeProps({
                src: "/background.mp4",
                type: "video/mp4",
                "data-sp-87e8ba60": "",
              })}
            />
            {" Trình duyệt của bạn không hỗ trợ thẻ video. "}
          </video>
          <div
            {...mergeProps({
              className: "video-overlay",
              "data-sp-87e8ba60": "",
            })}
          />
          <div
            {...mergeProps({
              className: "hcontent",
              "data-sp-87e8ba60": "",
            })}
          >
            <div
              {...mergeProps({
                className: "left",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "badge",
                  "data-sp-87e8ba60": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "qu-n-tr",
                    "data-sp-87e8ba60": "",
                  })}
                >
                  {"QUẢN TRỊ"}
                </div>
              </div>
              <div
                {...mergeProps({
                  className: "b-ng-i-u-khi-n",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Bảng điều khiển"}
              </div>
              <div
                {...mergeProps({
                  className: "theo-d-i-tin-ng-n",
                  "data-sp-87e8ba60": "",
                })}
              >
                {
                  " Theo dõi tin đăng, người dùng và trạng thái xử lý AI trong toàn hệ thống. "
                }
              </div>
            </div>
            <button
              {...mergeProps({
                type: "button",
                className: "postbtn",
                onClick: ($event) => {
                  ctx.router.push("/post");
                },
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "ng-tin",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Đăng tin"}
              </div>
              <div
                {...mergeProps({
                  className: "div",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"+"}
              </div>
            </button>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "body-layout",
            "data-sp-87e8ba60": "",
          })}
        >
          <aside
            {...mergeProps({
              className: "sidebar",
              "aria-label": "Điều hướng quản trị",
              "data-sp-87e8ba60": "",
            })}
          >
            <div
              {...mergeProps({
                className: "m-c-qu-n-tr",
                "data-sp-87e8ba60": "",
              })}
            >
              {"MỤC QUẢN TRỊ"}
            </div>
            <RouterLink
              {...mergeProps({
                to: "/admin/dashboard",
                className: "nav",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "th-ng-k-t-ng-quan",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Thống kê tổng quan"}
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/posts",
                className: "nav2",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "tin-ch-duy-t",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Tin chờ duyệt"}
              </div>
              <div
                {...mergeProps({
                  className: "count",
                  "data-sp-87e8ba60": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "_18",
                    "data-sp-87e8ba60": "",
                  })}
                >
                  {display(ctx.pending)}
                </div>
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/broker-applications",
                className: "nav2",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Duyệt quyền đăng tin"}
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/users",
                className: "nav2",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "ng-i-d-ng",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Người dùng"}
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/reports",
                className: "nav2",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "b-o-c-o-tin-ng",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Báo cáo tin đăng"}
              </div>
              <div
                {...mergeProps({
                  className: "count",
                  "data-sp-87e8ba60": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "_7",
                    "data-sp-87e8ba60": "",
                  })}
                >
                  {display(ctx.openReports)}
                </div>
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/audit-logs",
                className: "nav",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "nh-t-ký-ki-m-to-n",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Nhật ký kiểm toán"}
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/projects",
                className: "nav",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Dự án"}
              </div>
            </RouterLink>
            <RouterLink
              {...mergeProps({
                to: "/admin/ai-config",
                className: "nav",
                activeClass: "active-nav",
                "data-sp-87e8ba60": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "c-u-h-nh-ai",
                  "data-sp-87e8ba60": "",
                })}
              >
                {"Cấu hình AI"}
              </div>
            </RouterLink>
          </aside>
          <main
            {...mergeProps({
              id: "page-content",
              tabIndex: "-1",
              className: "main-content-area outline-none",
              "data-sp-87e8ba60": "",
            })}
          >
            <RouterView
              {...mergeProps({
                "data-sp-87e8ba60": "",
              })}
            />
          </main>
        </div>
      </div>
    </div>,
  ]);
});
