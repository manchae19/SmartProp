import test from 'node:test';
import assert from 'node:assert/strict';
import { publicChatBody } from '../../../server/publicChat.mjs';
import { publicChatResponse,citationHref } from './chat.js';
import { chatPresentation } from './chatPresentation.js';
function packet(){
 const now=Date.now(), url='https://example.org/test-only';
 const citation={sourceId:'document:fixture:0000',url,version:'test-v1',contentHash:'b'.repeat(64),scope:'PUBLIC',kind:'SOURCE_DOCUMENT',title:'TEST ONLY document'};
 const source={sourceId:citation.sourceId,url,version:citation.version,title:citation.title,publisher:'TEST FIXTURE',jurisdiction:'Đà Nẵng',publishedAt:new Date(now-86400000).toISOString(),retrievedAt:new Date(now-3600000).toISOString(),validUntil:new Date(now+86400000).toISOString()};
 return {mode:'SAFE',answer:'TEST ONLY source excerpt.',generationMode:'EVIDENCE_ONLY',retrievalMode:'TOOL_EVIDENCE_ONLY',citations:[citation],recommendedProperties:[],dataLimitations:[],evidence:{responseKind:'KNOWLEDGE_EVIDENCE',documents:[source]}};
}
test('document citation survives relay with original public source',()=>{
 const data=publicChatBody(packet());assert.equal(publicChatResponse(data),data);assert.equal(data.citations[0].url,'https://example.org/test-only');
 assert.equal(chatPresentation(data).summary,data.answer);assert.equal(chatPresentation(data).citations[0].label,'TEST ONLY document');
});
test('stale source and mismatched binding are blocked',()=>{
 for(const alter of [p=>p.evidence.documents[0].validUntil='2000-01-01T00:00:00Z',p=>p.evidence.documents[0].url='https://example.org/other',p=>p.evidence.documents=[],p=>p.evidence.documents[0].publisher='',p=>p.evidence.documents[0].publishedAt='invalid']){
  const p=packet();alter(p);assert.throws(()=>publicChatBody(p));
 }
});
test('private, relative or executable links are not allowed',()=>{
 const c=packet().citations[0];
 for(const url of ['/private/file','http://example.org/test','https://127.0.0.1/','https://host.internal/file','javascript:alert(1)','https://user:secret@example.org/','https://example.org/?token=value']) assert.equal(citationHref({...c,url},[]),null);
});
test('Unicode source path is preserved through relay and second validation',()=>{
 const p=packet();p.citations[0].url='https://example.org/tài-liệu';p.evidence.documents[0].url=p.citations[0].url;
 publicChatResponse(publicChatBody(p));
});

test('historical document snapshots remain readable without accepting stale live answers',()=>{
 const p=packet();p.evidence.documents[0].validUntil='2000-01-01T00:00:00Z';
 assert.throws(()=>publicChatResponse(p));
 assert.equal(chatPresentation(p,{historical:true}).summary,p.answer);
 p.citations[0].url='javascript:alert(1)';
 assert.throws(()=>chatPresentation(p,{historical:true}));
});
