"""[BL-634] 계정 배타성 가드 — `register()` 전제조건으로 **실제로 막는지** 검증한다.

종전에 `EXCLUSIVE` 는 `live_session_admin.py _cmd_status` 에서 **판정만 하고 print** 했고,
유일한 강제는 `scripts/soak-restart.sh` 셸 한 곳이라 소크 재시작 경로에만 걸렸다.
[BL-633] 의 사망은 **재기동이 아니라 세션 시작** 시점에 이미 오염된 계정 위에서 났다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.exceptions import AccountNotExclusive, ProviderError
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
)
from src.trading.schemas import AccountBalanceResponse, RegisterLiveSessionRequest
from src.trading.services.account_exclusivity import AccountExclusivityService
from src.trading.services.live_session_service import LiveSignalSessionService

_VALID_SETTINGS = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "cross",
    "position_size_pct": 10.0,
}


def _make_strategy(user_id: UUID) -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="t",
        pine_source="//@version=5\nstrategy('t')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=_VALID_SETTINGS,
    )


def _make_account(user_id: UUID, *, exchange_uid: str | None = "558689281") -> ExchangeAccount:
    return ExchangeAccount(
        id=uuid4(),
        user_id=user_id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"y",
        exchange_uid=exchange_uid,
    )


def _resting(order_link_id: str | None) -> SimpleNamespace:
    return SimpleNamespace(order_id="ex-1", order_link_id=order_link_id)


def _balance_service() -> AsyncMock:
    service = AsyncMock()
    service.get_balance = AsyncMock(
        return_value=AccountBalanceResponse(
            account_id=uuid4(),
            asset="USDT",
            supported=True,
            reason=None,
            total=Decimal("10000"),
            free=Decimal("10000"),
            fetched_at=datetime.now(UTC),
        )
    )
    return service


def _build(
    *,
    account: ExchangeAccount,
    strategy: Strategy,
    resting: list[SimpleNamespace],
    ledger: dict[UUID, set[UUID]],
    siblings: list[ExchangeAccount] | None = None,
    provider_error: bool = False,
) -> tuple[LiveSignalSessionService, AsyncMock, list[tuple[str, bool | None]]]:
    """진짜 `AccountExclusivityService` 를 단 `register()` 를 조립한다.

    `ledger` = `exchange_account_id -> {Order.id}`. 실제
    `OrderRepository.list_existing_ids` 가 계정 스코프로 실재만 돌려주는 계약 그대로다.
    """
    saved = LiveSignalSession(
        id=uuid4(),
        user_id=account.user_id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m5,
    )
    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=0)
    repo.save = AsyncMock(return_value=saved)

    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    account_repo.list_by_exchange_uid = AsyncMock(return_value=siblings or [account])

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    order_repo = AsyncMock()

    async def _list_existing_ids(account_id: UUID, order_ids: set[UUID]) -> frozenset[UUID]:
        return frozenset(ledger.get(account_id, set()) & set(order_ids))

    order_repo.list_existing_ids = AsyncMock(side_effect=_list_existing_ids)

    account_service = AsyncMock()
    account_service.get_credentials_for_order = AsyncMock(return_value=SimpleNamespace())

    calls: list[tuple[str, bool | None]] = []

    async def _fetch(creds: object, symbol: str, *, reduce_only: bool | None = True):
        calls.append((symbol, reduce_only))
        if provider_error:
            raise ProviderError("bybit unreachable")
        return resting

    provider = AsyncMock()
    provider.fetch_open_conditional_orders = AsyncMock(side_effect=_fetch)

    service = LiveSignalSessionService(
        repo=repo,
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        balance_service=_balance_service(),
        exclusivity_service=AccountExclusivityService(
            account_repo=account_repo,
            order_repo=order_repo,
            account_service=account_service,
            bybit_futures_provider=provider,
        ),
    )
    return service, repo, calls


def _req(strategy_id: UUID, account_id: UUID) -> RegisterLiveSessionRequest:
    return RegisterLiveSessionRequest(
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        interval="5m",
    )


@pytest.mark.asyncio
async def test_register_is_refused_when_a_foreign_resting_order_sits_on_the_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """유도 시험 **양성** — 위반 상태를 만들면 세션이 안 열린다.

    다른 호스트가 낸 조건부 주문은 그 호스트의 DB 에서 나온 `Order.id` 를
    `orderLinkId` 로 달고 있으므로, **이 원장에는 그 id 가 없다**.
    """
    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    service, repo, _ = _build(
        account=account,
        strategy=strategy,
        resting=[_resting(str(uuid4()))],  # 남의 호스트가 발행한 id
        ledger={account.id: set()},
    )

    with pytest.raises(AccountNotExclusive) as exc:
        await service.register(user_id, _req(strategy.id, account.id))

    assert exc.value.status_code == 409
    assert len(exc.value.foreign) == 1
    # ★전제조건이라는 것의 의미 — quota lock 도 INSERT 도 **닿지 않는다**.
    repo.acquire_quota_lock.assert_not_called()
    repo.save.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_succeeds_when_every_resting_order_is_ours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """유도 시험 **음성** — 정상 상태(우리 주문만 걸려 있음)는 통과한다.

    이 대조가 없으면 가드는 「항상 거부」로도 양성 시험을 통과한다. 소크 재기동은
    자기 자신의 resting 을 남긴 채 돌아오는 것이 정상이므로, 여기서 막히면
    가드가 운영을 영구히 세운다.
    """
    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    our_order = uuid4()
    service, repo, calls = _build(
        account=account,
        strategy=strategy,
        resting=[_resting(str(our_order))],
        ledger={account.id: {our_order}},
    )
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", lambda: None)

    result = await service.register(user_id, _req(strategy.id, account.id))

    assert result is repo.save.return_value
    repo.commit.assert_awaited_once()
    # `reduce_only=None` 은 협상 불가 — 기본값 `True` 는 TP/SL 만 주고,
    # 오염을 만드는 조건부 **진입**을 통째로 놓친다.
    assert calls == [("BTC/USDT", None)]


@pytest.mark.asyncio
async def test_an_order_placed_under_a_sibling_account_row_is_still_ours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """소유권 집합의 **계정 축** — uid 형제 행까지 합집합한다.

    [BL-605] 가 증명했듯 같은 실제 계정이 행 2개로 존재한다. 행 A 로 낸 주문을 행 B 로
    등재하며 조회하면, 축을 자기 행 하나로 좁힌 구현은 **우리 것을 FOREIGN 으로**
    판정해 정상 재기동을 영구히 막는다. 이 테스트가 그 거짓 양성을 잡는다.
    """
    user_id = uuid4()
    strategy = _make_strategy(user_id)
    registering = _make_account(user_id)
    sibling = _make_account(user_id)
    our_order = uuid4()
    service, repo, _ = _build(
        account=registering,
        strategy=strategy,
        resting=[_resting(str(our_order))],
        # 주문은 **형제 행**의 이름으로 원장에 있다.
        ledger={sibling.id: {our_order}},
        siblings=[sibling, registering],
    )
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", lambda: None)

    await service.register(user_id, _req(strategy.id, registering.id))

    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_resting_order_without_a_link_id_is_treated_as_foreign() -> None:
    """`orderLinkId` 가 없으면 우리 것이라고 주장할 근거가 없다 ⇒ FOREIGN.

    내부 `Order.id` 가 그대로 `orderLinkId` 로 나간다는 규약이 이 대조의 유일한
    근거이므로, link 가 비어 있으면 판정 수단 자체가 없다.
    """
    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    service, repo, _ = _build(
        account=account,
        strategy=strategy,
        resting=[_resting(None)],
        ledger={account.id: set()},
    )

    with pytest.raises(AccountNotExclusive):
        await service.register(user_id, _req(strategy.id, account.id))
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_the_guard_fails_closed_when_the_exchange_cannot_be_reached() -> None:
    """거래소를 못 읽으면 **세션을 열지 않는다**.

    「확인 못 했으니 통과」는 이 가드의 존재 이유를 지운다 — 이 프로젝트가 fail-open
    으로 반복해 데인 자리다. `ProviderError`(502) 가 그대로 올라가 등재가 멈춘다.
    """
    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    service, repo, _ = _build(
        account=account,
        strategy=strategy,
        resting=[],
        ledger={},
        provider_error=True,
    )

    with pytest.raises(ProviderError):
        await service.register(user_id, _req(strategy.id, account.id))
    repo.acquire_quota_lock.assert_not_called()
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_an_account_with_no_resting_orders_never_touches_the_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resting 이 0 이면 소유권 조회 자체가 필요 없다 — 판정할 대상이 없다."""
    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    service, repo, calls = _build(
        account=account, strategy=strategy, resting=[], ledger={account.id: {uuid4()}}
    )
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", lambda: None)

    await service.register(user_id, _req(strategy.id, account.id))

    repo.commit.assert_awaited_once()
    assert calls == [("BTC/USDT", None)]
