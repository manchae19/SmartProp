import { api } from '../auth/api.js';
import { usePagedResource } from '../../shared/hooks/usePagedResource.js';
export function isPublicProperty(p, now = Date.now()) {
  return !!p && p.status === 'PUBLISHED' && !p.deletedAt && !p.hiddenAt && (p.expiresAt == null || Date.parse(p.expiresAt) > now);
}
export function usePublicListings(filters, {
  size = 20,
  delay = 180,
  endpoint = '/properties'
} = {}) {
  const request = async path => {
    const result = await api(path, {
      authenticated: false
    });
    return {
      ...result,
      items: (result.items || []).filter(p => isPublicProperty(p))
    };
  };
  return usePagedResource(request, endpoint, filters, null, {
    size,
    delay,
    loadingDuringDelay:true
  });
}
