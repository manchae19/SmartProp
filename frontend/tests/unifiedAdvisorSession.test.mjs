import test from 'node:test'
import assert from 'node:assert/strict'
import { clearSession, session } from '../src/features/auth/api.js'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { resolveAdvisorResultsView } from '../src/features/prediction/advisorAnalysis.js'
import { createUnifiedAdvisorController } from '../src/features/prediction/unifiedAdvisorState.js'

const BASE_DISTRICTS = ['Tất cả', 'Hải Châu', 'Sơn Trà', 'Ngũ Hành Sơn']

function setSessionState({ status = 'UNAUTHENTICATED', token = null, user = null } = {}) {
  session.set({ status, token, user, error: null })
}

function sampleResearchResponse(extraArea = 'Khu Nghiên Cứu Lịch Sử A') {
  return {
    advisorVersion: 'ADVISOR_ORCHESTRATOR_V1',
    mode: 'INTERNAL_RESEARCH',
    criteria: { includeResearch: true },
    serviceStatus: {
      recommendationService: 'AVAILABLE',
      areaService: 'AVAILABLE',
      comparableService: 'AVAILABLE',
      valuationService: 'AVAILABLE',
      partialResult: false,
    },
    topAreas: [
      {
        district: extraArea,
        ward: 'Hòa Cường Bắc',
        candidateCount: 12,
        areaScore: 88,
        unverifiedCount: 12,
        needsReviewCount: 0,
        warnings: ['TiniX CC BY-NC 4.0'],
      },
    ],
    recommendedProperties: [
      {
        id: 'tinix:tnx-101',
        title: 'Quan sát nghiên cứu TiniX #101',
        district: 'Hải Châu',
        ward: 'Hòa Cường Bắc',
        priceVnd: 3400000000,
        areaSqm: 75,
        recommendationScore: 86,
        liveListing: false,
        researchReference: true,
        source: { kind: 'TINIX_AI', name: 'TiniX AI', recordKey: 'tnx-101', detailUrl: null },
        fitReasons: ['Khớp ngân sách nghiên cứu'],
        warnings: ['Dữ liệu nghiên cứu TiniX (CC BY-NC 4.0)'],
        comparableEvidence: {
          status: 'AVAILABLE',
          candidateCount: 1,
          searchStage: 'WARD',
          comparables: [
            {
              candidateId: 'tnx-202',
              sourceKind: 'TINIX_RESEARCH',
              liveListing: false,
              researchReference: true,
              listingUrl: null,
              datasetLicense: 'CC BY-NC 4.0',
            },
          ],
          warnings: [],
        },
        valuationEvidence: {
          available: false,
          predictedAskingPriceVnd: null,
        },
      },
    ],
    warnings: ['RESEARCH_COMPARABLES_LABEL: Dữ liệu nghiên cứu lịch sử CC BY-NC 4.0'],
  }
}

function sampleSafeResponse() {
  return {
    advisorVersion: 'ADVISOR_ORCHESTRATOR_V1',
    mode: 'SAFE',
    criteria: { includeResearch: false },
    serviceStatus: {
      recommendationService: 'AVAILABLE',
      areaService: 'AVAILABLE',
      comparableService: 'AVAILABLE',
      valuationService: 'AVAILABLE',
      partialResult: false,
    },
    topAreas: [
      {
        district: 'Hải Châu',
        ward: 'Phước Ninh',
        candidateCount: 2,
        areaScore: 84,
        unverifiedCount: 0,
        needsReviewCount: 0,
        warnings: [],
      },
    ],
    recommendedProperties: [
      {
        id: 'property:hc-01',
        title: 'Nhà phố Hải Châu công khai',
        district: 'Hải Châu',
        ward: 'Phước Ninh',
        priceVnd: 3450000000,
        areaSqm: 72,
        recommendationScore: 84,
        liveListing: true,
        researchReference: false,
        source: { kind: 'PROPERTY', name: 'SmartProp', recordKey: 'hc-01', detailUrl: '/listing/hc-01' },
        fitReasons: ['Phù hợp ngân sách'],
        warnings: [],
        comparableEvidence: {
          status: 'AVAILABLE',
          candidateCount: 1,
          searchStage: 'WARD',
          comparables: [
            {
              candidateId: 'property:hc-02',
              sourceKind: 'SMARTPROP',
              liveListing: true,
              researchReference: false,
              listingUrl: '/listing/hc-02',
            },
          ],
          warnings: [],
        },
        valuationEvidence: {
          available: true,
          modelVersion: 'v1.3',
          predictedAskingPriceVnd: 3550000000,
        },
      },
    ],
    warnings: ['HEURISTIC_V1_1: điểm quy tắc có trọng số'],
  }
}

const flushMicrotasks = async () => {
  for (let i = 0; i < 6; i++) await Promise.resolve()
}

