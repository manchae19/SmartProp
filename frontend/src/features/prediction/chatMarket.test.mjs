import test from 'node:test';
import assert from 'node:assert/strict';
import { publicChatBody } from '../../../server/publicChat.mjs';
import { publicChatResponse, citationHref } from './chat.js';
import { chatPresentation } from './chatPresentation.js';
function packet() {
  const query = {district:'Sơn Trà', propertyType:'APARTMENT', transactionType:'SALE', priceUnit:'TOTAL'};
  const asOf = new Date().toISOString();
  return {mode:'SAFE', answer:'Giá chào hiện tại từ 2 tin SmartProp, không phải giá giao dịch.', generationMode:'EVIDENCE_ONLY', retrievalMode:'TOOL_EVIDENCE_ONLY', recommendedProperties:[], dataLimitations:[],
    citations:[{sourceId:'market-summary:fixture', url:'/api/v1/properties/market-summary?'+new URLSearchParams(query), version:asOf, contentHash:'a'.repeat(64), scope:'PUBLIC', kind:'MARKET_SUMMARY', title:'Giá chào SmartProp'}],
    evidence:{intent:'MARKET_PRICE',responseKind:'MARKET_PRICE_EVIDENCE', marketSummary:{sourceId:'market-summary:fixture',query,asOf,source:'CURRENT_PUBLISHED_ASKING_PRICES',historyAvailable:false,amounts:{count:2,totalAskingPrice:'6000000000',averageAskingPrice:'3000000000',minimumAskingPrice:'2000000000',maximumAskingPrice:'4000000000',weightedAskingPricePerSqm:'50000000'}}}};
}
test('relay preserves market filters and client accepts sanitized packet',()=>{
  const result=publicChatBody(packet());
  assert.equal(publicChatResponse(result),result);
  assert.equal(new URL(result.citations[0].url,'https://test.invalid').searchParams.get('district'),'Sơn Trà');
});
test('market display uses evidence answer without asking for a budget',()=>{
  const data=packet();assert.equal(chatPresentation(data).summary,data.answer);
  assert.equal(chatPresentation(data).citations[0].label,'Thống kê giá chào SmartProp');
});
test('reject altered source, filters and numbers',()=>{
  for(const alter of [p=>p.evidence.marketSummary.amounts.count=-1,p=>p.evidence.marketSummary.source='FAKE',p=>p.evidence.marketSummary.query.district='Other',p=>p.citations[0].url+='&district=Other',p=>p.citations[0].url+='&url=https://example.org']){
    const p=packet();alter(p);assert.throws(()=>publicChatBody(p));
  }
});
test('only fixed same-origin market source links are rendered',()=>{
  const c=packet().citations[0];
  assert.equal(citationHref({...c,url:'//evil.invalid/api/v1/properties/market-summary'},[]),null);
  assert.equal(citationHref({...c,url:'/api/v1/properties/market-summary?transactionType=SALE&priceUnit=PER_MONTH'},[]),null);
  assert.equal(citationHref({...c,kind:'POI_EVIDENCE'},[]),null);
});

test('missing market analysis displays its own explanation instead of asking for budget',()=>{
 const data=packet();data.evidence.responseKind='INSUFFICIENT_MARKET_ANALYSIS_DATA';data.answer='Chưa có dữ liệu lượt tìm kiếm và giao dịch theo kỳ để xác nhận xu hướng.';
 assert.equal(chatPresentation(data).summary,data.answer);
});
