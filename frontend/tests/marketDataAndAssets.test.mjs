import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { DISTRICT_LIST, DISTRICT_PROFILES, getDistrictProfile } from '../src/features/market/marketData.js'
import { approvedFiles, publicFiles } from '../build/publicAssets.mjs'
import { hasNewNewsSnapshot } from '../src/features/news/newsPresentation.js'
import { NEWS_ILLUSTRATIONS, usableNewsIllustration } from '../src/features/news/newsIllustrations.js'
import { NEWS_EDITORIAL_COVERS, newsCardMedia, usableEditorialCover } from '../src/features/news/newsEditorialCovers.js'
import { NEWS_IMAGE_PERMISSIONS, permittedNewsImage } from '../src/features/news/newsImagePolicy.js'
import { safeNewsUrl } from '../src/features/news/useNews.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_DIR = path.resolve(__dirname, '..')
const PUBLIC_DIR = path.join(FRONTEND_DIR, 'public')

test('DISTRICT_PROFILES covers all 7 Da Nang administrative units including Hòa Vang', () => {
  assert.equal(DISTRICT_LIST.length, 7)
  for (const expected of ['Sơn Trà', 'Hải Châu', 'Liên Chiểu', 'Ngũ Hành Sơn', 'Cẩm Lệ', 'Thanh Khê', 'Hòa Vang']) {
    assert.ok(DISTRICT_LIST.includes(expected), `Missing district: ${expected}`)
    assert.ok(DISTRICT_PROFILES[expected]?.slug)
  }
})

test('getDistrictProfile resolves Hòa Vang variants and returns null for unknown slugs (never falls back to Sơn Trà)', () => {
  assert.equal(getDistrictProfile('hoa-vang')?.shortName, 'Hòa Vang')
  assert.equal(getDistrictProfile('Hòa Vang')?.shortName, 'Hòa Vang')
  assert.equal(getDistrictProfile('Hoà Vang')?.shortName, 'Hòa Vang')
  assert.equal(getDistrictProfile('Huyện Hòa Vang')?.shortName, 'Hòa Vang')
  assert.equal(getDistrictProfile('Quận Sơn Trà')?.shortName, 'Sơn Trà')

  assert.equal(getDistrictProfile('khong-ton-tai'), null)
  assert.equal(getDistrictProfile('unknown-district'), null)
  assert.equal(getDistrictProfile(''), null)
  assert.equal(getDistrictProfile(null), null)
})

test('marketData and Market UI components contain zero fabricated market numbers or false V1.3 badges', () => {
  for (const profile of Object.values(DISTRICT_PROFILES)) {
    assert.equal('viewsCount' in profile, false)
    assert.equal('activeListingsCount' in profile, false)
    assert.equal('priceHistory' in profile, false)
    assert.equal('aiInsights' in profile, false)
    assert.equal('avgPricePerM2' in profile.macro, false)
    assert.equal('priceGrowthYoY' in profile.macro, false)
    assert.equal('liquidityRating' in profile.macro, false)
  }

  for (const rel of [
    'src/features/market/marketData.js',
    'src/features/market/MarketInsightsView.jsx',
    'src/features/market/PriceTrendChart.jsx',
    'src/features/market/TopSearchedAreas.jsx',
  ]) {
    const src = fs.readFileSync(path.join(FRONTEND_DIR, rel), 'utf8')
    assert.doesNotMatch(src, /AI Valuation V1\.3|MODEL V1\.3|priceGrowthYoY|liquidityRating|145,0 triệu\/m²|37\.637/)
    assert.doesNotMatch(src, /media\/areas\/|hero-poster\.jpg/)
  }
})

test('publicAssets allowlist excludes unverified district images and every approved file exists on disk', () => {
  assert.equal(publicFiles.some((f) => f.startsWith('media/areas/')), false)
  assert.equal(publicFiles.includes('vite.svg'), false)

  const resolved = approvedFiles(PUBLIC_DIR)
  assert.equal(resolved.length, publicFiles.length, 'Every allowlisted public file must exist on disk')
})

test('News provenance, publisher image gate, URL sanitizer, and snapshot detector enforce strict contracts', () => {
  assert.deepEqual(NEWS_IMAGE_PERMISSIONS, {})
  assert.equal(
    permittedNewsImage({
      sourceUrl: 'https://vnexpress.net',
      imageUrl: 'https://vcdn1-vnexpress.vnecdn.net/2026/11/test.jpg',
    }),
    null
  )
  assert.equal(safeNewsUrl('javascript:alert(1)'), null)
  assert.equal(safeNewsUrl('http://example.com/news'), null)
  assert.equal(safeNewsUrl('https://user:pass@example.com/news'), null)
  assert.equal(safeNewsUrl('https://vnexpress.net/bai-viet-1.html'), 'https://vnexpress.net/bai-viet-1.html')

  for (const img of Object.values(NEWS_ILLUSTRATIONS)) {
    assert.equal(usableNewsIllustration(img), true, `Invalid illustration metadata: ${img.id}`)
    assert.equal(fs.existsSync(path.join(PUBLIC_DIR, img.src.replace(/^\//, ''))), true, `Missing file: ${img.src}`)
  }
  for (const cover of Object.values(NEWS_EDITORIAL_COVERS)) {
    assert.equal(usableEditorialCover(cover), true, `Invalid editorial cover metadata: ${cover.id}`)
    assert.equal(fs.existsSync(path.join(PUBLIC_DIR, cover.src.replace(/^\//, ''))), true, `Missing file: ${cover.src}`)
  }

  const media = newsCardMedia({
    id: 'art-1',
    title: 'Diễn biến thị trường bất động sản quý cuối năm',
    summary: 'Tổng hợp thông tin từ nguồn RSS.',
    category: 'Thị trường BĐS',
    sourceUrl: 'https://vnexpress.net',
    imageUrl: 'https://vcdn1-vnexpress.vnecdn.net/2026/11/blocked.jpg',
  })
  assert.ok(media.url?.startsWith('/images/news/editorial-'))
  assert.equal(media.illustration?.kind, 'AI_CONCEPT')

  assert.equal(hasNewNewsSnapshot([{ lastSuccessAt: '2026-11-28T05:00:00Z' }], '2026-11-28T04:00:00Z'), true)
  assert.equal(hasNewNewsSnapshot({ sources: [{ lastSuccessAt: '2026-11-28T05:00:00Z' }] }, '2026-11-28T04:00:00Z'), true)
  assert.equal(hasNewNewsSnapshot(null, '2026-11-28T04:00:00Z'), false)
})
