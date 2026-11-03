"""Prepare/validate Local-only V17/V18. Apply requires a separately approved plan hash.

Default and --prepare perform only database reads. Backups/reports are local files.
Never baseline, repair, clean, import or execute standard migrations on this database.
"""
import argparse,datetime,getpass,hashlib,json,os,re,subprocess,sys
from pathlib import Path
import mysql_schema_contract as schema

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.scratch/flyway-local-forward'
URL='jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC'
PROFILE='hybrid-local-existing-v13'
SERVER_UUID='60f0e116-d443-11f1-bdbf-7085c2fe30d2'
CANONICAL='d56139b83c23c71581d0e6f099861270155b050d6d4585e37189a38983c3d01d'
NEW_TABLES={'broker_applications','user_avatars','user_external_identities'}
LOCAL=ROOT/'database/legacy-hybrid-local'
EXPECTED_LOCAL={'V14__crawler_external_listings.sql','V17__local_broker_applications.sql','V18__local_avatar_and_google_identity.sql'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def credentials():
    values={}
    file=ROOT/'.env'
    if file.exists():
        for line in file.read_text(encoding='utf-8-sig').splitlines():
            m=re.match(r'^\s*(?:export\s+)?(DB_USER|DB_PASSWORD)\s*=\s*(.*)$',line)
            if m:
                v=m[2].strip()
                if len(v)>1 and v[0]==v[-1] and v[0] in '\"\'':v=v[1:-1]
                values[m[1]]=v
    user=os.environ.get('DB_USER') or values.get('DB_USER')
    password=os.environ.get('DB_PASSWORD') or values.get('DB_PASSWORD')
    if not(user and password):
        if not sys.stdin.isatty():raise RuntimeError('Enter private credentials in your local interactive terminal; never send them in chat.')
        user=input('MySQL Local user [root]: ').strip() or 'root';password=getpass.getpass('MySQL Local password (hidden): ')
    if not password:raise RuntimeError('Private password required')
    return user,password

def migration_inventory():
    result={}
    for folder in [ROOT/'database/migrations',LOCAL]:
        versions=[]
        for p in sorted(folder.glob('V*.sql')):
            m=re.fullmatch(r'V(\d+)__[A-Za-z0-9_]+\.sql',p.name)
            if not m:raise RuntimeError('Unexpected migration filename')
            versions.append(int(m[1]));result[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
        if len(versions)!=len(set(versions)):raise RuntimeError('Duplicate migration version in location')
    if {p.name for p in LOCAL.glob('V*.sql')}!=EXPECTED_LOCAL:raise RuntimeError('Unexpected Local migration inventory')
    if sha(LOCAL/'V14__crawler_external_listings.sql')!=CANONICAL:raise RuntimeError('Original crawler14 file changed')
    # Only these CREATE TABLE statements may be pending; no changes to existing tables.
    wanted={}
    for p in sorted(LOCAL.glob('V1[78]__*.sql')):
        sql=p.read_text(encoding='utf8');clean=re.sub(r'^\s*--[^\n]*','',sql,flags=re.M)
        tables=schema.schema(sql)
        rest=re.sub(r'CREATE TABLE\s+\w+\s*\(.*?\)\s*ENGINE\s*=\s*[^;]+;','',clean,flags=re.I|re.S).strip()
        if rest or any(name in wanted for name in tables):raise RuntimeError('Pending SQL is not exclusively additive table creation')
        wanted.update({n:schema.table_contract(t) for n,t in tables.items()})
    if set(wanted)!=NEW_TABLES:raise RuntimeError('Unexpected pending table scope')
    return result,wanted

def execution_inventory():
    paths=['backend/pom.xml','backend/mvnw.cmd','backend/scripts/flyway-local-forward.py','backend/scripts/mysql_schema_contract.py']
    return {p:sha(ROOT/p) for p in paths}

class Local:
    def __init__(self):
        self.user,self.password=credentials();self.env=os.environ.copy()
        for name in ['MAVEN_ARGS','MAVEN_OPTS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','MVNW_VERBOSE']:
            if self.env.get(name):raise RuntimeError('Unexpected runtime override:'+name)
        if any(k.startswith('FLYWAY_') for k in self.env):raise RuntimeError('Unexpected Flyway environment override')
        self.env.update(DB_USER=self.user,DB_PASSWORD=self.password,DB_URL=URL,MYSQL_PWD=self.password,
            MYSQL_TEST_LOGIN_FILE=str(OUT/'disabled-login-file'))
        rt=ROOT/'.scratch/devtools/runtime.json'
        if rt.exists():self.env.setdefault('JAVA_HOME',json.loads(rt.read_text())['jdk'])
        self.env.setdefault('MAVEN_USER_HOME',str(ROOT/'.scratch/backend-huy-integration/maven-home'))
        self.mysql=Path('F:/MySQL/Server8.0/bin/mysql.exe')
        self.dump=self.mysql.with_name('mysqldump.exe')
    def redact(self,s):return s.replace(self.password,'[REDACTED]')
    def command(self,args,sql=None,timeout=180):
        r=subprocess.run(args,cwd=ROOT/'backend',env=self.env,input=sql,capture_output=True,encoding='utf8',errors='replace',timeout=timeout)
        if r.returncode:raise RuntimeError(self.redact(r.stderr or r.stdout or 'Command failed'))
        return r.stdout
    def query(self,sql):
        if not re.match(r'^\s*(SELECT|SHOW|CHECKSUM)\b',sql,re.I) or ';' in sql:raise ValueError('Single read-only query only')
        return self.command([str(self.mysql),'--no-defaults','--protocol=TCP','--host=127.0.0.1','--port=3306',
            '--database=smartprop','--user='+self.user,'--connect-timeout=5','--default-character-set=utf8mb4',
            '--batch','--raw','--skip-column-names'],sql='START TRANSACTION READ ONLY;\n'+sql+';\nCOMMIT;\n')
    def objects(self,sql):return [json.loads(line) for line in self.query(sql).splitlines() if line.strip()]
    def snapshot(self):
        identity=self.objects("SELECT JSON_OBJECT('database',DATABASE(),'port',@@port,'server_uuid',@@server_uuid,'version',VERSION())")[0]
        if identity!={'database':'smartprop','port':3306,'server_uuid':SERVER_UUID,'version':'8.0.46'}:raise RuntimeError('Wrong server/database identity; no writes')
        names=self.query("SELECT table_name FROM information_schema.tables WHERE table_schema='smartprop' AND table_type='BASE TABLE' ORDER BY table_name").splitlines()
        if not names or any(not re.fullmatch(r'[A-Za-z0-9_]+',n) for n in names):raise RuntimeError('Unexpected table inventory')
        ddl={n:self.query('SHOW CREATE TABLE smartprop.`'+n+'`').split('\t',1)[1].strip() for n in names}
        counts={n:int(self.query('SELECT COUNT(*) FROM smartprop.`'+n+'`')) for n in names}
        checksums={line.split('\t')[0].split('.',1)[1]:line.split('\t')[1] for line in self.query('CHECKSUM TABLE '+','.join('smartprop.`'+n+'`' for n in names)+' EXTENDED').splitlines()}
        if any(v=='NULL' for v in checksums.values()):raise RuntimeError('A table checksum unavailable')
        history=self.objects("SELECT JSON_OBJECT('version',version,'type',type,'checksum',checksum,'success',success,'script',script) FROM flyway_schema_history ORDER BY installed_rank")
        triggers=self.objects("SELECT JSON_OBJECT('name',trigger_name,'timing',action_timing,'event',event_manipulation,'table',event_object_table,'body',action_statement) FROM information_schema.triggers WHERE trigger_schema='smartprop' ORDER BY trigger_name")
        return dict(identity=identity,ddl=ddl,rowcounts=counts,checksums=checksums,history=history,triggers=triggers)
    def flyway(self,goal,standard=False,allow_pending=False):
        if goal not in {'validate','info','migrate'}:raise ValueError('Forbidden Flyway goal')
        if standard and goal=='migrate':raise ValueError('Standard migration cannot target this Local database')
        if allow_pending and (standard or goal!='validate'):raise ValueError('Pending allowance is only for Local pre-migration validation')
        name='standard-on-local' if standard else 'local'
        args=[str(ROOT/'backend/mvnw.cmd'),'--batch-mode','--no-transfer-progress',
          '-Dmaven.repo.local='+str(ROOT/'.scratch/m2'),'-P'+('standard-migrations' if standard else PROFILE),
          '-Dflyway.locations=filesystem:'+str(ROOT/'database'/('migrations' if standard else 'legacy-hybrid-local')),
          '-Dflyway.url='+URL,'-Dflyway.schemas=smartprop','-Dflyway.defaultSchema=smartprop',
          '-Dflyway.createSchemas=false','-Dflyway.baselineOnMigrate=false','-Dflyway.cleanDisabled=true',
          '-Dflyway.outOfOrder=false','-Dflyway.validateMigrationNaming=true','-Dflyway.validateOnMigrate=true',
          '-Dflyway.target='+('16' if standard else '18'),'org.flywaydb:flyway-maven-plugin:11.7.2:'+goal]
        if allow_pending:args.insert(-1,'-Dflyway.ignoreMigrationPatterns=*:pending')
        else:args.insert(-1,'-Dflyway.ignoreMigrationPatterns=')
        try:output=self.command(args,timeout=300)
        except RuntimeError as exc:
            (OUT/(name+'-'+goal+'.log')).write_text(str(exc),encoding='utf8');raise
        (OUT/(name+'-'+goal+'.log')).write_text(self.redact(output),encoding='utf8')
    def backup(self,before):
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        file=OUT/('smartprop-before-local-completion-'+stamp+'.sql')
        args=[str(self.dump),'--no-defaults','--protocol=TCP','--host=127.0.0.1','--port=3306','--user='+self.user,
          '--single-transaction','--skip-lock-tables','--routines','--triggers','--events','--hex-blob','--no-tablespaces',
          '--set-gtid-purged=OFF','--default-character-set=utf8mb4','smartprop']
        with file.open('xb') as f:r=subprocess.run(args,env=self.env,stdout=f,stderr=subprocess.PIPE,timeout=120)
        if r.returncode:raise RuntimeError('Backup failed: '+self.redact(r.stderr.decode('utf8',errors='replace')))
        content=file.read_text(encoding='utf-8-sig')
        tables=set(schema.schema(content))
        if file.stat().st_size<1000 or '-- Dump completed on ' not in content[-1000:] or tables!=set(before['ddl']) or re.search(r'(?im)^(?:mysqldump:.*(?:error|failed)|ERROR \d+|Got error:)',content):raise RuntimeError('Backup completeness check failed')
        if self.snapshot()!=before:raise RuntimeError('Database changed during backup; stop for review')
        return {'path':str(file),'bytes':file.stat().st_size,'sha256':sha(file),'table_count':len(tables),'dump_completed':True,'restore_tested':False}
    def close(self):
        self.env.pop('DB_PASSWORD',None);self.env.pop('MYSQL_PWD',None);self.password=''

def audit_before(before,wanted):
    if len(before['ddl'])!=45 or set(before['ddl'])&NEW_TABLES:raise RuntimeError('Unexpected tables or partial rollout; do not retry/repair automatically')
    h=before['history']
    if [(x['version'],x['type'],x['checksum'],x['success']) for x in h]!=[('13','BASELINE',None,1),('14','SQL',-1382804267,1)]:raise RuntimeError('Unexpected Flyway history; stop without baseline/repair')
    actual={n:schema.table_contract(schema.schema(s.rstrip(';')+';')[n]) for n,s in before['ddl'].items()}
    current=schema.schema((ROOT/'database/migrations/V14__valuation_history.sql').read_text(encoding='utf8'))
    current.update(schema.schema((LOCAL/'V14__crawler_external_listings.sql').read_text(encoding='utf8')))
    differences=schema.compare({n:schema.table_contract(t) for n,t in current.items()},{n:actual[n] for n in current})[0]
    if differences:raise RuntimeError('Valuation/external schema drift: '+json.dumps(differences))
    for name,table in wanted.items():
        for fk in table['foreign_keys'].values():
            parent=actual.get(fk['parent'])
            if not parent or any(table['columns'][c]['type']!=parent['columns'][p]['type'] for c,p in zip(fk['columns'],fk['parent_columns'])):raise RuntimeError('Unresolved FK dependency for '+name)
    if before['rowcounts']['external_listings']!=3204 or before['rowcounts']['external_duplicate_groups']!=332:raise RuntimeError('Unexpected crawler inventory')
    return {'valuation_history':'FULL_CONTRACT_MATCH','external_tables':'FULL_CONTRACT_MATCH','users_fk_dependencies':'MATCH','new_tables':sorted(wanted)}

def check_after(before,after,wanted):
    if set(after['ddl'])!=set(before['ddl'])|NEW_TABLES:raise RuntimeError('Unexpected post-migration table inventory')
    for n in before['ddl']:
        if n=='flyway_schema_history':continue
        if any(before[k][n]!=after[k][n] for k in ['ddl','rowcounts','checksums']):raise RuntimeError('Existing table changed:'+n)
    if before['triggers']!=after['triggers']:raise RuntimeError('Existing triggers changed')
    if after['history'][:2]!=before['history'] or [(h['version'],h['type'],h['success']) for h in after['history'][2:]]!=[('17','SQL',1),('18','SQL',1)]:raise RuntimeError('Unexpected appended history')
    actual={n:schema.table_contract(schema.schema(after['ddl'][n].rstrip(';')+';')[n]) for n in wanted}
    diffs=schema.compare(wanted,actual)[0]
    if diffs or any(after['rowcounts'][n] for n in wanted):raise RuntimeError('New table contract/data differs:'+json.dumps(diffs))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',action='store_true',help='Read-only schema checks, validate and fresh backup; save review plan')
    p.add_argument('--apply',action='store_true',help='ONLY after explicit user approval of the displayed plan')
    p.add_argument('--reviewed-plan-sha256')
    args=p.parse_args()
    if args.apply and args.prepare:raise RuntimeError('Choose prepare OR apply')
    if args.apply and not re.fullmatch(r'[a-f0-9]{64}',args.reviewed_plan_sha256 or ''):raise RuntimeError('Apply requires the exact separately reviewed plan SHA256')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='backend-huy-latest':raise RuntimeError('Wrong branch; do not checkout automatically')
    OUT.mkdir(parents=True,exist_ok=True)
    inventory,wanted=migration_inventory();client=Local()
    try:
        before=client.snapshot();audit=audit_before(before,wanted)
        if args.apply:
            plan_file=OUT/'plan.json'
            if sha(plan_file)!=args.reviewed_plan_sha256:raise RuntimeError('Reviewed plan changed')
            plan=json.loads(plan_file.read_text(encoding='utf8'))
            if plan['migration_sha256']!=inventory or plan['execution_sha256']!=execution_inventory() or plan['before']!=before:raise RuntimeError('Schema/data/migrations/execution files changed since review; stop and re-review')
            old=plan['backup'];backup_file=Path(old['path'])
            if not backup_file.exists() or sha(backup_file)!=old['sha256']:raise RuntimeError('Reviewed backup missing/changed')
            client.flyway('validate',allow_pending=True)
            fresh=client.backup(before)
            # A second immediate precondition check prevents a stale snapshot.
            if client.snapshot()!=before:raise RuntimeError('Database changed before migrate')
            receipt={'status':'STARTING_APPROVED_MIGRATION','target':'127.0.0.1:3306/smartprop','reviewed_plan_sha256':args.reviewed_plan_sha256,'backup':fresh}
            receipt_file=OUT/'execution-receipt.json'
            receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf8')
            try:
                client.flyway('migrate');client.flyway('validate');after=client.snapshot();check_after(before,after,wanted)
                receipt.update(status='PASS',table_count=len(after['ddl']),history=after['history'],created_tables=sorted(NEW_TABLES),existing_tables_unchanged=True)
            except Exception:
                receipt['status']='FAILED_STOP_NO_RETRY_OR_REPAIR';raise
            finally:receipt_file.write_text(json.dumps(receipt,indent=2),encoding='utf8')
            print('PASS: appended V17/V18; created only three approved tables; existing44 data tables unchanged.');return
        client.flyway('validate',allow_pending=True)
        standard='EXPECTED_REJECTION_ON_LEGACY_LOCAL'
        try:client.flyway('validate',standard=True)
        except RuntimeError:
            log=(OUT/'standard-on-local-validate.log').read_text(encoding='utf8')
            if not all(s in log for s in ['-1382804267','679419338']):raise RuntimeError('Standard validation failed for an unexplained reason')
        else:raise RuntimeError('Standard profile unexpectedly accepted crawler14 history')
        result={'target':'127.0.0.1:3306/smartprop','audit':audit,'local_validate_applied_history':'PASS','pending_local_versions':['17','18'],'pending_acknowledged_only_for_prevalidation':True,'standard_on_legacy_local':standard,'database_writes':0}
        if args.prepare:
            backup=client.backup(before)
            plan={'target':'127.0.0.1:3306/smartprop','before':before,'migration_sha256':inventory,'execution_sha256':execution_inventory(),'backup':backup,'audit':audit,
                'expected_new_tables':sorted(NEW_TABLES),'flyway_target':'18','writes':['CREATE TABLE broker_applications','CREATE TABLE user_avatars','CREATE TABLE user_external_identities','Flyway INSERT history for V17/V18 only'],
                'approval_required':True,'prepared_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            file=OUT/'plan.json';file.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            result.update(plan_sha256=sha(file),backup={k:v for k,v in backup.items() if k!='path'},apply_executed=False)
        if client.snapshot()!=before:raise RuntimeError('Read-only preparation snapshot changed')
        (OUT/'preparation-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(result,ensure_ascii=False))
    finally:client.close()

if __name__=='__main__':
    try:main()
    except Exception as exc:print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
