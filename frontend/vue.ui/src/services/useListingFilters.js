import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { normalizeFilters, listingLink } from './listingFilters.js'

export function useListingFilters() {
  const route = useRoute(), router = useRouter()
  const filters = computed(() => normalizeFilters(route.query))
  function set(value, { replace = false } = {}) {
    const target = listingLink(route.path, value, route.path === '/map' && route.query.propertyId ? { propertyId: route.query.propertyId } : {})
    target.hash = route.hash
    if (JSON.stringify(target.query) !== JSON.stringify(route.query)) return router[replace ? 'replace' : 'push'](target)
  }
  return { filters, set, patch: value => set({ ...filters.value, ...value }), reset: () => set({}), link: (path, extra) => listingLink(path, filters.value, extra) }
}
