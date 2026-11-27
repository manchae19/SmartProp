import { createStateStore } from '../../shared/state/createStateStore.js'
import { districts } from '../map/districts.js'
import {
  advisorConsultRequest,
  advisorDistrictSuggestions,
  advisorError,
  advisorResearchActorKey,
  createAdvisorConsultClient,
} from './advisorAnalysis.js'

export const DEFAULT_ADVISOR_FORM = Object.freeze({
  budgetVnd: '3.500.000.000',
  budgetFlexibilityPct: 10,
  purpose: 'LIVING',
  propertyType: 'ALL',
  minAreaSqm: '',
  district: '',
  ward: '',
  limit: 5,
  includeComparables: true,
  includeValuation: true,
  includeResearch: false,
})

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
 * Reactive state & authorization controller for UnifiedAdvisorView.
 * Subscribes to the shared `session` store (`createStateStore`), discovers Advisor
 * research capability only for authenticated ADMIN accounts, cancels in-flight
 * requests via AbortController + sequence epochs, and immediately revokes all
 * research-derived state whenever authorization changes or is lost.
 */
export function createUnifiedAdvisorController({
  api,
  session,
  errorText = (e) => e?.message || '',
  baseDistricts = districts,
}) {
  const store = createStateStore({
    form: { ...DEFAULT_ADVISOR_FORM },
    busy: false,
    error: '',
    result: null,
    submitted: null,
    selectedPoiId: '',
    researchAvailable: false,
  })

  const consult = createAdvisorConsultClient(api, () => session.getSnapshot())
  let consultSeq = 0
  let configSeq = 0
  let consultAbort = null
  let configAbort = null
  let inFlightResearch = false
  let activeActorKey = null
  let unsubscribeSession = null

  function abortConsult() {
    if (consultAbort) {
      consultAbort.abort()
      consultAbort = null
    }
    inFlightResearch = false
  }

  function abortConfig() {
    if (configAbort) {
      configAbort.abort()
      configAbort = null
    }
  }

  function revokeResearchState({ clearError = true } = {}) {
    const snap = store.getSnapshot()
    const hasResearchData =
      inFlightResearch
      || snap.form.includeResearch === true
      || snap.result?.mode === 'INTERNAL_RESEARCH'
      || snap.submitted?.includeResearch === true

    if (inFlightResearch) {
      consultSeq++
      abortConsult()
    }

    store.edit((draft) => {
      draft.researchAvailable = false
      if (draft.form.includeResearch) {
        draft.form.includeResearch = false
      }
      if (hasResearchData) {
        draft.busy = false
        draft.result = null
        draft.submitted = null
        draft.selectedPoiId = ''
        if (clearError) {
          draft.error = ''
        }
      }
    })
  }

  function probeResearchCapability(actorKey) {
    abortConfig()
    const probeId = ++configSeq
    const controller = new AbortController()
    configAbort = controller

    Promise.resolve()
      .then(() => api('/admin/advisor/research-config', { authenticated: true, signal: controller.signal }))
      .then((config) => {
        if (
          probeId !== configSeq
          || controller.signal.aborted
          || advisorResearchActorKey(session.getSnapshot()) !== actorKey
        ) {
          return
        }
        const enabled = config?.enabled === true
        if (enabled) {
          store.edit((draft) => {
            draft.researchAvailable = true
          })
        } else {
          revokeResearchState({ clearError: true })
        }
      })
      .catch(() => {
        if (probeId !== configSeq || controller.signal.aborted) return
        revokeResearchState({ clearError: true })
      })
  }

  function syncSession(force = false) {
    const nextActorKey = advisorResearchActorKey(session.getSnapshot())
    if (!force && nextActorKey === activeActorKey) {
      return
    }
    const previousActorKey = activeActorKey
    activeActorKey = nextActorKey

    abortConfig()
    configSeq++

    if (previousActorKey !== null || !nextActorKey) {
      revokeResearchState({ clearError: true })
    } else {
      store.edit((draft) => {
        draft.researchAvailable = false
        draft.form.includeResearch = false
      })
    }

    if (nextActorKey) {
      probeResearchCapability(nextActorKey)
    }
  }

  function mount() {
    if (!unsubscribeSession) {
      unsubscribeSession = session.subscribe(() => syncSession(false))
    }
    syncSession(true)
    return () => {
      if (unsubscribeSession) {
        unsubscribeSession()
        unsubscribeSession = null
      }
      activeActorKey = null
      configSeq++
      consultSeq++
      abortConfig()
      abortConsult()
    }
  }

  function patch(key, value) {
    if (key === 'includeResearch') {
      setIncludeResearch(Boolean(value))
      return
    }
    store.edit((draft) => {
      draft.form[key] = value
    })
  }

  function setIncludeResearch(enabled) {
    const wants = Boolean(enabled)
    const canEnable =
      wants
      && store.getSnapshot().researchAvailable === true
      && advisorResearchActorKey(session.getSnapshot()) !== ''
    consultSeq++
    abortConsult()
    store.edit((draft) => {
      draft.form = { ...DEFAULT_ADVISOR_FORM, includeResearch: canEnable }
      draft.busy = false
      draft.error = ''
      draft.result = null
      draft.submitted = null
      draft.selectedPoiId = ''
    })
  }

  function toggleResearch() {
    setIncludeResearch(!store.getSnapshot().form.includeResearch)
  }

  function reset() {
    consultSeq++
    abortConsult()
    store.edit((draft) => {
      draft.form = { ...DEFAULT_ADVISOR_FORM }
      draft.busy = false
      draft.error = ''
      draft.result = null
      draft.submitted = null
      draft.selectedPoiId = ''
    })
  }

  function setSelectedPoiId(poiId) {
    store.edit((draft) => {
      draft.selectedPoiId = poiId || ''
    })
  }

  async function submit(event) {
    if (event?.preventDefault) event.preventDefault()

    abortConsult()
    const run = ++consultSeq
    const controller = new AbortController()
    consultAbort = controller

    const currentState = store.getSnapshot()
    const requestActorKey = advisorResearchActorKey(session.getSnapshot())
    const wantsResearch = currentState.form.includeResearch === true
    inFlightResearch = wantsResearch

    store.edit((draft) => {
      draft.busy = true
      draft.error = ''
      draft.result = null
      draft.submitted = null
      draft.selectedPoiId = ''
    })

    const formSnapshot = {
      ...currentState.form,
      includeResearch: wantsResearch,
    }

    try {
      if (wantsResearch && (!requestActorKey || !currentState.researchAvailable)) {
        const denied = new Error('Chế độ dữ liệu nghiên cứu yêu cầu phiên ADMIN hợp lệ.')
        denied.status = 403
        throw denied
      }
      const payload = advisorConsultRequest(formSnapshot)
      const response = await Promise.race([
        consult(formSnapshot, { signal: controller.signal }),
        abortSignalPromise(controller.signal),
      ])

      const liveActorKey = advisorResearchActorKey(session.getSnapshot())
      const liveState = store.getSnapshot()
      if (run !== consultSeq || controller.signal.aborted) {
        return false
      }
      if (payload.includeResearch || response?.mode === 'INTERNAL_RESEARCH') {
        if (!liveActorKey || liveActorKey !== requestActorKey || liveState.researchAvailable !== true) {
          inFlightResearch = false
          store.edit((draft) => {
            draft.busy = false
            draft.form.includeResearch = false
            draft.result = null
            draft.submitted = null
            draft.selectedPoiId = ''
          })
          return false
        }
      }

      inFlightResearch = false
      store.edit((draft) => {
        draft.submitted = payload
        draft.result = response
        draft.busy = false
      })
      return true
    } catch (failure) {
      if (run !== consultSeq || controller.signal.aborted || failure?.name === 'AbortError') {
        return false
      }
      inFlightResearch = false
      if (wantsResearch && (failure?.status === 401 || failure?.status === 403)) {
        store.edit((draft) => {
          draft.researchAvailable = false
          draft.form.includeResearch = false
          draft.result = null
          draft.submitted = null
          draft.selectedPoiId = ''
          draft.busy = false
          draft.error = advisorError(failure) || errorText(failure)
        })
        return false
      }
      store.edit((draft) => {
        draft.busy = false
        draft.error = advisorError(failure) || errorText(failure)
      })
      return false
    }
  }

  function canViewResearch() {
    const snap = store.getSnapshot()
    return snap.researchAvailable === true && advisorResearchActorKey(session.getSnapshot()) !== ''
  }

  function getDistrictSuggestions() {
    const snap = store.getSnapshot()
    return advisorDistrictSuggestions(baseDistricts, snap.result, canViewResearch())
  }

  return {
    subscribe: store.subscribe,
    getSnapshot: store.getSnapshot,
    mount,
    syncSession,
    patch,
    setIncludeResearch,
    toggleResearch,
    reset,
    submit,
    setSelectedPoiId,
    canViewResearch,
    getDistrictSuggestions,
  }
}
