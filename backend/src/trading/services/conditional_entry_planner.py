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
    as_market: bool = False


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


def _build_conditional_entry_key(
    session_id: UUID,
    trade_id: str,
    bar_time: datetime,
    stop_price: Decimal,
    quantity: Decimal,
    *,
    kind: Literal["cond", "condmkt"],
) -> str | None:
    """조건부 진입의 세션과 의도를 idempotency key 에 보존한다.

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
    key = f"live:{session_id}:{kind}:{bar_epoch}:{stop_price}:{quantity}:{trade_id}"
    # `condmkt`가 `cond`보다 길다. 긴 쪽을 기준으로 검사해 조건부와 시장가 전환이
    # 같은 trade_id에서 함께 발주 가능하거나 함께 거부되게 한다.
    longest_key = f"live:{session_id}:condmkt:{bar_epoch}:{stop_price}:{quantity}:{trade_id}"
    if len(longest_key) > _IDEMPOTENCY_KEY_MAX_LENGTH:
        return None
    return key


def build_conditional_entry_key(
    session_id: UUID,
    trade_id: str,
    bar_time: datetime,
    stop_price: Decimal,
    quantity: Decimal,
) -> str | None:
    """Resting 조건부 진입용 idempotency key를 만든다."""
    return _build_conditional_entry_key(
        session_id,
        trade_id,
        bar_time,
        stop_price,
        quantity,
        kind="cond",
    )


def build_market_converted_entry_key(
    session_id: UUID,
    trade_id: str,
    bar_time: datetime,
    stop_price: Decimal,
    quantity: Decimal,
) -> str | None:
    """돌파된 조건부 진입을 시장가로 전환할 때의 별도 key를 만든다."""
    return _build_conditional_entry_key(
        session_id,
        trade_id,
        bar_time,
        stop_price,
        quantity,
        kind="condmkt",
    )


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
    reference_price: Decimal | None = None,
    max_breach_pct: Decimal | None = None,
    allow_market_conversion: bool = True,
) -> ReconcilePlan:
    """조건부 진입 desired 상태를 거래소 실제와 비교해 결정론적 계획을 만든다.

    돌파 부등식은 시각 τ의 `reference_price`를, 백테스트 `try_fill`은 완성 bar의
    `high`/`low`를 본다. 미돌파 주문의 거래소 intrabar 트리거와 둘을 합치면 시뮬 조건을
    덮고, 양쪽 모두 등호 포함이라 경계도 어긋나지 않는다.

    Args:
        current_position: 거래소 **순** 포지션 (long +, short -, flat 0). one-way 모드
            전제다(실측 `positionIdx=0`). hedge 모드는 이 함수의 적용 대상이 아니다.
        qty_step / price_tick: 거래소 눈금. 비교 전 양쪽을 같은 눈금으로 내려놓기 위한
            것이지 발주 정밀도가 아니다(발주 정밀도는 provider 의 ccxt 가 적용한다).
        allow_market_conversion: 기준가가 거래소 last에서 왔을 때만 돌파 주문을 시장가로
            전환한다. False면 기존처럼 돌파를 발산으로 기록하고 등재하지 않는다.
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
        # 이미 돌파된 트리거는 거래소가 받지 않는다.
        # 롱 stop 은 트리거가 > 현재가, 숏 stop 은 트리거가 < 현재가여야 한다. 가격이
        # 피벗을 이미 지나가면 시뮬은 `low <= stop` 으로 즉시 체결로 보는데 거래소는
        # long RISE는 retCode 110092("expect Rising")이고 short FALL은 110093
        # ("expect Falling")으로 거부한다. 매 tick 재시도하면 거부 행만 쌓인다.
        # 참조가 미지정이면 이 검사를 건너뛴다 - 기존 호출자 무영향.
        convert_to_market = False
        if reference_price is not None and reference_price > 0:
            breached = (
                pending.direction == "long" and pending.stop_price <= reference_price
            ) or (pending.direction == "short" and pending.stop_price >= reference_price)
            if breached and (matching_actual or not allow_market_conversion):
                divergences.append(
                    {
                        "trade_id": pending.trade_id,
                        "reason": "trigger_already_breached",
                        "direction": pending.direction,
                        "stop_price": str(pending.stop_price),
                        "reference_price": str(reference_price),
                        "had_resting": bool(matching_actual),
                    }
                )
                to_cancel.extend(matching_actual)
                continue
            if breached:
                breach_pct = abs(reference_price - pending.stop_price) / reference_price * Decimal(
                    "100"
                )
                if max_breach_pct is not None and breach_pct > max_breach_pct:
                    divergences.append(
                        {
                            "trade_id": pending.trade_id,
                            "reason": "breach_exceeds_cap",
                            "direction": pending.direction,
                            "stop_price": str(pending.stop_price),
                            "reference_price": str(reference_price),
                            "breach_pct": str(breach_pct),
                            "max_breach_pct": str(max_breach_pct),
                        }
                    )
                    continue
                convert_to_market = True

        # ★전략이 의도한 포지션 자체가 거래소 눈금으로 표현 불가능한 경우.
        # 잔여 드리프트(목표에 거의 도달해 남은 차이가 눈금 미만)와는 다르다 - 이쪽은
        # 그 전략이 이 계정에서 **영원히 한 주도 못 낸다**는 뜻이다. 조용히 넘기면
        # 화면엔 "대기 중인 조건부 진입" 이 뜨는데 주문은 안 나가는 "되는 척" 이 된다.
        # 실측으로 걸렸다 - 시드 전략의 position_size_pct 가 0.01% 라 목표가
        # 0.00029138 이고 BTCUSDT 스텝은 0.001 이었다.
        if pending.target_position != 0 and _normalize(
            abs(pending.target_position), qty_step
        ) == Decimal("0"):
            divergences.append(
                {
                    "trade_id": pending.trade_id,
                    "reason": "below_exchange_minimum",
                    "target_position": str(pending.target_position),
                    "qty_step": str(qty_step),
                }
            )
            to_cancel.extend(matching_actual)
            continue

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
            as_market=convert_to_market,
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
