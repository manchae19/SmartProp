"""Pin private local databases and stop only processes owned by a launcher."""
import os
from pathlib import Path
import re
import subprocess


def datasource_arguments(url, user):
    if not re.fullmatch(r'jdbc:mysql://127\.0\.0\.1:\d+/(?:smartprop_local_demo|smartprop_history_[a-z0-9]+)\?[^\s]+',url):
        raise ValueError('Only an explicitly named private loopback schema is allowed')
    return ['--spring.datasource.url='+url,'--spring.datasource.username='+user]


def spring_environment(parent, *, url, user, password, jwt):
    datasource_arguments(url,user)
    env={key:value for key,value in parent.items()
         if not key.upper().startswith(('SPRING_','APP_','DB_','JWT_'))
         and key.upper() not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','JAVA_OPTIONS'}}
    env.update(DB_URL=url,DB_USER=user,DB_PASSWORD=password,JWT_SECRET=jwt,
               SPRING_DATASOURCE_URL=url,SPRING_DATASOURCE_USERNAME=user,SPRING_DATASOURCE_PASSWORD=password,
               APP_JWT_SECRET=jwt)
    return env


def cleanup_all(*actions):
    failures=[]
    for action in actions:
        try:
            action()
        except BaseException as error:
            failures.append(error)
    if failures:
        raise RuntimeError('Owned process cleanup failed: '+', '.join(type(e).__name__ for e in failures)) from failures[0]


def kill_owned_tree(process):
    if process.poll() is not None:
        return
    if os.name=='nt':
        executable=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'
        result=subprocess.run([str(executable),'/PID',str(process.pid),'/T','/F'],
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        if result.returncode and process.poll() is None:
            raise RuntimeError('Could not stop an owned test process tree')
    else:
        process.kill()


def stop_owned(process, *, graceful=None, force=None, timeout=10):
    if process is None or process.poll() is not None:
        return
    try:
        if graceful is not None:
            graceful()
        else:
            process.terminate()
    except (OSError,subprocess.SubprocessError):
        # A failed graceful stop still gets a bounded wait and a force fallback.
        pass
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if force is not None:
            force()
        else:
            process.kill()
        process.wait(timeout=5)
