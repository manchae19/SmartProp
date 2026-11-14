"""Read-only MySQL audit + offline TINIX_RESEARCH_V2 proposal. NO apply mode.

capture / evaluate / verify write only local audit artifacts. They never call
the importer, Flyway, DML or schema changes against MySQL.
"""
import argparse,collections,csv,datetime,hashlib,importlib.util,json,re,sqlite3,sys
from pathlib import Path
from tinix_quality import canonical,restore_original,sha
from tinix_quality_v2 import evaluate,RULE
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.scratch/tinix-quality-v2';STAGE=ROOT/'.scratch/tinix-integration/step19-1/staging.sqlite'
EXPECTED={'HYBRID_ELIGIBLE_RESEARCH':78462,'NEEDS_REVIEW':91647,'EXCLUDED':15864}
META_SQL="""SELECT internal_id,payload_sha256,quality_status,quality_issues,is_protected_holdout,
 duplicate_group,is_duplicate_representative,quality_rule_version,CAST(price_vnd AS CHAR),CAST(area_sqm AS CHAR)
 FROM tinix_dataset_records ORDER BY internal_id"""
def source_hashes():
    files=[ROOT/'backend/scripts/tinix_quality.py',ROOT/'backend/scripts/tinix_dataset.py',ROOT/'.env',ROOT/'frontend/vue.ui/src/components/business/ListingCard.vue']+list((ROOT/'database').rglob('V*.sql'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
def load(name):return json.loads((OUT/name).read_text(encoding='utf8'))
def local_credentials():
    spec=importlib.util.spec_from_file_location('tinix_v2_readonly_local',ROOT/'backend/scripts/flyway-local-forward.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.Local()
def select(cursor,sql,args=None):
    if not re.match(r'^\s*(SELECT|SHOW|CHECKSUM)\b',sql,re.I) or ';' in sql:raise ValueError('DRY RUN permits only one read-only MySQL statement')
    cursor.execute(sql,args);return cursor
def connect():
    import pymysql
    private=local_credentials()
    try:
        conn=pymysql.connect(host='127.0.0.1',port=3306,database='smartprop',user=private.user,password=private.password,
            charset='utf8mb4',autocommit=False,connect_timeout=5,read_timeout=180,init_command='SET SESSION TRANSACTION READ ONLY')
    finally:private.close()
    conn.begin()
    with conn.cursor() as c:
        select(c,'SELECT DATABASE(),@@port,@@server_uuid,@@session.transaction_read_only');identity=c.fetchone()
    if identity!=('smartprop',3306,'60f0e116-d443-11f1-bdbf-7085c2fe30d2',1):conn.close();raise RuntimeError('Wrong target or transaction not read-only')
    return conn
def facts(conn):
    with conn.cursor() as c:
        select(c,'SELECT quality_status,COUNT(*),SUM(is_duplicate_representative),SUM(is_protected_holdout) FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid) GROUP BY quality_status')
        rows=[(r[0],int(r[1]),int(r[2]),int(r[3])) for r in c.fetchall()]
        if {r[0]:r[1] for r in rows}!=EXPECTED or sum(r[2] for r in rows)!=55816:raise RuntimeError('Unexpected V1 baseline; no writes')
        select(c,'SELECT COUNT(*) FROM external_listings WHERE is_protected_holdout=1');held=c.fetchone()[0]
        select(c,'CHECKSUM TABLE external_listings,external_duplicate_groups EXTENDED');checks=c.fetchall()
        if held!=983:raise RuntimeError('Crawler holdout inventory changed')
        return dict(tinix=[list(r) for r in rows],crawler_holdouts=held,crawler_checksums=[list(r) for r in checks])
def auditdb():
    db=sqlite3.connect(OUT/'baseline.sqlite');db.row_factory=sqlite3.Row;db.execute('PRAGMA mmap_size=1073741824');db.execute('PRAGMA cache_size=-65536');return db
def stage():
    db=sqlite3.connect(STAGE.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA mmap_size=1073741824');db.execute('PRAGMA cache_size=-65536');return db
def capture():
    import pymysql
    OUT.mkdir(exist_ok=True);path=OUT/'baseline.sqlite'
    if path.exists():raise RuntimeError('Baseline already captured; never overwrite it automatically')
    db=auditdb();db.execute('CREATE TABLE base(id TEXT PRIMARY KEY,ph TEXT,status TEXT,issues TEXT,held INTEGER,grp TEXT,rep INTEGER,rule TEXT,price TEXT,area TEXT)')
    conn=connect();before=facts(conn);h=hashlib.sha256();count=0;cohorts=collections.Counter()
    try:
        with conn.cursor(pymysql.cursors.SSCursor) as c:
            select(c,META_SQL)
            while rows:=c.fetchmany(2000):
                for row in rows:
                    if row[7]!='TINIX_RESEARCH_V1':raise RuntimeError('Non-V1 row; stop audit')
                    h.update((canonical(row)+'\n').encode());flags=json.loads(row[3])
                    if row[2]=='NEEDS_REVIEW' and len(flags)==1:cohorts[flags[0]]+=1
                db.executemany('INSERT INTO base VALUES(?,?,?,?,?,?,?,?,?,?)',rows);count+=len(rows)
        if count!=185973 or cohorts['MULTIPLE_ASSETS']!=6483 or cohorts['SHORTHAND_TOTAL_PRICE']!=9992:raise RuntimeError('Baseline/cohort mismatch')
        db.commit();save('baseline.json',dict(captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=count,metadata_sha256=h.hexdigest(),facts=before,cohorts=dict(cohorts),protected_file_hashes=source_hashes(),read_only=True))
        print('READ-ONLY baseline captured:',count,'rows; cohorts:',cohorts['MULTIPLE_ASSETS'],cohorts['SHORTHAND_TOTAL_PRICE'],flush=True)
    finally:conn.rollback();conn.close();db.close()
def cohort(status,issues):
    return issues[0]+'_ONLY' if status=='NEEDS_REVIEW' and len(issues)==1 and issues[0] in {'MULTIPLE_ASSETS','SHORTHAND_TOTAL_PRICE'} else 'OTHER'
def finalize_capture():
    """Finish local receipt after a JSON serialization failure; no data re-import."""
    if (OUT/'baseline.json').exists():raise RuntimeError('Existing receipt is immutable')
    db=auditdb();h=hashlib.sha256();count=0;cohorts=collections.Counter();statuses=collections.Counter();reps=0
    for r in db.execute('SELECT * FROM base ORDER BY id'):
        values=tuple(r);h.update((canonical(values)+'\n').encode());count+=1;statuses[r['status']]+=1;reps+=r['rep'];flags=json.loads(r['issues'])
        if r['status']=='NEEDS_REVIEW' and len(flags)==1:cohorts[flags[0]]+=1
    if count!=185973 or dict(statuses)!=EXPECTED or reps!=55816 or cohorts['MULTIPLE_ASSETS']!=6483 or cohorts['SHORTHAND_TOTAL_PRICE']!=9992:raise RuntimeError('Incomplete capture; do not finalize')
    conn=connect()
    try:before=facts(conn)
    finally:conn.rollback();conn.close()
    save('baseline.json',dict(captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=count,metadata_sha256=h.hexdigest(),facts=before,cohorts=dict(cohorts),protected_file_hashes=source_hashes(),read_only=True,local_receipt_recovery='SUM Decimal serialization; full SELECT export already committed locally, no MySQL writes'))
    db.close();print('Local receipt finalized for185973 read-only exported rows',flush=True)
def run():
    baseline=load('baseline.json');rule_start_sha=hashlib.sha256((ROOT/'backend/scripts/tinix_quality_v2.py').read_bytes()).hexdigest()
    # Each proposal is a new local file. Never DROP/rewrite the captured baseline.
    recovery=auditdb();recovery.execute('SELECT COUNT(*) FROM base').fetchone();recovery.close()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    proposal_file=OUT/('proposal-'+stamp+'.sqlite');db=sqlite3.connect(proposal_file,uri=True);db.row_factory=sqlite3.Row
    db.execute('PRAGMA mmap_size=1073741824');db.execute('PRAGMA cache_size=-65536')
    db.execute('ATTACH DATABASE ? AS captured',((OUT/'baseline.sqlite').as_uri()+'?mode=ro',));db.execute('CREATE TEMP VIEW base AS SELECT * FROM captured.base')
    gold=stage();meta={r['id']:dict(r) for r in db.execute('SELECT * FROM base')}
    # Metadata only in memory (~tens of MB); raw rows stream sequentially from disk.
    current={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in baseline['protected_file_hashes']}
    if current!=baseline['protected_file_hashes']:raise RuntimeError('Protected V1/source file changed')
    db.execute('CREATE TABLE proposal(id TEXT PRIMARY KEY,status TEXT,issues TEXT,reasons TEXT,cohort TEXT,multi_fp INTEGER,short_resolved INTEGER,new_multi INTEGER,proof TEXT)')
    transitions=collections.Counter();by_cohort=collections.defaultdict(collections.Counter);before_reasons=collections.Counter();after_reasons=collections.Counter();reasons=collections.Counter();count=0
    sample_pools=collections.defaultdict(list);protected_groups={r['grp'] for r in meta.values() if r['held']}
    def consider(label,record):
        pool=sample_pools[label];pool.append(record);pool.sort(key=lambda r:r['id']);del pool[5:]
    fields=['id','cohort','v1_status','v2_status','v1_issues','v2_issues','reason_codes','price_raw','area_raw','title','description','multi_evidence','price_evidence']
    with (OUT/'dry_run_audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=[k for k in fields if k not in {'description','multi_evidence','price_evidence'}],extrasaction='ignore');writer.writeheader()
        for rawrow in gold.execute('SELECT id,record FROM records'):
            stored=json.loads(rawrow['record']);raw=stored['raw_payload'];base=meta.get(rawrow['id'])
            if not base or sha(canonical(raw))!=base['ph']:raise RuntimeError('Raw source/baseline hash mismatch:'+rawrow['id'])
            old=json.loads(base['issues']);group=cohort(base['status'],old);v2=evaluate(raw,old,base['status'],bool(base['held']) or base['grp'] in protected_groups)
            record=dict(id=base['id'],cohort=group,v1_status=base['status'],v2_status=v2['quality_status'],v1_issues=canonical(old),v2_issues=canonical(v2['quality_issues']),reason_codes=canonical(v2['reason_codes']),price_raw=raw.get('price'),area_raw=raw.get('area'),title=raw.get('name'),description=raw.get('description'),multi_evidence=canonical(v2['multi_evidence']),price_evidence=canonical(v2['price_evidence']))
            writer.writerow(record)
            db.execute('INSERT INTO proposal VALUES(?,?,?,?,?,?,?,?,?)',(base['id'],v2['quality_status'],record['v2_issues'],record['reason_codes'],group,v2['multi_reason_false_positive'],v2['shorthand_reason_resolved'],v2['newly_detected_multi'],canonical(dict(multi=v2['multi_evidence'],price=v2['price_evidence']))))
            transitions[(base['status'],v2['quality_status'])]+=1;counter=by_cohort[group];counter['rows']+=1
            counter['proposed_pass']+=v2['quality_status']=='HYBRID_ELIGIBLE_RESEARCH';counter['remain_review']+=v2['quality_status']=='NEEDS_REVIEW';counter['multi_reason_false_positive']+=v2['multi_reason_false_positive'];counter['shorthand_reason_resolved']+=v2['shorthand_reason_resolved'];counter['new_multi']+=v2['newly_detected_multi']
            before_reasons.update(old);after_reasons.update(v2['quality_issues']);reasons.update(v2['reason_codes'])
            if group!='OTHER':
                outcome='PASS' if v2['quality_status']=='HYBRID_ELIGIBLE_RESEARCH' else 'REVIEW'
                consider(group+'_'+outcome,record)
                for code in v2['reason_codes']:consider(group+'_'+code,record)
                if v2['newly_detected_multi']:consider(group+'_NEW_MULTI',record)
            elif v2['newly_detected_multi']:consider('OTHER_NEW_MULTI',record)
            if base['status']=='HYBRID_ELIGIBLE_RESEARCH' and v2['quality_status']=='NEEDS_REVIEW':
                for flag in v2['quality_issues']:consider('OTHER_DEMOTED_'+flag,record)
            count+=1
            if count%25000==0:db.commit();print('DRY RUN evaluated',count,flush=True)
    if count!=185973:raise RuntimeError('Incomplete local dataset')
    db.commit()
    # Keep original suspicion groups, including existing protected membership.
    v1groups={r['grp'] for r in db.execute("SELECT DISTINCT grp FROM base WHERE status='HYBRID_ELIGIBLE_RESEARCH' AND held=0")}
    v2groups={r[0] for r in db.execute("SELECT DISTINCT b.grp FROM base b JOIN proposal p ON p.id=b.id WHERE p.status='HYBRID_ELIGIBLE_RESEARCH' AND b.held=0")}-protected_groups
    if len(v1groups)!=55816:raise RuntimeError('Original dedup representation differs')
    v1rep={r['grp']:r['id'] for r in meta.values() if r['rep']}
    v2rep={r[0]:r[1] for r in db.execute("SELECT b.grp,MIN(b.id) FROM base b JOIN proposal p ON p.id=b.id WHERE p.status='HYBRID_ELIGIBLE_RESEARCH' AND b.held=0 GROUP BY b.grp") if r[0] not in protected_groups}
    with (OUT/'representatives_proposed.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['duplicate_group','v1_representative','v2_representative','change'])
        for g in sorted(v1groups|v2groups):w.writerow([g,v1rep.get(g,''),v2rep.get(g,''),'ADDED_GROUP' if g not in v1groups else 'REMOVED_GROUP' if g not in v2groups else 'REPRESENTATIVE_CHANGED' if v1rep.get(g)!=v2rep.get(g) else 'UNCHANGED'])
    missed_by_status={r[0]:r[1] for r in db.execute('SELECT b.status,COUNT(*) FROM base b JOIN proposal p ON p.id=b.id WHERE p.new_multi=1 GROUP BY b.status')}
    if hashlib.sha256((ROOT/'backend/scripts/tinix_quality_v2.py').read_bytes()).hexdigest()!=rule_start_sha:raise RuntimeError('Rule source changed during evaluation; rerun offline before accepting')
    summary=dict(rule=RULE,rows=count,proposal_file=str(proposal_file.relative_to(ROOT)),baseline_metadata_sha256=baseline['metadata_sha256'],v2_code_sha256=rule_start_sha,
        transitions=[dict(v1=a,v2=b,rows=n) for (a,b),n in sorted(transitions.items())],cohorts={k:dict(v) for k,v in by_cohort.items()},v1_reasons=dict(before_reasons),v2_reasons=dict(after_reasons),reason_codes=dict(reasons),
        representatives=dict(v1=len(v1groups),v2=len(v2groups),added_groups=len(v2groups-v1groups),lost_groups=len(v1groups-v2groups),delta=len(v2groups)-len(v1groups),changed_representative=sum(v1rep.get(g)!=v2rep.get(g) for g in v1groups&v2groups)),new_multi_by_v1_status=missed_by_status,mysql_updates=0,importer_runs=0)
    save('summary.json',summary)
    samples={}
    for label,pool in sorted(sample_pools.items()):
        for r in pool:
            if r['id'] not in samples:samples[r['id']]={**r,'sample_strata':[]}
            samples[r['id']]['sample_strata'].append(label)
    save('samples.json',list(samples.values()));save('sample-strata.json',{k:[r['id'] for r in v] for k,v in sample_pools.items()})
    db.close();gold.close();print(json.dumps(summary,ensure_ascii=False),flush=True)
def verify():
    import pymysql
    baseline=load('baseline.json');conn=connect();h=hashlib.sha256();count=0
    try:
        after=facts(conn)
        with conn.cursor(pymysql.cursors.SSCursor) as c:
            select(c,META_SQL)
            while rows:=c.fetchmany(2000):
                for row in rows:h.update((canonical(row)+'\n').encode());count+=1
        if h.hexdigest()!=baseline['metadata_sha256'] or after!=baseline['facts'] or source_hashes()!=baseline['protected_file_hashes']:raise RuntimeError('Baseline/source changed; no update attempted')
        # Cross-check the diverse sample against actual MySQL original fields.
        samples=load('samples.json');verified=0
        with conn.cursor() as c:
            for offset in range(0,len(samples),100):
                chunk=samples[offset:offset+100];expected={r['id']:r for r in chunk}
                select(c,'SELECT internal_id,raw_payload,raw_numeric_ieee754,payload_sha256 FROM tinix_dataset_records WHERE internal_id IN ('+','.join(['%s']*len(chunk))+')',tuple(expected))
                for rid,payload,bits,ph in c.fetchall():
                    raw=restore_original(json.loads(payload),json.loads(bits));r=expected[rid]
                    if sha(canonical(raw))!=ph or (raw.get('name'),raw.get('description'),raw.get('price'),raw.get('area'))!=(r['title'],r['description'],r['price_raw'],r['area_raw']):raise RuntimeError('Live source sample mismatch:'+rid)
                    verified+=1
        if verified!=len(samples):raise RuntimeError('Missing live samples')
        save('read-only-verification.json',dict(read_only=True,metadata_unchanged=True,rows=count,samples_crosschecked_against_mysql=verified,crawler_checksums_unchanged=True,protected_files_unchanged=True,mysql_updates=0,importer_runs=0));print('READ ONLY VERIFY PASS;',verified,'live samples;',count,'metadata rows unchanged',flush=True)
    finally:conn.rollback();conn.close()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['capture','finalize-capture','evaluate','verify']);a=p.parse_args()
    try:{'capture':capture,'finalize-capture':finalize_capture,'evaluate':run,'verify':verify}[a.action]()
    except Exception as exc:print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
