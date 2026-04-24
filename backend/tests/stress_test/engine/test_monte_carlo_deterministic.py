"""Monte Carlo 결정성: 동일 seed → 동일 결과, 다른 seed → 다른 결과."""

from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine import run_monte_carlo


def test_same_seed_produces_same_result() -> None:
    curve = [
        Decimal("10000"),
        Decimal("10100"),
        Decimal("10050"),
        Decimal("10200"),
        Decimal("10300"),
    ]
    r1 = run_monte_carlo(curve, n_samples=100, seed=42)
    r2 = run_monte_carlo(curve, n_samples=100, seed=42)
    assert r1.samples == r2.samples == 100
    assert r1.ci_lower_95 == r2.ci_lower_95
    assert r1.ci_upper_95 == r2.ci_upper_95
    assert r1.median_final_equity == r2.median_final_equity
    assert r1.max_drawdown_mean == r2.max_drawdown_mean
    assert r1.max_drawdown_p95 == r2.max_drawdown_p95
    assert r1.equity_percentiles == r2.equity_percentiles


def test_different_seed_produces_different_result() -> None:
    # SDD 원문은 3-point curve 였으나 returns 2 개만으론 seed 간 bootstrap 표본이
    # 자주 동일해져 flaky — return 분포를 5 개 이상으로 확장해 결정성 invariant 를 안정화.
    curve = [
        Decimal("10000"),
        Decimal("10050"),
        Decimal("10120"),
        Decimal("9980"),
        Decimal("10200"),
        Decimal("10350"),
    ]
    r1 = run_monte_carlo(curve, n_samples=100, seed=42)
    r2 = run_monte_carlo(curve, n_samples=100, seed=43)
    # 최소한 median 또는 ci 중 하나는 달라야 함 (확률적으로 거의 확실)
    assert (
        r1.median_final_equity != r2.median_final_equity
        or r1.ci_lower_95 != r2.ci_lower_95
    )
