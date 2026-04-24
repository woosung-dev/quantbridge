# H2 Sprint 9 · Phase A — Monte Carlo + Walk-Forward 엔진

**Branch:** `feat/h2s9-stress-engine` (from `stage/h2-sprint9` from `main`)
**Date:** 2026-04-24
**Master plan:** `/Users/woosung/.claude/plans/h2-sprint-9-validated-ember.md`
**Baseline:** main `b54c4f8`, backend 985 green (Stage 2c 2차 SLO TL-E-5 GREEN 이후)
**Worktree isolation:** YES (Agent 디스패치 시 `isolation=worktree`)

## Scope (고정)

순수 계산 엔진만. DB / HTTP / Celery 없음.

1. **Monte Carlo bootstrap** — seed-deterministic, 1000 샘플 기본, equity percentile fan (p5/p25/p50/p75/p95) 시계열 추가.
2. **Walk-Forward Analysis** — rolling train/test window, fold 별 IS/OOS 수익, degradation ratio. No-lookahead 불변 강제.
3. **기존 stub 이관** — `backend/src/backtest/monte_carlo.py` (77 줄) → `backend/src/stress_test/engine/monte_carlo.py` 로 이동 + 확장. `backend/tests/backtest/test_monte_carlo.py` → `backend/tests/stress_test/engine/` 로 이전. 원본은 삭제.
4. **Coverage** 신규 코드 90%+ (pytest-cov).

## Out of scope

- SQLModel / Alembic / Celery task / router (→ Phase B)
- Frontend UI (→ Phase C)
- Prometheus metric (→ Phase D)
- Parameter stability analysis (→ Sprint 10)
- Numba/Cython 최적화 (Sprint 10 이후)

## 파일 변경

### 1. `backend/src/stress_test/__init__.py` (신규)

```python
"""stress_test 도메인. Router / Service / Repository 3-Layer."""
```

### 2. `backend/src/stress_test/engine/__init__.py` (신규 디렉토리)

```python
"""stress_test 순수 계산 엔진 — DB/HTTP 의존 없음."""

from src.stress_test.engine.monte_carlo import MonteCarloResult, run_monte_carlo
from src.stress_test.engine.walk_forward import (
    WalkForwardFold,
    WalkForwardResult,
    run_walk_forward,
)

__all__ = [
    "MonteCarloResult",
    "run_monte_carlo",
    "WalkForwardFold",
    "WalkForwardResult",
    "run_walk_forward",
]
```

### 3. `backend/src/stress_test/engine/monte_carlo.py` (신규 — 이관 + 확장)

```python
"""Monte Carlo bootstrap 시뮬레이션.

기존 backtest/monte_carlo.py stub 의 bootstrap 로직을 이관하고 fan-chart 용
equity_percentiles 시계열을 추가한다. seed 고정으로 pytest snapshot 가능.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    samples: int
    ci_lower_95: Decimal
    ci_upper_95: Decimal
    median_final_equity: Decimal
    max_drawdown_mean: Decimal
    max_drawdown_p95: Decimal
    # fan chart 용 — key=percentile(5/25/50/75/95), value=시계열 (len = len(equity_curve))
    equity_percentiles: dict[int, list[Decimal]] = field(default_factory=dict)


def _max_drawdown(equity: np.ndarray) -> float:
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
    # simple return (일별)
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

    # per-bar percentile (축 0 = samples, 축 1 = bars)
    percentiles = {
        p: [_to_decimal(float(v)) for v in np.percentile(all_paths, p, axis=0)]
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
```

### 4. `backend/src/stress_test/engine/walk_forward.py` (신규)

