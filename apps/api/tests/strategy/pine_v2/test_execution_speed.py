"""pine_v2 corpus 실행 속도 baseline과 상대비 회귀 가드."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
from copy import deepcopy
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd
import pytest

from tests.strategy.pine_v2._corpus import RUNNABLE_CORPUS

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_OHLCV_FROZEN = _CORPUS_DIR / "corpus_ohlcv_frozen.parquet"
_GOLDEN_METRICS_BASELINE = _CORPUS_DIR / "baseline_metrics.json"
_EXECUTION_SPEED_BASELINE = _CORPUS_DIR / "execution_speed_baseline.json"
_REGEN_ENV = "REGEN_EXECUTION_SPEED"
_RATIO_REGRESSION_LIMIT = 2.0


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_frozen_ohlcv() -> pd.DataFrame:
    """고정 parquet → DataFrame (run_backtest_v2 계약)."""
    ohlcv_df = pd.read_parquet(_OHLCV_FROZEN)
    if "timestamp" in ohlcv_df.columns:
        ohlcv_df = ohlcv_df.set_index("timestamp")
    return ohlcv_df


def _measure_corpora() -> dict[str, dict[str, float]]:
    """동일 OHLCV에서 7개 corpus의 두 실행 경로 시간을 기록한다."""
    from src.backtest.engine.v2_adapter import run_backtest_v2
    from src.strategy.pine_v2.compat import parse_and_run_v2

    ohlcv_df = _load_frozen_ohlcv()
    bars = len(ohlcv_df)
    measured: dict[str, dict[str, float]] = {}

    for corpus_id in RUNNABLE_CORPUS:
        source = (_CORPUS_DIR / f"{corpus_id}.pine").read_text(encoding="utf-8")

        started_at = perf_counter()
        outcome = run_backtest_v2(source, ohlcv_df)
        run_backtest_seconds = perf_counter() - started_at
        assert outcome.status == "ok" and outcome.result is not None, (
            f"{corpus_id}: run_backtest_v2 status={outcome.status} error={outcome.error}"
        )

        started_at = perf_counter()
        parse_and_run_v2(source, ohlcv_df, strict=False)
        parse_and_run_seconds = perf_counter() - started_at

        bars_per_second = bars / run_backtest_seconds
        measured[corpus_id] = {
            "run_backtest_seconds": run_backtest_seconds,
            "parse_and_run_seconds": parse_and_run_seconds,
            "bars_per_second": bars_per_second,
        }

    fastest_bars_per_second = max(item["bars_per_second"] for item in measured.values())
    for item in measured.values():
        item["ratio_to_fastest"] = fastest_bars_per_second / item["bars_per_second"]
    return measured


@cache
def _measured_corpora() -> dict[str, dict[str, float]]:
    return _measure_corpora()


def _python_minor() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _build_baseline(corpora: dict[str, dict[str, float]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "ohlcv_sha256": _file_sha256(_OHLCV_FROZEN),
        "bars": len(_load_frozen_ohlcv()),
        "machine": {
            "platform": platform.platform(),
            "python": _python_minor(),
        },
        "corpora": corpora,
    }


def _load_baseline() -> dict[str, Any]:
    assert _EXECUTION_SPEED_BASELINE.exists(), (
        "execution speed baseline이 없습니다. "
        f"{_REGEN_ENV}=1 uv run pytest tests/strategy/pine_v2/test_execution_speed.py -q 로 생성하세요."
    )
    return json.loads(_EXECUTION_SPEED_BASELINE.read_text(encoding="utf-8"))


def _write_baseline(baseline: dict[str, Any]) -> None:
    _EXECUTION_SPEED_BASELINE.write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _baseline_for_test() -> dict[str, Any]:
    if os.environ.get(_REGEN_ENV) == "1":
        baseline = _build_baseline(_measured_corpora())
        _write_baseline(baseline)
        return baseline
    return _load_baseline()


def _assert_ratios_match_bars_per_second(corpora: dict[str, dict[str, Any]], *, label: str) -> None:
    fastest_bars_per_second = max(float(item["bars_per_second"]) for item in corpora.values())
    for corpus_id, item in corpora.items():
        expected_ratio = fastest_bars_per_second / float(item["bars_per_second"])
        actual_ratio = float(item["ratio_to_fastest"])
        assert math.isclose(actual_ratio, expected_ratio, rel_tol=1e-9, abs_tol=1e-12), (
            f"{label} {corpus_id}: ratio_to_fastest={actual_ratio} 는 "
            f"bars_per_second에서 계산한 {expected_ratio}와 일치하지 않습니다"
        )


def _assert_relative_ratio_regression(
    measured_corpora: dict[str, dict[str, Any]], baseline: dict[str, Any]
) -> None:
    baseline_corpora = baseline["corpora"]
    assert set(measured_corpora) == set(baseline_corpora), (
        "속도 측정 corpus 집합이 baseline과 다릅니다: "
        f"measured={sorted(measured_corpora)}, baseline={sorted(baseline_corpora)}"
    )
    _assert_ratios_match_bars_per_second(measured_corpora, label="재측정")
    _assert_ratios_match_bars_per_second(baseline_corpora, label="baseline")

    for corpus_id in RUNNABLE_CORPUS:
        actual_ratio = float(measured_corpora[corpus_id]["ratio_to_fastest"])
        baseline_ratio = float(baseline_corpora[corpus_id]["ratio_to_fastest"])
        assert actual_ratio <= baseline_ratio * _RATIO_REGRESSION_LIMIT, (
            f"{corpus_id}: 상대비 회귀 — measured={actual_ratio:.3f}, "
            f"baseline={baseline_ratio:.3f}, "
            f"limit={baseline_ratio * _RATIO_REGRESSION_LIMIT:.3f}"
        )


def test_execution_speed_baseline_corpora_match_runnable_corpus() -> None:
    """baseline은 canonical 7개 corpus와 동일 OHLCV를 가리킨다."""
    baseline = _baseline_for_test()
    golden_metrics = json.loads(_GOLDEN_METRICS_BASELINE.read_text(encoding="utf-8"))

    assert baseline["schema_version"] == 1
    assert set(baseline["corpora"]) == set(RUNNABLE_CORPUS)
    assert baseline["ohlcv_sha256"] == _file_sha256(_OHLCV_FROZEN)
    assert baseline["ohlcv_sha256"] == golden_metrics["ohlcv_sha256"]
    assert baseline["bars"] == len(_load_frozen_ohlcv())


def test_execution_speed_relative_ratios_do_not_regress() -> None:
    """머신 성능이 아니라 같은 실행 안의 corpus 상대비만 회귀 가드한다."""
    _assert_relative_ratio_regression(_measured_corpora(), _baseline_for_test())


def test_execution_speed_ratio_guard_rejects_tampered_baseline() -> None:
    """양성 대조: baseline 내부 ratio 정합성이 깨지면 판정 함수가 거부한다."""
    baseline = _baseline_for_test()
    tampered_baseline = deepcopy(baseline)
    corpus_id = RUNNABLE_CORPUS[0]
    tampered_baseline["corpora"][corpus_id]["ratio_to_fastest"] *= 10

    with pytest.raises(AssertionError, match="bars_per_second에서 계산한"):
        _assert_relative_ratio_regression(baseline["corpora"], tampered_baseline)


def test_execution_speed_ratio_guard_rejects_relative_ratio_regression() -> None:
    """양성 대조: 정합한 측정값의 상대비가 허용 임계를 넘으면 거부한다."""
    baseline = _baseline_for_test()
    measured_corpora = deepcopy(baseline["corpora"])
    corpus_id = max(
        RUNNABLE_CORPUS,
        key=lambda item: float(baseline["corpora"][item]["ratio_to_fastest"]),
    )
    baseline_ratio = float(baseline["corpora"][corpus_id]["ratio_to_fastest"])
    assert baseline_ratio > 1.0, "상대비 회귀 양성 대조에는 fastest 외 corpus가 필요합니다"

    slowdown = _RATIO_REGRESSION_LIMIT + 1.0
    measured_corpora[corpus_id]["bars_per_second"] /= slowdown
    measured_corpora[corpus_id]["ratio_to_fastest"] *= slowdown

    with pytest.raises(AssertionError, match="상대비 회귀"):
        _assert_relative_ratio_regression(measured_corpora, baseline)
