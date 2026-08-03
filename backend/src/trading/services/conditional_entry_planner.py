# 조건부 진입 주문의 desired 상태와 거래소 실제 상태를 순수하게 reconcile 계획으로 변환한다

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

if TYPE_CHECKING:
    # ★런타임 import 로 두지 마라 (BL-536 R2).
    #
    # 이 모듈은 순수 계획기이고 `PendingOrderSnapshot` 을 **타입으로만** 쓴다
    # (`plan_reconcile` 의 `desired` 주석 하나). 그런데 런타임 import 로 두면 이 모듈을
    # import 하는 **모든** 곳이 `pine_v2` 인터프리터 전체를 함께 끌고 온다 —
    # 실측으로 `event_loop`/`interpreter`/`stdlib`/`sizing`/`rendering` 등 **8 모듈**이
    # `src.tasks.live_signal` 의 top-level 폐포에 새로 들어왔다(6 -> 14).
    #
    # 그것이 위험한 이유는 celery worker 가 `backend/src` 를 bind-mount + watchfiles 로
    # 물기 때문이다. `event_loop.py` 편집 중간 상태가 지금까지는 **한 세션의 평가 실패**
    # (그래서 fail-closed 비활성화가 돌 수 있었다)였는데, top-level 로 올리면
    # **`src.tasks.live_signal` 모듈 import 실패 = celery 태스크 미등록**이 된다.
    # 그러면 비활성화 코드조차 안 돌고 beat 는 계속 큐에 쌓는다.
    #
    # `from __future__ import annotations` 가 있어 주석은 문자열로 남으므로 런타임에
    # 이 이름이 필요 없다. 아무도 이 모듈에서 `PendingOrderSnapshot` 를 import 하지 않는다
    # (grep 확인). 회귀 방어는 `tests/tasks/test_live_signal_import_blast_radius.py`.
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
    """거래소에 새로 등재할 조건부 진입 주문.

    ★`take_profit`/`stop_loss`/`trailing_stop` 은 **판단 없이 통과**시킨다. 계획기는 순수
    함수로 남고, 무엇을 드롭할지는 라이브 태스크의 게이트가 정한다(거래소 제약이라
    계획기의 관심사가 아니다).

    ★`crosses_zero`/`overshoot_ratio`/`resulting_position_qty` 는 **파생값이지 결정이
    아니다**. 수량 산식(`abs(target_position - current_position)`)도 `reduce_only=False`도
    그대로다 — BL-516 은 "합쳐진 주문 1건" 을 고치기 전에 **크기부터 재기로** 판정했다.

    ★★BL-562 — 이 셋은 전부 **등재 시점 근사**다. 조건부 주문은 거래소에서 트리거될
    때까지 대기하고, 그 사이 포지션이 움직이면 값이 낡는다. 노출 폭은 두 층이다:
      (a) 보통은 **다음 reconcile tick 이 걷어낸다** — 수량이
          `|target - current_position|` 이라 포지션이 움직이면 비교 튜플(`:542-547`)이
          어긋나 resting 을 취소하고 새 값으로 재등재한다.
      (b) 목표와 실포지션이 같은 폭으로 움직여 **튜플이 그대로면 재등재가 없다** —
          그때는 등재 시점 판정이 트리거까지 살아남는다.
    (b) 는 **캡·게이트 B 로는** 못 고친다: 주문은 이미 거래소에 있고 `tpSize` 는 등재할
    때 확정되므로 체결 시점에 다시 판정해도 바꿀 것이 없다. 고정 테스트 =
    `tests/trading/test_conditional_entry_planner.py` 의 BL-562 두 건.

    ★**계측은 다르다** — 반전 크기는 체결 후 실제 포지션으로 다시 잰다
    (`qb_live_conditional_reversal_filled_total`, 발화는
    `tasks/trading.py:_enqueue_conditional_reversal_measure`). 여기 값들은 **등재 판정용**
    이고, "실제로 얼마나 큰 반전이 체결됐나" 의 답은 그쪽 counter 다.
    """

    trade_id: str
    direction: EntryDirection
    side: EntrySide
    quantity: Decimal
    trigger_price: Decimal
    trigger_direction: int
    comment: str
    as_market: bool = False
    # BL-523 — 엔진이 이 진입에 붙여 둔 exit 레벨. 조건부 진입에서는 지금 **항상 None** 이다
    # (`PendingOrderSnapshot` docstring 참조). 그 "항상 None" 을 관측 가능하게 만드는 것이
    # 이 배관의 목적이다.
    take_profit: Decimal | None = None
    stop_loss: Decimal | None = None
    trailing_stop: Decimal | None = None
    # BL-516 안 3 — 반전 계측. `crosses_zero` 는 목표와 실포지션의 부호가 교차한다는 뜻이고,
    # `overshoot_ratio` 는 `quantity / |target_position|` (1.0 = 순수 진입)이다.
    # `target_position` 이 0 이면 비율을 정의할 수 없어 None 이다.
    crosses_zero: bool = False
    overshoot_ratio: Decimal | None = None
    # 이 주문이 체결된 뒤의 포지션 크기. tpSize 정합 게이트의 분모다.
    # ★`abs(target_position)` 이 아니라 `|current_position ± quantity|` 다 — 발주 수량은
    # 거래소 눈금으로 절삭되므로(percent_of_equity 사이징은 소수 20자리를 만든다) 목표를
    # 그대로 쓰면 눈금 미정렬 목표를 가진 **순수 진입까지** 불일치로 보인다.
    resulting_position_qty: Decimal = Decimal("0")


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


