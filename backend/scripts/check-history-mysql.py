import argparse,json,os,re,signal,socket,subprocess,time,uuid
from pathlib import Path
from local_runtime import cleanup_all, kill_owned_tree, spring_environment, stop_owned
parser=argparse.ArgumentParser(description='Check valuation history only against a new isolated MySQL schema.')
parser.add_argument('--browser',action='store_true',help='Also run Vue browser tests against the real backend and v6 model.')
options=parser.parse_args()
root=Path(__file__).resolve().parents[2]
for checked_port in ([13317,18081,18082,15174] if options.browser else [13317,18081]):
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',checked_port))
        except OSError:raise SystemExit(f'Port {checked_port} is in use; leave its process running and stop this check.')
runtime_path=root/'.scratch/devtools/runtime.json'
runtime=json.loads(runtime_path.read_text(encoding='utf-8')) if runtime_path.exists() else {}
for key, variable in [('jdk','JAVA_HOME'),('maven','MAVEN_HOME'),('mysql','SMARTPROP_MYSQL_HOME')]:
    if os.environ.get(variable):runtime[key]=os.environ[variable]
    if not runtime.get(key):raise RuntimeError('Configure '+variable+' before checking the isolated backend.')
mysql=Path(runtime['mysql'])/'bin'
work=root/'.scratch'/('mysql-history-'+uuid.uuid4().hex[:12])
work.mkdir()
data=work/'data'
port=13317
with socket.socket() as probe:
    probe.bind(('127.0.0.1',port))
initial=subprocess.run([str(mysql/'mysqld.exe'),'--no-defaults','--initialize-insecure',f'--basedir={runtime["mysql"]}',f'--datadir={data}',f'--log-error={work / "initialize.log"}'],capture_output=True,text=True)
if initial.returncode:raise RuntimeError('MySQL initialization failed; see '+str(work))
server=subprocess.Popen([str(mysql/'mysqld.exe'),'--no-defaults',f'--basedir={runtime["mysql"]}',f'--datadir={data}','--bind-address=127.0.0.1',f'--port={port}','--mysqlx=0','--skip-log-bin',f'--log-error={work / "server.log"}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print(f'Isolated MySQL PID={server.pid}, port={port}, workspace={work.name}',flush=True)
args=[str(mysql/'mysql.exe'),'--no-defaults','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','--default-character-set=utf8mb4']
ai=None
def sql(value,database=None):
    result=subprocess.run(args+([database] if database else []),input=value,text=True,encoding='utf-8',capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr)
try:
    deadline=time.monotonic()+30
    while True:
        ready=subprocess.run(args+['--execute=SELECT 1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if ready.returncode==0:break
        if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('MySQL not ready; see '+str(work))
        time.sleep(.5)
    schema='smartprop_history_'+uuid.uuid4().hex[:12]
    sql(f'CREATE DATABASE {schema} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;')
    migrations=sorted((root/'database/migrations').glob('V*__*.sql'),key=lambda p:int(p.name.split('__')[0][1:]))
    for path in migrations:sql(path.read_text(encoding='utf-8-sig'),schema)
    print(f'All {len(migrations)} migrations applied only to the temporary schema.',flush=True)
    ai_port=18081
    with socket.socket() as probe:probe.bind(('127.0.0.1',ai_port))
    ai_log=(work/'ai.log').open('w',encoding='utf-8')
    ai=subprocess.Popen([str(root/'ai-services/.venv/Scripts/python.exe'),'-X','utf8',str(root/'ai-services/run_api.py'),'--port',str(ai_port)],stdout=ai_log,stderr=subprocess.STDOUT)
    import urllib.request
    for attempt in range(60):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{ai_port}/health',timeout=1) as response:
                if response.status==200:break
        except OSError:time.sleep(.25)
    else:raise RuntimeError('Isolated AI did not become ready')
    db_url=f'jdbc:mysql://127.0.0.1:{port}/{schema}?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false'
    env=spring_environment(os.environ,url=db_url,user='root',password='',jwt=uuid.uuid4().hex+uuid.uuid4().hex)
    env['JAVA_HOME']=runtime['jdk'];env['SMARTPROP_HISTORY_TEST_URL']=db_url;env['SMARTPROP_HISTORY_AI_URL']=f'http://127.0.0.1:{ai_port}'
    maven=Path(runtime['maven']);launcher=next((maven/'boot').glob('plexus-classworlds-*.jar'))
    command=[str(Path(runtime['jdk'])/'bin/java.exe'),f'-Dmaven.home={maven}',f'-Dclassworlds.conf={maven}/bin/m2.conf',f'-Dmaven.multiModuleProjectDirectory={root}/backend',f'-Dmaven.repo.local={root}/.scratch/m2','-classpath',str(launcher),'org.codehaus.plexus.classworlds.launcher.Launcher','-B','-ntp','-f',str(root/'backend/pom.xml'),f'-Dsmartprop.build.directory={work}/target','-DforkCount=0','package' if options.browser else 'test']
    with (work/'maven.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    print((work/'maven.log').read_text(encoding='utf-8')[-5000:],flush=True)
    if result.returncode:raise RuntimeError('BE tests failed; see '+str(work/'maven.log'))
    browser=None
    if options.browser:
        from browser_history_check import run_browser_check
        browser=run_browser_check(root,runtime,env,work,ai_port)
    (root/'.scratch/history-mysql-verification.json').write_text(json.dumps({'passed':True,'mysql':'8.4.13','migrations':len(migrations),'schema':schema,'port':port,'log':str(work/'maven.log'),'test_server_pid':server.pid,'browser':browser}),encoding='utf-8')
finally:
    def terminate_ai():
        ai_pid=re.search(r'\[PID (\d+)\]',(work/'ai.log').read_text(encoding='utf-8'))
        if ai_pid:os.kill(int(ai_pid[1]),signal.SIGTERM)
        else:kill_owned_tree(ai)
    def shutdown_mysql():
        subprocess.run([str(mysql/'mysqladmin.exe'),'--no-defaults','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','shutdown'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    cleanup_all(lambda:stop_owned(ai,graceful=terminate_ai,force=lambda:kill_owned_tree(ai),timeout=5),
                lambda:ai_log.close() if ai is not None else None,
                lambda:stop_owned(server,graceful=shutdown_mysql,timeout=15))
    print('Only the isolated MySQL process has stopped; source databases were not used.',flush=True)