```python
"""Walk-Forward Analysis — rolling IS/OOS 백테스트.

각 fold 에서 backtest.engine.run_backtest 호출 → IS/OOS 수익률 산출 → degradation ratio.
No-lookahead 는 test_start > train_end 불변으로 보장.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import pandas as pd

from src.backtest.engine import run_backtest  # pine_v2 기반 (v2_adapter.run_backtest_v2 alias)
from src.backtest.engine.types import BacktestConfig


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold_index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    in_sample_return: Decimal
    out_of_sample_return: Decimal
    oos_sharpe: Decimal | None
    num_trades_oos: int


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    folds: list[WalkForwardFold]
    aggregate_oos_return: Decimal  # 평균
    degradation_ratio: Decimal     # avg(IS) / avg(OOS). >1 = OOS 악화. OOS=0 이면 Decimal("Infinity")


def run_walk_forward(
    pine_source: str,
    ohlcv: pd.DataFrame,
    *,
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
    backtest_config: BacktestConfig | None = None,
    max_folds: int = 20,
) -> WalkForwardResult:
    """Rolling walk-forward. OHLCV index 는 tz-aware DatetimeIndex 여야 한다.

    Args:
        pine_source: strategy pine 소스.
        ohlcv: `run_backtest` 와 동일 shape (open/high/low/close/volume + tz-aware index).
        train_bars: 학습 구간 바 수.
        test_bars: 검증 구간 바 수.
        step_bars: rolling step. None → test_bars (non-overlapping).
        backtest_config: None → BacktestConfig() 기본.
        max_folds: 상한. 초과 fold 는 drop.

    Raises:
        ValueError: train_bars+test_bars > len(ohlcv), 또는 train_bars ≤ 0, test_bars ≤ 0.
    """
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    if train_bars + test_bars > len(ohlcv):
        raise ValueError(
            f"train_bars + test_bars ({train_bars + test_bars}) "
            f"exceeds ohlcv length ({len(ohlcv)})"
        )
    step = step_bars if step_bars is not None else test_bars
    if step <= 0:
        raise ValueError("step_bars must be positive")

    cfg = backtest_config or BacktestConfig()

    folds: list[WalkForwardFold] = []
    idx = 0
    fold_index = 0
    n = len(ohlcv)
    while idx + train_bars + test_bars <= n and fold_index < max_folds:
        train_slice = ohlcv.iloc[idx : idx + train_bars]
        test_slice = ohlcv.iloc[idx + train_bars : idx + train_bars + test_bars]

        is_outcome = run_backtest(pine_source, train_slice, cfg)
        oos_outcome = run_backtest(pine_source, test_slice, cfg)

        if is_outcome.status != "ok" or is_outcome.result is None:
            raise ValueError(
                f"IS backtest failed at fold {fold_index}: status={is_outcome.status}"
            )
        if oos_outcome.status != "ok" or oos_outcome.result is None:
            raise ValueError(
                f"OOS backtest failed at fold {fold_index}: status={oos_outcome.status}"
            )

        folds.append(
            WalkForwardFold(
                fold_index=fold_index,
                train_start=train_slice.index[0].to_pydatetime(),
                train_end=train_slice.index[-1].to_pydatetime(),
                test_start=test_slice.index[0].to_pydatetime(),
                test_end=test_slice.index[-1].to_pydatetime(),
                in_sample_return=is_outcome.result.metrics.total_return,
                out_of_sample_return=oos_outcome.result.metrics.total_return,
                oos_sharpe=oos_outcome.result.metrics.sharpe_ratio,
                num_trades_oos=oos_outcome.result.metrics.num_trades,
            )
        )
        idx += step
        fold_index += 1

    if not folds:
        raise ValueError("no folds produced — check train/test/step parameters")

    # Decimal-first 합산 (Sprint 4 D8)
    is_sum = sum((f.in_sample_return for f in folds), start=Decimal("0"))
    oos_sum = sum((f.out_of_sample_return for f in folds), start=Decimal("0"))
    is_avg = is_sum / Decimal(len(folds))
    oos_avg = oos_sum / Decimal(len(folds))

    degradation: Decimal
    if oos_avg == 0:
        degradation = Decimal("Infinity") if is_avg != 0 else Decimal("1")
    else:
        degradation = is_avg / oos_avg

    return WalkForwardResult(
        folds=folds,
        aggregate_oos_return=oos_avg,
        degradation_ratio=degradation,
    )
```

### 5. 삭제

- `backend/src/backtest/monte_carlo.py` — `git rm`
- `backend/tests/backtest/test_monte_carlo.py` — `git rm` (동일 로직 테스트는 `tests/stress_test/engine/` 로 이전)

## Tests (RED → GREEN → REFACTOR)

