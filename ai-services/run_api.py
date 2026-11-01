"""Start the local demo without Click or assumptions about the working directory."""
import argparse
import os
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent


def port_number(value):
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Cổng phải từ 1 đến 65535.")
    return port


def main():
    parser = argparse.ArgumentParser(description="Chạy API SmartProp AI v6 trên localhost.")
    parser.add_argument("--port", type=port_number, default=8000)
    parser.add_argument("--diagnose", action="store_true", help="Ghi tín hiệu dừng và vòng đời API vào .scratch/api-diagnostics/.")
    args = parser.parse_args()

    print(f"SmartProp AI v6 [PID {os.getpid()}]: đang nạp thư viện và model, vui lòng giữ terminal mở.", flush=True)
    if args.diagnose:
        from api_diagnostics import run_diagnosed

        run_diagnosed(SERVICE_DIR, args.port)
        return

    import uvicorn

    uvicorn.run("main:app", app_dir=str(SERVICE_DIR), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("SmartProp AI: nhận tín hiệu ngắt trong khi khởi động.", file=sys.stderr, flush=True)
        raise SystemExit(130)
