# 조건부 진입 reconcile의 거래소 배선과 귀속 불변식을 검증한다.
from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

import src.tasks.celery_app
import src.tasks.live_signal  # noqa: F401

celery_module = sys.modules["src.tasks.celery_app"]
live_signal_module = sys.modules["src.tasks.live_signal"]

from src.strategy.pine_v2.event_loop import PendingOrderSnapshot  # noqa: E402
from src.strategy.schemas import StrategySettings  # noqa: E402
from src.trading.models import OrderSide, OrderState  # noqa: E402
from src.trading.providers import ConditionalOrderSnapshot, PositionSnapshot  # noqa: E402
from src.trading.services.conditional_entry_planner import (  # noqa: E402
    build_conditional_entry_key,
    build_market_converted_entry_key,
    parse_conditional_entry_key,
)


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


_BAR_TIME = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _session() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval="1m",
        is_active=True,
    )


def _pending(
    trade_id: str = "entry",
    *,
    direction: str = "long",
    target_position: Decimal = Decimal("1"),
    stop_price: Decimal = Decimal("100"),
    take_profit: Decimal | None = None,
    stop_loss: Decimal | None = None,
    trailing_stop: Decimal | None = None,
) -> PendingOrderSnapshot:
    return PendingOrderSnapshot(
        trade_id=trade_id,
        direction=direction,  # type: ignore[arg-type]
        target_position=target_position,
        entry_qty=abs(target_position),
        stop_price=stop_price,
        placed_bar=1,
        comment="entry",
        take_profit=take_profit,
        stop_loss=stop_loss,
        trailing_stop=trailing_stop,
    )


def _position(side: str, size: Decimal) -> PositionSnapshot:
    return PositionSnapshot(
        side=side,
        size=size,
        entry_price=None,
        mark_price=None,
        unrealized_pnl=None,
        liquidation_price=None,
        leverage=None,
        take_profit_price=None,
        stop_loss_price=None,
        position_idx=0,
    )


def _result(pending_orders: list[PendingOrderSnapshot]) -> SimpleNamespace:
    return SimpleNamespace(pending_orders=pending_orders)


def _order(
    session: SimpleNamespace,
    *,
    trade_id: str = "entry",
    strategy_id: UUID | None = None,
    exchange_account_id: UUID | None = None,
    exchange_order_id: str | None = None,
    submitted_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        strategy_id=strategy_id or session.strategy_id,
        exchange_account_id=exchange_account_id or session.exchange_account_id,
        trigger_price=Decimal("100"),
        quantity=Decimal("1"),
        side=OrderSide.buy,
        trigger_direction=1,
        reduce_only=False,
        state=OrderState.submitted,
        exchange_order_id=exchange_order_id,
        # BL-500 나이 게이트 기본값 = "방금 제출" — 게이트가 열리려면 테스트가 명시적으로
        # 늙혀야 한다. 기본이 늙은 값이면 무관한 테스트가 조용히 제거 경로를 탄다.
        submitted_at=submitted_at if submitted_at is not None else datetime.now(UTC),
        idempotency_key=build_conditional_entry_key(
            session.id, trade_id, _BAR_TIME, Decimal("100"), Decimal("1")
        ),
    )


def _exchange_order(order: SimpleNamespace) -> ConditionalOrderSnapshot:
    return ConditionalOrderSnapshot(
        order_id=order.exchange_order_id or "exchange-entry",
        side="buy",
        kind="other",
        price=None,
        trigger_price=Decimal("100"),
        qty=Decimal("1"),
        reduce_only=False,
        position_idx=0,
        order_link_id=str(order.id),
    )


