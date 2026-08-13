# Monte Carlo 음수 equity 처리 회귀 테스트 (BL-150 fix)
from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine.monte_carlo import run_monte_carlo

_SANE_THRESHOLD = 1e9  # ci 값이 10억 미만이면 sign-flip 폭발 없음으로 간주


def _equity(values: list[float]) -> list[Decimal]:
    return [Decimal(str(v)) for v in values]


def test_negative_equity_ci_does_not_explode() -> None:
    """음수 equity를 포함하는 전략에서 CI 값이 조 단위로 폭발하지 않아야 한다."""
    curve = _equity([10_000, 8_000, 5_000, 1_000, -5_000, -15_000, -20_000])
    result = run_monte_carlo(curve, n_samples=200, seed=42)
    assert abs(float(result.ci_upper_95)) < _SANE_THRESHOLD, (
        f"ci_upper_95 exploded: {result.ci_upper_95}"
    )
    assert abs(float(result.ci_lower_95)) < _SANE_THRESHOLD, (
        f"ci_lower_95 exploded: {result.ci_lower_95}"
    )


def test_negative_equity_percentiles_do_not_explode() -> None:
    """음수 equity 구간이 있을 때 per-bar percentile 시계열이 폭발하지 않아야 한다."""
    curve = _equity([10_000, 7_000, 3_000, -2_000, -8_000, -12_000])
    result = run_monte_carlo(curve, n_samples=200, seed=42)
    for key, series in result.equity_percentiles.items():
        for i, v in enumerate(series):
            assert abs(float(v)) < _SANE_THRESHOLD, (
                f"p{key}[{i}] exploded: {v}"
            )


def test_all_negative_equity_is_handled() -> None:
    """전 구간 음수 equity도 에러 없이 처리되어야 한다."""
    curve = _equity([10_000, -1_000, -5_000, -10_000])
    result = run_monte_carlo(curve, n_samples=100, seed=42)
    assert result.samples == 100
    assert abs(float(result.ci_upper_95)) < _SANE_THRESHOLD
