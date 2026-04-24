"""Prometheus metrics — Sprint 9 Phase D.

5종 metrics:
- qb_backtest_duration_seconds    (Histogram)
- qb_order_rejected_total         (Counter, labels: exchange, reason)
- qb_kill_switch_triggered_total  (Counter, labels: trigger_type)
- qb_ccxt_request_duration_seconds (Histogram, labels: exchange, endpoint)
- qb_active_orders                (Gauge)

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


@asynccontextmanager
async def ccxt_timer(exchange: str, endpoint: str) -> AsyncIterator[None]:
    """CCXT 호출을 감싸 latency histogram 에 기록.

    사용:
        async with ccxt_timer("bybit", "create_order"):
            await exchange.create_order(...)

    예외 경로에서도 finally 블록으로 항상 observe — 실패한 요청도 latency 에 포함.
    """
    started = time.monotonic()
    try:
        yield
    finally:
        qb_ccxt_request_duration_seconds.labels(exchange=exchange, endpoint=endpoint).observe(
            time.monotonic() - started
        )
