"""코드 세션은 legacy Pine 경로에 들어가지 않는다. 모든 IO는 대역이다."""

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.code_runtime.models import CodeRuntimeError
from src.tasks.code_live_signal import code_quantity


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
    ) == Decimal("0.033")
    assert code_quantity(
        capital=Decimal("10000"),
        percent=Decimal("10"),
        price=Decimal("30000"),
        step=Decimal("0.001"),
        minimum=Decimal("0.001"),
    ) != Decimal("11000") * Decimal("0.1") / Decimal("30000")


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
