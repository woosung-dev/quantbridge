"""Sprint 38 BL-188 v3 — sizing canonical helper 8 case golden.

codex G.0 iter 1+2 [P1] must-fix 1 (sizing source 단일화) + must-fix 3 (leverage Nx
reject) + iter 2 [P1] #1 (D2 manual override) 검증. helper 가 결정한 5 필드 dict
가 Backtest.config JSONB 에 저장 → _build_engine_config 가 BacktestConfig 로 propagate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.backtest.exceptions import (
    MirrorNotAllowed,
    PinePartialDeclaration,
    SizingSourceConflict,
)
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import _resolve_sizing_canonical
from src.strategy.models import ParseStatus, PineVersion, Strategy

_PINE_BARE = """//@version=5
strategy("Bare", overlay=true)
ema = ta.ema(close, 5)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""

_PINE_DEFAULT_QTY_FULL = """//@version=5
strategy("WithQty", overlay=true, default_qty_type=strategy.cash, default_qty_value=5000)
ema = ta.ema(close, 5)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""

_PINE_DEFAULT_QTY_PARTIAL = """//@version=5
strategy("Partial", overlay=true, default_qty_type=strategy.cash)
ema = ta.ema(close, 5)
if ta.crossover(close, ema)
    strategy.entry("L", strategy.long)
"""


def _make_strategy(
    *,
    pine_source: str = _PINE_BARE,
    settings: dict | None = None,
    trading_sessions: list[str] | None = None,
) -> Strategy:
    """Pine source / Live settings / sessions 변형 가능한 Strategy 인스턴스."""
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="t",
        pine_source=pine_source,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=settings,
        trading_sessions=trading_sessions or [],
    )


def _make_request(
    *,
    strategy_id,
    default_qty_type: str | None = None,
    default_qty_value: Decimal | None = None,
    position_size_pct: Decimal | None = None,
    trading_sessions: list[str] | None = None,
) -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        default_qty_type=default_qty_type,  # type: ignore[arg-type]
        default_qty_value=default_qty_value,
        position_size_pct=position_size_pct,
        trading_sessions=trading_sessions or [],  # type: ignore[arg-type]
    )


# 1. Pine 명시 (둘 다) → tier 1 (Pine override).
def test_pine_full_declaration_returns_pine_tier() -> None:
    strategy = _make_strategy(pine_source=_PINE_DEFAULT_QTY_FULL)
    req = _make_request(strategy_id=strategy.id)
    result = _resolve_sizing_canonical(req, strategy)
    assert result["sizing_source"] == "pine"
    assert result["sizing_basis"] == "pine_native"
    assert result["default_qty_type"] == "strategy.cash"
    assert result["default_qty_value"] == 5000.0
    assert result["live_position_size_pct"] is None
    assert result["leverage_basis"] == 1.0


# 2. Pine partial declaration → 422 PinePartialDeclaration.
def test_pine_partial_declaration_raises_422() -> None:
    strategy = _make_strategy(pine_source=_PINE_DEFAULT_QTY_PARTIAL)
    req = _make_request(strategy_id=strategy.id)
    with pytest.raises(PinePartialDeclaration) as excinfo:
        _resolve_sizing_canonical(req, strategy)
    assert excinfo.value.declared_type == "strategy.cash"
    assert excinfo.value.declared_value is None


# 3. Manual form override (D2) → tier 2 (Pine 미명시 + form 명시).
def test_manual_form_override_returns_form_tier() -> None:
    strategy = _make_strategy(
        settings={
            "leverage": 1,
            "margin_mode": "isolated",
            "position_size_pct": 30.0,
        }
    )
    req = _make_request(
        strategy_id=strategy.id,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=Decimal("15"),
    )
    result = _resolve_sizing_canonical(req, strategy)
    assert result["sizing_source"] == "form"
    assert result["sizing_basis"] == "form_equity"
    assert result["default_qty_type"] == "strategy.percent_of_equity"
    assert result["default_qty_value"] == 15.0
    assert result["live_position_size_pct"] is None


# 4. Live mirror 1x — request.position_size_pct 명시 → tier 3.
def test_live_mirror_request_explicit_returns_live_tier() -> None:
    strategy = _make_strategy(
        settings={
            "leverage": 1,
            "margin_mode": "isolated",
            "position_size_pct": 30.0,
        }
    )
    req = _make_request(
        strategy_id=strategy.id,
        position_size_pct=Decimal("25"),
    )
    result = _resolve_sizing_canonical(req, strategy)
    assert result["sizing_source"] == "live"
    assert result["sizing_basis"] == "live_available_balance_approx_equity"
    assert result["default_qty_type"] is None
    assert result["default_qty_value"] is None
    assert result["live_position_size_pct"] == 25.0  # request 우선


# 5. Live mirror 1x — settings 만 (request 미명시) → tier 3 implicit.
def test_live_mirror_settings_only_returns_live_tier() -> None:
    strategy = _make_strategy(
        settings={
            "leverage": 1,
            "margin_mode": "cross",
            "position_size_pct": 50.0,
        }
    )
    req = _make_request(strategy_id=strategy.id)
    result = _resolve_sizing_canonical(req, strategy)
    assert result["sizing_source"] == "live"
    assert result["sizing_basis"] == "live_available_balance_approx_equity"
    assert result["live_position_size_pct"] == 50.0  # settings 값


# 6. Live leverage Nx → 422 MirrorNotAllowed (codex must-fix 3).
def test_live_leverage_nx_raises_mirror_not_allowed() -> None:
    strategy = _make_strategy(
        settings={
            "leverage": 3,
            "margin_mode": "isolated",
            "position_size_pct": 30.0,
        }
    )
    req = _make_request(strategy_id=strategy.id)
    with pytest.raises(MirrorNotAllowed) as excinfo:
        _resolve_sizing_canonical(req, strategy)
    assert excinfo.value.live_leverage == 3
    assert excinfo.value.live_margin_mode == "isolated"


# 7. Double sizing (position_size_pct + default_qty_*) → 422 SizingSourceConflict.
#    schema validator 가 1차 차단하지만 helper service-level 2차 방어 검증.
def test_double_sizing_raises_conflict_at_service_level() -> None:
    """schema validator 우회 (model_construct) → service-level 2차 방어."""
    strategy = _make_strategy()
    # CreateBacktestRequest validator 를 우회하기 위해 model_construct 사용.
    req = CreateBacktestRequest.model_construct(
        strategy_id=strategy.id,
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        leverage=Decimal("1.0"),
        fees_pct=Decimal("0.001"),
        slippage_pct=Decimal("0.0005"),
        include_funding=True,
        allow_degraded_pine=False,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=Decimal("10"),
        position_size_pct=Decimal("30"),  # 동시 명시 — schema validator 미우회.
        trading_sessions=[],
    )
    with pytest.raises(SizingSourceConflict):
        _resolve_sizing_canonical(req, strategy)


# 8. 모두 None — fallback (qty=1.0 호환).
def test_no_sizing_input_returns_fallback() -> None:
    strategy = _make_strategy()  # settings=None
    req = _make_request(strategy_id=strategy.id)
    result = _resolve_sizing_canonical(req, strategy)
    assert result["sizing_source"] == "fallback"
    assert result["sizing_basis"] == "fallback_qty1"
    assert result["default_qty_type"] is None
    assert result["default_qty_value"] is None
    assert result["live_position_size_pct"] is None
    assert result["leverage_basis"] == 1.0
