"""Durable account checkpoints. Spring validates live auth and owns the database.

Never send credentials, account profile, or internal context to the browser.
Each request gets an isolated SessionStore, so failures/concurrent requests cannot
mutate the committed checkpoint. DB revision CAS makes a complete turn atomic.
"""
from copy import copy, deepcopy
from dataclasses import asdict, fields
import re
import secrets
import json
from decimal import Decimal
import httpx
from .session import Context, SessionStore
from .tools import UpstreamError


class CheckpointSessions(SessionStore):
    def __init__(self, conversation_id, saved):
        super().__init__()
        self.conversation_id = conversation_id
        self.saved = deepcopy(saved)
        self.context = None

    def begin(self, session_id, *, scope):
        # Only server-owned state from the authenticated checkpoint endpoint enters here.
        saved, self.saved = self.saved, None
        if saved:
            allowed = {f.name for f in fields(Context)} - {"scope", "session_id"}
            self.context = Context(scope=scope, session_id=self.conversation_id,
                                   **{k:v for k,v in saved.items() if k in allowed})
            self.context.turns += 1
            return self.context, self.conversation_id, True
        context, _, _ = super().begin(None, scope=scope)
        context.session_id = self.conversation_id
        self.context = context
        return context, self.conversation_id, False


def checkpoint_call(backend, method, path, token, payload=None):
    key = backend.settings.checkpoint_key
    if len(key) < 32:
        raise UpstreamError(503)
    try:
        response = backend.client.request(method, "/api/v1/users/me/advisor-chats/" + path,
            headers={"Authorization":token, "X-Chat-Checkpoint-Key":key}, json=payload)
        if response.status_code != 200:
            raise UpstreamError(response.status_code)
        return response.json()
    except httpx.HTTPError:
        raise UpstreamError() from None


def _unsupported(value):
    raise TypeError("Unsupported checkpoint value")


def durable_chat(orchestrator, payload, token, account):
    conversation_id = payload.sessionId or secrets.token_hex(16)
    if not re.fullmatch(r"[a-f0-9]{32}", conversation_id):
        raise UpstreamError(404)
    saved = checkpoint_call(orchestrator.backend, "GET", conversation_id+"/checkpoint", token) if payload.sessionId else None
    local = copy(orchestrator)
    local.sessions = CheckpointSessions(conversation_id, saved["checkpoint"] if saved else None)
    result = local.chat(payload, token=token, account=account)
    # Backend tools may use Decimal for coordinates or exact money; JSON must retain precision.
    context = json.loads(json.dumps(asdict(local.sessions.context), default=lambda value: str(value) if isinstance(value, Decimal) else _unsupported(value)))
    context.pop("scope",None)
    context.pop("session_id",None)
    checkpoint_call(orchestrator.backend,"PUT",conversation_id+"/checkpoint",token,{
        "revision":saved["revision"] if saved else 0,
        "question":payload.question, "response":result.model_dump(mode="json"), "checkpoint":context})
    return result
