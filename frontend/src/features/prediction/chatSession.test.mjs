import test from 'node:test';
import assert from 'node:assert/strict';
import {createChatSession} from './chat.js';
const response = text => ({answer:text,evidence:{session:{id:'b'.repeat(32)}}});
test('identity reset drops old response and does not unlock a new pending request',async()=>{
 const pending=[];const chat=createChatSession(request=>new Promise((resolve,reject)=>pending.push({request,resolve,reject})));
 const old=chat.getSnapshot().submit('old identity question');
 chat.getSnapshot().reset();
 assert.equal(chat.getSnapshot().state.messages.length,0);
 assert.equal(chat.getSnapshot().state.sessionId,null);
 const fresh=chat.getSnapshot().submit('new identity question');
 pending[0].resolve(response('old answer'));
 assert.equal(await old,false);assert.equal(chat.getSnapshot().state.busy,true);
 pending[1].resolve(response('new answer'));assert.equal(await fresh,true);
 assert.equal(chat.getSnapshot().state.messages.length,2);assert.equal(chat.getSnapshot().state.messages[1].response.answer,'new answer');
 assert.equal(pending[1].request.sessionId,undefined);
});
test('identity reset ignores errors from the retired conversation',async()=>{
 let reject;const chat=createChatSession(()=>new Promise((_,fail)=>reject=fail));const request=chat.getSnapshot().submit('question');chat.getSnapshot().reset();reject(new Error('old error'));await request;
 assert.equal(chat.getSnapshot().state.error,null);assert.equal(chat.getSnapshot().state.messages.length,0);
});
test('ordinary clear starts a fresh conversation',async()=>{
 const chat=createChatSession(async()=>response('answer'));await chat.getSnapshot().submit('question');chat.getSnapshot().clear();
 assert.equal(chat.getSnapshot().state.messages.length,0);assert.equal(chat.getSnapshot().state.sessionId,null);
});
