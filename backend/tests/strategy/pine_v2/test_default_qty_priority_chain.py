# Sprint 38 BL-188 v3 A2 — compat parse_and_run_v2 D2 priority chain (Pine > form > Live > fallback) + Pine partial reject (service layer)
"""compat.parse_and_run_v2 가 sizing 4-tier chain 을 정확히 적용하는지 검증.

D2 결정 (BL-188 v3 codex iter 2 [P1] #1):
  1. Pine `strategy(default_qty_type=..., default_qty_value=...)` 명시 → override
  2. Pine 미명시 + form_default_qty_type/value 명시 → form 우선
  3. Pine·form 미명시 + live_position_size_pct 명시 → ("strategy.percent_of_equity", live_pct)
  4. 모두 None → qty=1.0 fallback

Pine partial (type-only / value-only) 은 service helper `_resolve_sizing_canonical`
이 1차 422 reject. compat 은 service 보장 후만 호출되지만, 본 테스트는 chain
silent downgrade 회귀 방어 차원에서 service helper 의 reject 도 회귀 보장.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pandas as pd
import pytest

from src.backtest.exceptions import PinePartialDeclaration
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import _resolve_sizing_canonical
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.pine_v2.compat import parse_and_run_v2

_PINE_BARE_LONG_ENTRY = """//@version=5
strategy("Bare", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
"""

_PINE_FULL_QTY = """//@version=5
strategy("Full", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=25)
if bar_index == 1
    strategy.entry("L", strategy.long)
"""

_PINE_PARTIAL_TYPE_ONLY = """//@version=5
strategy("Partial", overlay=true, default_qty_type=strategy.cash)
if bar_index == 1
    strategy.entry("L", strategy.long)
"""


def _make_ohlcv(n: int = 5) -> pd.DataFrame:
    """3-bar 직선 가격 OHLCV (entry 가 bar_index==1 에서 1회 발생)."""
    idx = pd.date_range("2026-04-01 00:00:00+00:00", periods=n, freq="1h")
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [1.0] * n,
        },
        index=idx,
    )


def _state_from_run(result):
    """Track S → historical.strategy_state, Track A → virtual.strategy_state."""
    if result.historical is not None:
        return result.historical.strategy_state
    return result.virtual.strategy_state


def test_chain_pine_explicit_overrides_form_and_live() -> None:
    """Tier 1: Pine strategy() default_qty_type/value 명시 시 form/Live 가 무시되어야 함."""
    out = parse_and_run_v2(
        _PINE_FULL_QTY,
        _make_ohlcv(),
        initial_capital=10_000.0,
        live_position_size_pct=99.0,  # ignored
        form_default_qty_type="strategy.cash",  # ignored
        form_default_qty_value=500.0,  # ignored
    )
    state = _state_from_run(out)
    assert state.default_qty_type == "strategy.percent_of_equity"
    assert state.default_qty_value == 25.0
    assert state.initial_capital == 10_000.0


def test_chain_form_takes_over_when_pine_silent() -> None:
    """Tier 2: Pine 미명시 + form 명시 → form 사용."""
    out = parse_and_run_v2(
        _PINE_BARE_LONG_ENTRY,
        _make_ohlcv(),
        initial_capital=10_000.0,
        form_default_qty_type="strategy.cash",
        form_default_qty_value=500.0,
    )
    state = _state_from_run(out)
    assert state.default_qty_type == "strategy.cash"
    assert state.default_qty_value == 500.0


def test_chain_live_tier_when_pine_and_form_silent() -> None:
    """Tier 3: Pine·form 미명시 + live_position_size_pct → percent_of_equity 매핑."""
    out = parse_and_run_v2(
        _PINE_BARE_LONG_ENTRY,
        _make_ohlcv(),
        initial_capital=10_000.0,
        live_position_size_pct=15.0,
    )
    state = _state_from_run(out)
    assert state.default_qty_type == "strategy.percent_of_equity"
    assert state.default_qty_value == 15.0


def test_chain_fallback_when_all_silent() -> None:
    """Tier 4: 모두 None → state.default_qty_type 도 None (compute_qty=1.0 fallback)."""
    out = parse_and_run_v2(
        _PINE_BARE_LONG_ENTRY,
        _make_ohlcv(),
        initial_capital=10_000.0,
    )
    state = _state_from_run(out)
    assert state.default_qty_type is None
    assert state.default_qty_value is None
    # entry 발생 확인 (compute_qty fallback=1.0 사용)
    assert len(state.open_trades) == 1
    assert next(iter(state.open_trades.values())).qty == pytest.approx(1.0)


def test_live_tier_requires_initial_capital_assert() -> None:
    """live_position_size_pct 명시 시 initial_capital None 이면 silent skip 금지 → assert."""
    with pytest.raises(AssertionError, match="initial_capital"):
        parse_and_run_v2(
            _PINE_BARE_LONG_ENTRY,
            _make_ohlcv(),
            initial_capital=None,
            live_position_size_pct=10.0,
        )


def _make_strategy(*, pine_source: str = _PINE_FULL_QTY) -> Strategy:
    """_resolve_sizing_canonical 입력용 Strategy fixture (settings 없음)."""
    now = datetime.now(UTC)
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="Test",
        description="",
        pine_source=pine_source,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        parsed_at=now,
        tags=[],
        created_at=now,
        updated_at=now,
        settings=None,
    )


def test_pine_partial_rejects_at_service_helper() -> None:
    """Pine type-only 선언은 service helper 가 422 reject — chain silent fallthrough 차단."""
    request = CreateBacktestRequest(
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2026, 1, 31, tzinfo=UTC),
        initial_capital=Decimal("10000"),
    )
    strategy = _make_strategy(pine_source=_PINE_PARTIAL_TYPE_ONLY)
    with pytest.raises(PinePartialDeclaration):
        _resolve_sizing_canonical(request, strategy)