LiveEntryKind = Literal["cond", "condmkt", "entry"]

LIVE_ENTRY_KEY_PREFIX = "live:"
CONDITIONAL_ENTRY_KINDS: tuple[LiveEntryKind, ...] = ("cond", "condmkt")
# 시장가 진입 key 는 `live:<sess>:<bar_time ISO>:<seq>:entry:<trade_id>` 다
# (`tasks/live_signal._build_idempotency_key`). ISO 시각이 `:` 를 포함하므로 split 이
# 아니라 이 마커로 가른다. `trade_id` 는 Pine 사용자 입력이라 `:` 를 포함할 수 있어
# **마커 뒤 전부**가 id 다.
_MARKET_ENTRY_MARKER = ":entry:"


@dataclass(frozen=True, slots=True)
class ParsedLiveEntryKey:
    """우리가 만든 라이브 **진입** 주문 key 를 되짚은 결과 (BL-536).

    ★이 타입이 존재하는 이유는 파서를 세 벌로 늘리지 않기 위해서다. 진입 완결성 분해는
    `session_id`/`trade_id` 만으로는 부족하고 `kind`(조건부인가 시장가 전환인가)와
    `bar_epoch`(같은 trade_id 의 재발행을 시간순으로 세우는 축)가 필요하다. 그래서
    형식 판정 자리를 옮기지 않고 **이 파일 하나에서 필드를 더 준다** —
    `parse_conditional_entry_key` 와 `live_signal._pine_trade_id_from_order_key` 는
    둘 다 여기로 위임한다.

    ★`bar_epoch` 는 **관용적으로** 판독한다. int 로 안 읽히면 `None` 이고 파싱은 계속
    성공한다. 엄격하게 막으면 BL-544 의 공백 재개 seed 가 legacy/비정규 key 앞에서
    fail-closed 로 떨어져 **세션이 계속 죽는다** — 그 함수의 기존 동작은 epoch 를 아예
    검사하지 않았다. 계약은 "논리 정수만 보존" 이다: `001`/`+1` 같은 비정규 표기도
    받아들이므로 **문자열 왕복은 보장하지 않는다**(codex G1 Q5).

    ★`close` key 는 여기서 `None` 으로 떨어진다. `:entry:` 마커가 없기 때문이며,
    기존 파서 두 벌의 동작과 정확히 같다. 청산은 진입이 아니다.
    """

    session_id: UUID
    kind: LiveEntryKind
    trade_id: str
    bar_epoch: int | None
    # 조건부 계열에만 있다 (시장가 진입 key 는 두 값을 싣지 않는다).
    trigger: str | None
    quantity: str | None


def _lenient_int(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _market_entry_bar_epoch(head: str) -> int | None:
    """`<bar_time ISO>:<seq>` 앞부분에서 bar epoch 를 관용 판독한다. 실패하면 None."""
    iso, separator, _sequence_no = head.rpartition(":")
    if not separator:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp())
    except (TypeError, ValueError):
        return None


