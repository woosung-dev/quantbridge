"""Webhook POST endpoint E2E tests (T19).

Tests HMAC acceptance/rejection through the HTTP endpoint.
Webhook is PUBLIC (no JWT) -- HMAC token IS the authentication.
CSO-1: WebhookSecret uses secret_encrypted (bytes, not plaintext).
CSO-6: MAX_WEBHOOK_BODY = 64KB cap verified.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.trading.encryption import EncryptionService
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName, WebhookSecret


@pytest.fixture
def crypto():
    """EncryptionService with a test key for CSO-1 encrypted secrets."""
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


def _sign(secret: str, body_bytes: bytes) -> str:
    """Compute HMAC-SHA256 hex digest (uses plaintext secret, not encrypted)."""
    return hmac_module.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()


def _tv_payload(
    exchange_account_id: str,
    *,
    symbol: str = "BTC/USDT",
    side: str = "buy",
    quantity: str = "0.01",
    order_type: str = "market",
) -> dict:
    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "type": order_type,
        "exchange_account_id": exchange_account_id,
    }


class _FakeDispatcher:
    """Celery dispatcher mock -- prevents Redis connection in tests."""

    def __init__(self) -> None:
        self.dispatched_ids: list[str] = []

    async def dispatch_order_execution(self, order_id):
        self.dispatched_ids.append(str(order_id))


@pytest.mark.asyncio
async def test_webhook_valid_hmac_returns_201(client, app, db_session, crypto):
    """Valid HMAC token -> 201 (order created)."""
    # --- Setup: user, strategy, exchange account, webhook secret ---
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="Webhook Test Strategy",
        pine_source="// test",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        # BL-474 — webhook 은 이제 Strategy.settings 에서 leverage/margin_mode 를
        # 해결한다. settings 없는 전략은 422 (별도 테스트가 그 정책을 잠근다).
        settings={
            "schema_version": 1,
            "leverage": 2,
            "margin_mode": "isolated",
            "position_size_pct": 0.01,
        },
    )
    db_session.add(strategy)
    await db_session.flush()

    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test_api_key_1234"),
        api_secret_encrypted=crypto.encrypt("test_api_secret_1234"),
        label="test",
    )
    db_session.add(acct)
    await db_session.flush()

    plaintext_secret = "MY_WEBHOOK_SECRET_123"
    ws = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt(plaintext_secret),
    )
    db_session.add(ws)
    await db_session.flush()

    # --- Override EncryptionService + OrderDispatcher + Futures provider ---
    # BL-474 — leverage 가 채워지면서 notional 가드가 처음으로 활성화된다.
    # 실 CCXT 를 막되 소유권 게이트는 실 repo 로 유지하려면 provider 를 갈아끼운다.
    from src.trading.dependencies import (
        get_bybit_futures_provider,
        get_encryption_service,
        get_order_dispatcher,
    )

    app.dependency_overrides[get_encryption_service] = lambda: crypto
    app.dependency_overrides[get_order_dispatcher] = _FakeDispatcher
    app.dependency_overrides[get_bybit_futures_provider] = _StubFuturesProvider

    # --- Build signed request ---
    payload = _tv_payload(str(acct.id))
    body_bytes = json.dumps(payload).encode()
    token = _sign(plaintext_secret, body_bytes)

    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={token}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["strategy_id"] == str(strategy.id)
    assert body["exchange_account_id"] == str(acct.id)
    assert body["symbol"] == "BTC/USDT"
    assert body["side"] == "buy"
    assert body["state"] == "pending"

    # cleanup overrides
    app.dependency_overrides.pop(get_encryption_service, None)
    app.dependency_overrides.pop(get_order_dispatcher, None)


@pytest.mark.asyncio
async def test_webhook_bad_hmac_returns_401(client, app, db_session, crypto):
    """Invalid HMAC token -> 401."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="Webhook Test Strategy",
        pine_source="// test",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test_api_key_1234"),
        api_secret_encrypted=crypto.encrypt("test_api_secret_1234"),
    )
    db_session.add(acct)
    await db_session.flush()

    ws = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt("REAL_SECRET"),
    )
    db_session.add(ws)
    await db_session.flush()

    from src.trading.dependencies import get_encryption_service

    app.dependency_overrides[get_encryption_service] = lambda: crypto

    payload = _tv_payload(str(acct.id))
    body_bytes = json.dumps(payload).encode()
    # Sign with WRONG secret
    token = _sign("WRONG_SECRET", body_bytes)

    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={token}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )

    assert res.status_code == 401, res.text

    app.dependency_overrides.pop(get_encryption_service, None)


