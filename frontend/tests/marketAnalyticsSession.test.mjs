import test from 'node:test'
import assert from 'node:assert/strict'
import { createStateStore } from '../src/shared/state/createStateStore.js'
import { createMarketAnalyticsController } from '../src/features/market/marketAnalyticsState.js'
import { marketResponse } from '../e2e/pr37-market-fixture.mjs'

const guest = { status: 'UNAUTHENTICATED', token: null, user: null }
const admin = { status: 'AUTHENTICATED', token: 'fixture-a', user: { id: 1, role: 'ADMIN', status: 'ACTIVE' } }
const buyer = { ...admin, user: { ...admin.user, role: 'BUYER' } }
const broker = { ...admin, user: { ...admin.user, role: 'BROKER' } }
const tick = () => new Promise(resolve => setImmediate(resolve))

function setup(t, initial, onResearch = async () => marketResponse({ research: true, sufficient: true })) {
  const calls = []
  const session = createStateStore(initial)
  const controller = createMarketAnalyticsController({
    session,
    api(url, options) {
      const query = new URL(url, 'http://fixture.invalid').searchParams
      const research = query.get('includeResearch') === 'true'
      calls.push({ research, source: query.get('source'), authenticated: options.authenticated, signal: options.signal })
      return research ? onResearch() : Promise.resolve(marketResponse())
    },
  })
  t.after(controller.mount())
  return { session, controller, calls, state: controller.getSnapshot }
}

for (const [name, initial] of [['anonymous', guest], ['BUYER', buyer], ['BROKER', broker],
  ['unavailable', { ...admin, status: 'UNAVAILABLE' }],
  ['locked', { ...admin, user: { ...admin.user, status: 'LOCKED' } }]]) {
  test(name + ' can only request SAFE even if a caller tries to opt in', async t => {
    const { controller, calls, state } = setup(t, initial)
    await controller.setResearchEnabled(true)
    await controller.patchFilter('source', 'TINIX_RESEARCH')
    assert.equal(calls.length, 3)
    assert.ok(calls.every(call => !call.research && !call.authenticated && call.source !== 'TINIX_RESEARCH'))
    assert.equal(state().canRequestResearch, false)
    assert.equal(state().researchAvailable, false)
    assert.equal(state().data.meta.researchIncluded, false)
  })
}

test('ADMIN page load is SAFE and explicit opt-in succeeds only after the server authorizes it', async t => {
  const { controller, calls, state } = setup(t, admin)
  await tick()
  assert.deepEqual(calls.map(call => call.research), [false])
  assert.equal(state().canRequestResearch, true)
  assert.equal(state().researchAvailable, false)
  await controller.patchFilter('source', 'TINIX_RESEARCH')
  assert.equal(calls.at(-1).research, false)
  await controller.setResearchEnabled(true)
  assert.equal(calls.at(-1).authenticated, true)
  assert.equal(state().researchAvailable, true)
  assert.equal(state().data.meta.researchIncluded, true)
  await controller.setResearchEnabled(false)
  assert.equal(state().researchAvailable, false)
  assert.equal(state().data.meta.researchLicense, null)
})

for (const status of [401, 403]) {
  test('research HTTP ' + status + ' revokes capability and falls back to SAFE', async t => {
    const { controller, calls, state } = setup(t, admin, async () => { throw Object.assign(Error('fixture denial'), { status }) })
    await controller.setResearchEnabled(true)
    assert.deepEqual(calls.map(call => call.research), [false, true, false])
    assert.equal(state().filters.includeResearch, false)
    assert.equal(state().researchAvailable, false)
    assert.equal(state().data.meta.researchLicense, null)
    assert.match(state().researchError, /không được phép/)
    await controller.retry()
    assert.equal(calls.at(-1).research, false)
  })
}

const transitions = [
  ['same-token role downgrade', buyer],
  ['same-user token replacement', { ...admin, token: 'fixture-b' }],
  ['ADMIN A to ADMIN B', { ...admin, user: { ...admin.user, id: 2 } }],
  ['logout', guest],
  ['session unavailable', { ...admin, status: 'UNAVAILABLE' }],
  ['account locked', { ...admin, user: { ...admin.user, status: 'LOCKED' } }],
]

for (const [name, next] of transitions) {
  test(name + ' clears completed results and rejects a delayed response, including rapid restoration', async t => {
    let release
    let count = 0
    const fixture = () => {
      if (count++ === 0) return Promise.resolve(marketResponse({ research: true, sufficient: true }))
      return new Promise(resolve => { release = resolve })
    }
    const { controller, session, calls, state } = setup(t, admin, fixture)
    await controller.setResearchEnabled(true)
    assert.equal(state().researchAvailable, true)
    const pending = controller.patchFilter('district', 'Hòa Vang')
    const signal = calls.at(-1).signal
    assert.equal(calls.at(-1).research, true)
    session.set(next)
    assert.equal(signal.aborted, true)
    assert.equal(state().data, null)
    assert.equal(state().researchAvailable, false)
    session.set(admin)
    assert.equal(state().canRequestResearch, true)
    assert.equal(state().filters.includeResearch, false)
    release(marketResponse({ research: true, sufficient: true }))
    assert.equal(await pending, null)
    await tick()
    assert.deepEqual(calls.map(call => call.research), [false, true, true, false])
    assert.equal(state().researchAvailable, false)
    assert.equal(state().data.meta.researchIncluded, false)
  })
}

test('a public response with research metadata is discarded', async t => {
  const controller = createMarketAnalyticsController({
    session: createStateStore(guest),
    api: async () => marketResponse({ research: true, sufficient: true }),
  })
  t.after(controller.mount())
  await tick()
  assert.equal(controller.getSnapshot().data, null)
  assert.match(controller.getSnapshot().error, /nghiên cứu không được phép/)
})
