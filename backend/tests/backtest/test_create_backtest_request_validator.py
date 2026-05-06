"""Sprint 38 BL-188 v3 — CreateBacktestRequest validator 회귀.

codex G.0 iter 1+2 [P1] must-fix 1 (sizing source 단일화) Pydantic schema-level 1차
차단 검증. service.py `_resolve_sizing_canonical` 의 SizingSourceConflict 와 이중 방어.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.backtest.schemas import CreateBacktestRequest


def _base_kwargs(**overrides) -> dict:
    """validator 검증용 base — 모든 필수 필드 + 기본값."""
    base = {
        "strategy_id": uuid4(),
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "period_start": datetime(2024, 1, 1, tzinfo=UTC),
        "period_end": datetime(2024, 1, 7, tzinfo=UTC),
        "initial_capital": Decimal("10000"),
    }
    base.update(overrides)
    return base


# 1. position_size_pct 만 명시 (Live mirror) → OK.
def test_position_size_pct_alone_is_valid() -> None:
    req = CreateBacktestRequest(**_base_kwargs(position_size_pct=Decimal("30")))
    assert req.position_size_pct == Decimal("30")
    assert req.default_qty_type is None
    assert req.default_qty_value is None


# 2. default_qty_type/value 만 명시 (manual) → OK.
def test_default_qty_alone_is_valid() -> None:
    req = CreateBacktestRequest(
        **_base_kwargs(
            default_qty_type="strategy.percent_of_equity",
            default_qty_value=Decimal("10"),
        )
    )
    assert req.default_qty_type == "strategy.percent_of_equity"
    assert req.position_size_pct is None


# 3. 동시 명시 → 422 ValidationError (`_no_double_sizing`).
def test_position_size_pct_with_default_qty_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CreateBacktestRequest(
            **_base_kwargs(
                position_size_pct=Decimal("30"),
                default_qty_type="strategy.percent_of_equity",
                default_qty_value=Decimal("10"),
            )
        )
    # message 안 'canonical 1개' 키워드 확인 (사용자 친화 메시지).
    assert "canonical" in str(excinfo.value)


# 4. trading_sessions 빈 list = 24h.
def test_trading_sessions_default_empty_list() -> None:
    req = CreateBacktestRequest(**_base_kwargs())
    assert req.trading_sessions == []


# 5. trading_sessions Literal 명시 → OK.
def test_trading_sessions_explicit_values() -> None:
    req = CreateBacktestRequest(**_base_kwargs(trading_sessions=["asia", "london"]))
    assert req.trading_sessions == ["asia", "london"]


# 6. trading_sessions 잘못된 값 → 422.
def test_trading_sessions_invalid_value_raises() -> None:
    with pytest.raises(ValidationError):
        # 의도적 Literal 위반 — Pydantic validator 의 422 reject 검증.
        CreateBacktestRequest(**_base_kwargs(trading_sessions=["tokyo"]))


# 7. position_size_pct 범위 (0, 100] — 0 reject.
def test_position_size_pct_zero_raises() -> None:
    with pytest.raises(ValidationError):
        CreateBacktestRequest(**_base_kwargs(position_size_pct=Decimal("0")))


# 8. position_size_pct 100 초과 → 422.
def test_position_size_pct_above_100_raises() -> None:
    with pytest.raises(ValidationError):
        CreateBacktestRequest(**_base_kwargs(position_size_pct=Decimal("100.01")))


# 9. position_size_pct = 100 → OK (le 경계).
def test_position_size_pct_equals_100_is_valid() -> None:
    req = CreateBacktestRequest(**_base_kwargs(position_size_pct=Decimal("100")))
    assert req.position_size_pct == Decimal("100")