def _patch_reconcile(
    monkeypatch: pytest.MonkeyPatch,
    *,
    local_orders: list[SimpleNamespace] | None = None,
    exchange_orders: list[ConditionalOrderSnapshot] | None = None,
    positions: list[PositionSnapshot] | None = None,
    database_orders: list[SimpleNamespace] | None = None,
    precision_error: Exception | None = None,
    execute_error: Exception | None = None,
    active_sessions: list[SimpleNamespace] | None = None,
    active_sessions_by_account: dict[UUID, list[SimpleNamespace]] | None = None,
    account_row: SimpleNamespace | None = None,
    sibling_accounts: list[SimpleNamespace] | None = None,
    pending_cancel_rows: int = 1,
    fresh_state: OrderState | None = OrderState.submitted,
    fresh_exchange_order_id: str | None = "exchange-raced",
    exchange_orders_error: Exception | None = None,
    probe_status: str | None = "submitted",
    probe_error: Exception | None = None,
    probe_filled_price: Decimal | None = None,
    probe_filled_quantity: Decimal | None = None,
    terminal_write_back_rows: int = 1,
    last_price: Decimal | None = Decimal("64"),
    recent_market_conversion: bool = False,
) -> SimpleNamespace:
    # ★BL-583 — 아래 패치들은 **클래스 정의 모듈**의 속성을 갈아치운다. 그 상태에서 소비
    #   모듈이 **처음** 적재되면 그 모듈 최상단의 `from … import OrderRepository` 가 MagicMock
    #   을 자기 전역으로 **복사**하고, monkeypatch teardown 은 정의 모듈만 되돌리므로 그
    #   복사본이 세션 끝까지 남는다. 리컨사일러가 밟는 지연 import 는 두 곳이고 둘 다 그런
    #   소비 모듈이다:
    #     `live_signal.py:834`  `_write_back_confirmed_terminal`     → `src.tasks.trading`
    #                                                                 (`trading.py:91`)
    #     `live_signal.py:3027` `_conditional_entry_janitor_delay_…` → `src.tasks.orphan_scanner`
    #                                                                 (`orphan_scanner.py:25`)
    #   실측 피해: 앞은 `tests/trading/test_cancel_order_task.py` 2건이 남의 가짜 repo 로
    #   `get_by_id` 해 `not_found`(2 failed), 뒤는 `tests/trading/test_orphan_scanner.py`
    #   3건(3 failed). 패치보다 먼저 적재해 그 창을 없앤다 — 프로덕션의 지연 import 는 그대로
    #   둔다. 모듈수준으로 올리면 import 실패 등급이 「평가 1건 실패」에서 **celery 태스크
    #   미등록**으로 올라간다(`test_live_signal_import_blast_radius.py` docstring).
    # (별칭을 붙이는 이유는 ruff 뿐이다 — `import src.tasks.x` 두 줄은 같은 `src` 이름에
    #  묶여 한쪽 `noqa` 가 RUF100 으로 떨어진다. 별칭이면 줄 순서에 무관하게 안정적이다.)
    from src.tasks import orphan_scanner as _preload_orphan_scanner  # noqa: F401
    from src.tasks import trading as _preload_trading  # noqa: F401

    session = AsyncMock()
    order_repo = AsyncMock()
    order_repo.list_resting_conditional_entries = AsyncMock(return_value=local_orders or [])
    orders_by_id = {order.id: order for order in database_orders or local_orders or []}

    async def get_by_id(order_id: UUID) -> SimpleNamespace | None:
        return orders_by_id.get(order_id)

    order_repo.get_by_id = AsyncMock(side_effect=get_by_id)
    order_repo.transition_to_cancelled = AsyncMock(return_value=1)
    # BL-560 — terminal write-back. rowcount 는 단일행 UPDATE 승자 규약의 입력이라
    # 기본값을 1(승자)로 두고, 패자 경로는 테스트가 명시적으로 0 을 준다.
    order_repo.transition_to_filled = AsyncMock(return_value=terminal_write_back_rows)
    order_repo.transition_to_rejected = AsyncMock(return_value=terminal_write_back_rows)
    order_repo.transition_pending_to_cancelled = AsyncMock(return_value=pending_cancel_rows)
    order_repo.get_state_and_exchange_id_fresh = AsyncMock(
        return_value=None if fresh_state is None else (fresh_state, fresh_exchange_order_id)
    )
    order_repo.has_recent_market_converted_entry = AsyncMock(return_value=recent_market_conversion)
    order_repo.commit = AsyncMock()

    account_repo = AsyncMock()
    # [BL-517] — stand-down 축이 `exchange_uid` 형제 행까지 본다. 기본값은 **uid 없음**이라
    # 자기 행만 보는 폴백을 타고, 그래서 기존 케이스의 관측 동작이 그대로 보존된다.
    own_account_row = account_row or SimpleNamespace(id=uuid4(), exchange_uid=None)
    account_repo.get_by_id = AsyncMock(return_value=own_account_row)
    # ★페이크는 프로덕션의 제약 축을 그대로 흉내낸다(`backend/AGENTS.md` §10 규약 3).
    #   실제 `list_by_exchange_uid` 는 `WHERE exchange_uid == uid ORDER BY created_at ASC`
    #   (`exchange_account_repository.py:57-63`)라 **자기 행을 포함**한다. 페이크가 자기 행을
    #   빼면 `ownership_scope_ids` 의 `if account.id not in ids` 폴백이 **테스트에서만** 발화해,
    #   프로덕션에서 도달하지 않는 경로를 재게 된다 — 재현하려던 위상이 페이크 안에서 소멸한다.
    account_repo.list_by_exchange_uid = AsyncMock(
        return_value=[own_account_row, *sibling_accounts] if sibling_accounts else []
    )
    kill_switch_repo = AsyncMock()
    kill_switch_repo.get_active = AsyncMock(return_value=None)

    # 같은 계정·심볼의 다른 활성 세션 = 계정 순포지션이 우리 것만이 아니라는 신호.
    live_session_repo = AsyncMock()

    def list_active_by_account(account_id: UUID) -> list[SimpleNamespace]:
        if active_sessions_by_account is None:
            return active_sessions or []
        return active_sessions_by_account.get(account_id, active_sessions or [])

    live_session_repo.list_active_by_account = AsyncMock(side_effect=list_active_by_account)

    import src.trading.repositories.exchange_account_repository as account_repo_module
    import src.trading.repositories.kill_switch_event_repository as kill_switch_repo_module
    import src.trading.repositories.live_signal_session_repository as live_session_repo_module
    import src.trading.repositories.order_repository as order_repo_module

    monkeypatch.setattr(
        live_session_repo_module,
        "LiveSignalSessionRepository",
        MagicMock(return_value=live_session_repo),
    )
    monkeypatch.setattr(order_repo_module, "OrderRepository", MagicMock(return_value=order_repo))
    monkeypatch.setattr(
        account_repo_module, "ExchangeAccountRepository", MagicMock(return_value=account_repo)
    )
    monkeypatch.setattr(
        kill_switch_repo_module,
        "KillSwitchEventRepository",
        MagicMock(return_value=kill_switch_repo),
    )

    provider = AsyncMock()
    provider.fetch_open_conditional_orders = AsyncMock(
        return_value=exchange_orders or [], side_effect=exchange_orders_error
    )
    provider.fetch_open_positions = AsyncMock(return_value=positions or [])
    provider.fetch_last_price = AsyncMock(return_value=last_price)
    provider.cancel_order = AsyncMock()
    provider.fetch_order = AsyncMock(
        return_value=SimpleNamespace(
            exchange_order_id="probe",
            status=probe_status,
            filled_price=probe_filled_price,
            filled_quantity=probe_filled_quantity,
            raw={},
        ),
        side_effect=probe_error,
    )

    import src.trading.providers as providers_module

    monkeypatch.setattr(providers_module, "BybitFuturesProvider", MagicMock(return_value=provider))

    exchange_service = AsyncMock()
    exchange_service.get_credentials_for_order = AsyncMock(return_value=SimpleNamespace())
    import src.trading.services.account_service as account_service_module

    monkeypatch.setattr(
        account_service_module, "ExchangeAccountService", MagicMock(return_value=exchange_service)
    )

    order_service = AsyncMock()
    if execute_error is None:
        order_service.execute = AsyncMock(return_value=(SimpleNamespace(id=uuid4()), False))
    else:
        order_service.execute = AsyncMock(side_effect=execute_error)
    import src.trading.services.order_service as order_service_module

    monkeypatch.setattr(order_service_module, "OrderService", MagicMock(return_value=order_service))

    market_exchange = SimpleNamespace(
        load_markets=AsyncMock(side_effect=precision_error),
        market=MagicMock(return_value={"precision": {"amount": "0.001", "price": "0.1"}}),
    )
    monkeypatch.setattr(
        celery_module,
        "get_ccxt_provider_for_worker",
        lambda: SimpleNamespace(exchange=market_exchange),
    )

    return SimpleNamespace(
        order_repo=order_repo,
        account_repo=account_repo,
        live_session_repo=live_session_repo,
        provider=provider,
        order_service=order_service,
        market_exchange=market_exchange,
        sm=lambda: _SessionContext(session),
    )


async def _reconcile(
    session: SimpleNamespace,
    result: SimpleNamespace,
    harness: SimpleNamespace,
    *,
    market_orders_in_flight: bool = False,
    fallback_reference_price: Decimal | None = None,
    max_trigger_breach_pct: float | None = None,
) -> None:
    await live_signal_module._reconcile_conditional_entries(
        session,
        result,
        StrategySettings(
            leverage=2,
            margin_mode="cross",
            position_size_pct=10,
            max_trigger_breach_pct=max_trigger_breach_pct,
        ),
        harness.sm,
        bar_time=_BAR_TIME,
        market_orders_in_flight=market_orders_in_flight,
        fallback_reference_price=fallback_reference_price,
    )


def test_conditional_key_round_trip_preserves_colon_in_trade_id() -> None:
    session_id = uuid4()

    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    epoch = int(bar_time.timestamp())

    key = build_conditional_entry_key(
        session_id, "entry:leg:one", bar_time, Decimal("100"), Decimal("1")
    )

    assert key == f"live:{session_id}:cond:{epoch}:100:1:entry:leg:one"
    assert parse_conditional_entry_key(key) == (session_id, "entry:leg:one")


