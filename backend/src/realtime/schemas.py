# 실시간 WebSocket 이벤트와 인증 메시지 계약의 단일 정의.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

USER_CHANNEL_PREFIX = "qb:rt:user:"
TICKER_CHANNEL_PREFIX = "qb:rt:ticker:"
WS_CLOSE_AUTH_FAILED = 4401
WS_CLOSE_ORIGIN_DENIED = 4403
WS_CLOSE_CONNECTION_LIMIT = 4408


class RealtimeEnvelope(BaseModel):
    """Redis pubsub와 WebSocket이 공유하는 이벤트 envelope.

    ts는 epoch-ms 단위다.
    """

    v: int = 1
    type: Literal[
        "order_update",
        "kill_switch",
        "kill_switch_resolved",
        "session_state",
        "ticker",
        "position_update",
    ]
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


class TickerPayload(BaseModel):
    """Bybit 공개 ticker 이벤트 payload."""

    model_config = ConfigDict(extra="ignore")

    symbol: str
    mark_price: str
    last_price: str | None = None


class PositionUpdatePayload(BaseModel):
    """거래소 포지션 변경 무효화 힌트 payload."""

    model_config = ConfigDict(extra="ignore")

    symbol: str
    side: str
    size: str


PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "order_update": OrderUpdatePayload,
    "kill_switch": KillSwitchPayload,
    "kill_switch_resolved": KillSwitchPayload,
    "session_state": SessionStatePayload,
    "ticker": TickerPayload,
    "position_update": PositionUpdatePayload,
}


class AuthMessage(BaseModel):
    """WebSocket 최초 인증 메시지."""

    type: Literal["auth"]
    token: str


def user_channel(user_id: str) -> str:
    """채널 키는 users.id 내부 UUID 문자열이며 clerk_user_id가 아니다."""
    return f"{USER_CHANNEL_PREFIX}{user_id}"


def ticker_channel(symbol: str) -> str:
    """Bybit raw 심볼별 공개 ticker Redis 채널을 만든다."""
    return f"{TICKER_CHANNEL_PREFIX}{symbol}"
