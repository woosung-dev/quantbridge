"""BL-512 거래소 주문 응답 계측의 retCode 분류와 주문 경로 배선을 검증한다."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import src.tasks.trading as trading_module
from src.common.metrics import (
    _normalize_exchange_order_response_reason,
    qb_exchange_order_response_total,
    qb_live_conditional_guard_total,
)
from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, ExchangeName, OrderSide, OrderState, OrderType
from src.trading.providers import OrderReceipt

_TRIGGER_BREACHED_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110093,"retMsg":"expect Falling, '
    'but trigger_price[633023000] >= current[632859000]??LastPrice","result":{},'
    '"retExtInfo":{},"time":1785212835243}'
)
_LONG_TRIGGER_BREACHED_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110092,"retMsg":"expect Rising, '
    'but trigger_price[633023000] <= current[632859000]??LastPrice","result":{},'
    '"retExtInfo":{},"time":1785212835243}'
)
_REDUCE_ONLY_VIOLATION_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110017,"retMsg":"current position '
    'is zero, cannot fix reduce-only order qty","result":{},"retExtInfo":{},'
    '"time":1785035422319}'
)
_POSITION_ZERO_RESPONSE = (
    'provider_failure: InvalidOrder: bybit {"retCode":110034,"retMsg":"There is no net '
    'position","result":{},"retExtInfo":{},"time":1785035422319}'
)
_PERMISSION_DENIED_RESPONSE = (
    'provider_failure: PermissionDenied: bybit {"retCode":10005,"retMsg":"Invalid API-key, '
    'IP, or permissions for action.","result":{},"retExtInfo":{},"time":1785034847821}'
)


class _SessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _Crypto:
    def __init__(self, _keys: object) -> None:
        pass

    def decrypt(self, _value: object) -> str:
        return "credential"


def _order() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        exchange_account_id=uuid4(),
        state=OrderState.pending,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=None,
        margin_mode=None,
        reduce_only=False,
        trigger_price=None,
        trigger_by=None,
        take_profit=None,
        stop_loss=None,
        trigger_direction=None,
        oco_group_id=None,
        trailing_stop=None,
    )


def _account(order: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=order.exchange_account_id,
        user_id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"api-key",
        api_secret_encrypted=b"api-secret",
        passphrase_encrypted=None,
        exchange_uid=None,
    )


def _receipt(status: str) -> OrderReceipt:
    return OrderReceipt(
        exchange_order_id=f"bybit-{status}",
        filled_price=Decimal("100") if status == "filled" else None,
        status=status,  # type: ignore[arg-type]
        raw={},
    )


def _patch_execution(
    monkeypatch: pytest.MonkeyPatch,
    response: OrderReceipt | ProviderError,
) -> tuple[SimpleNamespace, SimpleNamespace]:
    order = _order()
    account = _account(order)
    session = SimpleNamespace(
        commit=AsyncMock(),
        get=AsyncMock(return_value=account),
    )
    repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=order),
        transition_to_submitted=AsyncMock(return_value=1),
        transition_to_filled=AsyncMock(return_value=1),
        transition_to_rejected=AsyncMock(return_value=1),
        attach_exchange_order_id=AsyncMock(),
    )
    provider = SimpleNamespace(
        create_order=AsyncMock(
            side_effect=response if isinstance(response, ProviderError) else None,
            return_value=None if isinstance(response, ProviderError) else response,
        )
    )

    monkeypatch.setattr(trading_module, "OrderRepository", MagicMock(return_value=repo))
    monkeypatch.setattr(trading_module, "EncryptionService", _Crypto)
    monkeypatch.setattr(
        trading_module,
        "_provider_from_order_snapshot_or_fallback",
        lambda *_args, **_kwargs: provider,
    )
    monkeypatch.setattr(trading_module, "publish_realtime", AsyncMock())
    monkeypatch.setattr(trading_module, "_enqueue_trailing_if_intended", lambda _order: None)
    monkeypatch.setattr(trading_module, "_enqueue_closed_pnl_refresh", lambda _order: None)
    monkeypatch.setattr(trading_module.fetch_order_status_task, "apply_async", MagicMock())

    return SimpleNamespace(order=order, repo=repo, provider=provider), session


async def _execute(
    monkeypatch: pytest.MonkeyPatch, response: OrderReceipt | ProviderError
) -> tuple[dict[str, object], SimpleNamespace]:
    harness, session = _patch_execution(monkeypatch, response)
    result = await trading_module._execute_with_session(
        harness.order.id,
        lambda: _SessionContext(session),  # type: ignore[arg-type]
    )
    return result, harness


def test_110093_maps_to_trigger_breached_reason() -> None:
    assert _normalize_exchange_order_response_reason(_TRIGGER_BREACHED_RESPONSE) == "trigger_breached"


def test_110092_maps_to_trigger_breached_reason() -> None:
    assert _normalize_exchange_order_response_reason(_LONG_TRIGGER_BREACHED_RESPONSE) == "trigger_breached"


def test_110017_maps_to_reduce_only_violation() -> None:
    assert (
        _normalize_exchange_order_response_reason(_REDUCE_ONLY_VIOLATION_RESPONSE)
        == "reduce_only_violation"
    )


def test_110034_maps_to_position_zero() -> None:
    assert _normalize_exchange_order_response_reason(_POSITION_ZERO_RESPONSE) == "position_zero"


def test_same_ccxt_class_splits_by_retcode() -> None:
    assert "InvalidOrder" in _TRIGGER_BREACHED_RESPONSE
    assert "InvalidOrder" in _REDUCE_ONLY_VIOLATION_RESPONSE
    assert _normalize_exchange_order_response_reason(
        _TRIGGER_BREACHED_RESPONSE
    ) != _normalize_exchange_order_response_reason(_REDUCE_ONLY_VIOLATION_RESPONSE)


def test_10005_maps_to_permission_denied() -> None:
    assert _normalize_exchange_order_response_reason(_PERMISSION_DENIED_RESPONSE) == "permission_denied"


def test_auth_error_codes_split_from_permission() -> None:
    for retcode in ("10003", "10004"):
        response = _PERMISSION_DENIED_RESPONSE.replace("10005", retcode, 1)
        assert _normalize_exchange_order_response_reason(response) == "auth_failed"
    for retcode in ("10005", "10010", "10020", "10027", "10028"):
        response = _PERMISSION_DENIED_RESPONSE.replace("10005", retcode, 1)
        assert _normalize_exchange_order_response_reason(response) == "permission_denied"


def test_unknown_retcode_falls_back_to_other() -> None:
    unknown_response = _TRIGGER_BREACHED_RESPONSE.replace("110093", "999999", 1)
    assert _normalize_exchange_order_response_reason(unknown_response) == "other"


def test_missing_retcode_falls_back_to_unparsed() -> None:
    missing_response = _TRIGGER_BREACHED_RESPONSE.replace('"retCode":110093,', "", 1)
    assert _normalize_exchange_order_response_reason(missing_response) == "unparsed"


async def test_provider_error_rejection_increments_with_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter = qb_exchange_order_response_total.labels(
        exchange="bybit",
        outcome="rejected",
        reason="trigger_breached",
    )
    before = counter._value.get()

    result, _ = await _execute(monkeypatch, ProviderError(_TRIGGER_BREACHED_RESPONSE))

    assert result["state"] == "rejected"
    assert counter._value.get() == before + 1


async def test_network_error_records_unknown_not_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter = qb_exchange_order_response_total.labels(
        exchange="bybit",
        outcome="unknown",
        reason="unparsed",
    )
    before = counter._value.get()

    result, _ = await _execute(monkeypatch, ProviderError("NetworkError: connection timeout"))

    assert result["state"] == "rejected"
    assert counter._value.get() == before + 1


async def test_unparsed_message_is_unknown_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter = qb_exchange_order_response_total.labels(
        exchange="bybit",
        outcome="unknown",
        reason="unparsed",
    )
    before = counter._value.get()

    result, _ = await _execute(
        monkeypatch,
        ProviderError("malformed Bybit response: missing 'id'"),
    )

    assert result["state"] == "rejected"
    assert counter._value.get() == before + 1


async def test_rejected_at_submission_increments(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = qb_exchange_order_response_total.labels(
        exchange="bybit",
        outcome="rejected",
        reason="rejected_at_submission",
    )
    before = counter._value.get()

    result, _ = await _execute(monkeypatch, _receipt("rejected"))

    assert result["state"] == "rejected"
    assert counter._value.get() == before + 1


async def test_successful_fill_increments_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = qb_exchange_order_response_total.labels(
        exchange="bybit",
        outcome="accepted",
        reason="filled",
    )
    before = counter._value.get()

    result, _ = await _execute(monkeypatch, _receipt("filled"))

    assert result["state"] == "filled"
    assert counter._value.get() == before + 1


async def test_submitted_increments_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = qb_exchange_order_response_total.labels(
        exchange="bybit",
        outcome="accepted",
        reason="submitted",
    )
    before = counter._value.get()

    result, harness = await _execute(monkeypatch, _receipt("submitted"))

    assert result["state"] == "submitted"
    harness.repo.attach_exchange_order_id.assert_awaited_once()
    assert counter._value.get() == before + 1


def test_guard_metric_rejects_unknown_outcome() -> None:
    with pytest.raises(ValueError, match="Unsupported live conditional guard outcome"):
        qb_live_conditional_guard_total.labels(outcome="unknown")


def test_guard_metric_accepts_new_outcomes() -> None:
    qb_live_conditional_guard_total.labels(outcome="convert_suppressed")
    qb_live_conditional_guard_total.labels(outcome="breach_reverted")


async def test_metric_failure_does_not_break_order_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def metric_failure(**_labels: str) -> object:
        raise OSError("metrics mmap is read-only")

    monkeypatch.setattr(
        trading_module.qb_exchange_order_response_total,
        "labels",
        metric_failure,
    )

    result, harness = await _execute(monkeypatch, _receipt("submitted"))

    assert result["state"] == "submitted"
    harness.provider.create_order.assert_awaited_once()
    harness.repo.attach_exchange_order_id.assert_awaited_once()
