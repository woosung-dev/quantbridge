# 사용자별 Redis 실시간 무효화 힌트를 발행한다.
from __future__ import annotations

import logging
import time
from typing import Any, Literal, cast

from pydantic import ValidationError

from src.common.metrics import qb_rt_publish_failed_total, qb_rt_publish_invalid_total
from src.common.metrics_multiproc import _count_safely, record_metric_safely
from src.common.redis_client import get_redis_lock_pool
from src.realtime.schemas import PAYLOAD_MODELS, RealtimeEnvelope, ticker_channel, user_channel

logger = logging.getLogger(__name__)


def _get_redis_lock_pool() -> Any:
    """테스트에서 Redis pool을 교체할 수 있는 간접 지점."""
    return get_redis_lock_pool()


async def _publish_envelope(channel: str, event_type: str, payload: dict[str, Any]) -> None:
    """계약 검증 뒤 Redis pub/sub envelope를 발행한다."""
    try:
        PAYLOAD_MODELS[event_type].model_validate(payload)
    except (KeyError, ValidationError):
        logger.warning("realtime_publish_invalid_payload event_type=%s", event_type)
        _count_safely(qb_rt_publish_invalid_total, event_type=event_type)
        return

    try:
        envelope = RealtimeEnvelope(
            type=cast(
                Literal[
                    "order_update",
                    "kill_switch",
                    "kill_switch_resolved",
                    "session_state",
                    "ticker",
                    "position_update",
                ],
                event_type,
            ),
            ts=time.time_ns() // 1_000_000,
            payload=payload,
        )
        await _get_redis_lock_pool().publish(channel, envelope.model_dump_json())
    except Exception:
        logger.exception("realtime_publish_failed event_type=%s", event_type)
        record_metric_safely(qb_rt_publish_failed_total.inc)


async def publish_realtime(user_id: str, event_type: str, payload: dict[str, Any]) -> None:
    """사용자별 Redis pub/sub 발행 실패가 거래 상태 전이를 방해하지 않게 한다."""
    await _publish_envelope(user_channel(user_id), event_type, payload)


async def publish_ticker(symbol: str, payload: dict[str, Any]) -> None:
    """공개 ticker envelope를 심볼 채널로 발행한다."""
    await _publish_envelope(ticker_channel(symbol), "ticker", payload)
