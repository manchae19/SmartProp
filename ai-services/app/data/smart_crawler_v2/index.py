"""Old-data access is restricted to identity and dedup/holdout fingerprints.

No old HTML is opened, no labels repaired and no legacy decision is changed.
"""
import csv,hashlib,json,re,unicodedata
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from .sources import DATA,identity

ROOT=DATA.parents[2]
def norm(value):return ' '.join(''.join(c for c in unicodedata.normalize('NFD',str(value or '').lower()) if not unicodedata.combining(c)).replace('đ','d').split())
def hash_value(value):return hashlib.sha256(value.encode('utf8')).hexdigest()
def canonical_url(url):
    p=urlsplit(url or '')
    if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password:raise ValueError('Invalid source URL')
    return urlunsplit(('https',p.hostname.removeprefix('www.').lower(),p.path.rstrip('/'),'',''))

def fingerprints(row):
    category=norm(row.get('property_type') or row.get('category'))
    category={'house':'nha o','apartment':'can ho chung cu','land':'dat nen'}.get(category,category)
    district=norm(row.get('district'));area=str(row.get('area_sqm') or '')
    try:
        from decimal import Decimal
        area=str(Decimal(area).normalize())
    except Exception:return []
    if not category or not district or not area:return []
    title=norm(row.get('title'));address=norm(row.get('address') or row.get('address_raw'))
    keys=[]
    # These links cause quarantine/review, never a physical-identity merge.
    if len(title.split())>=7:keys.append(hash_value('TITLE_AREA|'+category+'|'+district+'|'+area+'|'+title))
    # Require an actual number in the address; a district/street alone is weak.
    if len(address.split())>=5 and re.search(r'\b\d+[a-z]?(?:/\d+)*\s+',address):
        keys.append(hash_value('ADDRESS_AREA|'+category+'|'+district+'|'+area+'|'+address))
    return keys

