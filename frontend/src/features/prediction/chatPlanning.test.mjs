import test from 'node:test';
import assert from 'node:assert/strict';
import {publicChatBody} from '../../../server/publicChat.mjs';
import {publicChatResponse,citationHref} from './chat.js';
import {chatPresentation} from './chatPresentation.js';
function packet(){
 const c={sourceId:'planning:'+'a'.repeat(24),url:'https://hoaxuan.danang.gov.vn/test-fixture',title:'TEST ONLY notice',version:'a'.repeat(16),contentHash:'a'.repeat(64),scope:'PUBLIC',kind:'PLANNING_SOURCE'};
 const source={sourceId:c.sourceId,url:c.url,title:c.title,checkedAt:new Date(Date.now()-86400000).toISOString(),documentDate:'2025-01-01',publicationDate:null,verification:'SOURCE_CHECKED',legalStatus:'Fixture consultation; not approval'};
 return {mode:'SAFE',answer:'TEST ONLY planning answer',generationMode:'EVIDENCE_ONLY',retrievalMode:'TOOL_EVIDENCE_ONLY',recommendedProperties:[],citations:[c],dataLimitations:[],evidence:{responseKind:'PLANNING_LOOKUP',planningLookup:{version:'V1',status:'OK',operation:'PLANNING_STATUS',sources:[source],items:[{id:'HX-LAND-001',name:'Fixture',legalStatus:source.legalStatus,sourceIds:[c.sourceId]}],total:1,truncated:false}}};
}
test('planning source survives /api/chat relay and presentation',()=>{
 const p=publicChatBody(packet());assert.equal(publicChatResponse(p),p);
 const v=chatPresentation(p);assert.equal(v.summary,p.answer);assert.equal(v.citations[0].planningSource.documentDate,'2025-01-01');assert.equal(v.citations[0].href,p.citations[0].url);
});
test('unapproved metadata and mismatched provenance rejected',()=>{
 for(const alter of [p=>p.evidence.planningLookup.sources[0].verification='UNREVIEWED',p=>p.evidence.planningLookup.sources[0].url+='-other',p=>p.evidence.planningLookup.sources[0].checkedAt='2099-01-01',p=>p.evidence.planningLookup.items[0].sourceIds=['missing'],p=>delete p.evidence.planningLookup,p=>p.evidence.planningLookup.sources[0].documentDate='bad']){const p=packet();alter(p);assert.throws(()=>publicChatBody(p));}
});
test('planning source URL allowlist rejects unsafe links',()=>{
 const c=packet().citations[0];for(const url of ['https://example.org/test','http://hoaxuan.danang.gov.vn/test','https://hoaxuan.danang.gov.vn.evil.org/test','https://hoaxuan.danang.gov.vn/test?token=secret','javascript:alert(1)'])assert.equal(citationHref({...c,url},[]),null);
});
test('empty planning answers and historical checkpoint remain readable',()=>{
 const p=packet();p.citations=[];Object.assign(p.evidence.planningLookup,{status:'SOURCE_UNAVAILABLE',sources:[],items:[],total:0});assert.equal(chatPresentation(p).summary,p.answer);
 assert.equal(chatPresentation(packet(),{historical:true}).summary,'TEST ONLY planning answer');
});
