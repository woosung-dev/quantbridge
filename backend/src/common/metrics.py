"""Prometheus metrics — Sprint 9 Phase D / Sprint 10 Phase A2 + D.

8종 metrics:
- qb_backtest_duration_seconds    (Histogram)
- qb_order_rejected_total         (Counter, labels: exchange, reason)
- qb_kill_switch_triggered_total  (Counter, labels: trigger_type)
- qb_ccxt_request_duration_seconds (Histogram, labels: exchange, endpoint)
- qb_active_orders                (Gauge)
- qb_rate_limit_throttled_total   (Counter, labels: scope, endpoint)  ← Sprint 10 Phase B
- qb_ccxt_request_errors_total    (Counter, labels: exchange, endpoint, error_class)  ← Sprint 10 Phase D
- qb_order_snapshot_fallback_total (Counter, labels: reason)  ← Sprint 23 BL-102
- qb_redlock_acquire_total        (Counter, labels: outcome)  ← Sprint 10 Phase A2
- qb_redis_lock_pool_healthy      (Gauge)  ← Sprint 10 Phase A2
- qb_live_signal_evaluated_total  (Counter, labels: interval, outcome)  ← Sprint 26 B.4
- qb_live_signal_dispatch_total   (Counter, labels: action, outcome)    ← Sprint 26 B.4
- qb_live_signal_skipped_total    (Counter, labels: reason)             ← Sprint 26 B.4
- qb_live_signal_entry_skipped_total (Counter, labels: reason)          ← BL-483
- qb_live_signal_liquidation_total (Counter, labels: direction)         ← BL-483
- qb_live_signal_eval_duration_seconds (Histogram, labels: interval)    ← Sprint 26 B.4
- qb_live_signal_outbox_pending_gauge  (Gauge)                          ← Sprint 26 B.4
- qb_closed_pnl_backfill_total       (Counter, labels: outcome)         ← MP-2
- qb_partial_fill_total              (Counter, labels: source, kind)    ← Sprint 48 Pass 2
- qb_exchange_order_response_total  (Counter, labels: exchange, outcome, reason) ← BL-512
- qb_live_conditional_guard_total   (Counter, labels: outcome)          ← BL-512
- qb_live_conditional_reversal_total (Counter, labels: bucket)          ← BL-516
- qb_live_conditional_reversal_filled_total (Counter, labels: bucket)   ← BL-562

원칙:
- `PROMETHEUS_MULTIPROC_DIR` 설정 시 shared multiprocess registry, 미설정 시 기본 `REGISTRY`.
- label cardinality 낮게 유지 — exchange 는 enum 2~4개, reason/trigger_type 도 enum.
- 민감 정보 label 금지 (user_id, strategy_id, api_key, account_id).
- Celery worker 값은 process별 mmap 파일에 기록하고 API가 `MultiProcessCollector`로 수집.

BL-512 label cardinality:
- qb_exchange_order_response_total: exchange ∈ {bybit, binance, okx, unknown} ≤ 4,
  outcome ∈ {accepted, rejected, unknown} = 3, reason ∈ {trigger_breached,
  reduce_only_same_side, reduce_only_position_zero, reduce_only_violation,
  position_zero, insufficient_balance, auth_failed, permission_denied, rate_limited,
  other, unparsed, rejected_at_submission, filled, submitted} = 14.
  최대 4 x 3 x 14 = 168 series.
- qb_live_conditional_guard_total: outcome ∈ {conditional_placed, market_converted,
  breach_capped, breach_with_resting, reference_unavailable, convert_suppressed,
  breach_reverted, bracket_attached, bracket_unavailable, bracket_supplied_gate_dropped,
  bracket_tp_dropped_size, bracket_trailing_only_dropped, recovery_placed,
  recovery_reverted, recovery_suppressed, recovery_expired} = 16. 최대 16 series.

`ccxt_timer` context manager 는 Bybit/OKX provider 에서 CCXT 호출을 감싸는 데 사용.
"""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from src.common.metrics_multiproc import configure_multiprocess, record_metric_safely

configure_multiprocess()


_LIVE_CONDITIONAL_GUARD_OUTCOMES: frozenset[str] = frozenset(
    {
        "conditional_placed",
        "market_converted",
        "breach_capped",
        "breach_with_resting",
        "reference_unavailable",
        "convert_suppressed",
        "breach_reverted",
        # 거래소가 돌파를 판정해 조건부 주문을 거절한 뒤의 복구 태스크 결과.
        # `recovery_placed`는 거래소 수락이 아니라 시장가 복구 발주를 요청한 결과다.
        # 신규 원장 등재일 수도 있고, 같은 key의 기존 요청에 합류한 캐시 응답일 수도 있다.
        "recovery_placed",
        "recovery_reverted",
        "recovery_suppressed",
        "recovery_expired",
        # BL-523 — 조건부 진입에 브래킷을 실을 수 있었는가. ★`bracket_unavailable` 이
        # 이 5종의 존재 이유다. 조건부 진입은 체결 전까지 `open_trades` 에 없고
        # `place_exit` 는 `open_trades` 만 타깃하므로(`strategy_state.py:963`)
        # `exit_levels_for` 가 항상 `(None, None, None)` 을 준다 — 즉 배관을 깔아도
        # 실을 것이 없다. 그 "없음" 을 추측이 아니라 관측으로 만드는 것이 이 라벨이다.
        #
        # ★BL-563 — 이 3종은 **엔진이 공급한 원본 leg 기준**이고 상호배타다. 합은
        #   `qb_live_conditional_placed_total`(등재 성공 수)과 같다.
        #     bracket_attached             — 공급됐고 주문에도 실려 나갔다.
        #     bracket_supplied_gate_dropped — 공급됐는데 게이트가 전부 드롭했다.
        #     bracket_unavailable          — **엔진이 아예 공급하지 않았다**.
        #   판정을 게이트 **뒤**의 `OrderRequest` 로 하면 TP-only 반전(게이트 B 가 TP 를
        #   드롭 + SL/trailing 없음)이 "엔진이 공급 안 함" 으로 섞여 BL-523 의 판정
        #   근거를 오염시킨다. 그래서 세 번째 라벨이 있다.
        "bracket_attached",
        "bracket_unavailable",
        "bracket_supplied_gate_dropped",
        # TP 만 드롭(SL 유지). `_merge_exit_params` 가 `tpSize = 주문수량` 을 넣는데
        # 반전이면 주문수량 > 체결 후 포지션이라 거래소가 진입 자체를 거부한다.
        "bracket_tp_dropped_size",
        # 고정 SL 없는 트레일링 단독 = 체결되면 무방비 포지션. leg 를 등재하지 않는다.
        "bracket_trailing_only_dropped",
    }
)


