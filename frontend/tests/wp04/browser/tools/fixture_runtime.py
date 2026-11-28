"""Start the disposable WP04 test stack on Windows. This launcher owns its entire runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[4]
EVIDENCE = ROOT / '.smartprop/wp04-fixture'
HOST = '127.0.0.1'
PORT = {'mysql':54041, 'spring':54042, 'valuation':54043, 'react':54044}
SCHEMA = 'wp04_final_fixture'
APPROVED_BASE = '0e9053f0c4085351a7d429f81995f6895ad80e33'
BASE = {key:f'http://{HOST}:{port}' for key,port in PORT.items() if key!='mysql'}
UNUSED_PROXY_PORTS = (54045, 54046)
demos = {'broker':'broker-wp04@example.invalid','buyer':'buyer-wp04@example.invalid','admin':'admin-wp04@example.invalid'}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def http(url, body=None):
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode('utf-8'),
        headers={'Content-Type':'application/json','Accept':'application/json, text/html'})
    with opener.open(request, timeout=3) as response:
        return response.status,response.read()

def wait_http(url, process, seconds):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        if process.poll() is not None:
            raise RuntimeError('Process exited before readiness: '+url)
        try:
            return http(url)
        except (OSError,urllib.error.URLError):
            time.sleep(.5)
    raise RuntimeError('Readiness deadline: '+url)

def available(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        sock.bind((HOST,port))

def loopback_owner(port):
    socket_name=f'{HOST}:{port}'
    with socket.socket() as client:
        if client.connect_ex((HOST,port)):
            return ''
    table=subprocess.check_output(['netstat.exe','-ano','-p','TCP'],text=True,timeout=12)
    for row in table.splitlines():
        fields=row.split()
        if len(fields)==5 and fields[1]==socket_name and fields[3]=='LISTENING':
            return fields[-1]
    return ''

def clean_env(values):
    keep=('PATH','PATHEXT','SYSTEMROOT','WINDIR','COMSPEC','TMP','TEMP','USERPROFILE','HOME',
          'USERDOMAIN','USERNAME','APPDATA','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)',
          'PROGRAMDATA','JAVA_HOME','NUMBER_OF_PROCESSORS')
    return {**{k:v for k,v in os.environ.items() if k.upper() in keep},'PYTHONDONTWRITEBYTECODE':'1',**values}

def listener_is_owned(owner, process, name):
    if owner == str(process.pid):
        return True
    if name != 'valuation' or not owner.isdecimal():
        return False
    # Windows virtual environments use a parent launcher for the Python interpreter.
    evidence=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        f"Get-CimInstance Win32_Process -Filter 'ProcessId={int(owner)}' | Select-Object Name,ParentProcessId,CommandLine | ConvertTo-Json -Compress"],
        text=True,timeout=12).strip()
    child=json.loads(evidence) if evidence else {}
    argv=child.get('CommandLine','')
    return (child.get('Name')=='python.exe' and child.get('ParentProcessId')==process.pid
            and f'-m uvicorn main:app --host {HOST} --port {PORT[name]}' in argv)

def verify_mysql_process(owner, data):
    if not owner.isdecimal():
        return False
    evidence=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        f"Get-CimInstance Win32_Process -Filter 'ProcessId={int(owner)}' | Select-Object Name,CommandLine | ConvertTo-Json -Compress"],
        text=True,timeout=12).strip()
    process=json.loads(evidence) if evidence else {}
    return process.get('Name')=='mysqld.exe' and str(data).lower() in process.get('CommandLine','').lower()

def verify_artifacts(folder):
    pinned = json.loads((ROOT/'ai-services/artifacts/v1_3.manifest.json').read_text(encoding='utf-8'))
    names = {'model.json', 'feature_schema.json', 'calibration.json', 'artifact_manifest.json'}
    if pinned['model_version'] != 'v1.3' or {entry['name'] for entry in pinned['files']} != names:
        raise RuntimeError('Unexpected V1.3 manifest')
    for entry in pinned['files']:
        file = folder / entry['name']
        with file.open('rb') as data:
            actual = hashlib.file_digest(data, 'sha256').hexdigest()
        if actual != entry['sha256'] or file.stat().st_size != entry['bytes']:
            raise RuntimeError('Invalid fixture artifact: '+entry['name'])


def run(args):
    if os.name != 'nt':
        raise RuntimeError('This fixture requires Windows process ownership checks')
    if subprocess.run(['git','merge-base','--is-ancestor',APPROVED_BASE,'HEAD'],cwd=ROOT).returncode:
        raise RuntimeError('Approved WP04 main must be integrated first')
    jar = ROOT/'backend/target/smartprop-backend-0.1.0.jar'
    vite = ROOT/'frontend/node_modules/vite/bin/vite.js'
    java, node = shutil.which('java.exe'), shutil.which('node.exe')
    source_tools = [args.mysql_bin.resolve()/f'{name}.exe' for name in ('mysqld','mysql','mysqladmin')]
    if not java or not node or any(not file.is_file() for file in [jar,vite,*source_tools]):
        raise RuntimeError('Build Spring Boot and provide JDK, Node/Vite, and MySQL binaries')
    artifact_dir = args.artifacts.resolve()
    verify_artifacts(artifact_dir)
    for port in (*PORT.values(),*UNUSED_PROXY_PORTS):
        available(port)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    manifest = EVIDENCE/'runtime.json'
    run_dir = Path(tempfile.mkdtemp(prefix='wp04-owned-',dir=EVIDENCE))
    data = run_dir/'mysql-data'
    password = secrets.token_hex(15)
    database_password = secrets.token_hex(24)
    marker = secrets.token_hex(16)
    checkpoint_key = secrets.token_hex(32)
    pid_proof = {}
    processes = {}
    mysql_verified = False
    enabled = subprocess.CREATE_NO_WINDOW
    mysqld, mysql, mysqladmin = map(str,source_tools)
    mysql_args=['--no-defaults','--protocol=TCP','--host='+HOST,f'--port={PORT["mysql"]}','--user=root','-BN','--default-character-set=utf8mb4']
    safe_env=clean_env({})
    stop=run_dir/'STOP'

    def report(state):
        manifest.write_text(json.dumps({'state':state,'root':str(run_dir),'stack':BASE,'ports':PORT,
            'pids':pid_proof,'schema':SCHEMA,'stop_file':str(stop),
            'credentials_file':str(run_dir/'fixture-accounts.json'),'db_file':str(run_dir/'db-runtime.json')},
            indent=2)+'\n',encoding='utf-8')

    def sql(command):
        result=subprocess.run([mysql,*mysql_args],input=command.encode('utf-8'),env=safe_env,
            capture_output=True,timeout=15,creationflags=enabled)
        if result.returncode:
            # SQL includes fixture credentials during setup, so only record the error class.
            match=__import__('re').search(rb'ERROR [0-9]+',result.stderr)
            raise RuntimeError('MySQL fixture command failed '+(match.group().decode() if match else ''))
        return result.stdout.decode('utf-8').strip()

    def start(name, argv, folder, env):
        with (run_dir/(name+'.log')).open('wb') as log:
            process=subprocess.Popen([str(value) for value in argv],cwd=folder,env=env,stdout=log,
                stderr=subprocess.STDOUT,creationflags=enabled)
        processes[name]=process
        return process

    try:
        report('provisioning')
        init=subprocess.run([mysqld,'--no-defaults','--initialize-insecure',f'--datadir={data}',
            f'--log-error={run_dir/"mysql-init.log"}'],env=safe_env,creationflags=enabled,timeout=240)
        if init.returncode:
            raise RuntimeError('MySQL fixture initialization failed')
        db=start('mysql',[mysqld,'--no-defaults','--bind-address='+HOST,f'--port={PORT["mysql"]}',
            f'--datadir={data}',f'--log-error={run_dir/"mysqld-server.log"}','--skip-log-bin','--mysqlx=OFF',
            '--innodb-flush-log-at-trx-commit=2'],
            ROOT,safe_env)
        for _ in range(60):
            with socket.socket() as s:
                s.settimeout(.3)
                if s.connect_ex((HOST,PORT['mysql']))==0:
                    break
            time.sleep(.5)
        else:
            raise RuntimeError('MySQL fixture did not listen')
        for _ in range(10):
            owner=loopback_owner(PORT['mysql'])
            if owner:
                break
            time.sleep(.5)
        if not verify_mysql_process(owner,data):
            raise RuntimeError('MySQL port ownership differs from launcher')
        identity=sql('SELECT @@server_uuid,@@datadir,@@port;').split('\t')
        server_uuid, actual_dir, actual_port=identity
        uuid.UUID(server_uuid)
        if Path(actual_dir).resolve()!=data.resolve() or int(actual_port)!=PORT['mysql']:
            raise RuntimeError('MySQL datadir/port check failed')
        mysql_verified=True
        pid_proof['mysql']={'pid':int(owner),'launcher_pid':db.pid,'uuid':server_uuid,'datadir':str(data)}
        assertion=f'SELECT marker FROM {SCHEMA}.wp04_isolation_marker;'
        sql(f"""CREATE DATABASE {SCHEMA} CHARACTER SET utf8mb4;
