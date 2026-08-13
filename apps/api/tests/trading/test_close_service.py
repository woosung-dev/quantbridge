# 세션 포지션 reduce-only 청산 서비스의 안전 계약을 검증한다
from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, ExchangeName, Order, OrderSide, OrderState, OrderType
from src.trading.providers import ConditionalOrderSnapshot, PositionSnapshot
from src.trading.services.close_service import ClosePositionService
from src.trading.services.order_service import OrderService

_SETTINGS = {"leverage": 3, "margin_mode": "cross", "position_size_pct": 10.0}


def _position(
    side: str = "long", leverage: Decimal | None = Decimal("3"), position_idx: int | None = None
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


def _conditional(
    order_id: str = "ex-cond-1", order_link_id: str | None = "link-1"
) -> ConditionalOrderSnapshot:
    """미체결 **조건부 진입** 한 건 — reduce_only=False 가 「진입」의 정의다."""
    return ConditionalOrderSnapshot(
        order_id=order_id,
        side="buy",
        kind="other",
        price=None,
        trigger_price=Decimal("100"),
        qty=Decimal("0.029"),
        reduce_only=False,
        position_idx=0,
        order_link_id=order_link_id,
    )


def _service(
    *,
    settings: dict[str, object] | None = _SETTINGS,
    positions: list[PositionSnapshot] | None = None,
    conditional_orders: list[ConditionalOrderSnapshot] | None = None,
    mode: ExchangeMode = ExchangeMode.demo,
    exchange: ExchangeName = ExchangeName.bybit,
    read_only: bool | None = None,
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
                read_only=read_only,
            )
        )
    )
    strategy_repo = SimpleNamespace(
        find_by_id_and_owner=AsyncMock(return_value=SimpleNamespace(settings=settings))
    )
    account_service = SimpleNamespace(get_credentials_for_order=AsyncMock(return_value=object()))
    # [BL-661] — 조건부 조회를 페이크에 **먼저** 심는다. 이게 없으면 `close_service` 가
    # 그것을 부르는 순간 이 파일 전건이 `AttributeError` 로 죽는다(회귀가 아니라 페이크 구멍).
    provider = SimpleNamespace(
        fetch_open_positions=AsyncMock(return_value=positions or []),
        fetch_open_conditional_orders=AsyncMock(return_value=conditional_orders or []),
    )
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


@pytest.mark.parametrize("settings", [None, {"leverage": 3}])
async def test_close_survives_unset_or_invalid_settings(settings) -> None:
    """BL-537 — 전략 설정이 없거나 깨져도 라이브 포지션은 닫혀야 한다.

    reduce-only 청산은 leverage/margin_mode 를 거래소에 보내지 않는다
    (`providers.py` create_order 의 `if not order.reduce_only:` 가 set_margin_mode 와
    set_leverage 를 **둘 다** 감싼다). 그래서 이 값들 때문에 422 를 내면, 설정을 비운
    사용자의 포지션이 앱에서 영구히 안 닫힌다 — 그게 07-28 의 9시간 방치다.
    ★`position_service` 의 close_blocked_reason 은 이 게이트를 평가하지 않아
      "누르면 실패하는 버튼" 이 됐다.
    """
    service, user_id, session, orders = _service(
        settings=settings, positions=[_position(leverage=Decimal("7"))]
    )

    await service.close_position(user_id, session.id)

    request = orders.execute.await_args.args[0]
    assert request.reduce_only is True
    assert request.leverage == 7
    assert request.margin_mode == "cross"


@pytest.mark.parametrize(
    ("position_leverage", "settings", "expected"),
    [
        (None, _SETTINGS, 3),
        (Decimal("0"), _SETTINGS, 3),
        (None, None, 1),
        (Decimal("0"), None, 1),
        (Decimal("999"), None, 125),
    ],
)
async def test_close_always_emits_a_positive_in_range_leverage(
    position_leverage, settings, expected
) -> None:
    """★leverage 는 futures/spot provider 를 가르는 판별자다.

    `tasks/trading.py` `_has_leverage` 는 not-null AND > 0 일 때만 futures 로 보낸다.
    0/None 이면 청산이 조용히 **스팟**으로 나가 linear 포지션을 못 닫는다.
    상한은 `OrderRequest.leverage` 의 `Field(ge=1, le=125)` — 넘기면 ValidationError 가
    🔴 청산 자체를 막는다.
    """
    service, user_id, session, orders = _service(
        settings=settings, positions=[_position(leverage=position_leverage)]
    )

    await service.close_position(user_id, session.id)

    request = orders.execute.await_args.args[0]
    assert request.leverage == expected


