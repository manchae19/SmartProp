"""Opt-in lifecycle diagnostics; preserve Uvicorn's normal signal handling."""
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone

import uvicorn


class RunJournal:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.path = directory / f"api-{timestamp}-{os.getpid()}.jsonl"
        self.started_at = time.monotonic()

    def record(self, event, **fields):
        entry = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                     elapsed_seconds=round(time.monotonic() - self.started_at, 3),
                     pid=os.getpid(), event=event, **fields)
        line = json.dumps(entry, ensure_ascii=False)
        # Diagnostic output must not prevent Uvicorn from handling a stop signal.
        try:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        except OSError as error:
            self._print(f"SmartProp diagnostic: không ghi được log ({type(error).__name__}).")
        self._print(f"SmartProp diagnostic: {line}")

    @staticmethod
    def _print(message):
        try:
            print(message, flush=True)
        except (OSError, RuntimeError):
            pass


class DiagnosticServer(uvicorn.Server):
    def __init__(self, config, journal):
        super().__init__(config)
        self.journal = journal

    def handle_exit(self, sig, frame):
        super().handle_exit(sig, frame)
        self.journal.record("stop_signal", signal=signal.Signals(sig).name,
                            force_exit=self.force_exit)

    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        self.journal.record("startup_result", ready=self.started)

    async def shutdown(self, sockets=None):
        self.journal.record("shutdown_begin", should_exit=self.should_exit)
        await super().shutdown(sockets=sockets)
        self.journal.record("shutdown_complete")


def run_diagnosed(service_dir, port):
    journal = RunJournal(service_dir.parent / ".scratch" / "api-diagnostics")
    print(f"SmartProp diagnostic log: {journal.path}", flush=True)
    journal.record("launch", parent_pid=os.getppid(), port=port)
    server = None
    try:
        # Match run_api.py's app_dir independently of the shell's working directory.
        sys.path.insert(0, str(service_dir))
        config = uvicorn.Config("main:app", host="127.0.0.1", port=port, workers=1)
        config.load_app()
        server = DiagnosticServer(config, journal)
        try:
            server.run()
        except KeyboardInterrupt:
            # Uvicorn re-raises captured SIGINT after its graceful shutdown.
            journal.record("keyboard_interrupt")
        if not server.started:
            raise SystemExit(3)
    except BaseException as error:
        journal.record("exit_exception", exception_type=type(error).__name__)
        raise
    finally:
        journal.record("launcher_exit", ready=bool(server and server.started),
                       captured_signals=[signal.Signals(sig).name for sig in server._captured_signals]
                       if server else [])
