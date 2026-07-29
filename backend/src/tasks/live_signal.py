"""Sprint 26 — Live Signal Auto-Trading 의 evaluate + dispatch Celery tasks.

두 task 분리 (codex G.0 P1 #3 transactional outbox):

1. `evaluate_live_signals_task` (Beat 1분 fire) — interval 별 due session 평가:
   - RedisLock contention 차단 (P1 #4 ttl_ms=60_000 + heartbeat extend 20s)
   - try_claim_bar winner-only (P2 #3) — 같은 bar 두 번 평가 race 방어
   - CCXT fetch_ohlcv(limit_bars=300) closed-bar (P1 #6)
   - run_live (warmup replay, Option B) → LiveSignalEvent INSERT (status=pending)
   - state upsert + session UPDATE + commit 단일 트랜잭션 (P1 #3 outbox)
   - 신규 INSERT 된 event 만 dispatch task apply_async

2. `dispatch_live_signal_event_task` (apply_async 받음) — pending event 1건:
   - sessions_port=_StrategySessionsAdapter 의무 주입 (P1 #5)
   - idempotency_key with sequence_no (P2 #5)
   - OrderService.execute → mark_dispatched / mark_failed
   - max_retries=3, default_retry_delay=15s

Sprint 18 BL-080 prefork-safe: 모든 task 가 `run_in_worker_loop` (asyncio.run 금지),
per-call `create_worker_engine_and_sm()` + `await engine.dispose()` finally.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from celery import shared_task
from pydantic import ValidationError

from src.common.alert import track_pending_alert
from src.common.metrics import (
    qb_active_orders,
    qb_live_conditional_cancelled_total,
    qb_live_conditional_guard_total,
    qb_live_conditional_placed_total,
    qb_live_conditional_reconcile_errors_total,
    qb_live_conditional_sweep_filled_total,
    qb_live_position_divergence_total,
    qb_live_signal_dispatch_total,
    qb_live_signal_divergence_total,
    qb_live_signal_entry_skipped_total,
    qb_live_signal_eval_duration_seconds,
    qb_live_signal_evaluated_total,
    qb_live_signal_liquidation_total,
    qb_live_signal_outbox_pending_gauge,
    qb_live_signal_skipped_total,
)
from src.common.redlock import RedisLock
from src.core.config import settings
from src.market_data.constants import to_ccxt_perpetual_symbol
from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.schemas import StrategySettings, validate_strategy_settings
from src.trading.alerting import send_rule_alert
from src.trading.exceptions import (
    BalanceUnverified,
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    MinNotionalNotMet,
    NotionalExceeded,
    TradingSessionClosed,
)
from src.trading.models import (
    AlertChannel,
    ExchangeMode,
    ExchangeName,
    LiveSignalEventStatus,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.realtime_publisher import publish_realtime

logger = logging.getLogger(__name__)


# 발산 alert 의 기본 사유/제목. preflight 비-발산 카테고리는 아래 메타데이터가 덮어쓴다.
_DIVERGENCE_REASON = "pine_v2 coverage↔interpreter 발산"
_DIVERGENCE_TITLE = "Live signal divergence — 세션 자동 비활성화 (무신호 차단)"


# preflight 카테고리별 운영 처리 계약. pageable=True 만 divergence metric으로 즉시 page한다.
_PREFLIGHT_CATEGORY_METADATA: dict[str, tuple[bool, str, str | None]] = {
    "coverage_unrunnable": (True, _DIVERGENCE_REASON, None),
    "degraded_unconsented": (True, _DIVERGENCE_REASON, None),
    "equity_baseline_missing": (
        False,
        "자본 기준선 부재",
        "세션에 자본 기준선(equity_baseline_usdt)이 없습니다",
    ),
    "equity_exhausted": (
        False,
        "자본 소진",
        "세션 누적 손익이 기준 자본을 초과했습니다",
    ),
    "gap_resync_position_mismatch": (
        False,
        "평가 공백 후 포지션 불일치",
        "평가 공백이 상한을 초과했고 거래소와 시뮬레이션 포지션을 재동기화할 수 없습니다",
    ),
    # ★등재하지 않으면 `_fire_divergence_alert` 가 기본 사유로 떨어져 운영자에게
    # "pine_v2 coverage↔interpreter 발산" 이라는 **틀린 진단**이 나간다. 위
    # `gap_resync_position_mismatch` 와 같은 계열(포지션 불일치)이므로 같은 처리 계약을 쓴다.
    "position_direction_mismatch": (
        False,
        "엔진↔거래소 포지션 방향 불일치",
        "엔진과 거래소가 연속 2회 평가에서 서로 반대 방향 포지션을 들고 있습니다",
    ),
}

# 실측된 서버 기전은 1 bar 지연뿐이다. 봉 개수 대신 벽시계 5분으로 제한해 1h 봉 장기
# 공백을 과거 주문으로 되살리지 않는다.
_MAX_CATCHUP_WALL_CLOCK_GAP = timedelta(minutes=5)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ohlcv_rows_to_dataframe(rows: list[list[Any]]) -> Any:
    """CCXT raw OHLCV [[ts_ms, o, h, l, c, v], ...] → DataFrame (timestamp column).

    `run_live` 가 마지막 bar timestamp 추출 시 'timestamp' 컬럼 우선 사용.
    Decimal 변환은 run_historical 내부에서 처리.
    """
    import pandas as pd

    df = pd.DataFrame(rows, columns=["timestamp_ms", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    return df.drop(columns=["timestamp_ms"])


def _last_close_or_none(df: Any) -> Decimal | None:
    """마지막 종료 bar의 종가를 Decimal로 반환하고 얻지 못하면 None을 반환한다."""
    try:
        value = Decimal(str(df["close"].iloc[-1]))
    except Exception:
        return None
    return value if value.is_finite() and value > 0 else None


def _build_idempotency_key(
    *, session_id: UUID, bar_time: datetime, sequence_no: int, action: str, trade_id: str
) -> str:
    """Sprint 26 codex G.0 P2 #5 — sequence_no 포함 idempotency_key.

    같은 bar 안 entry+close 동시 발생 시 sequence_no 가 두 event 를 분리하여
    OrderService 가 별개 Order INSERT 보장.
    """
    return f"live:{session_id}:{bar_time.isoformat()}:{sequence_no}:{action}:{trade_id}"


def _sanitize_for_jsonb(value: Any) -> Any:
    """BL-123 — PostgreSQL JSONB strict 호환 위해 NaN / Infinity → None.

    `run_historical` 의 indicator (ATR/EMA 등) 가 warmup 중 NaN 반환 가능. dict.to_report()
    가 이걸 dict 안에 그대로 두면 `INSERT ... json_value` 시 PG 가
    `InvalidTextRepresentationError: invalid input syntax for type json: Token "NaN"`
    raise. recursive sanitize 로 모든 NaN/Infinity 를 None 으로 정규화.

    Decimal/datetime 등 다른 nonstandard 타입은 별도 처리 (이미 schema 가 str 또는 numeric).
    """
    import math

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _sanitize_for_jsonb(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_jsonb(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_for_jsonb(v) for v in value]
    return value


def _signal_to_order_side(action: str, direction: str) -> OrderSide:
    """Pine signal (action, direction) → CCXT OrderSide.

    entry+long  → buy   (open long)
    entry+short → sell  (open short)
    close+long  → sell  (close long position)
    close+short → buy   (close short position)
    """
    if action == "entry":
        return OrderSide.buy if direction == "long" else OrderSide.sell
    if action == "close":
        return OrderSide.sell if direction == "long" else OrderSide.buy
    raise ValueError(f"Unsupported live-signal action: {action!r}")


def _action_is_reduce_only(action: str) -> bool:
    """Wave 1 C3 — close 주문만 reduce-only.

    close 의 반대편 시장청산 주문이 reduceOnly 없으면 잔여 포지션을 넘겨 over-fill /
    포지션 반전 위험. entry 는 신규 포지션 오픈이므로 reduce_only=False.
    """
    return action == "close"


# API 경계 정밀도(`OrderRequest.quantity` = decimal_places=8) 아래의 값은 주문으로 나갈 수
# 없으므로 포지션으로도 존재할 수 없다. 부동소수 누적 잔재를 방향으로 오독하지 않기 위한
# 바닥값이며, 이보다 크게 잡으면 진짜 소액 포지션이 flat 으로 위장된다.
_POSITION_DUST = Decimal("1E-8")

# 같은 방향 크기 차이를 발산이라 부르기 위한 **상대** 문턱.
#
# ★엔진의 `position_size` 는 float 누적이고(실측 `-0.029910810628287526`) 거래소는
# 수량 step 으로 양자화한다(실측 `0.029`, BTC linear step 0.001). 즉 **의도가 같아도
# 두 값은 절대 같아지지 않는다.** 정확 비교를 쓰면 이 counter 는 정상 상태에서 매 tick
# 발화해 아무것도 말하지 않게 된다.
#
# 실측 양자화 폭 = step 0.001 / 포지션 0.029 = **3.45%**. 문턱은 그보다 위여야 하고,
# 실제로 잡아야 할 부분체결(실측 0.001 vs 0.029 = 96.5%)보다는 한참 아래여야 한다.
_POSITION_SIZE_REL_TOL = Decimal("0.05")

# 방향 불일치를 **연속 2회** 봤는지 기억하는 자리. `last_strategy_state_report` JSONB 에
# 얹으므로 **마이그레이션이 없다.** `run_live` 도 그 dict 에 자기 키를 얹으므로
# (`pending_orders` / `window_bars` 등) 관행에 맞고, 밑줄 접두어로 엔진 산출물이 아님을
# 표시한다. 엔진 키와 충돌하면 그 순간 판정이 조용히 틀리므로 이름을 겹치게 두지 마라.
_DIRECTION_MISMATCH_KEY = "_qb_direction_mismatch_seen"

# 거래소를 못 읽어 **판정 자체를 못 한** 경우. "불일치 없음"(None)과 반드시 구분해야 한다 —
# 둘을 합치면 REST 가 한 번 흔들릴 때마다 직전 strike 가 지워져, 진짜 지속 발산이
# 영원히 2회차에 도달하지 못한다(가드가 조용히 무력화된다).
_PROBE_FAILED = "probe_failed"


def _net_position_size(positions: Sequence[Any]) -> Decimal:
    """거래소 포지션 목록 → 부호 있는 순포지션(long 양수 / short 음수).

    조건부 reconciler 의 사이징과 발산 감지가 **같은 산술**을 써야 한다. 둘이 갈리면
    한쪽이 발산이라 부르는 상태를 다른 쪽이 정상으로 사이징한다.
    """
    net = Decimal("0")
    for position in positions:
        if position.side == "long":
            net += position.size
        elif position.side == "short":
            net -= position.size
        else:
            raise ValueError(f"unknown position side: {position.side!r}")
    return net


def _classify_position_divergence(engine: Decimal, exchange: Decimal) -> str | None:
    """엔진이 믿는 포지션과 거래소 순포지션의 불일치를 분류한다. 일치하면 None.

    ★`direction` 만 fail-closed 대상이다. 엔진이 롱을 믿는데 거래소가 숏이면 엔진의
    close 는 **거래소 포지션과 같은 방향** 주문이 되고, `reduce_only=True` 하나가
    포지션 증가를 막는 유일한 방벽이 된다(실측 `110017 reduce-only order has same
    side` 4건). 나머지 갈래는 관측만 한다 — `engine_only` 는 유령 포지션이라 close 가
    무해하게 거절되고, `size` 는 부분체결·수량 step 의 정상 결과일 수 있으며,
    양쪽을 죽이면 이 스프린트가 고치려는 상태에서 세션이 상시 사망한다.
    """
    engine_flat = abs(engine) < _POSITION_DUST
    exchange_flat = abs(exchange) < _POSITION_DUST
    if engine_flat and exchange_flat:
        return None
    if engine_flat:
        return "exchange_only"
    if exchange_flat:
        return "engine_only"
    if (engine > 0) != (exchange > 0):
        return "direction"
    larger = max(abs(engine), abs(exchange))
    if abs(engine - exchange) > larger * _POSITION_SIZE_REL_TOL:
        return "size"
    return None


def _to_engine_position(strategy_state_report: dict[str, Any]) -> Decimal | None:
    """`to_report()["position_size"]` → Decimal. 읽을 수 없으면 None(감지 건너뜀).

    `position_size` 는 float 누적이라(`event_loop.py:506` 주석) Decimal 경계에서 한 번만
    변환한다. NaN/Inf 는 warmup 지표가 낼 수 있으므로 비교에 넣지 않고 조용히 뺀다 —
    발산 판정의 입력이 비정상이면 그 판정 자체가 의미 없다.
    """
    raw = strategy_state_report.get("position_size")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return value if value.is_finite() else None


async def _detect_position_divergence(
    sess: Any,
    engine_position: Decimal,
    *,
    account_repo: Any,
) -> str | None:
    """엔진 포지션과 거래소 순포지션을 대조해 발산 갈래를 돌려준다.

    조회 실패는 None(fail-open) — 감지기가 거래소를 못 읽었다는 사실을 세션 사망으로
    바꾸지 않는다. 감지 못 한 발산은 close 거절로 여전히 드러난다.

    ★조회를 `_reconcile_conditional_entries` 의 것과 공유하지 않는 이유 — 그 함수는
    desired 도 로컬 주문도 없으면 **REST 를 열기 전에 조기 반환한다**(stop-entry 를 안
    쓰는 전략에 비용을 지우지 않으려는 의도적 계약). 그런데 유령 포지션이 남는 상태가
    바로 그 상태다(진입은 이미 sim 에서 체결됐고 pending 이 없다). 거기에 얹으면 감지가
    가장 필요한 순간에 정확히 눈을 감는다. 그래서 tick 당 조회 1회를 더 쓴다.
    """
    from src.trading.encryption import EncryptionService
    from src.trading.providers import BybitFuturesProvider
    from src.trading.services.account_service import ExchangeAccountService

    try:
        bybit_provider = BybitFuturesProvider()
        exchange_svc = ExchangeAccountService(
            repo=account_repo,
            crypto=EncryptionService(settings.trading_encryption_keys),
            bybit_futures_provider=bybit_provider,
        )
        creds = await exchange_svc.get_credentials_for_order(sess.exchange_account_id)
        positions = await bybit_provider.fetch_open_positions(creds, sess.symbol)
        exchange_position = _net_position_size(positions)
    except Exception:
        qb_live_position_divergence_total.labels(category=_PROBE_FAILED).inc()
        logger.warning(
            "live_signal_position_divergence_probe_failed",
            exc_info=True,
            extra={"session_id": str(sess.id), "symbol": sess.symbol},
        )
        # ★None(일치)이 아니라 `_PROBE_FAILED`(모름)를 돌려준다. 호출부가 이걸 보고
        # 직전 strike 를 **보존**한다. None 으로 돌리면 조용히 strike 를 지운다.
        return _PROBE_FAILED

    category = _classify_position_divergence(engine_position, exchange_position)
    if category is not None:
        logger.warning(
            "live_signal_position_divergence",
            extra={
                "session_id": str(sess.id),
                "symbol": sess.symbol,
                "category": category,
                "engine_position": str(engine_position),
                "exchange_position": str(exchange_position),
            },
        )
    return category


def _classify_live_divergence(msg: str) -> str:
    """BL-362 — interpreter PineRuntimeError 메시지 → bounded category (≤5 runtime 값).

    W1 `_classify_trailing_failure`(trading.py) 미러: raw 는 절대 metric label 에 안 싣고
    category enum 만. case-insensitive substring ladder — interpreter.py 의 모든 raise-site
    메시지 prefix 대조. 미분류는 unexpected.
    """
    low = msg.lower()
    if "undefined name" in low:
        return "undefined_name"
    if "attribute access not supported" in low:
        return "unsupported_attr"
    if (
        "not supported in current scope" in low
        or "function not supported" in low
        or "method not supported" in low
    ):
        return "unsupported_call"
    if low.startswith("unsupported "):
        return "unsupported_node"
    if "not supported" in low:
        # 일반 구조적 미지원 (Subscript on non-Name / var·varip tuple destructuring 등).
        return "unsupported_node"
    return "unexpected"


async def _reconcile_conditional_entries(
    sess: Any,
    result: Any,
    parsed_settings: StrategySettings,
    sm: Any,
    *,
    bar_time: datetime,
    market_orders_in_flight: bool,
    fallback_reference_price: Decimal | None = None,
) -> None:
    """조건부 진입 desired 상태를 안전하게 거래소 resting 주문으로 수렴시킨다.

    ★`market_orders_in_flight` 가 True 면 이번 tick 은 건너뛴다. 이 함수는 dispatch
    태스크를 `apply_async` 한 **직후**에 불리므로, 그 시장가 진입/청산이 아직 거래소에
    반영되기 전의 포지션을 읽는다. 그 값으로 사이징하면 초과 수량 주문이 나간다 -
    실측 예: 청산 대기 중 포지션 +1 에서 target -0.5 를 보면 수량 1.5 를 등재하고,
    청산이 체결된 뒤 돌파가 오면 의도의 3배가 열린다. 한 tick 늦추는 편이 낫다.
    """
    if market_orders_in_flight:
        qb_live_conditional_reconcile_errors_total.labels(stage="deferred_market_inflight").inc()
        return
    try:
        from src.tasks.celery_app import get_ccxt_provider_for_worker
        from src.trading.dependencies import _CeleryOrderDispatcher, _StrategySessionsAdapter
        from src.trading.encryption import EncryptionService
        from src.trading.exit_attribution import parse_our_order_link_id
        from src.trading.kill_switch import (
            CumulativeLossEvaluator,
            DailyLossEvaluator,
            KillSwitchEvaluator,
            KillSwitchService,
        )
        from src.trading.providers import BybitFuturesProvider, _to_bybit_linear_symbol
        from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
        from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
        from src.trading.repositories.live_signal_session_repository import (
            LiveSignalSessionRepository,
        )
        from src.trading.repositories.order_repository import OrderRepository
        from src.trading.schemas import OrderRequest
        from src.trading.services.account_service import ExchangeAccountService
        from src.trading.services.conditional_entry_planner import (
            RestingConditionalEntry,
            build_conditional_entry_key,
            build_market_converted_entry_key,
            parse_conditional_entry_key,
            plan_reconcile,
        )
        from src.trading.services.order_service import OrderService

        async with sm() as session:
            order_repo = OrderRepository(session)
            local_orders = await order_repo.list_resting_conditional_entries(
                sess.strategy_id, sess.exchange_account_id
            )
            desired = list(result.pending_orders)

            # stop-entry를 쓰지 않는 전략에는 DB 조회 하나 외 비용을 지우고 REST를 절대 열지 않는다.
            if not desired and not local_orders:
                return

            account_repo = ExchangeAccountRepository(session)
            kse_repo = KillSwitchEventRepository(session)
            active_kill_switch = await kse_repo.get_active(
                strategy_id=sess.strategy_id, account_id=sess.exchange_account_id
            )
            cancel_reason = "desired_removed"
            if not sess.is_active:
                desired = []
                cancel_reason = "session_inactive"
            elif active_kill_switch is not None:
                desired = []
                cancel_reason = "kill_switch"

            bybit_provider = BybitFuturesProvider()
            exchange_service = ExchangeAccountService(
                repo=account_repo,
                crypto=EncryptionService(settings.trading_encryption_keys),
                bybit_futures_provider=bybit_provider,
            )
            creds = await exchange_service.get_credentials_for_order(sess.exchange_account_id)

            actual_by_order_id: dict[str, RestingConditionalEntry] = {}
            for order in local_orders:
                parsed_key = parse_conditional_entry_key(order.idempotency_key)
                if parsed_key is None or parsed_key[0] != sess.id or order.trigger_price is None:
                    continue
                actual_by_order_id[str(order.id)] = RestingConditionalEntry(
                    trade_id=parsed_key[1],
                    order_id=str(order.id),
                    exchange_order_id=order.exchange_order_id,
                    stop_price=order.trigger_price,
                    quantity=order.quantity,
                    side=order.side.value,
                    trigger_direction=order.trigger_direction,
                    reduce_only=order.reduce_only,
                )

            exchange_orders = await bybit_provider.fetch_open_conditional_orders(
                creds, sess.symbol, reduce_only=None
            )
            confirmed_order_ids: set[str] = set()
            for exchange_order in exchange_orders:
                linked_order_id = parse_our_order_link_id(exchange_order.order_link_id)
                if linked_order_id is None:
                    continue
                linked_order = await order_repo.get_by_id(linked_order_id)
                if (
                    linked_order is None
                    or linked_order.strategy_id != sess.strategy_id
                    or linked_order.exchange_account_id != sess.exchange_account_id
                    or linked_order.trigger_price is None
                    or linked_order.reduce_only
                ):
                    continue
                parsed_key = parse_conditional_entry_key(linked_order.idempotency_key)
                if parsed_key is None or parsed_key[0] != sess.id:
                    continue
                # 가격·수량은 거래소 echo가 아니라 우리가 저장한 요청값이 SSOT다.
                confirmed_order_ids.add(str(linked_order.id))
                actual_by_order_id[str(linked_order.id)] = RestingConditionalEntry(
                    trade_id=parsed_key[1],
                    order_id=str(linked_order.id),
                    exchange_order_id=exchange_order.order_id,
                    stop_price=linked_order.trigger_price,
                    quantity=linked_order.quantity,
                    side=linked_order.side.value,
                    trigger_direction=linked_order.trigger_direction,
                    reduce_only=exchange_order.reduce_only,
                )

            # BL-500 — 거래소 부재가 로컬 행을 이긴다.
            #
            # `actual` 은 로컬 `pending`/`submitted` 행으로 먼저 채우고 거래소 응답으로
            # 덮어쓰기만 했다(이중 등재 봉인, D4). 그래서 거래소엔 없고 DB 만 남은
            # 주문이 desired 와 일치하면 계획기가 "이미 등재됨" 으로 보고 재등재하지
            # 않아 그 trade_id 가 **영구 no-op** 이 된다.
            #
            # ★"목록에 없다" 는 부재의 증거로 **부족하다.** 세 가지가 겹친다.
            #   (1) 주문 조회와 포지션 조회는 원자적 스냅샷이 아니다 — 방금 트리거된
            #       주문은 open-order 에서 먼저 사라지고 포지션에는 늦게 뜬다.
            #   (2) 응답이 열화(레이트리밋·부분 응답)됐을 수 있고, 그러면 살아 있는
            #       주문 전체가 한 tick 에 "사라진" 것으로 보인다.
            #   (3) 이 함수의 다른 모든 열화 입력은 fail-closed 인데(정밀도 실패·취소
            #       실패·stand-down·시장가 지연) 여기만 "주문을 더 낸다" 방향이다.
            #
            # 그래서 후보마다 **거래소에 직접 물어** terminal 인지 확인한다. 확인하지
            # 못하면 그대로 둔다. `exchange_order_id` 가 아직 없는 in-flight 행은 물어볼
            # 대상 자체가 없으므로 건드리지 않는다(진짜 이중 등재 방어).
            #
            # ★상태 전이는 하지 않는다 — 그건 watchdog·`Reconciler` 책임이다. 여기서는
            #   `actual` 에서만 뺀다.
            fill_confirmed = False
            for order_id, resting in list(actual_by_order_id.items()):
                if order_id in confirmed_order_ids or resting.exchange_order_id is None:
                    continue
                try:
                    # orderId 조회에서는 필터가 느슨해도, 조건부 주문임을 명시해 client-id
                    # 조회 경로와 같은 StopOrder 계약을 유지한다.
                    probe = await bybit_provider.fetch_order(
                        creds, resting.exchange_order_id, sess.symbol, trigger=True
                    )
                except Exception:
                    qb_live_conditional_reconcile_errors_total.labels(
                        stage="exchange_missing_probe_failed"
                    ).inc()
                    logger.warning(
                        "live_conditional_reconcile_probe_failed",
                        extra={
                            "session_id": str(sess.id),
                            "order_id": order_id,
                            "exchange_order_id": resting.exchange_order_id,
                        },
                        exc_info=True,
                    )
                    continue
                if probe.status not in ("filled", "cancelled", "rejected"):
                    continue  # 거래소는 아직 살아 있다고 말한다. 목록 쪽이 열화였다.
                del actual_by_order_id[order_id]
                # 체결이 확인됐다면 위(`:387`)에서 찍을 포지션 스냅샷이 그 체결보다
                # 앞설 수 있다. 낡은 포지션으로 사이징하면 이중 포지션이 되므로 이번
                # tick 은 등재하지 않는다.
                if probe.status == "filled":
                    fill_confirmed = True
                else:
                    qb_live_conditional_reconcile_errors_total.labels(
                        stage="exchange_missing"
                    ).inc()
                logger.warning(
                    "live_conditional_reconcile_divergence",
                    extra={
                        "session_id": str(sess.id),
                        "order_id": order_id,
                        "exchange_order_id": resting.exchange_order_id,
                        "reason": "exchange_missing_resting_order",
                        "exchange_status": probe.status,
                    },
                )

            try:
                market_provider = get_ccxt_provider_for_worker()
                await market_provider.exchange.load_markets()
                market = market_provider.exchange.market(_to_bybit_linear_symbol(sess.symbol))
                precision = market.get("precision") if isinstance(market, dict) else None
                if not isinstance(precision, dict):
                    raise ValueError("conditional entry market precision is unavailable")
                qty_step = Decimal(str(precision["amount"]))
                price_tick = Decimal(str(precision["price"]))
                if (
                    not qty_step.is_finite()
                    or not price_tick.is_finite()
                    or qty_step <= Decimal("0")
                    or price_tick <= Decimal("0")
                ):
                    raise ValueError("conditional entry market precision is unavailable")
            except Exception:
                qb_live_conditional_reconcile_errors_total.labels(stage="precision").inc()
                logger.exception(
                    "live_conditional_reconcile_precision_failed",
                    extra={"session_id": str(sess.id), "symbol": sess.symbol},
                )
                return

            # ★계정 순포지션을 세션 target 에서 빼는 산술은 "이 계정·심볼의 포지션이 이
            # 세션 것뿐" 이라는 전제 위에 선다. 그 전제가 깨지는 경우가 둘이고 둘 다
            # 실주문을 파괴적으로 만든다.
            #   (a) hedge mode — long/short 가 동시에 열려 순포지션이 우리 사이징 모델과
            #       다른 의미가 된다.
            #   (b) 같은 계정·심볼에 다른 전략 세션 — 활성 세션 unique 키가
            #       `strategy_id` 를 포함하므로(`models.py` uq_live_sessions_active_unique)
            #       구조적으로 허용된다. 전략 A 가 +1 보유 중 전략 B 가 -1 을 목표하면
            #       B 는 수량 2 를 내 **A 의 포지션까지 닫고 반전**한다.
            # 두 경우 모두 stand-down 한다 — 새로 등재하지 않고 이미 올려둔 우리 조건부
            # 진입을 걷는다. 취소는 어느 경우에도 안전하고(포지션을 늘리지 않는다),
            # 남겨두면 그게 잘못된 전제로 체결된다.
            positions = await bybit_provider.fetch_open_positions(creds, sess.symbol)
            hedge_mode = len(positions) > 1 or any(
                position.position_idx not in (None, 0) for position in positions
            )
            session_repo = LiveSignalSessionRepository(session)
            shares_account_symbol = any(
                other.id != sess.id and other.symbol == sess.symbol
                for other in await session_repo.list_active_by_account(sess.exchange_account_id)
            )
            stand_down_reason = (
                "hedge_mode"
                if hedge_mode
                else "shared_account_symbol"
                if shares_account_symbol
                else None
            )
            current_position = Decimal("0")
            if stand_down_reason is not None:
                qb_live_conditional_reconcile_errors_total.labels(stage="positions").inc()
                logger.error(
                    "live_conditional_reconcile_divergence",
                    extra={"session_id": str(sess.id), "reason": stand_down_reason},
                )
                desired = []
                cancel_reason = stand_down_reason
            else:
                current_position = _net_position_size(positions)

            reference_price = fallback_reference_price
            allow_market_conversion = False
            if desired:
                exchange_reference_price = await bybit_provider.fetch_last_price(creds, sess.symbol)
                if exchange_reference_price is None:
                    qb_live_conditional_guard_total.labels(outcome="reference_unavailable").inc()
                    logger.warning(
                        "live_conditional_reconcile_divergence",
                        extra={
                            "session_id": str(sess.id),
                            "symbol": sess.symbol,
                            "reason": "reference_price_unavailable",
                        },
                    )
                else:
                    reference_price = exchange_reference_price
                    allow_market_conversion = True

            max_breach_pct = (
                Decimal(str(parsed_settings.max_trigger_breach_pct))
                if parsed_settings.max_trigger_breach_pct is not None
                else None
            )
            plan = plan_reconcile(
                desired=desired,
                actual=tuple(actual_by_order_id.values()),
                current_position=current_position,
                qty_step=qty_step,
                price_tick=price_tick,
                reference_price=reference_price,
                max_breach_pct=max_breach_pct,
                allow_market_conversion=allow_market_conversion,
            )
            for divergence in plan.divergences:
                if divergence["reason"] == "breach_exceeds_cap":
                    qb_live_conditional_guard_total.labels(outcome="breach_capped").inc()
                elif (
                    divergence["reason"] == "trigger_already_breached"
                    and divergence.get("had_resting") is True
                ):
                    qb_live_conditional_guard_total.labels(outcome="breach_with_resting").inc()
                logger.warning(
                    "live_conditional_reconcile_divergence",
                    extra={"session_id": str(sess.id), **divergence},
                )

            cancel_failed = False
            cancel_raced = False
            desired_trade_ids = {entry.trade_id for entry in desired}
            for entry in plan.to_cancel:
                try:
                    if entry.exchange_order_id is None:
                        rows = await order_repo.transition_pending_to_cancelled(
                            UUID(entry.order_id), cancelled_at=datetime.now(UTC)
                        )
                        if rows != 1:
                            # BL-499 — 실행 워커가 `pending → submitted` 를 먼저 커밋했다.
                            # 진짜 실패가 아니라 **경합 패배**다. 예외로 만들면 스택과
                            # `stage="cancel"` 오류 metric 이 실패와 구분되지 않고, 그
                            # 결과로 "이 경합이 실제로 나는가" 를 원장에서 물을 수 없다.
                            # (preflight 가 이 구분 부재 때문에 잘못된 결론을 냈다.)
                            fresh = await order_repo.get_state_and_exchange_id_fresh(
                                UUID(entry.order_id)
                            )
                            if fresh is not None and fresh[0] != OrderState.pending:
                                state, exchange_id = fresh
                                # `submitted` + exchange id 없음은 janitor가 30분 뒤 거래소
                                # client-id 조회로 확인한다. 즉시 경합을 재시도하지는 않는다.
                                deferred = state == OrderState.submitted and exchange_id is None
                                cancel_raced = True
                                qb_live_conditional_reconcile_errors_total.labels(
                                    stage="cancel_deferred" if deferred else "cancel_raced"
                                ).inc()
                                log = logger.warning
                                log(
                                    "live_conditional_reconcile_cancel_deferred_to_janitor"
                                    if deferred
                                    else "live_conditional_reconcile_cancel_raced",
                                    extra={
                                        "session_id": str(sess.id),
                                        "order_id": entry.order_id,
                                        "observed_state": state.value,
                                        "has_exchange_order_id": exchange_id is not None,
                                        "janitor_delay_minutes": (
                                            _conditional_entry_janitor_delay_minutes()
                                            if deferred
                                            else None
                                        ),
                                    },
                                )
                                continue
                    else:
                        await bybit_provider.cancel_order(
                            creds, entry.exchange_order_id, sess.symbol
                        )
                        rows = await order_repo.transition_to_cancelled(
                            UUID(entry.order_id), cancelled_at=datetime.now(UTC)
                        )
                    if rows != 1:
                        raise RuntimeError("conditional entry cancel lost its state transition")
                    await order_repo.commit()
                    # OrderService.execute 가 생성 시 inc 했으므로 terminal 전이에서 dec.
                    # 조건부 진입은 교체·세션 종료로 반복 취소되므로 빠뜨리면 active gauge 가
                    # 단조 증가해 운영 경보가 왜곡된다(표준 취소 경로는 trading.py 가 dec 한다).
                    qb_active_orders.dec()
                    reason = (
                        cancel_reason
                        if not desired_trade_ids
                        else "replaced"
                        if entry.trade_id in desired_trade_ids
                        else "desired_removed"
                    )
                    qb_live_conditional_cancelled_total.labels(reason=reason).inc()
                except Exception:
                    cancel_failed = True
                    qb_live_conditional_reconcile_errors_total.labels(stage="cancel").inc()
                    logger.exception(
                        "live_conditional_reconcile_cancel_failed",
                        extra={"session_id": str(sess.id), "order_id": entry.order_id},
                    )
            if cancel_failed:
                return
            if fill_confirmed:
                # 위에서 거래소가 체결을 확인해 준 조건부 진입이 있다. 이번 tick 의
                # `current_position` 은 그 체결보다 앞선 스냅샷일 수 있으므로 등재하지
                # 않는다. 다음 tick 이 새 포지션으로 다시 계획한다.
                return
            if cancel_raced:
                # ★패배해도 이번 tick 의 등재는 하지 않는다(fail-closed 유지).
                #   `current_position` 은 취소 루프보다 **먼저** 찍은 스냅샷이라, 패배한
                #   주문이 그 사이 체결되면 낡은 포지션 위에서 사이징한 주문이 나간다.
                #   다음 tick 이 새 포지션·거래소 스냅샷으로 다시 계획하면 된다.
                return
            to_place = plan.to_place
            if not to_place:
                return

            evaluators: list[KillSwitchEvaluator] = [
                CumulativeLossEvaluator(
                    order_repo,
                    threshold_percent=settings.kill_switch_cumulative_loss_percent,
                    capital_base=settings.kill_switch_capital_base_usd,
                    balance_provider=exchange_service,
                ),
                DailyLossEvaluator(
                    order_repo,
                    threshold_usd=settings.kill_switch_daily_loss_usd,
                ),
            ]
            order_service = OrderService(
                session=session,
                repo=order_repo,
                dispatcher=_CeleryOrderDispatcher(),
                kill_switch=KillSwitchService(evaluators=evaluators, events_repo=kse_repo),
                sessions_port=_StrategySessionsAdapter(session),
                exchange_service=exchange_service,
            )
            for placement_index, planned_entry in enumerate(to_place):
                try:
                    breach_pct: Decimal | None = None
                    if planned_entry.as_market:
                        interval_seconds = {
                            "1m": 60,
                            "5m": 300,
                            "15m": 900,
                            "1h": 3600,
                        }.get(str(sess.interval))
                        if interval_seconds is None:
                            # 미지 interval은 전환 창을 해석할 수 없다. 창 크기의 폴백은
                            # 전환 허용 근거가 아니므로 시장가 전환만 명시적으로 막는다.
                            qb_live_conditional_guard_total.labels(
                                outcome="convert_suppressed"
                            ).inc()
                            logger.warning(
                                "live_conditional_reconcile_market_convert_suppressed",
                                extra={
                                    "session_id": str(sess.id),
                                    "trade_id": planned_entry.trade_id,
                                    "reason": "unknown_interval",
                                    "interval": str(sess.interval),
                                },
                            )
                            continue
                        since = bar_time - timedelta(seconds=interval_seconds * 2)
                        if await order_repo.has_recent_market_converted_entry(
                            exchange_account_id=sess.exchange_account_id,
                            strategy_id=sess.strategy_id,
                            session_id=sess.id,
                            since=since,
                        ):
                            qb_live_conditional_guard_total.labels(
                                outcome="convert_suppressed"
                            ).inc()
                            logger.warning(
                                "live_conditional_reconcile_market_convert_suppressed",
                                extra={
                                    "session_id": str(sess.id),
                                    "trade_id": planned_entry.trade_id,
                                    "since": since.isoformat(),
                                },
                            )
                            continue

                        conversion_reference_price = await bybit_provider.fetch_last_price(
                            creds, sess.symbol
                        )
                        if conversion_reference_price is None:
                            qb_live_conditional_guard_total.labels(
                                outcome="reference_unavailable"
                            ).inc()
                            logger.warning(
                                "live_conditional_reconcile_market_convert_skipped",
                                extra={
                                    "session_id": str(sess.id),
                                    "trade_id": planned_entry.trade_id,
                                    "reason": "reference_price_unavailable",
                                },
                            )
                            continue
                        still_breached = (
                            planned_entry.direction == "long"
                            and planned_entry.trigger_price <= conversion_reference_price
                        ) or (
                            planned_entry.direction == "short"
                            and planned_entry.trigger_price >= conversion_reference_price
                        )
                        if not still_breached:
                            qb_live_conditional_guard_total.labels(outcome="breach_reverted").inc()
                            logger.warning(
                                "live_conditional_reconcile_market_convert_skipped",
                                extra={
                                    "session_id": str(sess.id),
                                    "trade_id": planned_entry.trade_id,
                                    "reason": "breach_reverted",
                                    "stop_price": str(planned_entry.trigger_price),
                                    "reference_price": str(conversion_reference_price),
                                },
                            )
                            continue
                        breach_pct = (
                            abs(conversion_reference_price - planned_entry.trigger_price)
                            / conversion_reference_price
                            * Decimal("100")
                        )
                        if max_breach_pct is not None and breach_pct > max_breach_pct:
                            qb_live_conditional_guard_total.labels(outcome="breach_capped").inc()
                            logger.warning(
                                "live_conditional_reconcile_divergence",
                                extra={
                                    "session_id": str(sess.id),
                                    "trade_id": planned_entry.trade_id,
                                    "reason": "breach_exceeds_cap",
                                    "direction": planned_entry.direction,
                                    "stop_price": str(planned_entry.trigger_price),
                                    "reference_price": str(conversion_reference_price),
                                    "breach_pct": str(breach_pct),
                                    "max_breach_pct": str(max_breach_pct),
                                },
                            )
                            continue
                    request = OrderRequest(
                        strategy_id=sess.strategy_id,
                        exchange_account_id=sess.exchange_account_id,
                        symbol=sess.symbol,
                        side=OrderSide(planned_entry.side),
                        type=OrderType.market,
                        quantity=planned_entry.quantity,
                        price=None,
                        trigger_price=None
                        if planned_entry.as_market
                        else planned_entry.trigger_price,
                        trigger_direction=(
                            None if planned_entry.as_market else planned_entry.trigger_direction
                        ),
                        trigger_by=None if planned_entry.as_market else "LastPrice",
                        reduce_only=False,
                        leverage=parsed_settings.leverage,
                        margin_mode=parsed_settings.margin_mode,
                    )
                    idempotency_key = (
                        build_market_converted_entry_key(
                            sess.id,
                            planned_entry.trade_id,
                            bar_time,
                            planned_entry.trigger_price,
                            planned_entry.quantity,
                        )
                        if planned_entry.as_market
                        else build_conditional_entry_key(
                            sess.id,
                            planned_entry.trade_id,
                            bar_time,
                            planned_entry.trigger_price,
                            planned_entry.quantity,
                        )
                    )
                    if idempotency_key is None:
                        # 되짚지 못할 key 로 발주하면 우리 주문을 영원히 남의 것으로 본다.
                        qb_live_conditional_reconcile_errors_total.labels(
                            stage="unrepresentable_key"
                        ).inc()
                        continue
                    await order_service.execute(
                        request,
                        idempotency_key=idempotency_key,
                        body_hash=None,
                    )
                    qb_live_conditional_placed_total.labels(direction=planned_entry.direction).inc()
                    qb_live_conditional_guard_total.labels(
                        outcome=(
                            "market_converted" if planned_entry.as_market else "conditional_placed"
                        )
                    ).inc()
                    if planned_entry.as_market:
                        logger.warning(
                            "live_conditional_reconcile_divergence",
                            extra={
                                "session_id": str(sess.id),
                                "trade_id": planned_entry.trade_id,
                                "reason": "market_converted",
                                "stop_price": str(planned_entry.trigger_price),
                                "breach_pct": str(breach_pct),
                            },
                        )
                        # 시장가 전환은 포지션 스냅샷을 즉시 낡게 만든다. 이 tick의 나머지
                        # 등재는 다음 tick의 새 포지션 스냅샷까지 미룬다.
                        remaining_count = len(to_place) - placement_index - 1
                        for _ in range(remaining_count):
                            qb_live_conditional_reconcile_errors_total.labels(
                                stage="deferred_after_market_convert"
                            ).inc()
                        if remaining_count:
                            logger.warning(
                                "live_conditional_reconcile_deferred_after_market_convert",
                                extra={
                                    "session_id": str(sess.id),
                                    "remaining_count": remaining_count,
                                },
                            )
                        return
                except (BalanceUnverified, MinNotionalNotMet, NotionalExceeded):
                    qb_live_conditional_reconcile_errors_total.labels(
                        stage=(
                            "market_place_gate"
                            if planned_entry.as_market
                            else "conditional_place_gate"
                        )
                    ).inc()
                    logger.exception(
                        "live_conditional_reconcile_place_failed",
                        extra={"session_id": str(sess.id), "trade_id": planned_entry.trade_id},
                    )
                except Exception:
                    qb_live_conditional_reconcile_errors_total.labels(
                        stage="market_place" if planned_entry.as_market else "conditional_place"
                    ).inc()
                    logger.exception(
                        "live_conditional_reconcile_place_failed",
                        extra={"session_id": str(sess.id), "trade_id": planned_entry.trade_id},
                    )
    except Exception:
        qb_live_conditional_reconcile_errors_total.labels(stage="reconcile").inc()
        logger.exception("live_conditional_reconcile_failed", extra={"session_id": str(sess.id)})


async def _alert_live_divergence(
    *,
    session_id: UUID,
    stage: str,
    category: str,
    raw_msg: str,
    error_count: int,
    last_error_bar: int,
    reason: str = _DIVERGENCE_REASON,
    title: str = _DIVERGENCE_TITLE,
) -> None:
    """BL-362 — 발산 감지 → 세션 자동 비활성화 critical alert (무신호 차단 고지).

    raw_msg 는 사용자 본인 Pine 심볼/구조 메시지(거래소 시크릿 아님 — interpreter raise-site
    전수조사로 시장데이터·문자열 리터럴 미포함 검증) → actionable 차원에서 포함하되 [:200]
    truncate(defense-in-depth). 원본 전체·stack 은 호출부 logger.error 가 기록.

    G2 P2#3 — kill_switch `_send_alert_safely` 미러: send 예외는 swallow + log (alert 실패가
    fire-and-forget task 를 unretrieved-exception 으로 남기거나 흐름 깨면 안 됨).
    """
    try:
        await send_rule_alert(
            settings,
            channel=AlertChannel.both,
            title=title,
            message=(
                f"{reason}({stage}/{category}) 감지 — 세션을 "
                "비활성화했습니다(오신호 dispatch 차단, 고정 SL/포지션은 거래소측 유지). "
                f"전략 수정 후 재활성화 필요. detail: {raw_msg[:200]}"
            ),
            context={
                "session_id": str(session_id)[:8],
                "stage": stage,
                "category": category,
                "error_count": str(error_count),
                "last_error_bar": str(last_error_bar),
            },
        )
    except Exception as exc:
        logger.warning(
            "live_signal_divergence_alert_failed",
            extra={"session_id": str(session_id)[:8], "error": str(exc)},
        )


def _fire_divergence_alert(
    *,
    session_id: UUID,
    stage: str,
    category: str,
    raw_msg: str,
    error_count: int,
    last_error_bar: int,
    reason: str | None = None,
) -> None:
    """fire-and-forget alert. `_evaluate_session_inner` 는 이미 persistent `_WORKER_LOOP`
    안이므로 `create_task` + `track_pending_alert` (kill_switch.py 패턴).
    `run_in_worker_loop` 금지 (nested ban §9.4).

    사유와 제목은 `_PREFLIGHT_CATEGORY_METADATA` 에서 끌어온다. 문자열 동등 비교로
    override 를 판정하면 리터럴 하나만 어긋나도 조용히 멈춰 그럴듯하지만 틀린 사유가
    나가므로, 미지정(None)일 때만 메타데이터/기본값으로 채운다.

    ★제목도 함께 바꾼다 — 카운터가 페이징을 안 해도 제목이 "divergence" 면 사람은
    제목을 보고 호출된다. 계약을 반만 고치는 셈이다.
    """
    metadata = _PREFLIGHT_CATEGORY_METADATA.get(category)
    pageable = metadata[0] if metadata is not None else True
    if reason is None:
        reason = metadata[1] if metadata is not None else _DIVERGENCE_REASON
    title = _DIVERGENCE_TITLE if pageable else f"Live signal 세션 자동 비활성화 — {reason}"
    task = asyncio.create_task(
        _alert_live_divergence(
            session_id=session_id,
            stage=stage,
            category=category,
            raw_msg=raw_msg,
            error_count=error_count,
            last_error_bar=last_error_bar,
            reason=reason,
            title=title,
        )
    )
    track_pending_alert(task)


async def _heartbeat_extend(lock: RedisLock, *, period_s: float, ttl_ms: int) -> None:
    """RedisLock heartbeat — TTL 만료 전 token CAS 로 PEXPIRE.

    codex G.0 P1 #4 fix: ttl_ms=60_000 + 20s 마다 heartbeat. evaluate task 가 60s
    이상 걸려도 lock 안 풀림. 호출자가 finally 에서 task.cancel() 의무.
    extend 실패 (token mismatch) 시 즉시 종료 — 다른 worker 가 lock 빼앗은 상황.
    """
    try:
        while True:
            await asyncio.sleep(period_s)
            ok = await lock.extend(ttl_ms)
            if not ok:
                logger.warning(
                    "live_signal_heartbeat_extend_failed",
                    extra={"key": getattr(lock, "_key", None)},
                )
                return
    except asyncio.CancelledError:
        return


# Sprint 18 BL-080 prefork-safe engine factory — `_worker_engine.py` 단일 SSOT.
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402


def _enqueue_conditional_entry_sweep() -> None:
    """비활성화 직후 고아 조건부 진입 취소를 best-effort로 요청한다."""
    try:
        sweep_conditional_entries_task.apply_async(expires=240)
    except Exception:
        logger.exception("conditional_entry_sweep_enqueue_failed")


# ---------------------------------------------------------------------------
# Task #1: evaluate_live_signals_task (Beat 1분 fire)
# ---------------------------------------------------------------------------


@shared_task(name="live_signal.evaluate_all", max_retries=0)  # type: ignore[untyped-decorator]
def evaluate_live_signals_task() -> dict[str, Any]:
    """Sprint 26 — 1분 Beat fire. interval 별 due session 평가.

    Beat schedule entry: `evaluate-live-signals` (60s schedule, expires=50).
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_evaluate_all())


