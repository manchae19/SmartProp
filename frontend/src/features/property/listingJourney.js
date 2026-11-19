import { normalizeFilters } from './listingFilters.js';
export function safeListingsReturnTo(value) {
  if (typeof value !== 'string' || !/^\/listings(?:\?|$)/.test(value)) return '/listings';
  try {
    const url = new URL(value, 'https://smartprop.invalid');
    if (url.origin !== 'https://smartprop.invalid' || url.pathname !== '/listings') return '/listings';
    const filters = normalizeFilters(Object.fromEntries(url.searchParams));
    const params = new URLSearchParams(filters);
    if (params.get('sort') === 'newest') params.delete('sort');
    if (/^\d{1,5}$/.test(url.searchParams.get('page') || '')) params.set('page',url.searchParams.get('page'));
    return '/listings' + (params.size ? '?' + params : '');
  } catch { return '/listings'; }
}
export function listingsReturnFor(route) {
  if (route.path === '/listings') return safeListingsReturnTo(route.fullPath);
  if (route.query.returnTo) return safeListingsReturnTo(route.query.returnTo);
  const params = new URLSearchParams(normalizeFilters(route.query));
  if (params.get('sort') === 'newest') params.delete('sort');
  return '/listings' + (params.size ? '?' + params : '');
}
