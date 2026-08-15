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


class LiveSignalSessionNotFound(AppException):
    """Raised when LiveSignalSession lookup fails. session_id is required."""

    status_code = 404
    code = "live_signal_session_not_found"

    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"LiveSignalSession not found: {session_id}")
        self.session_id = session_id


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


class TrailingContractError(ProviderError):
    """재시도해도 안 고쳐지는 money-path 계약 위반 — 즉시 alert + give up(non-retryable).

    예: 미검증 ccxt 버전(라우팅 계약 불확실) / tick 정규화 후 distance<=0 / hedge-mode.
    reason = alert 에 실을 안전한 분류 문자열(원본 예외 텍스트 누설 금지).
    """

    code = "trailing_contract_error"

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        super().__init__(detail)


class UnsupportedExchangeError(ProviderError):
    """dispatch 시점 (exchange, mode, has_leverage) tuple 미지원 — Sprint 22 BL-091.

    ProviderError 상속 = `tasks/trading.py:_execute_with_session` 의 `except ProviderError`
    가 자동 catch → Order graceful `rejected` 전이 + `qb_active_orders.dec()` (winner-only).
    fetch 분기 (`_fetch_order_status_with_session`) 도 동일 패턴.
    """

    status_code = 502
    code = "unsupported_exchange"

    def __init__(self, key: tuple[object, ...]) -> None:
        super().__init__(f"Unsupported (exchange, mode, has_leverage): {key}")
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
            f"current UTC hour {current_hour_utc} is outside allowed trading_sessions={sessions}"
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
            f"leverage={requested} exceeds configured cap bybit_futures_max_leverage={cap}"
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


class ReadOnlyAccountNotAllowed(AppException):
    """읽기 전용 API 키는 라이브 세션의 주문 경로를 열 수 없다."""

    status_code = 422
    code = "read_only_account_not_allowed"

    def __init__(self) -> None:
        super().__init__("읽기 전용 API 키로는 라이브 세션을 시작할 수 없습니다.")


