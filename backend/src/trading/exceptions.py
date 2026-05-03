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


class UnsupportedExchangeError(ProviderError):
    """dispatch 시점 (exchange, mode, has_leverage) tuple 미지원 — Sprint 22 BL-091.

    ProviderError 상속 = `tasks/trading.py:_execute_with_session` 의 `except ProviderError`
    가 자동 catch → Order graceful `rejected` 전이 + `qb_active_orders.dec()` (winner-only).
    fetch 분기 (`_fetch_order_status_with_session`) 도 동일 패턴.
    """

    status_code = 502
    code = "unsupported_exchange"

    def __init__(self, key: tuple[object, ...]) -> None:
        super().__init__(
            f"Unsupported (exchange, mode, has_leverage): {key}"
        )
        self.key = key


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


class AccountModeNotAllowed(AppException):
    """Sprint 26 — Live Session 은 Bybit Demo 한정 (BL-003 mainnet runbook 완료 전까지).

    account.exchange != ExchangeName.bybit OR account.mode != ExchangeMode.demo 시 raise.
    """

    status_code = 422
    code = "account_mode_not_allowed"

    def __init__(self, *, exchange: object, mode: object) -> None:
        super().__init__(
            f"Live Session 은 Bybit Demo 한정 (BL-003 mainnet runbook 완료 전까지). "
            f"received: exchange={exchange}, mode={mode}"
        )
        self.exchange = exchange
        self.mode = mode


class LiveSessionQuotaExceeded(AppException):
    """Sprint 26 — 사용자별 active Live Session ≤ 5 (codex G.0 P3 #3 + plan §3 A.5)."""

    status_code = 422
    code = "live_session_quota_exceeded"

    def __init__(self, *, current: int, cap: int) -> None:
        super().__init__(
            f"active Live Session count {current} >= cap {cap}. "
            "기존 session deactivate 후 재시도."
        )
        self.current = current
        self.cap = cap


class SessionAlreadyActive(AppException):
    """Sprint 26 — partial unique index 위반.

    같은 (user_id, strategy_id, exchange_account_id, symbol) 조합의 active session 이
    이미 존재. deactivate 후 재INSERT 가능 (partial unique 가 is_active=true 만 cover).
    """

    status_code = 409
    code = "session_already_active"


class StrategySettingsRequired(AppException):
    """Sprint 26 — strategy.settings is None.

    Live Session 시작 시 leverage / margin_mode / position_size_pct 가 사전 설정되어
    있어야. PUT /api/v1/strategies/{id}/settings 로 설정 후 재시도.
    """

    status_code = 422
    code = "strategy_settings_required"


class InvalidStrategySettings(AppException):
    """Sprint 26 — strategy.settings JSONB malformed (codex G.0 P2 #4).

    StrategySettings.model_validate 실패 — DB 직접 수정 또는 schema migration 누락.
    PUT /api/v1/strategies/{id}/settings 로 재설정.
    """

    status_code = 422
    code = "invalid_strategy_settings"

    def __init__(self, *, error: str) -> None:
        super().__init__(f"invalid strategy.settings JSONB: {error}")
        self.error = error


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