### `backend/tests/stress_test/__init__.py` + `engine/__init__.py` — 빈 파일

### `backend/tests/stress_test/engine/test_monte_carlo_deterministic.py`

```python
from decimal import Decimal
from src.stress_test.engine import run_monte_carlo


def test_same_seed_produces_same_result():
    curve = [Decimal("10000"), Decimal("10100"), Decimal("10050"), Decimal("10200"), Decimal("10300")]
    r1 = run_monte_carlo(curve, n_samples=100, seed=42)
    r2 = run_monte_carlo(curve, n_samples=100, seed=42)
    assert r1.samples == r2.samples == 100
    assert r1.ci_lower_95 == r2.ci_lower_95
    assert r1.ci_upper_95 == r2.ci_upper_95
    assert r1.median_final_equity == r2.median_final_equity
    assert r1.max_drawdown_mean == r2.max_drawdown_mean
    assert r1.max_drawdown_p95 == r2.max_drawdown_p95
    assert r1.equity_percentiles == r2.equity_percentiles


def test_different_seed_produces_different_result():
    curve = [Decimal("10000"), Decimal("10050"), Decimal("10120")]
    r1 = run_monte_carlo(curve, n_samples=100, seed=42)
    r2 = run_monte_carlo(curve, n_samples=100, seed=43)
    # 최소한 median 또는 ci 중 하나는 달라야 함 (확률적으로 거의 확실)
    assert r1.median_final_equity != r2.median_final_equity or r1.ci_lower_95 != r2.ci_lower_95
```

### `backend/tests/stress_test/engine/test_monte_carlo_ci_bounds.py`

```python
from decimal import Decimal
from src.stress_test.engine import run_monte_carlo


def test_ci_lower_le_median_le_ci_upper():
    curve = [Decimal(str(10000 * (1 + 0.001 * i))) for i in range(100)]
    r = run_monte_carlo(curve, n_samples=500, seed=42)
    assert r.ci_lower_95 <= r.median_final_equity <= r.ci_upper_95


def test_max_drawdown_in_valid_range():
    curve = [Decimal("10000"), Decimal("9000"), Decimal("11000"), Decimal("8000"), Decimal("12000")]
    r = run_monte_carlo(curve, n_samples=200, seed=42)
    assert Decimal("0") <= r.max_drawdown_mean <= Decimal("1")
    assert r.max_drawdown_mean <= r.max_drawdown_p95
```

### `backend/tests/stress_test/engine/test_monte_carlo_percentiles_shape.py`

```python
from decimal import Decimal
from src.stress_test.engine import run_monte_carlo


def test_equity_percentiles_keys_and_length():
    curve = [Decimal("10000"), Decimal("10100"), Decimal("10200"), Decimal("10300")]
    r = run_monte_carlo(curve, n_samples=50, seed=42)
    assert set(r.equity_percentiles.keys()) == {5, 25, 50, 75, 95}
    for p, series in r.equity_percentiles.items():
        assert len(series) == len(curve), f"percentile {p} length mismatch"


def test_percentile_monotonic_at_each_bar():
    curve = [Decimal(str(10000 + 10 * i)) for i in range(20)]
    r = run_monte_carlo(curve, n_samples=200, seed=42)
    for i in range(len(curve)):
        assert r.equity_percentiles[5][i] <= r.equity_percentiles[25][i]
        assert r.equity_percentiles[25][i] <= r.equity_percentiles[50][i]
        assert r.equity_percentiles[50][i] <= r.equity_percentiles[75][i]
        assert r.equity_percentiles[75][i] <= r.equity_percentiles[95][i]
```

### `backend/tests/stress_test/engine/test_monte_carlo_input_validation.py`

```python
import pytest
from decimal import Decimal
from src.stress_test.engine import run_monte_carlo


def test_empty_curve_raises():
    with pytest.raises(ValueError):
        run_monte_carlo([], n_samples=10)


def test_single_point_raises():
    with pytest.raises(ValueError):
        run_monte_carlo([Decimal("10000")], n_samples=10)


def test_two_points_ok():
    r = run_monte_carlo([Decimal("10000"), Decimal("10100")], n_samples=10, seed=1)
    assert r.samples == 10
```

