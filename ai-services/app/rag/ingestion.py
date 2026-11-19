"""Local reviewed intake, bounded extraction and atomic full-snapshot replacement.

No implicit crawling. URL reads require --fetch-urls, an explicit host allowlist,
reuse permission and review. Removed sources disappear on the next successful write.
"""
import io
import json
import re
import socket
import ipaddress
import time
from datetime import datetime,timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import httpx
from .config import GroundingError
from .knowledge import document,digest
from .intent import fold
from .document_store import FORMAT,TOPICS,DocumentStore,public_url,timestamp

LIMIT=5*1024*1024
class HtmlText(HTMLParser):
    def __init__(self):super().__init__();self.hidden=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','nav','footer'):self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ('script','style','nav','footer'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

def extract(raw,suffix):
    if len(raw)>LIMIT:raise GroundingError('SOURCE_TOO_LARGE')
    if suffix=='.pdf':
        import subprocess,sys
        try:
            worker=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('document_pdf.py'))],input=raw,capture_output=True,timeout=30,check=True)
            result=json.loads(worker.stdout)
        except (subprocess.SubprocessError,ValueError):raise GroundingError('PDF_EXTRACTION_FAILED_OR_TIMEOUT') from None
        if 'error' in result:raise GroundingError(result['error'])
        text=result['text']
    else:
        text=raw.decode('utf-8-sig')
        if suffix=='.html':
            parser=HtmlText();parser.feed(text);text='\n'.join(parser.parts)
    if len(text)>500000:raise GroundingError('EXTRACTED_TEXT_TOO_LARGE')
    if not text.strip():raise GroundingError('EMPTY_OR_SCANNED_DOCUMENT_REQUIRES_OCR')
    if re.search(r'(?i)(?:ignore (?:all |the )?(?:previous|system) instructions|BEGIN (?:RSA |EC )?PRIVATE KEY|(?:api[_-]?key|password|jwt[_-]?secret)\s*[:=]\s*[^\s]{8,})',text):raise GroundingError('DOCUMENT_REQUIRES_SECURITY_REVIEW')
    return text

def chunks(text):
    words=text.split();start=0
    while start<len(words):
        end=start;length=0
        while end<len(words) and end-start<130 and length+len(words[end])+1<=900:
            length+=len(words[end])+1;end+=1
        if end==start:raise GroundingError('OVERSIZED_DOCUMENT_TOKEN')
        yield ' '.join(words[start:end])
        if end==len(words):break
        start=max(start+1,end-15)

class ReviewedFetcher:
    def __init__(self,allowed_hosts):self.allowed=set(allowed_hosts);self.robots={};self.last={}
    def read(self,url):
        if not public_url(url):raise GroundingError('INVALID_SOURCE_URL')
        host=urlsplit(url).hostname
        if host not in self.allowed:raise GroundingError('SOURCE_HOST_NOT_APPROVED')
        with httpx.Client(timeout=httpx.Timeout(8,connect=3),trust_env=False,follow_redirects=False,headers={'User-Agent':'SmartPropKnowledgeIntake/1.0','Accept-Encoding':'identity'}) as client:
            if host not in self.robots:
                robots_url='https://'+host+'/robots.txt'
                raw,_=self._read(client,robots_url,robots=True)
                parser=RobotFileParser(robots_url);parser.parse(raw.decode('utf-8',errors='replace').splitlines());self.robots[host]=parser
            if not self.robots[host].can_fetch('SmartPropKnowledgeIntake',url):raise GroundingError('ROBOTS_DISALLOWED')
            return self._read(client,url)
    def _read(self,client,url,robots=False):
        target=httpx.URL(url);host=target.host
        addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise GroundingError('PRIVATE_SOURCE_ADDRESS_BLOCKED')
        delay=1-(time.monotonic()-self.last.get(host,0))
        if delay>0:time.sleep(delay)
        self.last[host]=time.monotonic()
        # Connect to the address we validated, without a second DNS lookup.
        # TLS still verifies the original hostname (SNI), and Host remains original.
        pinned=target.copy_with(host=addresses[0][4][0])
        with client.stream('GET',pinned,headers={'Host':host},extensions={'sni_hostname':host}) as response:
            if robots and response.status_code==404:return b'','text/plain'
            if response.status_code!=200:raise GroundingError('SOURCE_HTTP_'+str(response.status_code))
            data=bytearray();maximum=128*1024 if robots else LIMIT
            for part in response.iter_bytes():
                data.extend(part)
                if len(data)>maximum:raise GroundingError('SOURCE_TOO_LARGE')
            return bytes(data),response.headers.get('content-type','').split(';')[0]

