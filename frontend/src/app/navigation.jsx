import React, { useMemo, useLayoutEffect, useRef } from 'react';
import { Link, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import { homeSectionId, navigationOffset } from '../shared/lib/siteNavigation.js';
export { Outlet };
export function queryFromSearch(search) {const result={};for(const [key,value] of new URLSearchParams(search))result[key]=key in result?[].concat(result[key],value):value;return result;}
export function toUrl(value) {
  if (typeof value === 'string') return value;
  if (value?.pathname) return value;
  const query = new URLSearchParams();
  for (const [key, queryValue] of Object.entries(value?.query || {})) if (queryValue != null) for (const item of Array.isArray(queryValue) ? queryValue : [queryValue]) query.append(key, String(item));
  return (value?.path || location.pathname) + (query.size ? '?' + query : '') + (value?.hash || '');
}
export function useRouteState() {
  const here = useLocation(),
    params = useParams();
  return useMemo(() => ({
    path: here.pathname,
    fullPath: here.pathname + here.search + here.hash,
    hash: here.hash,
    query: queryFromSearch(here.search),
    params
  }), [here, params]);
}
export function useAppNavigation() {
  const navigate = useNavigate();
  return useMemo(() => ({
    push: target => navigate(toUrl(target)),
    replace: target => navigate(toUrl(target), {
      replace: true
    }),
    back: () => navigate(-1),
    go: count => navigate(count)
  }), [navigate]);
}
export const SiteLink = React.forwardRef(function SiteLink({
  to,
  replace,
  children,
  className = '',
  activeClass = 'router-link-active',
  exactActiveClass = 'router-link-exact-active',
  ...props
}, ref) {
  const here = useLocation(),
    url = toUrl(to),
    target = new URL(typeof url === 'string' ? url : url.pathname + (url.search || '') + (url.hash || ''), location.origin);
  const exact = here.pathname === target.pathname;
  return <Link {...props} ref={ref} to={url} replace={replace} className={[className, exact ? activeClass : '', exact && here.search === target.search && here.hash === target.hash ? exactActiveClass : ''].filter(Boolean).join(' ')}>{children}</Link>;
});
export function RouteScroll() {
  const here = useLocation(),
    previous = useRef(null);
  useLayoutEffect(() => {
    const before = previous.current;
    previous.current = here;
    if (before && ['/home', '/listings', '/map'].includes(here.pathname) && here.pathname === before.pathname && here.hash === before.hash) return;
    let cancelled = false,
      frame,
      attempts = 0;
    const scroll = () => {
      if (cancelled) return;
      const target = here.pathname === '/home' && here.hash ? homeSectionId(here.hash) : null;
      const selector = target ? '#' + target : here.pathname.startsWith('/post') && here.hash ? here.hash : null;
      if (selector) {
        const element = document.querySelector(selector);
        if (!element && attempts++ < 40) {
          frame = requestAnimationFrame(scroll);
          return;
        }
        if (element) window.scrollTo({
          top: element.getBoundingClientRect().top + window.scrollY - (target ? navigationOffset() : 100),
          behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
        });
      } else window.scrollTo({
        top: 0,
        behavior: 'auto'
      });
    };
    frame = requestAnimationFrame(scroll);
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
    };
  }, [here]);
  return null;
}
