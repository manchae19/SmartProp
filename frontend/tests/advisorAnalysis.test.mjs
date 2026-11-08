import test from 'node:test'
import assert from 'node:assert/strict'
import {
  advisorConsultRequest,
  advisorError,
  effectiveBudgetPreview,
  parseAdvisorBudget,
} from '../src/features/prediction/advisorAnalysis.js'

test('parseAdvisorBudget accepts VN dot-grouped integers', () => {
  assert.equal(parseAdvisorBudget('3.500.000.000'), 3500000000)
  assert.equal(parseAdvisorBudget('1000000'), 1000000)
})

test('parseAdvisorBudget rejects invalid input', () => {
  assert.throws(() => parseAdvisorBudget('abc'))
  assert.throws(() => parseAdvisorBudget('-5'))
  assert.throws(() => parseAdvisorBudget('1,5'))
})

test('effectiveBudgetPreview computes a bounded ceiling', () => {
  const preview = effectiveBudgetPreview('3.500.000.000', 10)
  assert.equal(preview.statedBudgetVnd, 3500000000)
  assert.equal(preview.effectiveCeilingVnd, 3850000000)
})

test('effectiveBudgetPreview rejects an out-of-range flexibility', () => {
  assert.throws(() => effectiveBudgetPreview('3.500.000.000', 40))
})

test('advisorConsultRequest builds a public (SAFE) request', () => {
  const body = advisorConsultRequest({ budgetVnd: '3.500.000.000', budgetFlexibilityPct: 10, purpose: 'LIVING', propertyType: 'ALL', limit: 5 })
  assert.equal(body.purpose, 'LIVING')
  assert.equal(body.includeResearch, false)
  assert.equal(body.propertyType, 'ALL')
})

test('advisorConsultRequest rejects an invalid purpose', () => {
  assert.throws(() => advisorConsultRequest({ budgetVnd: '1.000.000.000', purpose: 'NOPE', propertyType: 'ALL', limit: 5 }))
})

test('advisorError maps HTTP statuses to user messages', () => {
  assert.match(advisorError({ status: 401 }), /Phiên đăng nhập/)
  assert.match(advisorError({ status: 403 }), /quyền/)
  assert.match(advisorError({ status: 429 }), /nhiều yêu cầu/)
  assert.match(advisorError({ status: 503 }), /tạm gián đoạn/)
})
