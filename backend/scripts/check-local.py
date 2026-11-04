"""Read-only checks for the local FE, AI and backend; never start or stop services."""
import argparse
import json
import urllib.error
import urllib.request


def port(value):
    result = int(value)
    if not 1024 <= result <= 65535:
        raise argparse.ArgumentTypeError('Cổng phải từ 1024 đến 65535.')
    return result


def probe(url):
    try:
        try:
            response = urllib.request.urlopen(url, timeout=2)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status = response.status
            body = response.read(65537)
        try:
            data = json.loads(body) if len(body) <= 65536 else None
        except (ValueError, UnicodeError):
            data = None
        return status, data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return None, {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend-port', type=port, default=5173)
    parser.add_argument('--ai-port', type=port, default=8000)
    parser.add_argument('--backend-port', type=port, default=8080)
    args = parser.parse_args()
    checks = [
        ('AI v6', args.ai_port, '/health', lambda status, data: status == 200 and data.get('model_ready') is True and data.get('model_version') == 'v6',
         r'Chạy .\ai-services\.venv\Scripts\python.exe -X utf8 ai-services/run_api.py'),
        ('BE và MySQL', args.backend_port, '/actuator/health/readiness', lambda status, data: status == 200 and data.get('status') == 'UP',
         r'Kiểm tra terminal BE: powershell -NoProfile -File backend/scripts/run-local.ps1'),
        ('FE → AI', args.frontend_port, '/api/ai/health', lambda status, data: status == 200 and data.get('model_ready') is True and data.get('model_version') == 'v6',
         'Kiểm tra npm.cmd run dev và AI_API_TARGET của Vite; khởi động lại Vite nếu vừa đổi cấu hình.'),
        ('FE → BE', args.frontend_port, '/api/v1/users/me/valuation-history', lambda status, data: status == 401 and data.get('code') == 'UNAUTHENTICATED',
         'Kiểm tra BE_API_TARGET của Vite và readiness BE. HTTP 502 thường là proxy chưa nối được BE.'),
    ]
    passed = True
    for label, local_port, path, valid, hint in checks:
        status, data = probe(f'http://127.0.0.1:{local_port}{path}')
        ok = valid(status, data)
        passed = passed and ok
        result = f'HTTP {status}' if status is not None else 'không kết nối được'
        print(f'{"OK" if ok else "CHƯA SẴN SÀNG"}: {label} — {result}')
        if not ok:
            print('  ' + hint)
    if passed:
        print('Kết nối demo sẵn sàng. HTTP 401 của lịch sử là đúng vì phép kiểm tra không gửi tài khoản/JWT.')
        print('Đây là kiểm tra kết nối; chưa xác nhận đăng nhập hoặc lưu kết quả của tài khoản cụ thể.')
    else:
        print('Không dừng tiến trình đang chiếm cổng. Nếu đổi cổng dịch vụ, cập nhật proxy và các tham số kiểm tra tương ứng.')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
