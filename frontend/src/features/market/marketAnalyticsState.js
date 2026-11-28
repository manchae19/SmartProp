import { createStateStore } from '../../shared/state/createStateStore.js'
import {
  loadMarketAnalytics,
  marketResearchActorKey,
  requestsMarketResearch,
} from './marketAnalytics.js'

export const EMPTY_MARKET_FILTERS = Object.freeze({
  district: '',
  propertyType: '',
  source: 'ALL',
  includeResearch: false,
})

function sanitizePublicFilters(filters = {}) {
  return {
    ...EMPTY_MARKET_FILTERS,
    ...filters,
    source: String(filters?.source ?? '').trim().toUpperCase() === 'TINIX_RESEARCH'
      ? 'ALL'
      : (filters?.source || 'ALL'),
    includeResearch: false,
  }
}

function abortSignalPromise(signal) {
  if (!signal) return new Promise(() => {})
  if (signal.aborted) {
    const err = new Error('Yêu cầu đã bị hủy do thay đổi quyền phiên.')
    err.name = 'AbortError'
    return Promise.reject(err)
  }
  return new Promise((_, reject) => {
    signal.addEventListener(
      'abort',
      () => {
        const err = new Error('Yêu cầu đã bị hủy do thay đổi quyền phiên.')
        err.name = 'AbortError'
        reject(err)
      },
      { once: true }
    )
  })
}

/**
 * Reactive state & authorization controller for MarketAnalyticsView.
 * Subscribes to the shared `session` store, discovers server-side Market research
 * availability strictly for authenticated ACTIVE ADMIN sessions without exposing
 * controls to unauthorized callers, cancels in-flight requests, and immediately
 * revokes all research-derived UI state when authorization changes or is lost.
 */