class _GuardOutcomeCounter(Counter):
    """고정 outcome 외 라벨 생성으로 인한 cardinality 증가를 차단한다."""

    def labels(self, *labelvalues: Any, **labelkwargs: Any) -> _GuardOutcomeCounter:
        outcome = labelkwargs.get("outcome") if labelkwargs else labelvalues[0]
        if outcome not in _LIVE_CONDITIONAL_GUARD_OUTCOMES:
            raise ValueError(f"Unsupported live conditional guard outcome: {outcome}")
        return super().labels(*labelvalues, **labelkwargs)


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
    multiprocess_mode="sum",
)

qb_metrics_render_fallback_total = Counter(
    "qb_metrics_render_fallback_total",
    "Metrics renders that fell back to the single-process registry",
)

qb_metrics_mutation_failed_total = Counter(
    "qb_metrics_mutation_failed_total",
    "Metric mutations that failed without affecting business operations",
)

# 6. Rate limit throttled (Sprint 10 Phase B)
qb_rate_limit_throttled_total = Counter(
    "qb_rate_limit_throttled_total",
    "Rate limit 초과로 429 응답한 횟수",
    labelnames=("scope", "endpoint"),
)

# Sprint 24 BL-013 — WebSocket auth/network circuit breaker (codex G.0 P1 #3).
# `BybitAuthError` 즉시 block (block_auth) / network 3회 누적 block (block_network) /
# network 1-2회 발생 (network_failure) / 수동 해제 (restored) / Open 중 skip (skipped).
# Cardinality: outcome ∈ {block_auth, block_network, network_failure, restored, skipped} = 5.
qb_ws_auth_circuit_total = Counter(
    "qb_ws_auth_circuit_total",
    "WS auth/network circuit breaker 이벤트 (BL-013) — outcome 별 카운트",
    labelnames=("outcome",),
)

# Sprint 23 BL-102 — Order.dispatch_snapshot fallback (codex G.0 P1 #4 + G.0 P2 #1).
# snapshot 이 NULL (legacy row Sprint 23 이전 생성) 또는 invalid (DB manual mutation
# 으로 unknown enum / non-bool / missing key) 일 때 inc. 정상 경로 (snapshot 정확)
# 에서는 inc 안 됨. Sprint 24+ 잔존 legacy row tracking + invalid snapshot 발견.
# Cardinality: reason ∈ {missing, invalid} = 2 series. 안전.
qb_order_snapshot_fallback_total = Counter(
    "qb_order_snapshot_fallback_total",
    "Order.dispatch_snapshot 부재/invalid 시 legacy account+leverage fallback 호출",
    labelnames=("reason",),
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


# BL-512 — ProviderError 원문에서 retCode 숫자를 읽는다.
# ★**어떤 사유인지의 판정 근거는 `retCode` 뿐이다.** retMsg 는 실응답에서 깨진 구분자를
#   포함하므로 코드 판정에 절대 쓰지 않는다(BL-512 원 제약, 그대로 유효).
#   아래 110017 분기만 예외인데, 그것도 **코드를 정한 뒤 그 안에서 갈래만** 가르는 용도다
#   - 이미 110017 로 확정된 뒤라 구분자가 깨져도 다른 사유로 새지 않는다.
_BYBIT_RETCODE_PATTERN = re.compile(r'"retCode"\s*:\s*(\d+)')
_EXCHANGE_ORDER_RESPONSE_REASONS: dict[str, str] = {
    "110092": "trigger_breached",
    "110093": "trigger_breached",
    "110034": "position_zero",
    "110004": "insufficient_balance",
    "110006": "insufficient_balance",
    "110007": "insufficient_balance",
    "110012": "insufficient_balance",
    "110044": "insufficient_balance",
    "110045": "insufficient_balance",
    "110051": "insufficient_balance",
    "110052": "insufficient_balance",
    "110053": "insufficient_balance",
    "10003": "auth_failed",
    "10004": "auth_failed",
    "10005": "permission_denied",
    "10010": "permission_denied",
    "10020": "permission_denied",
    "10027": "permission_denied",
    "10028": "permission_denied",
    "10006": "rate_limited",
    "10018": "rate_limited",
}


def _normalize_exchange_order_response_reason(message: str) -> str:
    """Bybit retCode allowlist 외 응답을 저카디널리티 reason 으로 정규화한다."""
    match = _BYBIT_RETCODE_PATTERN.search(message)
    if match is None:
        return "unparsed"

    retcode = match.group(1)
    if retcode == "110017":
        # 정본 문서 두 곳이 코드로만 묶지 말라고 했는데 110017을 하나로 묶고 있었다.
        # retMsg까지 분리해 무해한 포지션 0과 위험한 반대 방향을 각각 계측한다.
        normalized_message = re.sub(r"\s+", " ", message).casefold()
        if "same side" in normalized_message:
            return "reduce_only_same_side"
        if "current position is zero" in normalized_message:
            return "reduce_only_position_zero"
        return "reduce_only_violation"

    return _EXCHANGE_ORDER_RESPONSE_REASONS.get(retcode, "other")


qb_exchange_order_response_total = Counter(
    "qb_exchange_order_response_total",
    "거래소 주문 제출 응답 또는 응답 미확인 결과",
    labelnames=("exchange", "outcome", "reason"),
)


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
    multiprocess_mode="mostrecent",
)

# --- Sprint 12 Phase C: Bybit Private WebSocket ---
# 10. 도착 축 — WS order event 가 왔는데 대응하는 local Order row 가 없다.
qb_ws_orphan_event_total = Counter(
    "qb_ws_orphan_event_total",
    "WS order events arrived before local DB row exists (REST/WS race)",
    labelnames=("account_id",),
)

# 11. 폐기 축 — 그 고아 이벤트를 실제로 버린 것 (BL-448).
#
# ★도착 축과 왜 둘인가. 종전에는 도착 카운터 하나뿐이라 **무엇을 잃었는지** 알 수 없었다.
#   `reason` 이 그 축이다 — `terminal_event_lost` 는 머니-패스 손실(reconciler 가 회수해야
#   하는 대상)이고 `non_terminal_ignored` 는 로컬 행이 있었어도 skip 했을 무해한 값이다.
#   ★종전의 `qb_ws_orphan_buffer_size` gauge 는 여기서 사라졌다 — 그 버퍼를 읽는 프로덕션
#   경로가 애초에 없어(`replay_orphan` 호출자 0) 버퍼째 걷어냈기 때문이다. 경보를 걸 자리는
#   이제 버퍼 크기가 아니라 `reason="terminal_event_lost"` 의 증가율이다.
qb_ws_orphan_discarded_total = Counter(
    "qb_ws_orphan_discarded_total",
    "WS order events discarded because no local order row matched (recovery is the reconciler)",
    labelnames=("account_id", "reason"),
)

