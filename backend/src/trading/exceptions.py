"""trading 도메인 예외. src.common.exceptions.AppException 상속."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from src.common.exceptions import AppException


class EncryptionError(AppException):
    """AES-256 Fernet 복호화 실패."""

    status_code = 500
    code = "encryption_error"


class AccountNotFound(AppException):
    """Raised when ExchangeAccount lookup fails. account_id is required."""

    status_code = 404
    code = "account_not_found"

    def __init__(self, account_id: UUID) -> None:
        super().__init__(f"ExchangeAccount not found: {account_id}")
        self.account_id = account_id


class KillSwitchActive(AppException):
    """Kill Switch 이벤트 활성 — 주문 차단."""

    status_code = 409
    code = "kill_switch_active"


class WebhookUnauthorized(AppException):
    status_code = 401
    code = "webhook_unauthorized"


class IdempotencyConflict(AppException):
    """동일 idempotency_key로 이미 다른 payload의 주문 존재 — autoplan E2.

    original_order_id: 기존 주문의 UUID (T17 router가 409 응답에 포함).
    """

    status_code = 409
    code = "idempotency_conflict"

    def __init__(self, message: str, *, original_order_id: UUID | None = None) -> None:
        super().__init__(message)
        self.original_order_id = original_order_id


class OrderNotFound(AppException):
    """Raised when Order lookup fails. order_id is required."""

    status_code = 404
    code = "order_not_found"

    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Order not found: {order_id}")
        self.order_id = order_id


class ProviderError(AppException):
    """ExchangeProvider 호출 실패 (CCXT 예외 래핑)."""

    status_code = 502
    code = "provider_error"


class TradingSessionClosed(AppException):
    """요청 시점이 전략의 허용 trading_sessions 밖. Sprint 7d.

    strategy.trading_sessions가 비어있지 않고 현재 UTC hour가 어느 세션에도
    속하지 않을 때 OrderService.execute가 raise.
    """

    status_code = 422
    code = "trading_session_closed"

    def __init__(self, *, sessions: list[str], current_hour_utc: int) -> None:
        super().__init__(
            f"current UTC hour {current_hour_utc} is outside allowed "
            f"trading_sessions={sessions}"
        )
        self.sessions = sessions
        self.current_hour_utc = current_hour_utc


class LeverageCapExceeded(AppException):
    """OrderRequest.leverage가 settings.bybit_futures_max_leverage 상한 초과.

    Sprint 7a: OrderRequest의 정적 `le=125` (Bybit 이론 상한)과 별개로, 운영
    리스크 관리용 동적 cap을 서비스 계층에서 enforce. 4/4 리뷰 컨센서스.
    """

    status_code = 422
    code = "leverage_cap_exceeded"

    def __init__(self, requested: int, cap: int) -> None:
        super().__init__(
            f"leverage={requested} exceeds configured cap "
            f"bybit_futures_max_leverage={cap}"
        )
        self.requested = requested
        self.cap = cap


class NotionalExceeded(AppException):
    """주문 notional(qty x price x leverage)이 계좌 자본 x max_leverage x safety 초과.

    Sprint 8+ Kill Switch capital_base 동적 바인딩과 함께 도입. leverage cap이 비율
    상한만 보는 반면, 본 가드는 실제 포지션 규모가 잔고 대비 과도한지 금액 단위로 검증.
    safety factor 0.95로 청산 여유 확보.
    """

    status_code = 422
    code = "notional_exceeded"

    def __init__(
        self,
        *,
        notional: Decimal,
        available: Decimal,
        leverage: int,
        max_notional: Decimal,
    ) -> None:
        super().__init__(
            f"notional {notional} exceeds max {max_notional} "
            f"(available={available}, leverage={leverage}x)"
        )
        self.notional = notional
        self.available = available
        self.leverage = leverage
        self.max_notional = max_notional
