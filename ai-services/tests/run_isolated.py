"""Run pytest in-process from ai-services without access to live services."""
import ipaddress
import os
from pathlib import Path
import sys
import weakref


def main():
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["RAG_SQL_ENABLED"] = "false"
    sys.path.insert(0, str(Path.cwd()))
    local_sockets = weakref.WeakSet()
    blocked = set()

    def guard(event, args):
        if event not in {"socket.connect", "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
            return
        if event == "socket.getaddrinfo":
            host, port = args[:2]
            if host in (None, "localhost", "127.0.0.1", "::1"):
                return
        else:
            sock, address = args[:2]
            if isinstance(address, tuple):
                host, port = address[:2]
                if ipaddress.ip_address(host).is_loopback:
                    if event == "socket.bind" and port == 0:
                        local_sockets.add(sock)
                        return
                    if event == "socket.connect" and any(
                        bound.fileno() != -1 and bound.getsockname()[:2] == (host, port)
                        for bound in list(local_sockets)
                    ):
                        return
            else:
                host, port = "non-IP", None
        blocked.add((event, host, port))
        raise RuntimeError(f"Live network access blocked by test runner: {event}")

    sys.addaudithook(guard)
    import pytest

    result = pytest.main(sys.argv[1:])
    if blocked:
        print(f"Blocked live network operations: {len(blocked)}", file=sys.stderr)
        return 1
    return result


if __name__ == "__main__":
    sys.exit(main())
