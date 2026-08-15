"""Sprint 7a T4 — E2E: manual OrderRequest (BTC/USDT:USDT, leverage=5, margin_mode="cross")
→ OrderService.execute → Order(pending) → inline dispatcher awaits
task_mod._async_execute → BybitFuturesProvider → CCXT mock → Order(filled).

CCXT mock으로 네트워크 차단. Webhook TV payload parser 확장은 Sprint 7b로 분리되므로
manual service-level 경로를 통과해 leverage/margin_mode 전파 체인을 end-to-end 검증.

범위 & 경계:
- **service-level integration test** — HTTP/authz E2E 아님. Bybit v5 UTA CCXT 불변식
  (set_margin_mode → set_leverage → create_order 순서 + defaultType=linear + demo)
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
   → create_order 순서. defaultType="linear", testnet=False(demo), enable_demo_trading(True). close() await 됨.
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
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import OrderRequest
from src.trading.services.order_service import OrderService


class _NoopEngine:
    """Sprint 17 Phase C — async dispose no-op for tests."""

    async def dispose(self) -> None:
        return None


def _make_fake_create_worker_engine_and_sm(db_session: AsyncSession):
    """Sprint 17 Phase C — (engine, sm) tuple matching backtest.py:31.

    test_celery_task.py / test_celery_task_futures.py 와 동일 패턴.
    """

    @asynccontextmanager
    async def _session_ctx():
        yield db_session

    class _FakeSM:
        def __call__(self):
            return _session_ctx()

    def _factory():
        return _NoopEngine(), _FakeSM()

    return _factory


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
    # MP-4: precision 변환 stub (str passthrough).
    mock_exchange.load_markets = AsyncMock(return_value={})
    mock_exchange.amount_to_precision = MagicMock(side_effect=lambda symbol, amount: str(amount))
    mock_exchange.price_to_precision = MagicMock(side_effect=lambda symbol, price: str(price))

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
        auth_subject=f"user_{uuid4().hex[:8]}",
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

    # ── 2. Sprint 22 BL-091: dispatch 가 ExchangeAccount(bybit, demo) +
    # OrderRequest(leverage=5) 로 자동 BybitFuturesProvider 라우트.
    # Sprint 21 까지의 settings.exchange_provider="bybit_futures" 강제 불필요.
    # ── 3. Celery task가 보는 session을 테스트 session으로 대체 ──
    monkeypatch.setattr(
        task_mod,
        "create_worker_engine_and_sm",
        _make_fake_create_worker_engine_and_sm(db_session),
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
    # account.mode=demo → testnet=False, enable_demo_trading(True) 호출
    assert call_kwargs["options"]["testnet"] is False
    mock_exchange.enable_demo_trading.assert_called_once_with(True)

    mock_exchange.set_margin_mode.assert_awaited_once_with("cross", "BTC/USDT:USDT")
    mock_exchange.set_leverage.assert_awaited_once_with(5, "BTC/USDT:USDT")
    # Sprint 12 Phase C: Celery task 가 OrderSubmit.client_order_id=str(order.id) 채움
    # → 6번째 positional 인자로 {"orderLinkId": <UUID-str>} 전달.
    create_call = mock_exchange.create_order.await_args
    assert create_call.args[:5] == ("BTC/USDT:USDT", "market", "buy", "0.001", None)
    assert "orderLinkId" in create_call.args[5]
    assert len(create_call.args[5]["orderLinkId"]) == 36  # UUID4 string
    mock_exchange.close.assert_awaited_once()


# === BL-474 — 위 독스트링이 "Sprint 7b 로 분리" 라고 적어둔 그 부채 ===
#
# Sprint 7a 는 webhook payload 경로를 미루고 manual service-level 로만 leverage
# 전파를 잠갔다. 그 미룸이 그대로 남아, HTTP ingress 로 들어온 주문은 leverage 를
# 해결하지 않아 spot 으로 나갔다. 아래가 그 마지막 고리를 HTTP 부터 ccxt 까지 잠근다.


class _StubGuardProvider:
    """notional 가드 경로 전용 stub (fail-soft None).

    주문 자체는 `tasks/trading.py` 가 registry 로 새 BybitFuturesProvider 를 만들어
    쓰므로 ccxt mock 이 그대로 관측한다 — 이 override 는 가드만 잠재운다.
    """

    async def fetch_mark_price(self, creds, symbol):
        return None

    async def fetch_min_notional(self, creds, symbol):
        return None

    async def fetch_balance(self, creds):
        return {}


@pytest.mark.asyncio
@pytest.mark.filterwarnings(
    "ignore:nested transaction already deassociated:sqlalchemy.exc.SAWarning"
)
async def test_e2e_webhook_payload_routes_to_bybit_linear_provider(
    client,
    app,
    db_session: AsyncSession,
    ccxt_futures_mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP webhook POST → HMAC → 파싱 → settings 해결 → linear perp 체결.

    심볼로 `BTCUSDT` 를 보내 정규화 사슬을 실제로 통과시킨다 —
    `normalize_symbol_input` → `BTC/USDT` → `_to_bybit_linear_symbol` →
    `BTC/USDT:USDT`. 다이얼로그 기본값이 `BTCUSDT` 라 이게 실사용 형태다.
    """
    import hashlib
    import hmac as hmac_module
    import json

    import src.tasks.trading as task_mod
    from src.trading.dependencies import get_bybit_futures_provider, get_order_dispatcher
    from src.trading.models import WebhookSecret

    crypto = EncryptionService(settings.trading_encryption_keys)

    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="BL-474 webhook→linear",
        pine_source="//@version=5\nstrategy('bl474')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings={
            "schema_version": 1,
            "leverage": 2,
            "margin_mode": "isolated",
            "position_size_pct": 0.01,
        },
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("bl474-api-key"),
        api_secret_encrypted=crypto.encrypt("bl474-api-secret"),
        label="bl474 webhook",
    )
    db_session.add(account)
    await db_session.flush()

    plaintext_secret = "BL474_E2E_SECRET"
    db_session.add(
        WebhookSecret(
            strategy_id=strategy.id,
            secret_encrypted=crypto.encrypt(plaintext_secret),
        )
    )
    await db_session.flush()

    monkeypatch.setattr(
        task_mod,
        "create_worker_engine_and_sm",
        _make_fake_create_worker_engine_and_sm(db_session),
    )

    dispatched_ids: list[UUID] = []

    class _InlineDispatcher:
        async def dispatch_order_execution(self, order_id: UUID) -> None:
            dispatched_ids.append(order_id)
            await task_mod._async_execute(order_id)

    app.dependency_overrides[get_order_dispatcher] = _InlineDispatcher
    app.dependency_overrides[get_bybit_futures_provider] = _StubGuardProvider

    payload = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "quantity": "0.001",
        "type": "market",
        "exchange_account_id": str(account.id),
    }
    body_bytes = json.dumps(payload).encode()
    token = hmac_module.new(plaintext_secret.encode(), body_bytes, hashlib.sha256).hexdigest()

    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={token}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 201, res.text
    assert len(dispatched_ids) == 1

    fetched = await OrderRepository(db_session).get_by_id(UUID(res.json()["id"]))
    assert fetched is not None
    assert fetched.state == OrderState.filled
    assert fetched.leverage == 2
    assert fetched.margin_mode == "isolated"
    # 세션 스코프는 정확 문자열 동등이라 canonical 로 저장돼야 한다 (BL-454).
    assert fetched.symbol == "BTC/USDT"

    mock_exchange, mock_bybit_cls = ccxt_futures_mock
    assert mock_bybit_cls.call_args.args[0]["options"]["defaultType"] == "linear"
    mock_exchange.set_margin_mode.assert_awaited_once_with("isolated", "BTC/USDT:USDT")
    mock_exchange.set_leverage.assert_awaited_once_with(2, "BTC/USDT:USDT")
    assert mock_exchange.create_order.await_args.args[0] == "BTC/USDT:USDT"
