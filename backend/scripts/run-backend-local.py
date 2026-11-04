"""Launch full Backend only after the separately approved Local V17/V18 rollout.

No migrations, import, seed or credential-file edits. --check performs only reads.
"""
import argparse,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('forward',Path(__file__).with_name('flyway-local-forward.py'))
forward=importlib.util.module_from_spec(spec);spec.loader.exec_module(forward)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--port',type=int,default=8080);args=p.parse_args()
    if not 1024<=args.port<=65535:raise RuntimeError('Port must be1024..65535')
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='backend-huy-latest':raise RuntimeError('Use backend-huy-latest')
    forward.OUT.mkdir(parents=True,exist_ok=True)
    _,wanted=forward.migration_inventory();client=forward.Local()
    try:
        before=client.snapshot()
        if len(before['ddl'])!=48 or not forward.NEW_TABLES<=set(before['ddl']):raise RuntimeError('Local V17/V18 not complete. Review/approve the migration plan first; no changes performed.')
        if [(h['version'],h['type'],h['success']) for h in before['history']]!=[('13','BASELINE',1),('14','SQL',1),('17','SQL',1),('18','SQL',1)] or before['history'][1]['checksum']!=-1382804267:raise RuntimeError('Unexpected Local history; no repair performed')
        actual={n:forward.schema.table_contract(forward.schema.schema(before['ddl'][n].rstrip(';')+';')[n]) for n in wanted}
        if forward.schema.compare(wanted,actual)[0]:raise RuntimeError('Completion schema drift; stop')
        client.flyway('validate')
        if client.snapshot()!=before:raise RuntimeError('Database changed during prechecks')
        if args.check:print('PASS: Local48 tables, BASELINE13/crawler14/V17/V18, strict Flyway Validate. No writes.');return
        jar=ROOT/'.scratch/backend-huy-integration/build/smartprop-backend-0.1.0.jar'
        if not jar.exists() or any(f.stat().st_mtime>jar.stat().st_mtime for f in (ROOT/'backend/src/main').rglob('*') if f.is_file()):raise RuntimeError('Build the current Backend into .scratch/backend-huy-integration/build first')
        env={k:v for k,v in client.env.items() if not k.startswith(('SPRING_','APP_'))};env.pop('MYSQL_PWD',None)
        # Only relevant application credentials/settings; never print or rewrite .env.
        allowed={'JWT_SECRET','GOOGLE_LOGIN_ENABLED','GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REDIRECT_URI','GOOGLE_FRONTEND_ORIGIN','REFRESH_ENABLED','REFRESH_SECURE_COOKIE','CORS_ORIGINS','STORAGE_ROOT','ACCESS_TOKEN_MINUTES'}
        envfile=ROOT/'.env'
        if envfile.exists():
            for line in envfile.read_text(encoding='utf-8-sig').splitlines():
                m=re.match(r'^\s*(?:export\s+)?([A-Z_]\w*)\s*=\s*(.*)$',line)
                if m and m[1] in allowed and m[1] not in env:
                    value=m[2].strip()
                    if len(value)>1 and value[0]==value[-1] and value[0] in '\"\'':value=value[1:-1]
                    env[m[1]]=value
        if not env.get('JWT_SECRET'):raise RuntimeError('Configure private JWT_SECRET locally; never send it in chat')
        jdk=env.get('JAVA_HOME') or json.loads((ROOT/'.scratch/devtools/runtime.json').read_text())['jdk']
        java=Path(jdk)/'bin/java.exe'
        command=[str(java),'-jar',str(jar),'--spring.profiles.active='+forward.PROFILE,
          '--server.address=127.0.0.1','--server.port='+str(args.port),'--app.server.transport=NIO2',
          '--spring.datasource.url='+forward.URL,'--spring.flyway.enabled=false','--spring.jpa.hibernate.ddl-auto=validate',
          '--spring.sql.init.mode=never','--app.seed.enabled=false','--app.database-seed.enabled=false',
          '--app.import.external-listings=','--app.email.worker-enabled=false','--app.recommendation.allow-unverified-external=false',
          '--app.google.enabled=false']
        print('Full Backend:127.0.0.1:'+str(args.port)+'; explicit Local profile, Broker/Avatar enabled, Google disabled. No startup migration/import/seed.',flush=True)
        process=subprocess.Popen(command,cwd=ROOT/'backend',env=env)
        try:code=process.wait()
        except KeyboardInterrupt:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            return
        if code:raise RuntimeError('Backend stopped; inspect the error, do not migrate/repair automatically')
    finally:client.close()

if __name__=='__main__':
    try:main()
    except Exception as exc:print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