def parse_live_entry_key(key: str | None) -> ParsedLiveEntryKey | None:
    """우리가 만든 라이브 진입 key 세 형식을 되짚는 **유일한** 자리.

    - 조건부 진입   `live:<sess>:cond:<bar_epoch>:<stop>:<qty>:<trade_id>`
    - 시장가 전환   `live:<sess>:condmkt:<bar_epoch>:<stop>:<qty>:<trade_id>`
    - 시장가 진입   `live:<sess>:<bar_time ISO>:<seq>:entry:<trade_id>`

    셋 다 아니면 `None` — 청산 key, 웹훅 주문, 수동 주문이 전부 여기로 떨어진다.
    호출부는 그것을 "우리 진입이 아님" 으로 세야지 조용히 버리면 안 된다.
    """
    if not key or not key.startswith(LIVE_ENTRY_KEY_PREFIX):
        return None
    session_part, separator, rest = key[len(LIVE_ENTRY_KEY_PREFIX) :].partition(":")
    if not separator:
        return None
    try:
        session_id = UUID(session_part)
    except (TypeError, ValueError):
        return None

    for kind in CONDITIONAL_ENTRY_KINDS:
        marker = f"{kind}:"
        if not rest.startswith(marker):
            continue
        # 앞의 세 구분자만 분리하고 나머지는 trade id 그대로 보존한다.
        parts = rest[len(marker) :].split(":", 3)
        if len(parts) != 4 or not all(parts):
            return None
        return ParsedLiveEntryKey(
            session_id=session_id,
            kind=kind,
            trade_id=parts[3],
            bar_epoch=_lenient_int(parts[0]),
            trigger=parts[1],
            quantity=parts[2],
        )

    index = rest.find(_MARKET_ENTRY_MARKER)
    if index == -1:
        return None
    trade_id = rest[index + len(_MARKET_ENTRY_MARKER) :]
    if not trade_id:
        return None
    return ParsedLiveEntryKey(
        session_id=session_id,
        kind="entry",
        trade_id=trade_id,
        bar_epoch=_market_entry_bar_epoch(rest[:index]),
        trigger=None,
        quantity=None,
    )


def is_conditional_entry_key(key: str | None) -> bool:
    """key가 우리 조건부 진입 또는 시장가 전환 주문인지 판정한다."""
    parsed = parse_live_entry_key(key)
    return parsed is not None and parsed.kind in CONDITIONAL_ENTRY_KINDS


def conditional_entry_key_like(session_id: UUID, kind: LiveEntryKind) -> str:
    """고정 세션에서 조건부 진입 kind의 key를 찾는 SQL LIKE 패턴을 만든다.

    이 LIKE는 `session_id`가 고정됐을 때만 정확하다. `trade_id`는 Pine 사용자 입력이라
    `:`를 포함할 수 있으므로, 세션을 고정하지 않은 kind 판정은 SQL이 아니라
    `parse_live_entry_key`가 한다.
    """
    return f"{LIVE_ENTRY_KEY_PREFIX}{session_id}:{kind}:%"