async def _async_evaluate_all() -> dict[str, Any]:
    """due session list → 각 session 별 _evaluate_session_inner 순차 실행.

    sequential 처리: 5건 quota cap 안에서 충분 — 동시성 늘리려면 asyncio.gather
    가능하나 asyncpg pool / Redis lock pool 소모 증가하여 보수적 채택.
    """
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = LiveSignalSessionRepository(session)
            due_sessions = list(await repo.list_active_due(now=datetime.now(UTC)))
            event_repo = LiveSignalEventRepository(session)
            pending = await event_repo.list_pending(limit=10_000)
            qb_live_signal_outbox_pending_gauge.set(len(pending))

        if not due_sessions:
            return {"due_count": 0, "evaluated": 0}

        results: list[dict[str, Any]] = []
        for sess in due_sessions:
            # Sprint 26 Phase D fix — interval/status 가 String 컬럼이라 SQLAlchemy 가
            # raw str 반환. StrEnum cast 가 자동 안 되므로 str() 으로 정규화.
            # G3 — per-session 격리: 한 세션의 uncaught 오류(예: analyze_coverage 같은
            # pre-claim 호출)가 batch 전체를 abort 하여 이후 세션을 starve 시키지 않도록 방어.
            try:
                res = await _async_evaluate_session(sess.id, str(sess.interval))
            except Exception:
                logger.exception(
                    "live_signal_eval_session_error", extra={"session_id": str(sess.id)}
                )
                qb_live_signal_skipped_total.labels(reason="eval_error").inc()
                res = {"error": "eval_error"}
            results.append({"session_id": str(sess.id), **res})

        return {"due_count": len(due_sessions), "evaluated": len(results), "results": results}
    finally:
        await engine.dispose()


