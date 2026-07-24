# 세션 포지션 reduce-only 청산 서비스의 안전 계약을 검증한다
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, ExchangeName, Order, OrderSide, OrderState, OrderType
from src.trading.providers import PositionSnapshot
from src.trading.services.close_service import ClosePositionService
from src.trading.services.order_service import OrderService

_SETTINGS = {"leverage": 3, "margin_mode": "cross", "position_size_pct": 10.0}


def _position(
    side: str = "long", leverage: Decimal = Decimal("3"), position_idx: int | None = None
) -> PositionSnapshot:
    return PositionSnapshot(
        side=side,
        size=Decimal("1.25"),
        entry_price=Decimal("100"),
        mark_price=Decimal("101"),
        unrealized_pnl=Decimal("1"),
        liquidation_price=None,
        leverage=leverage,
        take_profit_price=None,
        stop_loss_price=None,
        position_idx=position_idx,
    )


def _service(
    *,
    settings: dict[str, object] | None = _SETTINGS,
    positions: list[PositionSnapshot] | None = None,
    mode: ExchangeMode = ExchangeMode.demo,
    exchange: ExchangeName = ExchangeName.bybit,
    order_service: object | None = None,
) -> tuple[ClosePositionService, object, object, object]:
    user_id = uuid4()
    session = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
    )
    session_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=session))
    account_repo = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                id=session.exchange_account_id,
                mode=mode,
                exchange=exchange,
            )
        )
    )
    strategy_repo = SimpleNamespace(
        find_by_id_and_owner=AsyncMock(return_value=SimpleNamespace(settings=settings))
    )
    account_service = SimpleNamespace(get_credentials_for_order=AsyncMock(return_value=object()))
    provider = SimpleNamespace(fetch_open_positions=AsyncMock(return_value=positions or []))
    response = SimpleNamespace(id=uuid4(), state=OrderState.pending)
    orders = order_service or SimpleNamespace(execute=AsyncMock(return_value=(response, False)))
    return (
        ClosePositionService(
            session_repo=session_repo,
            account_repo=account_repo,
            strategy_repo=strategy_repo,
            account_service=account_service,
            bybit_futures_provider=provider,
            order_service=orders,  # type: ignore[arg-type]
        ),
        user_id,
        session,
        orders,
    )


@pytest.mark.parametrize(
    ("settings", "reason"),
    [(None, "settings_unset"), ({"leverage": 3}, "settings_invalid")],
)
async def test_close_rejects_unset_or_invalid_settings(settings, reason) -> None:
    service, user_id, session, orders = _service(settings=settings, positions=[_position()])

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == reason
    orders.execute.assert_not_awaited()


async def test_close_rejects_non_owned_session() -> None:
    service, user_id, session, _ = _service(positions=[_position()])
    service._session_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(user_id=uuid4())
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "live session not found"


@pytest.mark.parametrize(
    ("positions", "reason"),
    [([], "no_open_position"), ([_position(), _position("short")], "hedge_unsupported")],
)
async def test_close_rejects_flat_or_hedged_position(positions, reason) -> None:
    service, user_id, session, orders = _service(positions=positions)

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == reason
    orders.execute.assert_not_awaited()


async def test_close_rejects_nonzero_position_index() -> None:
    service, user_id, session, orders = _service(positions=[_position(position_idx=1)])

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "hedge_unsupported"
    orders.execute.assert_not_awaited()


@pytest.mark.parametrize(
    ("position_side", "close_side"),
    [("long", OrderSide.sell), ("short", OrderSide.buy)],
)
async def test_close_builds_reduce_only_futures_order(position_side, close_side) -> None:
    service, user_id, session, orders = _service(
        positions=[_position(position_side, leverage=Decimal("7"))]
    )

    response = await service.close_position(user_id, session.id)

    request = orders.execute.await_args.args[0]
    assert request.side == close_side
    assert request.type == OrderType.market
    assert request.quantity == Decimal("1.25")
    assert request.price is None
    assert request.reduce_only is True
    assert request.leverage == 7
    assert request.risk_percent is None
    assert orders.execute.await_args.kwargs == {"idempotency_key": None, "flatten": True}
    assert response.order_id == orders.execute.return_value[0].id
    assert response.state == OrderState.pending


@pytest.mark.parametrize("failure", ["fetch", "execute"])
async def test_close_propagates_provider_errors(failure: str) -> None:
    service, user_id, session, orders = _service(positions=[_position()])
    if failure == "fetch":
        service._bybit_futures_provider.fetch_open_positions.side_effect = ProviderError("down")
    else:
        orders.execute.side_effect = ProviderError("down")

    with pytest.raises(ProviderError):
        await service.close_position(user_id, session.id)


async def test_close_reaches_order_service_outer_commit() -> None:
    """LESSON-019: 청산도 OrderService의 outer commit 경로를 반드시 지난다."""
    session = AsyncMock(spec=AsyncSession)
    session.begin_nested = MagicMock(return_value=AsyncMock())
    saved_order = Order(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.sell,
        type=OrderType.market,
        quantity=Decimal("1.25"),
        price=None,
        state=OrderState.pending,
        leverage=3,
        margin_mode="cross",
        reduce_only=True,
    )
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=saved_order)
    repo.get_by_id = AsyncMock(return_value=saved_order)
    order_service = OrderService(
        session=session,
        repo=repo,
        dispatcher=AsyncMock(),
        kill_switch=AsyncMock(),
    )
    service, user_id, session_model, _ = _service(
        positions=[_position()], order_service=order_service
    )
    saved_order.strategy_id = session_model.strategy_id
    saved_order.exchange_account_id = session_model.exchange_account_id

    await service.close_position(user_id, session_model.id)

    session.commit.assert_awaited_once()
