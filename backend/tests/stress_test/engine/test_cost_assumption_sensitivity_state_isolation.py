# BL-084 강화 — call count + BacktestConfig 값 isolation spy (codex P2#9 반영)
"""Sprint 50 BL-084 강화 invariant test.

codex P2#9 권고: id(outcome.result) 만 모으면 GC/id reuse 로 flaky 가능. 신규 패턴:
1) run_backtest 호출 횟수 = N1 * N2 정확히 일치
2) 각 호출의 BacktestConfig 값 = grid (i, j) 와 1:1 매칭 (cfg fees/slippage isolation)
3) 매 호출마다 새 PersistentStore + Interpreter 보장 = run_backtest 자체가 보장
   (Sprint 19 BL-084 Resolved). 본 test 는 Cost Assumption Sensitivity wrapper
   가 그 호출 chain 을 손상 X 검증.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.stress_test.engine import run_cost_assumption_sensitivity


def test_cost_assumption_call_count_and_cfg_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """9 cell grid → run_backtest 9회 호출 + 매번 다른 (fees, slippage) cfg."""
    from src.stress_test.engine import cost_assumption_sensitivity as ca_mod

    real_run_backtest = ca_mod.run_backtest
    seen_cfgs: list[tuple[float, float]] = []

    def spy_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg):  # type: ignore[no-untyped-def]
        seen_cfgs.append((cfg.fees, cfg.slippage))
        return real_run_backtest(pine, ohlcv, cfg)

    monkeypatch.setattr(ca_mod, "run_backtest", spy_run_backtest)

    pine = """
//@version=5
strategy("X")
ema = ta.ema(close, 5)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""
    idx = pd.date_range("2024-01-01", periods=200, freq="h", tz="UTC")
    ohlcv = pd.DataFrame(
        {
            "open": [100.0 + i * 0.1 for i in range(200)],
            "high": [101.0 + i * 0.1 for i in range(200)],
            "low": [99.0 + i * 0.1 for i in range(200)],
            "close": [100.5 + i * 0.1 for i in range(200)],
            "volume": [1000.0] * 200,
        },
        index=idx,
    )
    fees_grid = [Decimal("0.0005"), Decimal("0.001"), Decimal("0.002")]
    slippage_grid = [Decimal("0.0001"), Decimal("0.0005"), Decimal("0.001")]

    result = run_cost_assumption_sensitivity(
        pine,
        ohlcv,
        param_grid={"fees": fees_grid, "slippage": slippage_grid},
    )
    assert len(result.cells) == 9

    # codex P2#9 강화: call count = 9 (정확히 N1*N2 회)
    assert len(seen_cfgs) == 9, "run_backtest must be called exactly N1*N2 times"

    # cfg isolation: 각 cell 이 unique (fees, slippage) cfg 호출
    expected_cfgs = {
        (float(f), float(s)) for f in fees_grid for s in slippage_grid
    }
    assert set(seen_cfgs) == expected_cfgs, (
        "each cell must invoke run_backtest with a unique (fees, slippage) cfg"
    )

    # 중복 cfg 없음 (id() reuse 회피 가능 patterns 까지 정합)
    assert len(set(seen_cfgs)) == 9, "duplicate cfg detected — cell isolation broken"
