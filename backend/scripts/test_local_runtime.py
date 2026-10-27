"""Synthetic regression checks; never open a DB connection or signal real processes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import local_runtime as runtime


class LocalRuntimeTest(unittest.TestCase):
    def test_ambient_spring_and_jvm_configuration_cannot_select_a_source_database(self):
        parent={'PATH':'preserved','SPRING_DATASOURCE_URL':'jdbc:mysql://127.0.0.1:3306/source_fixture',
                'SPRING_DATASOURCE_USERNAME':'ambient','SPRING_DATASOURCE_PASSWORD':'ambient-secret',
                'SPRING_APPLICATION_JSON':'{"spring":{"datasource":{"url":"source_fixture"}}}',
                'SPRING_CONFIG_LOCATION':'file:source-config.yml','SPRING_PROFILES_ACTIVE':'production',
                'JAVA_TOOL_OPTIONS':'-Dspring.datasource.url=source_fixture','APP_JWT_SECRET':'ambient'}
        url='jdbc:mysql://127.0.0.1:13317/smartprop_history_fixture?connectionTimeZone=UTC'
        env=runtime.spring_environment(parent,url=url,user='root',password='generated-secret',jwt='generated-jwt')
        self.assertEqual(env['PATH'],'preserved')
        self.assertEqual(env['SPRING_DATASOURCE_URL'],url)
        self.assertEqual(env['SPRING_DATASOURCE_PASSWORD'],'generated-secret')
        self.assertEqual(env['APP_JWT_SECRET'],'generated-jwt')
        for name in ['SPRING_APPLICATION_JSON','SPRING_CONFIG_LOCATION','SPRING_PROFILES_ACTIVE','JAVA_TOOL_OPTIONS']:
            self.assertNotIn(name,env)
        options=runtime.datasource_arguments(url,'root')
        self.assertIn('--spring.datasource.url='+url,options)
        self.assertIn('--spring.datasource.username=root',options)
        self.assertNotIn('generated-secret',' '.join(options))

    def test_source_schema_and_nonloopback_peers_are_rejected(self):
        for url in ['jdbc:mysql://127.0.0.1:3306/smartprop?x=1','jdbc:mysql://remote:13317/smartprop_history_fixture?x=1']:
            with self.subTest(url=url),self.assertRaises(ValueError):
                runtime.datasource_arguments(url,'root')

    def test_mysql_cleanup_is_reached_when_ai_cleanup_raises(self):
        called=[]
        def bad_ai():
            called.append('ai')
            raise subprocess.TimeoutExpired('synthetic-ai',5)
        with self.assertRaises(RuntimeError):
            runtime.cleanup_all(bad_ai,lambda:called.append('mysql'))
        self.assertEqual(called,['ai','mysql'])

    def test_stuck_process_is_killed_after_bounded_wait(self):
        process=Mock()
        process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired('synthetic',1),0]
        runtime.stop_owned(process,timeout=1)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_args_list[1].kwargs,{'timeout':5})

    def test_failed_graceful_mysql_shutdown_still_falls_back(self):
        process=Mock()
        process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired('synthetic',1),0]
        runtime.stop_owned(process,graceful=Mock(side_effect=OSError('synthetic')),timeout=1)
        process.kill.assert_called_once()

    def test_demo_call_site_pins_db_and_reaches_mysql_after_interrupt(self):
        spec=importlib.util.spec_from_file_location('run_demo_test',Path(__file__).with_name('run-demo.py'))
        demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for executable in ['jdk/bin/java.exe','mysql/bin/mysqld.exe','mysql/bin/mysql.exe']:
                path=root/executable;path.parent.mkdir(parents=True,exist_ok=True);path.touch()
            (root/'backend/target').mkdir(parents=True)
            (root/'backend/pom.xml').touch()
            (root/'backend/target/smartprop-backend-0.1.0.jar').touch()
            mysql=Mock();mysql.poll.return_value=None;mysql.wait.return_value=0
            backend=Mock();backend.poll.return_value=None;backend.wait.side_effect=[KeyboardInterrupt(),subprocess.TimeoutExpired('synthetic',10),0]
            env={'JAVA_HOME':str(root/'jdk'),'SMARTPROP_MYSQL_HOME':str(root/'mysql'),
                 'SPRING_DATASOURCE_URL':'jdbc:mysql://127.0.0.1:3306/source_fixture',
                 'SPRING_APPLICATION_JSON':'{}'}
            with patch.object(demo,'ROOT',root),patch.object(demo,'BACKEND',root/'backend'),patch.object(demo,'STATE',root/'state'),\
                 patch.object(demo,'ensure_free'),patch.dict(os.environ,env,clear=True),\
                 patch('sys.argv',['run-demo.py']),patch.object(demo.subprocess,'Popen',side_effect=[mysql,backend]) as launch,\
                 patch.object(demo.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
                self.assertEqual(demo.main(),130)
            args,kwargs=launch.call_args
            self.assertIn('--spring.datasource.url='+kwargs['env']['DB_URL'],args[0])
            self.assertEqual(kwargs['env']['SPRING_DATASOURCE_URL'],kwargs['env']['DB_URL'])
            self.assertNotIn('SPRING_APPLICATION_JSON',kwargs['env'])
            self.assertTrue(any('mysqladmin.exe' in call.args[0][0] for call in run.call_args_list))
            backend.kill.assert_called_once()


if __name__=='__main__':unittest.main()