async def _async_evaluate_session(session_id: UUID, interval_value: str) -> dict[str, Any]:
    """단일 session 평가 — RedisLock + heartbeat + per-call engine.

    interval_value 는 metric label cardinality cap 위해 caller 에서 str 로 전달.
    """
    started = time.monotonic()
    lock = RedisLock(f"live:eval:{session_id}", ttl_ms=60_000)
    heartbeat: asyncio.Task[None] | None = None
    try:
        async with lock as acquired:
            if not acquired:
                qb_live_signal_skipped_total.labels(reason="contention").inc()
                return {"skipped": "contention"}

            heartbeat = asyncio.create_task(_heartbeat_extend(lock, period_s=20.0, ttl_ms=60_000))
            try:
                outcome = await _evaluate_session_inner(session_id, interval_value)
            finally:
                heartbeat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat
            return outcome
    finally:
        qb_live_signal_eval_duration_seconds.labels(interval=interval_value).observe(
            time.monotonic() - started
        )


async def _evaluate_session_inner(session_id: UUID, interval_value: str) -> dict[str, Any]:
    """Lock 안에서 실행되는 핵심 평가 로직.

    Flow:
    1. session fetch + active 검증
    2. strategy + StrategySettings.model_validate (P2 #4)
    3. account + Bybit Demo 강제 (P2 #1)
    4. CCXTProvider.fetch_ohlcv(limit_bars=300, ...) (P1 #6)
    5. last_bar_time 비교 → no new bar skip
    6. try_claim_bar winner-only (P2 #3)
    7. run_live (warmup replay, Option B)
    8. transactional outbox: events INSERT + state upsert + session.last_evaluated commit (P1 #3)
    9. 신규 INSERT 된 event 만 dispatch task apply_async
    """
    from src.strategy.pine_v2.event_loop import run_live
    from src.strategy.repository import StrategyRepository
    from src.tasks.celery_app import get_ccxt_provider_for_worker
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            sess_repo = LiveSignalSessionRepository(session)
            event_repo = LiveSignalEventRepository(session)
            account_repo = ExchangeAccountRepository(session)
            strategy_repo = StrategyRepository(session)

            # 1. session fetch
            sess = await sess_repo.get_by_id(session_id)
            if sess is None or not sess.is_active:
                qb_live_signal_skipped_total.labels(reason="session_inactive").inc()
                return {"skipped": "session_inactive"}

            # 2. strategy + settings validate (P2 #4)
            strategy = await strategy_repo.find_by_id_and_owner(sess.strategy_id, sess.user_id)
            if strategy is None:
                qb_live_signal_skipped_total.labels(reason="strategy_missing").inc()
                return {"skipped": "strategy_missing"}
            try:
                parsed_settings: StrategySettings | None = validate_strategy_settings(
                    strategy.settings
                )
            except ValidationError as exc:
                qb_live_signal_skipped_total.labels(reason="invalid_settings").inc()
                logger.warning(
                    "live_signal_invalid_settings",
                    extra={"session_id": str(sess.id), "error": str(exc)},
                )
                return {"skipped": "invalid_settings"}
            if parsed_settings is None:
                qb_live_signal_skipped_total.labels(reason="invalid_settings").inc()
                return {"skipped": "settings_unset"}

            # 3. account + Bybit Demo 강제 (P2 #1)
            account = await account_repo.get_by_id(sess.exchange_account_id)
            if (
                account is None
                or account.exchange != ExchangeName.bybit
                or account.mode != ExchangeMode.demo
            ):
                qb_live_signal_skipped_total.labels(reason="non_demo_account").inc()
                return {"skipped": "non_demo_account"}

            # 3.5 BL-362 — coverage preflight (money-path fail-closed). backtest/service.py 와
            # 동일 게이트: 미지원 builtin(is_runnable=False) 또는 degraded(heikinashi/
            # request.security/timeframe.period — graceful 실행이나 결과 divergence) 감지 시
            # 세션 자동 비활성화. live 엔 allow_degraded_pine 동의 플래그 없음 → 하드 차단.
            # account/demo check 뒤에 배치 — non-demo 세션은 비활성화 아닌 skip 유지 (G1 P1#2).
            cov = analyze_coverage(strategy.pine_source)
            preflight_cat: str | None = None
            preflight_symbols: tuple[str, ...] = ()
            equity_baseline_usdt = sess.equity_baseline_usdt
            if not cov.is_runnable:
                preflight_cat, preflight_symbols = "coverage_unrunnable", cov.all_unsupported
            elif cov.has_degraded:
                preflight_cat, preflight_symbols = "degraded_unconsented", cov.degraded_calls
            # NaN/Infinity 를 먼저 걸러야 한다 — `Decimal('NaN') <= 0` 은 False 가 아니라
            # InvalidOperation 을 raise 한다(실측). 그리고 그건 "자본 소진"이 아니라
            # 애초에 쓸 수 없는 기준선이므로 equity_baseline_missing 으로 진단해야 맞다.
            elif (
                equity_baseline_usdt is None
                or equity_baseline_usdt.is_nan()
                or equity_baseline_usdt.is_infinite()
                or equity_baseline_usdt <= Decimal("0")
            ):
                preflight_cat = "equity_baseline_missing"
            if preflight_cat is not None:
                preflight_pageable, _, preflight_raw_msg = _PREFLIGHT_CATEGORY_METADATA[
                    preflight_cat
                ]
                if preflight_raw_msg is None:
                    preflight_raw_msg = ", ".join(preflight_symbols)[:200]
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:  # winner-only dedupe (동시 worker 2nd UPDATE rowcount=0)
                    _enqueue_conditional_entry_sweep()
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    if preflight_pageable:
                        qb_live_signal_divergence_total.labels(
                            stage="preflight", category=preflight_cat
                        ).inc()
                    qb_live_signal_skipped_total.labels(reason=preflight_cat).inc()
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="preflight",
                        category=preflight_cat,
                        raw_msg=preflight_raw_msg,
                        error_count=0,
                        last_error_bar=-1,
                    )
                    logger.error(
                        "live_signal_preflight_blocked",
                        extra={
                            "session_id": str(sess.id),
                            "category": preflight_cat,
                            "symbols": list(preflight_symbols),
                        },
                    )
                return {"deactivated": preflight_cat}

            # 4. CCXT fetch_ohlcv (P1 #6 closed-bar)
            #
            # ★BL-530 — 엔진이 재생하는 봉은 주문이 나가는 상품과 같아야 한다.
            # `CCXTProvider` 는 `defaultType: "spot"` 이라 `sess.symbol`("BTC/USDT")을 그대로
            # 넘기면 **스팟** 봉이 온다. 그런데 주문은 `BybitFuturesProvider`(defaultType
            # "linear")로 **무기한선물**에 나간다. 두 상품 가격은 붙어 있지 않아(실측 스팟이
            # perp 보다 ~40 USDT / 0.066% 높음) 시뮬은 스팟 고가로 매수 스톱을 체결하는데
            # 거래소 perp 는 그 근처도 안 간다 → 엔진만 포지션을 믿는 유령 진입이 생기고,
            # 그 포지션의 close 는 전량 거절된다(실측 46/51 이 이 갈래). 방향까지 어긋나면
            # reduce-only 하나가 반대 방향 포지션 증가를 막는 유일한 방벽이 된다.
            #
            # ★`sess.symbol` 자체는 canonical 로 **불변**이다 — 주문 라우팅·세션 스코프·
            # 원장 매칭이 전부 그 값에 묶여 있다. 바꾸는 것은 이 fetch 인자뿐이다.
            provider = get_ccxt_provider_for_worker()
            ohlcv_rows = await provider.fetch_ohlcv(
                to_ccxt_perpetual_symbol(sess.symbol), str(sess.interval), limit_bars=300
            )
            if not ohlcv_rows:
                qb_live_signal_evaluated_total.labels(
                    interval=interval_value, outcome="no_new_bar"
                ).inc()
                return {"skipped": "empty_ohlcv"}

            # 5. warmup 창의 첫/마지막 bar → no new bar skip + catch-up 범위 판정
            window_start = datetime.fromtimestamp(int(ohlcv_rows[0][0]) / 1000, tz=UTC)
            last_bar_ms = int(ohlcv_rows[-1][0])
            last_bar_time = datetime.fromtimestamp(last_bar_ms / 1000, tz=UTC)
            last_evaluated_bar_time = sess.last_evaluated_bar_time
            if last_evaluated_bar_time is not None and last_bar_time <= last_evaluated_bar_time:
                qb_live_signal_evaluated_total.labels(
                    interval=interval_value, outcome="no_new_bar"
                ).inc()
                return {"skipped": "no_new_bar"}
            emit_from_bar_time: datetime | None = None
            requires_gap_resync = False
            if last_evaluated_bar_time is not None:
                elapsed = last_bar_time - last_evaluated_bar_time
                if elapsed <= _MAX_CATCHUP_WALL_CLOCK_GAP:
                    emit_from_bar_time = last_evaluated_bar_time
                else:
                    requires_gap_resync = True

            carry_pnl, _ = await event_repo.sum_realized_pnl_before(sess.id, bar_time=window_start)
            assert equity_baseline_usdt is not None  # 위 preflight가 None을 이미 비활성화한다.
            effective_capital = equity_baseline_usdt + carry_pnl
            if (
                effective_capital.is_nan()
                or effective_capital.is_infinite()
                or effective_capital <= Decimal("0")
            ):
                preflight_cat = "equity_exhausted"
                preflight_pageable, _, preflight_raw_msg = _PREFLIGHT_CATEGORY_METADATA[
                    preflight_cat
                ]
                if preflight_raw_msg is None:
                    preflight_raw_msg = ", ".join(preflight_symbols)[:200]
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:  # winner-only dedupe (동시 worker 2nd UPDATE rowcount=0)
                    _enqueue_conditional_entry_sweep()
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    if preflight_pageable:
                        qb_live_signal_divergence_total.labels(
                            stage="preflight", category=preflight_cat
                        ).inc()
                    qb_live_signal_skipped_total.labels(reason=preflight_cat).inc()
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="preflight",
                        category=preflight_cat,
                        raw_msg=preflight_raw_msg,
                        error_count=0,
                        last_error_bar=-1,
                    )
                    logger.error(
                        "live_signal_preflight_blocked",
                        extra={
                            "session_id": str(sess.id),
                            "category": preflight_cat,
                            "symbols": list(preflight_symbols),
                        },
                    )
                return {"deactivated": preflight_cat}

            # 6. try_claim_bar winner-only (P2 #3)
            won = await sess_repo.try_claim_bar(sess.id, last_bar_time, uuid4())
            if not won:
                # 다른 worker 가 이미 같은 bar claim 한 상태 — UPDATE no-op rollback
                await session.rollback()
                qb_live_signal_evaluated_total.labels(
                    interval=interval_value, outcome="claim_lost"
                ).inc()
                return {"skipped": "claim_lost"}

            # 장기 공백은 과거 이벤트를 발주하지 않는다. 거래소가 flat인지 먼저 확인하고,
            # 아래 warmup replay 결과의 시뮬레이션 flat과 함께 조용한 resync를 판정한다.
            exchange_positions: list[Any] | None = None
            if requires_gap_resync:
                from src.trading.encryption import EncryptionService
                from src.trading.providers import BybitFuturesProvider
                from src.trading.services.account_service import ExchangeAccountService

                try:
                    bybit_provider = BybitFuturesProvider()
                    exchange_svc = ExchangeAccountService(
                        repo=account_repo,
                        crypto=EncryptionService(settings.trading_encryption_keys),
                        bybit_futures_provider=bybit_provider,
                    )
                    creds = await exchange_svc.get_credentials_for_order(sess.exchange_account_id)
                    exchange_positions = await bybit_provider.fetch_open_positions(
                        creds, sess.symbol
                    )
                except Exception:
                    logger.warning(
                        "live_signal_gap_resync_position_fetch_failed",
                        exc_info=True,
                        extra={"session_id": str(sess.id), "symbol": sess.symbol},
                    )

            # 7. run_live (warmup replay, Option B)
            df = _ohlcv_rows_to_dataframe(ohlcv_rows)
            pyramiding: int | None = None
            try:
                pyramiding = extract_content(strategy.pine_source).declaration.pyramiding
            except Exception:
                logger.warning(
                    "live_signal_pyramiding_extract_failed",
                    exc_info=True,
                    extra={"session_id": str(sess.id)},
                )
            run_live_kwargs: dict[str, Any] = {
                "initial_capital": float(effective_capital),
                "live_position_size_pct": parsed_settings.position_size_pct,
                # BL-483 후속: pine_v2 청산 모델은 isolated 기준이다.
                # margin_mode는 아직 전달하지 않으며 cross 모델은 별도 BL 설계가 필요하다.
                "leverage": float(parsed_settings.leverage),
                "sessions_allowed": tuple(strategy.trading_sessions or ()),
                "pyramiding": pyramiding,
                "fill_timing": parsed_settings.fill_timing,
            }
            if emit_from_bar_time is not None:
                run_live_kwargs["emit_from_bar_time"] = emit_from_bar_time
            try:
                result = run_live(strategy.pine_source, df, **run_live_kwargs)
            except Exception as exc:
                # G2 — run_live 가 result.errors 로 surface 안 되는 예외를 raise 하는 경로:
                # parse SyntaxError / 미구현 na-semantics 의 raw ZeroDivisionError(`x/0`) /
                # math domain ValueError(`math.sqrt(-1)`) 등 (strict=False 의 except PineRuntimeError
                # 가 안 잡음). 미처리 시 claim rollback + 세션 active 유지 → 매 tick crash-loop.
                # → 동일 fail-closed: 세션 비활성화 + metric + alert. (interpreter na-semantics
                # 자체 수정은 BL-374 로 분리.)
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:
                    _enqueue_conditional_entry_sweep()
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    qb_live_signal_divergence_total.labels(
                        stage="runtime", category="run_live_error"
                    ).inc()
                    qb_live_signal_evaluated_total.labels(
                        interval=interval_value, outcome="divergence_blocked"
                    ).inc()
                    # G3 NIT#4 — raw_msg 는 임의 예외 str (구조적 audit 범위 밖). Telegram까지
                    # fan-out하므로 호출부에서 예외 클래스명만 전달한다. 전체 원문은 아래 logger에만 남긴다.
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="runtime",
                        category="run_live_error",
                        raw_msg=type(exc).__name__,
                        error_count=1,
                        last_error_bar=-1,
                    )
                    logger.exception(
                        "live_signal_run_live_crash",
                        extra={"session_id": str(sess.id), "error_type": type(exc).__name__},
                    )
                return {"deactivated": "run_live_error"}

            # 7.5 BL-362 — runtime divergence safety net (money-path fail-closed).
            # run_historical(strict=False) 가 PineRuntimeError 를 삼키고 계속 → state corruption
            # 가능 → 오신호. errors 비어있지 않으면(어느 bar든) 세션 비활성화 + events INSERT/
            # dispatch 차단. claim(UPDATE) + deactivate(UPDATE) 단일 commit (events 안 넣음).
            if result.errors:
                # errors[-1] = 가장 최근(최고 bar) runtime error. block-on-any 라 warmup
                # corruption 도 포착(마지막 bar 만 필터링하지 않음).
                category = _classify_live_divergence(result.errors[-1][1])
                rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                await sess_repo.commit()
                if rows == 1:  # winner-only dedupe
                    _enqueue_conditional_entry_sweep()
                    await publish_realtime(
                        str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                    )
                    qb_live_signal_divergence_total.labels(stage="runtime", category=category).inc()
                    qb_live_signal_evaluated_total.labels(
                        interval=interval_value, outcome="divergence_blocked"
                    ).inc()
                    _fire_divergence_alert(
                        session_id=sess.id,
                        stage="runtime",
                        category=category,
                        raw_msg=result.errors[-1][1],
                        error_count=len(result.errors),
                        last_error_bar=result.errors[-1][0],
                    )
                    logger.error(
                        "live_signal_runtime_divergence",
                        extra={
                            "session_id": str(sess.id),
                            "category": category,
                            "error_count": len(result.errors),
                            "errors": result.errors[:10],
                        },
                    )
                return {"deactivated": "runtime_divergence", "category": category}

            if requires_gap_resync:
                # `to_report()["open_trades"]` 는 **list** 다(`strategy_state.py:1005`).
                # dict 로 검사하면 항상 False 라 조용한 resync 가 절대 안 타고 모든 장기
                # 공백이 세션을 죽인다 - 수면·배포 공백이 정확히 그 경로다.
                simulated_open_trades = result.strategy_state_report.get("open_trades")
                simulated_flat = (
                    isinstance(simulated_open_trades, list) and not simulated_open_trades
                )
                if exchange_positions == [] and simulated_flat:
                    # try_claim_bar가 이미 최신 bar_time을 기록했다. 마지막 bar 신호만 이어서
                    # 처리해 수면·배포 공백을 조용히 정상화한다.
                    pass
                else:
                    category = "gap_resync_position_mismatch"
                    rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                    await sess_repo.commit()
                    if rows == 1:
                        _enqueue_conditional_entry_sweep()
                        await publish_realtime(
                            str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                        )
                        qb_live_signal_skipped_total.labels(reason=category).inc()
                        _fire_divergence_alert(
                            session_id=sess.id,
                            stage="gap_resync",
                            category=category,
                            raw_msg="exchange_or_simulated_position_not_flat",
                            error_count=0,
                            last_error_bar=-1,
                        )
                    return {"deactivated": category}

            # 7.6 BL-530 — 엔진↔거래소 포지션 발산 감지.
            #
            # 지금까지 이 발산은 **close 가 거절될 때까지 보이지 않았다.** 계기를 perp 로
            # 맞춰도(위 4단계) 진입 유실·부분체결로 재발할 수 있으므로 감지는 계기 수리와
            # 독립적으로 필요하다. 조회 실패는 fail-open — REST 한 번 실패로 세션을 죽이지
            # 않는다(이 파일의 다른 포지션 조회와 같은 계약).
            #
            # ★**방향 불일치는 한 번 봤다고 죽이지 않는다.** 거래소는 스톱을 **bar 안에서
            # 실시간으로** 트리거하는데 엔진은 **bar 종가에만** 평가한다. stop-and-reverse
            # 전략에서는 거래소가 먼저 반대편으로 넘어가고 엔진이 다음 bar 에 따라가는
            # 구간이 정상적으로 존재한다 — 실측(2026-07-28 soak): 거래소가 17:46:28 에
            # 롱으로 체결됐는데 엔진이 평가한 bar 는 17:45 종가라 아직 숏이었고, 초판
            # 가드가 이 **자기해소되는 skew** 로 세션을 죽였다.
            # 그래서 **연속 2회 평가에서 살아남은 경우에만** 차단한다. 한 bar 를 넘겨도
            # 반대편이면 그건 스스로 풀리는 상태가 아니다.
            #
            # ★**판정하지 못한 tick 이 직전 strike 를 지우면 안 된다.** 판정 실패는 두
            # 경로로 온다 — `position_size` 를 못 읽거나(NaN/부재), 거래소 probe 가
            # 실패하거나(REST blip, 현실적). 둘 다 "불일치 없음" 이 아니라 "모름" 이다.
            # 모름을 False 로 적으면 REST 한 번 흔들릴 때마다 strike 가 초기화돼 진짜
            # 지속 발산이 영원히 2회차에 도달하지 못한다(가드 fail-open 무력화).
            # 그래서 `None`(모름)이면 직전 값을 그대로 넘긴다.
            previous_state = await sess_repo.get_state(sess.id)
            # 직전 리포트를 못 읽으면 "직전 strike 없음" 으로 본다. 아래 `isinstance` 방어와
            # 같은 계약이며, state 행이 아직 없거나 리포트가 비어 있는 첫 tick 이 정상이다.
            previous_report = getattr(previous_state, "last_strategy_state_report", None)
            previous_direction_mismatch = (
                isinstance(previous_report, dict)
                and previous_report.get(_DIRECTION_MISMATCH_KEY) is True
            )

            engine_position = _to_engine_position(result.strategy_state_report)
            direction_mismatch_seen: bool | None = None
            if engine_position is not None:
                divergence_category = await _detect_position_divergence(
                    sess, engine_position, account_repo=account_repo
                )
                if divergence_category != _PROBE_FAILED:
                    direction_mismatch_seen = divergence_category == "direction"
                direction_mismatch_persisted = (
                    direction_mismatch_seen is True and previous_direction_mismatch
                )
                if direction_mismatch_seen and not direction_mismatch_persisted:
                    # 첫 관측 — 다음 평가까지 유예한다. 플래그는 아래 upsert 로 넘어간다.
                    qb_live_position_divergence_total.labels(category="direction_transient").inc()
                if direction_mismatch_persisted:
                    rows = await sess_repo.deactivate(sess.id, at=datetime.now(UTC))
                    await sess_repo.commit()
                    if rows == 1:
                        _enqueue_conditional_entry_sweep()
                        await publish_realtime(
                            str(sess.user_id), "session_state", {"session_id": str(sess.id)}
                        )
                        qb_live_signal_divergence_total.labels(
                            stage="position", category="direction"
                        ).inc()
                        qb_live_signal_evaluated_total.labels(
                            interval=interval_value, outcome="divergence_blocked"
                        ).inc()
                        _fire_divergence_alert(
                            session_id=sess.id,
                            stage="position",
                            category="position_direction_mismatch",
                            raw_msg="engine and exchange hold opposite sides for two evaluations",
                            error_count=0,
                            last_error_bar=-1,
                        )
                    return {"deactivated": "position_divergence", "category": "direction"}
                if (
                    divergence_category is not None
                    and divergence_category != _PROBE_FAILED
                    and not direction_mismatch_seen
                ):
                    # 죽이지는 않는다 — 크기를 재서 BL-522 설계 입력으로 삼는다.
                    # 차단 counter 와 분리한다(페이징 계약이 다르다).
                    qb_live_position_divergence_total.labels(category=divergence_category).inc()

            for entry_skip in result.entry_skips:
                reason = entry_skip.get("reason")
                if not isinstance(reason, str) or reason not in (
                    "margin_insufficient",
                    "non_finite_qty",
                    "pyramiding_cap",
                    "session_closed",
                ):
                    reason = "other"
                qb_live_signal_entry_skipped_total.labels(reason=reason).inc()
            for liquidation in result.liquidations:
                direction = liquidation.get("direction")
                if direction in ("long", "short"):
                    qb_live_signal_liquidation_total.labels(direction=direction).inc()

            # 8. transactional outbox — events INSERT + state upsert + commit (P1 #3)
            signals_payload: list[dict[str, object]] = [
                {
                    "action": s.action,
                    "direction": s.direction,
                    "trade_id": s.trade_id,
                    "qty": s.qty,
                    "sequence_no": s.sequence_no,
                    "comment": s.comment,
                    # catch-up은 signal별 원래 bar 시각을 보존한다. 기본 호출의 None은
                    # repository가 이번 last_bar_time으로 기존처럼 폴백한다.
                    "bar_time": s.bar_time,
                    # MP-1 — close signal 의 청산 realized PnL (entry 는 None).
                    "realized_pnl": s.realized_pnl,
                    # Phase 3 — entry signal 의 exit 레벨 (bracket placement + trailing). close 는 None.
                    "take_profit": s.take_profit,
                    "stop_loss": s.stop_loss,
                    "trailing_stop": s.trailing_stop,
                }
                for s in result.signals
            ]
            existing_events = await event_repo.list_by_session(sess.id, limit=1000)
            existing_keys = {
                (e.bar_time, e.sequence_no, e.action, e.trade_id) for e in existing_events
            }
            inserted_or_existing = await event_repo.insert_pending_events(
                session_id=sess.id, bar_time=last_bar_time, signals=signals_payload
            )
            new_events = [
                e
                for e in inserted_or_existing
                if (e.bar_time, e.sequence_no, e.action, e.trade_id) not in existing_keys
            ]
            # 화면 총계 SSOT는 append-only LiveSignalEvent 원장이다.
            # warmup 창이 과거 entry를 재현하지 못하면 창 안 close가 run_live 결과에서 사라진다(D2).
            # 원장 합계는 창과 무관하게 단조이므로 화면 총계는 이 값을 사용한다.
            ledger_realized_pnl, ledger_closed_trades = await event_repo.sum_realized_pnl_all(
                sess.id
            )

            # BL-123 — JSONB 호환 sanitize (NaN/Infinity → None). run_historical 의
            # warmup 중 ATR/EMA 등이 NaN 반환 가능 → PG strict JSONB reject.
            sanitized_report = _sanitize_for_jsonb(result.strategy_state_report)
            # 방향 불일치 1회차를 다음 평가로 넘긴다(위 7.6). 여기 얹는 이유는 이 dict 가
            # 이미 매 tick upsert 되기 때문이다 — 새 컬럼도 새 저장소도 만들지 않는다.
            # ★판정하지 못한 tick(`None`)은 직전 값을 그대로 넘긴다 — 지우지 않는다.
            if isinstance(sanitized_report, dict):
                sanitized_report[_DIRECTION_MISMATCH_KEY] = (
                    previous_direction_mismatch
                    if direction_mismatch_seen is None
                    else direction_mismatch_seen
                )
            # Sprint 28 Slice 3 (BL-140b) — equity_curve append.
            # 이번 tick 에 새로 INSERT 된 close event 만 curve 에 반영한다. warmup 창
            # 재계산의 미세 변동은 point 를 추가하지 않는다.
            # defensive: non-Decimal mock value 도 graceful (None 반환 = skip).
            from src.trading.equity_calculator import append_equity_point

            new_equity_curve: list[dict[str, object]] | None = None
            try:
                existing_state = await sess_repo.get_state(sess.id)
                new_close_events = [
                    event
                    for event in new_events
                    if event.action == "close" and event.realized_pnl is not None
                ]
                if new_close_events:
                    pnl_delta = sum(
                        (Decimal(str(event.realized_pnl)) for event in new_close_events),
                        Decimal("0"),
                    )
                    # 영구 규칙: Decimal-first 합산 (calculator 안에서 처리)
                    prev_curve = (
                        existing_state.equity_curve
                        if existing_state is not None and existing_state.equity_curve is not None
                        else []
                    )
                    new_curve = append_equity_point(
                        prev_curve,  # type: ignore[arg-type]
                        timestamp_ms=int(last_bar_time.timestamp() * 1000),
                        pnl_delta=pnl_delta,
                    )
                    # TypedDict → dict 호환 cast (runtime 동일 구조)
                    new_equity_curve = [dict(p) for p in new_curve]
            except (InvalidOperation, ValueError, TypeError) as exc:
                # Decimal 변환 실패 (mock value / corrupt DB 등) — equity_curve skip + log.
                # KillSwitch eval 자체는 절대 fail 금지 (BL-004 영구 규칙 정합).
                logger.warning("equity_curve_skip session=%s err=%s", sess.id, exc)

            await sess_repo.upsert_state(
                session_id=sess.id,
                last_strategy_state_report=sanitized_report
                if isinstance(sanitized_report, dict)
                else {},
                total_closed_trades=ledger_closed_trades,
                total_realized_pnl=ledger_realized_pnl,
                equity_curve=new_equity_curve,
            )

            # LESSON-019 — claim UPDATE + events INSERT + state upsert 단일 commit
            await sess_repo.commit()
            await publish_realtime(str(sess.user_id), "session_state", {"session_id": str(sess.id)})

        # 9. dispatch task enqueue — outbox commit 후 (visibility race 방지)
        for ev in new_events:
            if ev.status == LiveSignalEventStatus.pending:
                dispatch_live_signal_event_task.apply_async(
                    args=[str(ev.id)],
                    expires=300,
                )

        await _reconcile_conditional_entries(
            sess,
            result,
            parsed_settings,
            sm,
            bar_time=last_bar_time,
            market_orders_in_flight=bool(new_events),
            fallback_reference_price=_last_close_or_none(df),
        )

        qb_live_signal_evaluated_total.labels(interval=interval_value, outcome="success").inc()
        return {
            "evaluated": True,
            "events_inserted": len(new_events),
            "last_bar_time": last_bar_time.isoformat(),
        }
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Task #2: dispatch_live_signal_event_task (per event)
# ---------------------------------------------------------------------------


