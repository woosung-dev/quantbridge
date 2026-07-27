# 조건부 진입 주문의 desired 상태와 거래소 실제 상태를 순수하게 reconcile 계획으로 변환한다

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any, Literal
from uuid import UUID

from src.strategy.pine_v2.event_loop import PendingOrderSnapshot

EntryDirection = Literal["long", "short"]
EntrySide = Literal["buy", "sell"]


@dataclass(frozen=True)
class RestingConditionalEntry:
    """거래소에 현재 resting 중인 조건부 진입 주문의 최소 스냅샷.

    ★`stop_price`/`quantity` 는 **우리가 요청한 값**(`Order` 행)이어야 하고 거래소가
    되돌려준 값이 아니다. 거래소는 자기 정밀도로 절삭한 값을 echo 하므로(실측 DB
    `0.02953691` -> 거래소 `0.029`), echo 를 비교에 쓰면 우리 눈금과 거래소 눈금이라는
    **두 개의 SSOT** 가 생겨 영원히 불일치 -> 무한 cancel+place 가 된다.

    ★`reduce_only` 는 안전장치다. 계획기는 `reduce_only=True` 인 주문을 **절대 취소하지
    않는다** — 그건 TP/SL 이나 손절 레그이지 진입이 아니다. 상위 계층이 필터를 잘못
    넘겨도 사용자의 손절이 지워지지 않게 하는 마지막 방어선이다.
    """

    trade_id: str
    order_id: str
    exchange_order_id: str | None
    stop_price: Decimal
    quantity: Decimal
    side: EntrySide
    trigger_direction: int | None = None
    reduce_only: bool = False


@dataclass(frozen=True)
class PlannedConditionalEntry:
    """거래소에 새로 등재할 조건부 진입 주문."""

    trade_id: str
    direction: EntryDirection
    side: EntrySide
    quantity: Decimal
    trigger_price: Decimal
    trigger_direction: int
    comment: str


@dataclass(frozen=True)
class ReconcilePlan:
    """조건부 진입 reconcile의 취소, 등재, fail-closed 발산 결과."""

    to_cancel: tuple[RestingConditionalEntry, ...]
    to_place: tuple[PlannedConditionalEntry, ...]
    divergences: tuple[dict[str, Any], ...]


def entry_trigger_direction(direction: EntryDirection) -> int:
    """진입 방향의 Bybit v5 triggerDirection을 반환한다.

    `exit_order_mapping.trigger_direction_for`는 청산 side와 SL/TP 종류를 기준으로
    계산하므로 재사용하지 않는다. 예를 들어 long 청산 sell STOP_LOSS는 FALL(2)이지만,
    long 진입 breakout은 RISE(1)에서 trigger되어야 한다.
    """
    return 1 if direction == "long" else 2


# `Order.idempotency_key` 는 VARCHAR(200) 이다. 초과하면 Postgres 가
# StringDataRightTruncation 을 던지고 상위 except 가 그것을 삼켜, 엔진은 진입이
# 장전됐다고 믿는데 거래소엔 아무것도 없는 상태가 된다. 미리 잘라내고 거부한다.
_IDEMPOTENCY_KEY_MAX_LENGTH = 200


