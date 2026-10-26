"""Lifecycle diagnostics must observe signals without changing stop behaviour."""
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api_diagnostics import DiagnosticServer, RunJournal


class DiagnosticTests(unittest.TestCase):
    def test_signal_is_recorded_and_still_requests_graceful_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = RunJournal(Path(directory))
            server = DiagnosticServer(uvicorn.Config("main:app"), journal)
            with patch("builtins.print"):
                server.handle_exit(signal.SIGINT, None)
            self.assertTrue(server.should_exit)
            self.assertFalse(server.force_exit)
            entry = json.loads(journal.path.read_text(encoding="utf-8"))
            self.assertEqual((entry["event"], entry["signal"]), ("stop_signal", "SIGINT"))
            self.assertGreaterEqual(entry["elapsed_seconds"], 0)

    def test_second_interrupt_retains_uvicorn_force_exit_behaviour(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = RunJournal(Path(directory))
            server = DiagnosticServer(uvicorn.Config("main:app"), journal)
            with patch("builtins.print"):
                server.handle_exit(signal.SIGINT, None)
                server.handle_exit(signal.SIGINT, None)
            self.assertTrue(server.force_exit)
            entries = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["force_exit"] for entry in entries], [False, True])

    def test_unwritable_log_does_not_prevent_stop_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = RunJournal(Path(directory))
            journal.path = Path(directory)  # Opening a directory as a file fails.
            server = DiagnosticServer(uvicorn.Config("main:app"), journal)
            with patch("builtins.print"):
                server.handle_exit(signal.SIGTERM, None)
            self.assertTrue(server.should_exit)

    def test_real_server_records_signal_and_completes_shutdown(self):
        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def interrupt_after_startup():
            # Inject SIGINT in this process only, once Uvicorn is listening.
            signal.raise_signal(signal.SIGINT)

        with tempfile.TemporaryDirectory() as directory:
            journal = RunJournal(Path(directory))
            config = uvicorn.Config(app, host="127.0.0.1", port=0, lifespan="off",
                                    callback_notify=interrupt_after_startup, log_config=None)
            server = DiagnosticServer(config, journal)
            with patch("builtins.print"), self.assertRaises(KeyboardInterrupt):
                server.run()
            entries = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([entry["event"] for entry in entries],
                             ["startup_result", "stop_signal", "shutdown_begin", "shutdown_complete"])
            self.assertTrue(entries[0]["ready"])
            self.assertEqual(entries[1]["signal"], "SIGINT")


if __name__ == "__main__":
    unittest.main()