### `backend/tests/stress_test/engine/test_walk_forward_no_lookahead.py`

```python
"""No-lookahead 불변: test_start > train_end 모든 fold."""

import pandas as pd
import pytest
from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import make_sine_ohlcv, SIMPLE_PINE  # 기존 helper 활용 (fixture)


def test_test_window_after_train_window():
    ohlcv = make_sine_ohlcv(n_bars=500)
    result = run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50)
    for fold in result.folds:
        assert fold.test_start > fold.train_end, f"lookahead at fold {fold.fold_index}"


def test_no_bar_overlap_between_train_and_test():
    ohlcv = make_sine_ohlcv(n_bars=500)
    result = run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50)
    for fold in result.folds:
        assert fold.train_end <= fold.test_start  # 엄격히: train_end < test_start
```

> **Note:** `tests/backtest/helpers.py` 의 `make_sine_ohlcv` / `SIMPLE_PINE` 이 기존에 없으면 Phase A 에서 신규 추가. 기존 `tests/backtest/conftest.py` 에 유사 fixture 가 있을 수 있음 — Agent 가 확인 후 결정.

### `backend/tests/stress_test/engine/test_walk_forward_degradation.py`

```python
from decimal import Decimal
from dataclasses import replace
from src.stress_test.engine.walk_forward import WalkForwardFold, WalkForwardResult, run_walk_forward
from datetime import datetime, UTC


def _mk_fold(idx, is_ret, oos_ret):
    t = datetime(2026, 1, 1, tzinfo=UTC)
    return WalkForwardFold(
        fold_index=idx,
        train_start=t, train_end=t, test_start=t, test_end=t,
        in_sample_return=Decimal(str(is_ret)),
        out_of_sample_return=Decimal(str(oos_ret)),
        oos_sharpe=None,
        num_trades_oos=0,
    )


# degradation_ratio 는 실 계산 분기를 파이썬 레벨에서 재검증 (run_walk_forward 는 엔진-의존이라 helper 함수 내부 로직도 단위 검증)
# 실 함수 호출 버전:
def test_degradation_ratio_with_real_run():
    # Use simple deterministic OHLCV — is_avg > oos_avg (overfit 시뮬) → ratio > 1
    import pandas as pd
    from tests.backtest.helpers import make_trending_ohlcv, OVERFIT_PINE
    ohlcv = make_trending_ohlcv(n_bars=400)
    result = run_walk_forward(OVERFIT_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50)
    # 단지 타입/범위 체크 (구체 비율은 엔진 의존)
    assert isinstance(result.degradation_ratio, Decimal)
    assert result.aggregate_oos_return == sum(
        (f.out_of_sample_return for f in result.folds), Decimal("0")
    ) / Decimal(len(result.folds))
```

### `backend/tests/stress_test/engine/test_walk_forward_insufficient_data.py`

```python
import pytest
from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import make_sine_ohlcv, SIMPLE_PINE


def test_train_plus_test_exceeds_length():
    ohlcv = make_sine_ohlcv(n_bars=100)
    with pytest.raises(ValueError, match="exceeds ohlcv length"):
        run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=80, test_bars=50)


def test_non_positive_bars_raises():
    ohlcv = make_sine_ohlcv(n_bars=500)
    with pytest.raises(ValueError):
        run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=0, test_bars=50)
    with pytest.raises(ValueError):
        run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=100, test_bars=-1)
```

### `backend/tests/stress_test/engine/test_walk_forward_fold_count.py`

```python
from src.stress_test.engine import run_walk_forward
from tests.backtest.helpers import make_sine_ohlcv, SIMPLE_PINE


def test_fold_count_matches_expected():
    ohlcv = make_sine_ohlcv(n_bars=500)
    # (500 - 100) / 50 = 8 possible folds, but last must have 50 test bars → floor((500-100)/50) = 8
    result = run_walk_forward(SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=50)
    # (500 - 150) / 50 + 1 = 8 folds (idx 0, 50, 100, ..., 350)
    assert len(result.folds) == (500 - 100 - 50) // 50 + 1


def test_max_folds_caps_output():
    ohlcv = make_sine_ohlcv(n_bars=2000)
    result = run_walk_forward(
        SIMPLE_PINE, ohlcv, train_bars=100, test_bars=50, step_bars=10, max_folds=5
    )
    assert len(result.folds) == 5
```