# 12. reconnect 직후 reconciliation 에서 exchange 에 없는 local active order.
qb_ws_reconcile_unknown_total = Counter(
    "qb_ws_reconcile_unknown_total",
    "Local active orders not found in exchange open/recent (state unchanged + alert)",
    labelnames=("account_id",),
)

# 13. reconciliation debounce 30s 로 skip 된 횟수.
qb_ws_reconcile_skipped_total = Counter(
    "qb_ws_reconcile_skipped_total",
    "Reconciliation skipped due to 30s debounce",
)

# 14. 같은 account 에 대해 process-level guard 가 중복 enqueue 차단.
qb_ws_duplicate_enqueue_total = Counter(
    "qb_ws_duplicate_enqueue_total",
    "ws_stream task duplicate enqueue blocked by process-level guard",
)

# 15. WebSocket 재연결 횟수.
qb_ws_reconnect_total = Counter(
    "qb_ws_reconnect_total",
    "WebSocket reconnect attempts",
    labelnames=("account_id",),
)

qb_ws_subscribe_rejected_total = Counter(
    "qb_ws_subscribe_rejected_total",
    "WebSocket subscribe negative acknowledgements",
    labelnames=("account_id",),
)

# 16. (Sprint 19 BL-081) Pending fire-and-forget alert task 의 현재 in-flight 개수.
# Sprint 18 의 영속 _WORKER_LOOP 채택 후 alert task 가 cross-task 경계를 살아남을
# 수 있어 unbounded 누적 risk. 본 gauge 는 운영 모니터링 — 임계 (e.g. >50)
# 초과 시 Slack/Grafana alert 권장 (Sprint 20+ 운영 wire-up).
qb_pending_alerts = Gauge(
    "qb_pending_alerts",
    "In-flight fire-and-forget alert tasks (kill switch / scan watchdog 등)",
    multiprocess_mode="livesum",
)

# 17. (Sprint 26) Live Signal Auto-Trading — eval/dispatch task observability.
# 1분 Beat 가 active session 별로 평가 → outbox INSERT → dispatch task 가 OrderService.execute.
qb_live_signal_evaluated_total = Counter(
    "qb_live_signal_evaluated_total",
    "Live signal evaluate task outcome (per session per fire)",
    labelnames=("interval", "outcome"),  # outcome: success | no_new_bar | claim_lost | error
)
qb_live_signal_dispatch_total = Counter(
    "qb_live_signal_dispatch_total",
    "Live signal event dispatch outcome",
    labelnames=(
        "action",
        "outcome",
    ),  # action: entry|close, outcome: dispatched|kill_switched|notional|other
)
qb_live_conditional_placed_total = Counter(
    "qb_live_conditional_placed_total",
    "Live conditional entry intents accepted for execution",
    labelnames=("direction",),
)
qb_live_conditional_cancelled_total = Counter(
    "qb_live_conditional_cancelled_total",
    "Live conditional entries cancelled during reconciliation",
    labelnames=("reason",),
)
# ★`deferred_market_inflight` 계열은 유실 건수가 아니라 시장가 주문이 in-flight 인 tick 의
# 평가 발화 횟수다. `deferred_market_inflight` 는 pending 조건부 진입이 있어 실제로 미룬
# 경우이고, `deferred_market_inflight_noop` 는 미룰 조건부 진입이 없었던 경우다.
#
# ★원장 기반 `entry_completeness` 비율과 절대 합산하지 마라. 이 값은 의도별 원장이 아니라
# tick 발화 횟수라 같은 조건부 진입이 여러 bar 에서 중복 발화할 수 있다.
#
# ★`deferred_market_inflight_noop` 는 이번 배포에서 태어난 새 series 다. 기존 라벨과 절대값을
# 나란히 비교할 수 없고, 같은 관측 창의 차분만 비교해야 한다.
#
# ★`deferred_ledger_unreadable` — [ADR-025] §⑧. 원장을 못 읽어 그 tick 만 현행 시뮬로 되돌린
# 경우다. 이것도 **실패가 아니라 미룸**이라 `deferred_market_inflight` 계열과 같은 성질이며,
# 발생률은 `qb_live_conditional_fill_ownership_total{outcome=ledger_unreadable_fallback}` 과
# **같은 tick 을 세므로** 두 값은 나란히 움직여야 한다(갈리면 한쪽 계측이 깨진 것이다).
qb_live_conditional_reconcile_errors_total = Counter(
    "qb_live_conditional_reconcile_errors_total",
    "Live conditional entry reconciliation failures",
    labelnames=("stage",),
)
qb_live_conditional_guard_total = _GuardOutcomeCounter(
    "qb_live_conditional_guard_total",
    "조건부 진입 등재 시점 가드의 판정 결과이며 실제 거래소 결과는 qb_exchange_order_response_total",
    labelnames=("outcome",),
)
qb_live_conditional_sweep_filled_total = Counter(
    "qb_live_conditional_sweep_filled_total",
    "Inactive-session conditional entries found filled during sweep",
)