CREATE USER 'wp04_fixture'@'{HOST}' IDENTIFIED BY '{database_password}';
GRANT ALL ON {SCHEMA}.* TO 'wp04_fixture'@'{HOST}';
CREATE TABLE {SCHEMA}.wp04_isolation_marker(marker VARCHAR(32) NOT NULL);
INSERT INTO {SCHEMA}.wp04_isolation_marker VALUES('{marker}');
CREATE DATABASE wp02_phase_b_fixture CHARACTER SET utf8mb4;""")
        if sql(assertion)!=marker:
            raise RuntimeError('MySQL marker check failed')

        ai_folder=ROOT/'ai-services'
        ai_env={'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','OMP_NUM_THREADS':'2',
            'SMARTPROP_V1_3_MODEL_DIR':str(artifact_dir)}
        valuation=start('valuation',[args.python,'-X','utf8','-m','uvicorn','main:app','--host',HOST,
            '--port',PORT['valuation'],'--no-proxy-headers'],ai_folder,clean_env(ai_env))
        spring_env={'DB_URL':f'jdbc:mysql://{HOST}:{PORT["mysql"]}/{SCHEMA}?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false',
            'DB_USER':'wp04_fixture','DB_PASSWORD':database_password,'JWT_SECRET':secrets.token_hex(32),
            'STORAGE_ROOT':str(run_dir/'uploads'),'CORS_ORIGINS':BASE['react'],
            'APP_VALUATION_ENABLED':'true','APP_VALUATION_BASE_URL':BASE['valuation'],
            'APP_ADVISOR_VALUATION_ENABLED':'true','APP_ADVISOR_VALUATION_BASE_URL':BASE['valuation'],
            'APP_RECOMMENDATION_TINIX_ENABLED':'false','APP_RECOMMENDATION_ALLOW_UNVERIFIED_EXTERNAL':'false',
            'REFRESH_ENABLED':'true','REFRESH_SECURE_COOKIE':'false','CHAT_CHECKPOINT_KEY':checkpoint_key}
        jars=run_dir/'java-libs'
        jars.mkdir(exist_ok=True)
        with zipfile.ZipFile(jar) as bundle:
            for name in bundle.namelist():
                if name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
                    target=jars/Path(name).name
                    if not target.is_file():
                        target.write_bytes(bundle.read(name))
        migration_env={**{k:v for k,v in spring_env.items() if k.startswith('DB_')},
            'WP04_SQL_UUID':server_uuid,'WP04_SQL_DATADIR':str(data),'WP04_SQL_MARKER':marker}
        with (run_dir/'migrations.log').open('wb') as log:
            migration=subprocess.run([java,'-cp',str(jars/'*'),str(TOOLS/'Wp04Migrate.java')],
                cwd=ROOT,env=clean_env(migration_env),stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=enabled)
        if migration.returncode:
            raise RuntimeError('Disposable Flyway migration failed; see migrations.log')
        spring=start('spring',[java,'-jar',jar,
            '--server.address='+HOST,f'--server.port={PORT["spring"]}','--spring.profiles.active=standard-migrations',
            '--spring.flyway.enabled=false',
            '--spring.jpa.hibernate.ddl-auto=validate','--spring.sql.init.mode=never','--app.seed.enabled=false',
            '--app.database-seed.enabled=false'],ROOT,clean_env(spring_env))
        wait_http(BASE['valuation']+'/model/options',valuation,60)
        wait_http(BASE['spring']+'/actuator/health',spring,140)
        if sql(assertion)!=marker or sql('SELECT @@server_uuid;')!=server_uuid:
            raise RuntimeError('MySQL fixture identity changed')
        for role, email in demos.items():
            code,_=http(BASE['spring']+'/api/v1/auth/register',
                {'fullName':f'Fixture {role.title()}','email':email,'password':password,'role':'BUYER'})
            if code!=201:
                raise RuntimeError('Unable to create synthetic account')
        sql(f"""USE {SCHEMA};