def build_conditional_entry_key(
    session_id: UUID,
    trade_id: str,
    bar_time: datetime,
    stop_price: Decimal,
    quantity: Decimal,
) -> str | None:
    """조건부 진입의 세션·의도를 마이그레이션 없이 idempotency key 에 보존한다.

    ★`bar_time` 이 들어가는 이유 — `OrderService.execute` 는 같은 key 를 다시 보면
    거래소로 **dispatch 하지 않고** 캐시된 응답을 돌려준다(`order_service.py:417-419`).
    key 가 `(trade_id, 가격, 수량)` 만으로 결정되면, 취소했다가 같은 의도로 재등재할 때
    거래소엔 아무것도 안 올라가는데 DB 와 metric 은 "등재됨" 이라고 보고한다.
    bar 단위로 갈라두면 같은 bar 안 재시도는 여전히 멱등이고, 다음 bar 의 재등재는
    실제로 나간다. 라이브 시그널 key 가 이미 같은 이유로 bar_time 을 싣는다.

    반환이 `None` 이면 그 레그는 발주하지 않는다 — 길이 초과와 빈 `trade_id` 는
    파서가 되짚지 못해 우리 주문을 영원히 남의 것으로 보게 만든다.
    """
    # trade_id 는 마지막 필드라 `:` 를 포함해도 되지만, 비어 있으면 파서가 되짚지 못한다.
    if not trade_id.strip():
        return None
    # ★bar_time 은 epoch 초로 싣는다. isoformat() 은 `:` 를 포함해 split 파싱을 깨뜨린다.
    bar_epoch = int(bar_time.timestamp())
    key = f"live:{session_id}:cond:{bar_epoch}:{stop_price}:{quantity}:{trade_id}"
    if len(key) > _IDEMPOTENCY_KEY_MAX_LENGTH:
        return None
    return key


def parse_conditional_entry_key(key: str | None) -> tuple[UUID, str] | None:
    """우리 조건부 진입 key에서 세션과 Pine trade id를 복원한다.

    `trade_id`는 Pine 사용자 입력이라 `:`를 포함할 수 있다. 따라서 앞의 다섯 구분자만
    분리하고 나머지는 trade id 그대로 보존한다. 이 형식 판정은 한 곳만 유지한다.
    """
    if not key:
        return None
    parts = key.split(":", 6)
    if (
        len(parts) != 7
        or parts[0] != "live"
        or parts[2] != "cond"
        or not parts[3]
        or not parts[4]
        or not parts[5]
        or not parts[6]
    ):
        return None
    try:
        return UUID(parts[1]), parts[6]
    except (TypeError, ValueError):
        return None


