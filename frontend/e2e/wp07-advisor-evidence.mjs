import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { join } from 'node:path'
import { advisorPath, prepareAdvisor, waitResponse } from '../tests/wp04/browser/workflows.mjs'

const { WP07_APP: app, WP07_API: api, WP07_OUTPUT: output } = process.env
const mode = process.argv[2]
assert.ok(['baseline', 'candidate'].includes(mode))
for (const address of [app, api]) assert.match(address, /^http:\/\/127\.0\.0\.1:\d{2,5}$/)
assert.ok(output, 'Set a disposable evidence directory')
mkdirSync(output, { recursive: true })
const criteria = {
  budgetVnd: 7000000000, budgetFlexibilityPct: 0, purpose: 'LIVING', propertyType: 'HOUSE',
  minAreaSqm: 60, limit: 5, includeResearch: false, includeValuation: true, includeComparables: true,
}
const post = (body) => fetch(api + advisorPath, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  signal: AbortSignal.timeout(45000),
})

function assertSafe(body) {
  assert.equal(body.mode, 'SAFE')
  assert.equal(body.criteria.includeResearch, false)
  for (const property of body.recommendedProperties) {
    assert.equal(property.researchReference, false)
    assert.equal(property.liveListing, true)
    assert.ok(['PROPERTY', 'EXTERNAL'].includes(property.source.kind))
    assert.ok(property.priceVnd <= body.criteria.effectiveCeilingVnd)
    assert.ok(!property.evidence?.some(entry => entry.source === 'TINIX_RESEARCH'))
    for (const comparable of [property.comparableEvidence, property.valuationComparableEvidence]) {
      assert.ok(!comparable?.comparables?.some(item => item.researchReference || item.sourceKind === 'TINIX_RESEARCH'))
    }
  }
}

async function snapshot(district) {
  const response = await post({ ...criteria, district })
  assert.equal(response.status, 200)
  const body = await response.json()
  assertSafe(body)
  assert.ok(body.recommendedProperties.length > 0)
  return body.recommendedProperties.map(property => {
    assert.equal(property.district, district)
    assert.equal(property.valuationEvidence.modelVersion, 'v1.3')
    assert.ok(Number.isSafeInteger(property.valuationEvidence.predictedAskingPriceVnd))
    assert.equal(property.comparableEvidence.cohort.purpose, 'SIMILAR_LISTING')
    assert.equal(property.valuationComparableEvidence.cohort.purpose, 'VALUATION_SUPPORT')
    if (mode === 'baseline') {
      assert.equal(property.evidence, undefined)
    } else {
      assert.equal(property.evidence.length, 6)
      assert.ok(property.evidence.every(item => item.observedAt == null && item.generatedAt == null && item.freshness === 'UNKNOWN'))
      assert.ok(property.evidence.every(item => Object.keys(item).every(key =>
        ['kind', 'source', 'status', 'observedAt', 'generatedAt', 'freshness', 'limitations', 'reference'].includes(key))))
    }
    const { valuationEvidence } = property
    return {
      title: property.title,
      asking: property.priceVnd,
      valuation: valuationEvidence.predictedAskingPriceVnd,
      adjusted: valuationEvidence.explanation?.calibration?.adjusted_price_vnd,
      treeShap: valuationEvidence.explanation?.status,
      recommendationScore: property.recommendationScore,
      similarCohort: property.comparableEvidence.cohort.scannedCohortAskingPrice,
      supportCohort: property.valuationComparableEvidence.cohort.scannedCohortAskingPrice,
    }
  }).sort((left, right) => left.title.localeCompare(right.title))
}

