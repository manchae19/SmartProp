"""Small IO boundary for immutable research snapshots and owned writer locks."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import uuid


def atomic_json(path, value):
    path = Path(path)
    temporary = path.parent / ('.pending_' + uuid.uuid4().hex)
    try:
        temporary.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf8'))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def writer_lock(root, name='writer.lock'):
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    token = uuid.uuid4().hex
    created = None
    published = False
    try:
        try:
            stream = path.open('x', encoding='utf8')
        except FileExistsError as exc:
            raise ValueError('Another writer owns the lock') from exc
        with stream:
            created = os.fstat(stream.fileno())
            json.dump(dict(pid=os.getpid(), owner=token), stream)
        published = True
        yield
    finally:
        if created is not None:
            try:
                current = path.stat()
                if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                    try:
                        owned = json.loads(path.read_text(encoding='utf8')).get('owner') == token
                    except json.JSONDecodeError:
                        owned = not published
                    if owned:
                        path.unlink()
            except FileNotFoundError:
                pass
