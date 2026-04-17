"""Sprint 7a T4 — E2E: manual OrderRequest (BTC/USDT:USDT, leverage=5, margin_mode="cross")
→ OrderService.execute → Order(pending) → inline dispatcher awaits
task_mod._async_execute → BybitFuturesProvider → CCXT mock → Order(filled).

CCXT mock으로 네트워크 차단. Webhook TV payload parser 확장은 Sprint 7b로 분리되므로
manual service-level 경로를 통과해 leverage/margin_mode 전파 체인을 end-to-end 검증.

범위 & 경계:
- **service-level integration test** — HTTP/authz E2E 아님. Bybit v5 UTA CCXT 불변식
  (set_margin_mode → set_leverage → create_order 순서 + defaultType=linear + testnet)
  을 propagation 체인 전체로 잠그는 목적.
- HTTP/authz 경로는 Sprint 6 `test_router_orders.py`에서 이미 커버됨.
- 이 테스트는 conftest `db_session`의 savepoint wrapper와 `OrderService.execute`의
  `begin_nested()`가 같은 세션을 공유하기 때문에 벤인(benign) `SAWarning:
  nested transaction already deassociated`를 발생시킨다. Production에서 Celery
  워커는 별도 세션에서 돌기 때문에 이 경로를 타지 않는다. warnings-as-errors CI
  승격 시 이 테스트만 조용히 깨지지 않도록 `filterwarnings` 마크로 명시적 억제.

검증 포인트:
1. Order row state == filled
2. Order row leverage=5, margin_mode="cross"
3. Order row exchange_order_id + filled_price 채움
4. CCXT mock: set_margin_mode(("cross","BTC/USDT:USDT")) → set_leverage((5,"BTC/USDT:USDT"))
   → create_order 순서. defaultType="linear", testnet=True. close() await 됨.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService

# re-export guard: OrderService 레이어가 실제 instance를 기대하는 타입 참조 유지
from src.trading.kill_switch import KillSwitchService  # noqa: F401
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.repository import OrderRepository
from src.trading.schemas import OrderRequest
from src.trading.service import OrderService


def _make_fake_session_factory(db_session: AsyncSession):
    """Celery task가 사용하는 async_session_factory를 테스트 session으로 대체.

    test_celery_task.py / test_celery_task_futures.py와 동일 패턴.
    """

    @asynccontextmanager
    async def _session_ctx():
        yield db_session

    class _FakeSM:
        def __call__(self):
            return _session_ctx()

    return lambda: _FakeSM()


@pytest.fixture
def ccxt_futures_mock(monkeypatch: pytest.MonkeyPatch):
    """ccxt.async_support.bybit를 MagicMock으로 교체.

    set_margin_mode / set_leverage / create_order / close 모두 AsyncMock.
    create_order는 `id=fx-e2e-7` + `average=50234.5` + status=closed 반환.
    """
    mock_exchange = MagicMock()
    mock_exchange.set_margin_mode = AsyncMock(return_value=None)
    mock_exchange.set_leverage = AsyncMock(return_value=None)
    mock_exchange.create_order = AsyncMock(
        return_value={
            "id": "fx-e2e-7",
            "average": 50234.5,
            "status": "closed",
            "symbol": "BTC/USDT:USDT",
        }
    )
    mock_exchange.cancel_order = AsyncMock(return_value={})
    mock_exchange.close = AsyncMock()

    mock_bybit_cls = MagicMock(return_value=mock_exchange)

    import ccxt.async_support as ccxt_async

    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


class _NoopKillSwitch:
    """KillSwitch 통과용 no-op — E2E는 gating 경로가 아니라 propagation 체인 검증."""

    async def ensure_not_gated(self, *, strategy_id: UUID, account_id: UUID) -> None:
        return None


@pytest.mark.asyncio
@pytest.mark.filterwarnings(
    "ignore:nested transaction already deassociated:sqlalchemy.exc.SAWarning"
)
async def test_e2e_manual_futures_order_propagates_leverage_through_ccxt(
    db_session: AsyncSession,
    ccxt_futures_mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """manual OrderRequest(leverage=5, cross) → OrderService → _async_execute
    → BybitFuturesProvider → CCXT mock → Order(filled). 전 체인 불변식 검증.
    """
    import src.tasks.trading as task_mod

    # ── 1. Setup: User → Strategy → ExchangeAccount (FK + credentials 암호화) ──
    crypto = EncryptionService(settings.trading_encryption_keys)

    user = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="T4 E2E Futures Strategy",
        pine_source="//@version=5\nstrategy('t4-e2e')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("e2e-api-key-futures"),
        api_secret_encrypted=crypto.encrypt("e2e-api-secret-futures"),
        label="T4 e2e futures",
    )
    db_session.add(account)
    await db_session.commit()

    # ── 2. Exchange provider 설정: bybit_futures + lazy singleton 리셋 ──
    monkeypatch.setattr(task_mod.settings, "exchange_provider", "bybit_futures")
    monkeypatch.setattr(task_mod, "_exchange_provider", None)

    # ── 3. Celery task가 보는 session을 테스트 session으로 대체 ──
    monkeypatch.setattr(
        task_mod, "async_session_factory", _make_fake_session_factory(db_session)
    )

    # ── 4. Inline dispatcher — `_async_execute(order_id)`를 즉시 await ──
    dispatched_ids: list[UUID] = []

    class _InlineDispatcher:
        async def dispatch_order_execution(self, order_id: UUID) -> None:
            dispatched_ids.append(order_id)
            # Celery 경유 없이 바로 async path 실행 (CCXT는 mock 되어 있음)
            await task_mod._async_execute(order_id)

    # ── 5. OrderService 조립 (Repository + inline dispatcher + noop kill switch) ──
    order_repo = OrderRepository(db_session)
    service = OrderService(
        session=db_session,
        repo=order_repo,
        dispatcher=_InlineDispatcher(),
        kill_switch=_NoopKillSwitch(),  # type: ignore[arg-type]
    )

    # ── 6. Manual OrderRequest: Futures + leverage=5 + margin_mode=cross ──
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )

    # ── 7. Execute — 내부적으로 commit → inline dispatch → _async_execute ──
    response, is_replayed = await service.execute(req, idempotency_key=None)
    assert is_replayed is False
    assert len(dispatched_ids) == 1

    # ── 8. Order row (filled) 검증 ──
    order_id = response.id
    fetched = await order_repo.get_by_id(order_id)
    assert fetched is not None
    assert fetched.state == OrderState.filled
    assert fetched.leverage == 5
    assert fetched.margin_mode == "cross"
    assert fetched.exchange_order_id == "fx-e2e-7"
    assert fetched.filled_price == Decimal("50234.5")
    assert fetched.symbol == "BTC/USDT:USDT"

    # ── 9. CCXT mock 호출 순서/인자 검증 (Bybit v5 UTA: margin_mode → leverage → order) ──
    mock_exchange, mock_bybit_cls = ccxt_futures_mock

    call_kwargs = mock_bybit_cls.call_args.args[0]
    assert call_kwargs["apiKey"] == "e2e-api-key-futures"
    assert call_kwargs["secret"] == "e2e-api-secret-futures"
    assert call_kwargs["options"]["defaultType"] == "linear"
    assert call_kwargs["options"]["testnet"] is True

    mock_exchange.set_margin_mode.assert_awaited_once_with("cross", "BTC/USDT:USDT")
    mock_exchange.set_leverage.assert_awaited_once_with(5, "BTC/USDT:USDT")
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT", "market", "buy", 0.001, None
    )
    mock_exchange.close.assert_awaited_once()
