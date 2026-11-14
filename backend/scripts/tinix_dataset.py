"""Pinned TiniX research import, Local smartprop only. No legacy source writes.

prepare: stream Parquet to disk-backed SQLite, preserve original fields and bits.
migrate: Flyway V19 only, after checking original Local history and all 48 tables.
import: 5,000-row acceptance then full import, transactional batches, replay checks.
"""
import argparse,collections,datetime,hashlib,importlib.util,json,math,os,sqlite3,sys
from pathlib import Path
from decimal import Decimal
from tinix_quality import quality,canonical,norm,sha,RULE,restore_original
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.scratch/tinix-integration/step19-1'
DATASET='tinixai/vietnam-real-estates';REVISION='ca3fedcbb089bf65f7e4cfb03316cce4bd0d779f';LICENSE='cc-by-nc-4.0'
def load_local():
    spec=importlib.util.spec_from_file_location('tinix_local',ROOT/'backend/scripts/flyway-local-forward.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.Local()
def save(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def prepared():
    db=sqlite3.connect(OUT/'staging.sqlite');db.row_factory=sqlite3.Row
    db.execute('PRAGMA mmap_size=1073741824');db.execute('PRAGMA cache_size=-65536')
    return db
def protected_snapshot(local):
    # Never read all large staging JSON blobs just to verify unrelated tables.
    # The importer independently roundtrips every source field on both passes.
    before=json.loads((OUT/'mysql-before.json').read_text())
    identity=local.objects("SELECT JSON_OBJECT('database',DATABASE(),'port',@@port,'server_uuid',@@server_uuid,'version',VERSION())")[0]
    names=local.query("SELECT table_name FROM information_schema.tables WHERE table_schema='smartprop' AND table_type='BASE TABLE' ORDER BY table_name").splitlines()
    if set(names)!=set(before['ddl'])|{'tinix_dataset_records'}:raise RuntimeError('Unexpected table inventory')
    old=sorted(before['ddl']);ddl={n:local.query('SHOW CREATE TABLE smartprop.`'+n+'`').split('\t',1)[1].strip() for n in names}
    counts={n:int(local.query('SELECT COUNT(*) FROM smartprop.`'+n+'`')) for n in names}
    checksums={line.split('\t')[0].split('.',1)[1]:line.split('\t')[1] for line in local.query('CHECKSUM TABLE '+','.join('smartprop.`'+n+'`' for n in old)+' EXTENDED').splitlines()}
    history=local.objects("SELECT JSON_OBJECT('version',version,'type',type,'checksum',checksum,'success',success,'script',script) FROM flyway_schema_history ORDER BY installed_rank")
    triggers=local.objects("SELECT JSON_OBJECT('name',trigger_name,'timing',action_timing,'event',event_manipulation,'table',event_object_table,'body',action_statement) FROM information_schema.triggers WHERE trigger_schema='smartprop' ORDER BY trigger_name")
    return dict(identity=identity,ddl=ddl,rowcounts=counts,checksums=checksums,history=history,triggers=triggers)
def replay_fingerprint(local):
    # Covering secondary index: avoid scanning large clustered JSON/TEXT rows.
    # Every payload/hash/original column is verified separately on both passes.
    return local.query("SELECT JSON_OBJECT('rows',COUNT(*),'ids',BIT_XOR(CRC32(internal_id)),'eligibility',BIT_XOR(CRC32(CONCAT_WS('|',internal_id,quality_status,is_duplicate_representative,is_protected_holdout,transaction_type,price_vnd)))) FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)")
def prepare():
    import pyarrow.parquet as pq,pyarrow.compute as pc
    sys.path.insert(0,str(ROOT/'ai-services'))
    from app.data.smart_crawler_v2.index import OldIndex
    manifest=json.loads((OUT/'download-manifest.json').read_text())
    if manifest['revision']!=REVISION or manifest['license']!=LICENSE or len(manifest['files'])!=10:raise RuntimeError('Incomplete pinned dataset')
    index=OldIndex.load();local,_,_,dbfacts=index.add_mysql_readonly()
    try:save('dedup-input-manifest.json',dict(files=index.inputs,mysql=dbfacts,protected_identity_count=len(index.holdouts)))
    finally:local.close()
    stage=prepared()
    stage.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY,ref TEXT UNIQUE,payload_hash TEXT,grp TEXT,held INTEGER,status TEXT,record TEXT,representative INTEGER DEFAULT 0)')
    if stage.execute('SELECT COUNT(*) FROM records').fetchone()[0]:raise RuntimeError('Staging exists; use already prepared data, never overwrite automatically')
    nulls=collections.Counter();types=collections.Counter();scanned=0;danang=0;schema=None
    for item in manifest['files']:
        path=OUT/'parquet'/item['path'];h=hashlib.sha256()
        with path.open('rb') as f:
            for part in iter(lambda:f.read(2**20),b''):h.update(part)
        if h.hexdigest()!=item['sha256']:raise RuntimeError('Changed Parquet shard')
        pf=pq.ParquetFile(path);current={f.name:str(f.type) for f in pf.schema_arrow}
        if schema is not None and schema!=current:raise RuntimeError('Shard schema drift')
        schema=current;offset=0
        for batch in pf.iter_batches(batch_size=2048):
            # Filter without changing original physical row reference.
            province=batch.column('province_name').to_pylist()
            wanted=[i for i,v in enumerate(province) if norm(v)=='da nang']
            rows=batch.take(wanted).to_pylist() if wanted else []
            for ordinal,row in zip(wanted,rows):
                ref=f"{item['path']}:{offset+ordinal}";rid=sha(DATASET+'@'+REVISION+':'+ref)
                numeric={k:v.hex() for k,v in row.items() if isinstance(v,float)}
                raw={k:({'$nonfinite_float64':v.hex()} if isinstance(v,float) and not math.isfinite(v) else v) for k,v in row.items()}
                q=quality(raw);payload=canonical(raw);ph=sha(payload)
                for k,v in row.items():
                    if v is None:nulls[k]+=1
                types[str(row.get('property_type_name'))]+=1
                # Reuse only ID/holdout/fingerprint metadata, never recovery or HTML.
                fp={'title':row.get('name'),'category':{'HOUSE':'Nhà ở','LAND':'Đất nền','APARTMENT':'Căn hộ chung cư','VILLA':'VILLA'}.get(q['normalized_type'],''),
                    'district':q['district'],'area_sqm':q['area_sqm'],'address_raw':None}
                matched,held=index.match_fingerprints(fp)
                if matched:q['quality_issues'].append('LEGACY_ASSET_FINGERPRINT_MATCH')
                if held:q['quality_issues'].append('PROTECTED_HOLDOUT_FINGERPRINT_CONFLICT')
                if matched and q['quality_status']=='HYBRID_ELIGIBLE_RESEARCH':q['quality_status']='EXCLUDED' if held else 'NEEDS_REVIEW'
                group=sha(canonical([norm(row.get('name')),norm(row.get('property_type_name')),norm(row.get('district_name')),norm(row.get('ward_name')),q['area_sqm']]))
                if not norm(row.get('name')):group=sha(payload)
                record=dict(internal_id=rid,dataset_name=DATASET,dataset_revision=REVISION,dataset_license=LICENSE,row_reference=ref,
                    raw_payload=raw,raw_numeric_ieee754=numeric,payload_sha256=ph,**q,duplicate_group=group,
                    is_protected_holdout=bool(held),quality_rule_version=RULE,legacy_matches=matched)
                stage.execute('INSERT INTO records(id,ref,payload_hash,grp,held,status,record) VALUES(?,?,?,?,?,?,?)',(rid,ref,ph,group,bool(held),q['quality_status'],canonical(record)))
                danang+=1
            offset+=batch.num_rows;scanned+=batch.num_rows
        stage.commit();print(f'STAGED {item["path"]}: scanned={scanned} DaNang={danang}',flush=True)
    # A protected member quarantines the whole suspicion group. Other duplicate
    # rows remain staging; a single eligible representative may be recommended.
    stage.execute("UPDATE records SET held=1,status='EXCLUDED' WHERE grp IN (SELECT grp FROM records WHERE held=1)")
    stage.execute("UPDATE records SET representative=1 WHERE id IN (SELECT MIN(id) FROM records WHERE status='HYBRID_ELIGIBLE_RESEARCH' AND held=0 GROUP BY grp)")
    stage.commit()
    result=dict(dataset=DATASET,revision=REVISION,license=LICENSE,scanned=scanned,danang=danang,schema=schema,field_count=len(schema),null_counts=dict(nulls),types=dict(types),
        quality=dict(stage.execute('SELECT status,COUNT(*) FROM records GROUP BY status').fetchall()),eligible_representatives=stage.execute('SELECT COUNT(*) FROM records WHERE representative=1').fetchone()[0],
        duplicate_rows=stage.execute('SELECT COUNT(*)-COUNT(DISTINCT grp) FROM records').fetchone()[0],duplicate_groups=stage.execute('SELECT COUNT(*) FROM (SELECT grp FROM records GROUP BY grp HAVING COUNT(*)>1)').fetchone()[0],
        held=stage.execute('SELECT COUNT(*) FROM records WHERE held=1').fetchone()[0],holdout_fingerprint_limit='Exact long-title/category/district/area match only; physical identity cannot be established without source IDs or precise address.')
    save('staging-summary.json',result);stage.close();print(json.dumps(result,ensure_ascii=False),flush=True)
def assert_identity(local):
    identity=local.objects("SELECT JSON_OBJECT('database',DATABASE(),'port',@@port,'uuid',@@server_uuid)")[0]
    if identity!={'database':'smartprop','port':3306,'uuid':'60f0e116-d443-11f1-bdbf-7085c2fe30d2'}:raise RuntimeError('Wrong Local target')
    branch=__import__('subprocess').check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='backend-huy-latest':raise RuntimeError('Wrong branch')
def flyway(local,goal,pending=False):
    if goal not in {'validate','migrate','info'}:raise RuntimeError('Forbidden Flyway goal')
    args=[str(ROOT/'backend/mvnw.cmd'),'--batch-mode','--no-transfer-progress','-Dmaven.repo.local='+str(ROOT/'.scratch/m2'),
        '-Phybrid-local-existing-v13','-Dflyway.locations=filesystem:'+str(ROOT/'database/legacy-hybrid-local')+',filesystem:'+str(ROOT/'database/research-migrations'),
        '-Dflyway.url=jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC','-Dflyway.schemas=smartprop','-Dflyway.defaultSchema=smartprop',
        '-Dflyway.createSchemas=false','-Dflyway.cleanDisabled=true','-Dflyway.baselineOnMigrate=false','-Dflyway.outOfOrder=false',
        '-Dflyway.target=19','-Dflyway.ignoreMigrationPatterns='+('*:pending' if pending else ''),'org.flywaydb:flyway-maven-plugin:11.7.2:'+goal]
    output=local.command(args,timeout=300);(OUT/('flyway-'+goal+('-pre' if pending else '')+'.log')).write_text(local.redact(output),encoding='utf8')
def compare_old(before,after,history_allowed=False):
    for n in before['ddl']:
        if n=='tinix_dataset_records' or (history_allowed and n=='flyway_schema_history'):continue
        for key in ['ddl','rowcounts','checksums']:
            if before[key][n]!=after[key].get(n):raise RuntimeError('STOP unexpected old table change:'+n+':'+key)
    if before['triggers']!=after['triggers']:raise RuntimeError('Existing triggers changed')
def migrate():
    local=load_local()
    try:
        assert_identity(local);before=local.snapshot()
        expected=[('13','BASELINE',None),('14','SQL',-1382804267),('17','SQL',675090364),('18','SQL',-1428745198)]
        if [(r['version'],r['type'],r['checksum']) for r in before['history']]!=expected or any(r['success']!=1 for r in before['history']) or len(before['ddl'])!=48:raise RuntimeError('Unexpected history/schema, no automatic retries')
        original=json.loads((OUT/'mysql-before.json').read_text());compare_old(original,before)
        sql=(ROOT/'database/research-migrations/V19__tinix_research_staging.sql').read_text()
        # Exactly one additive CREATE TABLE, no arbitrary SQL or old-table mutation.
        import mysql_schema_contract as contract
        tables=contract.schema(sql)
        if set(tables)!={'tinix_dataset_records'} or any(x in sql.upper() for x in ['DROP ','TRUNCATE ','ALTER ','INSERT ','UPDATE ','DELETE ']):raise RuntimeError('Migration exceeds staging scope')
        flyway(local,'validate',pending=True)
        save('migration-preflight.json',dict(identity=before['identity'],history=before['history'],tables_before=48,table_to_create='tinix_dataset_records',migration_sha256=sha(sql),backup_requested=False,explicit_user_authorization='Step19.1'))
        flyway(local,'migrate');flyway(local,'validate');after=local.snapshot();compare_old(before,after,True)
        if len(after['ddl'])!=49 or after['history'][:-1]!=before['history'] or after['history'][-1]['version']!='19' or after['history'][-1]['success']!=1:raise RuntimeError('Unexpected V19 result')
        save('mysql-after-migration.json',after);print('V19 PASS: 49 tables; previous 48 unchanged except Flyway history',flush=True)
    finally:local.close()
ORIGINAL=['name','description','property_type_name','province_name','district_name','ward_name','street_name','project_name','price','area','floor_count','frontage_width','house_depth','road_width','bedroom_count','bathroom_count','house_direction','balcony_direction','published_at']
META=['internal_id','dataset_name','dataset_revision','dataset_license','row_reference','raw_payload','raw_numeric_ieee754','payload_sha256','price_vnd','area_sqm','normalized_type','district','ward','transaction_type','transaction_basis','quality_status','quality_issues','is_protected_holdout','duplicate_group','is_duplicate_representative','quality_rule_version']
def import_data():
    import pymysql
    local=load_local();stage=prepared();conn=None
    try:
        assert_identity(local);flyway(local,'validate');before=protected_snapshot(local)
        if 'tinix_dataset_records' not in before['ddl'] or before['history'][-1]['version']!='19':raise RuntimeError('Apply approved V19 first')
        summary=json.loads((OUT/'staging-summary.json').read_text());expected=summary['danang']
        if expected<5000 or stage.execute('SELECT COUNT(*) FROM records').fetchone()[0]!=expected:raise RuntimeError('Staging incomplete')
        conn=pymysql.connect(host='127.0.0.1',port=3306,user=local.user,password=local.password,database='smartprop',charset='utf8mb4',autocommit=False,connect_timeout=5)
        columns=META+ORIGINAL
        sql='INSERT INTO tinix_dataset_records ('+','.join('`'+x+'`' for x in columns)+') VALUES ('+','.join(['%s']*len(columns))+') ON DUPLICATE KEY UPDATE internal_id=tinix_dataset_records.internal_id'
        def one_pass(limit,label):
            # Sequential clustered-primary-key order avoids random disk I/O on
            # a small Local InnoDB buffer pool. All values are still verified.
            cursor=stage.execute('SELECT * FROM records ORDER BY id LIMIT ?', (limit,));seen=0
            while rows:=cursor.fetchmany(1000):
                values=[];originals={}
                for r in rows:
                    d=json.loads(r['record']);d.update(quality_status=r['status'],is_protected_holdout=bool(r['held']),is_duplicate_representative=bool(r['representative']))
                    raw=d['raw_payload'];originals[r['id']]=d
                    value=[]
                    for field in columns:
                        v=raw.get(field) if field in ORIGINAL else d[field]
                        if field in {'raw_payload','raw_numeric_ieee754','quality_issues'}:v=canonical(v)
                        elif isinstance(v,dict):v=None
                        value.append(v)
                    values.append(tuple(value))
                try:
                    with conn.cursor() as cur:
                        # Detect conflicts instead of overwriting earlier staging decisions.
                        cur.execute('SELECT internal_id,payload_sha256,quality_rule_version FROM tinix_dataset_records WHERE internal_id IN ('+','.join(['%s']*len(rows))+')',tuple(originals))
                        existing=cur.fetchall();present=set()
                        for rid,ph,rule in existing:
                            if ph!=originals[rid]['payload_sha256'] or rule!=RULE:raise RuntimeError('Immutable row conflict:'+rid)
                            present.add(rid)
                        fresh=[v for v in values if v[0] not in present]
                        # A replay does not parse/write megabytes of unchanged
                        # payloads. The same full roundtrip verifier runs below.
                        if fresh:cur.executemany(sql,fresh)
                        cur.execute('SELECT internal_id,raw_payload,raw_numeric_ieee754,price_vnd,area_sqm,quality_status,verification_status,research_only,listing_availability,'+','.join('`'+f+'`' for f in ORIGINAL)+' FROM tinix_dataset_records WHERE internal_id IN ('+','.join(['%s']*len(rows))+')',tuple(originals))
                        stored=cur.fetchall()
                        if len(stored)!=len(rows):raise RuntimeError('Batch incomplete')
                        for result in stored:
                            rid,payload,bits,p,a,status,verification,research,available=result[:9]
                            d=originals[rid]
                            reconstructed=restore_original(json.loads(payload),json.loads(bits))
                            if reconstructed!=d['raw_payload'] or sha(canonical(reconstructed))!=d['payload_sha256'] or json.loads(bits)!=d['raw_numeric_ieee754'] or p!=(Decimal(d['price_vnd']) if d['price_vnd'] else None) or a!=(Decimal(d['area_sqm']) if d['area_sqm'] else None) or status!=d['quality_status'] or (verification,research,available)!=('UNVERIFIED',1,'UNKNOWN'):raise RuntimeError('Roundtrip mismatch:'+rid)
                            for field,value in zip(ORIGINAL,result[9:]):
                                expected=d['raw_payload'].get(field)
                                if isinstance(expected,dict):expected=None
                                if value!=expected or isinstance(value,float) and value.hex()!=d['raw_numeric_ieee754'][field]:raise RuntimeError('Original typed column mismatch:'+rid+':'+field)
                    conn.commit()
                except Exception:conn.rollback();raise
                seen+=len(rows)
                if seen%5000==0:print(f'{label}: verified {seen}/{limit}',flush=True)
            return seen
        a=one_pass(5000,'PHASE_A');checksum_a=replay_fingerprint(local);count_a=int(local.query('SELECT COUNT(*) FROM tinix_dataset_records'))
        one_pass(5000,'PHASE_A_REPLAY')
        if checksum_a!=replay_fingerprint(local):raise RuntimeError('Sample replay changed records')
        save('phase-a-receipt.json',dict(verified=a,table_count=count_a,all_fields_roundtrip=True,decimal_roundtrip=True,idempotent=True))
        one_pass(expected,'PHASE_B');checksum_b=replay_fingerprint(local)
        one_pass(expected,'PHASE_B_REPLAY')
        if checksum_b!=replay_fingerprint(local):raise RuntimeError('Full replay changed rows')
        after=protected_snapshot(local);compare_old(before,after)
        stats=local.objects("SELECT JSON_OBJECT('quality',quality_status,'rows',COUNT(*),'representatives',SUM(is_duplicate_representative),'held',SUM(is_protected_holdout)) FROM tinix_dataset_records GROUP BY quality_status")
        if after['rowcounts']['tinix_dataset_records']!=expected:raise RuntimeError('Unexpected staging count')
        save('mysql-after-import.json',after);save('import-receipt.json',dict(rows=expected,quality=stats,phase_a=a,all_fields_roundtrip=True,idempotent=True,unchanged_existing_tables=48,checksum=checksum_b));print(json.dumps(stats),flush=True)
    finally:
        if conn:conn.close()
        stage.close();local.close()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','migrate','import']);a=p.parse_args()
    try:{'prepare':prepare,'migrate':migrate,'import':import_data}[a.action]()
    except Exception as e:print('STOP: '+str(e),file=sys.stderr);sys.exit(1)
