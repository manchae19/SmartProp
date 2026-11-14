"""Opt-in Local research server and private Vue proxy. No migrations/imports.

Default datasource is READ ONLY: login/refresh are not supported on this instance.
--allow-login explicitly permits ordinary user-initiated authentication writes;
it never logs in automatically, creates accounts or modifies existing sessions.
The ephemeral demo key is shared server-to-server in process environments only.
"""
import argparse,importlib.util,json,os,secrets,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load():
    s=importlib.util.spec_from_file_location('tinix_runtime',ROOT/'backend/scripts/run-recommendation-local.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8080);p.add_argument('--frontend-port',type=int,default=5173);p.add_argument('--check',action='store_true');p.add_argument('--allow-login',action='store_true');a=p.parse_args()
    m=load();jar=m.artifact();m.check_port(a.port);m.check_port(a.frontend_port)
    java=Path(os.environ['JAVA_HOME'])/'bin/java.exe' if os.environ.get('JAVA_HOME') else Path(shutil.which('java') or '')
    if not java.is_file():java=Path(json.loads((ROOT/'.scratch/devtools/runtime.json').read_text())['jdk'])/'bin/java.exe'
    version=subprocess.run([str(java),'-version'],capture_output=True,text=True)
    if not __import__('re').search(r'version "21[.]',version.stdout+version.stderr):raise RuntimeError('Use JDK21 in JAVA_HOME')
    if a.check:print(json.dumps(dict(database='127.0.0.1:3306/smartprop',port=a.port,profile='hybrid-local-existing-v13',tinix=True,safe_crawler_flag=False,read_only=not a.allow_login,key_in_bundle=False)));return
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='backend-huy-latest':raise RuntimeError('Wrong branch')
    env=m.private_environment();key=secrets.token_urlsafe(48)
    env.update(APP_RECOMMENDATION_TINIX_ENABLED='true',APP_RECOMMENDATION_DEMO_KEY=key,SMARTPROP_INTERNAL_DEMO_KEY=key,SMARTPROP_DEV_API_TARGET='http://127.0.0.1:'+str(a.port))
    command=m.command(java,jar,a.port)+['--app.recommendation.tinix-enabled=true']
    if a.allow_login:
        origin=f'http://127.0.0.1:{a.frontend_port},http://localhost:{a.frontend_port}'
        command=[x for x in command if not x.startswith(('--spring.datasource.hikari.read-only=','--spring.datasource.hikari.connection-init-sql='))]+[
            '--app.refresh.enabled=true','--app.refresh.secure-cookie=false','--app.cors-origins='+origin]
        env['VITE_ENABLE_REFRESH']='true'
        print('Operator enabled normal login: signing in may create/update auth sessions. No automatic login or account changes.',flush=True)
    processes=[]
    try:
        processes.append(subprocess.Popen(command,cwd=ROOT/'backend',env=env))
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(120):
            if processes[0].poll() is not None:raise RuntimeError('Owned backend failed; no auto-migration')
            try:
                with opener.open(f'http://127.0.0.1:{a.port}/actuator/health',timeout=2) as r:
                    if r.status==200:break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Backend startup timeout')
        node=shutil.which('node')
        if not node:raise RuntimeError('Node is required')
        processes.append(subprocess.Popen([node,'node_modules/vite/bin/vite.js','--port',str(a.frontend_port)],cwd=ROOT/'frontend/vue.ui',env=env))
        print(f'TiniX Local: http://127.0.0.1:{a.frontend_port}/advisor; ADMIN session required; public SAFE remains unchanged. Ctrl+C stops only these owned processes.',flush=True)
        while all(p.poll() is None for p in processes):time.sleep(1)
    except KeyboardInterrupt:pass
    finally:
        for p in reversed(processes):
            if p.poll() is None:p.terminate()
        for p in processes:
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for name in ['DB_PASSWORD','JWT_SECRET','APP_RECOMMENDATION_DEMO_KEY','SMARTPROP_INTERNAL_DEMO_KEY']:env.pop(name,None)
if __name__=='__main__':
    try:main()
    except Exception as e:print('STOP: '+str(e),file=sys.stderr);sys.exit(1)