@pytest.mark.parametrize("settings", [_SETTINGS, None])
async def test_close_survives_non_finite_exchange_leverage(settings) -> None:
    """★거래소가 NaN/Inf 를 주면 `int()` 가 ValueError 를 던져 🔴 청산이 500 이 된다.

    `_position_snapshot_from_ccxt` 는 leverage 를 `finite_only` 없이 파싱하므로
    (`providers.py` `_decimal_or_none(position.get("leverage"), strict=True)`)
    `Decimal("NaN")` 이 그대로 올라온다. 비유한 값은 후보에서 건너뛰고 다음 출처로
    넘어가야 한다 — 청산은 어떤 필드 때문에도 막히면 안 된다.
    """
    service, user_id, session, orders = _service(
        settings=settings, positions=[_position(leverage=Decimal("NaN"))]
    )

    await service.close_position(user_id, session.id)

    request = orders.execute.await_args.args[0]
    assert request.leverage == (3 if settings else 1)


async def test_close_rejects_non_owned_session() -> None:
    service, user_id, session, _ = _service(positions=[_position()])
    service._session_repo.get_by_id = AsyncMock(return_value=SimpleNamespace(user_id=uuid4()))

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "live session not found"


async def test_close_rejects_read_only_key() -> None:
    service, user_id, session, orders = _service(positions=[_position()], read_only=True)

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "read_only_key"
    orders.execute.assert_not_awaited()


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


async def test_close_still_returns_no_open_position_when_truly_flat() -> None:
    """[BL-661] **음성 대조** — 포지션도 조건부도 없으면 계약은 한 글자도 안 바뀐다.

    `detail` 은 여전히 **문자열** `no_open_position` 이다. 이걸 dict 로 바꾸면
    `live_session_admin.py:385` 와 `real_broker/_harness.py:352` 의 `detail == "..."`
    비교가 조용히 거짓이 되고, harness 의 멱등 흡수가 **거짓말**이 된다.
    """
    service, user_id, session, orders = _service(positions=[], conditional_orders=[])

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "no_open_position"
    orders.execute.assert_not_awaited()