class OldIndex:
    def __init__(self):self.keys=set();self.urls=set();self.fps={};self.holdouts=set();self.inputs={};self.groups={};self.protected_groups=set()
    def add(self,row,source_hint=''):
        source=row.get('source') or source_hint
        key=row.get('record_key') or row.get('list_id') or ''
        sid=str(row.get('source_listing_id') or '')
        url=row.get('source_url') or row.get('detail_url') or ''
        if not source and ':' in key:source=key.split(':',1)[0]
        if ':' in sid:sid=sid.split(':',1)[1]
        if not sid and ':' in key:sid=key.split(':',1)[1]
        if not sid.isdigit() and source and url:sid=identity(source,url)
        try:self.urls.add(canonical_url(url))
        except ValueError:pass
        if source not in {'cafeland','nhadat24h','homedy','alonhadat','chotot'} or not sid.isdigit():return
        key=source+':'+sid;self.keys.add(key)
        held=str(row.get('protected_holdout',row.get('is_protected_holdout',''))).lower() in {'true','1'}
        if held:self.holdouts.add(key)
        for field in ['pipeline_group','duplicate_group','duplicate_candidate_group']:
            group=row.get(field)
            if group:
                self.groups.setdefault(group,set()).add(key)
                if held:self.protected_groups.add(group)
        for fp in fingerprints(row):self.fps.setdefault(fp,set()).add(key)
    def protect_groups(self):
        changed=True
        while changed:
            count=len(self.holdouts)
            for group,members in self.groups.items():
                if group in self.protected_groups or members&self.holdouts:
                    self.protected_groups.add(group);self.holdouts.update(members)
            changed=len(self.holdouts)!=count
    def match_identity(self,source,sid,url):
        key=source+':'+sid
        if key in self.keys:return 'KNOWN_SOURCE_ID'
        try:
            if canonical_url(url) in self.urls:return 'KNOWN_SOURCE_URL'
        except ValueError:return 'INVALID_SOURCE_URL'
        return None
    def match_fingerprints(self,row):
        matches=set()
        for fp in fingerprints(row):matches.update(self.fps.get(fp,set()))
        return sorted(matches),sorted(matches&self.holdouts)
    @classmethod
    def load(cls):
        index=cls()
        # Enumerate raw snapshots for keys/URLs only; no old descriptions/HTML.
        for file in sorted((DATA/'data_raw').rglob('*')):
            if file.suffix.lower() not in {'.csv','.jsonl'} or 'singapore_hdb' in file.parts:continue
            hint=next((s for s in ['cafeland','nhadat24h','homedy','alonhadat','chotot'] if s in str(file).lower()),'')
            try:
                with file.open(encoding='utf-8-sig',newline='') as f:
                    records=csv.DictReader(f) if file.suffix=='.csv' else (json.loads(line) for line in f if line.strip())
                    for row in records:
                        # Ignore all other raw data fields, including contacts.
                        index.add({k:row.get(k,'') for k in ['source','source_listing_id','source_url','detail_url','record_key','list_id']},hint)
                index.inputs[str(file.relative_to(ROOT))]=hashlib.sha256(file.read_bytes()).hexdigest()
            except (OSError,UnicodeError,json.JSONDecodeError,csv.Error) as exc:
                raise RuntimeError('Cannot build complete old-ID index: '+str(file)) from exc
        pipeline=DATA/'processed/remaining_diversity_review/runs/518bbc989587326c/all_listings_after_review.csv'
        with pipeline.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                fields=['source','source_listing_id','detail_url','record_key','title','category','district','area_sqm','address_raw','pipeline_group','duplicate_candidate_group','protected_holdout']
                index.add({k:row.get(k,'') for k in fields})
        index.inputs[str(pipeline.relative_to(ROOT))]=hashlib.sha256(pipeline.read_bytes()).hexdigest()
        # Remember failed/blocked old fetch identities too, without reopening any
        # old page or rerunning its extraction/recovery pipeline.
        manifest=DATA/'processed/collection_source_review/fetch_manifest.json'
        if manifest.exists():
            for key,meta in json.loads(manifest.read_text(encoding='utf8')).items():
                if ':' in key:
                    source,sid=key.split(':',1);index.add({'source':source,'source_listing_id':sid,'detail_url':meta.get('requested_url','')})
            index.inputs[str(manifest.relative_to(ROOT))]=hashlib.sha256(manifest.read_bytes()).hexdigest()
        blocked=ROOT/'.scratch/hybrid-full-audit/step18-4/blocked.csv'
        if blocked.exists():
            with blocked.open(encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):
                    if 'HOLDOUT' in row.get('reason_code',''):index.holdouts.add(row['record_key'])
            index.inputs[str(blocked.relative_to(ROOT))]=hashlib.sha256(blocked.read_bytes()).hexdigest()
        index.protect_groups();return index

    def add_mysql_readonly(self):
        import importlib.util,sys
        scripts=ROOT/'backend/scripts'
        if str(scripts) not in sys.path:sys.path.insert(0,str(scripts))
        spec=importlib.util.spec_from_file_location('v2_readonly_local',scripts/'flyway-local-forward.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);client=module.Local()
        ident=client.objects("SELECT JSON_OBJECT('database',DATABASE(),'port',@@port,'server_uuid',@@server_uuid)")[0]
        if ident['database']!='smartprop' or ident['port']!=3306 or ident['server_uuid']!=module.SERVER_UUID:raise RuntimeError('Wrong Local database')
        rows=client.objects("""SELECT JSON_OBJECT('source',source,'source_listing_id',source_listing_id,'record_key',record_key,'detail_url',detail_url,
         'title',title,'category',category,'district',district,'area_sqm',CAST(area_sqm AS CHAR),'address_raw',address_raw,
         'duplicate_group',duplicate_group,'is_protected_holdout',is_protected_holdout) FROM external_listings""")
        if len(rows)!=3204 or sum(bool(r['is_protected_holdout']) for r in rows)!=983:raise RuntimeError('Unexpected current external/holdout inventory')
        for r in rows:self.add(r)
        internal=client.objects("SELECT JSON_OBJECT('record_key',CONCAT('property:',id),'title',title,'category',property_type,'district',district,'area_sqm',CAST(area_sqm AS CHAR),'address_raw',address) FROM properties")
        for row in internal:
            for fp in fingerprints(row):self.fps.setdefault(fp,set()).add(row['record_key'])
        self.protect_groups()
        checks='CHECKSUM TABLE external_listings,external_duplicate_groups,properties,property_images,flyway_schema_history EXTENDED'
        before=client.query(checks)
        return client,checks,before,dict(identity=ident,external_count=len(rows),protected_holdout_count=983,internal_properties=len(internal))