UPDATE users SET role='BROKER' WHERE email='{demos['broker']}';
UPDATE users SET role='ADMIN' WHERE email='{demos['admin']}';
UPDATE users SET email_verified_at=UTC_TIMESTAMP(6) WHERE email LIKE '%-wp04@example.invalid';""")
        ids=[]
        rows=[]
        for index in range(16):
            id=f'61000000-0000-4000-8000-{index+1:012}'
            ids.append(id)
            district, ward = ('Cẩm Lệ', 'Hòa Thọ Đông') if index < 8 else ('Hải Châu', 'Hòa Cường Bắc')
            rows.append(f"""('{id}',@owner,'Nhà thử WP04 {index+1}','Tin tổng hợp cho demo, không có thông tin cá nhân.',
'HOUSE','SALE',{3200000000+(index%8)*180000000},'TOTAL',{72+(index%8)*3},3,2,'Đà Nẵng','{district}','{ward}',
'Đường WP04 {index+1}, {ward}',ST_GeomFromText('POINT({108.214+index*.0001} {16.037+index*.0001})',4326,'axis-order=long-lat'),
'PUBLISHED',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6)+INTERVAL 30 DAY)""")
        sql(f"""USE {SCHEMA}; SET @owner=(SELECT id FROM users WHERE email='{demos['broker']}');