async def test_close_reports_resting_conditional_entries_when_flat() -> None:
    """[BL-661] 포지션이 비어도 **미체결 조건부 진입**이 남아 있으면 flat 이 아니다.

    그 주문은 나중에 트리거되어 아무도 안 보는 때 포지션을 연다. 종전에는 이 경우가
    `no_open_position` 과 **구분되지 않아** 운영 CLI 가 「정리 완료」로 읽었다.
    ★취소하지 않는다 — 보고만 한다(취소는 비가역, 미룸은 가역).
    """
    service, user_id, session, orders = _service(
        positions=[],
        conditional_orders=[_conditional("ex-cond-1"), _conditional("ex-cond-2")],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 409
    detail = exc_info.value.detail
    assert isinstance(detail, dict), "잔존 목록을 실으려면 detail 이 구조체여야 한다"
    assert detail["code"] == "resting_conditional_entries"
    assert detail["count"] == 2
    assert detail["detail"] == "포지션은 없지만 미체결 진입 주문 2건이 남아 있습니다."
    assert [o["order_id"] for o in detail["orders"]] == ["ex-cond-1", "ex-cond-2"]
    # 청산 주문은 나가지 않는다 — 포지션이 없으므로 낼 것이 없다.
    orders.execute.assert_not_awaited()


async def test_close_ignores_reduce_only_exits_when_flat() -> None:
    """[BL-661] **음성 대조** — 남은 것이 TP/SL 뿐이면 그건 「진입」이 아니다.

    ★이 자리가 내 1판 설계의 구멍이었다(codex G1 이 잡았다). 조회는 `reduce_only=None`
    이라 **진입과 청산이 함께** 온다(`providers.py:1276` 의 `if reduce_only is not None`
    단락이 필터를 꺼버린다). 돌아온 개수를 그대로 세면 **고아 TP/SL 만 남은 계정**이
    「조건부 진입이 남았다」로 오판돼 exit 3 이 나간다.
    분기·count·orders 에 들어가는 것은 `reduce_only is False` 뿐이어야 한다.
    """
    exit_leg = ConditionalOrderSnapshot(
        order_id="ex-tp-1",
        side="sell",
        kind="tp",
        price=None,
        trigger_price=Decimal("120"),
        qty=Decimal("0.029"),
        reduce_only=True,
        position_idx=0,
        order_link_id="link-tp",
    )
    service, user_id, session, orders = _service(positions=[], conditional_orders=[exit_leg])

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "no_open_position"
    orders.execute.assert_not_awaited()


async def test_close_detail_is_json_serializable() -> None:
    """[BL-661] detail 은 **그대로 JSON 으로 나간다** — `Decimal` 을 담으면 409 가 500 이 된다.

    Starlette `JSONResponse` 는 `json.dumps` 를 직접 부르고, `ConditionalOrderSnapshot` 의
    `qty`/`trigger_price` 는 `Decimal` 이다. 실측: `json.dumps({'qty': Decimal('0.029')})`
    → `TypeError: Object of type Decimal is not JSON serializable`.
    """
    service, user_id, session, _ = _service(positions=[], conditional_orders=[_conditional()])

    with pytest.raises(HTTPException) as exc_info:
        await service.close_position(user_id, session.id)

    # dict 인 것을 먼저 못 박는다 — 안 그러면 detail 이 문자열인 동안 `json.dumps` 가
    # 그냥 통과해 **아무것도 재지 않는 초록**이 된다(공허한 음성 대조).
    assert isinstance(exc_info.value.detail, dict)
    json.dumps(exc_info.value.detail)


async def test_close_fails_closed_when_conditional_fetch_fails() -> None:
    """[BL-661] 조건부 조회가 실패하면 **fail-closed** — flat 이라고 말하지 않는다.

    같은 조회를 쓰는 배타성 가드가 이미 fail-closed 다
    (`account_exclusivity.py:66-72`). 여기서 fail-open 하면 「거래소에 물어보지 못했다」가
    「조건부가 없다」로 둔갑해 [BL-661] 이 고치려는 바로 그 거짓 성공이 돌아온다.
    """
    service, user_id, session, orders = _service(positions=[])
    service._bybit_futures_provider.fetch_open_conditional_orders = AsyncMock(  # type: ignore[attr-defined]
        side_effect=ProviderError("bybit unreachable")
    )

    with pytest.raises(ProviderError):
        await service.close_position(user_id, session.id)

    orders.execute.assert_not_awaited()


async def test_close_uses_reduce_only_none_when_querying_conditionals() -> None:
    """[BL-661] `reduce_only=None` 은 **협상 불가 계약**이다.

    기본값 `True` 는 TP/SL(reduce-only)만 준다. 우리가 찾는 것은 **진입**이라
    `reduce_only=False` 다. `None` 이라야 필터가 꺼져 둘 다 온다 —
    `providers.py:1276` 의 `if reduce_only is not None` 단락이 그 기전이다.
    """
    service, user_id, session, _ = _service(positions=[], conditional_orders=[_conditional()])

    with pytest.raises(HTTPException):
        await service.close_position(user_id, session.id)

    provider = service._bybit_futures_provider  # type: ignore[attr-defined]
    assert provider.fetch_open_conditional_orders.await_args.kwargs["reduce_only"] is None


async def test_close_reports_resting_entries_when_position_open() -> None:
    """BL-684 — 열린 포지션에서도 남은 진입 주문을 응답으로 보고한다."""
    service, user_id, session, orders = _service(
        positions=[_position()],
        conditional_orders=[_conditional("ex-entry-1"), _conditional("ex-entry-2")],
    )

    response = await service.close_position(user_id, session.id)

    assert response.resting_entries_unknown is False
    assert [order.order_id for order in response.resting_entries] == ["ex-entry-1", "ex-entry-2"]
    assert response.detail == "reduce-only market close accepted · 미체결 진입 주문 2건이 남아 있다"
    orders.execute.assert_awaited_once()
    provider = service._bybit_futures_provider  # type: ignore[attr-defined]
    assert provider.fetch_open_conditional_orders.await_count == 1
    assert provider.fetch_open_conditional_orders.await_args.kwargs["reduce_only"] is None


async def test_close_reports_no_resting_entries_when_position_open() -> None:
    """BL-684 — 조회 성공의 빈 목록은 확인 실패와 구분해 기존 성공 문구를 보존한다."""
    service, user_id, session, orders = _service(positions=[_position()], conditional_orders=[])

    response = await service.close_position(user_id, session.id)

    assert response.resting_entries == []
    assert response.resting_entries_unknown is False
    assert response.detail == "reduce-only market close accepted"
    orders.execute.assert_awaited_once()


async def test_close_continues_when_resting_entry_fetch_fails() -> None:
    """BL-684 — 열린 포지션은 잔량 조회 장애가 있어도 청산 주문을 낸다."""
    service, user_id, session, orders = _service(positions=[_position()])
    service._bybit_futures_provider.fetch_open_conditional_orders = AsyncMock(  # type: ignore[attr-defined]
        side_effect=ProviderError("bybit unreachable")
    )

    response = await service.close_position(user_id, session.id)

    orders.execute.assert_awaited_once()
    assert response.resting_entries_unknown is True
    assert response.resting_entries == []
    # ★문구가 원인을 단정하지 않는다 — 포획이 `except Exception` 이라 프로그래밍 오류도
    #   여기로 오는데, 그것을 「거래소 조회 오류」라고 부르면 거짓 보고다. 원인은 로그의
    #   `error=<예외 타입>` 에 남는다.
    assert response.detail == "reduce-only market close accepted · 미체결 진입 주문 확인 실패"


async def test_close_fetches_resting_entries_before_executing_close() -> None:
    """BL-684 — 주문 접수 뒤 조회 예외가 500으로 보이는 모호함을 만들지 않는다."""
    service, user_id, session, orders = _service(positions=[_position()])
    provider = service._bybit_futures_provider  # type: ignore[attr-defined]
    call_order: list[str] = []

    async def _fetch_entries(*args, **kwargs):
        call_order.append("fetch_entries")
        return []

    async def _execute(*args, **kwargs):
        call_order.append("execute")
        return orders.execute.return_value

    provider.fetch_open_conditional_orders.side_effect = _fetch_entries
    orders.execute.side_effect = _execute

    await service.close_position(user_id, session.id)

    assert call_order == ["fetch_entries", "execute"]


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
