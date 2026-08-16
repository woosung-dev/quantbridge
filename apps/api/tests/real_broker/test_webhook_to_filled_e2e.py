"""주문 leg가 Bybit Demo linear 선물에서 **실제 체결**까지 이어지는지 검증한다.

## ★이 파일이 재지 **않는** 것 — 이름에 속지 마라

파일명은 `webhook_to_filled` 이지만 이 스위트는 **HTTP webhook 층을 타지 않는다.**
진입점은 `OrderService.execute(OrderRequest)` 이고, 그 앞의 라우터·HMAC 서명 검증
(`WebhookService.ensure_authorized`)·TV payload 파싱(`parse_tv_payload`)·
`exchange_account_id` 추출은 **한 줄도 실행되지 않는다.** ⇒ 그 층만 깨진 회귀에서는
이 테스트가 **거래소 주문까지 성공하고도 초록**이다(2026-08-14 codex 적대 리뷰 P1).

그 층의 커버리지는 `tests/trading/test_router_orders.py`(HTTP/authz)와
`tests/trading/test_webhook_*.py` 가 갖는다 — 단 **거래소는 mock 이다.**
「HTTP 부터 실거래소까지」를 한 줄로 잇는 판은 아직 없다. 그것을 채우려면
`app` 픽스처의 `get_async_session` override 를 savepoint `db_session` 이 아니라
아래와 같은 **커밋 세션**으로 갈아야 한다 — 별건으로 남겼다([BL-024] 잔여).

## 왜 커밋 세션인가 · 왜 linear perp 인가

- 청산 하네스는 `create_worker_engine_and_sm()` 으로 **별도 엔진**을 연다. savepoint 기반
  `db_session` 의 commit 은 그 엔진에서 **안 보여서** 청산이 전건 `undecidable` 이 된다.
  ⇒ `_test_engine` 에서 만든 세션으로 실제 commit 한다.
- flat 판정이 `fetch_open_positions` 라 **spot 에는 포지션이 없어** 무엇을 사든 flat 이
  나온다(거짓 안전망). ⇒ `BTC/USDT:USDT` linear perp 만 쓴다.
- 청산 finalizer 가 계정·라이브 세션 행을 **테스트 함수가 끝난 뒤** 다시 읽으므로
  본문에서 seed 를 지우지 않는다.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.auth.models import User
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
async def test_order_service_to_bybit_demo_filled(
    _test_engine,
    bybit_demo_test_credentials: tuple[str, str],
    broker_flat_guard,
    _no_op_enqueue: dict[str, list[object]],
) -> None:
    """주문 원장 생성·실발주·watchdog 체결 확정과 청산 등록 순서를 함께 검증한다.

    ★이름이 `webhook` 이 아닌 이유는 모듈 docstring 을 봐라 — 진입점은 `OrderService` 이고
    HTTP·HMAC 층은 **이 테스트가 재지 않는다.**
    """
    api_key, api_secret = bybit_demo_test_credentials
    crypto = EncryptionService(settings.trading_encryption_keys)
    session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)

    async with session_factory() as session:
        user = User(
            auth_subject=f"real_broker_{uuid4().hex}",
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

        # ★DSN 교체를 손으로 재구현하지 마라 — `_test_dsn_in_effect` 가 정본이다.
        #   이 회차의 결함이 정확히 「같은 교체를 한 곳에서만 했다」였다([LESSON-109]).
        #   `_async_fetch_order_status` 도 `create_worker_engine_and_sm()` 을 타므로 같은 계약이다.
        order_after_watchdog = None
        with _harness._test_dsn_in_effect():
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

        assert order_after_watchdog is not None
        assert order_after_watchdog.state == OrderState.filled, (
            "Bybit Demo 시장가 주문이 초기 호출 뒤 3회의 watchdog 재확인에도 filled가 아니다."
        )
        assert order_after_watchdog.filled_price is not None
