# [BL-460] BacktestConfig 의 비용률이 실제로 증거금 게이트까지 도달하는지 검증한다.
"""배선 오라클 — 단위 테스트만으로는 못 잡는 구간을 막는다.

`strategy_state` 단위 테스트(`tests/strategy/pine_v2/test_margin_gate_net_equity.py`)는
`configure_sizing(taker_cost_rate=...)` 를 **직접** 부른다. 그래서 어댑터가 그 값을
넘기는 것을 잊어도 초록으로 남는다 — 게이트는 프로덕션 경로에서만 gross 로 되돌아가고
아무도 모른다. 여기서 그 한 칸을 못 박는다.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine import v2_adapter
from src.backtest.engine.types import BacktestConfig

SOURCE = """//@version=5
strategy("noop", overlay=true)
"""


def _ohlcv(bars: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [100.0] * bars,
            "high": [101.0] * bars,
            "low": [99.0] * bars,
            "close": [100.0] * bars,
            "volume": [1.0] * bars,
        },
        index=pd.date_range("2026-01-01", periods=bars, freq="1D", tz="UTC"),
    )


def _captured_kwargs(monkeypatch: pytest.MonkeyPatch, cfg: BacktestConfig) -> dict:
    """`run_backtest_v2` 가 엔진에 넘긴 kwargs 를 가로챈다."""
    seen: dict = {}
    real = v2_adapter.parse_and_run_v2

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(v2_adapter, "parse_and_run_v2", spy)
    v2_adapter.run_backtest_v2(SOURCE, _ohlcv(), config=cfg)
    return seen


def test_config_cost_rates_reach_the_engine_as_a_single_leg_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """leg 비용률 = fees + slippage 로 합쳐져 엔진에 전달된다."""
    cfg = BacktestConfig(
        init_cash=Decimal("10000"),
        fees=0.002,
        slippage=0.0005,
        leverage=3.0,
    )

    seen = _captured_kwargs(monkeypatch, cfg)

    assert seen["taker_cost_rate"] == pytest.approx(0.0025)
    # 같은 호출이 leverage 도 그대로 넘긴다 — 비용률만 도착하고 게이트가 꺼져 있으면 무의미.
    assert seen["leverage"] == pytest.approx(3.0)


def test_default_config_still_sends_the_measured_live_cost_rate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """기본 config 도 실측 비용률(0.055% + 0.014%)을 넘긴다 — 0 으로 새지 않는다."""
    seen = _captured_kwargs(monkeypatch, BacktestConfig())

    assert seen["taker_cost_rate"] == pytest.approx(0.00069)