# BL-516 안 3 — 부호가 교차하는 조건부 진입(반전)을 **등재한 횟수**와 그 크기.
#
# ★수량 산식은 의도적으로 바꾸지 않았다. `plan_reconcile` 은 `abs(target - current)` 한 건을
#   그대로 내보내고 `reduce_only=False` 도 그대로다. leg 분리(청산 leg + 진입 leg)는
#   `Order.reduce_only.is_(False)` 술어 4곳(`order_repository.py:275/315/347/513`)이 청산 leg 를
#   reconciler·sweep·janitor·진입원장에서 전부 배제해 고아 주문을 낳고, 같은 trigger 가의
#   조건부 2건은 체결 순서가 보장되지 않아 `110017 same-side` 를 늘리기 때문이다.
#   그래서 이 counter 는 **고치기 전에 크기부터 재는** 계측기다.
#
# ★`bucket` 은 overshoot 비율 `주문수량 / |목표 포지션|` 의 하한이다. `1x` 는 반전이지만
#   보유가 미미해 순수 진입과 사실상 같은 경우(예: 목표 -8, 보유 +0.001 -> 비율 1.0001)다.
#   순수 진입(비율 정확히 1.0)은 부호 교차가 아니므로 **여기서 세지 않는다** — 분모가 필요하면
#   `qb_live_conditional_placed_total` 을 봐라.
#
# ★유실 건수가 아니라 **등재 성공 횟수**다. 발화 지점이 `order_service.execute` 직후라
#   캡(`max_reversal_overshoot_ratio`)에 막혀 등재되지 않은 반전은 여기 없다 —
#   그쪽은 `qb_live_conditional_plan_drop_evaluations_total{reversal_overshoot_exceeds_cap}` 이다.
#
# ★★BL-562 — **체결된 반전 수가 아니라 등재 시점 판정이다.** 두 방향으로 어긋난다:
#     (1) 등재는 매 tick 취소·재등재될 수 있어 한 의도가 여러 번 오른다(지속시간 신호).
#     (2) 조건부 주문은 트리거까지 대기하므로 bucket 은 **등재 순간의 포지션**으로 잰
#         근사다. 보통은 다음 tick 재등재가 갱신하지만, 목표와 실포지션이 같은 폭으로
#         움직이면 갱신 없이 트리거까지 간다(`conditional_entry_planner.py:542-547`).
#   ⇒ 이 값을 "실제로 이만큼 반전이 체결됐다" 로 읽지 마라. 체결 기준이 필요하면 원장
#     (`trading/entry_completeness.py` 계열)을 봐라 — 이 counter 와 **합산하지 마라**.
#
# Cardinality: bucket ∈ {1x, 2x, 4x, 8x+} = 4 series.
qb_live_conditional_reversal_total = Counter(
    "qb_live_conditional_reversal_total",
    "부호가 교차하는 조건부 진입을 **등재한** 횟수 (등재 시점 근사, overshoot 버킷별)",
    labelnames=("bucket",),
)

# BL-562 — 같은 질문을 **체결 시점의 실제 포지션**으로 다시 잰다.
#
# ★★위 `qb_live_conditional_reversal_total` 과 **절대 합산하지 마라. 축이 다르다.**
#     등재 counter — "이런 반전을 등재했다". 취소·재등재로 **한 의도가 여러 번** 오르고,
#                    등재된 뒤 트리거 전에 포지션이 움직이면 그 값은 낡는다.
#     이 counter   — "체결된 조건부 진입 1건을 **체결 후 포지션**으로 재보니 이랬다".
#                    fill-transition 승자 1곳에서만 예약되므로 **체결당 정확히 1회**다.
#   ⇒ 비율이 필요하면 이 counter 안에서만 만들어라(분모 = 이 counter 의 전 버킷 합).
#
# bucket ∈ {1x, 2x, 4x, 8x+}  — 등재 counter 와 **같은 경계**(`_reversal_overshoot_bucket` 공유)
#          + {not_reversal} + `unmeasured_*` 6종 = 11 series.
#     not_reversal — 쟀고, 반전이 아니었다(같은 방향 증량 또는 flat 진입).
#
# ★★**못 잰 것을 한 라벨에 묻지 마라.** `unmeasured` 하나로 두면 "재보니 반전이 없었다" 와
#   "계측기가 죽었다" 가 같은 침묵이 된다 — BL-560 이 정확히 그 병이었고, codex 2차 리뷰가
#   이 counter 에서 같은 병을 다시 지적했다. 그래서 사유별로 가른다:
#     unmeasured_no_position          — 포지션이 안 보인다(체결 미전파 / 체결 직후 청산).
#     unmeasured_pre_fill_read        — 포지션 방향이 우리 체결과 반대 = **체결 전 스냅샷**.
#     unmeasured_no_anchor            — 포지션 생성 시각 또는 `submitted_at` 결측.
#     unmeasured_position_predates_order — 포지션이 우리 주문 발주보다 먼저 생겼다
#                                       (= 우리 체결이 만든 포지션이 아니다).
#     unmeasured_no_fill_qty          — 체결 수량이 없거나 비정상.
#     unmeasured_error                — 계정/복호화/거래소 조회 실패. **인프라 신호**다.
#   ⇒ `unmeasured_*` 합이 크면 반전이 없는 것이 아니라 **계측이 안 되고 있는 것**이다.
#     특히 `unmeasured_error` 는 반전 분포가 아니라 장애 알림으로 읽어라.
qb_live_conditional_reversal_filled_total = Counter(
    "qb_live_conditional_reversal_filled_total",
    "체결된 조건부 진입을 체결 후 실제 포지션으로 재판정한 반전 버킷 (체결당 1회)",
    labelnames=("bucket",),
)