test('Advisor invalidates a same-token research result and pending response across auth transitions', async t => {
  const snapshot = { status: 'AUTHENTICATED', token: 'advisor-fixture', authGeneration: 1,
    user: { id: 42, role: 'ADMIN', status: 'ACTIVE' } }
  const auth = createStateStore(snapshot)
  let calls = 0, release
  const late = new Promise(resolve => { release = resolve })
  const controller = createUnifiedAdvisorController({
    session: auth,
    api: async (path, opts) => path === '/admin/advisor/research-config' ? { enabled: true }
      : !opts.body.includeResearch ? sampleSafeResponse()
        : ++calls === 1 ? sampleResearchResponse() : late,
  })
  t.after(controller.mount())
  await flushMicrotasks()
  controller.toggleResearch()
  assert.equal(await controller.submit(), true)
  assert.equal(controller.getSnapshot().result.mode, 'INTERNAL_RESEARCH')
  const pending = controller.submit()
  await flushMicrotasks()
  assert.equal(calls, 2)

  auth.set({ ...snapshot, authTransition: true, authGeneration: 2 })
  assert.equal(controller.canViewResearch(), false)
  assert.equal(controller.getSnapshot().result, null)
  auth.set({ ...snapshot, authTransition: false, authGeneration: 2 })
  release(sampleResearchResponse())
  assert.equal(await pending, false)
  await flushMicrotasks()
  assert.equal(controller.getSnapshot().result, null)
  assert.equal(controller.getSnapshot().form.includeResearch, false)
  assert.equal(await controller.submit(), true)
  assert.equal(controller.getSnapshot().result.mode, 'SAFE')
})

test('1 & 5. Valid ADMIN unlocks research via reactive session store (including login after mount) without auto-sending includeResearch=true', async () => {
  clearSession()
  const calls = []
  const ctrl = createUnifiedAdvisorController({
    session,
    baseDistricts: BASE_DISTRICTS,
    api: async (path, opts) => {
      calls.push({ path, opts })
      if (path === '/admin/advisor/research-config') return { enabled: true }
      return opts.body.includeResearch ? sampleResearchResponse() : sampleSafeResponse()
    },
  })
  const unmount = ctrl.mount()
  try {
    // Initially unauthenticated -> no capability probe, research unavailable
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, false)
    assert.equal(calls.length, 0)

    // Case 5: Login ADMIN AFTER mount via real session store
    setSessionState({ status: 'AUTHENTICATED', token: 'jwt-admin-1', user: { id: 1, role: 'ADMIN' } })
    await flushMicrotasks()

    assert.equal(ctrl.getSnapshot().researchAvailable, true)
    assert.equal(ctrl.canViewResearch(), true)
    // Never auto-enables includeResearch!
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)

    // Default submit sends SAFE (includeResearch: false)
    assert.equal(await ctrl.submit(), true)
    assert.equal(calls.at(-1).opts.body.includeResearch, false)
    assert.equal(ctrl.getSnapshot().result.mode, 'SAFE')

    // Case 1: Explicit toggle enables research for valid ADMIN
    ctrl.toggleResearch()
    assert.equal(ctrl.getSnapshot().form.includeResearch, true)
    assert.equal(await ctrl.submit(), true)
    assert.equal(calls.at(-1).opts.body.includeResearch, true)
    assert.equal(ctrl.getSnapshot().result.mode, 'INTERNAL_RESEARCH')
  } finally {
    unmount()
    clearSession()
  }
})

test('2, 3, 4. Anonymous, BUYER, BROKER, research disabled, and config 403 all deny research cleanly', async () => {
  clearSession()
  let configCalls = 0
  let mode = 'disabled'
  const ctrl = createUnifiedAdvisorController({
    session,
    baseDistricts: BASE_DISTRICTS,
    api: async (path) => {
      if (path === '/admin/advisor/research-config') {
        configCalls++
        if (mode === 'forbidden') {
          const err = new Error('Forbidden')
          err.status = 403
          throw err
        }
        return { enabled: false }
      }
      return sampleSafeResponse()
    },
  })
  const unmount = ctrl.mount()
  try {
    // Case 2: Anonymous, BUYER, BROKER
    for (const actor of [
      { status: 'UNAUTHENTICATED', token: null, user: null },
      { status: 'AUTHENTICATED', token: 'jwt-buyer', user: { id: 11, role: 'BUYER' } },
      { status: 'AUTHENTICATED', token: 'jwt-broker', user: { id: 12, role: 'BROKER' } },
    ]) {
      setSessionState(actor)
      await flushMicrotasks()
      assert.equal(ctrl.getSnapshot().researchAvailable, false)
      ctrl.setIncludeResearch(true)
      assert.equal(ctrl.getSnapshot().form.includeResearch, false)
    }
    assert.equal(configCalls, 0)

    // Case 3: ADMIN when research is disabled on server
    mode = 'disabled'
    setSessionState({ status: 'AUTHENTICATED', token: 'jwt-admin', user: { id: 1, role: 'ADMIN' } })
    await flushMicrotasks()
    assert.equal(configCalls, 1)
    assert.equal(ctrl.getSnapshot().researchAvailable, false)
    ctrl.setIncludeResearch(true)
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)

    // Case 4: ADMIN when config request returns 403
    mode = 'forbidden'
    setSessionState({ status: 'AUTHENTICATED', token: 'jwt-admin-2', user: { id: 2, role: 'ADMIN' } })
    await flushMicrotasks()
    assert.equal(configCalls, 2)
    assert.equal(ctrl.getSnapshot().researchAvailable, false)
    assert.equal(ctrl.getSnapshot().error, '')
  } finally {
    unmount()
    clearSession()
  }
})

