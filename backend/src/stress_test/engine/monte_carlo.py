"""Monte Carlo bootstrap 시뮬레이션.

기존 backtest/monte_carlo.py stub 의 bootstrap 로직을 이관하고 fan-chart 용
equity_percentiles 시계열을 추가한다. seed 고정으로 pytest snapshot 가능.

Bootstrap resampling:
  - 시작 자본 포함 시계열에서 일별 수익률(simple return)을 계산
  - 리샘플링(replace=True) 해 N 경로의 누적 equity curve 재구성
  - seed=42 고정으로 결정적 결과 보장 (pytest snapshot)
  - per-bar percentile (p5/p25/p50/p75/p95) 시계열도 함께 반환 → fan chart
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    # fan chart 용 — key=percentile 문자열("5"/"25"/"50"/"75"/"95"), value=시계열
    # (len = len(equity_curve)). JSON 직렬화 시 int → str 변환을 BE 에 고정해
    # Phase B API / FE 가 key type 에 대해 동일한 스펙을 공유한다.
    equity_percentiles: dict[str, list[Decimal]] = field(default_factory=dict)


def _max_drawdown(equity: np.ndarray[tuple[int], np.dtype[np.float64]]) -> float:
    """단일 equity 시계열의 최대 낙폭 (0~1 비율)."""
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak == 0, 1.0, peak)
    return float(-dd.min())


def _to_decimal(v: float) -> Decimal:
    return Decimal(str(round(v, 8)))


def run_monte_carlo(
    equity_curve: list[Decimal],
    *,
    n_samples: int = 1000,
    seed: int = 42,
) -> MonteCarloResult:
    """Bootstrap Monte Carlo.

    Args:
        equity_curve: 시작 자본 포함 시계열. 길이 ≥ 2.
        n_samples: 리샘플링 횟수 (기본 1000).
        seed: numpy RNG 시드 (기본 42). 동일 입력+seed → 동일 결과.

    Raises:
        ValueError: equity_curve 길이 < 2.
    """
    if len(equity_curve) < 2:
        raise ValueError("equity_curve must have at least 2 data points")

    eq = np.array([float(v) for v in equity_curve], dtype=np.float64)
    # simple return (bar-to-bar)
    returns = np.diff(eq) / np.where(eq[:-1] == 0, 1.0, eq[:-1])

    rng = np.random.default_rng(seed=seed)
    n_periods = len(returns)
    total_bars = n_periods + 1  # initial + simulated
    initial = eq[0]

    # 모든 simulated path 를 2D 로 적재 (fan chart 용)
    all_paths = np.empty((n_samples, total_bars), dtype=np.float64)
    final_equities = np.empty(n_samples, dtype=np.float64)
    max_drawdowns = np.empty(n_samples, dtype=np.float64)

    for i in range(n_samples):
        sampled = rng.choice(returns, size=n_periods, replace=True)
        simulated = initial * np.cumprod(1 + sampled)
        simulated = np.concatenate([[initial], simulated])
        all_paths[i] = simulated
        final_equities[i] = simulated[-1]
        max_drawdowns[i] = _max_drawdown(simulated)

    # per-bar percentile (축 0 = samples, 축 1 = bars) — JSON 안전한 string key.
    percentiles: dict[str, list[Decimal]] = {
        str(p): [_to_decimal(float(v)) for v in np.percentile(all_paths, p, axis=0)]
        for p in (5, 25, 50, 75, 95)
    }

    return MonteCarloResult(
        samples=n_samples,
        ci_lower_95=_to_decimal(float(np.percentile(final_equities, 5))),
        ci_upper_95=_to_decimal(float(np.percentile(final_equities, 95))),
        median_final_equity=_to_decimal(float(np.median(final_equities))),
        max_drawdown_mean=_to_decimal(float(np.mean(max_drawdowns))),
        max_drawdown_p95=_to_decimal(float(np.percentile(max_drawdowns, 95))),
        equity_percentiles=percentiles,
    )
