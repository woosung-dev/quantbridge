"""Sprint 38 BL-188 v3 — _build_engine_config Live mirror 매핑 회귀.

codex G.0 iter 2 [P1] #3: submit() 가 bt.config JSONB 에 저장한 sizing canonical 5
필드 + trading_sessions 가 worker `_build_engine_config()` 에서 BacktestConfig 로
정확히 propagate 되는지 검증. 본 매핑 누락 시 worker 가 Live mirror 결정 silent
ignore = 거짓 trust 회복 실패.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from src.backtest.models import Backtest, BacktestStatus
from src.backtest.service import BacktestService


def _make_service() -> BacktestService:
    return BacktestService(
        repo=AsyncMock(),
        strategy_repo=AsyncMock(),
        ohlcv_provider=AsyncMock(),
        dispatcher=AsyncMock(),
    )


def _make_bt(*, config: dict | None) -> Backtest:
    return Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.QUEUED,
        config=config,
    )


# 1. Live mirror config (1x) → BacktestConfig.live_position_size_pct 매핑.
def test_live_mirror_config_propagates_to_engine() -> None:
    svc = _make_service()
    bt = _make_bt(
        config={
            "leverage": 1.0,
            "fees": 0.001,
            "slippage": 0.0005,
            "include_funding": True,
            "live_position_size_pct": 30.0,
            "sizing_source": "live",
            "sizing_basis": "live_available_balance_approx_equity",
            "leverage_basis": 1.0,
            "trading_sessions": ["asia", "london"],
        }
    )
    cfg = svc._build_engine_config(bt)
    assert cfg.live_position_size_pct == 30.0
    assert cfg.sizing_source == "live"
    assert cfg.sizing_basis == "live_available_balance_approx_equity"
    assert cfg.leverage_basis == 1.0
    assert cfg.trading_sessions == ("asia", "london")
    # default_qty_* 는 Live mirror 시 None.
    assert cfg.default_qty_type is None
    assert cfg.default_qty_value is None


# 2. Pine 명시 config → default_qty_* 매핑 + sizing_source="pine".
def test_pine_config_propagates_to_engine() -> None:
    svc = _make_service()
    bt = _make_bt(
        config={
            "leverage": 1.0,
            "fees": 0.001,
            "slippage": 0.0005,
            "include_funding": True,
            "default_qty_type": "strategy.cash",
            "default_qty_value": 5000.0,
            "sizing_source": "pine",
            "sizing_basis": "pine_native",
            "leverage_basis": 1.0,
        }
    )
    cfg = svc._build_engine_config(bt)
    assert cfg.default_qty_type == "strategy.cash"
    assert cfg.default_qty_value == 5000.0
    assert cfg.sizing_source == "pine"
    assert cfg.sizing_basis == "pine_native"
    assert cfg.live_position_size_pct is None


# 3. Form (manual override) config → default_qty_* + sizing_source="form".
def test_form_config_propagates_to_engine() -> None:
    svc = _make_service()
    bt = _make_bt(
        config={
            "leverage": 1.0,
            "fees": 0.001,
            "slippage": 0.0005,
            "include_funding": True,
            "default_qty_type": "strategy.percent_of_equity",
            "default_qty_value": 15.0,
            "sizing_source": "form",
            "sizing_basis": "form_equity",
            "leverage_basis": 1.0,
        }
    )
    cfg = svc._build_engine_config(bt)
    assert cfg.default_qty_type == "strategy.percent_of_equity"
    assert cfg.default_qty_value == 15.0
    assert cfg.sizing_source == "form"
    assert cfg.sizing_basis == "form_equity"


# 4. Legacy config (sizing 메타 없음) → fallback.
def test_legacy_config_falls_back_to_default() -> None:
    svc = _make_service()
    bt = _make_bt(
        config={
            "leverage": 1.0,
            "fees": 0.001,
            "slippage": 0.0005,
            "include_funding": True,
        }
    )
    cfg = svc._build_engine_config(bt)
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
    assert cfg.live_position_size_pct is None
    assert cfg.default_qty_type is None
    assert cfg.default_qty_value is None
    assert cfg.trading_sessions == ()


# 5. NULL config (Sprint 30 이전) → engine default.
def test_null_config_uses_engine_default() -> None:
    svc = _make_service()
    bt = _make_bt(config=None)
    cfg = svc._build_engine_config(bt)
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
    assert cfg.leverage_basis == 1.0
    assert cfg.trading_sessions == ()


# 6. trading_sessions 빈 list → tuple() (24h).
def test_empty_trading_sessions_becomes_empty_tuple() -> None:
    svc = _make_service()
    bt = _make_bt(
        config={
            "leverage": 1.0,
            "trading_sessions": [],
        }
    )
    cfg = svc._build_engine_config(bt)
    assert cfg.trading_sessions == ()


# 7. 잘못된 sizing_source / sizing_basis → fallback (defensive).
def test_invalid_sizing_metadata_falls_back() -> None:
    svc = _make_service()
    bt = _make_bt(
        config={
            "leverage": 1.0,
            "sizing_source": "INVALID_SOURCE",
            "sizing_basis": "INVALID_BASIS",
        }
    )
    cfg = svc._build_engine_config(bt)
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
