import test from 'node:test'
import assert from 'node:assert/strict'
import {advisorRequest, parseAdvisorBudget, formatAdvisorBudget} from '../src/services/advisor.js'

test('arbitrary VND budgets retain every dong, including contract maximum', () => {
  for (const amount of ['750000000','1250000000','2350000000','3780000000','4650000000','8900000000','15500000000','2350000001','999999999999999','1']) {
    const grouped = new Intl.NumberFormat('vi-VN').format(BigInt(amount))
    assert.equal(formatAdvisorBudget(amount),grouped)
    assert.equal(parseAdvisorBudget(grouped),Number(amount))
    assert.equal(advisorRequest({budgetVnd:grouped,purpose:'LIVING',propertyType:'ALL'}).budgetVnd,Number(amount))
    assert.equal(JSON.parse(JSON.stringify({budgetVnd:parseAdvisorBudget(grouped)})).budgetVnd,Number(amount))
  }
})

test('invalid currency, fractions, malformed groups and excessive budgets fail explicitly', () => {
  for (const amount of ['', ' ', '0', '-1', '+20', '2,35', '2.350', '1.25.000.000', '1e9', 'Infinity', 'NaN', '2350000000đ', '1000000000000000', '9'.repeat(200)]) {
    // 2.350 is valid Vietnam grouping: 2,350 VND, never 2.35 billion.
    if (amount === '2.350') assert.equal(parseAdvisorBudget(amount),2350)
    else assert.throws(()=>parseAdvisorBudget(amount),/ngân sách|Ngân sách/)
  }
})

test('legacy billion-unit callers use exact integer arithmetic too', () => {
  const f={purpose:'LIVING',propertyType:'ALL'}
  assert.equal(advisorRequest({...f,budgetBillions:'999999.999999999'}).budgetVnd,999999999999999)
  assert.equal(advisorRequest({...f,budgetBillions:'2.350000001'}).budgetVnd,2350000001)
  assert.equal(advisorRequest({...f,budgetVnd:'2.350.000.001',budgetBillions:'1'}).budgetVnd,2350000001)
})
