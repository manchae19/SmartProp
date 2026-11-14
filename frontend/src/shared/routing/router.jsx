import React, { Suspense, useLayoutEffect } from "react";
import {
  createBrowserRouter,
  redirect,
  Outlet,
  Link,
  useLocation,
  useMatches,
} from "react-router-dom";
import { reactive } from "../state/store.js";
export const currentRoute = reactive({
  path: location.pathname,
  fullPath: location.pathname + location.search + location.hash,
  hash: location.hash,
  query: Object.fromEntries(new URLSearchParams(location.search)),
  params: {},
});
let activeRouter,
  scrollBehavior,
  previous = {
    ...currentRoute,
  };
function routeValue(url, params = {}) {
  const query = {};
  for (const [k, v] of url.searchParams) {
    if (k in query) query[k] = [].concat(query[k], v);
    else query[k] = v;
  }
  return {
    path: url.pathname,
    hash: url.hash,
    fullPath: url.pathname + url.search + url.hash,
    query,
    params,
  };
}
export function toUrl(value) {
  if (typeof value === "string") return value;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(value?.query || {})) {
    if (v == null) continue;
    for (const item of Array.isArray(v) ? v : [v])
      params.append(k, String(item));
  }
  return (
    (value?.path || currentRoute.path) +
    (params.size ? "?" + params.toString() : "") +
    (value?.hash || "")
  );
}
const navigation = {
  push: (to) => activeRouter.navigate(toUrl(to)),
  replace: (to) =>
    activeRouter.navigate(toUrl(to), {
      replace: true,
    }),
  back: () => activeRouter.navigate(-1),
  go: (n) => activeRouter.navigate(n),
};
export const useRoute = () => currentRoute;
export const useRouter = () => navigation;
export const RouterView = Outlet;
export const RouterLink = React.forwardRef(function RouterLink(
  {
    to,
    replace,
    children,
    className = "",
    activeClass = "router-link-active",
    exactActiveClass = "router-link-exact-active",
    ...props
  },
  ref,
) {
  const here = useLocation(),
    url = toUrl(to),
    target = new URL(url, location.origin),
    exact = here.pathname === target.pathname;
  return (
    <Link
      {...{
        ...props,
        ref,
        to: url,
        replace,
        className: [
          className,
          exact ? activeClass : "",
          exact && here.search === target.search && here.hash === target.hash
            ? exactActiveClass
            : "",
        ]
          .filter(Boolean)
          .join(" "),
      }}
    >
      {children}
    </Link>
  );
});
function RouteFrame({ Root }) {
  const here = useLocation(),
    matches = useMatches(),
    params = Object.assign({}, ...matches.map((m) => m.params));
  useLayoutEffect(() => {
    const to = routeValue(
        new URL(here.pathname + here.search + here.hash, location.origin),
        params,
      ),
      from = previous;
    Object.assign(currentRoute, to);
    previous = to;
    let stop = false,
      tries = 0;
    const scroll = () => {
      if (stop) return;
      const result = scrollBehavior?.(to, from, null);
      if (!result) return;
      if (result.el) {
        const node = document.querySelector(result.el);
        if (!node && tries++ < 40) {
          requestAnimationFrame(scroll);
          return;
        }
        if (node)
          window.scrollTo({
            top:
              node.getBoundingClientRect().top +
              window.scrollY -
              (result.top || 0),
            behavior:
              result.behavior === "instant"
                ? "auto"
                : result.behavior || "auto",
          });
      } else
        window.scrollTo({
          top: result.top || 0,
          behavior: "auto",
        });
    };
    requestAnimationFrame(scroll);
    return () => {
      stop = true;
    };
  }, [here.key]);
  return <Root />;
}
const Loading = () => (
  <div
    {...{
      role: "status",
      className:
        "grid min-h-screen place-items-center bg-brand-cream text-brand-navy",
    }}
  >
    {"SmartProp..."}
  </div>
);
function RouteError() {
  return (
    <div
      {...{
        role: "alert",
        className: "p-8 text-brand-navy",
      }}
    >
      <p>{"Không tải được trang. Vui lòng thử lại."}</p>
      <button
        {...{
          type: "button",
          onClick: () => location.reload(),
        }}
      >
        {"Tải lại"}
      </button>
    </div>
  );
}
export function createAppRouter(options) {
  const guards = [];
  scrollBehavior = options.scrollBehavior;
  async function guard({ request, params }) {
    await Promise.resolve();
    const to = routeValue(new URL(request.url), params);
    for (const fn of guards) {
      const result = await fn(to);
      if (result && result !== true) throw redirect(toUrl(result));
      if (result === false) throw redirect(currentRoute.fullPath);
    }
    return null;
  }
  function convert(route) {
    let element;
    if (route.component) {
      const C =
        typeof route.component === "function"
          ? React.lazy(route.component)
          : route.component;
      element = (
        <Suspense
          {...{
            fallback: <Loading />,
          }}
        >
          <C />
        </Suspense>
      );
    }
    const entry = {
      path: route.path === "/:pathMatch(.*)*" ? "*" : route.path,
      element,
      loader: async (args) => {
        await guard(args);
        if (route.redirect && !route.children)
          throw redirect(
            toUrl(
              typeof route.redirect === "function"
                ? route.redirect(
                    routeValue(new URL(args.request.url), args.params),
                  )
                : route.redirect,
            ),
          );
        return null;
      },
    };
    if (route.children) {
      entry.children = route.children.map(convert);
      if (route.redirect)
        entry.children.unshift({
          index: true,
          loader: () => redirect(toUrl(route.redirect)),
        });
    }
    return entry;
  }
  activeRouter = createBrowserRouter([
    {
      path: "/",
      element: (
        <RouteFrame
          {...{
            Root: options.root,
          }}
        />
      ),
      errorElement: <RouteError />,
      HydrateFallback: Loading,
      children: options.routes.map(convert),
    },
  ]);
  return {
    ...navigation,
    browser: activeRouter,
    beforeEach: (fn) => guards.push(fn),
  };
}
