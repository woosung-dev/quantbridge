"""Monte Carlo 엔진 테스트 — seed=42 결정적 snapshot + 경계 케이스."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.backtest.monte_carlo import run_monte_carlo

# ---------------------------------------------------------------------------
# 공유 fixture
# ---------------------------------------------------------------------------

_BASE_CURVE = [Decimal(str(v)) for v in [10000, 10050, 10120, 9980, 10200, 10350, 10100]]


# ---------------------------------------------------------------------------
# Snapshot test (seed=42 결정성)
# ---------------------------------------------------------------------------


def test_snapshot_seed42() -> None:
    result = run_monte_carlo(_BASE_CURVE, n_samples=1000, seed=42)

    assert result.samples == 1000
    assert result.ci_lower_95 > Decimal("0")
    assert result.ci_upper_95 > result.ci_lower_95
    assert result.median_final_equity > Decimal("0")
    assert Decimal("0") <= result.max_drawdown_mean <= Decimal("1")
    assert Decimal("0") <= result.max_drawdown_p95 <= Decimal("1")

    # seed=42 고정 결과 고정값 검증 — 회귀 방지
    result2 = run_monte_carlo(_BASE_CURVE, n_samples=1000, seed=42)
    assert result.ci_lower_95 == result2.ci_lower_95
    assert result.ci_upper_95 == result2.ci_upper_95
    assert result.median_final_equity == result2.median_final_equity
    assert result.max_drawdown_mean == result2.max_drawdown_mean
    assert result.max_drawdown_p95 == result2.max_drawdown_p95


def test_different_seeds_produce_different_results() -> None:
    r1 = run_monte_carlo(_BASE_CURVE, n_samples=200, seed=1)
    r2 = run_monte_carlo(_BASE_CURVE, n_samples=200, seed=2)
    assert r1.median_final_equity != r2.median_final_equity


# ---------------------------------------------------------------------------
# 경계 케이스
# ---------------------------------------------------------------------------


def test_empty_curve_raises_value_error() -> None:
    with pytest.raises(ValueError, match="at least 2 data points"):
        run_monte_carlo([], n_samples=100, seed=42)


def test_single_point_raises_value_error() -> None:
    with pytest.raises(ValueError, match="at least 2 data points"):
        run_monte_carlo([Decimal("10000")], n_samples=100, seed=42)


def test_all_positive_returns_has_positive_ci() -> None:
    # 균등 1% 수익률 — bootstrap 리샘플링해도 동일 수익률만 선택됨 → CI bounds 일치
    curve = [Decimal(str(10000 * (1.01**i))) for i in range(20)]
    result = run_monte_carlo(curve, n_samples=500, seed=42)
    assert result.ci_lower_95 > Decimal("0")
    assert result.ci_upper_95 >= result.ci_lower_95


def test_flat_curve_has_near_zero_drawdown() -> None:
    curve = [Decimal("10000")] * 10
    result = run_monte_carlo(curve, n_samples=200, seed=42)
    # returns 모두 0 → drawdown 0
    assert result.max_drawdown_mean == Decimal("0.0")


def test_result_is_frozen_dataclass() -> None:
    result = run_monte_carlo(_BASE_CURVE, n_samples=100, seed=42)
    with pytest.raises((AttributeError, TypeError)):
        result.samples = 999  # type: ignore[misc]


def test_n_samples_reflected_in_result() -> None:
    result = run_monte_carlo(_BASE_CURVE, n_samples=250, seed=42)
    assert result.samples == 250