def test_conditional_key_changes_per_bar_so_replacement_actually_dispatches() -> None:
    """★같은 의도라도 bar 가 다르면 key 가 달라야 한다.

    key 가 (trade_id, 가격, 수량) 만으로 결정되면 취소 후 재등재 때 OrderService 가
    dispatch 없이 캐시 응답을 돌려준다 - 거래소엔 아무것도 없는데 DB 와 metric 은
    "등재됨" 이라고 보고한다.
    """
    session_id = uuid4()
    args = ("PivRevLE", Decimal("100"), Decimal("1"))
    first = build_conditional_entry_key(
        session_id, args[0], datetime(2026, 5, 1, 12, 0, tzinfo=UTC), *args[1:]
    )
    second = build_conditional_entry_key(
        session_id, args[0], datetime(2026, 5, 1, 13, 0, tzinfo=UTC), *args[1:]
    )

    assert first != second
    assert parse_conditional_entry_key(first) == parse_conditional_entry_key(second)


def test_conditional_key_rejects_unrepresentable_trade_ids() -> None:
    """빈 trade_id 와 200자 초과는 발주하면 안 된다.

    전자는 파서가 되짚지 못해 우리 주문을 영원히 남의 것으로 보게 만들고,
    후자는 VARCHAR(200) 오류가 상위 except 에 삼켜져 "장전됐다고 믿는데 거래소엔 없는"
    상태를 만든다.
    """
    session_id = uuid4()
    bar_time = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    assert (
        build_conditional_entry_key(session_id, "  ", bar_time, Decimal("1"), Decimal("1")) is None
    )
    assert (
        build_conditional_entry_key(session_id, "x" * 200, bar_time, Decimal("1"), Decimal("1"))
        is None
    )


@pytest.mark.asyncio
async def test_zero_cost_shortcut_skips_exchange_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([]), harness)

    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.provider.fetch_last_price.assert_not_awaited()


@pytest.mark.asyncio
async def test_reference_price_comes_from_exchange_last_not_bar_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price is None
    assert harness.provider.fetch_last_price.await_count == 2
    harness.provider.fetch_last_price.assert_awaited_with(ANY, session.symbol)


@pytest.mark.asyncio
async def test_reference_price_not_fetched_when_no_conditional_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([]), harness)

    harness.provider.fetch_last_price.assert_not_awaited()


@pytest.mark.asyncio
async def test_reference_price_failure_still_places_conditional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id="exchange-old")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        exchange_orders=[_exchange_order(stale)],
        last_price=None,
    )

    await _reconcile(
        session,
        _result([_pending("new")]),
        harness,
        fallback_reference_price=Decimal("99"),
    )

    harness.provider.fetch_last_price.assert_awaited_once_with(ANY, session.symbol)
    harness.provider.cancel_order.assert_awaited_once_with(ANY, "exchange-old", session.symbol)
    harness.order_service.execute.assert_awaited_once()
    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price == Decimal("100")


@pytest.mark.asyncio
async def test_reference_price_failure_forbids_market_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=None)

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        fallback_reference_price=Decimal("110"),
    )

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_reference_forbids_conversion_even_if_reprobe_would_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★평가자 추가 게이트 - 전환 금지의 주체가 폴백 판정임을 분리해 고정한다.

    첫 조회 실패와 발주 직전 재확인이 같은 대역을 쓰면 둘 다 None 이라 어느 가드가
    막았는지 구분되지 않는다(변이 F7 이 그 틈으로 통과했다). 첫 조회만 실패시키고
    재확인은 성공시키면 폴백 판정만 남는다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=None)
    harness.provider.fetch_last_price = AsyncMock(side_effect=[None, Decimal("110")])

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        fallback_reference_price=Decimal("110"),
    )

    assert harness.provider.fetch_last_price.await_count == 1
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejected_recent_conversion_still_suppresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        last_price=Decimal("110"),
        recent_market_conversion=True,
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_repo.has_recent_market_converted_entry.assert_awaited_once()
    harness.order_service.execute.assert_not_awaited()
    harness.provider.fetch_last_price.assert_awaited_once_with(ANY, session.symbol)


@pytest.mark.asyncio
async def test_breach_reverted_before_place_skips_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    harness.provider.fetch_last_price.side_effect = [Decimal("110"), Decimal("99")]

    await _reconcile(session, _result([_pending()]), harness)

    assert harness.provider.fetch_last_price.await_count == 2
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_breach_exceeding_cap_at_reprobe_is_not_converted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.common.metrics import qb_live_conditional_guard_total

    cap = Decimal("1")
    initial_reference_price = Decimal("100.5")
    reprobe_reference_price = Decimal("102")
    initial_breach_pct = (
        abs(initial_reference_price - Decimal("100")) / initial_reference_price * Decimal("100")
    )
    reprobe_breach_pct = (
        abs(reprobe_reference_price - Decimal("100")) / reprobe_reference_price * Decimal("100")
    )
    assert initial_breach_pct <= cap < reprobe_breach_pct

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=initial_reference_price)
    harness.provider.fetch_last_price = AsyncMock(
        side_effect=[initial_reference_price, reprobe_reference_price]
    )
    counter = qb_live_conditional_guard_total.labels(outcome="breach_capped")
    before = counter._value.get()

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=float(cap),
    )

    assert harness.provider.fetch_last_price.await_count == 2
    harness.order_service.execute.assert_not_awaited()
    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_reprobe_within_cap_still_converts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cap = Decimal("1")
    initial_reference_price = Decimal("100.5")
    reprobe_reference_price = Decimal("100.75")
    initial_breach_pct = (
        abs(initial_reference_price - Decimal("100")) / initial_reference_price * Decimal("100")
    )
    reprobe_breach_pct = (
        abs(reprobe_reference_price - Decimal("100")) / reprobe_reference_price * Decimal("100")
    )
    assert initial_breach_pct <= cap
    assert reprobe_breach_pct <= cap

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=initial_reference_price)
    harness.provider.fetch_last_price = AsyncMock(
        side_effect=[initial_reference_price, reprobe_reference_price]
    )

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=float(cap),
    )

    assert harness.provider.fetch_last_price.await_count == 2
    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_interval_skips_conversion(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.common.metrics import qb_live_conditional_guard_total

    session = _session()
    session.interval = "2h"
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    counter = qb_live_conditional_guard_total.labels(outcome="convert_suppressed")
    before = counter._value.get()

    with caplog.at_level(logging.WARNING):
        await _reconcile(session, _result([_pending()]), harness)

    harness.provider.fetch_last_price.assert_awaited_once_with(ANY, session.symbol)
    harness.order_repo.has_recent_market_converted_entry.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()
    assert counter._value.get() == before + 1
    assert any(
        record.message == "live_conditional_reconcile_market_convert_suppressed"
        and getattr(record, "reason", None) == "unknown_interval"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_deferred_legs_after_conversion_are_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.common.metrics import qb_live_conditional_reconcile_errors_total

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    counter = qb_live_conditional_reconcile_errors_total.labels(
        stage="deferred_after_market_convert"
    )
    before = counter._value.get()

    await _reconcile(session, _result([_pending("a"), _pending("b")]), harness)

    assert harness.order_service.execute.await_count == 1
    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_market_conversion_stops_further_placements_in_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending("a"), _pending("b")]), harness)

    assert harness.order_service.execute.await_count == 1
    assert harness.order_service.execute.await_args.args[0].trigger_price is None


