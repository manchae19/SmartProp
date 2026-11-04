"""Single-source rate limits, bounded retries, robots/policy/redirect guards."""
import json,time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from .evidence import now,sha

UA='SmartPropResearch/2.0 (bounded academic metadata pilot; no training)'
class SourceUnavailable(RuntimeError):pass

class Client:
    def __init__(self,source,evidence_dir,delay=3,timeout=20,retries=1):
        self.source=source;self.delay=max(3,delay);self.timeout=min(30,max(1,timeout));self.retries=min(2,max(0,retries))
        self.last=0.;self.requests=0;self.closed=False;self.robot=None
        self.session=requests.Session();self.session.headers.update({'User-Agent':UA})
        self.out=Path(evidence_dir);self.out.mkdir(parents=True,exist_ok=True)
    def prepare(self):
        if self.source.policy!='BOUNDED_INTERNAL_RESEARCH':raise SourceUnavailable(self.source.policy)
        url='https://'+self.source.host+'/robots.txt'
        body=self._request(url,robots=True)
        text=body.decode('utf8',errors='replace')
        if 'user-agent:' not in text.lower() or '<html' in text.lower():raise SourceUnavailable('ROBOTS_UNREADABLE_OR_CHALLENGE')
        self.robot=RobotFileParser(url);self.robot.parse(text.splitlines())
        self.delay=max(self.delay,self.robot.crawl_delay(UA) or self.robot.crawl_delay('*') or 0)
        if self.delay>60:raise SourceUnavailable('ROBOTS_DELAY_EXCEEDS_SMALL_PILOT_POLICY')
        (self.out/(self.source.name+'-robots.txt')).write_bytes(body)
        return {'url':url,'sha256':sha(body),'observed_at':now(),'terms_url':self.source.terms_url,'policy':self.source.policy}
    def get(self,url):
        if self.closed:raise SourceUnavailable('SOURCE_STOPPED_AFTER_RESTRICTION')
        if self.robot is None:raise SourceUnavailable('ROBOTS_NOT_CHECKED')
        if not self.robot.can_fetch(UA,url):raise SourceUnavailable('ROBOTS_DISALLOWED')
        return self._request(url)
    def _request(self,url,robots=False):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname!=self.source.host or parsed.username or parsed.password or parsed.port not in {None,443}:raise SourceUnavailable('URL_HOST_NOT_ALLOWED')
        for attempt in range(self.retries+1):
            time.sleep(max(0,self.delay-(time.monotonic()-self.last)));self.last=time.monotonic();self.requests+=1
            try:
                with self.session.get(url,timeout=self.timeout,allow_redirects=False,stream=True) as response:
                    if response.status_code in {401,403,429}:self.closed=True;raise SourceUnavailable('ACCESS_RESTRICTED_HTTP_'+str(response.status_code))
                    if 300<=response.status_code<400:raise SourceUnavailable('REDIRECT_REQUIRES_REVIEW')
                    if response.status_code>=500:
                        if attempt<self.retries:time.sleep(2**attempt*2);continue
                        raise SourceUnavailable('HTTP_'+str(response.status_code))
                    if response.status_code!=200:raise SourceUnavailable('HTTP_'+str(response.status_code))
                    chunks=[];size=0
                    for chunk in response.iter_content(65536):
                        size+=len(chunk)
                        if size>3_000_000:raise SourceUnavailable('RESPONSE_TOO_LARGE')
                        chunks.append(chunk)
                    body=b''.join(chunks)
                    if not robots and 'html' not in response.headers.get('Content-Type','').lower():raise SourceUnavailable('UNEXPECTED_CONTENT_TYPE')
                    low=body[:12000].lower()
                    if not robots and any(s in low for s in [b'cf-chl-',b'captcha-delivery.com',b'just a moment...',b'checking your browser']):
                        self.closed=True;raise SourceUnavailable('CHALLENGE_PAGE_STOP')
                    return body
            except (requests.Timeout,requests.ConnectionError):
                if attempt<self.retries:time.sleep(2**attempt*2);continue
                raise SourceUnavailable('NETWORK_UNAVAILABLE')
        raise SourceUnavailable('RETRY_LIMIT')