# BL-536 — 지금까지 Prometheus 계측이 **0개**였던 침묵 유실 지점 2 곳.
#
# ★★두 counter 모두 「유실 건수」가 아니라 **「평가 발화 횟수」**다. 이름이 그렇게 돼 있고,
#   그 이유가 이 주석의 존재 이유다. `plan_reconcile` 과 `run_live` 는 순수 함수라 상태를
#   지우지 않는다. 해결되지 않은 leg 는 **매 평가마다** 같은 사유를 다시 만든다 — 특히
#   `below_exchange_minimum`(전략 수량이 거래소 step 미만이라 이 계정에서 영원히 한 주도
#   못 낸다)은 **새 bar 마다** 1씩 오른다. 그러면 "시간당 N" 은 유실 의도 N개가 아니라
#   **한 의도가 N bar 살아 있었다**는 뜻이다.
#
# ★**"매 분" 이 아니라 "bar 당" 이다** (BL-536 R2 정정). beat 는 1분마다 깨우지만
#   `run_live` 는 `no_new_bar` 조기 return **뒤**에만 돈다. 5m 세션이면 5분에 1회,
#   1h 세션이면 60분에 1회다. 이것을 "매 분" 으로 읽으면 지속시간을 **12~60배 과소평가**한다.
#   (`gates-and-traps.md` 가 이미 등재한 함정 — "tick 간격을 상수의 근거로 삼기 전에
#   그 tick 이 실제로 언제 도는지 읽어라".)
#
# ★★**두 counter 를 같은 시간축으로 읽지 마라.** 발화 지점이 서로 다른 조기 return 뒤에 있다:
#     pending_order_skip — `run_live` 직후. runtime divergence / gap mismatch /
#                          position divergence **앞**이라 그 tick 들도 잡힌다.
#     plan_drop          — `_reconcile_conditional_entries` 안. 위 셋을 **전부 통과한**
#                          tick 에서만 오른다. 즉 분모가 더 작다.
#   같은 창에서 두 값을 나란히 놓고 비율을 만들면 그 비율은 아무것도 뜻하지 않는다.
#
#   이것은 `qb_live_position_divergence_total{engine_only}` 이 무효가 된 것과 **같은 유형의
#   함정**이다(아래 그 counter 주석 참조). 그래서:
#     - 원장 기반 분해(`trading/entry_completeness.py`)와 **절대 합산하지 마라**.
#     - 고유 의도 수가 필요하면 원장 분해의 에피소드 수를 봐라. 이 값은 지속시간 신호다.
#
# ★기존 `qb_live_conditional_guard_total` 과도 합산하지 마라. `breach_exceeds_cap` 과
#   `trigger_already_breached`(had_resting) 는 guard 에도 함께 기록되고, `breach_capped` 는
#   계획기 밖 시장가 전환 직전 재조회에서도 오른다. 두 counter 는 등식 검산 대상이 아니다.
#
# ★발화 지점은 라이브 태스크(`tasks/live_signal.py`)다. 계획기와 `pine_v2` 엔진에는 넣지
#   않는다 — `event_loop.py` 는 백테스트·옵티마이저·스트레스 테스트가 재실행하는 **같은
#   엔진**이라 거기 계측을 넣으면 백테스트를 돌릴 때마다 라이브 metric 이 발화한다.
#
# reason 은 라이브 태스크에서 allowlist 정규화한다(미지 값은 `other`) — cardinality 보호.
qb_live_conditional_plan_drop_evaluations_total = Counter(
    "qb_live_conditional_plan_drop_evaluations_total",
    "조건부 진입 계획기가 leg 를 드롭한 **평가 발화 횟수** (중복 포함, 유실 건수 아님)",
    # reason ∈ reduce_only_entry_ignored | trigger_already_breached | breach_exceeds_cap
    #        | below_exchange_minimum | target_already_met_cancelled | entry_side_mismatch
    #        | reversal_overshoot_exceeds_cap | other  = 8 series.
    labelnames=("reason",),
)

# BL-576 — 조건부 reconcile 중 계획기 밖에서 난 사건을 사건 종류와 사유로 분리한다.
# `plan_drop` 은 위 `qb_live_conditional_plan_drop_evaluations_total{reason}` 가 이미
# 평가 발화 횟수를 세므로 여기에 넣지 않는다. 두 counter 를 합산하지 마라.
# `breach_exceeds_cap` 은 계획기와 등재 가드 양쪽에서 나고 payload 키셋도 달라 reason
# 단독으로는 유일하지 않다. event 축이 그 충돌을 막는다.
# Cardinality: event별 허용 reason 1 + 2 + 1 + 3 + 1 = 8, event별 other 5 = 최대 13 series.
qb_live_conditional_divergence_total = Counter(
    "qb_live_conditional_divergence_total",
    "조건부 reconcile의 계획기 밖 사건 수 (event와 정규화된 reason별)",
    labelnames=("event", "reason"),
)

# ★이 counter 는 `run_live` 가 정상 반환한 평가에서만 오른다. 그 뒤의 runtime divergence·
#   gap mismatch·position divergence 는 각자 조기 return 하므로, 그 tick 들은 여기 안 잡힌다.
#   발화 지점을 `run_live` 직후로 둔 이유가 그것이다 — 더 앞에는 result 자체가 없다.
#
# ★★**트랜잭션 밖이다 — 재시도만큼 중복된다** (BL-536 R3-⑤).
#   발화 지점이 `try_claim_bar` 뒤 · 단일 commit **앞**이라, 이후 state upsert/commit 이
#   실패하면 DB claim 은 rollback 되지만 **Counter 증가는 되돌아가지 않는다.** 다음 tick 이
#   같은 bar 를 재평가하면 이 값만 한 번 더 오른다.
#   ★고치지 않고 **적어 두는** 쪽을 택했다. commit 뒤로 옮기면 위 조기 return 세 곳
#   (runtime divergence · gap mismatch · position divergence)의 평가가 **통째로 안 잡힌다** —
#   그건 이 counter 를 `run_live` 직후에 둔 이유 자체를 되돌리는 것이고, 잃는 정보가 더 크다.
#   이 counter 는 애초에 「평가 발화 횟수(중복 포함)」계열이므로 중복은 계약 위반이 아니다.
#   ★다만 **"발화 = 평가 1회" 로 읽지 마라.** commit 실패 재시도가 있으면 발화 수 ≥ 평가 수다.
qb_live_pending_order_skip_evaluations_total = Counter(
    "qb_live_pending_order_skip_evaluations_total",
    "엔진이 pending 진입 leg 를 건너뛴 **평가 발화 횟수** (중복 포함, 유실 건수 아님)",
    # reason ∈ session_disallowed | invalid_leg | below_api_precision | other = 4 series.
    labelnames=("reason",),
)
qb_trailing_placement_total = Counter(
    "qb_trailing_placement_total",
    "STEP B — fill 후 native trailing-stop placement 결과",
    # outcome: placed | skipped_no_intent | skipped_unsupported
    #          | skipped_position_flat_premature (transient — fast-fill REST-lag, 재시도 중)
    #          | skipped_position_flat_confirmed (재시도 후 진짜 flat 으로 concede)
    #          | skipped_position_mismatch | skipped_position_zero
    #          | skipped_position_reopened (BL-372 — close→동일방향 reopen 된 무관 포지션)
    #          | failed (network/exchange → 무방비 → critical alert)
    #          | failed_contract (TrailingContractError — 버전/degenerate/hedge)
    labelnames=("outcome",),
)

# MP-2 — Bybit closedPnl 확정 손익 backfill 결과.
# outcome: applied | already_synced | skipped_unsupported | skipped_incomplete | never_found
#          | failed_provider | orphan_row | malformed_row.
# never_found / failed_provider / skipped_incomplete > 0 이면 해당 청산 주문이 pine_v2
# 시뮬레이션 손익을 유지한 채로 Kill Switch에 계상되고 있다는 뜻이다.
# skipped_incomplete 는 exchange_order_id/account/filled_at 결측 같은 데이터 이상이다
# (경합으로 인한 정상 no-op 는 계상하지 않는다).
# malformed_row 는 파싱 불가로 건너뛴 거래소 행 (페이지 전체를 버리지 않기 위한 관측치).
# orphan_row 는 우리 Order 와 매칭되지 않는 closedPnl 행 = 거래소 네이티브 TP/SL 청산.
# Cardinality: 고정 outcome 8개 series만 허용한다.
qb_closed_pnl_backfill_total = Counter(
    "qb_closed_pnl_backfill_total",
    "Bybit closedPnl 확정 손익 backfill 결과",
    labelnames=("outcome",),
)

