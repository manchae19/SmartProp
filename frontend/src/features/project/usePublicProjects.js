import { api } from '../auth/api.js';
import { usePagedResource } from '../../shared/hooks/usePagedResource.js';
export function usePublicProjects({
  size = 12
} = {}) {
  return usePagedResource(path => api(path, {
    authenticated: false
  }), '/projects', () => ({}), null, {
    size
  });
}
