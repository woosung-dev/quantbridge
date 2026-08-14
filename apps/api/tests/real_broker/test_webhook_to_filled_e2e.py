"""TV 주문 leg가 Bybit Demo linear 선물에서 체결까지 이어지는지 검증한다.

실거래소 청산 하네스는 별도 worker 엔진으로 DB를 다시 열므로, seed는 savepoint 기반
`db_session`이 아니라 `_test_engine`에서 만든 세션으로 실제 commit한다. 또한 spot은
포지션 조회로 flat을 판정할 수 없어 거짓 안전망이 되므로 `BTC/USDT:USDT` linear perp만
사용한다. 청산 finalizer가 계정과 라이브 세션을 다시 읽어야 하므로 테스트 본문에서
seed를 정리하지 않는다.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.auth.models import User
from src.core import config
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.tasks.trading import _async_fetch_order_status
from src.trading.dependencies import get_order_dispatcher
from src.trading.encryption import EncryptionService
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import OrderRequest
from src.trading.services.order_service import OrderService
from tests.real_broker import _harness

pytestmark = pytest.mark.real_broker

_BTCUSDT_TEST_SYMBOL = "BTC/USDT:USDT"
_TEST_QTY = Decimal("0.001")


class _NoopKillSwitch:
    """실주문 leg에서는 gating이 아닌 broker 배선과 체결만 측정한다."""

    async def ensure_not_gated(self, *, strategy_id: UUID, account_id: UUID) -> None:
        return None


@pytest.mark.asyncio
async def test_tv_webhook_to_bybit_demo_filled(
    _test_engine,
    bybit_demo_test_credentials: tuple[str, str],
    broker_flat_guard,
    _no_op_enqueue: dict[str, list[object]],
) -> None:
    """주문 원장 생성·실발주·watchdog 체결 확정과 청산 등록 순서를 함께 검증한다."""
    api_key, api_secret = bybit_demo_test_credentials
    crypto = EncryptionService(settings.trading_encryption_keys)
    session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)

    async with session_factory() as session:
        user = User(
            clerk_user_id=f"real_broker_{uuid4().hex}",
            email=f"{uuid4().hex}@test.local",
        )
        strategy = Strategy(
            user_id=user.id,
            name="real_broker e2e strategy",
            pine_source="//@version=5\nstrategy('real-broker-e2e')",
            pine_version=PineVersion.v5,
            parse_status=ParseStatus.ok,
        )
        account = ExchangeAccount(
            user_id=user.id,
            exchange=ExchangeName.bybit,
            mode=ExchangeMode.demo,
            api_key_encrypted=crypto.encrypt(api_key),
            api_secret_encrypted=crypto.encrypt(api_secret),
            label="real_broker e2e",
        )
        session.add_all([user, strategy, account])
        await session.commit()

        live_session = LiveSignalSession(
            user_id=user.id,
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol=_BTCUSDT_TEST_SYMBOL,
            interval=LiveSignalInterval.m1,
            is_active=True,
        )
        session.add(live_session)
        await session.commit()

        broker_flat_guard(
            account_id=account.id,
            symbol=_BTCUSDT_TEST_SYMBOL,
            live_session_id=live_session.id,
            account_label="real_broker e2e",
        )

        order_repo = OrderRepository(session)
        service = OrderService(
            session=session,
            repo=order_repo,
            dispatcher=get_order_dispatcher(),
            kill_switch=_NoopKillSwitch(),  # type: ignore[arg-type]
        )
        request = OrderRequest(
            strategy_id=strategy.id,
            exchange_account_id=account.id,
            symbol=_BTCUSDT_TEST_SYMBOL,
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=_TEST_QTY,
            price=None,
            leverage=5,
            margin_mode="cross",
        )
        response, is_replayed = await service.execute(request, idempotency_key=None)

        assert is_replayed is False
        delayed = _no_op_enqueue["trading.execute_order.delay"]
        assert len(delayed) == 1
        assert delayed[0][0] == (str(response.id),)

        await _harness._execute_order_now(response.id)

        session.expire_all()
        submitted_order = await order_repo.get_by_id(response.id)
        assert submitted_order is not None
        assert submitted_order.exchange_order_id is not None

        previous_database_url = config.settings.database_url
        order_after_watchdog = None
        config.settings.database_url = _harness._effective_db_url()
        try:
            for retry in range(4):
                await _async_fetch_order_status(response.id, attempt=1)
                session.expire_all()
                order_after_watchdog = await order_repo.get_by_id(response.id)
                if (
                    order_after_watchdog is not None
                    and order_after_watchdog.state == OrderState.filled
                ):
                    break
                if retry < 3:
                    await asyncio.sleep(2)
        finally:
            config.settings.database_url = previous_database_url

        assert order_after_watchdog is not None
        assert order_after_watchdog.state == OrderState.filled, (
            "Bybit Demo 시장가 주문이 초기 호출 뒤 3회의 watchdog 재확인에도 filled가 아니다."
        )
        assert order_after_watchdog.filled_price is not None
