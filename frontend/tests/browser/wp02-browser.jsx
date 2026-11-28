
import React from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const id = '10000000-0000-4000-8000-000000000000'
const district = 'Hải Châu'
const house = { id, status: 'PUBLISHED', transactionType: 'SALE', priceUnit: 'TOTAL', currency: 'VND',
  title: 'Nhà fixture', propertyType: 'HOUSE', district, city: 'Đà Nẵng', ward: 'Hòa Cường Bắc',
  price: 5200000000, areaSqm: 80, contentVersion: 1, latitude: null, longitude: null,
  bedrooms: 3, bathrooms: 2, images: [], amenities: [] }
const list = { candidateId: 'property:sample', sourceKind: 'SMARTPROP', sourceLabel: 'SmartProp',
  liveListing: true, researchReference: false, district, ward: house.ward, propertyType: 'HOUSE', areaSqm: 82,
  askingPriceVnd: 4100000000, similarityScore:.92, featureCoverage:.74, scoreBreakdown:{location:'1.00'}, listingUrl: '/properties/sample' }
const research = { ...list, candidateId: 'tinix:synthetic', sourceKind: 'TINIX_RESEARCH',
  researchReference: true, liveListing: false, listingUrl: null, datasetLicense: 'CC BY-NC 4.0',
  attribution: 'Synthetic TiniX' }
const cohort = (purpose, available = true) => ({
  purpose, status: available ? 'AVAILABLE' : 'INSUFFICIENT_EVIDENCE', retrievedCandidateCount: available ? 8 : 1,
  uniqueEligibleCandidateCount: available ? 6 : 1, returnedSampleCount: 1, scanComplete: true,
  scannedCohortAskingPrice:{ observations: available ? 6 : 1, medianPriceVnd: available ? 4150000000 : null,
    medianPricePerSqmVnd: available ? 50345000 : null },
  provenance:{ SMARTPROP:{ uniqueEligible: available ? 6 : 1, returned: 1 } }, limitations:['Giá rao, chưa xác nhận giá giao dịch.']
})
const comp = (purpose, available = true) => ({ status:'AVAILABLE', candidateCount:1, searchStage:'DISTRICT',
  comparables: [list], cohort: cohort(purpose, available), warnings: [] })
const estimate = { available:true, modelVersion:'v1.3', predictedAskingPriceVnd: 5280000000, featuresUsed:{areaSqm:80}, missingFeatures: [], warnings:[] }
const advisorProperty = { ...house, liveListing:true, scoreBreakdown:{}, recommendationScore:85,
  priceVnd: house.price, source:{kind:'PROPERTY',recordKey:id},
  comparableEvidence:comp('SIMILAR_LISTING'), valuationComparableEvidence:comp('VALUATION_SUPPORT', false), valuationEvidence:estimate }
window.requests = []
window.heldComparables = []
window.holdComparables = false
window.fixtureResponse = 'available'
window.fetch = async (resource, options = {}) => {
  const url = new URL(typeof resource === 'string' ? resource : resource.url, location.origin)
  const data = options.body ? JSON.parse(options.body) : null
  window.requests.push({ path:url.pathname, method:options.method ?? 'GET', data })
  let status = 200
  let payload = {}
  if (url.pathname.endsWith('/comparables')) {
    if (window.holdComparables) {
      await new Promise(resolve => window.heldComparables.push(resolve))
    } else {
      await new Promise(resolve => setTimeout(resolve, 240))
    }
    payload = { reference: {}, comparables: [list], searchStage:'DISTRICT',
      evidence: cohort(data.purpose, window.fixtureResponse === 'available') }
    if (window.fixtureResponse === 'empty') payload.comparables = []
    if (window.fixtureResponse === 'unavailable') status = 503
    if (window.fixtureResponse === 'research') payload.comparables = [research]
  } else if (url.pathname.endsWith('/model/options')) {
    payload = { model_version:'v1.3', categories:[{category:'Nhà ở', locations:[district]}], location_labels:{[district]:district} }
  } else if (url.pathname.endsWith('/predict')) {
    payload = { model_version: 'v1.3', predicted_asking_price_vnd: 5310000000, features_used:{area_sqm: 80}, missing_features:[], warnings:[] }
  } else if (url.pathname.endsWith('/valuation-options')) {
    payload = { categories: [{category:'Nhà ở', locations:[district]}] }
  } else if (url.pathname.endsWith('/valuation-preview')) {
    payload = estimate
  } else if (url.pathname.endsWith('/properties/' + id)) {
    payload = house
  } else if (url.pathname.endsWith('/points-of-interest')) {
    payload = []
  } else if (url.pathname.endsWith('/users/me')) {
    payload = { id:1, role:'BROKER', displayName:'Fixture' }
  } else {
    status = 404
  }
  return new Response(JSON.stringify(payload), {status, headers:{'content-type':'application/json'}})
}
const { session } = await import('/src/features/auth/api.js')
const {default: Direct} = await import('/src/features/property/ComparablesView.jsx')
const {default: Lookup} = await import('/src/features/property/ComparableEvidenceLookup.jsx')
const {default: Listing} = await import('/src/features/property/ListingDetailView.jsx')
const {default: Valuation} = await import('/src/features/prediction/ValuationPanel.jsx')
const {default: Post} = await import('/src/features/prediction/PostValuationPanel.jsx')
const {default: Advisor} = await import('/src/features/prediction/AdvisorResults.jsx')
const root = createRoot(document.querySelector('#root'))
const render = (component, content) => root.render(<MemoryRouter key={component} initialEntries={['/listing/' + id]}>
  <Routes><Route path="/listing/:id" element={content}/></Routes></MemoryRouter>)
window.setFixtureSession = (role = 'BROKER', status = 'AUTHENTICATED', actor = 1) =>
  session.set({token:'synthetic-fixture', user:{id:actor, role}, status})
window.broker = () => window.setFixtureSession()
window.logoutFixture = () => session.set({token:null, user:null, status:'UNAUTHENTICATED'})
window.lookupCriteria = areaSqm => render('lookup', <Lookup title="Đối chiếu fixture"
  body={{purpose:'VALUATION_SUPPORT', propertyType:'HOUSE', district, areaSqm, limit:5}}/>)
window.releaseComparable = async () => {
  window.heldComparables.shift()()
  // Let the fetch completion and any React updates render before checking the DOM.
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
}
window.broker()
window.showFixture = (component, authorized = true) => {
  const sample = { mode:'SAFE', serviceStatus:{}, recommendedProperties:[advisorProperty], topAreas:[], warnings:[] }
  const internal = { ...sample, mode:'INTERNAL_RESEARCH', recommendedProperties:[
    {...advisorProperty, comparableEvidence: {...advisorProperty.comparableEvidence, comparables:[list,research]}}
  ] }
  if (component === 'direct') render(component, <Direct/>)
  if (component === 'listing') render(component, <Listing/>)
  if (component === 'valuation') render(component, <Valuation initialInput={{category:'Nhà ở', area_sqm:'80', location_feature:district}}/>)
  if (component === 'post') render(component, <Post draft={{propertyType:'Nhà phố', transactionType:'Bán', area:'80',
    valuationLocation:district, district, bedrooms:3, price:'7500000000'}}/>)
  if (component === 'advisor') render(component, <Advisor result={sample} canViewResearch={false}/>)
  if (component === 'internal') render(component, <Advisor result={internal} canViewResearch={authorized}/>)
}
window.showFixture('direct')
