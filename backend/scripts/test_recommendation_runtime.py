"""Runtime safety tests without MySQL/process starts or private credentials."""
import importlib.util,socket,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('runtime',Path(__file__).with_name('run-recommendation-local.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RecommendationRuntimeTest(unittest.TestCase):
    def test_current_artifact_has_controller_and_exact_security_route(self):self.assertTrue(m.artifact().is_file())
    def test_readonly_command_has_no_migration_or_import(self):
        args=m.command('java','jar',8080)
        for flag in ['--spring.flyway.enabled=false','--spring.sql.init.mode=never','--spring.jpa.hibernate.ddl-auto=validate','--spring.datasource.hikari.read-only=true','--app.import.external-listings=','--app.recommendation.allow-unverified-external=false']:self.assertIn(flag,args)
        self.assertFalse(any('password' in x.lower() or 'jwt-secret' in x.lower() for x in args))
    def test_occupied_port_is_refused_without_replacing_process(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));s.listen();port=s.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError,'Port already used'):m.check_port(port)
    def test_database_and_bind_are_pinned(self):
        args=m.command('java','jar',8082)
        self.assertIn('--server.address=127.0.0.1',args)
        self.assertIn('--spring.datasource.url=jdbc:mysql://127.0.0.1:3306/smartprop?connectionTimeZone=UTC',args)
        self.assertNotIn('13306',' '.join(args))
if __name__=='__main__':unittest.main()
