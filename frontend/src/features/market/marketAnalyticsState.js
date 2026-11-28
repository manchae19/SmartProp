import { createStateStore } from '../../shared/state/createStateStore.js'
import { sameRestrictedSession } from '../../shared/lib/restrictedSession.js'
import { isMarketResearchAdmin, loadMarketAnalytics, requestsMarketResearch } from './marketAnalytics.js'

export const EMPTY_MARKET_FILTERS = Object.freeze({
  district: '', propertyType: '', source: 'ALL', includeResearch: false,
})

function publicFilters(filters) {
  return {
    ...filters,
    source: String(filters.source).trim().toUpperCase() === 'TINIX_RESEARCH' ? 'ALL' : filters.source,
    includeResearch: false,
  }
}

function sameResearchSession(previous, next) {
  const wasAdmin = isMarketResearchAdmin(previous)
  const isAdmin = isMarketResearchAdmin(next)
  if (!wasAdmin || !isAdmin) return wasAdmin === isAdmin
  return sameRestrictedSession(previous, next)
}

export function createMarketAnalyticsController({ api, session, errorText = e => e?.message || '' }) {
  const store = createStateStore({
    filters: { ...EMPTY_MARKET_FILTERS },
    data: null, busy: false, error: '', researchError: '',
    canRequestResearch: isMarketResearchAdmin(session.getSnapshot()),
    researchAvailable: false,
  })

  let activeSession = session.getSnapshot()
  let request
  let mounted = false

  function update(patch) {
    store.set({ ...store.getSnapshot(), ...patch })
  }

  async function load(filters, optIn = false, researchError = '') {
    if (!mounted) return null
    const state = store.getSnapshot()
    const research = isMarketResearchAdmin(session.getSnapshot())
      && (optIn || state.filters.includeResearch)
      && requestsMarketResearch(filters)
    const next = research ? { ...filters, includeResearch: true } : publicFilters(filters)

    request?.abort()
    const run = new AbortController()
    request = run
    update({
      filters: next, busy: true, error: '', researchError,
      researchAvailable: research && state.researchAvailable,
      data: !research && state.data?.meta.researchIncluded ? null : state.data,
    })

    try {
      const data = await loadMarketAnalytics(next, api, {
        allowResearch: research, signal: run.signal, getSession: session.getSnapshot,
      })
      if (request !== run || run.signal.aborted) return null
      if (research && data.meta.researchIncluded !== true) return denyResearch(next)
      update({ data, busy: false, researchAvailable: research })
      return data
    } catch (failure) {
      if (request !== run || run.signal.aborted) return null
      if (research && (failure?.status === 401 || failure?.status === 403)) return denyResearch(next)
      update({
        data: null, busy: false, researchAvailable: false,
        error: (failure?.status ? errorText(failure) : failure?.message)
          || 'Chưa tải được dữ liệu thị trường. Vui lòng thử lại.',
      })
      return null
    } finally {
      if (request === run) request = null
    }
  }

  function denyResearch(filters) {
    update({ researchAvailable: false, data: null })
    return load(publicFilters(filters), false, 'Dữ liệu nghiên cứu hiện không được phép hoặc chưa được bật.')
  }

  function syncSession() {
    const next = session.getSnapshot()
    const changed = !sameResearchSession(activeSession, next)
    activeSession = next
    if (!changed) return

    const state = store.getSnapshot()
    const hadResearch = requestsMarketResearch(state.filters) || state.researchAvailable
    const filters = publicFilters(state.filters)
    if (hadResearch) request?.abort()
    update({
      canRequestResearch: isMarketResearchAdmin(next), filters, researchAvailable: false,
      researchError: '', data: hadResearch ? null : state.data,
    })
    if (hadResearch) void load(filters)
  }

  return {
    subscribe: store.subscribe,
    getSnapshot: store.getSnapshot,
    mount() {
      mounted = true
      activeSession = session.getSnapshot()
      update({ canRequestResearch: isMarketResearchAdmin(activeSession), researchAvailable: false, data: null })
      const unsubscribe = session.subscribe(syncSession)
      void load(publicFilters(store.getSnapshot().filters))
      return () => {
        mounted = false
        unsubscribe()
        request?.abort()
        request = null
      }
    },
    retry: () => load(store.getSnapshot().filters),
    patchFilter(key, value) {
      return load({ ...store.getSnapshot().filters, [key]: value })
    },
    setResearchEnabled(enabled) {
      const filters = store.getSnapshot().filters
      return load(enabled ? { ...filters, includeResearch: true } : publicFilters(filters), enabled)
    },
  }
}