@shared_task(  # type: ignore[untyped-decorator]
    name="live_signal.dispatch_event",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def dispatch_live_signal_event_task(self: Any, event_id: str) -> dict[str, Any]:
    """Sprint 26 — 단일 LiveSignalEvent → OrderService.execute.

    eval task 가 commit 후 apply_async 로 enqueue. broker 발주 후 mark_dispatched
    / mark_failed. 일시 장애 시 max_retries=3 (15s/30s/45s exponential).

    codex G.2 P1 #10 fix — retry 소진 시 event 가 status=pending 으로 영구 잔류
    하지 않도록 max_retries 도달 시 mark_failed(error='max_retries_exhausted')
    + commit. `dispatch_pending_live_signal_events_task` Beat 가 별도로 잔여 pending
    회수.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    try:
        return run_in_worker_loop(_async_dispatch_event(UUID(event_id)))
    except (
        KillSwitchActive,
        NotionalExceeded,
        LeverageCapExceeded,
        MinNotionalNotMet,
        TradingSessionClosed,
    ):
        # 재시도해도 풀리지 않는 deterministic reject — _async_dispatch_event 가 이미
        # mark_failed + commit 처리 후 raise 했으므로 retry 안 함.
        return {"failed": "deterministic_reject"}
    except Exception as exc:  # BLE001 — 재시도 가능 일시 장애
        # codex G.2 P1 #10 — retry 소진 시 event 영구 stuck 차단
        retries_so_far = getattr(self.request, "retries", 0) or 0
        if retries_so_far >= getattr(self, "max_retries", 3):
            logger.exception(
                "live_signal_dispatch_max_retries_exhausted_marking_failed",
                extra={"event_id": event_id, "retries": retries_so_far},
            )
            try:
                run_in_worker_loop(
                    _async_mark_event_failed(UUID(event_id), error="max_retries_exhausted")
                )
            except Exception:
                logger.exception(
                    "live_signal_dispatch_mark_failed_on_exhaustion_failed",
                    extra={"event_id": event_id},
                )
            qb_live_signal_dispatch_total.labels(
                action="unknown", outcome="max_retries_exhausted"
            ).inc()
            return {"failed": "max_retries_exhausted"}
        logger.exception("live_signal_dispatch_failed_will_retry", extra={"event_id": event_id})
        raise self.retry(exc=exc) from exc


async def _async_mark_event_failed(event_id: UUID, *, error: str) -> None:
    """codex G.2 P1 #10 helper — retry 소진 시 mark_failed + commit (per-call engine)."""
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = LiveSignalEventRepository(session)
            await repo.mark_failed(event_id, error=error)
            await repo.commit()
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Task #3: dispatch_pending_live_signal_events_task (Beat 5min — outbox 회수)
# ---------------------------------------------------------------------------


@shared_task(  # type: ignore[untyped-decorator]
    name="live_signal.dispatch_pending",
    max_retries=0,
)
def dispatch_pending_live_signal_events_task() -> dict[str, Any]:
    """Sprint 26 — codex G.2 P1 #10 fix — outbox pending 회수 Beat.

    5분 주기 fire. status=pending 인 event 를 list_pending(limit=50) 으로 조회하여
    `dispatch_live_signal_event_task.apply_async` 재발행. eval task 의 dispatch enqueue
    가 worker crash / Redis broker 일시 장애로 유실됐을 때 회수 안전망.

    중복 fire 위험 (같은 event 가 in-flight + pending 시 두 번 발행) 은 dispatch task
    내부의 `if event.status != pending: skipped='already_terminal'` 가드 로 차단.
    """
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_dispatch_pending())


