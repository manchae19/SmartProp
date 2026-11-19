"""Reviewed local document corpus. No network, SQL or private uploads in chat."""
import ipaddress
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from .config import GroundingError, RagUnavailable
from .knowledge import digest

FORMAT='SMARTPROP_DOCUMENT_CORPUS_V1'
TOPICS={'LEGAL','PLANNING','INFRASTRUCTURE','MARKET','GENERAL'}
def timestamp(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None:raise ValueError()
        return dt
    except (AttributeError,ValueError,TypeError):raise GroundingError('INVALID_DOCUMENT_TIMESTAMP') from None

def public_url(value):
    try:
        u=urlsplit(value);host=(u.hostname or '').lower()
        if u.scheme!='https' or not host or u.username or u.password or u.port not in (None,443) or u.query or u.fragment or len(value)>2000:return False
        if host in ('localhost','localhost.localdomain') or host.endswith(('.local','.internal','.localhost')):return False
        try:ipaddress.ip_address(host);return False
        except ValueError:pass
        return '.' in host and all(part and part.replace('-','').isalnum() for part in host.split('.'))
    except (ValueError,TypeError):return False

class DocumentStore:
    def __init__(self,path):self.path=Path(path) if path else None
    def load(self):
        if self.path is None or not self.path.is_file():raise RagUnavailable('DOCUMENT_CORPUS_UNAVAILABLE')
        try:
            if self.path.stat().st_size>8*1024*1024:raise GroundingError('DOCUMENT_CORPUS_TOO_LARGE')
            corpus=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):raise RagUnavailable('DOCUMENT_CORPUS_UNAVAILABLE') from None
        if corpus.get('format')!=FORMAT or corpus.get('contentHash')!=digest({k:v for k,v in corpus.items() if k!='contentHash'}):raise GroundingError('DOCUMENT_CORPUS_HASH_MISMATCH')
        docs=corpus.get('documents')
        if not isinstance(docs,list) or len(docs)>2000:raise GroundingError('INVALID_DOCUMENT_COUNT')
        seen=set();now=datetime.now(timezone.utc)
        for d in docs:
            m=d.get('metadata',{})
            if d.get('scope')!='PUBLIC' or d.get('kind')!='SOURCE_DOCUMENT' or d.get('sourceId') in seen or not public_url(d.get('url')):raise GroundingError('INVALID_DOCUMENT_PERMISSION')
            if d.get('contentHash')!=digest({k:v for k,v in d.items() if k not in ('contentHash','version')}):raise GroundingError('DOCUMENT_HASH_MISMATCH')
            if m.get('topic') not in TOPICS or m.get('approval')!='APPROVED' or m.get('permission')!='PERMITTED' or not m.get('permissionBasis') or not m.get('publisher') or not m.get('title'):raise GroundingError('INVALID_DOCUMENT_REVIEW')
            published,retrieved,expires=(timestamp(m.get(k)) for k in ('publishedAt','retrievedAt','validUntil'))
            if published>retrieved or retrieved>now or expires<=retrieved:raise GroundingError('INVALID_DOCUMENT_DATES')
            if not isinstance(d.get('text'),str) or not 1<=len(d['text'])<=1200:raise GroundingError('INVALID_DOCUMENT_CHUNK')
            seen.add(d['sourceId'])
        return corpus
    def select(self,topic,district=None):
        corpus=self.load();now=datetime.now(timezone.utc)
        relevant=[d for d in corpus['documents'] if (topic=='GENERAL' or d['metadata']['topic']==topic) and (not district or not d['metadata'].get('districts') or district in d['metadata']['districts'])]
        active=[d for d in relevant if timestamp(d['metadata']['validUntil'])>now]
        return active,len(relevant)-len(active)

def conflicts(documents):
    claims={}
    for d in documents:
        m=d['metadata'];key=m.get('claimKey');value=m.get('claimValue')
        if key and value is not None:claims.setdefault(key,set()).add(str(value))
    return sorted(k for k,v in claims.items() if len(v)>1)
