"""Monte Carlo equity_percentiles 구조 & 단조성."""

from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine import run_monte_carlo


def test_equity_percentiles_keys_and_length() -> None:
    curve = [
        Decimal("10000"),
        Decimal("10100"),
        Decimal("10200"),
        Decimal("10300"),
    ]
    r = run_monte_carlo(curve, n_samples=50, seed=42)
    # JSON-safe string keys (FIX-4) — FE/Phase B API 와 key type 스펙 고정.
    assert set(r.equity_percentiles.keys()) == {"5", "25", "50", "75", "95"}
    for p, series in r.equity_percentiles.items():
        assert len(series) == len(curve), f"percentile {p} length mismatch"


def test_percentile_monotonic_at_each_bar() -> None:
    curve = [Decimal(str(10000 + 10 * i)) for i in range(20)]
    r = run_monte_carlo(curve, n_samples=200, seed=42)
    for i in range(len(curve)):
        assert r.equity_percentiles["5"][i] <= r.equity_percentiles["25"][i]
        assert r.equity_percentiles["25"][i] <= r.equity_percentiles["50"][i]
        assert r.equity_percentiles["50"][i] <= r.equity_percentiles["75"][i]
        assert r.equity_percentiles["75"][i] <= r.equity_percentiles["95"][i]