class LiveSessionQuotaExceeded(AppException):
    """Sprint 26 — 사용자별 active Live Session ≤ 5 (codex G.0 P3 #3 + plan §3 A.5)."""

    status_code = 422
    code = "live_session_quota_exceeded"

    def __init__(self, *, current: int, cap: int) -> None:
        super().__init__(
            f"active Live Session count {current} >= cap {cap}. 기존 session deactivate 후 재시도."
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


class AlertRuleAlreadyActive(AppException):
    """같은 세션·타입의 활성 알림 규칙이 이미 존재."""

    status_code = 409
    code = "alert_rule_already_active"


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


class DemoAccountNotYetStable(AppException):
    """Wave 0 W4 — 라이브 전환 전 데모 안정화 기간 미충족.

    user.created_at 기준 경과일이 _MIN_DEMO_STABLE_DAYS 미만일 때 라이브 경로에서 raise.
    기존 error toast 가 표면화 — FE 무수정. demo 세션 생성에는 영향 없음.
    """

    status_code = 422
    code = "demo_account_not_yet_stable"

    def __init__(self, *, days_elapsed: int, min_required: int) -> None:
        super().__init__(
            f"데모 안정화 기간 미충족: {days_elapsed}일 경과 < 필요 {min_required}일. "
            "라이브 전환은 데모 안정화 후 가능."
        )
        self.days_elapsed = days_elapsed
        self.min_required = min_required


class SizingBaselineUnavailable(AppException):
    """BL-479 — 세션 시작 시 자본 기준선 스냅샷 실패. 사이징 없이 발주하느니 세션을 안 연다.

    BL-478 (a) 와 무관하다. 조건부 주문 등재가 구현돼도 이 게이트는 남는다 —
    자본 기준선이 없으면 `compute_qty()` 가 1.0 을 돌려주고 1 BTC 명목이 나간다.
    """

    status_code = 422
    code = "sizing_baseline_unavailable"

    def __init__(self, *, account_id: UUID, reason: str | None = None) -> None:
        super().__init__(
            "세션 시작 시점의 거래소 잔고를 읽지 못했습니다. 잔고를 모르면 주문 수량을 계산할 수 "
            "없어서 세션을 시작하지 않습니다. 거래소 계정의 API 키 상태를 확인한 뒤 다시 "
            "시도해주세요."
        )
        self.account_id = account_id
        self.reason = reason


class AccountNotExclusive(AppException):
    """[BL-634] — 그 거래소 계정에 **이 원장이 모르는 미체결 조건부 주문**이 걸려 있다.

    2026-08-08 부검(BL-633)이 확정한 사망 원인은 같은 Bybit demo 계정에 두 호스트가
    동시에 붙은 것이었다. 호스트가 둘이면 **데이터베이스도 둘**이라
    `uq_live_sessions_active_unique`(`models.py:471-487`, partial `is_active=true`)는
    원리상 못 막는다 — 각 DB 안에서 제약은 정상 성립했고 **둘을 합친 상태를 아는 주체가
    없었다**. 그래서 가드는 DB 가 아니라 **거래소 쪽 상태**를 본다.
    """

    status_code = 409
    code = "account_not_exclusive"

    def __init__(self, *, account_id: UUID, symbol: str, foreign: list[str]) -> None:
        super().__init__(
            f"거래소 계정에 이 원장이 발행하지 않은 미체결 조건부 주문이 {len(foreign)}건 "
            f"있습니다 ({symbol}). 같은 계정에 다른 호스트가 붙어 있을 수 있어 세션을 "
            "시작하지 않습니다. 해당 주문을 취소하거나 다른 호스트를 정지한 뒤 다시 "
            "시도해주세요."
        )
        self.account_id = account_id
        self.symbol = symbol
        self.foreign = foreign


class BalanceUnverified(AppException):
    """CF5 — live 모드에서 잔고 검증 불가 (fetch 실패/0) → 주문 거부 (fail-closed).

    demo 는 서비스 중단 방지 위해 fail-open(skip) 유지. live 는 잔고 미확인 상태로
    주문을 통과시키면 notional 리스크 가드가 무력화되므로 보수적으로 거부.
    """

    status_code = 422
    code = "balance_unverified"

    def __init__(self, *, account_id: UUID) -> None:
        super().__init__(
            f"live 주문 잔고 검증 불가 (balance fetch 실패/0): account={account_id}. "
            "잠시 후 재시도."
        )
        self.account_id = account_id


class AccountOwnershipMismatch(AppException):
    """주문의 exchange_account 가 strategy 소유자와 다른 사용자 소유 — TRD-4 IDOR 차단.

    webhook 경로는 strategy HMAC 으로만 인증되므로 current_user 가 없다. 따라서
    `ExchangeAccount.user_id == Strategy.user_id` 불변식을 서비스 계층에서 강제하여
    공격자가 타 tenant 계좌로 주문하는 것을 막는다.
    """

    status_code = 403
    code = "account_ownership_mismatch"


class OwnerAccountInactive(AppException):
    """전략 소유자의 계정이 비활성(탈퇴) — 2026-08-15 surface-truth (S3) 심층 방어.

    탈퇴 처리(`UserService` 의 `user.deleted` 분기)가 세션 전량 비활성 + 웹훅 시크릿 전량
    revoke 로 **원천**을 닫는다. 이 게이트는 그 뒤에 서는 두 번째 문이다 — 유출된 시크릿의
    grace 창, 이미 큐에 들어간 tick, 수기 주문 경로처럼 원천 차단이 한 박자 늦는 자리에서
    **돈이 나가는 마지막 순간**에 다시 묻는다.

    TRD-4(`AccountOwnershipMismatch`) 와 같은 자리에 두되 사유를 분리한다 — 「남의 계좌」와
    「없어진 사람의 계좌」는 운영자가 봐야 할 것이 다르다.
    """

    status_code = 403
    code = "owner_account_inactive"


class MinNotionalNotMet(AppException):
    """position notional(qty x price)이 거래소 최소 주문 cost 미달 (C5).

    Wave 1 — markets[symbol]['limits']['cost']['min'] (load_markets 메타) 기준.
    미달 주문은 거래소가 거부하므로 사전 차단해 불필요한 round-trip / 실패 주문을 막는다.
    min cost 미가용(None) 시 가드 skip (fail-open) — 서비스 중단 금지(demo 정책 일관).
    """

    status_code = 422
    code = "min_notional_not_met"

    def __init__(self, *, notional: Decimal, min_notional: Decimal) -> None:
        super().__init__(f"position notional {notional} is below exchange minimum {min_notional}")
        self.notional = notional
        self.min_notional = min_notional


class RiskSizingExceeded(AppException):
    """client 제출 qty 가 서버 권위 risk-기반 max_qty 를 초과 (Wave 2 P2).

    서버 권위 사이징: max_qty = 자본(USDT 잔고) x risk_percent% / |entry - stop|.
    client qty 를 신뢰하지 않고 거래소 잔고 + 전략 stop 거리로 재계산해, 한 트레이드의
    손실이 자본의 risk_percent% 를 넘지 않도록 강제한다. risk_percent 미설정 시 가드 skip
    (회귀 0). stop / 잔고 / entry 미가용 시 skip(fail-open, demo 정책 일관).
    """

    status_code = 422
    code = "risk_sizing_exceeded"

    def __init__(
        self,
        *,
        quantity: Decimal,
        max_quantity: Decimal,
        risk_percent: Decimal,
        stop_distance: Decimal,
    ) -> None:
        super().__init__(
            f"quantity {quantity} exceeds risk-based max {max_quantity} "
            f"(risk={risk_percent}%, stop_distance={stop_distance})"
        )
        self.quantity = quantity
        self.max_quantity = max_quantity
        self.risk_percent = risk_percent
        self.stop_distance = stop_distance


class NotionalExceeded(AppException):
    """position notional(qty x price)이 available x leverage x 0.95 초과 (CF5/MP-3).

    Bybit/Binance initial-margin 모델: 필요 증거금 = notional/leverage 가 가용 잔고의
    95%(open/close fee 버퍼) 이내여야 한다. leverage cap이 비율 상한만 보는 반면, 본
    가드는 포지션 규모가 잔고로 감당 가능한지 금액 단위로 검증한다.
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
