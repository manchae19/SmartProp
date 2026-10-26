"""Run a persistent, isolated local demo DB and backend; never read the real .env."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
STATE = BACKEND / "var/local-demo"


def ensure_free(port):
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"Cổng {port} đang được dùng; chọn cổng khác, không dừng tiến trình đó.") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db-port", type=int, default=13306)
    parser.add_argument("--check", action="store_true", help="Kiểm tra readiness rồi dừng các tiến trình vừa tạo.")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or not 1024 <= args.db_port <= 65535 or args.port == args.db_port:
        parser.error("Các cổng phải khác nhau và từ 1024 đến 65535.")
    ensure_free(args.port)
    ensure_free(args.db_port)
    runtime_path = ROOT / ".scratch/devtools/runtime.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path.exists() else {}
    java_home = Path(os.environ.get("JAVA_HOME") or runtime.get("jdk", ""))
    mysql_home = Path(os.environ.get("SMARTPROP_MYSQL_HOME") or runtime.get("mysql", ""))
    maven_home = Path(os.environ.get("MAVEN_HOME") or runtime.get("maven", ""))
    for executable in (java_home / "bin/java.exe", mysql_home / "bin/mysqld.exe", mysql_home / "bin/mysql.exe"):
        if not executable.is_file():
            raise RuntimeError("Cần JDK 21 và MySQL ZIP. Xem docs/VALUATION_HISTORY.md; runtime hiện tại: " + str(executable))
    jar = BACKEND / "target/smartprop-backend-0.1.0.jar"
    sources = list((BACKEND / "src").rglob("*.java")) + [BACKEND / "pom.xml"]
    if not jar.exists() or any(path.stat().st_mtime > jar.stat().st_mtime for path in sources):
        launcher = next((maven_home / "boot").glob("plexus-classworlds-*.jar"), None)
        if launcher is None:
            raise RuntimeError("Cần Maven 3.9.11; cấu hình MAVEN_HOME hoặc build backend trước.")
        command = [str(java_home / "bin/java.exe"), f"-Dmaven.home={maven_home}",
            f"-Dclassworlds.conf={maven_home}/bin/m2.conf", f"-Dmaven.multiModuleProjectDirectory={BACKEND}",
            f"-Dmaven.repo.local={ROOT}/.scratch/m2", "-classpath", str(launcher),
            "org.codehaus.plexus.classworlds.launcher.Launcher", "-B", "-ntp", "-f", str(BACKEND / "pom.xml"), "-DskipTests", "package"]
        build_env = os.environ.copy()
        build_env["JAVA_HOME"] = str(java_home)
        subprocess.run(command, cwd=ROOT, env=build_env, check=True)
    STATE.mkdir(parents=True, exist_ok=True)
    config_path = STATE / "private-config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = dict(jwt_secret=secrets.token_urlsafe(48), app_password=secrets.token_urlsafe(32), migration_sha256={})
        config_path.write_text(json.dumps(config), encoding="utf-8")
    migrations = sorted((ROOT / "database/migrations").glob("V*__*.sql"), key=lambda path: int(path.name.split("__")[0][1:]))
    for path in migrations:
        if path.name in config["migration_sha256"] and hashlib.sha256(path.read_bytes()).hexdigest() != config["migration_sha256"][path.name]:
            raise RuntimeError("SQL đã áp dụng vào demo bị sửa: " + path.name)
    data = STATE / "mysql-data"
    hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    if not data.exists():
        subprocess.run([str(mysql_home / "bin/mysqld.exe"), "--no-defaults", "--initialize-insecure",
            f"--basedir={mysql_home}", f"--datadir={data}", f"--log-error={STATE / 'mysql-initialize.log'}"], check=True, creationflags=hidden)
    mysql = subprocess.Popen([str(mysql_home / "bin/mysqld.exe"), "--no-defaults", f"--basedir={mysql_home}",
        f"--datadir={data}", "--bind-address=127.0.0.1", f"--port={args.db_port}", "--mysqlx=0", "--skip-log-bin",
        f"--log-error={STATE / 'mysql.log'}"], creationflags=hidden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sql_args = [str(mysql_home / "bin/mysql.exe"), "--no-defaults", "--connect-timeout=2", "--protocol=TCP",
        "--host=127.0.0.1", f"--port={args.db_port}", "--user=root", "--default-character-set=utf8mb4"]
    backend = None
    try:
        for _ in range(60):
            if mysql.poll() is not None:
                raise RuntimeError("MySQL demo không khởi động được; xem backend/var/local-demo/mysql.log")
            ready = subprocess.run(sql_args + ["--execute=SELECT 1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, creationflags=hidden)
            if ready.returncode == 0:
                break
            time.sleep(.5)
        else:
            raise RuntimeError("MySQL demo chưa sẵn sàng sau thời gian chờ.")

        def sql(value, schema=False):
            result = subprocess.run(sql_args + (["smartprop_local_demo"] if schema else []),
                input=value, encoding="utf-8", capture_output=True, timeout=30, creationflags=hidden)
            if result.returncode:
                # Keep SQL and generated credentials out of console errors.
                raise RuntimeError("Không áp dụng được SQL cho database demo; bản ghi dữ liệu hiện có được giữ nguyên.")
        sql("CREATE DATABASE IF NOT EXISTS smartprop_local_demo CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
        for path in migrations:
            if path.name not in config["migration_sha256"]:
                sql(path.read_text(encoding="utf-8-sig"), schema=True)
                config["migration_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                config_path.write_text(json.dumps(config), encoding="utf-8")
        # Random generated value is URL-safe; this is only the isolated demo instance.
        password = config["app_password"]
        sql(f"CREATE USER IF NOT EXISTS 'smartprop_demo'@'127.0.0.1' IDENTIFIED BY '{password}'; "
            f"ALTER USER 'smartprop_demo'@'127.0.0.1' IDENTIFIED BY '{password}'; "
            "GRANT SELECT,INSERT,UPDATE,DELETE ON smartprop_local_demo.* TO 'smartprop_demo'@'127.0.0.1';")
        env = os.environ.copy()
        env.update(DB_URL=f"jdbc:mysql://127.0.0.1:{args.db_port}/smartprop_local_demo?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false",
            DB_USER="smartprop_demo", DB_PASSWORD=password, JWT_SECRET=config["jwt_secret"],
            CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173")
        print(f"BE demo: http://127.0.0.1:{args.port}; MySQL riêng: 127.0.0.1:{args.db_port}. Giữ terminal mở.", flush=True)
        print("Dữ liệu demo lưu tại backend/var/local-demo; không đọc .env hoặc database nguồn.", flush=True)
        backend = subprocess.Popen([str(java_home / "bin/java.exe"), "-jar", str(jar), f"--server.port={args.port}",
            "--server.address=127.0.0.1", "--app.valuation.enabled=true", "--app.valuation.base-url=http://127.0.0.1:8000",
            "--spring.flyway.enabled=false", "--spring.sql.init.mode=never", "--spring.jpa.hibernate.ddl-auto=validate",
            "--app.seed.enabled=false", "--app.database-seed.enabled=false", "--app.email.enabled=false",
            "--debug=false", "--logging.level.root=INFO", "--logging.level.org.springframework=INFO",
            f"--app.storage-root={STATE / 'uploads'}"], cwd=BACKEND, env=env)
        if args.check:
            import urllib.request
            for _ in range(120):
                if backend.poll() is not None:
                    raise RuntimeError("Backend demo đã thoát trước khi sẵn sàng.")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/actuator/health/readiness", timeout=1) as response:
                        if json.load(response).get("status") == "UP":
                            print("Demo readiness: UP; kiểm tra xong, đang dừng đúng stack demo.", flush=True)
                            return 0
                except OSError:
                    pass
                time.sleep(.5)
            raise RuntimeError("Backend demo chưa sẵn sàng sau thời gian chờ.")
        return backend.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        if backend is not None and backend.poll() is None:
            backend.terminate()
            backend.wait(timeout=10)
        subprocess.run([str(mysql_home / "bin/mysqladmin.exe"), "--no-defaults", "--protocol=TCP", "--host=127.0.0.1",
            f"--port={args.db_port}", "--user=root", "shutdown"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, creationflags=hidden)
        try:
            mysql.wait(timeout=15)
        except subprocess.TimeoutExpired:
            mysql.terminate()
            mysql.wait(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.SubprocessError) as error:
        print(f"Không chạy được BE demo: {error}", file=sys.stderr)
        raise SystemExit(1)
