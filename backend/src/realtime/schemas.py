# 실시간 WebSocket 이벤트와 인증 메시지 계약의 단일 정의.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

USER_CHANNEL_PREFIX = "qb:rt:user:"
WS_CLOSE_AUTH_FAILED = 4401
WS_CLOSE_ORIGIN_DENIED = 4403
WS_CLOSE_CONNECTION_LIMIT = 4408


class RealtimeEnvelope(BaseModel):
    """Redis pubsub와 WebSocket이 공유하는 이벤트 envelope."""

    v: int = 1
    type: Literal["order_update", "kill_switch", "kill_switch_resolved", "session_state"]
    ts: int
    payload: dict[str, object]


class OrderUpdatePayload(BaseModel):
    """주문 상태 변경 이벤트 payload."""

    model_config = ConfigDict(extra="ignore")

    order_id: str
    state: str
    symbol: str
    side: str
    source: str


class KillSwitchPayload(BaseModel):
    """킬 스위치 변경 이벤트 payload."""

    model_config = ConfigDict(extra="ignore")

    event_id: str
    trigger_type: str


class SessionStatePayload(BaseModel):
    """트레이딩 세션 상태 변경 이벤트 payload."""

    model_config = ConfigDict(extra="ignore")

    session_id: str


PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "order_update": OrderUpdatePayload,
    "kill_switch": KillSwitchPayload,
    "kill_switch_resolved": KillSwitchPayload,
    "session_state": SessionStatePayload,
}


class AuthMessage(BaseModel):
    """WebSocket 최초 인증 메시지."""

    type: Literal["auth"]
    token: str


def user_channel(user_id: str) -> str:
    """채널 키는 users.id 내부 UUID 문자열이며 clerk_user_id가 아니다."""
    return f"{USER_CHANNEL_PREFIX}{user_id}"
