"""Exercise the actual launcher with closed stdin and an unrelated cwd."""
import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

SERVICE_DIR = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose", action="store_true", help="Also check lifecycle logging and five seconds of uptime.")
    args = parser.parse_args()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory() as directory:
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", str(SERVICE_DIR / "run_api.py"), "--port", str(port)]
            + (["--diagnose"] if args.diagnose else []),
            cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        banner = process.stdout.readline()
        pid_match = re.search(r"SmartProp AI v6 \[PID (\d+)\]", banner)
        diagnostic_banner = ""
        try:
            assert pid_match, f"Không nhận được banner từ launcher: {banner!r}"
            if args.diagnose:
                diagnostic_banner = process.stdout.readline()
                prefix = "SmartProp diagnostic log: "
                assert diagnostic_banner.startswith(prefix), diagnostic_banner
                journal_path = Path(diagnostic_banner[len(prefix):].strip())
            deadline = time.monotonic() + 15
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=1) as client:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("Launcher thoát trước khi API sẵn sàng.")
                    try:
                        health = client.get("/health")
                        if health.status_code == 200:
                            assert health.json()["model_ready"] is True
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError("Launcher không khởi động được trong 15 giây.")
                    time.sleep(0.05)
                options = client.get("/model/options")
                options.raise_for_status()
                results = []
                for category in options.json()["categories"]:
                    response = client.post("/predict", json=dict(
                        category=category["category"], area_sqm=80, location_feature=category["locations"][0]))
                    response.raise_for_status()
                    assert response.json()["predicted_asking_price_vnd"] > 0
                    results.append(dict(category=category["category"], status=response.status_code))
                assert client.post("/predict", json={}).status_code == 422
                assert client.get("/docs").status_code == 200
                if args.diagnose:
                    for _ in range(5):
                        time.sleep(1)
                        assert process.poll() is None, "API tự tắt khi đang chờ."
                        response = client.get("/health")
                        response.raise_for_status()
                        assert response.json()["model_ready"] is True
                    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
                    assert events[0]["event"] == "launch"
                    assert any(event["event"] == "startup_result" and event["ready"] for event in events)
                    assert not any(event["event"] in ("stop_signal", "launcher_exit") for event in events)
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    # Windows venv Python starts a child interpreter. Its PID
                    # comes from our launcher's banner; no global enumeration.
                    if pid_match:
                        os.kill(int(pid_match[1]), signal.SIGTERM)
                    else:
                        process.terminate()
                else:
                    process.terminate()
            output, _ = process.communicate(timeout=5)
            output = banner + diagnostic_banner + output
            print(output.strip())
        assert "Application startup complete" in output
        assert "Aborted!" not in output
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            assert probe.connect_ex(("127.0.0.1", port)) != 0, "Server chưa dừng sau smoke test."
    print(json.dumps(dict(http_smoke_passed=True, launcher="run_api.py", closed_stdin=True,
                         unrelated_cwd=True, diagnostics=args.diagnose,
                         idle_health_checks=5 if args.diagnose else 0,
                         predictions=results, server_stopped=True), ensure_ascii=False))


if __name__ == "__main__":
    main()
