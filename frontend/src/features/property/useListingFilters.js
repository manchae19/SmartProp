import { useRef } from "react";
import { useRouteState, useAppNavigation } from "../../app/navigation.jsx";
import { normalizeFilters, listingLink } from './listingFilters.js';
export function useListingFilters() {
  const route = useRouteState(),
    router = useAppNavigation();
  const _routerLatest = useRef(router);
  _routerLatest.current = router;
  const _routeLatest = useRef(route);
  _routeLatest.current = route;
  const getFilters = () => normalizeFilters(_routeLatest.current.query);
  function set(value, {
    replace = false
  } = {}) {
    const target = listingLink(_routeLatest.current.path, value, _routeLatest.current.path === '/map' && _routeLatest.current.query.propertyId ? {
      propertyId: _routeLatest.current.query.propertyId
    } : {});
    target.hash = _routeLatest.current.hash;
    if (JSON.stringify(target.query) !== JSON.stringify(_routeLatest.current.query)) return _routerLatest.current[replace ? 'replace' : 'push'](target);
  }
  return {
    filters: getFilters(),
    set,
    patch: value => set({
      ...getFilters(),
      ...value
    }),
    reset: () => set({}),
    link: (path, extra) => listingLink(path, getFilters(), extra)
  };
}