def intake(manifest_path,fetch_urls=False):
    manifest_path=Path(manifest_path).resolve()
    if manifest_path.stat().st_size>1024*1024:raise GroundingError('MANIFEST_TOO_LARGE')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    sources=manifest.get('sources')
    if manifest.get('format')!='SMARTPROP_DOCUMENT_INTAKE_V1' or not isinstance(sources,list) or len(sources)>40:raise GroundingError('INVALID_INTAKE_MANIFEST')
    hosts=manifest.get('allowedHosts',[])
    if not isinstance(hosts,list) or len(hosts)>20 or any(not isinstance(h,str) or not public_url('https://'+h+'/') for h in hosts):raise GroundingError('INVALID_SOURCE_HOST_ALLOWLIST')
    fetcher=ReviewedFetcher(hosts)
    documents=[];seen=set();fingerprints=set();report={'total':len(sources),'valid':0,'blocked':0,'duplicate':0,'removed':0,'records':[]}
    now=datetime.now(timezone.utc)
    for source in sources:
        sid=source.get('sourceId') if isinstance(source,dict) else None
        result={'sourceId':sid,'status':'BLOCKED'}
        try:
            if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sid) or sid in seen:raise GroundingError('INVALID_OR_DUPLICATE_SOURCE_ID')
            seen.add(sid)
            if source.get('status')=='REMOVED':result['status']='REMOVED';report['removed']+=1;continue
            if source.get('approval')!='APPROVED' or source.get('permission')!='PERMITTED' or not source.get('permissionBasis'):raise GroundingError('REVIEW_OR_REUSE_PERMISSION_REQUIRED')
            for key in ('title','publisher','version','jurisdiction','permissionBasis'):
                if not isinstance(source.get(key),str) or not 1<=len(source[key])<=300:raise GroundingError('INVALID_SOURCE_METADATA')
            if source.get('topic') not in TOPICS or not public_url(source.get('url')):raise GroundingError('INVALID_SOURCE_METADATA')
            published,retrieved,expires=(timestamp(source.get(k)) for k in ('publishedAt','retrievedAt','validUntil'))
            if not published<=retrieved<=now or expires<=now:raise GroundingError('SOURCE_EXPIRED_OR_INVALID_DATES')
            if fold(source['jurisdiction']) not in ('da nang','viet nam'):raise GroundingError('UNSUPPORTED_JURISDICTION')
            districts=source.get('districts',[])
            if not isinstance(districts,list) or len(districts)>10 or any(not isinstance(d,str) or not 1<=len(d)<=100 for d in districts):raise GroundingError('INVALID_SOURCE_GEOGRAPHY')
            if bool(source.get('claimKey'))!=('claimValue' in source):raise GroundingError('INCOMPLETE_STRUCTURED_CLAIM')
            if source.get('path'):
                path=(manifest_path.parent/source['path']).resolve()
                if not path.is_relative_to(manifest_path.parent) or path.suffix.lower() not in ('.txt','.md','.pdf'):raise GroundingError('SOURCE_PATH_OUTSIDE_INTAKE')
                if path.stat().st_size>LIMIT:raise GroundingError('SOURCE_TOO_LARGE')
                raw=path.read_bytes();suffix=path.suffix.lower()
            else:
                if not fetch_urls:raise GroundingError('URL_FETCH_REQUIRES_EXPLICIT_FLAG')
                raw,kind=fetcher.read(source['url'])
                suffix={ 'application/pdf':'.pdf','text/html':'.html','text/plain':'.txt','text/markdown':'.md'}.get(kind)
                if not suffix:raise GroundingError('UNSUPPORTED_SOURCE_CONTENT_TYPE')
                # The fetch timestamp is observed locally, never copied from a claimed date.
                source={**source,'retrievedAt':datetime.now(timezone.utc).isoformat()}
            fingerprint=digest({'url':source['url'],'version':source['version'],'sha256':sha256(raw).hexdigest()})
            if fingerprint in fingerprints:report['duplicate']+=1;result['status']='DUPLICATE';continue
            text=extract(raw,suffix)
            metadata={k:source[k] for k in ('title','publisher','topic','jurisdiction','publishedAt','retrievedAt','validUntil','approval','permission','permissionBasis')}
            metadata.update(parentSourceId=sid,sourceSha256=sha256(raw).hexdigest(),districts=districts)
            for key in ('claimKey','claimValue'):
                if key in source:
                    if not isinstance(source[key],str) or not 1<=len(source[key])<=300:raise GroundingError('INVALID_STRUCTURED_CLAIM')
                    metadata[key]=source[key]
            parts=list(chunks(text))
            if len(documents)+len(parts)>2000:raise GroundingError('TOO_MANY_CHUNKS')
            documents.extend(document('document:'+sid+':'+str(i).zfill(4),part,source['url'],source['version'],'SOURCE_DOCUMENT',{**metadata,'chunkIndex':i}) for i,part in enumerate(parts))
            fingerprints.add(fingerprint);report['valid']+=1;result.update(status='VALID',chunks=len(parts),sha256=metadata['sourceSha256'])
        except (GroundingError,OSError,ValueError,TypeError,KeyError,httpx.HTTPError) as error:
            report['blocked']+=1;result['reason']=str(error) if isinstance(error,GroundingError) else type(error).__name__
        finally:report['records'].append(result)
    corpus={'format':FORMAT,'builtAt':now.isoformat(),'documents':documents};corpus['contentHash']=digest(corpus)
    report['chunks']=len(documents)
    return corpus,report

def write_corpus(corpus,report,target,allow_empty=False):
    if report['blocked'] or not corpus['documents'] and not allow_empty:raise GroundingError('INTAKE_NOT_READY')
    target=Path(target)
    if target.is_file():
        try:existing=json.loads(target.read_text(encoding='utf-8'))
        except (OSError,ValueError):raise GroundingError('REFUSE_TO_OVERWRITE_UNRELATED_FILE') from None
        if not isinstance(existing,dict) or existing.get('format')!=FORMAT:raise GroundingError('REFUSE_TO_OVERWRITE_UNRELATED_FILE')
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.tmp')
    try:
        temporary.write_text(json.dumps(corpus,ensure_ascii=False,indent=2),encoding='utf-8')
        DocumentStore(temporary).load()
        temporary.replace(target)
    finally:
        if temporary.exists():temporary.unlink()