@pytest.mark.asyncio
async def test_webhook_missing_token_returns_422(client):
    """Missing token query param -> 422 (FastAPI validation)."""
    strategy_id = uuid4()
    res = await client.post(
        f"/api/v1/webhooks/{strategy_id}",
        content=b'{"symbol":"BTC/USDT","side":"buy","quantity":"0.01"}',
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_webhook_body_too_large_returns_413(client):
    """CSO-6: Content-Length > 64KB -> 413."""
    strategy_id = uuid4()
    # Create a body larger than 64KB
    large_body = b"x" * (64 * 1024 + 1)
    res = await client.post(
        f"/api/v1/webhooks/{strategy_id}?token=fake",
        content=large_body,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(large_body)),
        },
    )
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_webhook_no_auth_header_required(client):
    """Webhook is PUBLIC -- no JWT auth required. Should NOT get 401 for missing auth.

    It should fail for other reasons (missing HMAC match), not for missing JWT.
    """
    strategy_id = uuid4()
    payload = json.dumps({"symbol": "BTC/USDT", "side": "buy", "quantity": "0.01"}).encode()
    token = _sign("some_secret", payload)

    res = await client.post(
        f"/api/v1/webhooks/{strategy_id}?token={token}",
        content=payload,
        headers={"Content-Type": "application/json"},
        # NOTE: no Authorization header -- this is intentional
    )
    # Should be 401 (HMAC mismatch, no secrets in DB) -- NOT 403 (missing JWT)
    assert res.status_code == 401


# === BL-474 — webhook ingress 가 라이브 신호와 다른 시장으로 나가던 문제 ===
#
# 다이얼로그/TV 로 들어온 주문은 leverage 를 아예 해결하지 않아
# `order_service.py:194` 가 has_leverage=False 를 찍고 → `registry.py:37` 이
# BybitDemoProvider(spot) 를 고른다. 그런데 청산 원장(/v5/position/closed-pnl)·
# 포지션 코크핏·exchange_exits 는 전부 linear 전용이라, 그 체결은 확정 손익을
# 영원히 못 받는다. 즉 이 도구로 한 머니-패스 검증은 조용히 무효였다.
#
# 해결 지점은 Strategy.settings — live_signal.py:931-932 / close_service.py:86-92
# 가 이미 쓰는 SSOT 다. payload 로 받지 않는다(secret 보유자가 운영자 리스크
# 설정을 우회하게 두지 않는다).

_VALID_SETTINGS: dict[str, object] = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "isolated",
    "position_size_pct": 0.01,
}


class _StubFuturesProvider:
    """leverage 가 채워지면 notional 가드(`order_service.py:218-266`)가 처음으로
    활성화되어 실 CCXT 를 친다. 서비스가 아니라 provider 를 대신 넣어야
    TRD-4 소유권 게이트가 실 repo 로 계속 작동한다.

    전부 None = fail-soft. market order 는 `:229` 에서 단락되고 demo 는
    `:277-288` fail-open 분기를 탄다.
    """

    async def fetch_mark_price(self, creds, symbol):
        return None

    async def fetch_min_notional(self, creds, symbol):
        return None

    async def fetch_balance(self, creds):
        return {}


async def _seed_webhook_fixture(db_session, crypto, *, settings: object):
    """user / strategy(settings) / bybit demo account / webhook secret 한 벌."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="BL-474 Strategy",
        pine_source="// test",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=settings,
    )
    db_session.add(strategy)
    await db_session.flush()

    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("test_api_key_1234"),
        api_secret_encrypted=crypto.encrypt("test_api_secret_1234"),
        label="bl474",
    )
    db_session.add(acct)
    await db_session.flush()

    plaintext_secret = "BL474_WEBHOOK_SECRET"
    ws = WebhookSecret(
        strategy_id=strategy.id,
        secret_encrypted=crypto.encrypt(plaintext_secret),
    )
    db_session.add(ws)
    await db_session.flush()

    return user, strategy, acct, plaintext_secret


def _install_overrides(app, crypto):
    from src.trading.dependencies import (
        get_bybit_futures_provider,
        get_encryption_service,
        get_order_dispatcher,
    )

    app.dependency_overrides[get_encryption_service] = lambda: crypto
    app.dependency_overrides[get_order_dispatcher] = _FakeDispatcher
    app.dependency_overrides[get_bybit_futures_provider] = _StubFuturesProvider


@pytest.mark.asyncio
async def test_webhook_order_inherits_strategy_settings_and_routes_linear(
    client, app, db_session, crypto
):
    """★BL-474 핵심 핀. webhook 주문이 전략 Live Settings 를 상속해 linear 로 간다.

    `dispatch_snapshot["has_leverage"]` 를 단정하는 이유 — 이 값이 곧
    `tasks/trading.py:_provider_from_order_snapshot_or_fallback` 의 라우팅 입력이다.
    leverage 컬럼만 보면 스냅샷이 뒤처져도 통과해버린다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    _, strategy, acct, secret = await _seed_webhook_fixture(
        db_session, crypto, settings=_VALID_SETTINGS
    )
    _install_overrides(app, crypto)

    body_bytes = json.dumps(_tv_payload(str(acct.id))).encode()
    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={_sign(secret, body_bytes)}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 201, res.text

    order = await OrderRepository(db_session).get_by_id(UUID(res.json()["id"]))
    assert order is not None
    assert order.leverage == 2
    assert order.margin_mode == "isolated"
    assert order.dispatch_snapshot is not None
    assert order.dispatch_snapshot["has_leverage"] is True
    assert order.dispatch_snapshot["exchange"] == "bybit"
    assert order.dispatch_snapshot["mode"] == "demo"


