"""Browser stage of check-history-mysql.py; uses only that check's private schema."""
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from local_runtime import datasource_arguments, spring_environment, stop_owned


def run_browser_check(root, runtime, environment, work, ai_port):
    db_url = environment.get('SMARTPROP_HISTORY_TEST_URL', '')
    if not re.fullmatch(r'jdbc:mysql://127\.0\.0\.1:13317/smartprop_history_[a-z0-9]+\?[^\s]+', db_url):
        raise RuntimeError('Browser check requires the isolated history schema created by its parent.')
    frontend = root / 'frontend/vue.ui'
    cli = frontend / 'node_modules/@playwright/test/cli.js'
    node = shutil.which('node.exe' if os.name == 'nt' else 'node')
    if not node or not cli.is_file():
        raise RuntimeError('Install Node and run npm ci in frontend/vue.ui before the browser check.')
    backend_port = 18082
    env = spring_environment(environment,url=db_url,user='root',password='',jwt=secrets.token_urlsafe(48))
    env.update(
        CORS_ORIGINS='http://127.0.0.1:15174',
        SMARTPROP_BROWSER_HISTORY_TEST='isolated',
        SMARTPROP_BROWSER_HISTORY_REPORT=str(work / 'browser-results.json'),
    )
    command = [
        str(Path(runtime['jdk']) / 'bin/java.exe'), '-jar', str(work / 'target/smartprop-backend-0.1.0.jar'),
        *datasource_arguments(db_url,'root'), '--spring.profiles.active=default',
        f'--server.port={backend_port}', '--server.address=127.0.0.1',
        '--app.valuation.enabled=true', f'--app.valuation.base-url=http://127.0.0.1:{ai_port}',
        '--spring.flyway.enabled=false', '--spring.sql.init.mode=never', '--spring.jpa.hibernate.ddl-auto=validate',
        '--app.seed.enabled=false', '--app.database-seed.enabled=false', '--app.email.enabled=false',
        '--app.email.worker-enabled=false', '--app.refresh.enabled=false',
        '--debug=false', '--logging.level.root=INFO', '--logging.level.org.springframework=INFO',
        f'--app.storage-root={work / "uploads"}',
    ]
    backend = None
    with (work / 'browser-backend.log').open('w', encoding='utf-8') as log:
        try:
            backend = subprocess.Popen(command, cwd=root / 'backend', env=env, stdout=log, stderr=subprocess.STDOUT)
            print(f'Browser backend PID={backend.pid}; own schema only; waiting for readiness.', flush=True)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if backend.poll() is not None:
                    raise RuntimeError(f'Browser backend exited; see {work / "browser-backend.log"}')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{backend_port}/actuator/health/readiness', timeout=1) as response:
                        if json.load(response).get('status') == 'UP':
                            break
                except (OSError, ValueError):
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError(f'Browser backend readiness timed out; see {work / "browser-backend.log"}')
            # No bearer/password values are printed; browser fixtures are synthetic.
            result = subprocess.run([node, str(cli), 'test', '--config', 'playwright.live.config.js'],
                                    cwd=frontend, env=env, timeout=240)
            if result.returncode:
                raise RuntimeError('Real browser history check failed; see ignored test-results and ' + str(work))
            report = json.loads((work / 'browser-results.json').read_text(encoding='utf-8'))
            stats = report['stats']
            if stats['unexpected'] or stats['flaky'] or stats['skipped'] or stats['expected'] != 3:
                raise RuntimeError('Expected exactly three passing real-stack browser checks with no retries or skips.')
            return {'passed': 3, 'mocked_api_responses': False, 'backend_port': backend_port,
                    'frontend_port': 15174, 'report': str(work / 'browser-results.json')}
        finally:
            stop_owned(backend,timeout=15)