test('6, 7, 8, 12, 14. Logout, ADMIN->BUYER, and ADMIN A->ADMIN B revoke all research state, POI, areas, warnings, and district suggestions while keeping SAFE working', async () => {
  clearSession()
  let adminBEnabled = false
  const ctrl = createUnifiedAdvisorController({
    session,
    baseDistricts: BASE_DISTRICTS,
    api: async (path, opts) => {
      if (path === '/admin/advisor/research-config') {
        const uid = session.getSnapshot().user?.id
        return { enabled: uid === 100 ? true : adminBEnabled }
      }
      return opts.body.includeResearch ? sampleResearchResponse('Quận Nghiên Cứu Riêng') : sampleSafeResponse()
    },
  })
  const unmount = ctrl.mount()
  try {
    // Login ADMIN A (id: 100) and load research result + select POI
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-a', user: { id: 100, role: 'ADMIN' } })
    await flushMicrotasks()
    ctrl.setIncludeResearch(true)
    assert.equal(await ctrl.submit(), true)
    ctrl.setSelectedPoiId('poi-hc-school-1')

    assert.equal(ctrl.getSnapshot().result.mode, 'INTERNAL_RESEARCH')
    assert.equal(ctrl.getSnapshot().submitted.includeResearch, true)
    assert.equal(ctrl.getSnapshot().selectedPoiId, 'poi-hc-school-1')
    assert.ok(ctrl.getDistrictSuggestions().includes('Quận Nghiên Cứu Riêng'))

    // Case 14 (View helper defense-in-depth): even if stale research result were passed to AdvisorResults with canViewResearch=false, it returns null!
    assert.equal(resolveAdvisorResultsView(ctrl.getSnapshot().result, false), null)

    // Case 6: Logout after having research result
    clearSession()
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, false)
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)
    assert.equal(ctrl.getSnapshot().result, null)
    assert.equal(ctrl.getSnapshot().submitted, null)
    assert.equal(ctrl.getSnapshot().selectedPoiId, '')
    assert.equal(ctrl.getDistrictSuggestions().includes('Quận Nghiên Cứu Riêng'), false)

    // Re-login ADMIN A, load research result again, then Case 7: switch ADMIN -> BUYER
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-a2', user: { id: 100, role: 'ADMIN' } })
    await flushMicrotasks()
    ctrl.setIncludeResearch(true)
    assert.equal(await ctrl.submit(), true)
    ctrl.setSelectedPoiId('poi-2')

    setSessionState({ status: 'AUTHENTICATED', token: 'tok-buyer', user: { id: 100, role: 'BUYER' } })
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, false)
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)
    assert.equal(ctrl.getSnapshot().result, null)
    assert.equal(ctrl.getSnapshot().submitted, null)
    assert.equal(ctrl.getSnapshot().selectedPoiId, '')
    assert.equal(ctrl.getDistrictSuggestions().includes('Quận Nghiên Cứu Riêng'), false)

    // Case 12: SAFE request still works normally after role change!
    assert.equal(await ctrl.submit(), true)
    assert.equal(ctrl.getSnapshot().result.mode, 'SAFE')
    assert.equal(ctrl.getSnapshot().result.recommendedProperties.length, 1)

    // Re-login ADMIN A, load research result, then Case 8: switch ADMIN A (100) -> ADMIN B (200)
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-a3', user: { id: 100, role: 'ADMIN' } })
    await flushMicrotasks()
    ctrl.setIncludeResearch(true)
    assert.equal(await ctrl.submit(), true)
    assert.equal(ctrl.getSnapshot().result.mode, 'INTERNAL_RESEARCH')

    adminBEnabled = true
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-b', user: { id: 200, role: 'ADMIN' } })
    // Immediately on switch (before ADMIN B's config even settles), ADMIN A's research result is wiped!
    assert.equal(ctrl.getSnapshot().result, null)
    assert.equal(ctrl.getSnapshot().submitted, null)
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, true)
    assert.equal(ctrl.getSnapshot().result, null)
  } finally {
    unmount()
    clearSession()
  }
})

