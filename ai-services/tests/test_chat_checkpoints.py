import json
import unittest
from dataclasses import asdict
from types import SimpleNamespace
import httpx
from app.rag.checkpoints import durable_chat, CheckpointSessions
from app.rag.config import Settings
from app.rag.schemas import ChatRequest, ChatResponse
from app.rag.session import SessionStore
from app.rag.tools import BackendTools, UpstreamError


class Bot:
    def __init__(self,backend):self.backend=backend;self.sessions=SessionStore()
    def chat(self,payload,*,token,account):
        ctx,sid,resumed=self.sessions.begin(payload.sessionId,scope='ACCOUNT:'+account['subject'])
        prior=ctx.budget_vnd
        self.sessions.record(ctx,criteria={'budgetVnd':prior or '2000000000'},property_ids=[],area_ids=[],evidence_ids=[],question=payload.question)
        return ChatResponse(answer=prior or 'first',mode='SAFE',generationMode='EVIDENCE_ONLY',retrievalMode='TOOL_EVIDENCE_ONLY',citations=[],recommendedProperties=[],evidence={'session':{'id':sid}},dataLimitations=[])


class CheckpointsTest(unittest.TestCase):
    def setUp(self):
        self.rows={}; self.puts=0; self.fail=False
        def handler(req):
            actor=req.headers['authorization'];sid=req.url.path.split('/')[-2];key=(actor,sid)
            if req.headers.get('x-chat-checkpoint-key')!='k'*32:return httpx.Response(403)
            if req.method=='GET':return httpx.Response(200,json=self.rows[key]) if key in self.rows else httpx.Response(404)
            self.puts+=1
            if self.fail:return httpx.Response(503)
            body=json.loads(req.content);existing=self.rows.get(key,{'revision':0})
            if body['revision']!=existing['revision']:return httpx.Response(409)
            self.rows[key]={'revision':body['revision']+1,'checkpoint':body['checkpoint'],'response':body['response']}
            return httpx.Response(200,json={'id':sid})
        self.backend=BackendTools(Settings(checkpoint_key='k'*32));self.backend.client.close()
        self.backend.client=httpx.Client(base_url='http://127.0.0.1:8080',transport=httpx.MockTransport(handler))
        self.bot=Bot(self.backend)
    def tearDown(self):self.backend.close()
    def call(self,sid=None,actor='1'):
        return durable_chat(self.bot,ChatRequest(question='continue',sessionId=sid),'Bearer '+actor,{'subject':actor})
    def test_restart_preserves_context_and_identifier(self):
        result=self.call();sid=result.evidence['session']['id'];self.bot=Bot(self.backend)
        result=self.call(sid);self.assertEqual(result.answer,'2000000000');self.assertEqual(result.evidence['session']['id'],sid)
        self.assertEqual(self.rows[('Bearer 1',sid)]['revision'],2)
    def test_other_account_cannot_continue_known_id(self):
        sid=self.call().evidence['session']['id']
        with self.assertRaises(UpstreamError) as error:self.call(sid,'2')
        self.assertEqual(error.exception.status,404);self.assertEqual(self.puts,1)
    def test_failed_commit_does_not_change_saved_context(self):
        sid=self.call().evidence['session']['id'];before=__import__("copy").deepcopy(self.rows);self.fail=True
        with self.assertRaises(UpstreamError):self.call(sid)
        self.assertEqual(self.rows,before);self.assertEqual(self.bot.sessions.size(),0)
    def test_long_lived_account_checkpoint_ignores_memory_ttl_and_turn_cap(self):
        sid=self.call().evidence['session']['id'];row=self.rows[('Bearer 1',sid)];row['checkpoint']['turns']=200;row['checkpoint']['updated_at']=0
        result=self.call(sid);self.assertEqual(result.answer,'2000000000');self.assertEqual(row['revision'],1)
        self.assertEqual(self.rows[('Bearer 1',sid)]['checkpoint']['turns'],201)
    def test_checkpoint_scope_is_derived_from_auth(self):
        sessions=CheckpointSessions('a'*32,{'scope':'INTERNAL_RESEARCH','session_id':'b'*32,'created_at':0,'updated_at':0,'turns':1})
        ctx,sid,_=sessions.begin('a'*32,scope='ACCOUNT:2');self.assertEqual(ctx.scope,'ACCOUNT:2');self.assertEqual(sid,'a'*32)
    def test_missing_service_key_fails_closed_before_chat(self):
        self.backend.settings=Settings()
        with self.assertRaises(UpstreamError) as error:self.call()
        self.assertEqual(error.exception.status,503);self.assertEqual(self.puts,0)
    def test_real_orchestrator_resumes_budget_priorities_and_reference_after_restart(self):
        from tests.test_chat_budget_context import ConversationTests
        fixture=ConversationTests();fixture.setUp()
        fixture.backend.client=self.backend.client
        fixture.backend.settings=self.backend.settings
        self.bot=fixture.bot
        account={'subject':'1','enabled':False}
        def ask(question,sid=None):
            return durable_chat(self.bot,ChatRequest(question=question,sessionId=sid),'Bearer 1',account)
        result=ask('Tìm căn hộ toàn Đà Nẵng 10 tỷ, ưu tiên trường học')
        sid=result.evidence['session']['id'];original=[p['id'] for p in result.recommendedProperties]
        self.assertTrue(original)
        self.bot.sessions=SessionStore() # Simulate a worker restart; there is no warm context.
        fixture.backend.rows=list(reversed(fixture.backend.rows))
        result=ask('Căn thứ hai có phù hợp không?',sid)
        self.assertEqual(result.evidence['session']['id'],sid)
        self.assertEqual(result.recommendedProperties[0]['id'],original[1])
        self.assertEqual(self.rows[('Bearer 1',sid)]['revision'],2)
        self.assertEqual(self.rows[('Bearer 1',sid)]['checkpoint']['budget_vnd'],'10000000000')

    def test_personalized_api_preserves_not_found_status(self):
        from app.rag.api import create_chat_app
        from fastapi.testclient import TestClient
        self.backend.account_context=lambda token: {'subject':'2','enabled':False}
        with TestClient(create_chat_app(settings=self.backend.settings,orchestrator=self.bot)) as client:
            response=client.post('/chat/personalized',headers={'Authorization':'Bearer 2'},json={'question':'continue','sessionId':'a'*32})
            self.assertEqual(response.status_code,404)
            self.assertEqual(client.post('/chat/personalized',json={'question':'hello'}).status_code,401)

    def test_revision_conflict_is_not_converted_to_success(self):
        from unittest.mock import patch
        sid=self.call().evidence['session']['id']
        original=self.backend.client.request
        def stale(method,*args,**kwargs):
            if method=='PUT':return httpx.Response(409)
            return original(method,*args,**kwargs)
        with patch.object(self.backend.client,'request',side_effect=stale):
            with self.assertRaises(UpstreamError) as error:self.call(sid)
        self.assertEqual(error.exception.status,409)

if __name__=='__main__':unittest.main()
