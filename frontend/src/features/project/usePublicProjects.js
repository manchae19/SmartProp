import { reactive, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../auth/api.js'
import { createPagedResource } from '../../hooks/pagedResource.js'
export function usePublicProjects({ size = 12 } = {}) {
  const state = createPagedResource(path => api(path, { authenticated: false }), '/projects', () => ({}), null, reactive, { size })
  onMounted(() => state.load())
  onBeforeUnmount(() => state.dispose())
  return state
}
