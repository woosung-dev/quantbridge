"""실험 입력·완료 기록을 원자적으로 보존한다."""

from __future__ import annotations

import fcntl
import hashlib
import itertools
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
NATIVE_POLICY = {
    "account": "basic",
    "max_total_bars": 5000,
    "warmup_included": True,
    "history_request_mode": "bounded_ui",
}


def economic_cells_per_arm(frozen: dict, cohort: dict | None = None) -> int:
    """새6개월 계획만 선언한 전체 행렬을 검증하며 과거36셀 계약은 유지한다."""
    if "periods" not in frozen:
        return len(TIMEFRAMES) * len(PERIODS) * len(SCENARIOS)
    if (
        frozen.get("phase") != "full"
        or type(frozen["periods"]) is not list
        or frozen["periods"] != [6]
        or any(type(p) is not int for p in frozen["periods"])
    ):
        raise ValueError("명시 기간 계약은 full periods=[6]만 지원합니다")
    jobs = frozen.get("jobs", [])
    identifiers = list(dict.fromkeys(job["id"] for job in jobs))
    if cohort is not None:
        required_ids = [item["id"] for item in cohort["items"]]
        required_ids += [f"UNFILLED-{n:03}" for n in range(len(required_ids), cohort["target"])]
        if identifiers != required_ids:
            raise ValueError("명시6개월 계획의 원본 집합·순서가 동결 코호트와 다릅니다")
    expected = [
        {"id": identifier, "arm": arm, "timeframe": tf, "months": months, "scenario": scenario}
        for identifier, arm, tf, months, scenario in itertools.product(
            identifiers, ARMS, TIMEFRAMES, (6,), SCENARIOS
        )
    ]
    if (
        not identifiers
        or identity(jobs) != identity(expected)
        or type(frozen.get("expected_cells")) is not int
        or frozen["expected_cells"] != len(expected)
        or not set(frozen.get("artifacts", {})) <= set(identifiers)
        or any(
            identifier not in frozen.get("artifacts", {}) and not identifier.startswith("UNFILLED-")
            for identifier in identifiers
        )
    ):
        raise ValueError("명시6개월 계획은 누락·중복·사후필터 없는 전체 조건행렬이어야 합니다")
    return len(TIMEFRAMES) * len(SCENARIOS)


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def identity(value: object) -> str:
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
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