test('9, 10, 11, 13. In-flight abort on logout, delayed research response after permission loss/account switch, 401/403 revocation, and delayed capability probe rejection', async () => {
  clearSession()
  const pendingConfig = []
  const pendingConsult = []
  let nextConsultError = null

  const ctrl = createUnifiedAdvisorController({
    session,
    baseDistricts: BASE_DISTRICTS,
    api: (path, opts) => {
      if (path === '/admin/advisor/research-config') {
        return new Promise((resolve, reject) => {
          pendingConfig.push({ opts, resolve, reject })
        })
      }
      if (nextConsultError) {
        const err = nextConsultError
        nextConsultError = null
        return Promise.reject(err)
      }
      return new Promise((resolve, reject) => {
        pendingConsult.push({ opts, resolve, reject })
      })
    },
  })
  const unmount = ctrl.mount()
  try {
    // Case 13: ADMIN A mounts -> config probe #0 pending -> switches to ADMIN B (#1 returns false) -> late probe #0 resolves true!
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-a', user: { id: 10, role: 'ADMIN' } })
    await flushMicrotasks()
    assert.equal(pendingConfig.length, 1)

    setSessionState({ status: 'AUTHENTICATED', token: 'tok-b', user: { id: 20, role: 'ADMIN' } })
    await flushMicrotasks()
    assert.equal(pendingConfig[0].opts.signal.aborted, true)
    assert.equal(pendingConfig.length, 2)

    pendingConfig[1].resolve({ enabled: false })
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, false)

    // Late arrival of ADMIN A's enabled=true MUST NOT re-enable research for ADMIN B!
    pendingConfig[0].resolve({ enabled: true })
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, false)

    // Now login ADMIN C (id: 30) with enabled=true
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-c', user: { id: 30, role: 'ADMIN' } })
    await flushMicrotasks()
    pendingConfig.at(-1).resolve({ enabled: true })
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().researchAvailable, true)

    // Case 9 & 10: Start research request -> logout while in-flight -> delayed research response resolves later
    ctrl.setIncludeResearch(true)
    const inFlightPromise = ctrl.submit()
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().busy, true)
    const activeConsult = pendingConsult.at(-1)
    assert.ok(activeConsult.opts.signal)
    assert.equal(activeConsult.opts.signal.aborted, false)

    // Logout while request is pending
    clearSession()
    assert.equal(activeConsult.opts.signal.aborted, true)
    assert.equal(ctrl.getSnapshot().busy, false)
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)
    assert.equal(await inFlightPromise, false)

    // Delayed research response resolves after logout -> MUST NOT populate result, areas, warnings, or suggestions
    activeConsult.resolve(sampleResearchResponse('Quận Rò Rỉ Muộn'))
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().result, null)
    assert.equal(ctrl.getSnapshot().submitted, null)
    assert.equal(ctrl.getDistrictSuggestions().includes('Quận Rò Rỉ Muộn'), false)

    // Case 10b: ADMIN C starts research request -> switches to ADMIN D (also ADMIN!) before ADMIN C's response arrives
    setSessionState({ status: 'AUTHENTICATED', token: 'tok-c2', user: { id: 30, role: 'ADMIN' } })
    await flushMicrotasks()
    pendingConfig.at(-1).resolve({ enabled: true })
    await flushMicrotasks()
    ctrl.setIncludeResearch(true)
    const adminCPromise = ctrl.submit()
    await flushMicrotasks()
    const adminCConsult = pendingConsult.at(-1)

    setSessionState({ status: 'AUTHENTICATED', token: 'tok-d', user: { id: 40, role: 'ADMIN' } })
    await flushMicrotasks()
    pendingConfig.at(-1).resolve({ enabled: true })
    await flushMicrotasks()
    assert.equal(await adminCPromise, false)
    adminCConsult.resolve(sampleResearchResponse('Quận Của Admin C'))
    await flushMicrotasks()
    assert.equal(ctrl.getSnapshot().result, null)
    assert.equal(ctrl.getDistrictSuggestions().includes('Quận Của Admin C'), false)

    // Case 11: Research request fails with 403 -> revokes researchAvailable & includeResearch, clears research state, shows error
    ctrl.setIncludeResearch(true)
    const forbidden = new Error('Forbidden')
    forbidden.status = 403
    nextConsultError = forbidden
    assert.equal(await ctrl.submit(), false)
    assert.equal(ctrl.getSnapshot().researchAvailable, false)
    assert.equal(ctrl.getSnapshot().form.includeResearch, false)
    assert.equal(ctrl.getSnapshot().result, null)
    assert.match(ctrl.getSnapshot().error, /quyền/)
  } finally {
    unmount()
    clearSession()
  }
})