# exit-attribution — 거래소 청산 원장에 새로 적재된 행 수. 재조회로 중복 관측되는 행은
# 세지 않는다(원장 UNIQUE 가 종료 조건을 준다).
# classification: ours | bracket_tp | bracket_sl | trailing | liquidation | external_manual | unknown.
# Cardinality: 고정 classification 7개 series만 허용한다.
qb_exchange_exit_rows_total = Counter(
    "qb_exchange_exit_rows_total",
    "거래소 청산 원장에 새로 적재된 행 수",
    labelnames=("classification",),
)

# BL-457 — orderLinkId 가 우리 형식(UUID)인데 그 Order 행이 계정 스코프에 **없는** 행 수.
# 이 값이 오르면 (a) 우리 DB 가 주문 이력을 잃었거나 (b) 외부 도구가 UUID 모양 client
# order id 를 달고 있다. 어느 쪽이든 `ours` 를 주장할 근거가 아니므로 라벨은 unknown 으로
# 떨어지고, 그 사실 자체를 여기서 센다. ★"우리 DB 가 행을 잃었다" 는 청산의 속성이 아니라
# 우리 운영 사실이므로 domain enum 이 아니라 메트릭이 올바른 집이다. 이 카운터가 실제로
# 오르기 시작하면 그때 전용 classification 값 추가를 재검토한다(양방향 마이그레이션 0).
qb_exchange_exit_link_unverified_total = Counter(
    "qb_exchange_exit_link_unverified_total",
    "orderLinkId 는 우리 UUID 형식인데 해당 Order 행이 없어 소유를 주장하지 못한 청산 행 수",
)

# BL-464 — 원장 행의 전략 귀속 등급 분포. `inferred` 는 검정력이 없는 휴리스틱이므로
# 머니-패스 입력으로 승격하기 **전에** 실제 비율을 재기 위해 존재한다.
# confidence: exact | inferred | none. Cardinality: 고정 3개 series만 허용한다.
qb_exchange_exit_attribution_total = Counter(
    "qb_exchange_exit_attribution_total",
    "거래소 청산 원장 신규 행의 전략 귀속 등급",
    labelnames=("confidence",),
)

# BL-454 — TradingView 웹훅 심볼을 canonical 로 정규화하지 못해 거부한 횟수.
# ★fail-closed 를 택한 이유가 이 카운터다. TV `{{ticker}}` 가 퍼프에서 정확히 무엇인지
# 1차 출처로 확인하지 못했으므로 장식 제거를 추측으로 넣지 않았다. 이 값이 오르면
# `webhook_symbol_normalize_failed` 로그의 원문이 실제 포맷을 알려준다.
qb_webhook_symbol_rejected_total = Counter(
    "qb_webhook_symbol_rejected_total",
    "TradingView 웹훅 심볼을 정규화하지 못해 거부한 횟수",
)

# Sprint 48 Pass 2 — 체결 winner가 주문 수량보다 적은 확정 수량을 받은 경우만 집계.
# source: rest | ws | watchdog | reconciler.
# kind: entry | close.
# Cardinality: source 4개와 kind 2개로 총 고정 8개 series만 허용한다.
#
# ★BL-536 — **무엇을 세지 않는가.** 이 counter 를 진입 부분체결의 측정치로 쓰지 마라.
#   실측에서 `{ws}` = 19 인데 같은 창의 진입 원장(`reduce_only = false`)에는
#   `filled_quantity < quantity` 인 행이 **0** 이었다. 모순이 아니라 세는 대상이 다르다.
#   (a) 이제 코드는 `reduce_only` 를 검사해 `kind=entry|close` 로 분리한다. 청산 수량은
#       엔진 값을 그대로 싣고(`tasks/live_signal.py` 의 `Decimal(str(event.qty))`)
#       거래소 눈금으로 절삭되지 않으므로, **전량 체결이어도** 거래소 확정 수량이
#       우리 요청값보다 작아 `kind=close` 부분체결로 잡힌다. 조건부 진입은 반대다 —
#       `conditional_entry_planner.plan_reconcile` 이 `qty_step` 으로 미리 정규화해
#       발주하므로 그 불일치가 구조적으로 생기지 않는다.
#   (b) session / strategy / symbol label 이 없다. 어느 세션의 것인지 되짚을 수 없다.
#   (c) 시간축이 다르다. 이 값은 프로세스 수명 누적이고 발화 시점은 **terminal 시각**인데,
#       진입 원장 분해는 `created_at` cohort 다. 창 전 생성 - 창 안 체결 행은 한쪽에만 잡힌다.
#   진입 부분체결은 `trading/entry_completeness.py` 의 원장 분해로 측정한다.
qb_partial_fill_total = Counter(
    "qb_partial_fill_total",
    "Orders filled with a known quantity below the requested quantity",
    labelnames=("source", "kind"),
)


def record_partial_fill(*, source: str, reduce_only: bool) -> None:
    """부분체결 1건을 기록한다. ★**절대 던지지 않는다.**

    이 helper 가 있는 이유가 두 가지다 (2026-08-01 codex 적대 리뷰 MAJOR).

    1. ★**새 label 조합은 multiprocess mmap 할당을 새로 유발한다.** `kind` 축을 추가하면서
       `{source,kind}` 8종이 전부 처음 할당되는데, 그 할당이 실패하면(`OSError` 등)
       `.labels().inc()` 가 **던진다.** 네 호출부는 전부 **DB commit 뒤 · trailing/PnL 후속
       enqueue 앞**이라, 던지면 **체결 후처리가 통째로 중단된다.** `record_metric_safely` 가
       정확히 그것을 막으려고 존재한다(`tasks/trading.py` 의 reversal counter 가 선례).
       ★**「선재 상태라 새 위험이 없다」고 넘겼던 판단을 정정한다** — 새 label 조합 자체가 새 위험이다.
    2. `reduce_only → kind` 판정식이 네 곳에 복제돼 있었다. 의미가 바뀌면 드리프트한다.

    `reduce_only` 는 `orders` 에서 **NOT NULL · default false** 라 삼항이 모호하지 않다.
    회귀 가드 = `tests/trading/test_ws_state_handler_active_orders.py`
    `test_partial_fill_metric_failure_does_not_stop_fill_postprocessing`
    (래핑을 벗기면 죽는 것을 CONTROL 이 변이로 확인했다).
    """
    record_metric_safely(
        lambda: qb_partial_fill_total.labels(
            source=source, kind="close" if reduce_only else "entry"
        ).inc()
    )


