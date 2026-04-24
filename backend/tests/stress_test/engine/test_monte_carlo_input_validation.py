"""Monte Carlo 입력 검증."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.stress_test.engine import run_monte_carlo


def test_empty_curve_raises() -> None:
    with pytest.raises(ValueError):
        run_monte_carlo([], n_samples=10)


def test_single_point_raises() -> None:
    with pytest.raises(ValueError):
        run_monte_carlo([Decimal("10000")], n_samples=10)


def test_two_points_ok() -> None:
    r = run_monte_carlo([Decimal("10000"), Decimal("10100")], n_samples=10, seed=1)
    assert r.samples == 10
