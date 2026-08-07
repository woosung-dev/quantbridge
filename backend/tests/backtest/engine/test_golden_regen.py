"""`scripts/regen_golden.py` 계약 시험 + 커밋된 golden 의 필드 커버리지.

★키 **집합**과 **바이트 동일성**만 본다 — `expected.json` 의 키 정렬 순서만 바뀌어도
이 시험은 green 이어야 한다(음성 대조 N).

★`test_regen_roundtrip_is_stable` 은 실제로 golden 을 두 번 덮어쓴다. 원본을 바이트로
백업하고 `finally` 에서 복원한다. 프로세스가 강제 종료되면 워킹 트리가 오염될 수 있고,
그때 복구는 `git checkout -- backend/tests/backtest/engine/golden` 이다.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.backtest.engine import types as engine_types
from src.backtest.engine.types import BacktestMetrics

BACKEND_DIR = Path(__file__).resolve().parents[3]
SCRIPT = BACKEND_DIR / "scripts" / "regen_golden.py"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

requires_script = pytest.mark.skipif(
    not SCRIPT.exists(),
    reason=(
        "scripts/regen_golden.py 미구현 — 파일이 생기면 자동으로 켜진다. "
        "FileNotFoundError 로 red 를 만드는 것은 판별력 0이라 skip 으로 처리한다."
    ),
)


def _cases() -> list[Path]:
    """케이스 = `strategy.pine` 과 `ohlcv.csv` 가 **둘 다** 있는 디렉터리 (계약 §3.2)."""
    if not GOLDEN_DIR.is_dir():
        return []
    return sorted(
        d
        for d in GOLDEN_DIR.iterdir()
        if d.is_dir() and (d / "strategy.pine").is_file() and (d / "ohlcv.csv").is_file()
    )


def _expected_files() -> list[Path]:
    return [d / "expected.json" for d in _cases() if (d / "expected.json").is_file()]


def _snapshot(paths: list[Path]) -> dict[str, tuple[int, str]]:
    return {
        str(p): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths
    }


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )


def _scalar_field_names(cls: type) -> set[str]:
    """`dataclasses.fields()` 로 유도한다 — 필드명을 시험에 하드코딩하지 않는다.

    list 형(`monthly_returns` 계열)과 중첩 dataclass 형(`per_side` 계열)을 뺀 나머지.
    """
    return {f.name for f in dataclasses.fields(cls) if _field_kind(f) == "scalar"}


def _field_kind(field: dataclasses.Field) -> str:
    annotation = field.type if isinstance(field.type, str) else str(field.type)
    head = annotation.split("|")[0].strip()
    if head.startswith("list["):
        return "list"
    resolved = getattr(engine_types, head, None)
    if resolved is not None and dataclasses.is_dataclass(resolved):
        return "nested"
    return "scalar"


@requires_script
def test_regen_requires_confirm_flag() -> None:
    """`--confirm` 없으면 종료 코드 != 0 이고 **파일을 하나도 건드리지 않는다**."""
    expected = _expected_files()
    assert expected, f"golden 케이스가 없다 — {GOLDEN_DIR} 에 strategy.pine + ohlcv.csv 쌍이 필요"

    before = _snapshot(expected)
    proc = _run()
    after = _snapshot(expected)

    assert proc.returncode != 0, (
        f"--confirm 없이 돌렸는데 exit={proc.returncode} — 재생성은 명시 승인 없이 되면 안 된다.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    changed = [p for p in before if before[p] != after[p]]
    assert not changed, (
        f"--confirm 없이 돌렸는데 파일이 바뀌었다: {changed} — "
        f"exit code 만 1 로 두고 쓰기는 그대로 한 구현이다"
    )


@requires_script
def test_regen_check_mode_writes_nothing() -> None:
    """`--check` 는 비교만 한다 — 내용도 mtime 도 바뀌면 안 된다."""
    expected = _expected_files()
    assert expected, f"golden 케이스가 없다 — {GOLDEN_DIR}"

    before = _snapshot(expected)
    proc = _run("--check")
    after = _snapshot(expected)

    changed = [p for p in before if before[p] != after[p]]
    assert not changed, (
        f"--check 가 파일을 썼다: {changed} — 비교 전용 모드가 워킹 트리를 바꾸면 "
        f"'차이 없음' 판정이 자기 자신을 증명하게 된다.\nstdout:\n{proc.stdout}"
    )


@requires_script
def test_regen_roundtrip_is_stable() -> None:
    """2회 재생성 산출이 byte 동일 — 타임스탬프·set 순회 순서가 새면 여기서 잡힌다."""
    cases = _cases()
    assert cases, f"golden 케이스가 없다 — {GOLDEN_DIR}"
    expected = [d / "expected.json" for d in cases]

    backup = {p: (p.read_bytes() if p.is_file() else None) for p in expected}
    try:
        first_proc = _run("--confirm")
        assert first_proc.returncode == 0, (
            f"--confirm 1회차 exit={first_proc.returncode}\n"
            f"stdout:\n{first_proc.stdout}\nstderr:\n{first_proc.stderr}"
        )
        first = {p: p.read_bytes() for p in expected}

        second_proc = _run("--confirm")
        assert second_proc.returncode == 0, (
            f"--confirm 2회차 exit={second_proc.returncode}\n"
            f"stdout:\n{second_proc.stdout}\nstderr:\n{second_proc.stderr}"
        )
        second = {p: p.read_bytes() for p in expected}

        unstable = [str(p) for p in expected if first[p] != second[p]]
        assert not unstable, (
            f"2회 재생성 산출이 다르다: {unstable} — 생성 시각·해시 seed·집합 순회 순서 등 "
            f"비결정 값이 파일에 샜다. 이러면 --check 가 영원히 red 다"
        )
    finally:
        for path, blob in backup.items():
            if blob is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(blob)


def test_golden_expected_metrics_cover_all_scalar_fields() -> None:
    """커밋된 `expected.json` 의 `backtest.metrics` 키 집합 ⊇ `BacktestMetrics` 스칼라 전량.

    ★키 **집합** 비교라 정렬 순서 변경에는 반응하지 않는다.
    """
    scalars = _scalar_field_names(BacktestMetrics)
    assert scalars, "BacktestMetrics 에서 스칼라 필드를 하나도 못 유도했다 — 분류 로직 결함"

    checked = 0
    for case in _cases():
        path = case / "expected.json"
        assert path.is_file(), f"{case.name}: expected.json 이 없다 (케이스인데 스냅샷 부재)"
        doc = json.loads(path.read_text())

        if doc.get("status") != "ok":
            # 실행이 status=ok 가 아닌 케이스는 metrics 자체가 없을 수 있다.
            continue

        backtest = doc.get("backtest")
        assert isinstance(backtest, dict), (
            f"{case.name}: expected.json 에 'backtest' 객체가 없다 (got {type(backtest).__name__})"
        )
        assert "trades" not in backtest, (
            f"{case.name}: backtest.trades 가 남아 있다 — 거래 단위는 trust-layer baseline 소유다"
        )

        metrics = backtest.get("metrics")
        assert isinstance(metrics, dict), (
            f"{case.name}: backtest.metrics 가 dict 가 아니다 (got {type(metrics).__name__})"
        )

        missing = scalars - set(metrics)
        assert not missing, (
            f"{case.name}: backtest.metrics 에서 {len(missing)}개 스칼라 필드가 빠졌다 — "
            f"{sorted(missing)}. BacktestMetrics 스칼라 전량({len(scalars)}개)을 담아야 한다"
        )
        checked += 1

    assert checked >= 1, (
        f"status=ok 인 golden 케이스가 하나도 없다 (케이스 {len(_cases())}개) — "
        f"이 시험은 아무것도 재지 못했다"
    )