## 성능 가드

Phase A 완료 직전 `pytest -k monte_carlo --durations=5` 실행. 1년 1H 시계열 (~8760 점, n_samples=1000) 이 **10 초 미만** 이어야 한다. 초과 시:

1. `n_samples` 기본을 500 으로 낮추고 docstring/DoD 에 기록
2. Phase B router 는 여전히 request.n_samples 수락 (상한 2000)
3. Sprint 10 에 Numba/Cython 도입 issue 기록

## Golden Rules 체크리스트 (Phase A 완료 시)

- [ ] `Decimal` 이 모든 반환값. `Decimal(str(float_v))` 패턴.
- [ ] `Decimal` 합산은 `sum(..., start=Decimal("0"))` (Sprint 4 D8)
- [ ] 환경변수 하드코딩 없음
- [ ] `.env.example` 변경 없음
- [ ] `from __future__ import annotations` 사용
- [ ] TypeScript 영역 해당없음
- [ ] ruff / mypy green
- [ ] pytest `tests/stress_test/engine/` green
- [ ] 기존 985 테스트 전체 green (회귀 없음)
- [ ] `backend/src/backtest/monte_carlo.py` 삭제 확인, import 충돌 없음

## 커밋 단위

```
c1 feat(stress-test): Monte Carlo engine — bootstrap + equity percentile fan

- move backend/src/backtest/monte_carlo.py → backend/src/stress_test/engine/monte_carlo.py
- add equity_percentiles (p5/p25/p50/p75/p95) per-bar time series for fan chart
- move/rewrite tests to tests/stress_test/engine/
- seed=42 snapshot deterministic

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

c2 feat(stress-test): Walk-Forward engine — rolling IS/OOS + degradation ratio

- add src/stress_test/engine/walk_forward.py
- no-lookahead invariant test (test_start > train_end)
- max_folds=20 guard
- reuse backtest.engine.run_backtest + BacktestConfig

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## 검증 명령

```bash
# 테스트
cd backend
pytest tests/stress_test/engine/ -v --cov=src.stress_test.engine --cov-report=term-missing --durations=5
# 8+ 테스트 green, coverage ≥ 90%, MC 100 회 테스트 < 2s

# 린트/타입
ruff check src/stress_test/ tests/stress_test/
mypy src/stress_test/

# 회귀
pytest -x  # 전체 985+ green
```

## Agent 디스패치 계약

**isolation:** worktree (feat/h2s9-stress-engine 브랜치 기반).
**model:** inherit (Opus 4.7).
**prompt 요구 출력 JSON:**

```json
{
  "branch": "feat/h2s9-stress-engine",
  "commits": ["<sha1>", "<sha2>"],
  "tests_added": 8,
  "tests_total": 993,
  "coverage_stress_test_engine": "XX.X%",
  "mc_1000_duration_sec": X.XX,
  "issues": ["..."],
  "ready_for_evaluator": true
}
```

GWF (Go With Fix) 시 Agent 에게 단일 fix 커밋 요청 — 불필요한 리팩터 차단.

## 리스크

| 리스크                                                             | 확률 | 완화                                                                                        |
| ------------------------------------------------------------------ | ---- | ------------------------------------------------------------------------------------------- |
| `tests/backtest/helpers.py` 에 fixture 없음                        | 중   | Agent 가 먼저 확인 → 없으면 신규 생성. `conftest.py` 의 `make_ohlcv` 유사 함수 재사용 우선. |
| `run_backtest` signature 가 `BacktestConfig` 를 kwarg 로 받지 않음 | 낮   | `backend/src/backtest/engine/adapter.py` 직접 읽고 signature 맞춤.                          |
| MC 1000×8760 > 10초                                                | 중   | 기본값 500 하향 + issue 기록 (DoD 변경).                                                    |
| Decimal("Infinity") pydantic 직렬화 이슈                           | 중   | Phase B 스키마에서 문자열 변환 처리. Phase A 엔진은 Decimal 그대로 반환.                    |