@pytest.mark.asyncio
async def test_webhook_forwards_reduce_only_and_bracket_levels(client, app, db_session, crypto):
    """프론트가 이미 보내던 3 필드가 주문 행까지 도달한다.

    reduce_only 가 특히 중요하다 — 이게 False 로 저장되면 그 청산은 단건 즉시 확정
    (`_refresh_closed_pnl_with_session` 의 `not order.reduce_only` 조기 반환)에 안 잡혀
    체결 직후 손익이 "추정" 으로 남는다.

    ★[BL-438] 2026-08-14 정정 — 종전 docstring 은 스윕에도 "영원히" 안 잡힌다고 적었다.
    이제 거짓이다: 스윕은 `list_unsynced_with_exchange_exit` 로 바뀌어 거래소 원장의
    청산 행을 보므로 `reduce_only=false` 인 반전 청산도 회수한다.
    """
    from src.trading.repositories.order_repository import OrderRepository

    _, strategy, acct, secret = await _seed_webhook_fixture(
        db_session, crypto, settings=_VALID_SETTINGS
    )
    _install_overrides(app, crypto)

    payload = _tv_payload(str(acct.id), side="sell")
    payload["reduce_only"] = True
    payload["take_profit"] = "70000.5"
    payload["stop_loss"] = "48000"
    body_bytes = json.dumps(payload).encode()

    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={_sign(secret, body_bytes)}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 201, res.text

    order = await OrderRepository(db_session).get_by_id(UUID(res.json()["id"]))
    assert order is not None
    assert order.reduce_only is True
    assert order.take_profit == Decimal("70000.5")
    assert order.stop_loss == Decimal("48000")


@pytest.mark.asyncio
async def test_webhook_rejects_when_strategy_settings_unset(client, app, db_session, crypto):
    """settings 미설정 → 422 fail-closed. live_signal / close_service 와 동일 정책.

    spot 으로 흘려보내면 그 진입은 **닫을 수단이 없다** — 모든 청산 경로가
    linear reduce-only 로 나가고 거래소는 110017 로 거부한다.
    주문 행이 0개여야 한다. 거부해놓고 pending 을 남기면 그게 더 나쁘다.
    """
    from sqlalchemy import func, select

    from src.trading.models import Order

    _, strategy, acct, secret = await _seed_webhook_fixture(db_session, crypto, settings=None)
    _install_overrides(app, crypto)

    body_bytes = json.dumps(_tv_payload(str(acct.id))).encode()
    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={_sign(secret, body_bytes)}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "settings_unset"

    count = await db_session.execute(
        select(func.count()).select_from(Order).where(Order.strategy_id == strategy.id)
    )
    assert count.scalar_one() == 0


@pytest.mark.asyncio
async def test_webhook_rejects_when_strategy_settings_invalid(client, app, db_session, crypto):
    """스키마를 벗어난 settings → 422 settings_invalid (조용한 fallback 금지)."""
    _, strategy, acct, secret = await _seed_webhook_fixture(
        db_session, crypto, settings={"leverage": 999}
    )
    _install_overrides(app, crypto)

    body_bytes = json.dumps(_tv_payload(str(acct.id))).encode()
    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={_sign(secret, body_bytes)}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422, res.text
    assert res.json()["detail"] == "settings_invalid"


@pytest.mark.asyncio
async def test_webhook_settings_resolution_happens_after_hmac(client, app, db_session, crypto):
    """★순서 고정. settings 해결이 HMAC 앞에 오면 미인증 호출자가 응답 코드
    차이(401 vs 422)만으로 어느 strategy_id 에 settings 가 있는지 캘 수 있다.
    """
    _, strategy, acct, _secret = await _seed_webhook_fixture(db_session, crypto, settings=None)
    _install_overrides(app, crypto)

    body_bytes = json.dumps(_tv_payload(str(acct.id))).encode()
    res = await client.post(
        f"/api/v1/webhooks/{strategy.id}?token={_sign('WRONG_SECRET', body_bytes)}",
        content=body_bytes,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 401, res.text