def parse_conditional_entry_key(key: str | None) -> tuple[UUID, str] | None:
    """**resting** 조건부 진입 key에서 세션과 Pine trade id를 복원한다.

    ★`condmkt` 를 계속 거부한다. 시장가 전환 주문은 `trigger_price` 가 없어 호가창에
    남지 않으므로 reconcile 의 `actual` 이나 orphan sweep 의 대상이 아니다. 이 함수를
    넓히면 그 주문들이 취소 대상으로 끌려 들어온다.

    형식 판정 자체는 `parse_live_entry_key` 하나로 유지한다 (BL-536).
    """
    parsed = parse_live_entry_key(key)
    if parsed is None or parsed.kind != "cond":
        return None
    return parsed.session_id, parsed.trade_id


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
    max_reversal_overshoot_ratio: Decimal | None = None,
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
        max_reversal_overshoot_ratio: `quantity / |target_position|` 의 상한. None(기본)이면
            비활성이라 기존 동작과 byte-identical 이다. 초과하면 등재하지 않고 발산으로
            기록한다 — 반전 주문 1건이 청산과 진입을 합쳐 내는 크기를 사용자가 **선택적으로**
            제한하는 안전밸브이지, 수량 산식을 바꾸는 장치가 아니다.
            ★★BL-562 — 이 캡은 **등재 시점 근사**다. `current_position` 을 등재하는 그
            순간에만 보고, 조건부 주문은 트리거까지 대기하므로 체결 시점의 실제 반전 크기는
            이보다 클 수도 작을 수도 있다. **체결 시점 보장이 아니다** — 그 시점엔 주문이
            이미 거래소에 있어 크기를 못 바꾼다. 상세는 `PlannedConditionalEntry` docstring.
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
            breached = (pending.direction == "long" and pending.stop_price <= reference_price) or (
                pending.direction == "short" and pending.stop_price >= reference_price
            )
            # ★★BL-589 — 시장가 전환을 막는 것은 "대기 주문이 있다" 가 아니라 **"그 대기
            # 주문이 발화했을 수 있다"** 다. 배제의 원래 근거(PR #493)는 "거래소가 이미 그
            # 주문을 트리거했을 확률이 높아 취소+시장가는 이중 진입이 된다" 였는데, 그 확률은
            # 대기 주문 **자신의** 트리거가 뚫렸을 때만 0 이 아니다.
            #
            # 실측(2026-08-03 소크 T0+65분 사망): 피벗이 62811.5 -> 62661.71 로 내려가
            # 새 트리거가 현재가 62700 **아래**라 stop 으로 못 걸었는데, 올라가 있던 대기
            # 주문의 트리거는 62811.5 라 **한 번도 닿은 적이 없었다**. 그런데도 전환이 꺼져
            # 드롭됐고, 시뮬은 `low <= stop` 으로 이미 진입을 잡은 뒤였다 -> 엔진 롱 /
            # 거래소 숏 -> `direction` 발산 2회 연속 -> fail-closed.
            #
            # ★드롭 쪽이 손해보는 일은 없다 — 두 갈래 모두 `matching_actual` 을 취소하므로,
            # 전환이 하류 가드(미지 interval / 최근 전환 중복 / 돌파 해소 / breach cap)에
            # 걸려 무산되면 결과는 기존 드롭과 같다.
            resting_could_have_fired = any(
                (entry.side == "buy" and entry.stop_price <= reference_price)
                or (entry.side == "sell" and entry.stop_price >= reference_price)
                for entry in matching_actual
            )
            if breached and (resting_could_have_fired or not allow_market_conversion):
                divergences.append(
                    {
                        "trade_id": pending.trade_id,
                        "reason": "trigger_already_breached",
                        "direction": pending.direction,
                        "stop_price": str(pending.stop_price),
                        "reference_price": str(reference_price),
                        "had_resting": bool(matching_actual),
                        # ★`had_resting` 만으로는 "발화 가능한 대기 주문이 막았다"(정당한
                        # 보호)와 "전환 자체가 꺼져 있었다"(기준가 열화)가 구별되지 않는다.
                        "resting_could_have_fired": resting_could_have_fired,
                    }
                )
                to_cancel.extend(matching_actual)
                continue
            if breached:
                breach_pct = (
                    abs(reference_price - pending.stop_price) / reference_price * Decimal("100")
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

        # BL-516 안 3 — 이 주문이 청산과 진입을 합쳐 내는지, 합쳤다면 얼마나 큰지.
        # 부호 교차(`crosses_zero`)와 비율(`overshoot_ratio`)은 동치다: side 검사를 통과한
        # leg 는 목표가 항상 실포지션의 진행 방향에 있으므로 비율 > 1 은 교차일 때뿐이다.
        target_magnitude = abs(pending.target_position)
        crosses_zero = pending.target_position * current_position < 0
        overshoot_ratio = quantity / target_magnitude if target_magnitude > 0 else None
        if (
            crosses_zero
            and max_reversal_overshoot_ratio is not None
            and overshoot_ratio is not None
            and overshoot_ratio > max_reversal_overshoot_ratio
        ):
            # 등재를 거부하는 이상 이미 올라가 있는 같은 의도의 주문도 걷는다 — 남겨두면
            # 그게 체결돼 우리가 방금 거부한 반전을 그대로 실행한다.
            divergences.append(
                {
                    "trade_id": pending.trade_id,
                    "reason": "reversal_overshoot_exceeds_cap",
                    "direction": pending.direction,
                    "target_position": str(pending.target_position),
                    "current_position": str(current_position),
                    "quantity": str(quantity),
                    "overshoot_ratio": str(overshoot_ratio),
                    "max_reversal_overshoot_ratio": str(max_reversal_overshoot_ratio),
                }
            )
            to_cancel.extend(matching_actual)
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
            take_profit=pending.take_profit,
            stop_loss=pending.stop_loss,
            trailing_stop=pending.trailing_stop,
            crosses_zero=crosses_zero,
            overshoot_ratio=overshoot_ratio,
            resulting_position_qty=abs(
                current_position + (quantity if side == "buy" else -quantity)
            ),
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
        #
        # ★★BL-589 — **대기 stop 주문은 시장가 의도를 절대 만족시키지 못한다.** `as_market`
        # 은 위 등가 비교 축에 없어서, 눈금이 굵으면 둘이 "일치" 로 접힌다(실증: `price_tick`
        # 10 이면 desired stop 100 과 resting stop 108 이 둘 다 100 으로 정규화된다).
        # 그러면 아무것도 취소하지 않고 아무것도 등재하지 않아 **시장가로 나갔어야 할 진입이
        # 조용히 사라지고 대기 stop 만 남는다** — 고치려던 발산이 그대로 재발한다.
        # 이 구멍은 위 술어를 좁히기 전에는 도달 불가였다(전환과 대기 주문이 공존 못 했다).
        if planned.as_market or (
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
