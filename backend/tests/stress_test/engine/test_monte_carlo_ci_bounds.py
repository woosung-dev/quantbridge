"""Monte Carlo CI / drawdown 범위 불변."""

from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine import run_monte_carlo


def test_ci_lower_le_median_le_ci_upper() -> None:
    curve = [Decimal(str(10000 * (1 + 0.001 * i))) for i in range(100)]
    r = run_monte_carlo(curve, n_samples=500, seed=42)
    assert r.ci_lower_95 <= r.median_final_equity <= r.ci_upper_95


def test_max_drawdown_in_valid_range() -> None:
    curve = [
        Decimal("10000"),
        Decimal("9000"),
        Decimal("11000"),
        Decimal("8000"),
        Decimal("12000"),
    ]
    r = run_monte_carlo(curve, n_samples=200, seed=42)
    assert Decimal("0") <= r.max_drawdown_mean <= Decimal("1")
    assert r.max_drawdown_mean <= r.max_drawdown_p95
