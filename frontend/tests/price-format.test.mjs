import test from 'node:test'
import assert from 'node:assert/strict'
import { compactPrice, price } from '../src/features/property/property.js'

for (const [input, expected] of [['2000000000','2 tỷ'],['10000000000','10 tỷ'],['50000000','50 triệu'],['100000000','100 triệu'],['8500000000','8,5 tỷ'],['3650000000','3,65 tỷ'],['12500000','12,5 triệu'],['0','0 ₫'],['999999','999.999 ₫'],['999999999','≈ 1 tỷ'],['2345000000','≈ 2,35 tỷ']]) {
  test('compact price '+input,()=>assert.equal(compactPrice({priceExact:input,priceUnit:'TOTAL'}),expected))
}
test('rent labels retain their billing period',()=>{
  for(const [unit,suffix] of [['PER_MONTH','/tháng'],['PER_YEAR','/năm'],['PER_DAY','/ngày']])assert.equal(compactPrice({price:12000000,priceUnit:unit}),'12 triệu'+suffix)
})
test('exact field takes priority and large prices avoid Number conversion',()=>{
  assert.equal(compactPrice({priceExact:'9999999999999999.99',price:1}),'≈ 10.000.000 tỷ')
  assert.equal(compactPrice({priceExact:'2000000000',price:1}),'2 tỷ')
})
test('invalid or absent price is not fabricated as zero or negotiable',()=>{
  for(const input of [null,undefined,'bad','-1','NaN','Infinity'])assert.equal(compactPrice({price:input}),'—')
})
test('full-price formatter and source value remain unchanged',()=>{
  const property={priceExact:'2345000000.25',priceUnit:'PER_MONTH'}
  assert.equal(price(property),'2.345.000.000,25 ₫/tháng');assert.equal(property.priceExact,'2345000000.25')
})
