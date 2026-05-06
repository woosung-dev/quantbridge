"""Sprint 38 BL-188 v3 — submit() 안 sizing canonical helper 호출 + commit spy 회귀.

codex G.0 iter 2 [P1] #3 mapping fix 통합 검증. submit() 가:
  1. `_resolve_sizing_canonical(data, strategy)` 호출 결과를 `bt.config` JSONB 에 저장
  2. `repo.commit()` 호출 (LESSON-019 broken bug 재발 방어)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
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


def _make_strategy(
    *,
    pine_source: str = _PINE_BARE,
    settings: dict | None = None,
    trading_sessions: list[str] | None = None,
) -> Strategy:
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


def _make_request(strategy_id, **overrides) -> CreateBacktestRequest:
    base: dict = {
        "strategy_id": strategy_id,
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "period_start": datetime(2024, 1, 1, tzinfo=UTC),
        "period_end": datetime(2024, 1, 7, tzinfo=UTC),
        "initial_capital": Decimal("10000"),
    }
    base.update(overrides)
    return CreateBacktestRequest(**base)


def _make_service(strategy: Strategy) -> tuple[BacktestService, AsyncMock]:
    """공통 mock 서비스 + repo (return)."""
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=None)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    ohlcv_provider = AsyncMock()
    dispatcher = AsyncMock()
    dispatcher.dispatch_backtest = lambda _: "task-id-bl188-v3"

    svc = BacktestService(
        repo=repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=ohlcv_provider,
        dispatcher=dispatcher,
    )
    return svc, repo


# 1. Live mirror 1x — submit() 가 sizing canonical 결과를 bt.config 에 저장.
@pytest.mark.asyncio
async def test_submit_live_mirror_persists_sizing_canonical_to_bt_config() -> None:
    strategy = _make_strategy(
        settings={
            "leverage": 1,
            "margin_mode": "isolated",
            "position_size_pct": 30.0,
        },
        trading_sessions=["asia"],
    )
    svc, repo = _make_service(strategy)
    req = _make_request(strategy.id)
    await svc.submit(req, user_id=strategy.user_id, idempotency_key=None)

    # bt 인스턴스의 config 검증
    repo.create.assert_awaited_once()
    bt = repo.create.call_args.args[0]
    assert bt.config["sizing_source"] == "live"
    assert bt.config["sizing_basis"] == "live_available_balance_approx_equity"
    assert bt.config["live_position_size_pct"] == 30.0
    assert bt.config["leverage_basis"] == 1.0
    # trading_sessions 는 strategy fallback (request 미명시 → strategy 값).
    assert bt.config["trading_sessions"] == ["asia"]
    # default_qty_* 는 Live mirror 시 None — bt.config 에 키 자체 미존재.
    assert "default_qty_type" not in bt.config
    assert "default_qty_value" not in bt.config

    # LESSON-019 commit spy
    repo.commit.assert_awaited_once()


# 2. Pine 명시 strategy → bt.config 에 default_qty_* 저장 + sizing_source="pine".
@pytest.mark.asyncio
async def test_submit_pine_full_persists_pine_canonical() -> None:
    strategy = _make_strategy(pine_source=_PINE_DEFAULT_QTY_FULL)
    svc, repo = _make_service(strategy)
    req = _make_request(strategy.id)
    await svc.submit(req, user_id=strategy.user_id, idempotency_key=None)

    bt = repo.create.call_args.args[0]
    assert bt.config["sizing_source"] == "pine"
    assert bt.config["sizing_basis"] == "pine_native"
    assert bt.config["default_qty_type"] == "strategy.cash"
    assert bt.config["default_qty_value"] == 5000.0
    assert "live_position_size_pct" not in bt.config

    repo.commit.assert_awaited_once()


# 3. request.trading_sessions 가 strategy.trading_sessions 보다 우선.
@pytest.mark.asyncio
async def test_submit_request_trading_sessions_takes_precedence() -> None:
    strategy = _make_strategy(trading_sessions=["asia", "london"])
    svc, repo = _make_service(strategy)
    req = _make_request(strategy.id, trading_sessions=["ny"])
    await svc.submit(req, user_id=strategy.user_id, idempotency_key=None)

    bt = repo.create.call_args.args[0]
    assert bt.config["trading_sessions"] == ["ny"]


# 4. fallback (no Pine, no Live, no manual) → sizing_source="fallback".
@pytest.mark.asyncio
async def test_submit_fallback_sizing_source() -> None:
    strategy = _make_strategy()  # settings=None, no Pine qty
    svc, repo = _make_service(strategy)
    req = _make_request(strategy.id)
    await svc.submit(req, user_id=strategy.user_id, idempotency_key=None)

    bt = repo.create.call_args.args[0]
    assert bt.config["sizing_source"] == "fallback"
    assert bt.config["sizing_basis"] == "fallback_qty1"
    assert bt.config["leverage_basis"] == 1.0
    # trading_sessions 미명시 → strategy 도 빈 list → bt.config 에 키 자체 미존재.
    assert "trading_sessions" not in bt.config

    repo.commit.assert_awaited_once()
