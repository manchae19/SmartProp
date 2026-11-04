"""Run the current canonical Backend for read-only Recommendation acceptance.

No SQL updates, migrations, imports or process replacement. Existing listeners are
never stopped. This read-only service is not intended for login/upload workflows.
"""
import argparse,hashlib,json,os,re,shutil,socket,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
URL='jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC'

def artifact():
    jar=ROOT/'backend/target/smartprop-backend-0.1.0.jar'
    if not jar.exists():raise RuntimeError('Build current backend/target first with Maven Wrapper package')
    with zipfile.ZipFile(jar) as z:
        names=z.namelist()
        for entry in ['vn/smartprop/recommendation/RecommendationController.class','vn/smartprop/recommendation/HybridRecommendationService.class','application-hybrid-local-existing-v13.yml']:
            if 'BOOT-INF/classes/'+entry not in names:raise RuntimeError('Stale/wrong Backend artifact; rebuild backend/target')
        if b'/api/v1/recommendations' not in z.read('BOOT-INF/classes/vn/smartprop/auth/SecurityConfig.class'):raise RuntimeError('Recommendation security route missing from artifact')
    sources=[p for p in (ROOT/'backend/src/main').rglob('*') if p.is_file()]+[ROOT/'backend/pom.xml']
    if any(p.stat().st_mtime>jar.stat().st_mtime for p in sources):raise RuntimeError('Backend source newer than artifact; rebuild first')
    return jar

def check_port(port):
    if not 1024<=port<=65535:raise RuntimeError('Port must be1024..65535')
    with socket.socket() as s:
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):s.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        try:s.bind(('127.0.0.1',port))
        except OSError:raise RuntimeError('Port already used; choose another port, never stop an unknown process') from None

def private_environment():
    values={}
    if (ROOT/'.env').exists():
        for line in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines():
            m=re.match(r'^\s*(?:export\s+)?(DB_USER|DB_PASSWORD|JWT_SECRET)\s*=\s*(.*)$',line)
            if m:
                value=m[2].strip()
                if len(value)>1 and value[0]==value[-1] and value[0] in '\"\'':value=value[1:-1]
                values[m[1]]=value
    env={k:v for k,v in os.environ.items() if not k.startswith(('APP_','SPRING_','DB_','GOOGLE_','JWT_'))}
    for key in ['DB_USER','DB_PASSWORD','JWT_SECRET']:
        env[key]=os.environ.get(key) or values.get(key,'')
        if not env[key]:raise RuntimeError('Configure '+key+' privately in your terminal or existing.env; never send credentials in chat')
    if len(env['JWT_SECRET'].encode())<32:raise RuntimeError('JWT_SECRET must contain at least32 UTF-8 bytes')
    env['NO_PROXY']=env['no_proxy']='127.0.0.1,localhost,::1'
    return env

def command(java,jar,port):
    return [str(java),'-jar',str(jar),'--server.address=127.0.0.1','--server.port='+str(port),'--app.server.transport=NIO2',
      '--spring.profiles.active=hybrid-local-existing-v13','--app.local-lineage.require-complete=true',
      '--spring.datasource.url='+URL,'--spring.datasource.hikari.read-only=true',
      '--spring.datasource.hikari.connection-init-sql=SET SESSION TRANSACTION READ ONLY',
      '--spring.jpa.hibernate.ddl-auto=validate','--spring.flyway.enabled=false','--spring.sql.init.mode=never',
      '--app.recommendation.allow-unverified-external=false','--app.import.external-listings=',
      '--app.seed.enabled=false','--app.database-seed.enabled=false','--app.email.enabled=false','--app.email.worker-enabled=false',
      '--app.broker-applications.enabled=false','--app.profile.avatar-enabled=false','--app.google.enabled=false','--debug=false']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8080);p.add_argument('--check',action='store_true');args=p.parse_args()
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='backend-huy-latest':raise RuntimeError('Use backend-huy-latest')
    jar=artifact();check_port(args.port)
    rt=ROOT/'.scratch/devtools/runtime.json';jdk=os.environ.get('JAVA_HOME')
    if not jdk and rt.exists():jdk=json.loads(rt.read_text())['jdk']
    java=Path(jdk)/'bin/java.exe' if jdk else Path(shutil.which('java') or '')
    if not java.is_file():raise RuntimeError('Configure JAVA_HOME for JDK21')
    r=subprocess.run([str(java),'-version'],capture_output=True,text=True)
    if not re.search(r'version "21[.]',r.stdout+r.stderr):raise RuntimeError('Use JDK21 for this Backend')
    info={'branch':'backend-huy-latest','artifact':str(jar),'sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),'port':args.port,'mode':'SAFE_READ_ONLY','database':'127.0.0.1:3306/smartprop'}
    print(json.dumps(info),flush=True)
    if args.check:return
    env=private_environment();process=subprocess.Popen(command(java,jar,args.port),cwd=ROOT/'backend',env=env)
    try:code=process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:process.terminate()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        return
    finally:
        for key in ['DB_USER','DB_PASSWORD','JWT_SECRET']:env.pop(key,None)
    if code:raise RuntimeError('Owned Backend stopped; inspect startup error, do not migrate/repair automatically')

if __name__=='__main__':
    try:main()
    except Exception as exc:print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