def _normalize(value: Decimal, step: Decimal) -> Decimal:
    """거래소 눈금으로 0 방향 절삭한다."""
    if step <= Decimal("0"):
        raise ValueError("step must be positive")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def plan_reconcile(
    *,
    desired: Sequence[PendingOrderSnapshot],
    actual: Sequence[RestingConditionalEntry],
    current_position: Decimal,
    qty_step: Decimal,
    price_tick: Decimal,
) -> ReconcilePlan:
    """조건부 진입 desired 상태를 거래소 실제와 비교해 결정론적 계획을 만든다.

    Args:
        current_position: 거래소 **순** 포지션 (long +, short -, flat 0). one-way 모드
            전제다(실측 `positionIdx=0`). hedge 모드는 이 함수의 적용 대상이 아니다.
        qty_step / price_tick: 거래소 눈금. 비교 전 양쪽을 같은 눈금으로 내려놓기 위한
            것이지 발주 정밀도가 아니다(발주 정밀도는 provider 의 ccxt 가 적용한다).
    """
    to_cancel: list[RestingConditionalEntry] = []
    to_place: list[PlannedConditionalEntry] = []
    divergences: list[dict[str, Any]] = []

    # ★안전장치 — reduce-only 주문은 진입이 아니다(TP/SL/손절 레그). 상위 계층이 필터를
    # 잘못 넘겨 섞여 들어와도 계획기가 그걸 취소 대상으로 삼지 않는다. 사용자 손절을
    # 지우는 것이 이 스프린트가 낼 수 있는 최악의 결함이라 마지막 방어선을 여기 둔다.
    actual_by_trade_id: dict[str, list[RestingConditionalEntry]] = {}
    for entry in actual:
        if entry.reduce_only:
            divergences.append(
                {
                    "trade_id": entry.trade_id,
                    "reason": "reduce_only_entry_ignored",
                    "order_id": entry.order_id,
                }
            )
            continue
        actual_by_trade_id.setdefault(entry.trade_id, []).append(entry)

    for pending in sorted(desired, key=lambda entry: entry.trade_id):
        matching_actual = actual_by_trade_id.pop(pending.trade_id, [])
        quantity = _normalize(abs(pending.target_position - current_position), qty_step)
        if quantity == Decimal("0"):
            # 목표와 실포지션이 이미 같다 = 낼 주문이 없다. 조용한 no-op 이지 발산이 아니다
            # (같은 id 재발행이 대표 사례 — 엔진도 close 후 재open 이라 순변화가 0이다).
            # 단 이미 등재된 주문이 있으면 반드시 걷어낸다. 남겨두면 그게 체결될 때
            # 거래소만 목표를 넘어간다.
            #
            # ★이 취소는 무음이면 안 된다. 이 분기에 떨어지는 경우가 셋인데 계획기는
            # 셋을 구분하지 못한다 - (i) 의도된 같은 id 재발행 (ii) 사용자 수동 거래
            # (iii) **엔진 지연**. (iii) 은 형제 pending 이 먼저 체결돼 실포지션이 목표에
            # 도달했지만 엔진이 아직 마지막 종료 바에 머물러 있는 상태다. 그때 이 취소는
            # 돌파 직후 다음 레그를 한 tick 동안 호가창에서 지운다(다음 tick 에 재등재).
            if matching_actual:
                divergences.append(
                    {
                        "trade_id": pending.trade_id,
                        "reason": "target_already_met_cancelled",
                        "target_position": str(pending.target_position),
                        "current_position": str(current_position),
                    }
                )
            to_cancel.extend(matching_actual)
            continue

        side: EntrySide = "buy" if pending.target_position > current_position else "sell"
        expected_side: EntrySide = "buy" if pending.direction == "long" else "sell"
        if side != expected_side:
            to_cancel.extend(matching_actual)
            divergences.append(
                {
                    "trade_id": pending.trade_id,
                    "reason": "entry_side_mismatch",
                    "direction": pending.direction,
                    "required_side": side,
                    # 숫자를 실어야 알림 받은 사람이 8 초과인지 800 초과인지 안다.
                    "target_position": str(pending.target_position),
                    "current_position": str(current_position),
                }
            )
            continue

        planned = PlannedConditionalEntry(
            trade_id=pending.trade_id,
            direction=pending.direction,
            side=side,
            quantity=quantity,
            trigger_price=_normalize(pending.stop_price, price_tick),
            trigger_direction=entry_trigger_direction(pending.direction),
            comment=pending.comment,
        )
        if len(matching_actual) != 1:
            to_cancel.extend(matching_actual)
            to_place.append(planned)
            continue

        current = matching_actual[0]
        # ★`trigger_direction` 을 비교에서 빼면 방향이 뒤집힌 채 등재된 주문(과거 버그
        # 또는 수동 등재)이 side/수량/가격만 맞으면 "일치" 로 판정돼 영원히 살아남는다.
        # 진입 트리거 방향은 이 스프린트가 BL-365 로 명시적으로 다루는 바로 그 축이다.
        # `None` 은 방향 미상 = 불일치로 본다(재등재해서 확정 상태로 만든다).
        if (
            current.side,
            _normalize(current.quantity, qty_step),
            _normalize(current.stop_price, price_tick),
            current.trigger_direction,
        ) != (planned.side, planned.quantity, planned.trigger_price, planned.trigger_direction):
            to_cancel.append(current)
            to_place.append(planned)

    for unmatched in actual_by_trade_id.values():
        to_cancel.extend(unmatched)

    return ReconcilePlan(
        to_cancel=tuple(sorted(to_cancel, key=lambda entry: entry.trade_id)),
        to_place=tuple(sorted(to_place, key=lambda entry: entry.trade_id)),
        divergences=tuple(divergences),
    )
