"""실험 입력·완료 기록을 원자적으로 보존한다."""

from __future__ import annotations

import fcntl
import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARMS = ("pine", "terra", "gemini")
TIMEFRAMES = ("1h", "4h", "1d")
PERIODS = (6, 12, 24)
SCENARIOS = ("baseline", "fees_x2", "slippage_x2", "funding_x2")
MODELS = {"terra": "gpt-5.6-terra", "gemini": "gemini-3.8-flash-high"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def identity(value: object) -> str:
    return sha(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    )


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )
    temporary.replace(path)


def immutable(path: Path, value: object) -> None:
    if path.exists():
        if read(path) != value:
            raise ValueError(f"동결 입력 변경을 거부합니다: {path}")
    else:
        write(path, value)


def run_dir(value: str | Path) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(ROOT / "runs"):
        raise ValueError("산출물은 현재 checkout의 runs/ 아래에만 저장합니다")
    path.mkdir(parents=True, exist_ok=True)
    return path


def checked_file(root: Path, relative: str, expected: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or sha(path.read_bytes()) != expected:
        raise ValueError("경로 또는 SHA256이 동결 입력과 다릅니다")
    return path


@contextmanager
def lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def cached(folder: Path, request: dict) -> dict | None:
    """중단된 LLM 호출은 완료로 간주하거나 조용히 재호출하지 않는다."""
    if (folder / "request.json").exists():
        immutable(folder / "request.json", request)
    else:
        return None
    if not (folder / "receipt.json").exists():
        return {"status": "interrupted", "job_hash": identity(request)}
    receipt = read(folder / "receipt.json")
    if receipt["job_hash"] != identity(request):
        raise ValueError("완료 기록의 요청 해시가 다릅니다")
    for name, digest in receipt["files"].items():
        checked_file(folder, name, digest)
    return receipt


def receipt(folder: Path, request: dict, status: str, **details) -> dict:
    result = {
        "job_hash": identity(request),
        "status": status,
        "finished_at": now(),
        **details,
        "files": {
            p.name: sha(p.read_bytes())
            for p in sorted(folder.iterdir())
            if p.is_file() and p.name not in {"receipt.json", ".lock"}
        },
    }
    write(folder / "receipt.json", result)
    return result