export function createMarketAnalyticsController({
  api,
  session,
  errorText = (e) => e?.message || '',
}) {
  const store = createStateStore({
    filters: { ...EMPTY_MARKET_FILTERS },
    data: null,
    busy: false,
    error: '',
    researchAvailable: false,
  })

  let requestSeq = 0
  let probeSeq = 0
  let activeController = null
  let probeController = null
  let activeActor = ''
  let mounted = false

  function cancelActiveRequest() {
    requestSeq += 1
    if (activeController) {
      activeController.abort()
      activeController = null
    }
  }

  function cancelProbe() {
    probeSeq += 1
    if (probeController) {
      probeController.abort()
      probeController = null
    }
  }

  function canCurrentlyUseResearch() {
    const actor = marketResearchActorKey(session.getSnapshot())
    return actor !== '' && actor === activeActor && store.getSnapshot().researchAvailable === true
  }

  async function probeResearchCapability(actor) {
    cancelProbe()
    if (!actor) {
      store.edit((draft) => {
        draft.researchAvailable = false
      })
      return false
    }
    const seq = probeSeq
    const controller = new AbortController()
    probeController = controller
    try {
      await Promise.race([
        loadMarketAnalytics(
          { includeResearch: true },
          api,
          {
            allowResearch: true,
            signal: controller.signal,
            getSession: () => session.getSnapshot(),
          }
        ),
        abortSignalPromise(controller.signal),
      ])
      if (!mounted || seq !== probeSeq || controller.signal.aborted) return false
      if (marketResearchActorKey(session.getSnapshot()) !== actor) return false
      store.edit((draft) => {
        draft.researchAvailable = true
      })
      return true
    } catch {
      if (!mounted || seq !== probeSeq || controller.signal.aborted) return false
      if (marketResearchActorKey(session.getSnapshot()) === actor) {
        store.edit((draft) => {
          draft.researchAvailable = false
        })
      }
      return false
    } finally {
      if (probeController === controller) probeController = null
    }
  }

  async function load(nextFilters = store.getSnapshot().filters) {
    const wantsResearch = requestsMarketResearch(nextFilters)
    const actorAtStart = marketResearchActorKey(session.getSnapshot())
    const allowedAtStart = wantsResearch
      ? actorAtStart !== '' && store.getSnapshot().researchAvailable === true
      : true

    const effectiveFilters = wantsResearch && !allowedAtStart
      ? sanitizePublicFilters(nextFilters)
      : { ...EMPTY_MARKET_FILTERS, ...nextFilters }
    const effectiveResearch = requestsMarketResearch(effectiveFilters)

    cancelActiveRequest()
    const run = requestSeq
    const controller = new AbortController()
    activeController = controller

    store.edit((draft) => {
      draft.filters = effectiveFilters
      draft.busy = true
      draft.error = ''
      if (!effectiveResearch && draft.data?.meta?.researchIncluded === true) {
        draft.data = null
      }
    })

    try {
      const result = await Promise.race([
        loadMarketAnalytics(effectiveFilters, api, {
          allowResearch: effectiveResearch,
          signal: controller.signal,
          getSession: () => session.getSnapshot(),
        }),
        abortSignalPromise(controller.signal),
      ])

      if (!mounted || run !== requestSeq || controller.signal.aborted) return null

      if (effectiveResearch || result?.meta?.researchIncluded === true) {
        const currentActor = marketResearchActorKey(session.getSnapshot())
        if (!currentActor || currentActor !== actorAtStart || !store.getSnapshot().researchAvailable) {
          const safeFilters = sanitizePublicFilters(effectiveFilters)
          store.edit((draft) => {
            draft.filters = safeFilters
            draft.data = null
            draft.busy = false
          })
          return load(safeFilters)
        }
      }

      store.edit((draft) => {
        draft.data = result
        draft.busy = false
        draft.error = ''
      })
      return result
    } catch (failure) {
      if (!mounted || run !== requestSeq || controller.signal.aborted || failure?.name === 'AbortError') {
        return null
      }
      if (effectiveResearch && (failure?.status === 401 || failure?.status === 403)) {
        const safeFilters = sanitizePublicFilters(effectiveFilters)
        store.edit((draft) => {
          draft.researchAvailable = false
          draft.filters = safeFilters
          draft.data = null
          draft.busy = false
          draft.error = ''
        })
        return load(safeFilters)
      }
      const text = failure?.status ? errorText(failure) : failure?.message
      store.edit((draft) => {
        draft.data = null
        draft.busy = false
        draft.error = text || 'Chưa tải được dữ liệu thị trường. Vui lòng thử lại.'
      })
      return null
    } finally {
      if (activeController === controller) activeController = null
    }
  }

  function revokeResearchAndReload(baseFilters) {
    cancelProbe()
    cancelActiveRequest()
    const safeFilters = sanitizePublicFilters(baseFilters)
    store.edit((draft) => {
      draft.researchAvailable = false
      draft.filters = safeFilters
      draft.data = null
      draft.busy = false
      draft.error = ''
    })
    return load(safeFilters)
  }

  function syncActor() {
    if (!mounted) return
    const nextActor = marketResearchActorKey(session.getSnapshot())
    if (nextActor === activeActor) return

    const prevSnap = store.getSnapshot()
    const hadResearchState =
      requestsMarketResearch(prevSnap.filters)
      || prevSnap.data?.meta?.researchIncluded === true
      || prevSnap.researchAvailable === true

    activeActor = nextActor

    if (!nextActor) {
      if (hadResearchState) {
        void revokeResearchAndReload(prevSnap.filters)
      }
      return
    }

    // Actor changed (e.g. login as ADMIN, or switch ADMIN A -> ADMIN B):
    // never retain prior actor's research payload while probing new actor capability.
    if (hadResearchState) {
      const safeFilters = sanitizePublicFilters(prevSnap.filters)
      cancelActiveRequest()
      store.edit((draft) => {
        draft.researchAvailable = false
        draft.filters = safeFilters
        draft.data = null
        draft.error = ''
      })
      void load(safeFilters)
    }
    void probeResearchCapability(nextActor)
  }

  function patchFilter(key, value) {
    const current = store.getSnapshot().filters
    const next = { ...current, [key]: value }
    if (requestsMarketResearch(next) && !canCurrentlyUseResearch()) {
      return load(sanitizePublicFilters(next))
    }
    return load(next)
  }

  function mount() {
    mounted = true
    activeActor = marketResearchActorKey(session.getSnapshot())
    const unsubscribe = session.subscribe(syncActor)
    void load(sanitizePublicFilters(store.getSnapshot().filters))
    if (activeActor) {
      void probeResearchCapability(activeActor)
    }
    return () => {
      mounted = false
      unsubscribe()
      cancelProbe()
      cancelActiveRequest()
    }
  }

  return {
    subscribe: store.subscribe,
    getSnapshot: store.getSnapshot,
    mount,
    load,
    patchFilter,
  }
}
