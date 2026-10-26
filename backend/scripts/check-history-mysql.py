import json,os,re,signal,socket,subprocess,time,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[2]
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
    env=os.environ.copy();env['JAVA_HOME']=runtime['jdk'];env['SMARTPROP_HISTORY_TEST_URL']=f'jdbc:mysql://127.0.0.1:{port}/{schema}?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false';env['SMARTPROP_HISTORY_AI_URL']=f'http://127.0.0.1:{ai_port}'
    maven=Path(runtime['maven']);launcher=next((maven/'boot').glob('plexus-classworlds-*.jar'))
    command=[str(Path(runtime['jdk'])/'bin/java.exe'),f'-Dmaven.home={maven}',f'-Dclassworlds.conf={maven}/bin/m2.conf',f'-Dmaven.multiModuleProjectDirectory={root}/backend',f'-Dmaven.repo.local={root}/.scratch/m2','-classpath',str(launcher),'org.codehaus.plexus.classworlds.launcher.Launcher','-B','-ntp','-f',str(root/'backend/pom.xml'),'-DforkCount=0','test']
    with (work/'maven.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    print((work/'maven.log').read_text(encoding='utf-8')[-5000:],flush=True)
    if result.returncode:raise RuntimeError('BE tests failed; see '+str(work/'maven.log'))
    (root/'.scratch/history-mysql-verification.json').write_text(json.dumps({'passed':True,'mysql':'8.4.13','migrations':len(migrations),'schema':schema,'port':port,'log':str(work/'maven.log'),'test_server_pid':server.pid}),encoding='utf-8')
finally:
    if ai is not None:
        ai_pid=re.search(r'\[PID (\d+)\]',(work/'ai.log').read_text(encoding='utf-8'))
        if ai.poll() is None and ai_pid:os.kill(int(ai_pid[1]),signal.SIGTERM)
        ai.wait(timeout=5);ai_log.close()
    subprocess.run([str(mysql/'mysqladmin.exe'),'--no-defaults','--protocol=TCP','--host=127.0.0.1',f'--port={port}','--user=root','shutdown'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:server.wait(timeout=15)
    except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=5)
    print('Only the isolated MySQL process has stopped; source databases were not used.',flush=True)
