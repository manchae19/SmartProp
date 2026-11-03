"""Immediate quality admission, append-safe checkpoint, bounded live collection."""
import csv,json,os,hashlib
from datetime import datetime
from collections import Counter,defaultdict
from pathlib import Path
from .sources import SOURCES,discover,extract,identity
from .transport import Client,SourceUnavailable
from .evidence import EvidenceStore,now,excerpt,sha
from .quality import evaluate
from .index import OldIndex,fingerprints,canonical_url

DATASET_FIELDS=['source','source_listing_id','record_key','source_url','crawled_at','published_at','updated_at','date_basis',
 'source_evidence_reference','title','description','transaction_type','property_type','category','price_vnd','price_million','area_sqm',
 'land_area_sqm','floor_area_sqm','city','district','ward','address','latitude','longitude','images','quality_status','quality_score','quality_flags',
 'verification_status','duplicate_status','holdout_status','evidence_status','source_fields','normalization_basis','training_allowed','public_display_allowed']
def dump_csv(path,rows,fields):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    os.replace(tmp,path)

class Pipeline:
    def __init__(self,out,index,max_new=40,max_pages=2,delay=3,client_factory=Client):
        if not 1<=max_new<=100 or not 1<=max_pages<=3:raise ValueError('Pilot is limited to1–100 new listings and1–3 pages/source')
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True);self.index=index
        self.max_new=max_new;self.max_pages=max_pages;self.delay=delay;self.factory=client_factory
        self.state_file=self.out/'checkpoint.json'
        self.state=json.loads(self.state_file.read_text(encoding='utf8')) if self.state_file.exists() else {'version':2,'seen':{},'records':{},'evidence':[],'duplicates':[],'policies':[]}
        if self.state.get('version')!=2:raise ValueError('Unknown checkpoint')
        self.max_new=min(self.max_new,max(0,100-len(self.state['seen'])))
        self.store=EvidenceStore(self.out/'evidence');self.new_count=0;self.requests=0
        for key,entry in list(self.state['seen'].items()):
            if entry.get('status')=='DETAIL_RESERVED' and key not in self.state['records']:
                source,sid=key.split(':',1)
                meta_file=self.store.root/f'{source}_{sid}.json'
                if meta_file.exists():
                    metadata=json.loads(meta_file.read_text(encoding='utf8'))
                    if not self.store.verify(metadata):raise ValueError('Interrupted evidence hash mismatch')
                    self.state['records'][key]=dict(source=source,source_listing_id=sid,record_key=key,source_url=entry.get('source_url',''),crawled_at=metadata['fetched_at'],
                        quality_status='NEEDS_REVIEW',quality_score=0,quality_flags=['LOCAL_PIPELINE_INTERRUPTED_AFTER_EVIDENCE_CAPTURE'],verification_status='UNVERIFIED',
                        evidence_status='REDACTED_ASSET_SNAPSHOT_HASH_VERIFIED',source_evidence_reference=metadata['reference']+'#sha256='+metadata['sha256'],
                        duplicate_status='ID_WAS_NEW_FINGERPRINT_NOT_COMPLETED',holdout_status='NOT_ADMITTED_INCOMPLETE_CHECKS',training_allowed=False,public_display_allowed=False)
                    self.state['evidence'].append(metadata);self.state['seen'][key]={'status':'NEEDS_REVIEW','reason':'LOCAL_PIPELINE_INTERRUPTED_AFTER_EVIDENCE_CAPTURE'};self.save()
                else:self.unavailable(source,{'source_listing_id':sid,'detail_url':entry.get('source_url','')},'INTERRUPTED_DETAIL_NOT_AUTOMATICALLY_RETRIED')
    def save(self):
        temp=self.state_file.with_suffix('.json.tmp');temp.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding='utf8');os.replace(temp,self.state_file)
    def unavailable(self,source,card,reason):
        sid=str(card['source_listing_id']);key=source+':'+sid
        record=dict(source=source,source_listing_id=sid,record_key=key,source_url=card['detail_url'],crawled_at=now(),
            title=excerpt(card.get('title','')),quality_status='SOURCE_UNAVAILABLE',quality_flags=[reason],quality_score=0,
            verification_status='UNVERIFIED',evidence_status='UNAVAILABLE',duplicate_status='NEW_ID_ONLY',holdout_status='NO_DETAIL_FINGERPRINT',training_allowed=False,public_display_allowed=False)
        self.state['records'][key]=record;self.state['seen'][key]={'status':'SOURCE_UNAVAILABLE','reason':reason};self.save()
    def run_source(self,name):
        source=SOURCES[name]
        if source.policy!='BOUNDED_INTERNAL_RESEARCH':
            self.state['policies'].append(dict(source=name,status='SKIPPED',reason=source.reason,policy=source.policy,terms_url=source.terms_url));return
        # A failed/blocked source is not retried automatically on the next run.
        previous=[p for p in self.state['policies'] if p['source']==name and p.get('status')=='SOURCE_UNAVAILABLE']
        if previous:
            self.state['policies'].append(dict(source=name,status='CACHED_SOURCE_UNAVAILABLE',reason=previous[-1]['reason']));return
        client=self.factory(source,self.out/'policy',delay=self.delay)
        try:
            policy=client.prepare();self.state['policies'].append(dict(source=name,status='POLICY_ALLOWED_SMALL_INTERNAL_PILOT',**policy))
            url=source.listing
            for page in range(self.max_pages):
                if not url or self.new_count>=self.max_new:break
                body=client.get(url)
                try:cards,next_url=discover(name,body,url)
                except (ValueError,KeyError,IndexError) as exc:raise SourceUnavailable('LISTING_STRUCTURE_CHANGED_'+type(exc).__name__) from exc
                discovery=self.store.save_discovery(name,url,body,cards)
                self.state['evidence'].append(dict(source=name,source_listing_id='',source_url=url,**discovery))
                # Valid explicit newest dates first; unknown date remains unknown.
                def date_order(row):
                    raw=str(row.get('updated_attribute_raw') or row.get('posted_at_raw') or '')
                    for fmt in ['%d-%m-%Y %H:%M:%S','%d/%m/%Y','%d-%m-%Y']:
                        try:return datetime.strptime(raw,fmt).isoformat()
                        except ValueError:pass
                    return ''
                cards.sort(key=date_order,reverse=True)
                for card in cards:
                    if self.new_count>=self.max_new:break
                    sid=str(card.get('source_listing_id',''));detail=card.get('detail_url') or card.get('source_url','')
                    if not sid or identity(name,detail)!=sid:
                        self.state['duplicates'].append(dict(source=name,source_listing_id=sid,source_url=detail,reason='NOVELTY_OR_IDENTITY_UNDETERMINED',detail_requested=False));continue
                    card=dict(card,detail_url=detail);key=name+':'+sid
                    known=self.index.match_identity(name,sid,detail)
                    if known or key in self.state['seen']:
                        self.state['duplicates'].append(dict(source=name,source_listing_id=sid,source_url=detail,reason=known or 'CHECKPOINT_ALREADY_SEEN',detail_requested=False));continue
                    self.new_count+=1
                    # Reserve before network: an interrupted/failed detail is not
                    # silently fetched again or treated as a fresh listing.
                    self.state['seen'][key]={'status':'DETAIL_RESERVED','source_url':detail};self.save()
                    try:
                        payload=client.get(detail);observed=now()
                        stored=self.store.save_detail(name,sid,detail,payload)
                        if not self.store.verify(stored):raise ValueError('Persisted evidence hash mismatch')
                        evidence=extract(name,card,payload,detail)
                        record=evaluate(name,card,evidence,payload,observed)
                        stored.update(source_url=detail,discovery_reference=discovery['reference'],source_price_raw=evidence.get('price_raw',''),source_area_raw=evidence.get('area_raw',''),source_category=evidence.get('source_category',''))
                        self.state['evidence'].append(dict(stored,source=name,source_listing_id=sid))
                        record.update(source_evidence_reference=stored['reference']+'#sha256='+stored['sha256'],evidence_status='REDACTED_ASSET_SNAPSHOT_HASH_VERIFIED')
                        matches,held=self.index.match_fingerprints(record)
                        record['duplicate_status']='POSSIBLE_OLD_OR_BATCH_PROPERTY' if matches else 'NO_FINGERPRINT_MATCH_NOT_PHYSICAL_PROOF'
                        record['holdout_status']='HOLDOUT_RISK_QUARANTINED' if held else 'NO_KNOWN_ID_OR_FINGERPRINT_HOLDOUT_LINK'
                        if held:
                            record['quality_status']='REJECTED';record['quality_flags'].append('PROTECTED_HOLDOUT_FINGERPRINT_RISK')
                        elif matches:
                            if record['quality_status']=='READY_FOR_INTERNAL_REVIEW':record['quality_status']='NEEDS_REVIEW'
                            record['quality_flags'].append('POSSIBLE_DUPLICATE_REQUIRES_REVIEW')
                        if matches:self.state['duplicates'].append(dict(source=name,source_listing_id=sid,source_url=detail,reason='FINGERPRINT_LINK_NOT_PHYSICAL_PROOF',detail_requested=True,matched_keys=matches,protected_matches=held))
                        record['quality_flags']=sorted(set(record['quality_flags']));record['quality_score']=max(0,100-10*len(record['quality_flags']))
                        # Every observation is cached, never just the passing rows.
                        self.state['records'][key]=record;self.state['seen'][key]={'status':record['quality_status'],'evidence_sha256':stored['sha256']}
                        self.index.add(dict(record,detail_url=record['source_url'],is_protected_holdout=bool(held)))
                        self.save()
                    except SourceUnavailable as exc:
                        self.unavailable(name,card,str(exc))
                        if client.closed:raise
                    except (ValueError,KeyError,IndexError) as exc:
                        self.unavailable(name,card,'EXTRACTION_OR_EVIDENCE_FAILED_'+type(exc).__name__)
                url=next_url
        except SourceUnavailable as exc:self.state['policies'].append(dict(source=name,status='SOURCE_UNAVAILABLE',reason=str(exc)))
        finally:self.requests+=client.requests;self.save()
    def export(self):
        records=list(self.state['records'].values())
        raw=[]
        for r in records:
            observed=dict(r);source=r.get('source_fields',{})
            observed.update(price_raw=source.get('price_raw'),area_raw=source.get('area_raw'),source_category_raw=source.get('category_raw'),address_raw=source.get('address_raw'))
            raw.append(observed)
        dump_csv(self.out/'new_raw_listings.csv',raw,['source','source_listing_id','record_key','source_url','crawled_at','published_at','updated_at','date_basis','source_evidence_reference','title','description','price_raw','area_raw','source_category_raw','address_raw','quality_status','verification_status'])
        for name,status in [('new_clean_listings.csv','READY_FOR_INTERNAL_REVIEW'),('new_needs_review.csv','NEEDS_REVIEW'),('new_rejected_listings.csv','REJECTED'),('new_source_unavailable.csv','SOURCE_UNAVAILABLE')]:
            dump_csv(self.out/name,[r for r in records if r['quality_status']==status],DATASET_FIELDS)
        dump_csv(self.out/'quality_audit.csv',records,['record_key','source','source_listing_id','quality_status','quality_score','quality_flags','source_evidence_reference','verification_status','duplicate_status','holdout_status','evidence_status'])
        dump_csv(self.out/'source_evidence_manifest.csv',self.state['evidence'],['source','source_listing_id','source_url','reference','sha256','response_sha256','fetched_at','evidence_type','kind','original_response_persisted','copyright_notices','discovery_reference','source_price_raw','source_area_raw','source_category','source_date_meta','source_product_offer_observations'])
        dump_csv(self.out/'duplicate_audit.csv',self.state['duplicates'],['source','source_listing_id','source_url','reason','detail_requested','matched_keys','protected_matches'])
        dump_csv(self.out/'source_policy_audit.csv',self.state['policies'],['source','status','reason','policy','terms_url','url','sha256','observed_at'])
        per_source={}
        for name in SOURCES:
            source_rows=[r for r in records if r['source']==name];counts=Counter(r['quality_status'] for r in source_rows)
            per_source[name]=dict(total_new=len(source_rows),statuses=dict(counts),pass_rate=counts['READY_FOR_INTERNAL_REVIEW']/len(source_rows) if source_rows else None,
                flags=dict(Counter(f for r in source_rows for f in r['quality_flags'])))
        summary=dict(new_attempts_this_run=self.new_count,total_new_observations=len(records),classifications=dict(Counter(r['quality_status'] for r in records)),
            requests_this_run=self.requests,per_source=per_source,known_old_identity_count=len(self.index.keys),protected_identity_count=len(self.index.holdouts),
            duplicate_events=len(self.state['duplicates']),unique_identity_skips=len({(r['source'],r['source_listing_id']) for r in self.state['duplicates'] if not r['detail_requested']}),
            all_unverified=all(r['verification_status']=='UNVERIFIED' for r in records),mysql_writes=0,training_allowed=False,public_display_allowed=False,
            max_new_this_run=self.max_new,max_pages_per_source=self.max_pages)
        (self.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        self.save();return summary
