import test from 'node:test';
import assert from 'node:assert/strict';
import {createChatSession,publicChatResponse} from './chat.js';
import {createChatHistory} from './chatHistory.js';
const id='a'.repeat(32), other='b'.repeat(32);
const packet=()=>({mode:'SAFE',answer:'Saved answer',generationMode:'EVIDENCE_ONLY',retrievalMode:'TOOL_EVIDENCE_ONLY',citations:[],recommendedProperties:[],dataLimitations:[],evidence:{session:{id}}});
const saved=()=>({id,turns:[{number:1,question:'Saved question',response:packet()}],trimmed:false});
test('load history and continue with the server-issued conversation id',async()=>{
 let sent;const chat=createChatSession(async req=>{sent=req;return packet();});
 const history=createChatHistory(chat,async()=>saved(),()=> '1');
 assert.equal(await history.select(id),true);
 assert.equal(chat.getSnapshot().state.messages.length,2);
 assert.equal(await chat.getSnapshot().submit('Continue'),true);
 assert.equal(sent.sessionId,id);
 chat.getSnapshot().clear();assert.equal(chat.getSnapshot().state.sessionId,null);
});
test('late list response cannot expose previous account history',async()=>{
 let resolve,owner='1';const chat=createChatSession(async()=>packet());
 const history=createChatHistory(chat,()=>new Promise(r=>resolve=r),()=>owner);
 const loading=history.refresh();owner='2';history.reset();resolve([{id,title:'Private'}]);await loading;
 assert.deepEqual(history.getSnapshot().items,[]);
});
test('late selection cannot hydrate the next account',async()=>{
 let resolve,owner='1';const chat=createChatSession(async()=>packet());
 const history=createChatHistory(chat,()=>new Promise(r=>resolve=r),()=>owner);
 const loading=history.select(id);owner='2';history.reset();chat.getSnapshot().reset();resolve(saved());
 assert.equal(await loading,false);assert.equal(chat.getSnapshot().state.messages.length,0);
});
test('loading locks sends and failed selection leaves no active conversation',async()=>{
 let reject;const chat=createChatSession(async()=>packet());
 const history=createChatHistory(chat,()=>new Promise((_,r)=>reject=r),()=> '1');
 const loading=history.select(id);assert.equal(await chat.getSnapshot().submit('race'),false);
 reject(Error('403'));assert.equal(await loading,false);
 assert.equal(chat.getSnapshot().state.busy,false);assert.equal(chat.getSnapshot().state.sessionId,null);assert.ok(history.getSnapshot().error);
});
test('list preserves server activity order, caps entries and supports retry',async()=>{
 let fail=true;const chat=createChatSession(async()=>packet());
 const history=createChatHistory(chat,async()=>{if(fail)throw Error();return [{id:other,title:'Newer'},{id,title:'Older'}];},()=> '1');
 await history.refresh();assert.ok(history.getSnapshot().error);fail=false;await history.refresh(true);
 assert.deepEqual(history.getSnapshot().items.map(x=>x.id),[other,id]);assert.equal(history.getSnapshot().error,null);
});
test('malformed or unsafe saved response is rejected before displaying messages',async()=>{
 const chat=createChatSession(async()=>packet());const data=saved();data.turns[0].response.mode='INTERNAL_RESEARCH';
 const history=createChatHistory(chat,async()=>data,()=> '1');assert.equal(await history.select(id),false);assert.equal(chat.getSnapshot().state.messages.length,0);
});
test('two restores with equal message counts still represent different conversations',()=>{
 const chat=createChatSession(async()=>packet());chat.getSnapshot().restore(saved());
 chat.getSnapshot().restore({...saved(),id:other});assert.equal(chat.getSnapshot().state.sessionId,other);
});

test('successful send refreshes activity even when an older list request is pending',async()=>{
 const chat=createChatSession(async()=>packet());let finish,calls=0;
 const history=createChatHistory(chat,async()=>{calls++;if(calls===1)return new Promise(r=>finish=r);return [{id,title:'Just active'}];},()=> '1');
 const original=history.refresh();const afterSend=history.refresh(true);finish([]);await original;await afterSend;
 assert.equal(calls,2);assert.equal(history.getSnapshot().items[0].id,id);
});

test('delete active history resets chat and refreshes recent list',async()=>{
 const chat=createChatSession(async()=>packet());chat.getSnapshot().restore(saved());let deleted=false;
 const history=createChatHistory(chat,async(path,options)=>{if(options?.method==='DELETE'){deleted=true;return {deleted:true};}return [];},()=> '1');
 assert.equal(await history.remove(id),true);assert.equal(deleted,true);assert.equal(chat.getSnapshot().state.sessionId,null);assert.deepEqual(history.getSnapshot().items,[]);
});