@pytest.mark.asyncio
async def test_converted_order_has_no_trigger_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price is None
    assert request.trigger_direction is None
    assert request.trigger_by is None


@pytest.mark.asyncio
async def test_converted_order_uses_distinct_idempotency_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    key = harness.order_service.execute.await_args.kwargs["idempotency_key"]
    assert key is not None
    assert ":condmkt:" in key
    assert key != build_conditional_entry_key(
        session.id, "entry", _BAR_TIME, Decimal("100"), Decimal("1")
    )


@pytest.mark.asyncio
async def test_converted_key_is_not_parsed_as_resting_conditional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(session, _result([_pending()]), harness)

    key = harness.order_service.execute.await_args.kwargs["idempotency_key"]
    assert key == build_market_converted_entry_key(
        session.id, "entry", _BAR_TIME, Decimal("100"), Decimal("1")
    )
    assert parse_conditional_entry_key(key) is None


@pytest.mark.asyncio
async def test_missing_actual_places_conditional_market_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price == Decimal("100")
    assert request.trigger_direction == 1
    assert request.type.value == "market"
    assert request.price is None


@pytest.mark.asyncio
async def test_matching_exchange_actual_is_not_replaced(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    order = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(
        monkeypatch,
        exchange_orders=[_exchange_order(order)],
        database_orders=[order],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()
    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_disappeared_desired_cancels_resting_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    order = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(monkeypatch, local_orders=[order])

    await _reconcile(session, _result([]), harness)

    harness.provider.cancel_order.assert_awaited_once_with(ANY, "exchange-entry", "BTC/USDT")
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_exchange_order_is_never_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    foreign_order = _order(
        session, trade_id="otherleg", strategy_id=uuid4(), exchange_order_id="foreign-entry"
    )
    unlinked_order = ConditionalOrderSnapshot(
        order_id="unlinked-entry",
        side="buy",
        kind="other",
        price=None,
        trigger_price=Decimal("100"),
        qty=Decimal("1"),
        reduce_only=False,
        position_idx=0,
        order_link_id="not-a-uuid",
    )
    harness = _patch_reconcile(
        monkeypatch,
        exchange_orders=[unlinked_order, _exchange_order(foreign_order)],
        database_orders=[foreign_order],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_local_in_flight_order_prevents_duplicate_placement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    local_order = _order(session)
    harness = _patch_reconcile(monkeypatch, local_orders=[local_order])

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_order_service_error_does_not_escape_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, execute_error=RuntimeError("gate failed"))

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_precision_failure_skips_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, precision_error=RuntimeError("markets unavailable"))

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_hedge_positions_abort_reconcile(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        positions=[
            PositionSnapshot(
                side="long",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=1,
            ),
            PositionSnapshot(
                side="short",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=2,
            ),
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_hedge_positions_also_cancel_our_resting_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hedge mode 는 발주만 멈추는 게 아니라 이미 올려둔 우리 주문도 걷는다.

    포지션 산술을 더 이상 신뢰할 수 없는 상태인데 기존 조건부 진입을 남겨두면 그게
    잘못된 전제 위에서 체결된다. 취소는 포지션을 늘리지 않으므로 어느 경우에도 안전하다.
    """
    session = _session()
    resting = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[resting],
        exchange_orders=[_exchange_order(resting)],
        positions=[
            PositionSnapshot(
                side="long",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=1,
            ),
            PositionSnapshot(
                side="short",
                size=Decimal("1"),
                entry_price=None,
                mark_price=None,
                unrealized_pnl=None,
                liquidation_price=None,
                leverage=None,
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=2,
            ),
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()
    harness.provider.cancel_order.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_strategy_session_on_same_account_symbol_stands_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """같은 계정·심볼에 다른 전략 세션이 살아 있으면 사이징 전제가 깨진다.

    활성 세션 unique 키가 `strategy_id` 를 포함하므로 구조적으로 허용되는 배치다.
    reconciler 는 **계정 전체** 순포지션을 세션별 target 에서 빼므로, 전략 A 가 +1 을
    보유한 상태에서 전략 B 가 -1 을 목표하면 B 는 수량 2 를 내 A 의 포지션까지 닫고
    반전시킨다. 그래서 stand-down 하고 우리 주문을 걷는다.
    """
    session = _session()
    resting = _order(session, exchange_order_id="exchange-entry")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[resting],
        exchange_orders=[_exchange_order(resting)],
        active_sessions=[
            SimpleNamespace(
                id=uuid4(),  # 다른 세션
                strategy_id=uuid4(),  # 다른 전략
                exchange_account_id=session.exchange_account_id,
                symbol=session.symbol,  # 같은 심볼
            )
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()
    harness.provider.cancel_order.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exchange_uid", "should_stand_down"),
    [("558689281", True), (None, False)],
    ids=["uid-siblings", "uid-missing"],
)
async def test_exchange_uid_scope_controls_shared_account_symbol_stand_down(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exchange_uid: str | None,
    should_stand_down: bool,
) -> None:
    """UID 형제 행의 세션만 같은 실제 계정으로 보고 stand-down 한다 (BL-517)."""
    session = _session()
    sibling_account_id = uuid4()
    sibling_session = SimpleNamespace(
        id=uuid4(),
        strategy_id=uuid4(),
        exchange_account_id=sibling_account_id,
        symbol=session.symbol,
    )
    harness = _patch_reconcile(
        monkeypatch,
        account_row=SimpleNamespace(id=session.exchange_account_id, exchange_uid=exchange_uid),
        sibling_accounts=[SimpleNamespace(id=sibling_account_id)],
        active_sessions_by_account={
            session.exchange_account_id: [],
            sibling_account_id: [sibling_session],
        },
    )
    caplog.set_level(logging.ERROR, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending()]), harness)

    stand_down_reasons = [
        getattr(record, "reason", None)
        for record in caplog.records
        if record.message == "live_conditional_stand_down"
    ]
    assert stand_down_reasons == (["shared_account_symbol"] if should_stand_down else [])
    if should_stand_down:
        harness.account_repo.list_by_exchange_uid.assert_awaited_once_with(exchange_uid)
        # ★집합으로 비교한다 — 실제 `list_by_exchange_uid` 는 `created_at ASC` 정렬이라
        #   **순서는 데이터에 달렸고** 구현 계약이 아니다. 순서를 고정하면 DB 정렬이 바뀔 때
        #   동작이 같은데도 red 가 난다. 재야 할 것은 「형제 행까지 물었나」다.
        assert {
            args.args[0] for args in harness.live_session_repo.list_active_by_account.await_args_list
        } == {session.exchange_account_id, sibling_account_id}
        harness.order_service.execute.assert_not_awaited()
    else:
        harness.account_repo.list_by_exchange_uid.assert_not_awaited()
        harness.live_session_repo.list_active_by_account.assert_awaited_once_with(
            session.exchange_account_id
        )
        harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_session_on_different_symbol_does_not_stand_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 같은 계정이라도 심볼이 다르면 포지션이 섞이지 않는다.

    이게 GREEN 을 유지해야 위 가드가 과잉차단이 아님이 증명된다.
    """
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        active_sessions=[
            SimpleNamespace(
                id=uuid4(),
                strategy_id=uuid4(),
                exchange_account_id=session.exchange_account_id,
                symbol="ETH/USDT",  # 다른 심볼
            )
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_same_session_in_active_list_does_not_stand_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 자기 자신은 계정 활성 목록에 당연히 들어 있다.

    `other.id != sess.id` 를 빠뜨리면 모든 세션이 영원히 stand-down 한다(기능 전면 정지).
    """
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        active_sessions=[
            SimpleNamespace(
                id=session.id,
                strategy_id=session.strategy_id,
                exchange_account_id=session.exchange_account_id,
                symbol=session.symbol,
            )
        ],
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_local_order_from_another_session_is_never_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★로컬 경로의 세션 검사. 같은 전략·계정에 세션이 2개면 이게 유일한 방벽이다.

    `list_resting_conditional_entries` 는 strategy_id + account_id 만 좁히므로,
    key 의 session_id 검사를 빼면 다른 세션의 진입 주문을 취소하게 된다.
    """
    session = _session()
    other_session = _session()
    stale = _order(other_session, trade_id="otherleg", exchange_order_id="other-session-entry")
    harness = _patch_reconcile(monkeypatch, local_orders=[stale])

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_exchange_order_from_another_account_is_never_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """거래소 경로의 exchange_account_id 검사."""
    session = _session()
    foreign = _order(session, trade_id="otherleg", exchange_order_id="foreign-account-entry")
    foreign.exchange_account_id = uuid4()
    harness = _patch_reconcile(
        monkeypatch, exchange_orders=[_exchange_order(foreign)], database_orders=[foreign]
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_reduce_only_order_is_never_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """★사용자의 손절을 지우는 것이 이 스프린트가 낼 수 있는 최악의 결함이다."""
    session = _session()
    stop_loss = _order(session, trade_id="otherleg", exchange_order_id="stop-loss-leg")
    stop_loss.reduce_only = True
    harness = _patch_reconcile(
        monkeypatch, exchange_orders=[_exchange_order(stop_loss)], database_orders=[stop_loss]
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.cancel_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_placed_order_carries_parseable_conditional_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★발주에 실린 key 를 검사한다. 마이그레이션-0 기전 전체가 여기 달려 있다."""
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness)

    key = harness.order_service.execute.await_args.kwargs["idempotency_key"]
    assert parse_conditional_entry_key(key) == (session.id, "entry")


@pytest.mark.asyncio
async def test_reconcile_defers_while_market_orders_are_in_flight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★같은 tick 의 시장가 dispatch 가 아직 거래소에 반영되기 전이면 미룬다.

    그 포지션으로 사이징하면 초과 수량 주문이 나간다(실측 예: 의도의 3배).
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness, market_orders_in_flight=True)

    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


# ── BL-499 취소↔dispatch 경합의 패자 경로 ─────────────────────────────────


def _capture_error_stages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`qb_live_conditional_reconcile_errors_total` 의 stage 라벨을 수집한다."""
    stages: list[str] = []
    metric = MagicMock()
    metric.labels = MagicMock(side_effect=lambda stage: (stages.append(stage), MagicMock())[1])
    monkeypatch.setattr(live_signal_module, "qb_live_conditional_reconcile_errors_total", metric)
    return stages


@pytest.mark.asyncio
async def test_market_inflight_with_pending_entries_counts_deferred_and_skips_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness, market_orders_in_flight=True)

    assert stages == ["deferred_market_inflight"]
    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_market_inflight_without_pending_entries_counts_noop_and_skips_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(session, _result([]), harness, market_orders_in_flight=True)

    assert stages == ["deferred_market_inflight_noop"]
    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_market_inflight_metric_label_failure_is_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    metric = MagicMock()
    metric.labels.side_effect = OSError("No space left on device")
    monkeypatch.setattr(live_signal_module, "qb_live_conditional_reconcile_errors_total", metric)

    await _reconcile(session, None, harness, market_orders_in_flight=True)

    metric.labels.assert_called_once_with(stage="deferred_market_inflight")
    harness.provider.fetch_open_conditional_orders.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_race_is_classified_and_skips_placement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★경합 패배는 진짜 실패와 구분되고, 그 tick 의 등재는 하지 않는다.

    실행 워커가 `pending → submitted` 를 먼저 커밋하면 DB-only 취소는 rowcount 0 이다.
    이것은 실패가 아니라 패배이므로 `cancel_raced` 로 분류한다. 그래도 `to_place` 는
    건너뛴다 — `current_position` 은 취소 루프보다 먼저 찍은 스냅샷이라, 패배한 주문이
    그 사이 체결되면 낡은 포지션 위에서 사이징한 주문이 나간다.
    """
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=OrderState.submitted,
    )
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    assert stages == ["cancel_raced"]
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_race_does_not_touch_active_orders_gauge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★패배는 terminal 전이가 아니다. dec 하면 게이지가 음수로 표류한다."""
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=OrderState.filled,
    )
    _capture_error_stages(monkeypatch)
    gauge = MagicMock()
    monkeypatch.setattr(live_signal_module, "qb_active_orders", gauge)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    gauge.dec.assert_not_called()
    harness.order_repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_row_is_still_a_genuine_cancel_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — 행 자체가 없으면 여전히 실패다. 완화가 진짜 실패를 삼키면 안 된다."""
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=None,
    )
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    assert stages == ["cancel"]
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_next_tick_cancels_the_raced_order_on_the_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★자가 치유 — 패배한 주문은 다음 tick 에 `exchange_order_id` 로 정상 취소된다."""
    session = _session()
    raced = _order(session, trade_id="old", exchange_order_id="exchange-old")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[raced],
        exchange_orders=[_exchange_order(raced)],
        database_orders=[raced],
    )

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    harness.provider.cancel_order.assert_awaited_once_with(ANY, "exchange-old", session.symbol)


# ── BL-500 거래소 부재가 로컬 행을 이긴다 ─────────────────────────────────


@pytest.mark.asyncio
async def test_missing_order_confirmed_cancelled_is_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★거래소가 "취소됨" 이라고 확인해 주면 `actual` 에서 빠지고 재등재된다.

    이걸 안 하면 그 trade_id 는 영구 no-op 이다 — 계획기가 로컬 행만 보고
    "이미 등재됨" 으로 판정하기 때문이다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="cancelled"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.fetch_order.assert_awaited_once()
    harness.order_service.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_order_still_open_on_exchange_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★목록에 없다고 사라진 것이 아니다.

    주문 조회 응답이 열화(레이트리밋·부분 응답)됐거나 방금 트리거돼 목록에서만
    먼저 빠졌을 수 있다. 거래소가 아직 살아 있다고 말하면 그대로 둔다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="submitted"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_probe_failure_removes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """★확인하지 못하면 그대로 둔다.

    이 함수의 다른 모든 열화 입력은 fail-closed 다. 여기만 "주문을 더 낸다" 방향으로
    fail-open 하면 REST 한 번의 열화가 중복 등재로 번역된다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[ghost],
        exchange_orders=[],
        probe_error=RuntimeError("rate limited"),
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_fill_stands_down_this_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★체결이 확인되면 이번 tick 은 등재하지 않는다.

    포지션 스냅샷은 이 확인보다 앞서 찍혔을 수 있다. 낡은 포지션으로 사이징하면
    이중 포지션이 된다 — 다음 tick 이 새 포지션으로 다시 계획한다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="filled"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_fill_writes_back_to_the_order_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★BL-560 진짜 뿌리 — 확인했으면 **기록까지** 해야 한다.

    예전엔 `probe.status == "filled"` 를 확인하고도 `orders` 행을 그대로 뒀다. 그래서
    체결 기록이 세션이 죽을 때까지(스윕) 미뤄졌고, 그 사이 `list_fills_since` 를 읽는
    `_ledger_gap_seed` 가 그 체결을 못 봐 **엔진 원장이 낡은 채로 돌았다**.

    실측(세션 `70063496`, 2026-07-31): 주문 `9c7aef0b` 는 07:31~32 체결인데 `filled_at`
    은 07:44:13 — 13분 공백. 그 동안 엔진 숏 / 거래소 롱(`engine_position=-0.0297634`
    vs `exchange_position=0.029`)이었고, 다음 청산 신호가 `buy` reduce-only 로 나가
    `110017 same side` 가 됐다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[ghost],
        exchange_orders=[],
        probe_status="filled",
        probe_filled_price=Decimal("64000"),
        probe_filled_quantity=Decimal("0.029"),
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_repo.transition_to_filled.assert_awaited_once_with(
        ghost.id,
        exchange_order_id="probe",
        filled_price=Decimal("64000"),
        filled_quantity=Decimal("0.029"),
        filled_at=ANY,
    )
    harness.order_repo.commit.assert_awaited()


@pytest.mark.asyncio
async def test_still_open_probe_writes_nothing_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """★음성 대조군 — 거래소가 아직 살아 있다고 하면 원장을 건드리지 않는다.

    이게 없으면 위 테스트는 "무조건 전이한다" 는 오답도 통과시킨다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="submitted"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_repo.transition_to_filled.assert_not_awaited()
    harness.order_repo.transition_to_rejected.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmed_reject_also_writes_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """확인된 거절도 같은 공백을 만든다 — 같이 기록한다.

    `filled` 만 기록하면 거절된 행이 `submitted` 로 남아 `list_resting_conditional_entries`
    에 계속 잡히고, 계획기가 "이미 등재됨" 으로 보아 그 trade_id 가 영구 no-op 이 된다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="rejected"
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_repo.transition_to_rejected.assert_awaited_once()


@pytest.mark.asyncio
async def test_write_back_race_loser_does_not_double_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★중복 처리 금지 — rowcount 0 이면 commit 도 gauge 도 건드리지 않는다.

    watchdog · WS · 스윕 · 이 경로가 동시에 같은 주문을 본다. 승자만 후속을 돌려야
    gauge 가 음수로 표류하지 않고 trailing/closed-pnl 훅이 두 번 걸리지 않는다.
    """
    from src.common.metrics import qb_active_orders

    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[ghost],
        exchange_orders=[],
        probe_status="filled",
        terminal_write_back_rows=0,
    )
    commits_before = harness.order_repo.commit.await_count
    gauge_before = qb_active_orders._value.get()

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_repo.transition_to_filled.assert_awaited_once()
    assert harness.order_repo.commit.await_count == commits_before
    assert qb_active_orders._value.get() == gauge_before


@pytest.mark.asyncio
async def test_confirmed_fill_does_not_increment_exchange_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """체결 확인은 거래소 부재 오류가 아니므로 error metric을 올리지 않는다."""
    from src.common.metrics import qb_live_conditional_reconcile_errors_total

    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="filled"
    )
    counter = qb_live_conditional_reconcile_errors_total.labels(stage="exchange_missing")
    before = counter._value.get()

    await _reconcile(session, _result([_pending()]), harness)

    assert counter._value.get() == before


@pytest.mark.asyncio
async def test_cancelled_probe_still_increments_exchange_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조: 취소 확인은 기존처럼 거래소 부재 오류로 계측한다."""
    from src.common.metrics import qb_live_conditional_reconcile_errors_total

    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="cancelled"
    )
    counter = qb_live_conditional_reconcile_errors_total.labels(stage="exchange_missing")
    before = counter._value.get()

    await _reconcile(session, _result([_pending()]), harness)

    assert counter._value.get() == before + 1


@pytest.mark.asyncio
async def test_in_flight_order_without_exchange_id_is_never_probed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — `exchange_order_id` 가 없는 행은 물어볼 대상 자체가 없다.

    그건 아직 dispatch 가 거래소 id 를 붙이지 못한 in-flight 행이고, 지우면 진짜
    이중 등재 방어가 무너진다.
    """
    session = _session()
    in_flight = _order(session, exchange_order_id=None)
    harness = _patch_reconcile(monkeypatch, local_orders=[in_flight], exchange_orders=[])

    await _reconcile(session, _result([_pending()]), harness)

    harness.provider.fetch_order.assert_not_awaited()
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_exchange_lookup_failure_removes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★조회 실패 tick 에는 현상 유지다. 실패를 "거래소에 없다" 로 읽으면 안 된다."""
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[ghost],
        exchange_orders_error=RuntimeError("exchange unavailable"),
    )

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_submitted_without_exchange_id_is_deferred_to_janitor(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """★`submitted` 인데 거래소 id 가 없으면 경합이 아니라 제출 중단이다.

    dispatch 가 상태만 커밋하고 거래소 왕복에서 죽으면 그 행은 영구 고착하는데
    `orphan_scanner` 는 조건부 진입을 면제한다. 경합 카운터로 강등하면 영구 장애가
    1회성 경합에 섞여 사라진다.
    """
    session = _session()
    stale = _order(session, trade_id="old", exchange_order_id=None)
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[stale],
        pending_cancel_rows=0,
        fresh_state=OrderState.submitted,
        fresh_exchange_order_id=None,
    )
    stages = _capture_error_stages(monkeypatch)
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending(trade_id="new")]), harness)

    assert stages == ["cancel_deferred"]
    assert "live_conditional_reconcile_cancel_deferred_to_janitor" in caplog.messages


# ── BL-523 브래킷 배선 + 게이트 ────────────────────────────────────────────


def _capture_guard_outcomes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`qb_live_conditional_guard_total` 의 outcome 라벨을 수집한다."""
    outcomes: list[str] = []
    metric = MagicMock()
    metric.labels = MagicMock(
        side_effect=lambda outcome: (outcomes.append(outcome), MagicMock())[1]
    )
    monkeypatch.setattr(live_signal_module, "qb_live_conditional_guard_total", metric)
    return outcomes


@pytest.mark.asyncio
async def test_conditional_entry_without_exit_levels_places_a_bare_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★회귀 0 + 이 스프린트의 계측 대상.

    조건부 진입은 체결 전까지 `open_trades` 에 없어 `exit_levels_for` 가 항상
    `(None, None, None)` 을 준다(`test_run_live_pending_orders.py` 의 회귀 테스트).
    그래서 실운영에서 오르는 라벨은 `bracket_unavailable` 이어야 한다 — 그 "없음" 을
    추측이 아니라 관측으로 만드는 것이 배관의 목적이다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    outcomes = _capture_guard_outcomes(monkeypatch)

    await _reconcile(session, _result([_pending()]), harness)

    request = harness.order_service.execute.await_args.args[0]
    assert (request.take_profit, request.stop_loss, request.trailing_stop) == (None, None, None)
    assert "bracket_unavailable" in outcomes
    assert "bracket_attached" not in outcomes


@pytest.mark.asyncio
async def test_conditional_entry_carries_bracket_when_engine_supplies_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """음성 대조 — 엔진이 레벨을 주면 그대로 주문에 실린다(배관이 죽어 있지 않다)."""
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    outcomes = _capture_guard_outcomes(monkeypatch)

    await _reconcile(
        session,
        _result([_pending(take_profit=Decimal("192"), stop_loss=Decimal("64"))]),
        harness,
    )

    request = harness.order_service.execute.await_args.args[0]
    assert request.take_profit == Decimal("192")
    assert request.stop_loss == Decimal("64")
    assert "bracket_attached" in outcomes


@pytest.mark.asyncio
async def test_trailing_only_leg_is_not_placed_at_all(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """게이트 A — 고정 SL 없는 트레일링 단독은 등재하지 않는다.

    트레일링은 체결 **후** `set_trading_stop` 으로만 붙으므로(ccxt 는 trailing + trigger
    조합을 `InvalidOrder` 로 거부한다) SL 이 없으면 체결 순간부터 부착까지 무방비다.
    ★시장가 진입 경로와 달리 `mark_failed` 를 쓸 수 없다 — 조건부 진입에는
    `live_signal_events` 행이 없다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    outcomes = _capture_guard_outcomes(monkeypatch)
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending(trailing_stop=Decimal("4"))]), harness)

    harness.order_service.execute.assert_not_awaited()
    assert outcomes == ["bracket_trailing_only_dropped"]
    assert any(
        record.message == "live_conditional_guard_drop"
        and getattr(record, "reason", None) == "bracket_trailing_only"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_trailing_with_stop_loss_is_carried_on_a_non_reduce_only_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SL 이 있으면 진입은 나가고 trailing 은 `Order` 에 영속된다.

    ★`reduce_only is False` 를 함께 잠근다 — 거래소로 trailing 이 나가지 않는 것은
    `tasks/trading.py:421` 와 `providers.py:456` 이 둘 다 `reduce_only` 를 요구하기
    때문이다. 이 플래그가 뒤집히면 그 2중 방어가 통째로 무력해진다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch)

    await _reconcile(
        session,
        _result([_pending(stop_loss=Decimal("64"), trailing_stop=Decimal("4"))]),
        harness,
    )

    request = harness.order_service.execute.await_args.args[0]
    assert request.stop_loss == Decimal("64")
    assert request.trailing_stop == Decimal("4")
    assert request.reduce_only is False


@pytest.mark.asyncio
async def test_reversal_drops_take_profit_but_keeps_stop_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """게이트 B — tpSize 정합.

    `_merge_exit_params`(`providers.py:462-465`)가 `takeProfit.price` 를 넣으면 ccxt 가
    `tpslMode=Partial` 로 라우팅해 `tpSize = 주문수량` 이 된다. 반전은 주문수량(16) >
    체결 후 포지션(8) 이라 거래소가 **진입 자체를** 거부한다. 손계산 오라클은 2의
    거듭제곱 — 보유 +8, 목표 -8, 주문 16, 결과 포지션 8.
    보호를 통째로 잃지 않도록 SL 은 유지한다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    outcomes = _capture_guard_outcomes(monkeypatch)

    await _reconcile(
        session,
        _result(
            [
                _pending(
                    direction="short",
                    target_position=Decimal("-8"),
                    stop_price=Decimal("32"),
                    take_profit=Decimal("16"),
                    stop_loss=Decimal("64"),
                )
            ]
        ),
        harness,
    )

    request = harness.order_service.execute.await_args.args[0]
    assert request.quantity == Decimal("16")
    assert request.take_profit is None
    assert request.stop_loss == Decimal("64")
    assert "bracket_tp_dropped_size" in outcomes
    # BL-563 — SL 이 남아 실제로 나갔으므로 여기는 여전히 `bracket_attached` 다.
    assert "bracket_attached" in outcomes
    assert "bracket_supplied_gate_dropped" not in outcomes


@pytest.mark.asyncio
async def test_tp_only_reversal_is_not_counted_as_engine_supplied_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★BL-563 — 게이트가 전부 걷어낸 것과 엔진이 공급 안 한 것을 섞지 않는다.

    엔진이 TP 만 준 반전은 게이트 B 가 그 TP 를 드롭하므로 발주된 `OrderRequest` 는
    셋 다 None 이다. 판정을 그 `request` 로 하면 `bracket_unavailable` 이 올라
    **"엔진이 아무것도 공급하지 않았다"** 와 같은 라벨이 된다 — BL-523 의 판정 근거가
    바로 그 counter 라 그 순간 숫자를 못 믿는다.

    오라클은 게이트 B 테스트와 같은 2의 거듭제곱 — 보유 +8, 목표 -8, 주문 16,
    체결 후 포지션 8 (16 != 8 이라 게이트 B 가 발화).
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    outcomes = _capture_guard_outcomes(monkeypatch)

    await _reconcile(
        session,
        _result(
            [
                _pending(
                    direction="short",
                    target_position=Decimal("-8"),
                    stop_price=Decimal("32"),
                    take_profit=Decimal("16"),
                )
            ]
        ),
        harness,
    )

    request = harness.order_service.execute.await_args.args[0]
    assert (request.take_profit, request.stop_loss, request.trailing_stop) == (None, None, None)
    assert "bracket_tp_dropped_size" in outcomes
    # ★핵심 단언 — 게이트 드롭은 자기 축으로 가고 "공급 없음" 축을 오염시키지 않는다.
    assert "bracket_supplied_gate_dropped" in outcomes
    assert "bracket_unavailable" not in outcomes
    assert "bracket_attached" not in outcomes


@pytest.mark.asyncio
async def test_bracket_outcome_labels_are_mutually_exclusive_per_placement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-563 — 세 라벨의 합 = 등재 성공 수. 한 등재가 둘을 올리면 비율이 무의미해진다."""
    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    outcomes = _capture_guard_outcomes(monkeypatch)

    await _reconcile(
        session,
        _result(
            [
                _pending(
                    direction="short",
                    target_position=Decimal("-8"),
                    stop_price=Decimal("32"),
                    take_profit=Decimal("16"),
                )
            ]
        ),
        harness,
    )

    bracket_axis = [
        outcome
        for outcome in outcomes
        if outcome in ("bracket_attached", "bracket_unavailable", "bracket_supplied_gate_dropped")
    ]
    assert bracket_axis == ["bracket_supplied_gate_dropped"]
    assert outcomes.count("conditional_placed") == len(bracket_axis)


@pytest.mark.asyncio
async def test_reversal_placement_is_counted_with_its_overshoot_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-516 안 3 — 수량은 합친 채로 두되 크기는 잰다. 16 / 8 = 2 -> `2x`."""
    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    buckets: list[str] = []
    metric = MagicMock()
    metric.labels = MagicMock(side_effect=lambda bucket: (buckets.append(bucket), MagicMock())[1])
    monkeypatch.setattr(live_signal_module, "qb_live_conditional_reversal_total", metric)

    await _reconcile(
        session,
        _result(
            [_pending(direction="short", target_position=Decimal("-8"), stop_price=Decimal("32"))]
        ),
        harness,
    )

    assert harness.order_service.execute.await_args.args[0].quantity == Decimal("16")
    assert buckets == ["2x"]


@pytest.mark.asyncio
async def test_flat_entry_is_not_counted_as_a_reversal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """대조군 — 순수 진입은 부호 교차가 아니므로 반전 counter 가 오르지 않는다."""
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    buckets: list[str] = []
    metric = MagicMock()
    metric.labels = MagicMock(side_effect=lambda bucket: (buckets.append(bucket), MagicMock())[1])
    monkeypatch.setattr(live_signal_module, "qb_live_conditional_reversal_total", metric)

    await _reconcile(session, _result([_pending()]), harness)

    harness.order_service.execute.assert_awaited_once()
    assert buckets == []


@pytest.mark.asyncio
async def test_invalid_order_request_gets_its_own_stage_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★스키마 위반을 네트워크 실패와 **같은 라벨**로 삼키지 않는다.

    exit 레벨은 Pine float 에서 오므로 `decimal_places=8` 초과가 실제로 가능한 입력이다.
    그것을 `conditional_place`(거래소/네트워크 실패)로 세면 전략 결함을 인프라 결함으로
    오진한다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    stages = _capture_error_stages(monkeypatch)

    await _reconcile(
        session,
        _result([_pending(take_profit=Decimal("100.123456789"))]),
        harness,
    )

    harness.order_service.execute.assert_not_awaited()
    assert stages == ["conditional_request_invalid"]


@pytest.mark.asyncio
async def test_market_converted_entry_still_carries_its_bracket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """돌파로 시장가 전환된 진입도 같은 브래킷을 싣는다(전환은 트리거만 없앤다)."""
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))

    await _reconcile(
        session,
        _result([_pending(stop_loss=Decimal("64"), take_profit=Decimal("192"))]),
        harness,
    )

    request = harness.order_service.execute.await_args.args[0]
    assert request.trigger_price is None
    assert request.trigger_direction is None
    assert request.stop_loss == Decimal("64")
    assert request.take_profit == Decimal("192")


