"""Prometheus metrics — Sprint 9 Phase D / Sprint 10 Phase A2 + D.

8종 metrics:
- qb_backtest_duration_seconds    (Histogram)
- qb_order_rejected_total         (Counter, labels: exchange, reason)
- qb_kill_switch_triggered_total  (Counter, labels: trigger_type)
- qb_ccxt_request_duration_seconds (Histogram, labels: exchange, endpoint)
- qb_active_orders                (Gauge)
- qb_rate_limit_throttled_total   (Counter, labels: scope, endpoint)  ← Sprint 10 Phase B
- qb_ccxt_request_errors_total    (Counter, labels: exchange, endpoint, error_class)  ← Sprint 10 Phase D
- qb_redlock_acquire_total        (Counter, labels: outcome)  ← Sprint 10 Phase A2
- qb_redis_lock_pool_healthy      (Gauge)  ← Sprint 10 Phase A2

원칙:
- registry 는 기본 `REGISTRY` (single-process). Sprint 10+ 에서 multi-process 고려.
- label cardinality 낮게 유지 — exchange 는 enum 2~4개, reason/trigger_type 도 enum.
- 민감 정보 label 금지 (user_id, strategy_id, api_key, account_id).
- prometheus_client 는 fork-safe 하므로 Celery worker 가 동일 counter/gauge 참조 가능.

`ccxt_timer` context manager 는 Bybit/OKX provider 에서 CCXT 호출을 감싸는 데 사용.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from prometheus_client import Counter, Gauge, Histogram

# 1. Backtest 실행 시간 (queued → terminal state)
qb_backtest_duration_seconds = Histogram(
    "qb_backtest_duration_seconds",
    "Backtest worker execution time from queued to terminal state",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, float("inf")),
)

# 2. 주문 거부 카운터 (leverage_cap / notional / session_closed / idempotency_conflict / kill_switch)
qb_order_rejected_total = Counter(
    "qb_order_rejected_total",
    "Orders rejected before or at exchange",
    labelnames=("exchange", "reason"),
)

# 3. Kill Switch 발동 (cumulative_loss / daily_loss / api_error)
qb_kill_switch_triggered_total = Counter(
    "qb_kill_switch_triggered_total",
    "Kill Switch activations",
    labelnames=("trigger_type",),
)

# 4. CCXT exchange API latency
qb_ccxt_request_duration_seconds = Histogram(
    "qb_ccxt_request_duration_seconds",
    "CCXT exchange API request latency",
    labelnames=("exchange", "endpoint"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, float("inf")),
)

# 5. Active orders (pending + submitted). Eventually consistent (Phase 1 OK).
qb_active_orders = Gauge(
    "qb_active_orders",
    "Current pending + submitted order count (eventually consistent)",
)

# 6. Rate limit throttled (Sprint 10 Phase B)
qb_rate_limit_throttled_total = Counter(
    "qb_rate_limit_throttled_total",
    "Rate limit 초과로 429 응답한 횟수",
    labelnames=("scope", "endpoint"),
)

# 7. CCXT exchange API errors (Sprint 10 Phase D + Sprint 11 Phase G allowlist)
# `ccxt_timer` 의 except 분기에서 inc. `error_class = _normalize_error_class(exc)`.
# 정상 경로에서는 inc 되지 않음. `qb_ccxt_request_duration_seconds` 와 상관관계로
# rate(errors[5m]) / rate(duration_count[5m]) 가 error rate alert 의 기준.
#
# Cardinality 실측 (2026-04-25, Sprint 11 Phase G):
# - exchange ∈ {bybit, bybit_futures, okx, ...} ≤ 4
# - endpoint ∈ {create_order, cancel_order, fetch_balance, fetch_ohlcv, fetch_ticker, ...} ≤ 10
# - error_class: allowlist 28 (ccxt 공식) + 5 (built-in) + "Other" = 34.
# 총 4 x 10 x 34 ≈ 1,360 series (Grafana Cloud Free 10k 한도 내).
# 동적 커스텀 예외는 "Other" 버킷으로 수렴 → cardinality leak 차단.
qb_ccxt_request_errors_total = Counter(
    "qb_ccxt_request_errors_total",
    "CCXT exchange API errors — raise 직전 inc, exchange/endpoint/error_class 로 라벨링 (allowlist)",
    labelnames=("exchange", "endpoint", "error_class"),
)


# Sprint 11 Phase G — error_class allowlist. 외부에서 동적 custom Exception 이
# 주입돼도 Prometheus cardinality 가 폭발하지 않도록 "Other" 버킷으로 수렴.
_CCXT_ERROR_CLASSES: frozenset[str] = frozenset(
    {
        # ccxt.base.errors (2026-04 기준)
        "BaseError",
        "ExchangeError",
        "NetworkError",
        "DDoSProtection",
        "RequestTimeout",
        "AuthenticationError",
        "PermissionDenied",
        "AccountNotEnabled",
        "AccountSuspended",
        "ArgumentsRequired",
        "BadRequest",
        "BadSymbol",
        "BadResponse",
        "NullResponse",
        "InsufficientFunds",
        "InvalidAddress",
        "InvalidOrder",
        "OrderNotFound",
        "OrderNotCached",
        "CancelPending",
        "OrderImmediatelyFillable",
        "OrderNotFillable",
        "DuplicateOrderId",
        "NotSupported",
        "OnMaintenance",
        "InvalidNonce",
        "RateLimitExceeded",
        "ExchangeNotAvailable",
    }
)
_BUILTIN_ERROR_CLASSES: frozenset[str] = frozenset(
    {
        "TimeoutError",
        "ConnectionError",
        "OSError",
        "RuntimeError",
        "ValueError",
    }
)
_ALLOWLIST_ERROR_CLASSES: frozenset[str] = _CCXT_ERROR_CLASSES | _BUILTIN_ERROR_CLASSES


def _normalize_error_class(exc: BaseException) -> str:
    """Prometheus cardinality 보호 — allowlist 에 없는 예외는 "Other" 버킷."""
    name = type(exc).__name__
    return name if name in _ALLOWLIST_ERROR_CLASSES else "Other"


# 8. Redis distributed lock acquire outcomes (Sprint 10 Phase A2)
# outcome ∈ {success, contention, unavailable, timeout}
# - success:     SET NX 성공 (분산 lock 획득)
# - contention:  SET NX 실패 (다른 워커가 이미 보유)
# - unavailable: Redis 연결 장애 (socket timeout, ConnectionError)
# - timeout:     asyncio.wait_for timeout (reserved — 본 Phase 미구현)
qb_redlock_acquire_total = Counter(
    "qb_redlock_acquire_total",
    "Redis distributed lock acquire 시도 결과",
    labelnames=("outcome",),
)

# 9. Redis lock pool healthy (Sprint 10 Phase A2) — lifespan healthcheck 결과
# 1: PING+SET+GET+DEL 정상, 0: 장애. startup 에서 1회 세팅.
qb_redis_lock_pool_healthy = Gauge(
    "qb_redis_lock_pool_healthy",
    "1 if startup PING+SET+GET+DEL succeeded, 0 otherwise",
)


@asynccontextmanager
async def ccxt_timer(exchange: str, endpoint: str) -> AsyncIterator[None]:
    """CCXT 호출을 감싸 latency + error 를 관측.

    사용:
        async with ccxt_timer("bybit", "create_order"):
            await exchange.create_order(...)

    - latency: 정상/예외 관계없이 finally 블록에서 duration histogram 에 observe.
    - error:   except 블록에서 `qb_ccxt_request_errors_total` counter 를
               `(exchange, endpoint, _normalize_error_class(exc))` 라벨로 +1 후 `raise`.
               원 예외는 변형 없이 전파. allowlist 외 예외는 "Other" 버킷으로 수렴
               (Sprint 11 Phase G cardinality 보호).
    """
    started = time.monotonic()
    try:
        yield
    except Exception as exc:
        # 거래소 API 오류 계측 — BaseException (CancelledError, KeyboardInterrupt 등) 제외
        qb_ccxt_request_errors_total.labels(
            exchange=exchange,
            endpoint=endpoint,
            error_class=_normalize_error_class(exc),
        ).inc()
        raise
    finally:
        qb_ccxt_request_duration_seconds.labels(exchange=exchange, endpoint=endpoint).observe(
            time.monotonic() - started
        )
