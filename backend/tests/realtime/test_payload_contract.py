# 실시간 발행 payload가 프론트엔드 envelope 계약을 지키는지 검증한다.
from __future__ import annotations

import json
from typing import get_args

import pytest

from src.common.metrics import qb_rt_publish_invalid_total
from src.realtime.schemas import PAYLOAD_MODELS, RealtimeEnvelope
from src.trading import realtime_publisher


class _RecordingPool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.calls.append((channel, message))


VALID_PAYLOADS = {
    "order_update": {
        "order_id": "order-1",
        "state": "filled",
        "symbol": "BTC/USDT",
        "side": "buy",
        "source": "rest",
    },
    "kill_switch": {"event_id": "event-1", "trigger_type": "daily_loss"},
    "kill_switch_resolved": {"event_id": "event-1", "trigger_type": "daily_loss"},
    "session_state": {"session_id": "session-1"},
}


def test_payload_models_match_envelope_event_types() -> None:
    """신규 이벤트는 envelope와 payload 모델을 동시에 갱신해야 한다."""
    event_types = set(get_args(RealtimeEnvelope.model_fields["type"].annotation))

    assert event_types == set(PAYLOAD_MODELS)


@pytest.mark.asyncio
@pytest.mark.parametrize(("event_type", "payload"), VALID_PAYLOADS.items())
async def test_valid_payload_publishes(
    monkeypatch: pytest.MonkeyPatch, event_type: str, payload: dict[str, str]
) -> None:
    """각 계약 payload는 Redis 발행까지 도달해야 한다."""
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)

    await realtime_publisher.publish_realtime("user-1", event_type, payload)

    assert len(pool.calls) == 1
    assert json.loads(pool.calls[0][1])["payload"] == payload


@pytest.mark.asyncio
async def test_invalid_payload_skips_publish_and_counts_contract_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """필수 필드가 없으면 Redis 호출 없이 계약 위반만 기록해야 한다."""
    pool = _RecordingPool()
    monkeypatch.setattr(realtime_publisher, "_get_redis_lock_pool", lambda: pool)
    counter = qb_rt_publish_invalid_total.labels(event_type="session_state")
    before = counter._value.get()

    await realtime_publisher.publish_realtime("user-1", "session_state", {})

    assert pool.calls == []
    assert counter._value.get() == before + 1


@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        (
            "order_update",
            {
                "order_id": "order-1",
                "state": "filled",
                "symbol": "BTC/USDT",
                "side": "buy",
                "source": "ws",
            },
        ),
        ("kill_switch", {"event_id": "event-1", "trigger_type": "daily_loss"}),
        (
            "kill_switch_resolved",
            {"event_id": "event-1", "trigger_type": "daily_loss"},
        ),
        ("session_state", {"session_id": "session-1"}),
    ],
)
def test_representative_publisher_payloads_match_models(
    event_type: str, payload: dict[str, str]
) -> None:
    """실제 발행 지점의 대표 리터럴은 payload 모델을 통과해야 한다."""
    assert PAYLOAD_MODELS[event_type].model_validate(payload).model_dump() == payload
