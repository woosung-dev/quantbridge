"""pine_v2 백테스트 실행시간을 parse·execute·후처리 단계로 분해한다."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

import pytest

from tests.strategy.pine_v2.test_execution_speed import _CORPUS_DIR, _load_frozen_ohlcv

_BREAKDOWN_PATH = _CORPUS_DIR / "execution_stage_breakdown.json"
_MEASURED_CORPUS = ("s3_rsid", "s5_ema_trend")
_STAGE_KEYS = ("parse", "execute", "trades", "equity", "metrics")
_MIN_COVERAGE = 0.90
_MIN_DOMINANT_SHARE = 0.50


def _timed(
    stage_seconds: dict[str, float], stage: str, target: Callable[..., Any]
) -> Callable[..., Any]:
    """target의 누적 wall-clock 시간을 한 구간에 기록하는 monkeypatch wrapper."""

    @wraps(target)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started_at = perf_counter()
        try:
            return target(*args, **kwargs)
        finally:
            stage_seconds[stage] += perf_counter() - started_at

    return wrapper


def _measure_stage_breakdown(corpus_id: str) -> dict[str, Any]:
    """한 corpus의 adapter 경계별 누적 시간을 실측한다."""
    from src.backtest.engine import v2_adapter
    from src.strategy.pine_v2 import compat

    source = (_CORPUS_DIR / f"{corpus_id}.pine").read_text(encoding="utf-8")
    ohlcv_df = _load_frozen_ohlcv()
    stage_seconds: dict[str, float] = defaultdict(float)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            compat,
            "classify_script",
            _timed(stage_seconds, "parse", compat.classify_script),
        )
        monkeypatch.setattr(
            v2_adapter,
            "parse_and_run_v2",
            _timed(stage_seconds, "parse_and_run", v2_adapter.parse_and_run_v2),
        )
        monkeypatch.setattr(
            v2_adapter,
            "_build_raw_trades",
            _timed(stage_seconds, "trades", v2_adapter._build_raw_trades),
        )
        monkeypatch.setattr(
            v2_adapter,
            "_compute_equity_curve",
            _timed(stage_seconds, "equity", v2_adapter._compute_equity_curve),
        )
        monkeypatch.setattr(
            v2_adapter,
            "_compute_equity_extremes",
            _timed(stage_seconds, "equity", v2_adapter._compute_equity_extremes),
        )
        monkeypatch.setattr(
            v2_adapter,
            "_compute_metrics",
            _timed(stage_seconds, "metrics", v2_adapter._compute_metrics),
        )

        started_at = perf_counter()
        outcome = v2_adapter.run_backtest_v2(source, ohlcv_df)
        total_seconds = perf_counter() - started_at

    assert outcome.status == "ok" and outcome.result is not None, (
        f"{corpus_id}: run_backtest_v2 status={outcome.status} error={outcome.error}"
    )
    assert stage_seconds["parse_and_run"] >= stage_seconds["parse"], (
        f"{corpus_id}: parse 시간이 parse_and_run_v2 전체보다 큽니다; "
        "compat.classify_script 또는 adapter parse_and_run_v2 래퍼 경계를 확인하세요."
    )

    stages = {
        "parse": stage_seconds["parse"],
        "execute": stage_seconds["parse_and_run"] - stage_seconds["parse"],
        "trades": stage_seconds["trades"],
        "equity": stage_seconds["equity"],
        "metrics": stage_seconds["metrics"],
    }
    return {
        "total_seconds": total_seconds,
        "stages": stages,
        "unaccounted_seconds": total_seconds - sum(stages.values()),
    }


def _load_stage_breakdown() -> dict[str, dict[str, Any]]:
    assert _BREAKDOWN_PATH.exists(), f"단계별 실행시간 결과가 없습니다: {_BREAKDOWN_PATH}"
    return json.loads(_BREAKDOWN_PATH.read_text(encoding="utf-8"))


def _coverage(item: dict[str, Any]) -> float:
    return sum(item["stages"].values()) / item["total_seconds"]


def test_execution_stage_measurement_covers_most_runtime() -> None:
    """실측 래퍼가 총 시간의 대부분을 포착하는지 검증한다."""
    for corpus_id in _MEASURED_CORPUS:
        item = _measure_stage_breakdown(corpus_id)
        coverage = _coverage(item)
        assert coverage >= _MIN_COVERAGE, (
            f"{corpus_id}: 구간 합 커버리지={coverage:.3f} (< {_MIN_COVERAGE:.2f}); "
            f"unaccounted_seconds={item['unaccounted_seconds']:.3f}. "
            "누락 가능 경계: parse_and_run_v2 외부 준비·funding·state 추출·결과 조립."
        )


def test_execution_stage_breakdown_json_has_sufficient_coverage() -> None:
    """다음 단계가 읽는 JSON에 최소 두 corpus와 계측 커버리지를 보존한다."""
    breakdown = _load_stage_breakdown()

    assert set(_MEASURED_CORPUS).issubset(breakdown)
    for corpus_id in _MEASURED_CORPUS:
        item = breakdown[corpus_id]
        assert set(item["stages"]) == set(_STAGE_KEYS)
        assert all(seconds >= 0 for seconds in item["stages"].values())
        coverage = _coverage(item)
        assert coverage >= _MIN_COVERAGE, (
            f"{corpus_id}: JSON 구간 합 커버리지={coverage:.3f} (< {_MIN_COVERAGE:.2f}); "
            f"unaccounted_seconds={item['unaccounted_seconds']:.3f}. "
            "누락 가능 경계: parse_and_run_v2 외부 준비·funding·state 추출·결과 조립."
        )


def test_s3_rsid_json_records_a_dominant_stage() -> None:
    """가장 느린 corpus의 최대 구간이 단일 병목인지 JSON에서 명시한다."""
    item = _load_stage_breakdown()["s3_rsid"]
    dominant_stage, dominant_seconds = max(item["stages"].items(), key=lambda item: item[1])

    assert dominant_stage in _STAGE_KEYS
    assert dominant_seconds / item["total_seconds"] >= _MIN_DOMINANT_SHARE, (
        "s3_rsid: 최대 구간이 전체의 절반 미만이라 단일 병목이 아닙니다; "
        f"stage={dominant_stage}, share={dominant_seconds / item['total_seconds']:.3f}. "
        "실측값에 맞춰 임계와 index summary를 함께 갱신하세요."
    )
