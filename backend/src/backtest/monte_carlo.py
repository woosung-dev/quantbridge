"""Monte Carlo bootstrap 시뮬레이션 — Sprint 9-1 초안.

Bootstrap resampling:
  - 일별 수익률(daily returns)을 1000회 리샘플링해 누적 equity curve 재구성
  - seed=42 고정으로 결정적 결과 보장 (pytest snapshot 테스트 가능)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy as np


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    samples: int
    ci_lower_95: Decimal  # 5th percentile final equity
    ci_upper_95: Decimal  # 95th percentile final equity
    median_final_equity: Decimal
    max_drawdown_mean: Decimal
    max_drawdown_p95: Decimal


def _max_drawdown(equity: np.ndarray) -> float:
    """단일 equity 시계열의 최대 낙폭 (0~1 비율)."""
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak == 0, 1.0, peak)
    return float(-dd.min())


def run_monte_carlo(
    equity_curve: list[Decimal],
    *,
    n_samples: int = 1000,
    seed: int = 42,
) -> MonteCarloResult:
    """Bootstrap Monte Carlo.

    equity_curve: 시작 자본 포함 시계열 (ex: [10000, 10050, 10120, ...]).
    n_samples: 리샘플링 횟수 (기본 1000).
    seed: numpy RNG 시드. 재현성 보장.
    """
    if len(equity_curve) < 2:
        raise ValueError("equity_curve must have at least 2 data points")

    eq = np.array([float(v) for v in equity_curve], dtype=np.float64)

    # 일별 수익률 (log-return 대신 simple return — 소규모 변동에 동등)
    returns = np.diff(eq) / np.where(eq[:-1] == 0, 1.0, eq[:-1])

    rng = np.random.default_rng(seed=seed)
    n_periods = len(returns)
    initial = eq[0]

    final_equities = np.empty(n_samples, dtype=np.float64)
    max_drawdowns = np.empty(n_samples, dtype=np.float64)

    for i in range(n_samples):
        sampled = rng.choice(returns, size=n_periods, replace=True)
        simulated = initial * np.cumprod(1 + sampled)
        simulated = np.concatenate([[initial], simulated])
        final_equities[i] = simulated[-1]
        max_drawdowns[i] = _max_drawdown(simulated)

    def _d(v: float) -> Decimal:
        return Decimal(str(round(v, 8)))

    return MonteCarloResult(
        samples=n_samples,
        ci_lower_95=_d(float(np.percentile(final_equities, 5))),
        ci_upper_95=_d(float(np.percentile(final_equities, 95))),
        median_final_equity=_d(float(np.median(final_equities))),
        max_drawdown_mean=_d(float(np.mean(max_drawdowns))),
        max_drawdown_p95=_d(float(np.percentile(max_drawdowns, 95))),
    )