INSERT INTO properties(id,owner_id,title,description,property_type,transaction_type,price,price_unit,area_sqm,bedrooms,bathrooms,
city,district,ward,address,location,status,published_at,expires_at) VALUES """+',\n'.join(rows)+';')
        sql(f"""USE {SCHEMA};
INSERT INTO points_of_interest(id,name,category,location,source_name,external_id)
VALUES ('62000000-0000-4000-8000-000000000001','Công viên WP04 tổng hợp','park',
ST_GeomFromText('POINT(108.215 16.038)',4326,'axis-order=long-lat'),'SYNTHETIC_WP04','fixture-park');""")
        (run_dir/'fixture-accounts.json').write_text(json.dumps({'accounts':demos,'password':password,'listed_property_ids':ids},indent=2)+'\n',encoding='utf-8')
        vite_env={'SMARTPROP_DEV_PORT':str(PORT['react']),'SMARTPROP_DEV_API_TARGET':BASE['spring'],
            'SMARTPROP_DEV_CHAT_TARGET':f'http://{HOST}:54045','SMARTPROP_DEV_VISION_TARGET':f'http://{HOST}:54046',
            'AI_API_TARGET':BASE['valuation'],'VITE_ENABLE_REFRESH':'true','VITE_API_BASE_URL':'/api/v1'}
        react=start('react',[node,vite,'--host',HOST],
            ROOT/'frontend',clean_env(vite_env))
        wait_http(BASE['react']+'/',react,45)
        for name,process in (('spring',spring),('valuation',valuation),('react',react)):
            owner=loopback_owner(PORT[name])
            if not listener_is_owned(owner,process,name):
                raise RuntimeError(name+' loopback owner differs from launcher')
            pid_proof[name]={'pid':int(owner),'launcher_pid':process.pid}
        fixture={'uuid':server_uuid,'port':PORT['mysql'],'datadir':str(data),'schema':SCHEMA,
            'user':'wp04_fixture','password':database_password,'marker':marker,'mysql':mysql}
        (run_dir/'db-runtime.json').write_text(json.dumps(fixture),encoding='utf-8')
        report('ready')
        print('Owned WP04 runtime ready: '+str(manifest.relative_to(ROOT)),flush=True)
        pause=run_dir/'PAUSE_VALUATION'
        resume_request=run_dir/'RESTORE_VALUATION'
        while not stop.exists():
            if pause.is_file() and 'valuation' in processes:
                owned=processes['valuation']
                expected=pid_proof['valuation']['pid']
                if loopback_owner(PORT['valuation'])!=str(expected) or not listener_is_owned(str(expected),owned,'valuation'):
                    raise RuntimeError('Valuation owner changed before requested outage')
                owned.terminate()
                owned.wait(timeout=15)
                deadline = time.monotonic() + 15
                while owner := loopback_owner(PORT['valuation']):
                    if owner != str(expected):
                        raise RuntimeError('Valuation port was claimed by another process')
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Owned valuation listener did not close')
                    time.sleep(.25)
                del processes['valuation']
                report('valuation-offline')
            if resume_request.is_file() and 'valuation' not in processes:
                valuation=start('valuation-recovered',[args.python,'-X','utf8','-m','uvicorn','main:app','--host',HOST,
                    '--port',PORT['valuation'],'--no-proxy-headers'],ai_folder,clean_env(ai_env))
                del processes['valuation-recovered']
                processes['valuation']=valuation
                wait_http(BASE['valuation']+'/model/options',valuation,60)
                owner=loopback_owner(PORT['valuation'])
                if not listener_is_owned(owner,valuation,'valuation') or int(owner)==pid_proof['valuation']['pid']:
                    raise RuntimeError('Recovered valuation listener identity could not be verified')
                pid_proof['valuation_recovered']=int(owner)
                report('valuation-recovered')
                while not stop.exists():
                    if any(p.poll() is not None for p in processes.values()):
                        raise RuntimeError('A recovered fixture service stopped unexpectedly')
                    time.sleep(.5)
                break
            if any(p.poll() is not None for p in processes.values()):
                raise RuntimeError('A fixture service stopped unexpectedly')
            time.sleep(.5)
    except urllib.error.HTTPError as error:
        print('Fixture HTTP error',error.code,error.url,flush=True)
        report('failed')
        return 1
    except (OSError,RuntimeError,subprocess.SubprocessError) as error:
        print('Fixture failed:',str(error),flush=True)
        report('failed')
        return 1
    finally:
        for name,process in reversed(list(processes.items())):
            if name=='mysql':
                continue
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
        if mysql_verified and loopback_owner(PORT['mysql'])==str(pid_proof['mysql']['pid']):
            subprocess.run([mysqladmin,*mysql_args[:5],'shutdown'],env=safe_env,capture_output=True,timeout=20,creationflags=enabled)
            processes['mysql'].wait(timeout=90)
        elif 'mysql' in processes and processes['mysql'].poll() is None:
            processes['mysql'].terminate()
            processes['mysql'].wait(timeout=90)
    report('stopped')
    return 0

if __name__=='__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('--mysql-bin',type=Path,required=True)
    cli.add_argument('--python',type=Path,default=Path(sys.executable))
    cli.add_argument('--artifacts',type=Path,default=ROOT/'ai-services/artifacts/v1_3')
    sys.exit(run(cli.parse_args()))
