"""Run Advisor against existing MySQL Local in read-only mode; no migration/import.

Reads only DB_USER/DB_PASSWORD/JWT_SECRET from .env into memory. Never prints them.
"""
import argparse,getpass,hashlib,json,os,re,secrets,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
URL='jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC'
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8080)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:raise RuntimeError('Port must be1024..65535')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='backend-huy-latest':raise RuntimeError('Use backend-huy-latest; no branch changes are performed')
    values={}
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match=re.match(r'^\s*(?:export\s+)?(DB_USER|DB_PASSWORD|JWT_SECRET)\s*=\s*(.*)$',line)
            if match:
                value=match[2].strip()
                if len(value)>1 and value[0]==value[-1] and value[0] in '\"\'':value=value[1:-1]
                values[match[1]]=value
    user=os.environ.get('DB_USER') or values.get('DB_USER')
    password=os.environ.get('DB_PASSWORD') or values.get('DB_PASSWORD')
    if not(user and password):
        if not sys.stdin.isatty():raise RuntimeError('Enter private local credentials in an interactive terminal')
        user=input('MySQL Local user [root]: ').strip() or 'root';password=getpass.getpass('MySQL Local password (hidden): ')
    if not password:raise RuntimeError('Private credentials required')
    env={k:v for k,v in os.environ.items() if not k.startswith(('APP_','SPRING_'))}
    env.update(DB_URL=URL,DB_USER=user,DB_PASSWORD=password,MYSQL_PWD=password,
        MYSQL_TEST_LOGIN_FILE=str(ROOT/'.scratch/disabled-advisor-login-file'),
        JWT_SECRET=values.get('JWT_SECRET') or secrets.token_urlsafe(48),APP_RECOMMENDATION_ALLOW_UNVERIFIED_EXTERNAL='false')
    sql="""START TRANSACTION READ ONLY;
SELECT JSON_OBJECT('port',@@port,'database',DATABASE());
SELECT JSON_OBJECT('version',version,'type',type,'checksum',checksum,'success',success) FROM flyway_schema_history ORDER BY installed_rank;
COMMIT;
"""
    mysql=[r'F:\MySQL\Server8.0\bin\mysql.exe','--no-defaults','--protocol=TCP','--host=127.0.0.1','--port=3306',
       '--database=smartprop','--user='+user,'--batch','--raw','--skip-column-names']
    result=subprocess.run(mysql,input=sql,env=env,capture_output=True,encoding='utf8',timeout=15)
    if result.returncode:raise RuntimeError('Read-only MySQL precheck failed; no migration or import performed')
    rows=[json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if rows!=[{'port':3306,'database':'smartprop'},{'version':'13','type':'BASELINE','checksum':None,'success':1},
         {'version':'14','type':'SQL','checksum':-1382804267,'success':1}]:raise RuntimeError('Unexpected local identity/history; stop for review')
    jar=ROOT/'.scratch/backend-huy-integration/build/smartprop-backend-0.1.0.jar'
    if not jar.exists():raise RuntimeError('Build the current backend into .scratch/backend-huy-integration/build first')
    sources=list((ROOT/'backend/src/main').rglob('*.java'))+list((ROOT/'backend/src/main/resources').glob('application*.yml'))
    if any(p.stat().st_mtime>jar.stat().st_mtime for p in sources):raise RuntimeError('Source newer than jar; rebuild first')
    runtime=ROOT/'.scratch/devtools/runtime.json'
    jdk=os.environ.get('JAVA_HOME') or (json.loads(runtime.read_text())['jdk'] if runtime.exists() else '')
    java=Path(jdk)/'bin/java.exe'
    if not java.exists():raise RuntimeError('Configure JAVA_HOME for JDK21')
    if args.check:
        print(json.dumps({'branch':branch,'target':'127.0.0.1:3306/smartprop','history':'BASELINE13/SQL14 verified','mode':'SAFE_READ_ONLY','jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest()}));return
    command=[str(java),'-jar',str(jar),'--server.address=127.0.0.1','--server.port='+str(args.port),'--app.server.transport=NIO2',
      '--spring.datasource.url='+URL,'--spring.datasource.hikari.read-only=true',
      '--spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY',
      '--spring.jpa.hibernate.ddl-auto=validate','--spring.flyway.enabled=false','--spring.sql.init.mode=never',
      '--spring.profiles.active=hybrid-local-existing-v13','--app.local-lineage.require-complete=false',
      '--app.seed.enabled=false','--app.database-seed.enabled=false',
      '--app.import.external-listings=','--app.recommendation.allow-unverified-external=false',
      '--app.google.enabled=false','--app.profile.avatar-enabled=false','--app.broker-applications.enabled=false',
      '--app.email.enabled=false','--app.email.worker-enabled=false','--debug=false']
    print('Advisor SAFE/read-only:127.0.0.1:'+str(args.port)+'; no migration,import or seed. Ctrl+C stops this owned process.',flush=True)
    process=subprocess.Popen(command,cwd=ROOT/'backend',env=env)
    try:code=process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:process.terminate()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        return
    finally:
        env.pop('DB_PASSWORD',None);env.pop('MYSQL_PWD',None)
    if code:raise RuntimeError('Backend stopped; inspect the error before retrying, do not migrate/repair')
if __name__=='__main__':
    try:main()
    except Exception as exc:print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
