# BL-084 — Param Stability call count + cfg isolation spy (Sprint 50 codex P2#9 패턴 재사용)
"""Sprint 51 BL-084 강화 invariant test for Param Stability.

Sprint 50 cost_assumption_sensitivity_state_isolation 패턴 1:1 재사용.
1) run_backtest 호출 횟수 = N1 * N2 정확히 일치
2) 각 호출의 BacktestConfig.input_overrides 값 = grid (i, j) 와 1:1 매칭
3) 매 호출마다 새 PersistentStore + Interpreter 보장 (Sprint 19 BL-084 Resolved).
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.stress_test.engine import run_param_stability


def test_param_stability_call_count_and_cfg_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """9 cell grid → run_backtest 9회 호출 + 매번 다른 input_overrides cfg."""
    from src.stress_test.engine import param_stability as ps_mod

    real_run_backtest = ps_mod.run_backtest
    seen_overrides: list[tuple[tuple[str, float], tuple[str, float]]] = []

    def spy_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg):  # type: ignore[no-untyped-def]
        # cfg.input_overrides 는 MappingProxyType (Slice 1 review P1 fix). dict 변환.
        items = sorted(dict(cfg.input_overrides).items()) if cfg.input_overrides else []
        # tuple sort 후 첫/둘 element 쌍 (key, float(value))
        seen_overrides.append(
            (
                (items[0][0], float(items[0][1])),
                (items[1][0], float(items[1][1])),
            )
        )
        return real_run_backtest(pine, ohlcv, cfg)

    monkeypatch.setattr(ps_mod, "run_backtest", spy_run_backtest)

    pine = """
//@version=5
strategy("X")
emaPeriod = input.int(14, "EMA")
stopLossPct = input.float(1.0, "SL")
ema = ta.ema(close, emaPeriod)
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
    ema_grid = [Decimal("10"), Decimal("20"), Decimal("30")]
    sl_grid = [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")]

    result = run_param_stability(
        pine,
        ohlcv,
        param_grid={"emaPeriod": ema_grid, "stopLossPct": sl_grid},
    )
    assert len(result.cells) == 9

    # Sprint 50 codex P2#9 강화: call count = 9 (정확히 N1*N2 회).
    assert len(seen_overrides) == 9, "run_backtest must be called exactly N1*N2 times"

    # cfg isolation: 각 cell 이 unique input_overrides cfg 호출.
    expected = {
        (("emaPeriod", float(ema)), ("stopLossPct", float(sl)))
        for ema in ema_grid
        for sl in sl_grid
    }
    assert set(seen_overrides) == expected, (
        "each cell must invoke run_backtest with a unique input_overrides cfg"
    )
    assert len(set(seen_overrides)) == 9, (
        "duplicate cfg detected — cell isolation broken"
    )


def test_param_stability_preserves_base_input_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """codex Slice 3 review P2#1 회귀 가드 — base.input_overrides 의 sweep 외 키 보존.

    base 가 useLongs=True override 를 가진 상태에서 emaPeriod x stopLossPct sweep
    시, 모든 9 cell 의 input_overrides 에 useLongs=True 가 보존되어야 함.
    누락 시 base 명시 override 가 silent 손실 → 사용자 의도와 다른 결과.
    """
    from src.backtest.engine.types import BacktestConfig
    from src.stress_test.engine import param_stability as ps_mod

    real_run_backtest = ps_mod.run_backtest
    seen_useLongs_values: list[bool] = []

    def spy_run_backtest(pine: str, ohlcv: pd.DataFrame, cfg):  # type: ignore[no-untyped-def]
        if cfg.input_overrides is not None:
            seen_useLongs_values.append(bool(cfg.input_overrides.get("useLongs", None)))
        return real_run_backtest(pine, ohlcv, cfg)

    monkeypatch.setattr(ps_mod, "run_backtest", spy_run_backtest)

    pine = """
//@version=5
strategy("X")
emaPeriod = input.int(14, "EMA")
stopLossPct = input.float(1.0, "SL")
useLongs = input.bool(false, "Use Longs")
ema = ta.ema(close, emaPeriod)
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
    base_config = BacktestConfig(input_overrides={"useLongs": True})
    run_param_stability(
        pine,
        ohlcv,
        param_grid={
            "emaPeriod": [Decimal("10"), Decimal("20"), Decimal("30")],
            "stopLossPct": [Decimal("1.0"), Decimal("2.0"), Decimal("3.0")],
        },
        backtest_config=base_config,
    )
    assert len(seen_useLongs_values) == 9
    assert all(v is True for v in seen_useLongs_values), (
        "base.input_overrides['useLongs']=True 가 모든 9 cell 에서 보존되어야 함"
    )
