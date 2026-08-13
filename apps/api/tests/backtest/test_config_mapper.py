# Sprint 52 BL-222 P1 — config_mapper.build_engine_config_from_db unit test
"""Sprint 52 BL-222 P1 — `src/backtest/config_mapper.py` module-level helper unit test.

Sprint 31 BL-162a 진입 시점 매핑이 BacktestService._build_engine_config 에서 추출됐다.
본 unit test 는 추출된 helper 가 동일 매핑 정합성 보존을 검증.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.backtest.config_mapper import (
    build_engine_config_from_db,
    timeframe_to_freq,
)
from src.backtest.engine.types import BacktestConfig
from src.backtest.models import Backtest, BacktestStatus


def _make_bt(*, config: dict | None, initial_capital: Decimal = Decimal("10000"), timeframe: str = "1h") -> Backtest:
    return Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTCUSDT",
        timeframe=timeframe,
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=initial_capital,
        status=BacktestStatus.COMPLETED,
        config=config,
    )


def test_build_engine_config_null_config_uses_defaults_with_bt_overrides() -> None:
    """bt.config NULL → engine default 적용. init_cash / freq 만 bt 값."""
    bt = _make_bt(config=None, initial_capital=Decimal("25000"), timeframe="5m")
    cfg = build_engine_config_from_db(bt)

    default = BacktestConfig()
    assert cfg.init_cash == Decimal("25000")
    assert cfg.freq == "5min"
    assert cfg.fees == default.fees
    assert cfg.slippage == default.slippage
    assert cfg.leverage == default.leverage
    assert cfg.include_funding == default.include_funding
    assert cfg.trading_sessions == ()
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
    assert cfg.default_qty_type is None
    assert cfg.default_qty_value is None
    assert cfg.live_position_size_pct is None


def test_build_engine_config_with_bl188_v3_sizing_all_5_fields_preserved() -> None:
    """BL-188 v3 sizing 5 필드 + trading_sessions + fees/slippage/leverage 보존."""
    cfg_dict = {
        "fees": 0.002,
        "slippage": 0.0007,
        "leverage": 2.0,
        "include_funding": True,
        "trading_sessions": ["America/New_York", "Europe/London"],
        "default_qty_type": "percent_of_equity",
        "default_qty_value": 50.0,
        "live_position_size_pct": 25.0,
        "sizing_source": "form",
        "sizing_basis": "form_equity",
        "leverage_basis": 5.0,
    }
    bt = _make_bt(config=cfg_dict, initial_capital=Decimal("50000"), timeframe="4h")
    cfg = build_engine_config_from_db(bt)

    assert cfg.init_cash == Decimal("50000")
    assert cfg.freq == "4h"
    assert cfg.fees == 0.002
    assert cfg.slippage == 0.0007
    assert cfg.leverage == 2.0
    assert cfg.include_funding is True
    assert cfg.trading_sessions == ("America/New_York", "Europe/London")
    assert cfg.default_qty_type == "percent_of_equity"
    assert cfg.default_qty_value == 50.0
    assert cfg.live_position_size_pct == 25.0
    assert cfg.sizing_source == "form"
    assert cfg.sizing_basis == "form_equity"
    assert cfg.leverage_basis == 5.0


def test_build_engine_config_invalid_sizing_source_falls_back() -> None:
    """sizing_source 가 4 Literal 외 값이면 'fallback' 으로 강제."""
    bt = _make_bt(config={"sizing_source": "bogus_value"})
    cfg = build_engine_config_from_db(bt)
    assert cfg.sizing_source == "fallback"


def test_build_engine_config_invalid_sizing_basis_falls_back() -> None:
    """sizing_basis 가 4 Literal 외 값이면 'fallback_qty1' 으로 강제."""
    bt = _make_bt(config={"sizing_basis": "bogus_value"})
    cfg = build_engine_config_from_db(bt)
    assert cfg.sizing_basis == "fallback_qty1"


def test_timeframe_to_freq_maps_all_6_supported_timeframes() -> None:
    """6 timeframe Literal 모두 pandas offset alias 매핑 + fallback."""
    assert timeframe_to_freq("1m") == "1min"
    assert timeframe_to_freq("5m") == "5min"
    assert timeframe_to_freq("15m") == "15min"
    assert timeframe_to_freq("1h") == "1h"
    assert timeframe_to_freq("4h") == "4h"
    assert timeframe_to_freq("1d") == "1D"
    assert timeframe_to_freq("invalid_tf") == "1D"


def test_build_engine_config_partial_sizing_fields_omitted() -> None:
    """일부 sizing 필드만 채워진 config (실제 사용자 입력 변형) — None 보존."""
    bt = _make_bt(
        config={
            "fees": 0.001,
            "default_qty_type": "fixed",
            "default_qty_value": 100.0,
            # live_position_size_pct 누락
            # sizing_source / sizing_basis 누락 → fallback
        }
    )
    cfg = build_engine_config_from_db(bt)
    assert cfg.fees == 0.001
    assert cfg.default_qty_type == "fixed"
    assert cfg.default_qty_value == 100.0
    assert cfg.live_position_size_pct is None
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
