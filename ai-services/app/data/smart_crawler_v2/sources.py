from dataclasses import dataclass
from pathlib import Path
import sys
from urllib.parse import urlsplit,urljoin

DATA=Path(__file__).resolve().parents[1]
if str(DATA) not in sys.path:sys.path.insert(0,str(DATA))
import review_source_details as detail_parser
import audit_all_collected as identities

@dataclass(frozen=True)
class Source:
    name:str
    host:str
    listing:str
    policy:str
    terms_url:str
    reason:str

SOURCES={
 'cafeland':Source('cafeland','nhadat.cafeland.vn','https://nhadat.cafeland.vn/nha-dat-ban-tai-da-nang/',
    'BOUNDED_INTERNAL_RESEARCH','https://nhadat.cafeland.vn/ho-tro/quy-dinh-su-dung-220.html','Private small copies; attribution retained; no republication, images or training'),
 'nhadat24h':Source('nhadat24h','nhadat24h.net','https://nhadat24h.net/nha-dat-da-nang',
    'POLICY_REVIEW_REQUIRED','https://nhadat24h.net/quyche','Observed search=yes, ai-train=no, use=reference and AI-agent restrictions; no automatic override'),
 'homedy':Source('homedy','homedy.com','https://homedy.com/ban-nha-dat-da-nang',
    'POLICY_REVIEW_REQUIRED','https://homedy.com/quy-che-hoat-dong','Observed GPTBot restriction; do not change identity to evade it'),
 'alonhadat':Source('alonhadat','alonhadat.com.vn','https://alonhadat.com.vn/can-ban-nha-dat/da-nang',
    'POLICY_REVIEW_REQUIRED','https://alonhadat.com.vn/','robots allows public sale paths; authoritative reuse terms not confirmed for this pilot'),
 'chotot':Source('chotot','nha.chotot.com','https://nha.chotot.com/mua-ban-bat-dong-san-da-nang',
    'MIGRATED_SOURCE_REVIEW_REQUIRED','https://trogiup.chotot.com/nguoi-ban/dieu-khoan-su-dung-cua-nhatot-com/','Old domain redirects to www.nhatot.com; old public API not automatically reused'),
}

def identity(source,url):
    if source not in SOURCES or urlsplit(url).hostname not in identities.HOSTS[source]:return ''
    sid=identities.sid_url(source,url)
    return sid if sid.isdigit() and not sid.startswith('0') else ''

def discover(source,body,url):
    """Use existing source parsers. V2 never calls their fetch/main functions."""
    if source=='cafeland':
        from crawler_cafeland.crawl_cafeland_danang import parse_list
        rows,more=parse_list(body,url)
        next_page=int(__import__('re').search(r'page-(\d+)',url)[1])+1 if 'page-' in url else 2
        return rows,SOURCES[source].listing+f'page-{next_page}/' if more else None
    if source=='nhadat24h':
        from crawl_nhadat24h_danang import parse
        result=parse(body,url)
        return result if isinstance(result,tuple) else (result,None)
    if source=='homedy':
        from crawl_homedy_danang import listing_records
        return listing_records(body,url),None
    if source=='alonhadat':
        from crawl_alonhadat_danang import listings
        return listings(body,url)
    raise ValueError('No approved current Chotot/Nhatot adapter; do not probe hidden APIs')

def extract(source,card,body,response_url):
    row=dict(card,source=source)
    row['source_listing_id']=str(row['source_listing_id'])
    return detail_parser.parse_detail(row,{'http_status':200,'state':'downloaded','response_url':response_url},body)