qb_live_signal_skipped_total = Counter(
    "qb_live_signal_skipped_total",
    "Live signal evaluate skipped reason",
    # stop_entry_unsupported | equity_baseline_missing 등 preflight 차단 사유를 포함한다.
    labelnames=("reason",),  # contention | non_demo_account | invalid_settings | session_inactive
)
qb_live_signal_entry_skipped_total = Counter(
    "qb_live_signal_entry_skipped_total",
    "Live signal entry swallowed by an engine gate (not a divergence)",
    labelnames=(
        "reason",
    ),  # margin_insufficient | non_finite_qty | pyramiding_cap | session_closed
)
qb_live_signal_liquidation_total = Counter(
    "qb_live_signal_liquidation_total",
    "Live signal simulated liquidations",
    labelnames=("direction",),  # long | short
)
qb_live_signal_eval_duration_seconds = Histogram(
    "qb_live_signal_eval_duration_seconds",
    "Live signal evaluate task end-to-end latency",
    labelnames=("interval",),
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, float("inf")),
)
qb_live_signal_outbox_pending_gauge = Gauge(
    "qb_live_signal_outbox_pending_gauge",
    "Live signal outbox events with status=pending (snapshot at last eval cycle)",
    multiprocess_mode="mostrecent",
)
# BL-362 — live 경로 coverage↔interpreter 발산(silent swallow) fail-closed 집계.
# 발산 감지 시 세션 자동 비활성화 + 본 metric inc + critical alert. 0 초과 = 즉시 운영 page.
qb_live_signal_divergence_total = Counter(
    "qb_live_signal_divergence_total",
    "Live signal money-path divergence blocked (auto-deactivate session)",
    # stage: preflight | runtime | position
    # category(preflight): coverage_unrunnable | degraded_unconsented
    #   stop_entry_unsupported | equity_baseline_missing 는 skipped 전용이며 이 counter 대상 아님.
    # category(runtime): undefined_name | unsupported_attr | unsupported_call
    #                    | unsupported_node | unexpected | run_live_error
    #   run_live_error = run_live 가 result.errors 밖으로 raise (parse/raw arithmetic 등)
    # category(position): direction — 엔진과 거래소가 **반대 방향**을 들고 있다(BL-530).
    #   ★차단된 것만 싣는다. 차단하지 않는 발산 관측은 아래
    #   `qb_live_position_divergence_total` 이며, 여기에 섞으면 "0 초과 = 즉시 page"
    #   계약이 깨져 관측이 곧 오탐 페이징이 된다.
    labelnames=("stage", "category"),
)

# BL-530 — 엔진↔거래소 포지션 발산 **관측**(차단 아님). 위 counter 와 분리한 이유는
# 페이징 계약이 다르기 때문이다. 여기 값은 정상 운영 중에도 0 이 아닐 수 있고,
# BL-522(진입 완결성) 설계에 쓸 유실 크기의 입력이다.
#   category: engine_only    — 엔진만 포지션을 믿는다. 이 counter 는 dispatch 보다 한 tick
#               앞서 판정하므로 마지막 bar 신규 진입은 주문 enqueue 전 한 번 잡힌다.
#               유실이 없어도 진입 1건당 1씩 늘 수 있다. 이 값을 진입 유실의 측정치로
#               쓰지 마라.
#             engine_only_awaiting_trigger — 같은 세션의 같은 방향 대기 조건부 진입이 있다.
#               엔진은 봉 종가에 진입하고 거래소 조건부 진입은 트리거될 때까지 체결되지
#               않으므로, 이것은 설계된 지연이며 결함이 아니다.
#             engine_only_unexplained — 같은 세션의 같은 방향 대기 조건부 진입이 없어
#               설명할 수 없는 엔진 전용 포지션이다. 이 라벨만 결함 후보다.
#             engine_only — 대기 조건부 진입 원장을 읽지 못해 세분화하지 못한 잔여다
#               (fail-open).
#             위 세 라벨을 합산하면 옛 `engine_only`와 같지만, 그 합계도 여전히 진입
#               유실의 측정치가 아니다.
#               재생 창보다 오래 산 실제 포지션은 재생에 없어서 engine_only 가 아니라
#               exchange_only 로 나타난다. 진입 유실은 orders.idempotency_key 기준 진입측
#               원장으로 측정한다(live-close-diagnostics.md §3).
#             exchange_only  — 거래소에만 포지션이 남았다(고아 노출)
#             size           — 방향은 같고 크기가 다르다(부분체결·수량 step)
#             probe_failed   — 거래소를 못 읽어 판정 자체를 못 했다(fail-open)
#             direction_transient — 방향 불일치 **1회차**. 거래소는 bar 안에서 스톱을
#               트리거하고 엔진은 bar 종가에만 평가하므로 stop-and-reverse 는 한 bar
#               동안 정상적으로 어긋난다(실측). 연속 2회 살아남아야 차단이다.
# 차단된 `direction` 은 여기 없다 — 위 counter 가 SSOT 다.
qb_live_position_divergence_total = Counter(
    "qb_live_position_divergence_total",
    "Live engine vs exchange position divergence observed (not blocked)",
    labelnames=("category",),
)

# BL-544 — 장기 공백 재개 시 **주문 원장으로 엔진 포지션을 채택**한 결과. gap-resync 판정
# 직전에 정확히 1회 발화한다.
#   outcome: applied      — 채택했다. ★이 label 은 신규 엔진 훅
#              (`StrategyState.seed_positions_from_ledger`)이 실제로 돌아야만 나온다.
#              soak 의 sentinel 이 이것이다 — 코드가 mount 됐는지가 아니라 **돌았는지**를 잰다.
#            already_open — 원장 근거는 있는데 재생이 이미 포지션을 들고 있어 멱등 가드가 막았다.
#            no_basis     — 공백 창에 체결이 없다. 거래소가 non-flat 이면 계속 사망한다(설계대로).
#            inadmissible — 창이 자동 재구성 대상이 아니다(양방향 혼재 · reduce-only 포함 ·
#                           trade id 복원 실패/중복). seed 하지 않고 기존 판정으로 떨어진다.
#            unreadable   — 체결 수량/가격이 NULL 이거나 비정상.
#            overflow     — 창 안 체결이 상한을 넘었다. 부분 원장으로 순포지션을 만들지 않는다.
#            fetch_failed — 원장 조회 자체가 실패했다.
# ★applied 를 제외한 전부는 **기존 fail-closed 경로 유지**를 뜻한다. 0 초과가 곧 장애는 아니다.
qb_live_gap_ledger_seed_total = Counter(
    "qb_live_gap_ledger_seed_total",
    "Gap-resync engine position seeded from the order ledger",
    labelnames=("outcome",),
)

