"""코드 세션은 legacy Pine 경로에 들어가지 않는다. 모든 IO는 대역이다."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.code_runtime.models import CodeRuntimeError
from src.tasks.code_live_signal import code_quantity, completed_code_bars


@pytest.mark.asyncio
async def test_code_policy_dispatches_exclusive_task_helper(monkeypatch):
    from src.tasks.live_signal import _evaluate_session_with_engine

    session = object()
    live = SimpleNamespace(
        id=uuid4(), is_active=True, execution_snapshot={"source_policy": "code_v1"}
    )
    repo, strategy_repo = AsyncMock(), AsyncMock()
    repo.get_by_id.return_value = live
    helper = AsyncMock(return_value={"code_action": "hold"})
    monkeypatch.setattr(
        "src.trading.repositories.live_signal_session_repository.LiveSignalSessionRepository",
        lambda _: repo,
    )
    monkeypatch.setattr("src.strategy.repository.StrategyRepository", lambda _: strategy_repo)
    monkeypatch.setattr("src.tasks.code_live_signal.evaluate_code_session", helper)

    @asynccontextmanager
    async def sm():
        yield session

    assert await _evaluate_session_with_engine(live.id, "1m", sm) == {"code_action": "hold"}
    helper.assert_awaited_once_with(session, live)
    strategy_repo.find_by_id_and_owner.assert_not_awaited()
    repo.try_claim_bar.assert_not_awaited()


def test_decimal_frozen_baseline_sizing_and_step_rounding():
    # 고정 초기 기준선 방식이다. BT current cash의 복리 수량과 동일하다고 주장하지 않는다.
    assert code_quantity(
        capital=Decimal("10000"),
        percent=Decimal("10"),
        price=Decimal("30000"),
        step=Decimal("0.001"),
        minimum=Decimal("0.001"),
    ) == Decimal("0.032")
    assert code_quantity(
        capital=Decimal("10000"),
        percent=Decimal("10"),
        price=Decimal("30000"),
        step=Decimal("0.001"),
        minimum=Decimal("0.001"),
    ) != Decimal("11000") * Decimal("0.1") / Decimal("30000")


def test_incomplete_candle_cannot_enter_sl_or_size_reference():
    raw = [
        [0, 100, 102, 99, 101, 20],
        [60000, 101, 103, 100, 102, 20],
        [120000, 102, 999, 1, 500, 20],
    ]
    completed = completed_code_bars(
        raw, now=datetime.fromtimestamp(150, tz=UTC), interval_seconds=60
    )
    assert len(completed) == 2
    assert completed[-1]["close"] == "102"
    assert [bar["low"] for bar in completed[-2:]] == ["99", "100"]


def test_both_half_quantities_must_meet_minimum():
    with pytest.raises(CodeRuntimeError, match="50%"):
        code_quantity(
            capital=Decimal("10000"),
            percent=Decimal("1"),
            price=Decimal("30000"),
            step=Decimal("0.001"),
            minimum=Decimal("0.002"),
        )


@pytest.mark.parametrize("value", ["NaN", "0", "-1", "Infinity"])
def test_unknown_or_invalid_sizing_is_rejected(value):
    with pytest.raises(CodeRuntimeError):
        code_quantity(
            capital=Decimal(value),
            percent=Decimal("10"),
            price=Decimal("30000"),
            step=Decimal("0.001"),
            minimum=Decimal("0.001"),
        )