async def _async_dispatch_pending() -> dict[str, Any]:
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            repo = LiveSignalEventRepository(session)
            pending = await repo.list_pending(limit=50)
        qb_live_signal_outbox_pending_gauge.set(len(pending))
        for ev in pending:
            dispatch_live_signal_event_task.apply_async(
                args=[str(ev.id)],
                expires=300,
            )
        return {"reenqueued": len(pending)}
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Task #4: sweep_conditional_entries_task (Beat 5min + session 종료 직후)
# ---------------------------------------------------------------------------


@shared_task(name="live_signal.sweep_conditional_entries", max_retries=0)  # type: ignore[untyped-decorator]
def sweep_conditional_entries_task() -> dict[str, int]:
    """비활성 세션의 거래소 조건부 진입 주문을 취소한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_sweep_conditional_entries())


async def _async_sweep_conditional_entries() -> dict[str, int]:
    """고아 조건부 진입을 거래소 취소 뒤에만 cancelled로 전이한다."""
    from src.tasks.trading import (
        _enqueue_closed_pnl_refresh,
        _enqueue_trailing_if_intended,
        _has_leverage,
    )
    from src.trading.encryption import EncryptionService
    from src.trading.registry import dispatch
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.account_service import ExchangeAccountService

    engine, sm = create_worker_engine_and_sm()
    cancelled = 0
    try:
        async with sm() as session:
            order_repo = OrderRepository(session)
            account_repo = ExchangeAccountRepository(session)
            exchange_service = ExchangeAccountService(
                repo=account_repo,
                crypto=EncryptionService(settings.trading_encryption_keys),
            )
            orders = [
                (
                    order.id,
                    order.exchange_account_id,
                    order.exchange_order_id,
                    order.symbol,
                    _has_leverage(order),
                    SimpleNamespace(
                        id=order.id,
                        trailing_stop=order.trailing_stop,
                        reduce_only=order.reduce_only,
                    ),
                )
                for order in await order_repo.list_orphan_conditional_entries()
            ]
            for order_id, account_id, exchange_order_id, symbol, has_leverage, hook_order in orders:
                if exchange_order_id is None:
                    continue  # submitted + null id는 janitor가 client id로 확인한다.
                try:
                    account = await account_repo.get_by_id(account_id)
                    if account is None:
                        raise RuntimeError("conditional entry account missing")
                    provider = dispatch(account.exchange, account.mode, has_leverage)
                    creds = await exchange_service.get_credentials_for_order(account_id)
                    try:
                        await provider.cancel_order(creds, exchange_order_id, symbol)
                    except Exception:
                        try:
                            probe = await provider.fetch_order_by_client_id(
                                creds, str(order_id), symbol, trigger=True
                            )
                        except Exception:
                            with contextlib.suppress(Exception):
                                await session.rollback()
                            qb_live_conditional_reconcile_errors_total.labels(
                                stage="sweep_cancel"
                            ).inc()
                            logger.exception(
                                "live_conditional_entry_sweep_cancel_failed",
                                extra={"order_id": str(order_id)},
                            )
                            continue

                        now = datetime.now(UTC)
                        if probe is None:
                            rows = await order_repo.transition_to_cancelled(
                                order_id, cancelled_at=now
                            )
                        elif probe.status == "filled":
                            rows = await order_repo.transition_to_filled(
                                order_id,
                                exchange_order_id=probe.exchange_order_id,
                                filled_price=probe.filled_price,
                                filled_quantity=probe.filled_quantity,
                                filled_at=now,
                            )
                        elif probe.status == "cancelled":
                            rows = await order_repo.transition_to_cancelled(
                                order_id,
                                cancelled_at=now,
                                filled_price=probe.filled_price,
                                filled_quantity=probe.filled_quantity,
                            )
                        elif probe.status == "rejected":
                            rows = await order_repo.transition_to_rejected(
                                order_id,
                                error_message="Conditional entry rejected on exchange",
                                failed_at=now,
                                filled_price=probe.filled_price,
                                filled_quantity=probe.filled_quantity,
                            )
                        else:
                            qb_live_conditional_reconcile_errors_total.labels(
                                stage="sweep_cancel_stalled"
                            ).inc()
                            logger.warning(
                                "live_conditional_entry_sweep_cancel_stalled",
                                extra={"order_id": str(order_id)},
                            )
                            continue
                        if rows == 1:
                            await order_repo.commit()
                            if probe is None or probe.status == "cancelled":
                                cancelled += 1
                            qb_active_orders.dec()
                            if probe is not None and probe.status == "filled":
                                qb_live_conditional_sweep_filled_total.inc()
                                logger.warning(
                                    "live_conditional_entry_sweep_found_filled",
                                    extra={"order_id": str(order_id)},
                                )
                                _enqueue_trailing_if_intended(hook_order)
                                _enqueue_closed_pnl_refresh(hook_order)
                        continue

                    if (
                        await order_repo.transition_to_cancelled(
                            order_id, cancelled_at=datetime.now(UTC)
                        )
                        == 1
                    ):
                        cancelled += 1
                        qb_active_orders.dec()  # 생성 시 inc 된 것의 terminal 전이
                    await order_repo.commit()
                except Exception:
                    with contextlib.suppress(Exception):
                        await session.rollback()
                    qb_live_conditional_reconcile_errors_total.labels(stage="sweep_cancel").inc()
                    logger.exception(
                        "live_conditional_entry_sweep_cancel_failed",
                        extra={"order_id": str(order_id)},
                    )
        return {"cancelled": cancelled}
    finally:
        await engine.dispose()


def _conditional_entry_janitor_delay_minutes() -> int:
    from src.tasks.orphan_scanner import _SCAN_STUCK_THRESHOLD_MINUTES

    return _SCAN_STUCK_THRESHOLD_MINUTES


async def _async_dispatch_event(event_id: UUID) -> dict[str, Any]:
    """Per-call engine + dispose. OrderService 조립 + execute + mark_dispatched/failed.

    중요 의무:
    - sessions_port=_StrategySessionsAdapter 주입 (P1 #5 — bypass 차단)
    - idempotency_key with sequence_no (P2 #5 — 같은 bar entry+close 분리)
    - mark_failed 도 commit 의무 (LESSON-019)
    """
    from src.strategy.repository import StrategyRepository
    from src.trading.dependencies import _CeleryOrderDispatcher, _StrategySessionsAdapter
    from src.trading.encryption import EncryptionService
    from src.trading.kill_switch import (
        CumulativeLossEvaluator,
        DailyLossEvaluator,
        KillSwitchEvaluator,
        KillSwitchService,
    )
    from src.trading.providers import BybitFuturesProvider
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.kill_switch_event_repository import KillSwitchEventRepository
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.account_service import ExchangeAccountService
    from src.trading.services.order_service import OrderService

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            event_repo = LiveSignalEventRepository(session)
            event = await event_repo.get_by_id(event_id)
            if event is None:
                logger.warning(
                    "live_signal_dispatch_missing_event", extra={"event_id": str(event_id)}
                )
                return {"skipped": "missing"}
            if event.status != LiveSignalEventStatus.pending:
                # 이미 dispatched / failed — duplicate apply_async 방어
                return {"skipped": "already_terminal", "status": str(event.status)}

            sess_repo = LiveSignalSessionRepository(session)
            sess = await sess_repo.get_by_id(event.session_id)
            if sess is None or not sess.is_active:
                await event_repo.mark_failed(event.id, error="session_inactive")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="session_inactive"
                ).inc()
                return {"failed": "session_inactive"}

            # strategy + settings (P2 #4)
            strategy_repo = StrategyRepository(session)
            strategy = await strategy_repo.find_by_id_and_owner(sess.strategy_id, sess.user_id)
            if strategy is None:
                await event_repo.mark_failed(event.id, error="strategy_missing")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="strategy_missing"
                ).inc()
                return {"failed": "strategy_missing"}
            try:
                parsed_settings = validate_strategy_settings(strategy.settings)
            except ValidationError as exc:
                await event_repo.mark_failed(event.id, error=f"invalid_settings: {exc}")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="invalid_settings"
                ).inc()
                return {"failed": "invalid_settings"}
            if parsed_settings is None:
                await event_repo.mark_failed(event.id, error="settings_unset")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="settings_unset"
                ).inc()
                return {"failed": "settings_unset"}

            # OrderService 조립 (P1 #5: sessions_port 의무)
            order_repo = OrderRepository(session)
            account_repo = ExchangeAccountRepository(session)
            kse_repo = KillSwitchEventRepository(session)
            crypto = EncryptionService(settings.trading_encryption_keys)
            bybit_provider = BybitFuturesProvider()
            exchange_svc = ExchangeAccountService(
                repo=account_repo,
                crypto=crypto,
                bybit_futures_provider=bybit_provider,
            )

            # close만 거래소 flat을 확인한다. 명시적 0건이면 reduce-only 거부 주문을 만들지
            # 않고 실패 전이한다. 조회 실패는 정당한 청산을 막지 않도록 fail-open이다.
            if event.action == "close":
                try:
                    positions = await bybit_provider.fetch_open_positions(
                        await exchange_svc.get_credentials_for_order(sess.exchange_account_id),
                        sess.symbol,
                    )
                    if len(positions) == 0:
                        await event_repo.mark_failed(event.id, error="close_position_flat")
                        await event_repo.commit()
                        qb_live_signal_dispatch_total.labels(
                            action=event.action, outcome="close_position_flat"
                        ).inc()
                        return {"failed": "close_position_flat"}
                except Exception:
                    logger.warning(
                        "live_signal_close_position_check_failed_open",
                        exc_info=True,
                        extra={"event_id": str(event.id), "session_id": str(sess.id)},
                    )
            evaluators: list[KillSwitchEvaluator] = [
                CumulativeLossEvaluator(
                    order_repo,
                    threshold_percent=settings.kill_switch_cumulative_loss_percent,
                    capital_base=settings.kill_switch_capital_base_usd,
                    balance_provider=exchange_svc,
                ),
                DailyLossEvaluator(
                    order_repo,
                    threshold_usd=settings.kill_switch_daily_loss_usd,
                ),
            ]
            ks_svc = KillSwitchService(evaluators=evaluators, events_repo=kse_repo)

            order_svc = OrderService(
                session=session,
                repo=order_repo,
                dispatcher=_CeleryOrderDispatcher(),
                kill_switch=ks_svc,
                sessions_port=_StrategySessionsAdapter(session),  # P1 #5 fix
                exchange_service=exchange_svc,
            )

            # Phase 3 — 트레일링 가드 (codex gate BLOCKER): 트레일링이 의도된 stop 인데
            #   라이브 placement 미지원(set-trading-stop 엔드포인트라 fill 후 follow-on 필요)
            #   + 폴백 SL 부재 → 무방비 포지션. 안전 우선으로 진입 거부 (정직 defer).
            #   SL 이 있으면 bracket SL 이 보호 → 진입 허용 (트레일링은 drop, SL-only 동작).
            #   실제 트레일링 placement 는 fast-follow (데모 round-trip 검증 후).
            if (
                event.action == "entry"
                and event.trailing_stop is not None
                and event.stop_loss is None
            ):
                await event_repo.mark_failed(
                    event.id, error="trailing_stop_live_placement_unsupported"
                )
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(action=event.action, outcome="rejected").inc()
                return {"failed": "trailing_unsupported"}

            # OrderRequest 조립 — DB NUMERIC(18,8) round-trip 후 0/비정상으로 반올림된 exit
            # 레벨 등 모든 ValidationError 를 graceful mark_failed (poison pill 완전 차단,
            # 평가자 게이트 belt-and-suspenders). _to_decimal 의 float-boundary 가드 보완.
            try:
                req = OrderRequest(
                    strategy_id=sess.strategy_id,
                    exchange_account_id=sess.exchange_account_id,
                    symbol=sess.symbol,
                    side=_signal_to_order_side(event.action, event.direction),
                    type=OrderType.market,
                    quantity=Decimal(str(event.qty)),
                    price=None,  # market order
                    leverage=parsed_settings.leverage,
                    margin_mode=parsed_settings.margin_mode,
                    # MP-1 — close 이벤트 청산 PnL → Order.realized_pnl (kill-switch SUM 대상).
                    realized_pnl=event.realized_pnl,
                    # Wave 1 C3 — close 주문 reduce-only (over-fill/반전 방지). entry=False.
                    reduce_only=_action_is_reduce_only(event.action),
                    # Phase 3 — entry 주문에 TP/SL bracket 부착 → Bybit 포지션 bracket(거래소-네이티브 OCO).
                    # close 이벤트는 None (fold 안 됨). _merge_exit_params 가 takeProfit/stopLoss params 주입.
                    take_profit=event.take_profit,
                    stop_loss=event.stop_loss,
                    # ★ STEP B — trailing_stop 을 Order 에 영속(의도 보존). entry 는 reduce_only=False
                    #   라 tasks/trading 이 create_order 에 미주입(trailingStop 실으면 ccxt 가
                    #   trading-stop 엔드포인트로 라우팅 → entry 깨짐). 체결 후 place_trailing_stop 가
                    #   Order.trailing_stop 을 읽어 set_trading_stop 으로 발주(포지션 open 뒤).
                    #   trailing-only(SL 부재)는 위 가드가 여전히 거부(stage 2 — 무방비 윈도 회피).
                    #   ★ entry 만 영속(Opus A P3 defensive) — close 신호는 trailing=None 계약이나,
                    #   future extractor 가 reduce-only close 에 non-null trailing 을 실으면 ccxt 가
                    #   close 시장가를 trading-stop 으로 재라우팅(flatten 대신 trailing set) → 명시 차단.
                    trailing_stop=event.trailing_stop if event.action == "entry" else None,
                )
            except ValidationError as exc:
                await event_repo.mark_failed(event.id, error=f"invalid_order_request: {exc}")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(action=event.action, outcome="rejected").inc()
                return {"failed": "invalid_order_request"}
            idempotency_key = _build_idempotency_key(
                session_id=sess.id,
                bar_time=event.bar_time,
                sequence_no=event.sequence_no,
                action=event.action,
                trade_id=event.trade_id,
            )

            try:
                response, _replayed = await order_svc.execute(
                    req, idempotency_key=idempotency_key, body_hash=None
                )
            except KillSwitchActive:
                await event_repo.mark_failed(event.id, error="kill_switched")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="kill_switched"
                ).inc()
                raise
            except (
                NotionalExceeded,
                LeverageCapExceeded,
                MinNotionalNotMet,
                TradingSessionClosed,
            ) as exc:
                await event_repo.mark_failed(event.id, error=str(exc))
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(action=event.action, outcome="rejected").inc()
                raise
            except IdempotencyConflict as exc:
                # 같은 idempotency_key 가 다른 payload — 복구 불가, mark_failed
                await event_repo.mark_failed(event.id, error=f"idempotency_conflict: {exc}")
                await event_repo.commit()
                qb_live_signal_dispatch_total.labels(
                    action=event.action, outcome="idempotency_conflict"
                ).inc()
                return {"failed": "idempotency_conflict"}

            # OrderService.execute 가 self._session.commit() 내부 호출 — Order INSERT 영구화 완료.
            await event_repo.mark_dispatched(event.id, order_id=response.id)
            await event_repo.commit()
            qb_live_signal_dispatch_total.labels(action=event.action, outcome="dispatched").inc()
            return {"dispatched": str(response.id), "replayed": _replayed}
    finally:
        await engine.dispose()
