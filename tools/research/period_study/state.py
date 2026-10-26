"""원자적 체크포인트와 삭제하지 않는 실행 시도 기록."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(value) -> str:
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode())


def read(path: Path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) + "\n").encode()
    if path.suffix == ".gz":
        data = gzip.compress(data, mtime=0)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def immutable(path: Path, value) -> None:
    if path.exists():
        if read(path) != value:
            raise ValueError(f"동결 파일의 입력이 다릅니다: {path}")
    else:
        write(path, value)


def checked(root: Path, relative: str, expected: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("원자료 경로가 연구 루트 밖이거나 파일이 없습니다")
    if sha(path.read_bytes()) != expected:
        raise ValueError(f"원자료 SHA가 다릅니다: {relative}")
    return path


@contextmanager
def lock(path: Path):
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