# BL-591 / ADR-022 슬라이스 1 — **계측 전용**. 매 tick `run_live` **직전**에 원장으로 포지션을
# 유도하고 거래소 스냅샷과 대조한 결과다. ★슬라이스 1 은 아무것도 주입하지 않는다 —
# 이 counter 가 0 이 아니어도 **동작은 오늘과 동일**하다. 슬라이스 2 의 계수를 여기서 정한다.
#
#   outcome = `derive_open_position` 의 판정 (`ledger_position.py`):
#     no_fills / flat / open        — 판정됨
#     overflow / foreign_fill / close_without_open / duplicate_open / unreadable
#                                   — **판정 불가**(fail-closed). 슬라이스 2 는 주입하지 않는다.
# ★`legs == ()`(flat) 과 판정 불가를 **절대 합산하지 마라.** 전자는 "포지션이 없다고 판정함",
#   후자는 "모른다" 다. 합치면 모르는 상태가 flat 으로 둔갑한다.
qb_live_ledger_derive_total = Counter(
    "qb_live_ledger_derive_total",
    "Ledger-derived open position outcome, measured before run_live (no injection)",
    labelnames=("outcome",),
)

# BL-591 / ADR-022 슬라이스 1 — 원장 유도 포지션 ↔ 거래소 스냅샷 대조. **슬라이스 2 의
# veto 판정을 미리 재는 것**이며 지금은 아무 동작도 바꾸지 않는다.
#
#   decision: agree        — 일치. 슬라이스 2 라면 **주입했을** tick.
#             disagree     — 불일치. 슬라이스 2 라면 **veto + 관망**했을 tick.
#                            ★이 값의 비율과 연속 지속 길이가 관망 상한 계수의 직접 근거다.
#             undecidable  — 원장으로 판정 불가(위 counter 의 fail-closed 갈래).
#             probe_failed — 거래소 조회 자체가 실패. ★`disagree` 와 섞지 마라 —
#                            섞으면 조회 장애가 발산으로 둔갑한다.
# ★`agree` 는 "엔진에 주입 가능" 을 뜻하지 않는다. 주입은 **엔진이 flat 일 때만** 일어나므로
#   (`strategy_state.py:357`) 실제 주입 가능 tick 은 아래 `engine_flat` label 과 함께 봐야 한다.
qb_live_ledger_veto_total = Counter(
    "qb_live_ledger_veto_total",
    "Ledger vs exchange agreement measured before run_live (shadow; no action taken)",
    labelnames=("decision", "engine_flat"),
)

# BL-591 / ADR-022 슬라이스 1 — **연속 `disagree` 가 몇 tick 만에 풀렸는가.**
# ★관망 상한 계수의 **직접 근거**가 이 분포다. `disagree` 비율만으로는 상한을 못 정한다 —
#   중요한 것은 "얼마나 오래 어긋나 있었나" 이기 때문이다.
# ★label 은 **버킷**이다(raw tick 수를 label 로 쓰면 cardinality 가 터진다).
#   bucket: 1 | 2 | 3-5 | 6-15 | 16+
# ★tick 주기 = `interval` 이므로 **분이 아니라 tick 이다.** 1분봉이면 3-5 = 3~5분,
#   1시간봉이면 3~5시간이다. 절대 시간으로 읽으면 상한 계수를 틀리게 정한다.
qb_live_ledger_hold_resolved_total = Counter(
    "qb_live_ledger_hold_resolved_total",
    "Consecutive ledger/exchange disagreement runs, bucketed by tick length",
    labelnames=("bucket",),
)

# ADR-025 / BL-595 — 라이브 조건부 진입 체결의 **권한이 원장으로 넘어간 뒤**, 「엔진 시뮬이
# 하려던 것」과 「원장이 실제로 증언한 것」이 얼마나 갈리는가. 매 tick 재생 전체에 대해 센다.
#
#   outcome: agree                    — 시뮬도 체결했을 자리에서 원장도 체결했다.
#            engine_only_suppressed   — ★시뮬은 체결했을 텐데 원장에 없다 = [BL-595] **형 A 차단**.
#                                       수리 전이라면 여기서 유령 포지션이 생겨 세션이 죽었다.
#            ledger_only_adopted      — ★원장은 체결했는데 시뮬은 아직이다 = **형 B 차단**.
#                                       엔진이 못 본 봉에서 거래소가 체결한 경우가 여기다.
#            ledger_only_orphan       — 원장 체결의 `trade_id` 에 해당하는 pending 이 엔진에 없다.
#                                       **아무 동작도 하지 않는다**(ADR-025 R4) — 발생률만 잰다.
#            ledger_unreadable_fallback — 원장을 못 읽어 그 tick 만 **현행 시뮬로 되돌렸다**.
#                                       ★조용히 되돌리면 "고쳤는데 왜 또 죽나" 를 못 푼다.
#
# ★`engine_only_suppressed` + `ledger_only_adopted` 는 이 수리의 **양성 대조**다. 둘 다 0 이면
#   "고쳤다" 가 아니라 "그 경로를 안 밟았다" 이고, 그렇게 적어야 한다.
# ★`agree` 대비 나머지의 비율이 **백테스트 낙관 편의의 첫 실측치**이기도 하다 — 지금은 아무도
#   그 값을 모른다(Trust Layer 는 우리 자신의 얼린 출력과 대조할 뿐 외부 오라클이 없다).
qb_live_conditional_fill_ownership_total = Counter(
    "qb_live_conditional_fill_ownership_total",
    "Live conditional entry fills: engine simulation vs order-ledger testimony (ADR-025)",
    labelnames=("outcome",),
)

# Redis 실시간 팬아웃 발행 실패. user/event ID는 label로 사용하지 않는다.
qb_rt_publish_failed_total = Counter(
    "qb_rt_publish_failed_total",
    "Realtime Redis publish failures",
)

# Redis 호출 전 payload 계약 위반은 인프라 발행 실패와 분리해 관측한다.
qb_rt_publish_invalid_total = Counter(
    "qb_rt_publish_invalid_total",
    "Realtime publish payload contract violations",
    labelnames=("event_type",),
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
