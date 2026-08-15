"""OrderService — cross-tenant ownership gate (TRD-4 IDOR fix).

webhook 경로는 strategy HMAC 으로만 인증되고 exchange_account_id 를 payload body 에서
그대로 받는다. strategy 소유자와 account 소유자가 다르면 주문을 거부해야 한다.

거부 경로는 어떤 DB/세션 side-effect 보다 먼저 일어나야 하므로 순수 단위 테스트로
검증한다 (db_session 불필요). 정상 경로(positive guard)는 통합 테스트로 CI 에서 검증.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.trading.exceptions import AccountOwnershipMismatch
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderType,
)
from src.trading.schemas import OrderRequest
from src.trading.services.order_service import OrderService


class _NoopKillSwitch:
    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        return None


class _Dispatcher:
    dispatched = 0

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        _Dispatcher.dispatched += 1


class _OwnerPort:
    """StrategySessionsPort fake — get_owner 로 strategy 소유자 반환.

    ★`owner_active` 는 2026-08-15 surface-truth (S3) 가 추가한 축이다. 기본은 True —
    기존 케이스는 전부 「살아 있는 사용자」를 모형한다.
    """

    def __init__(self, owner_id: UUID | None, *, owner_active: bool = True) -> None:
        self._owner = owner_id
        self._owner_active = owner_active

    async def get_sessions(self, strategy_id: UUID) -> list[str]:
        return []

    async def get_owner(self, strategy_id: UUID) -> UUID | None:
        return self._owner

    async def is_owner_active(self, user_id: UUID) -> bool:
        return self._owner_active


class _AcctRepo:
    def __init__(self, account: ExchangeAccount | None) -> None:
        self._a = account

    async def get_by_id(self, account_id: UUID) -> ExchangeAccount | None:
        return self._a


class _ExchangeSvc:
    def __init__(self, account: ExchangeAccount | None) -> None:
        self._repo = _AcctRepo(account)

    async def fetch_balance_usdt(self, account_id: UUID) -> Decimal | None:
        return None


class _ExplodingRepo:
    """begin_nested 이전에 gate 가 raise 하면 session/repo 는 절대 안 쓰여야 한다."""

    def __getattr__(self, name: str):  # pragma: no cover - 호출되면 테스트 실패
        raise AssertionError(f"repo/session touched before ownership gate: {name!r}")


def _account(owner_id: UUID) -> ExchangeAccount:
    """in-memory ExchangeAccount (DB 불필요) — gate 는 user_id 만 본다."""
    return ExchangeAccount(
        id=uuid4(),
        user_id=owner_id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted="x",
        api_secret_encrypted="y",
    )


def _request(strategy_id: UUID, account_id: UUID) -> OrderRequest:
    return OrderRequest(
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )


async def test_rejects_order_when_account_owner_differs_from_strategy_owner():
    """TRD-4: strategy(소유 A) + exchange_account(소유 B) → AccountOwnershipMismatch.

    gate 가 어떤 session/repo 접근보다 먼저 raise (ExplodingRepo 가 보증).
    """
    strategy_owner = uuid4()
    victim_owner = uuid4()
    victim_acct = _account(victim_owner)

    _Dispatcher.dispatched = 0
    svc = OrderService(
        session=object(),  # 사용되면 안 됨
        repo=_ExplodingRepo(),
        dispatcher=_Dispatcher(),
        kill_switch=_NoopKillSwitch(),
        sessions_port=_OwnerPort(owner_id=strategy_owner),
        exchange_service=_ExchangeSvc(victim_acct),
    )

    with pytest.raises(AccountOwnershipMismatch):
        await svc.execute(_request(uuid4(), victim_acct.id), idempotency_key=None)

    assert _Dispatcher.dispatched == 0


async def test_rejects_when_account_not_found():
    """account 조회 실패 시에도 fail-closed (None != strategy_owner)."""
    svc = OrderService(
        session=object(),
        repo=_ExplodingRepo(),
        dispatcher=_Dispatcher(),
        kill_switch=_NoopKillSwitch(),
        sessions_port=_OwnerPort(owner_id=uuid4()),
        exchange_service=_ExchangeSvc(None),
    )
    with pytest.raises(AccountOwnershipMismatch):
        await svc.execute(_request(uuid4(), uuid4()), idempotency_key=None)
