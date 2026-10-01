"""푸시 트리거 측 진입점 — §4.3 페이로드 조립 + Celery enqueue (pwa.md §3.5 · §4.3).

★호출부(`publish_realtime` · `BacktestService.run`)는 이 모듈의 예외를 **반드시** 삼킨다 —
푸시는 부가 경로이고 본 경로(체결 전이·백테스트 결과)를 깨뜨리면 안 된다.
★잠금 화면 노출 대비 **금액·잔고·손익은 본문에 넣지 않는다**(심볼·방향·상태만).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.notifications.webpush_client import load_vapid_config
from src.trading.models import KillSwitchTriggerType, OrderState

PushPayload = dict[str, str]

TEST_PUSH_PAYLOAD: PushPayload = {
    "title": "QuantBridge 테스트 알림",
    "body": "알림이 정상 동작합니다",
    "url": "/dashboard",
    "tag": "test",
}

_ORDER_PUSH_TITLES: dict[str, str] = {
    OrderState.filled.value: "주문 체결",
    OrderState.rejected.value: "주문 거부",
}

# FE `apps/web/src/features/trading/labels.ts` `KS_TRIGGER_LABELS` 와 같은 문구 — 모르는 값은 원문.
_KILL_SWITCH_TRIGGER_LABELS: dict[str, str] = {
    KillSwitchTriggerType.daily_loss.value: "일일 손실 한도 초과",
    KillSwitchTriggerType.cumulative_loss.value: "누적 손실 한도 초과",
    KillSwitchTriggerType.api_error.value: "거래소 API 오류",
}


def realtime_push_payload(event_type: str, payload: Mapping[str, Any]) -> PushPayload | None:
    """실시간 이벤트 → 푸시 페이로드. 알릴 이벤트가 아니면 None.

    ★주문 상태 키는 `state` 다(`realtime/schemas.py` `OrderUpdatePayload`) — 스펙 문구의 `status` 가 아니다.
    """
    if event_type == "order_update":
        title = _ORDER_PUSH_TITLES.get(str(payload.get("state")))
        if title is None:
            return None
        return {
            "title": title,
            "body": f"{payload.get('symbol')} {payload.get('side')}",
            "url": "/trading",
            "tag": f"order:{payload.get('order_id')}",
        }
    if event_type == "kill_switch":
        trigger = str(payload.get("trigger_type"))
        return {
            "title": "킬 스위치 발동",
            "body": _KILL_SWITCH_TRIGGER_LABELS.get(trigger, trigger),
            "url": "/trading",
            "tag": "kill_switch",
        }
    return None


def backtest_finished_payload(
    backtest_id: UUID, *, succeeded: bool, strategy_name: str
) -> PushPayload:
    return {
        "title": "백테스트 완료" if succeeded else "백테스트 실패",
        "body": strategy_name,
        "url": f"/backtests/{backtest_id}",
        "tag": f"backtest:{backtest_id}",
    }


def enqueue_push(user_id: str, payload: PushPayload) -> None:
    """`notifications.send_push` 를 enqueue 한다.

    ★VAPID 가 없으면 **enqueue 도 하지 않는다** — 꺼진 기능이 브로커에 빈 작업을 쌓지 않게.
    """
    if load_vapid_config() is None:
        return
    from src.tasks.notifications import send_push_task  # 지연 import (순환 방지)

    send_push_task.delay(user_id, payload)
