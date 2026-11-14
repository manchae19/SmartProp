"""Privacy-minimised evidence; full response bytes are hashed then discarded."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re
from urllib.parse import urlsplit
from lxml import html,etree

def sha(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()

def redact(text):
    text=str(text or '')
    text=re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[REDACTED_EMAIL]',text)
    text=re.sub(r'(?<!\d)(?:\+84|0084|0)(?:[ .()-]*\d){8,10}(?!\d)', '[REDACTED_PHONE]',text)
    # Contact names/handles following these labels are not needed by SmartProp.
    text=re.sub(r'(?im)\b(?:liên hệ|hotline|zalo|sđt|điện thoại|contact|phone|inbox)\b[^\n\r]*','[CONTACT_REMOVED]',text)
    return text

def excerpt(text):
    return ' '.join(redact(text).split())[:240]

class EvidenceStore:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def save_discovery(self,source,url,body,cards):
        facts=[{k:redact(row.get(k,'')) for k in ['source_listing_id','detail_url','title','updated_attribute_raw','updated_display_raw','posted_at_raw']} for row in cards]
        value={'source':source,'source_url':url,'fetched_at':now(),'response_sha256':sha(body),'evidence_type':'EXTRACTED_DISCOVERY_METADATA','cards':facts}
        data=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode('utf8')
        file=self.root/(source+'-discovery-'+sha(data)[:20]+'.json');file.write_bytes(data)
        return {'reference':str(file),'sha256':sha(data),'response_sha256':sha(body),'fetched_at':value['fetched_at'],'kind':value['evidence_type']}
    def save_detail(self,source,sid,url,body):
        doc=html.fromstring(body)
        if source=='cafeland':roots=doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," detail-property ")]')
        elif source=='homedy':roots=doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," product-item ")]')
        else:roots=doc.xpath('//article|//main')
        if len(roots)!=1:raise ValueError('Cannot isolate one property evidence container')
        root=deepcopy(roots[0])
        # Preserve source asset text/labels, never unrelated page/seller/tracking UI.
        for node in list(root.xpath('.//script|.//style|.//form|.//iframe|.//button')):node.drop_tree()
        for node in list(root.xpath('.//*[@class]')):
            cls=(node.get('class') or '').lower()
            if any(part in cls for part in ['contact','broker','seller','agent-info','user-info','phone','chat']):node.drop_tree()
        for node in root.iter():
            for key in list(node.attrib):
                safe_location=(key=='href' and '/nha-dat-ban/' in node.attrib[key] and urlsplit(node.attrib[key]).hostname in {None,urlsplit(url).hostname} and not urlsplit(node.attrib[key]).query)
                if key not in {'class','id'} and not safe_location:del node.attrib[key]
            if node.text:node.text=redact(node.text)
            if node.tail:node.tail=redact(node.tail)
        # Keep notices as captured, not an invented licence or ownership claim.
        notices=[]
        for text in doc.xpath('//text()[contains(.,"©") or contains(.,"Bản quyền")]'):
            value=' '.join(str(text).split())
            if 0<len(value)<500:notices.append(value)
        metadata={'source':source,'source_listing_id':sid,'source_url':url,'fetched_at':now(),
            'response_sha256':sha(body),'evidence_type':'PRIVACY_REDACTED_ASSET_DOM','original_response_persisted':False,
            'copyright_notices':list(dict.fromkeys(notices)),'public_republication_allowed':False,'training_allowed':False}
        metadata['source_date_meta']=[{'property':node.get('property'),'content':node.get('content')} for node in doc.xpath('//meta[@property="article:published_time" or @property="article:modified_time"]')]
        offers=[]
        for node in doc.xpath('//script[@type="application/ld+json"]'):
            try:value=json.loads(node.text or '{}',strict=False)
            except (ValueError,TypeError):continue
            if isinstance(value,dict) and value.get('@type')=='Product' and isinstance(value.get('offers'),dict):
                offer=value['offers']
                if offer.get('url')==url:offers.append({k:offer.get(k) for k in ['url','price','priceCurrency','priceValidUntil']})
        metadata['source_product_offer_observations']=offers
        file=self.root/f'{source}_{sid}.html'
        if file.exists():raise FileExistsError('Evidence is immutable; do not overwrite an old source ID')
        data=etree.tostring(root,encoding='utf8',method='html');file.write_bytes(data)
        metadata.update(reference=str(file),sha256=sha(data),bytes=len(data))
        file.with_suffix('.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
        return metadata
    @staticmethod
    def verify(metadata):
        path=Path(metadata['reference'])
        return path.is_file() and sha(path.read_bytes())==metadata['sha256']
