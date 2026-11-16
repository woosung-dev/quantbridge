"""OrderService.cancel_for_user — submitted 취소는 OrderDispatcher 포트로 예약한다 (CF4).

라우터 경유 HTTP 테스트(`test_router_cancel_cf4.py` · `test_router_layer_contract.py`)는
Celery adapter 가 `cancel_order_task.delay` 를 부르는지를 잰다. 여기서는 service 가
Celery 를 모르고 포트만 부르는지를 fake dispatcher 로 잰다.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.trading.models import OrderState
from src.trading.services.order_service import OrderService


class _RecordingOrderDispatcher:
    def __init__(self) -> None:
        self.executions: list[UUID] = []
        self.cancels: list[UUID] = []

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.executions.append(order_id)

    async def dispatch_order_cancel(self, order_id: UUID) -> None:
        self.cancels.append(order_id)


@pytest.mark.asyncio
async def test_cancel_submitted_requests_exchange_cancel_once_via_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """submitted 주문 취소는 포트에 취소 예약을 1회 요청하고 DB 를 건드리지 않는다."""
    from src.tasks import trading as task_mod

    delay = MagicMock()
    monkeypatch.setattr(task_mod.cancel_order_task, "delay", delay)

    order_id, user_id = uuid4(), uuid4()
    order = SimpleNamespace(id=order_id, state=OrderState.submitted, risk_context=None)
    repo = AsyncMock()
    repo.get_by_id_for_user = AsyncMock(return_value=order)
    dispatcher = _RecordingOrderDispatcher()

    service = OrderService(AsyncMock(), repo, dispatcher, AsyncMock())
    outcome = await service.cancel_for_user(order_id, user_id)

    assert outcome.kind == "exchange_requested"
    assert dispatcher.cancels == [order_id]
    assert dispatcher.executions == []
    delay.assert_not_called()
    repo.transition_pending_to_cancelled.assert_not_awaited()
    repo.commit.assert_not_awaited()
