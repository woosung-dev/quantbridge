"""Sprint 23 BL-102 — Order.dispatch_snapshot priority + legacy fallback.

codex G.0 P1 #4 + G.2 P2 #3 verifier:
- snapshot 우선 사용 (account.mode 변경되어도 snapshot 가 winner)
- invalid snapshot (missing key / unknown enum / non-bool) → graceful fallback + metric
- legacy NULL snapshot → fallback + metric inc(reason=missing)
- JSONB manual mutation 시 task crash 안 됨

호출 진입점: `_provider_from_order_snapshot_or_fallback(order, account, submit)` +
`_parse_order_dispatch_snapshot(raw)` 단위 테스트.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY

from src.tasks.trading import (
    _parse_order_dispatch_snapshot,
    _provider_from_order_snapshot_or_fallback,
)
from src.trading.exceptions import UnsupportedExchangeError
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import (
    BybitDemoProvider,
    BybitFuturesProvider,
    OkxDemoProvider,
    OrderSubmit,
)


def _account(exchange: ExchangeName, mode: ExchangeMode) -> ExchangeAccount:
    return ExchangeAccount(
        user_id=uuid4(),
        exchange=exchange,
        mode=mode,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"x",
    )


def _order(snapshot: dict | None = None, leverage: int | None = None) -> Order:
    return Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
        leverage=leverage,
        dispatch_snapshot=snapshot,
    )


def _fallback_metric_value(reason: str) -> float:
    """qb_order_snapshot_fallback_total{reason=...} 현재 값 (test 격리용 baseline)."""
    val = REGISTRY.get_sample_value(
        "qb_order_snapshot_fallback_total", {"reason": reason}
    )
    return val if val is not None else 0.0


# ----------------------------------------------------------------------
# _parse_order_dispatch_snapshot 단위 — 엄격 검증 (codex G.0 P1 #4)
# ----------------------------------------------------------------------


class TestParseSnapshotStrict:
    """invalid JSONB 가 None 반환 (task crash 회피)."""

    def test_valid_snapshot(self) -> None:
        raw = {"exchange": "bybit", "mode": "demo", "has_leverage": False}
        parsed = _parse_order_dispatch_snapshot(raw)
        assert parsed == (ExchangeName.bybit, ExchangeMode.demo, False)

    def test_valid_snapshot_with_leverage(self) -> None:
        raw = {"exchange": "bybit", "mode": "demo", "has_leverage": True}
        parsed = _parse_order_dispatch_snapshot(raw)
        assert parsed == (ExchangeName.bybit, ExchangeMode.demo, True)

    def test_none_returns_none(self) -> None:
        assert _parse_order_dispatch_snapshot(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert _parse_order_dispatch_snapshot({}) is None

    def test_missing_key(self) -> None:
        raw = {"exchange": "bybit", "mode": "demo"}  # has_leverage 누락
        assert _parse_order_dispatch_snapshot(raw) is None

    def test_unknown_exchange_enum(self) -> None:
        """codex G.0 P1 #4 — DB manual mutation 으로 unknown enum 입력."""
        raw = {"exchange": "BAD", "mode": "demo", "has_leverage": False}
        assert _parse_order_dispatch_snapshot(raw) is None

    def test_unknown_mode_enum(self) -> None:
        raw = {"exchange": "bybit", "mode": "BAD", "has_leverage": False}
        assert _parse_order_dispatch_snapshot(raw) is None

    def test_string_has_leverage_rejected(self) -> None:
        """codex G.0 P1 #4 — `bool("false") == True` 위험. isinstance(bool) 강제."""
        raw = {"exchange": "bybit", "mode": "demo", "has_leverage": "false"}
        assert _parse_order_dispatch_snapshot(raw) is None

    def test_int_has_leverage_rejected(self) -> None:
        """has_leverage=1 (int) 도 명시 거부 — bool 만 OK."""
        raw = {"exchange": "bybit", "mode": "demo", "has_leverage": 1}
        assert _parse_order_dispatch_snapshot(raw) is None

    def test_non_dict_returns_none(self) -> None:
        assert _parse_order_dispatch_snapshot("not a dict") is None  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# _provider_from_order_snapshot_or_fallback — priority + fallback metric
# ----------------------------------------------------------------------


class TestSnapshotPriority:
    """snapshot 우선 vs account 현재값 conflict 시 snapshot 가 winner.

    codex G.2 P1 #1 (security critical): snapshot vs account 의 (exchange, mode)
    mismatch 는 silent broker bypass 위험 → reject (credentials immutable snapshot
    부재 한 architecturally 안전 정책).
    """

    def test_snapshot_priority_over_order_leverage_mutation(self) -> None:
        """Order.leverage=NULL 로 사후 mutation 되어도 snapshot.has_leverage=True 우선.

        snapshot.exchange/mode 와 account.exchange/mode 는 동일 (drift 없음) —
        leverage 만 mutation 된 case. has_leverage 분기는 snapshot 우선.
        """
        order = _order(
            snapshot={"exchange": "bybit", "mode": "demo", "has_leverage": True},
            leverage=None,  # mutation 시뮬
        )
        account = _account(ExchangeName.bybit, ExchangeMode.demo)
        provider = _provider_from_order_snapshot_or_fallback(order, account, submit=None)
        assert isinstance(provider, BybitFuturesProvider)