const snapshots = (await Promise.all([snapshot('Cẩm Lệ'), snapshot('Hải Châu')])).flat()
assert.ok(snapshots.some(row => row.asking !== row.valuation))
assert.ok(snapshots.every(row => String(row.adjusted) === String(row.valuation) && row.treeShap === 'AVAILABLE'))
const snapshotPath = join(output, 'wp07-baseline-prices.json')
if (mode === 'baseline') {
  writeFileSync(snapshotPath, JSON.stringify(snapshots, null, 2) + '\n')
  console.log('Baseline captured on Spring and FastAPI for ' + snapshots.length + ' listings')
} else {
  assert.deepEqual(snapshots, JSON.parse(readFileSync(snapshotPath, 'utf8')))
  const rejectResearch = await post({ ...criteria, includeResearch: true })
  assert.ok([401, 403].includes(rejectResearch.status), 'Guest research consult must be denied')
  const noMatches = await post({ ...criteria, budgetVnd: 100, district: 'Cẩm Lệ' })
  assert.equal(noMatches.status, 200)
  const emptyBody = await noMatches.json()
  assertSafe(emptyBody)
  assert.deepEqual(emptyBody.recommendedProperties, [])

  const require = createRequire(import.meta.url)
  const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright')
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME })
  try {
    for (const width of [1440, 390, 320]) {
      const page = await browser.newPage({ viewport: { width, height: 1050 } })
      const errors = []
      page.on('pageerror', error => errors.push(error.message))
      try {
        const submit = await prepareAdvisor(page, app)
        const request = waitResponse(page, advisorPath)
        await submit.click()
        const response = await request
        assert.equal(response.status(), 200)
        const body = await response.json()
        assertSafe(body)
        const card = page.locator('[data-advisor-property]').first()
        await card.waitFor()
        const price = await card.locator('[data-valuation-evidence] .ev-price').innerText()
        assert.equal(price.replace(/\D/g, ''), String(body.recommendedProperties[0].valuationEvidence.predictedAskingPriceVnd))
        assert.match(await card.locator('.ar-price').innerText(), /^Giá rao/)
        assert.equal(await card.locator('[data-comparable-evidence]').count(), 2)
        await card.locator('[data-wp07-evidence] summary').click()
        await card.locator('[data-evidence-kind="VALUATION"]').waitFor()
        assert.equal(await card.locator('[data-evidence-kind]').count(), 6)
        assert.equal(await card.locator('[data-evidence-freshness="UNKNOWN"]').count(), 6)
        assert.equal(await card.getByTestId('valuation-explanation-panel').getAttribute('data-explanation-status'), 'AVAILABLE')
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1))
        assert.deepEqual(errors, [])
        await card.screenshot({ path: join(output, 'wp07-advisor-' + width + '.png') })
        console.log('Real Advisor flow at ' + width + ' px PASS')
      } finally {
        await page.close()
      }
    }

    // The current producers omit timestamps. Supply one only in this browser fault-injection fixture.
    const page = await browser.newPage({ viewport: { width: 390, height: 1050 } })
    await page.route('**/api/v1/advisor/consult', async route => {
      const original = await route.fetch()
      const body = await original.json()
      const evidence = body.recommendedProperties[0].evidence
      evidence.find(item => item.kind === 'LOCATION').observedAt = new Date(Date.now() - 91 * 86400000).toISOString()
      evidence.find(item => item.kind === 'RECOMMENDATION').source = null
      evidence.find(item => item.kind === 'EXPLANATION').reference = 'https://example.invalid/'
      body.recommendedProperties[1].valuationEvidence.explanation = {
        explanation_version: '1.0', status: 'UNAVAILABLE', limitations: ['Fixture'],
      }
      await route.fulfill({ response: original, json: body })
    })
    const submit = await prepareAdvisor(page, app)
    const request = waitResponse(page, advisorPath)
    await submit.click()
    const body = await (await request).json()
    const card = page.locator('[data-advisor-property]').first()
    await card.locator('[data-wp07-evidence] summary').click()
    await card.getByText('Dữ liệu cũ hơn 90 ngày', { exact: true }).waitFor()
    await card.getByText(/Chưa rõ nguồn/).waitFor()
    assert.equal(await card.locator('[data-evidence-kind="EXPLANATION"]').count(), 0)
    const price = await card.locator('[data-valuation-evidence] .ev-price').innerText()
    assert.equal(price.replace(/\D/g, ''), String(body.recommendedProperties[0].valuationEvidence.predictedAskingPriceVnd))
    assert.equal(await card.getByTestId('valuation-explanation-panel').getAttribute('data-explanation-status'), 'AVAILABLE')
    const unavailable = page.locator('[data-advisor-property]').nth(1)
    await unavailable.locator('[data-wp07-evidence] summary').click()
    const explanation = unavailable.locator('[data-evidence-kind="EXPLANATION"]')
    await explanation.waitFor()
    assert.equal(await explanation.getAttribute('data-evidence-status'), 'UNAVAILABLE')
    assert.equal(await unavailable.getByTestId('valuation-explanation-panel').getAttribute('data-explanation-status'), 'UNAVAILABLE')
    assert.ok(await unavailable.locator('[data-valuation-evidence] .ev-price').isVisible())
    await page.close()
    console.log('Browser malformed metadata, missing source, stale observation and unavailable TreeSHAP PASS (mutated HTTP)')
  } finally {
    await browser.close()
  }

  writeFileSync(join(output, 'wp07-runtime-price-proof.json'), JSON.stringify({
    equalToBaseline: true, concurrentDistricts: 2, comparedListings: snapshots.length,
    guestResearchDenied: true, emptySafeWithoutFallback: true, browserViewports: [1440, 390, 320],
    currentProducersFreshness: 'UNKNOWN', mutatedMetadataBrowser: 'PASS', rows: snapshots,
  }, null, 2) + '\n')
}
