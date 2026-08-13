"""Trading 도메인 모델 구조 검증 — 마이그레이션 생성 전 SQLModel 인스턴스 정합성."""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4


def test_exchange_account_model_fields():
    from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName

    account = ExchangeAccount(
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"encrypted-key",
        api_secret_encrypted=b"encrypted-secret",
    )
    assert account.id is not None
    assert account.exchange == ExchangeName.bybit
    assert account.mode == ExchangeMode.demo
    assert account.api_key_encrypted == b"encrypted-key"
    assert account.created_at.tzinfo is not None  # AwareDateTime


def test_order_model_fields():
    from src.trading.models import Order, OrderSide, OrderState, OrderType

    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.01"),
        state=OrderState.pending,
        idempotency_key="test-key-123",
        webhook_payload={"source": "tv"},
    )
    assert order.id is not None
    assert order.quantity == Decimal("0.01")
    assert order.state == OrderState.pending
    assert order.idempotency_key == "test-key-123"


def test_kill_switch_event_model_fields():
    from src.trading.models import KillSwitchEvent, KillSwitchTriggerType

    event = KillSwitchEvent(
        trigger_type=KillSwitchTriggerType.cumulative_loss,
        strategy_id=uuid4(),
        trigger_value=Decimal("15.0"),
        threshold=Decimal("10.0"),
    )
    assert event.trigger_type == KillSwitchTriggerType.cumulative_loss
    assert event.resolved_at is None
    assert event.triggered_at.tzinfo is not None


def test_webhook_secret_model_fields():
    from src.trading.models import WebhookSecret

    ws = WebhookSecret(
        strategy_id=uuid4(),
        secret_encrypted=b"some-encrypted-hmac-secret-bytes",
    )
    assert ws.id is not None
    assert ws.revoked_at is None
    assert ws.created_at.tzinfo is not None