class TestSnapshotAccountDriftRejected:
    """codex G.2 P1 #1 (security critical) — snapshot vs current account drift 시 reject.

    snapshot=demo + account=live 시 BybitDemoProvider 선택 + creds=live = silent
    live endpoint 호출 위험. UnsupportedExchangeError raise → graceful rejected
    (creds 까지 immutable snapshot 부재한 한 안전한 정책).
    """

    def test_mode_drift_demo_to_live_rejected(self) -> None:
        """snapshot=demo + account=live → reject."""
        order = _order(
            snapshot={"exchange": "bybit", "mode": "demo", "has_leverage": False},
            leverage=None,
        )
        account_now_live = _account(ExchangeName.bybit, ExchangeMode.live)
        baseline = _fallback_metric_value("drift")
        with pytest.raises(UnsupportedExchangeError) as exc_info:
            _provider_from_order_snapshot_or_fallback(
                order, account_now_live, submit=None
            )
        assert "snapshot" in str(exc_info.value)
        assert _fallback_metric_value("drift") == baseline + 1

    def test_exchange_drift_bybit_to_okx_rejected(self) -> None:
        """snapshot=bybit + account=okx → reject (cross-exchange creds mismatch)."""
        order = _order(
            snapshot={"exchange": "bybit", "mode": "demo", "has_leverage": False},
            leverage=None,
        )
        account_now_okx = _account(ExchangeName.okx, ExchangeMode.demo)
        with pytest.raises(UnsupportedExchangeError) as exc_info:
            _provider_from_order_snapshot_or_fallback(
                order, account_now_okx, submit=None
            )
        assert "snapshot" in str(exc_info.value)

    def test_no_drift_proceeds_normally(self) -> None:
        """snapshot 와 account 가 동일 (정상 case) → drift 검증 통과 + provider 반환."""
        order = _order(
            snapshot={"exchange": "bybit", "mode": "demo", "has_leverage": False},
            leverage=None,
        )
        account = _account(ExchangeName.bybit, ExchangeMode.demo)
        provider = _provider_from_order_snapshot_or_fallback(order, account, submit=None)
        assert isinstance(provider, BybitDemoProvider)


class TestLegacyFallback:
    """snapshot 부재 (legacy row) 또는 invalid → account+leverage fallback + metric."""

    def test_legacy_null_snapshot_falls_back(self) -> None:
        baseline = _fallback_metric_value("missing")
        order = _order(snapshot=None, leverage=None)
        account = _account(ExchangeName.okx, ExchangeMode.demo)
        provider = _provider_from_order_snapshot_or_fallback(order, account, submit=None)
        # account=okx + leverage=None → OkxDemoProvider (fallback)
        assert isinstance(provider, OkxDemoProvider)
        # metric inc(reason=missing)
        assert _fallback_metric_value("missing") == baseline + 1

    def test_invalid_snapshot_falls_back_with_metric(self) -> None:
        """codex G.0 P1 #4 — invalid JSONB → graceful fallback + metric inc(invalid)."""
        baseline = _fallback_metric_value("invalid")
        order = _order(
            snapshot={"exchange": "BAD", "mode": "demo", "has_leverage": False},
            leverage=None,
        )
        account = _account(ExchangeName.bybit, ExchangeMode.demo)
        provider = _provider_from_order_snapshot_or_fallback(order, account, submit=None)
        # invalid → fallback to account=bybit + leverage=None → BybitDemoProvider
        assert isinstance(provider, BybitDemoProvider)
        # metric inc(reason=invalid)
        assert _fallback_metric_value("invalid") == baseline + 1

    def test_fallback_uses_submit_leverage_when_provided(self) -> None:
        """create_order 분기: submit.leverage > 0 → futures fallback."""
        baseline = _fallback_metric_value("missing")
        order = _order(snapshot=None, leverage=None)
        account = _account(ExchangeName.bybit, ExchangeMode.demo)
        submit = OrderSubmit(
            symbol="BTCUSDT",
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=Decimal("0.001"),
            price=None,
            leverage=5,
            margin_mode="cross",
        )
        provider = _provider_from_order_snapshot_or_fallback(order, account, submit=submit)
        # submit.leverage=5 → has_leverage=True → BybitFuturesProvider
        assert isinstance(provider, BybitFuturesProvider)
        assert _fallback_metric_value("missing") == baseline + 1


# ----------------------------------------------------------------------
# Order.dispatch_snapshot 컬럼 자체 sanity (Phase B.1 verifier)
# ----------------------------------------------------------------------


def test_order_dispatch_snapshot_default_none() -> None:
    """SQLModel Order 생성 시 dispatch_snapshot 기본값 None — legacy 호환."""
    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
    )
    assert order.dispatch_snapshot is None


def test_order_dispatch_snapshot_accepts_dict() -> None:
    """dict[str, object] 값 저장 OK."""
    snapshot = {"exchange": "bybit", "mode": "demo", "has_leverage": False}
    order = Order(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
        dispatch_snapshot=snapshot,
    )
    assert order.dispatch_snapshot == snapshot