@pytest.mark.asyncio
async def test_placed_metric_failure_does_not_skip_the_market_convert_deferral(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """시장가 전환 뒤 계측 실패가 남은 낡은 스냅샷 등재를 재개하면 안 된다."""
    import src.common.metrics as metrics_mod

    def _explode(**_kwargs: object) -> object:
        raise OSError("mmap allocation failed")

    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    monkeypatch.setattr(metrics_mod.qb_live_conditional_placed_total, "labels", _explode)

    await _reconcile(session, _result([_pending("a"), _pending("b")]), harness)

    assert harness.order_service.execute.await_count == 1
    assert harness.order_service.execute.await_args.args[0].trigger_price is None


@pytest.mark.asyncio
async def test_placed_metric_failure_is_not_counted_as_a_place_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.common.metrics as metrics_mod

    def _explode(**_kwargs: object) -> object:
        raise OSError("mmap allocation failed")

    session = _session()
    harness = _patch_reconcile(monkeypatch)
    failures = metrics_mod.qb_live_conditional_reconcile_errors_total.labels(
        stage="conditional_place"
    )
    before = failures._value.get()
    monkeypatch.setattr(metrics_mod.qb_live_conditional_placed_total, "labels", _explode)

    await _reconcile(session, _result([_pending()]), harness)

    after = failures._value.get()
    harness.order_service.execute.assert_awaited_once()
    assert after - before == 0


@pytest.mark.asyncio
async def test_guard_outcome_metric_failure_does_not_counted_as_place_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.common.metrics as metrics_mod

    def _explode(**_kwargs: object) -> object:
        raise OSError("mmap allocation failed")

    session = _session()
    harness = _patch_reconcile(monkeypatch)
    failures = metrics_mod.qb_live_conditional_reconcile_errors_total.labels(
        stage="conditional_place"
    )
    before = failures._value.get()
    monkeypatch.setattr(metrics_mod.qb_live_conditional_guard_total, "labels", _explode)

    await _reconcile(session, _result([_pending()]), harness)

    after = failures._value.get()
    harness.order_service.execute.assert_awaited_once()
    assert after - before == 0


@pytest.mark.asyncio
async def test_pre_execute_metric_failure_no_longer_masquerades_as_a_place_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """주문 전 계측 실패는 발주를 건너뛰되 **발주 실패로 오기록되지 않는다** (BL-580).

    ★**이 테스트가 내 판정을 정정했다.** 2026-08-04 연장에서 나는 `_reconcile_conditional_entries`
    의 12곳을 「전부 바깥 fail-open `except` 안이라 리컨사일 전체가 조용히 중단된다」로
    적었는데, **이 자리는 아니었다** — `unrepresentable_key` 계상은 발주 `try` 안이라
    예외가 **안쪽** `except Exception`(`stage="conditional_place"`)에 잡혔다.

    즉 수리 전 해악은 「중단」이 아니라 **오기록**이었다: 발주를 시도한 적도 없는데
    `conditional_place`(= 발주 실패)가 올라, 「되짚지 못할 key 라서 건너뛰었다」는 진짜
    사유가 사라진다. `_count_safely` 로 감싼 뒤에는 `continue` 가 제대로 실행돼 그 거짓
    계상이 사라진다.

    ⇒ **「전부 같은 형태」 가정은 12곳 중 최소 1곳에서 틀린다.** 이 레포가 반복해 덴
    함정이고(직전 회차: 8곳 중 1곳만 fail-open `try` 안), 이번에도 같았다.
    """
    import src.common.metrics as metrics_mod

    labels = metrics_mod.qb_live_conditional_reconcile_errors_total.labels

    def _explode(**kwargs: object) -> object:
        if kwargs["stage"] == "unrepresentable_key":
            raise OSError("mmap allocation failed")
        return labels(**kwargs)

    session = _session()
    harness = _patch_reconcile(monkeypatch)
    failures = metrics_mod.qb_live_conditional_reconcile_errors_total.labels(
        stage="conditional_place"
    )
    before = failures._value.get()
    monkeypatch.setattr(metrics_mod.qb_live_conditional_reconcile_errors_total, "labels", _explode)

    await _reconcile(session, _result([_pending("x" * 200)]), harness)

    after = failures._value.get()
    # 변하지 않은 것 — 되짚지 못할 key 로는 여전히 발주하지 않는다.
    harness.order_service.execute.assert_not_awaited()
    # 변한 것 — 계측 실패가 더는 「발주 실패」로 둔갑하지 않는다.
    assert after - before == 0
