# 진입 원장 한 창을 시도 단위와 에피소드 단위로 분해한다 — 유실의 "크기" 를 재는 순수 계산

"""라이브 진입 완결성 분해 (BL-536 계측기).

이 모듈은 아무것도 고치지 않는다. 진입 주문 원장 한 창을 받아 **두 개의 서로 다른
분모**로 분해할 뿐이다. 하나의 숫자로 답하지 않는 것이 설계 전체다.

- 층위 1 (발주 시도) — 주문 행 하나 = 시도 하나. 분모가 자명하고 해석 여지가 없다.
  이 층위가 **바닥 진실**이다.
- 층위 2 (진입 에피소드) — 같은 `(session_id, trade_id)` 의 연속 행을 끊어 만든 구간.
- 층위 3 (유실 채널, BL-522) — "왜 유실됐나" 의 분해. **상호배타가 아니고** 원장 밖 채널
  (C5)이 섞여 있어 층위 1·2 와도, 자기들끼리도 합산 불가다. `ChannelTable` 참조.

★**두 층위를 합산하지 마라.** 그래서 이 모듈은 두 층위를 하나로 묶는 합계를 제공하지
않는다 - 타입으로 막는다. 계측 counter(`qb_live_conditional_plan_drop_evaluations_total`
등)와도 합산 대상이 아니다. 그쪽은 "평가 발화 횟수" 라 중복을 포함한다.

## 왜 에피소드가 필요하고, 왜 그것만으로는 부족한가

`trade_id` 는 진입 1건의 식별자가 **아니다**. 엔진이 같은 id 의 pending stop 을 매 bar
덮어쓰며 재발행하고(`strategy_state.py` 의 "기존 동일 id pending 있으면 갱신 - Pine
re-issue 의미론"), 체결되면 `to_remove` 로 지운 뒤 나중에 같은 id 로 다시 진입한다.
실측 24h 표본에서 진입 42 주문의 `trade_id` 는 단 2 개였다. 그래서:

- `(session_id, trade_id)` 로 **한 번만** 묶으면 표본 전체가 에피소드 2 개가 되고 둘 다
  체결을 포함해 **유실률이 0% 로 소멸한다.** 체결에서 끊는 것이 이 층위의 전부다.
- 반대로 `(session_id, trade_id, bar_epoch)` 로 묶으면 **층위 1 과 동치**가 된다
  (실측: 22 주문 = 22 distinct bar_epoch). 새 층위가 아니다.

두 극단 사이에서 어디를 끊을지가 유일한 판단이고, 그 판단이 숫자를 바꾼다. 그래서
**한 규칙을 고르고 반대 해석의 수치를 함께 낸다** — `EpisodeRule` 두 값이 그것이다.
"""

from __future__ import annotations

from collections import Counter as _Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from uuid import UUID

from src.trading.models import OrderState
from src.trading.services.conditional_entry_planner import (
    LiveEntryKind,
    parse_live_entry_key,
)


class CounterBasis(StrEnum):
    """Prometheus counter 값을 **무엇으로 읽었는가**. 비교 가능 여부가 여기서 갈린다.

    ★★이 타입이 존재하는 이유가 이 스프린트의 주제 그 자체다 (R1).

    실측에서 `qb_live_conditional_placed_total{long+short}` = 126 인데
    `guard{conditional_placed}` 92 + `guard{market_converted}` 7 = **99** 였다. 27 이 남는다.
    두 counter 는 `live_signal.py` 의 **인접 두 줄**에서 무조건 함께 오르므로 구조적
    항등식은 성립한다. 그런데도 절대값이 어긋난 이유는 **출생일이 다르기 때문**이다:

        qb_live_conditional_placed_total  <- 30031efe (PR #489, 2026-07-27)
        qb_live_conditional_guard_total   <- 274dc645 (PR #493, 2026-07-28)  # 하루 뒤

    그 사이 5 커밋 동안 `placed_total` 은 **guard 가 존재하지도 않던 구간**을 홀로 쌓았다.
    그리고 그 값은 지워지지 않는다 — `metrics_multiproc.configure_multiprocess` 는
    mmap 디렉터리를 `makedirs(exist_ok=True)` 할 뿐 **비우지 않고**,
    `mark_metrics_process_dead` 는 live gauge 파일만 지운다. counter 파일은 배포를 넘어 산다.

    ★따라서 일반 규칙은 이것이다 — **서로 다른 시점에 도입된 두 counter 는 절대값 비교가
    구조적으로 불가능하다.** 같은 mmap 디렉터리를 공유해도 **유효 시작점이 다르다.**
    두 counter 가 모두 존재하는 창의 **차분**만 비교 가능하다.

    이 규칙을 주석이나 경고 문구로 두지 않고 **타입으로** 만든 이유 — 이 레포는 이미
    "수용 기준은 자기 집행되지 않는다" 를 배웠다. 아래 `CrossCounterCheck` 를 만드는
    함수들은 `basis is delta` 가 아니면 **숫자를 내지 않고 거부**한다.
    """

    delta = "delta"
    absolute = "absolute"
    # ★before 스냅샷은 **있는데** 그 series 만 없다 (R2-④). 없는 key 를 0 으로 읽으면
    #   `after - 0 = 절대값` 이 `delta` 로 위장한다 — 그리고 그 상황이 정확히 이 가드가
    #   겨냥한 것이다(**counter 가 태어나기 전에 뜬 스냅샷**). 그래서 별도 basis 다.
    unknown = "unknown"
    # ★차분이 음수다 (R2-⑤). 창 중간 재배포·mmap 재생성이면 counter 가 리셋된다.
    #   음수를 그대로 쓰면 `원장 >= 음수` 가 무조건 성립해 **부등식의 검정력이 0** 이 된다.
    #   절대값은 거부하면서 음수는 통과시키는 비대칭을 남기지 않는다.
    counter_reset = "counter_reset"


# 알려진 counter 도입 시점. ★**집행은 이 표에 의존하지 않는다** — 거부 규칙은
# `basis` 하나로 구조적으로 돌아간다. 이 표는 거부 사유를 사람에게 설명할 때 쓰는
# **증거**이고, 새 counter 가 늘어도 규칙은 그대로 유효하다.
COUNTER_INTRODUCED: dict[str, str] = {
    "qb_live_conditional_placed_total": "30031efe (PR #489, 2026-07-27)",
    "qb_live_conditional_guard_total": "274dc645 (PR #493, 2026-07-28)",
}


@dataclass(frozen=True, slots=True)
class CounterReading:
    """counter 하나를 읽은 결과. **어떻게 읽었는지**를 값과 분리 불가능하게 묶는다.

    ★단일 스냅샷에서 온 값을 `delta` 로 라벨하면 안 된다. 그것이 정확히 이번 재지시가
    잡은 결함이다 — 도구가 절대값을 "차분" 이라고 출력하고 있었다.
    """

    name: str
    value: float
    basis: CounterBasis

    @property
    def comparable(self) -> bool:
        """다른 counter 와 비교해도 되는가. 절대값은 유효 시작점을 모르므로 안 된다."""
        return self.basis is CounterBasis.delta

    @property
    def origin_note(self) -> str:
        introduced = COUNTER_INTRODUCED.get(self.name)
        return f" (도입 {introduced})" if introduced else ""


@dataclass(frozen=True, slots=True)
class CrossCounterCheck:
    """두 counter 를 비교한 결과. **비교 불가면 숫자가 아니라 거부**를 돌려준다.

    `holds` 가 `None` 인 것과 `False` 인 것은 다르다 — 전자는 "판정하지 않았다",
    후자는 "판정했고 깨졌다" 이다. 둘을 같은 값으로 뭉개면 거부가 통과로 읽힌다.
    """

    label: str
    comparable: bool
    holds: bool | None
    detail: str


_REFUSAL_REASON: dict[CounterBasis, str] = {
    CounterBasis.absolute: "절대값(유효 시작점 미상)",
    CounterBasis.unknown: "before 스냅샷에 그 series 가 없다 = counter 도입 전 스냅샷일 수 있다",
    CounterBasis.counter_reset: "차분이 음수 = 창 중간에 counter 가 리셋됐다",
}


def _refusal(label: str, readings: Sequence[CounterReading]) -> CrossCounterCheck:
    # 같은 counter 를 label 만 달리 읽은 경우가 흔하다(guard 의 두 outcome). 이름 기준으로
    # 중복을 걷어 운영자가 **몇 개의 counter 가 문제인지**를 바로 읽게 한다.
    offenders: list[str] = []
    for reading in readings:
        if reading.comparable:
            continue
        reason = _REFUSAL_REASON.get(reading.basis, reading.basis.value)
        entry = f"{reading.name}{reading.origin_note} [{reason}]"
        if entry not in offenders:
            offenders.append(entry)
    names = " · ".join(offenders)
    return CrossCounterCheck(
        label=label,
        comparable=False,
        holds=None,
        detail=(
            "★비교 거부 — 이 값들은 같은 창의 차분이 아니다. 서로 다른 시점에 도입된 "
            "counter 는 절대값 비교가 구조적으로 불가능하다. 두 스냅샷을 주고 차분으로 "
            f"비교해라. 문제 counter: {names}"
        ),
    )


def placement_identity_check(
    *,
    placed: CounterReading,
    conditional_placed: CounterReading,
    market_converted: CounterReading,
) -> CrossCounterCheck:
    """③-c(a) — `placed_total{long+short} == guard{conditional_placed} + guard{market_converted}`.

    ★구조적으로는 항등식이다. `live_signal.py` 의 인접 두 줄이 `order_service.execute`
    직후에 무조건 함께 오르고, `placed_total` 은 방향으로 · guard 는 조건부/전환으로
    같은 사건을 쪼갤 뿐이다.

    ★그러나 **절대값으로는 검산할 수 없다.** 두 counter 의 출생일이 다르기 때문이며,
    실측 126 vs 99 의 27 이 정확히 그 차이다. 그래서 basis 를 먼저 본다.
    """
    label = "placed_total{long+short} == guard{conditional_placed} + guard{market_converted}"
    readings = (placed, conditional_placed, market_converted)
    if not all(reading.comparable for reading in readings):
        return _refusal(label, readings)
    guard_sum = conditional_placed.value + market_converted.value
    holds = placed.value == guard_sum
    return CrossCounterCheck(
        label=label,
        comparable=True,
        holds=holds,
        detail=(
            f"{placed.value} == {conditional_placed.value} + {market_converted.value}"
            f" = {guard_sum} -> {'성립' if holds else '★깨짐'}"
        ),
    )


def cancel_inequality_check(
    *, ledger_cancelled: int, replaced: CounterReading
) -> CrossCounterCheck:
    """③-b — `원장 cancelled >= counter{replaced} 차분` 과 그 잔차(미계측 취소).

    ★항등식이 아니다. `transition_to_cancelled` 호출부 9 곳 중 counter 를 올리는 곳은
    1 곳뿐이고 `Order` 에 취소 사유 컬럼이 없다. 그래서 원장이 구조적으로 크거나 같다.

    ★여기도 절대값을 받으면 거부한다. 원장 쪽은 **창으로 자른 값**인데 counter 쪽만
    프로세스 수명 누적이면 부등식이 항상 성립해 **검정력이 0** 이 된다.
    """
    label = "원장 cancelled >= counter{replaced}"
    if not replaced.comparable:
        return _refusal(label, (replaced,))
    holds = ledger_cancelled >= replaced.value
    residual = ledger_cancelled - replaced.value
    return CrossCounterCheck(
        label=label,
        comparable=True,
        holds=holds,
        detail=(
            f"{ledger_cancelled} >= {replaced.value} -> "
            f"{'성립' if holds else '★깨짐 - counter 또는 조회 창이 틀렸다는 신호다'}"
            f" · 미계측 취소(잔차) = {residual}"
        ),
    )


class AttemptBucket(StrEnum):
    """층위 1 의 네 버킷. 상호배타이고 전수적이다 (`classify_attempt` 가 유일한 판정자)."""

    has_fill = "has_fill"
    rejected = "rejected"
    cancelled = "cancelled"
    # ★"미체결" 이 아니라 **"아직 판정할 수 없다"** 는 뜻이다. `pending`/`submitted` 뿐
    #   아니라 **체결 상태인데 수량을 못 읽는 행**도 여기 들어간다. 그 행을 `has_fill` 로
    #   보내면 판독 불가를 성공으로 바꾸는 것이고(BL-544 의 소비처는 정확히 그 행을
    #   `unreadable` 로 거부한다), `cancelled` 로 보내면 실재하는 포지션을 유실로 센다.
    #   어느 쪽도 사실이 아니므로 분자·분모 어디에도 넣지 않는다.
    open = "open"


class EpisodeOutcome(StrEnum):
    won = "won"
    lost = "lost"
    abandoned = "abandoned"
    open = "open"


class RejectionOrigin(StrEnum):
    """거절이 **어디서** 났는가. `rejected` 버킷을 정확히 분할한다 (BL-536 R2).

    ★`state == rejected` 는 "거래소가 거절했다" 를 뜻하지 않는다. `create_order` **이전**
    실패도 같은 상태로 떨어진다 — 자격증명 복호화 실패(`credential_decrypt_failed: ...`)와
    provider 의 비-CCXT 예외(`unexpected non-CCXT error: ...`)가 그것이다. 그 행을
    거래소 거절로 세면 **우리 인프라 장애가 진입 유실로 위장**한다.

    - `exchange` — retCode 가 원문에 있다. 거래소에 도달했고 거래소가 거절했다는 **확증**.
    - `local`    — 거래소에 **도달하지 못했다**(allowlist prefix). 유실률 분자에 넣지 않는다.
    - `unknown`  — 둘 다 아니다. ★**거래소 거절이라고 주장하지 않는다**(라벨은 unknown).
      다만 에피소드 판정에서는 유실 쪽에 남긴다 — 비동기 확정 거절 경로가 retCode 를
      싣지 않아 실제 거절이 여기로 떨어지는 **선재 결함**이 있기 때문이다. 여기서 빼면
      진짜 유실을 조용히 감춘다. 대신 `lost_with_unknown_origin` 으로 항상 표면화한다.
    """

    exchange = "exchange"
    local = "local"
    unknown = "unknown"


# 거래소에 **도달하지 못한** 실패의 원문 prefix. 코드 대조로 확정한 것만 넣는다
# (`tasks/trading.py` 의 `credential_decrypt_failed` · `providers.py` 의 비-CCXT 래핑).
# ★모르는 것을 여기 넣지 마라 — 넣는 순간 진짜 거래소 거절이 분자에서 사라진다.
_LOCAL_FAILURE_PREFIXES: tuple[str, ...] = (
    "credential_decrypt_failed",
    "unexpected non-CCXT error",
)

# ★**저장 형식은 원문 그대로가 아니다** (BL-536 R3-①). `tasks/trading.py` 가 provider 예외를
#   `f"provider_failure: {e}"` 로 **한 겹 감싸서** 저장한다. 그래서 실제 원장 값은
#
#       "provider_failure: unexpected non-CCXT error: RuntimeError"
#
#   이고, 위 prefix 를 `startswith` 로 그냥 대면 **통과하지 못한다**. R2-⑥ 이 두 경로 중
#   `credential_decrypt_failed`(래핑 없음) 하나만 고치고 다른 하나를 놓친 이유가 이것이다.
#   ★내 R2 테스트가 **래핑되지 않은** 형태만 단언해서 그 절반을 못 잡았다 — 원장에 실제로
#   저장되는 형태로 테스트하지 않으면 프로덕션 라인을 실행하지 않는 단언이 된다.
_WRAPPER_PREFIXES: tuple[str, ...] = ("provider_failure: ",)


def _ret_code(error_message: str | None) -> str | None:
    """거래소 원문에서 retCode 숫자만 뽑는 **유일한** 추출기.

    ★2026-08-01 codex 리뷰(LOW) — 같은 private 정규식을 세 곳이 각자 lazy import 하고 있었다.
    로직 중복은 아니었지만 참조가 흩어지면 **네 번째 사람이 다른 정규식을 들고 온다.**
    retCode 를 읽어야 하는 자리는 전부 이 함수를 통한다.
    """
    from src.common.metrics import _BYBIT_RETCODE_PATTERN

    match = _BYBIT_RETCODE_PATTERN.search(error_message or "")
    return match.group(1) if match else None


def _unwrap_error_message(message: str) -> str:
    """저장 시 덧씌운 래핑 접두사를 벗긴다. 중첩 래핑도 끝까지 벗긴다."""
    stripped = True
    while stripped:
        stripped = False
        for prefix in _WRAPPER_PREFIXES:
            if message.startswith(prefix):
                message = message[len(prefix) :]
                stripped = True
    return message


class EpisodeRule(StrEnum):
    """에피소드를 어디서 끊는가. 두 값의 수치를 **항상 함께** 낸다.

    - `fill_closes` (채택) — 체결에서만 끊는다. 근거: 엔진은 같은 `trade_id` 를 덮어쓰며
      재발행하고 체결 시 그 의도를 지운다. 즉 **체결이 곧 의도의 종결**이고, 체결 전의
      취소·거절은 같은 의도의 재시도다. 실측 epoch 표가 이 모양 그대로다
      (cancelled 여러 개 -> filled -> 다시 cancelled 여러 개 -> filled).
      이 규칙의 비율은 "그 의도가 **결국** 포지션이 됐나" 를 답한다.
    - `fill_or_rejection_closes` (반대 해석) — 거래소 거절도 끊는다. 근거: 거절은 그
      시점의 기회를 확정적으로 놓친 것이고, 나중 bar 의 체결은 **다른 가격의 다른 진입**
      이다. 이 규칙의 비율은 "놓친 기회가 얼마나 되나" 를 답한다.

    ★실측 사례가 둘을 가른다 - `PivRevSE` 가 `07:53 rejected(110093)` ->
    `07:56/07:57 cancelled` -> `08:07 filled`. 채택 규칙은 `won` 1 개, 반대 해석은
    `lost` 1 + `won` 1 이다. 어느 쪽도 틀리지 않았고, **한 숫자만 내면 그것이 거짓말**이다.
    """

    fill_closes = "fill_closes_episode"
    fill_or_rejection_closes = "fill_or_rejection_closes_episode"


class Attribution(StrEnum):
    """이 행이 누구 것인가. `Order` 에 세션 FK 가 없어 `idempotency_key` 로만 알 수 있다.

    ★셋을 하나로 뭉치면 안 된다. `nonconditional_ours` 는 **우리 진입이 맞지만 조건부
    파이프라인이 아니다**(TV 웹훅 신호의 시장가 진입). 그걸 `unattributable` 과 같은
    버킷에 넣으면 "외부 주문이 늘었다" 로 읽힌다.
    """

    conditional_ours = "conditional_ours"
    nonconditional_ours = "nonconditional_ours"
    unattributable = "unattributable"


@dataclass(frozen=True, slots=True)
class AttemptFact:
    """원장 행 하나의 순수 사실. 리포지토리·ORM 타입을 이 모듈에 들이지 않는다.

    선례: `exit_attribution.OrderFact`.
    """

    order_id: UUID
    session_id: UUID
    idempotency_key: str | None
    state: OrderState
    quantity: Decimal
    filled_quantity: Decimal | None
    created_at: datetime
    terminal_at: datetime | None
    error_message: str | None
    # ★층위 3(채널)이 이 필드를 요구한다 (BL-522 C3). 조회(`list_entry_attempts`)가 이미
    #   `reduce_only = false` 를 걸어서 실제 생산자는 항상 `False` 를 준다 — 그래도 술어를
    #   **여기 적어두는** 이유는 이번 회차의 결함이 정확히 그 지점이었기 때문이다:
    #   손으로 센 표가 **청산측** 부분체결 7 건을 진입 유실 C3 로 계상했다. 술어가 멀리 있는
    #   SQL 에만 있으면 분류기는 그것을 검사할 수 없고, 검사할 수 없으면 대조군도 못 만든다.
    reduce_only: bool = False


@dataclass(frozen=True, slots=True)
class ClassifiedAttempt:
    """한 행의 판정 결과. 층위 1 과 층위 2 가 같은 판정을 공유하게 만드는 자리."""

    fact: AttemptFact
    bucket: AttemptBucket
    attribution: Attribution
    kind: LiveEntryKind | None
    trade_id: str | None
    bar_epoch: int | None
    # 조건부 key 가 싣고 있는 발주 시점의 트리거 가격 (`Order` 에는 컬럼이 없다).
    # ★C4 가 이 값을 쓴다. 읽히지 않으면 `None` 이고, 그러면 C4 는 **판정하지 않는다**.
    trigger_price: Decimal | None
    # 창 밖에서 종결됐거나 아직 종결되지 않았다 = 이 창의 표로는 재현 불가능한 행.
    verdict_deferred: bool
    # `bucket is rejected` 일 때만 의미가 있다. 그 외에는 `None`.
    rejection_origin: RejectionOrigin | None

    @property
    def is_exchange_rejection(self) -> bool:
        """거래소가 **확정 거절**했다는 증거가 있는 행."""
        return self.rejection_origin is RejectionOrigin.exchange

    @property
    def is_local_failure(self) -> bool:
        """거래소에 도달조차 못 한 행. 유실률 분자에 넣으면 인프라 장애가 유실로 위장한다."""
        return self.rejection_origin is RejectionOrigin.local


def attempt_has_fill(fact: AttemptFact) -> bool:
    """이 행이 **실제로 포지션을 만들었나**.

    ★`state == 'filled'` 로 판정하면 안 된다. `transition_to_cancelled`/`_rejected` 는
    `filled_quantity` 가 0 이 아니면 체결분을 **보존한 채** 종결한다
    (`order_repository._STATES_THAT_CAN_CARRY_FILLS`). 즉 거래소에는 포지션이 남았는데
    상태는 `cancelled` 인 행이 실재하고, 상태로 판정하면 그걸 유실로 오분류한다.

    ★반대로 `state == 'filled'` 를 OR 로 얹어서도 안 된다. `filled_quantity` 가 NULL 인
    `filled` 행은 "판독 불가" 이지 성공이 아니다 - BL-544 의 소비처가 정확히 그 행을
    `unreadable` 로 거부한다. 여기서 성공으로 세면 판독 불가가 조용히 `won` 이 된다.
    그 행은 `AttemptBucket.open` 으로 간다.
    """
    quantity = fact.filled_quantity
    return quantity is not None and quantity > 0


def classify_attempt(fact: AttemptFact) -> AttemptBucket:
    """행 하나를 네 버킷 중 정확히 하나로 보낸다. 순서가 의미를 정한다."""
    if attempt_has_fill(fact):
        return AttemptBucket.has_fill
    if fact.state == OrderState.rejected:
        return AttemptBucket.rejected
    if fact.state == OrderState.cancelled:
        return AttemptBucket.cancelled
    # pending / submitted 그리고 **수량을 못 읽는 filled**. 위 docstring 참조.
    return AttemptBucket.open


def classify_rejection_origin(error_message: str | None) -> RejectionOrigin:
    """거절 원문에서 **거래소에 도달했는가**를 판정한다 (BL-536 R2).

    ★순서가 의미를 정한다. retCode 가 있으면 그건 거래소가 준 응답이므로 prefix 를 보기
    전에 `exchange` 다 — `provider_failure: {"retCode":110093,...}` 처럼 우리 wrapper
    문구가 앞에 붙어 있어도 마찬가지다.

    ★allowlist 에 없고 retCode 도 없으면 `unknown` 이다. **거래소 거절이라고 주장하지
    않는다.** 비동기 확정 거절 경로가 retCode 를 싣지 않는 선재 결함이 있어 진짜 거절도
    여기로 떨어지므로, 에피소드 판정에서는 유실 쪽에 남기고 그 사실을 별도로 표면화한다.
    """
    message = error_message or ""
    if _ret_code(message) is not None:
        return RejectionOrigin.exchange
    # ★래핑 접두사를 벗기고 판정한다 (R3-①). `startswith` 를 원문에 그냥 대면
    #   `provider_failure: unexpected non-CCXT error: ...` 가 통과하지 못해 `unknown` ->
    #   `lost` 로 계상되고, 우리 장애가 다시 진입 유실로 위장한다.
    if _unwrap_error_message(message).startswith(_LOCAL_FAILURE_PREFIXES):
        return RejectionOrigin.local
    return RejectionOrigin.unknown


def _lenient_price(raw: str | None) -> Decimal | None:
    """key 에 실린 가격 문자열을 관용적으로 읽는다. 못 읽으면 `None` — **추정하지 않는다**."""
    if raw is None:
        return None
    try:
        price = Decimal(raw)
    except (ArithmeticError, ValueError):
        return None
    return price if price.is_finite() else None


@dataclass(frozen=True, slots=True)
class _Attribution:
    """`_attribute` 의 반환. 위치 튜플이 다섯 칸이 되면 호출부가 조용히 어긋난다."""

    attribution: Attribution
    kind: LiveEntryKind | None
    trade_id: str | None
    bar_epoch: int | None
    trigger_price: Decimal | None


def _attribute(fact: AttemptFact) -> _Attribution:
    parsed = parse_live_entry_key(fact.idempotency_key)
    if parsed is None or parsed.session_id != fact.session_id:
        return _Attribution(Attribution.unattributable, None, None, None, None)
    bucket = (
        Attribution.conditional_ours
        if parsed.kind in ("cond", "condmkt")
        else Attribution.nonconditional_ours
    )
    return _Attribution(
        attribution=bucket,
        kind=parsed.kind,
        trade_id=parsed.trade_id,
        bar_epoch=parsed.bar_epoch,
        trigger_price=_lenient_price(parsed.trigger),
    )


def classify_attempts(
    facts: Iterable[AttemptFact], *, since: datetime, until: datetime | None
) -> list[ClassifiedAttempt]:
    """행들을 판정한다. 창(`since`, `until`)은 **판정 유예** 표기에만 쓴다 - 선별은 조회가 했다."""
    classified: list[ClassifiedAttempt] = []
    for fact in facts:
        bucket = classify_attempt(fact)
        attributed = _attribute(fact)
        terminal = fact.terminal_at
        deferred = bucket is AttemptBucket.open or terminal is None or terminal < since
        if not deferred and until is not None and terminal is not None:
            deferred = terminal >= until
        origin = (
            classify_rejection_origin(fact.error_message)
            if bucket is AttemptBucket.rejected
            else None
        )
        classified.append(
            ClassifiedAttempt(
                fact=fact,
                bucket=bucket,
                attribution=attributed.attribution,
                kind=attributed.kind,
                trade_id=attributed.trade_id,
                rejection_origin=origin,
                bar_epoch=attributed.bar_epoch,
                trigger_price=attributed.trigger_price,
                verdict_deferred=deferred,
            )
        )
    return classified


@dataclass(frozen=True, slots=True)
class AttemptLayer:
    """층위 1 — 주문 행 하나 = 발주 시도 하나.

    ★`total == has_fill + rejected + cancelled + open` 이 이 타입의 불변식이다
    (`assert_partitions` 로 잠근다). 겹치는 진단값(`unreadable_terminal` 등)은 버킷이
    아니라 **버킷 위에 얹은 별도 관측**이므로 이 합에 들어가지 않는다.
    """

    label: str
    total: int
    has_fill: int
    rejected: int
    cancelled: int
    open: int
    # --- 겹치는 진단 (버킷 아님) ---
    unreadable_terminal: int
    verdict_deferred: int
    rejected_ret_codes: tuple[tuple[str, int], ...]
    # --- `rejected` 버킷의 분할 (셋의 합 == rejected) ---
    rejected_exchange: int
    rejected_local: int
    rejected_unknown: int

    @property
    def exchange_verdicted(self) -> int:
        """**체결 또는 거래소 확정 거절**로 종결된 시도. 확정 거절률의 분모다.

        ★예전 이름은 `reached_exchange` 였고 docstring 이 "거래소가 실제로 답을 준 시도"
        라고 적었다. **그것은 사실이 아니다** (R2). Bybit 는 조건부·시장가 주문을 모두
        `submitted` 로 수락하고, `cancelled` 행은 **거래소가 이미 받아 보유하던** 주문이다
        (취소 성공 또는 probe 확인 뒤에만 그 상태가 된다). 즉 `submitted`/`cancelled` 도
        거래소에 도달했다 — 다만 **판정(체결/거절)이 아닐** 뿐이다.

        그래서 이 분모는 "도달" 이 아니라 "**판정으로 종결**" 을 뜻하고, 이름과 출력
        라벨이 그것을 정확히 말한다. 이 레포 교훈 그대로다 — 분모가 무엇인지 라벨에 적어라.
        """
        return self.has_fill + self.rejected_exchange

    @property
    def confirmed_rejection_rate(self) -> Decimal | None:
        """체결 또는 거래소 확정 거절로 끝난 시도 중 **확정 거절**의 비율.

        ★분자에서 `local`(거래소 미도달)과 `unknown`(retCode 없음)을 뺀다. 우리 인프라
        장애를 거래소 거절로 세면 유실률이 부풀고, 근거 없이 거래소를 탓하게 된다.
        분모가 0 이면 **비율이 없다**(0 이 아니다).
        """
        if self.exchange_verdicted == 0:
            return None
        return Decimal(self.rejected_exchange) / Decimal(self.exchange_verdicted)


@dataclass(frozen=True, slots=True)
class AttributionSplit:
    """행이 누구 것인지의 분해. 조건부 유실률의 분모에서 무엇을 뺐는지를 보이게 한다."""

    conditional_ours: int
    nonconditional_ours: int
    unattributable: int

    @property
    def total(self) -> int:
        return self.conditional_ours + self.nonconditional_ours + self.unattributable


@dataclass(frozen=True, slots=True)
class Episode:
    session_id: UUID
    trade_id: str
    outcome: EpisodeOutcome
    order_ids: tuple[UUID, ...]
    kinds: tuple[LiveEntryKind, ...]
    first_bar_epoch: int | None
    last_bar_epoch: int | None
    verdict_deferred: bool
    # ★구간에 거절이 있었다 (`local` 제외 = 유실로 셀 만한 것). `open` 으로 판정된
    #   에피소드에서도 이 사실은 남는다 - 그러지 않으면 유실이 `open` 뒤로 사라진다.
    had_rejection: bool
    # 그중 거래소 확정(retCode 있음)인 것이 있었나. `lost` 의 근거 강도를 구분한다.
    had_exchange_rejection: bool
    # 거래소에 도달조차 못 한 실패가 있었나 (우리 장애 - 유실이 아니다).
    had_local_failure: bool


@dataclass(frozen=True, slots=True)
class EpisodeLayer:
    """층위 2 — 진입 에피소드. 규칙마다 하나씩 만든다."""

    rule: EpisodeRule
    label: str
    total: int
    won: int
    lost: int
    abandoned: int
    open: int
    settled_won: int
    settled_lost: int
    settled_abandoned: int
    # --- 겹치는 진단 (버킷 아님) ---
    # ★`open` 인데 구간에 거절이 있었던 에피소드 수. 이 값이 0 이 아니면
    #   **유실이 `open` 뒤에 숨어 있다**. 활성 세션에서는 조회 시각에 resting `submitted`
    #   가 거의 항상 있고 `fill_closes` 는 마지막 체결 이후 전부를 한 구간으로 묶으므로,
    #   거절이 통째로 `open` 에 삼켜져 **유실률이 구조적으로 0** 이 될 수 있다.
    #   ★여기 세는 거절은 `_counts_as_loss` 기준이라 **확정(retCode 있음) + 코드 미상**을
    #     함께 포함한다(로컬 실패만 제외). "확정 거절" 이라고 부르면 안 된다 (R3-④) —
    #     코드가 스스로 retCode 없는 것을 `unknown` 으로 정의했기 때문이다.
    open_with_prior_rejection: int
    lost_with_unknown_origin: int
    episodes: tuple[Episode, ...]

    @property
    def resolved(self) -> int:
        return self.won + self.lost + self.abandoned

    @property
    def provisional(self) -> bool:
        """이 층위의 비율을 확정값으로 인용하면 안 되는가.

        ★`open` 에피소드가 하나라도 있으면 참이다. 그 구간들은 아직 판정되지 않았고,
        그 안에 확정 거절이 섞여 있을 수 있다(`open_with_prior_rejection`).
        출력은 이 표시를 **숫자 옆에** 달아야 한다 — 없으면 다음 사람이 확정값으로 인용한다.
        """
        return self.open > 0

    @property
    def loss_rate(self) -> Decimal | None:
        """`lost / (won + lost + abandoned)`. 분모가 0 이면 비율이 없다.

        ★`provisional` 이 참이면 이 값은 **하한**이다 — `open` 구간이 나중에 `lost` 로
        확정될 수 있기 때문이다.
        """
        if self.resolved == 0:
            return None
        return Decimal(self.lost) / Decimal(self.resolved)

    @property
    def settled_resolved(self) -> int:
        return self.settled_won + self.settled_lost + self.settled_abandoned

    @property
    def settled_loss_rate(self) -> Decimal | None:
        """창 안에서 **완전히 종결된** 에피소드만의 유실률.

        ★`loss_rate` 와 왜 둘인가 - `loss_rate` 는 `queried_at` 이 뒤로 갈수록 값이 변한다
        (창 끝에 `submitted` 였던 행이 나중에 체결되면 같은 창의 비율이 달라진다).
        재현 가능한 숫자가 필요하면 이쪽을 봐라. 대신 표본이 작다.
        """
        if self.settled_resolved == 0:
            return None
        return Decimal(self.settled_lost) / Decimal(self.settled_resolved)


@dataclass(frozen=True, slots=True)
class EntryCompletenessReport:
    """한 창의 분해 결과 전체.

    ★층위 1 과 층위 2 를 묶는 합계 프로퍼티가 **없다**. 분모가 다른 두 수를 더하지 못하게
    타입으로 막은 것이다.
    """

    session_id: UUID
    since: datetime
    until: datetime | None
    # ★`state` 는 **조회 시각의 값**이다. 이 표는 그 시각의 스냅샷이지 창의 불변 사실이
    #   아니다. 이 값을 안 적으면 그 표는 재현 불가능하다.
    queried_at: datetime
    truncated: bool
    attribution: AttributionSplit
    scope_attempts: AttemptLayer
    conditional_attempts: AttemptLayer
    primary: EpisodeLayer
    alternative: EpisodeLayer
    # 층위 3 (BL-522 채널). ★층위 1·2 와 합산 불가 — `ChannelTable` 주석 참조.
    channels: ChannelTable


def _ret_code_counts(attempts: Sequence[ClassifiedAttempt]) -> tuple[tuple[str, int], ...]:
    """거절 행의 retCode 분포. 원문에서 숫자만 읽는다 - retMsg 는 분류 근거로 쓰지 않는다."""
    counts: _Counter[str] = _Counter()
    for attempt in attempts:
        if attempt.bucket is not AttemptBucket.rejected:
            continue
        counts[_ret_code(attempt.fact.error_message) or "unparsed"] += 1
    return tuple(sorted(counts.items()))


def assert_partitions(layer: AttemptLayer | EpisodeLayer) -> None:
    """분할 불변식을 **실제로 집행한다** (BL-536 R2-⑨).

    ★예전 주석이 "`assert_partitions` 로 잠근다" 고 적었는데 그런 함수가 없었다. 문서화된
    불변식이 코드에 없으면 파티션은 **우연히 성립할 뿐**이고, 그 주석은 다음 사람에게
    거짓말을 한다. 이 레포 교훈 그대로다 — 수용 기준은 자기 집행되지 않는다.

    ★`assert` 문이 아니라 `ValueError` 다. `python -O` 는 assert 를 통째로 지운다 —
    그러면 프로덕션에서만 가드가 사라진다.
    """
    if isinstance(layer, AttemptLayer):
        bucket_sum = layer.has_fill + layer.rejected + layer.cancelled + layer.open
        if bucket_sum != layer.total:
            raise ValueError(
                f"층위 1 분할 위반 [{layer.label}]: "
                f"has_fill {layer.has_fill} + rejected {layer.rejected} + "
                f"cancelled {layer.cancelled} + open {layer.open} = {bucket_sum} != {layer.total}"
            )
        origin_sum = layer.rejected_exchange + layer.rejected_local + layer.rejected_unknown
        if origin_sum != layer.rejected:
            raise ValueError(
                f"거절 출처 분할 위반 [{layer.label}]: "
                f"exchange {layer.rejected_exchange} + local {layer.rejected_local} + "
                f"unknown {layer.rejected_unknown} = {origin_sum} != rejected {layer.rejected}"
            )
        return

    outcome_sum = layer.won + layer.lost + layer.abandoned + layer.open
    if outcome_sum != layer.total:
        raise ValueError(
            f"층위 2 분할 위반 [{layer.label}]: "
            f"won {layer.won} + lost {layer.lost} + abandoned {layer.abandoned} + "
            f"open {layer.open} = {outcome_sum} != {layer.total}"
        )
    if layer.settled_resolved > layer.resolved:
        raise ValueError(
            f"창 안 종결분이 전체보다 크다 [{layer.label}]: "
            f"{layer.settled_resolved} > {layer.resolved}"
        )


def build_attempt_layer(attempts: Sequence[ClassifiedAttempt], *, label: str) -> AttemptLayer:
    buckets: _Counter[AttemptBucket] = _Counter(attempt.bucket for attempt in attempts)
    unreadable = sum(
        1
        for attempt in attempts
        if attempt.bucket is AttemptBucket.open and attempt.fact.state == OrderState.filled
    )
    origins: _Counter[RejectionOrigin] = _Counter(
        attempt.rejection_origin
        for attempt in attempts
        if attempt.bucket is AttemptBucket.rejected and attempt.rejection_origin is not None
    )
    layer = AttemptLayer(
        label=label,
        total=len(attempts),
        has_fill=buckets[AttemptBucket.has_fill],
        rejected=buckets[AttemptBucket.rejected],
        cancelled=buckets[AttemptBucket.cancelled],
        open=buckets[AttemptBucket.open],
        unreadable_terminal=unreadable,
        verdict_deferred=sum(1 for attempt in attempts if attempt.verdict_deferred),
        rejected_ret_codes=_ret_code_counts(attempts),
        rejected_exchange=origins[RejectionOrigin.exchange],
        rejected_local=origins[RejectionOrigin.local],
        rejected_unknown=origins[RejectionOrigin.unknown],
    )
    assert_partitions(layer)
    return layer


def _sort_key(attempt: ClassifiedAttempt) -> tuple[int, int, datetime, str]:
    """`bar_epoch` 오름차순. 판독 불가 epoch 는 **뒤로** 밀고 생성 시각으로 세운다.

    epoch 가 없다고 행을 버리면 그 에피소드의 분모가 줄어든다. 같은 bar 에 `cond` 와
    `condmkt` 가 함께 있을 수 있어 `created_at` -> `order_id` 로 결정론을 끝까지 준다.
    """
    epoch = attempt.bar_epoch
    return (0 if epoch is not None else 1, epoch or 0, attempt.fact.created_at, str(attempt.fact.order_id))


def _counts_as_loss(attempt: ClassifiedAttempt) -> bool:
    """이 거절이 **유실**인가.

    ★거래소에 도달하지 못한 실패(`local`)는 유실이 아니라 **우리 장애**다. 유실률 분자에
    넣으면 인프라 문제가 진입 유실로 위장한다(R2-⑥).
    ★`unknown` 은 유실 쪽에 남긴다 — 비동기 확정 거절이 retCode 를 싣지 않는 선재 결함이
    있어 진짜 거절이 여기로 떨어진다. 빼면 진짜 유실을 감춘다. 대신 `lost_with_unknown_origin`
    으로 항상 표면화한다.
    """
    return attempt.bucket is AttemptBucket.rejected and not attempt.is_local_failure


def _episode_outcome(run: Sequence[ClassifiedAttempt]) -> EpisodeOutcome:
    if any(attempt.bucket is AttemptBucket.has_fill for attempt in run):
        return EpisodeOutcome.won
    if any(attempt.bucket is AttemptBucket.open for attempt in run):
        # 아직 살아 있는 시도가 섞여 있으면 유실을 단정하지 않는다 (fail-closed).
        # ★그 구간에 확정 거절이 있었다면 `Episode.had_rejection` 이 그것을 보존한다 -
        #   그러지 않으면 활성 세션에서 유실이 통째로 `open` 에 삼켜진다 (R2-③).
        return EpisodeOutcome.open
    if any(_counts_as_loss(attempt) for attempt in run):
        return EpisodeOutcome.lost
    return EpisodeOutcome.abandoned


def _closes_episode(attempt: ClassifiedAttempt, rule: EpisodeRule) -> bool:
    """이 행이 구간을 끊는가.

    ★대안 규칙에서 **로컬 실패는 끊지 않는다** (R3-②). 끊게 두면 같은 trade 에
    `credential_decrypt_failed` 뒤 실제 `110093` 거절이 오는 흔한 순서가
    `abandoned` + `lost` **두 에피소드**가 되어, 거절은 1건인데 분모가 2가 된다.
    우리 장애가 유실률의 **분모를 부풀려** 비율을 낮춘다 — R2-⑥ 이 분자에서 막은 것을
    분모에서 되돌리는 셈이다. 끊는 기준을 `_counts_as_loss` 와 같은 술어로 통일한다.
    """
    if attempt.bucket is AttemptBucket.has_fill:
        return True
    return rule is EpisodeRule.fill_or_rejection_closes and _counts_as_loss(attempt)


def build_episode_layer(
    attempts: Sequence[ClassifiedAttempt], *, rule: EpisodeRule, label: str
) -> EpisodeLayer:
    """조건부 진입 행을 `(session_id, trade_id)` 로 묶고 규칙대로 끊어 에피소드를 만든다.

    ★입력은 **조건부 우리 것만** 이어야 한다. 남의 행이나 시장가 진입이 섞이면 `trade_id`
    가 같아도 다른 파이프라인의 의도라 구간이 오염된다.
    """
    grouped: dict[tuple[UUID, str], list[ClassifiedAttempt]] = {}
    for attempt in attempts:
        if attempt.trade_id is None:
            continue
        grouped.setdefault((attempt.fact.session_id, attempt.trade_id), []).append(attempt)

    episodes: list[Episode] = []
    for (session_id, trade_id), rows in sorted(grouped.items(), key=lambda item: item[0][1]):
        run: list[ClassifiedAttempt] = []
        for attempt in sorted(rows, key=_sort_key):
            run.append(attempt)
            if _closes_episode(attempt, rule):
                episodes.append(_make_episode(session_id, trade_id, run))
                run = []
        if run:
            episodes.append(_make_episode(session_id, trade_id, run))

    outcomes: _Counter[EpisodeOutcome] = _Counter(episode.outcome for episode in episodes)
    settled: _Counter[EpisodeOutcome] = _Counter(
        episode.outcome for episode in episodes if not episode.verdict_deferred
    )
    layer = EpisodeLayer(
        rule=rule,
        label=label,
        total=len(episodes),
        won=outcomes[EpisodeOutcome.won],
        lost=outcomes[EpisodeOutcome.lost],
        abandoned=outcomes[EpisodeOutcome.abandoned],
        open=outcomes[EpisodeOutcome.open],
        settled_won=settled[EpisodeOutcome.won],
        settled_lost=settled[EpisodeOutcome.lost],
        settled_abandoned=settled[EpisodeOutcome.abandoned],
        open_with_prior_rejection=sum(
            1
            for episode in episodes
            if episode.outcome is EpisodeOutcome.open and episode.had_rejection
        ),
        lost_with_unknown_origin=sum(
            1
            for episode in episodes
            if episode.outcome is EpisodeOutcome.lost and not episode.had_exchange_rejection
        ),
        episodes=tuple(episodes),
    )
    assert_partitions(layer)
    return layer


def _make_episode(
    session_id: UUID, trade_id: str, run: Sequence[ClassifiedAttempt]
) -> Episode:
    epochs = [attempt.bar_epoch for attempt in run if attempt.bar_epoch is not None]
    return Episode(
        session_id=session_id,
        trade_id=trade_id,
        outcome=_episode_outcome(run),
        order_ids=tuple(attempt.fact.order_id for attempt in run),
        kinds=tuple(attempt.kind for attempt in run if attempt.kind is not None),
        first_bar_epoch=min(epochs) if epochs else None,
        last_bar_epoch=max(epochs) if epochs else None,
        verdict_deferred=any(attempt.verdict_deferred for attempt in run),
        had_rejection=any(_counts_as_loss(attempt) for attempt in run),
        had_exchange_rejection=any(attempt.is_exchange_rejection for attempt in run),
        had_local_failure=any(attempt.is_local_failure for attempt in run),
    )


# --- 층위 3: 유실 채널 (BL-522) ------------------------------------------------
#
# ★이 층위는 층위 1·2 와 **합산 불가**다. 같은 주문이 여러 채널에 동시에 걸릴 수 있고
#   (아래 `ChannelTable.mutually_exclusive` 참조), 채널 하나는 "왜 유실됐나" 를 묻지
#   "몇 건이 유실됐나" 를 묻지 않는다. 그래서 `ChannelTable` 에는 **총합 프로퍼티가 없다.**
#
# ★이 층위가 존재하는 이유 자체가 이번 회차의 결함이다 — 채널 표를 지금까지 **사람이 손으로
#   세서** dev-log 에 적었고, 그렇게 적힌 다섯 줄 중 둘이 조용히 틀렸다:
#     - C2 `deferred_market_inflight` 는 유실 채널이 아니라 **청산 tick 수**였다 (PR #511).
#     - C3 "부분체결 7 건" 은 **청산측** 부분체결이었다. 진입측은 0 건이다.
#   두 오류의 공통 원인은 술어가 코드에 없었다는 것 하나다. 그래서 표를 코드가 만든다.


class LedgerChannel(StrEnum):
    """원장 행으로 **판정 가능한** 채널만 여기 있다.

    ★C5(사전 게이트 거부)와 C2(반증됨)는 이 enum 에 **없다**. 원장에 발자국이 없는 채널을
    같은 타입에 넣으면 `sum(tally.matched for ...)` 한 줄로 한 분모에 섞인다.
    그 둘은 숫자 필드가 아예 없는 `NonLedgerChannel` 로 간다 — 구조적으로 못 더한다.
    """

    c1_residual_rejection = "C1"
    c3_partial_fill = "C3"
    c4_cancel_beats_trigger = "C4"


class ChannelVerdict(StrEnum):
    """한 후보 행에 대한 채널 판정. 셋은 상호배타·전수적이다 (후보 집합 위에서).

    ★`unmeasured` 가 `not_matched` 와 **다른 값**인 것이 이 층위의 전부다. 모르는 것을
    아는 것처럼 분류하면 그 채널은 항상 작아 보인다 (BL-562/BL-574). 선례는
    `order_repository.list_fills_since` 가 절단을 fail-closed 로 떨어뜨리는 관용구다.
    """

    matched = "matched"
    not_matched = "not_matched"
    unmeasured = "unmeasured"


class NonLedgerStatus(StrEnum):
    counter_only = "counter_only"
    disproven = "disproven"


@dataclass(frozen=True, slots=True)
class NonLedgerChannel:
    """원장으로 판정할 수 없는 채널. ★**숫자 필드가 하나도 없다.**

    그것이 요구사항 1 의 집행 방식이다 — 이 타입에는 더할 수 있는 값이 존재하지 않으므로
    원장 기반 채널과 한 분모에 넣는 산식을 **쓸 수가 없다**. 주석으로 금지하지 않는다.
    """

    key: str
    title: str
    status: NonLedgerStatus
    why: str
    # 그럼 어디를 봐야 하나. 없는 숫자를 지어내는 대신 **볼 자리**를 준다.
    where: str


NON_LEDGER_CHANNELS: tuple[NonLedgerChannel, ...] = (
    NonLedgerChannel(
        key="C5",
        title="사전 게이트 거부 (notional / balance)",
        status=NonLedgerStatus.counter_only,
        why=(
            "게이트가 `create_order` **이전**에 막는다 — `Order` 행이 만들어지지 않는다. "
            "원장에 발자국이 없으므로 이 채널의 크기는 원장 분해로 판정 불가다."
        ),
        where=(
            "qb_order_rejected_total{reason=min_notional|notional|balance_unverified} — 게이트 발화 지점. "
            "조건부 경로는 qb_live_conditional_reconcile_errors_total"
            "{stage=conditional_place_gate|market_place_gate} 로도 잡힌다. "
            "events 경로는 trading.live_signal_events(status=failed) 원장. "
            "★qb_live_signal_dispatch_total 은 outcome='rejected' 하나로 뭉쳐 있어 "
            "notional 인지 kill-switch 인지 구분되지 않는다 — 크기 근거로 쓰지 마라. "
            "(counter 는 두 스냅샷의 **차분**으로만. `CounterBasis` 참조)"
        ),
    ),
    NonLedgerChannel(
        key="C2",
        title="deferred_market_inflight",
        status=NonLedgerStatus.disproven,
        why=(
            "★**유실 채널이 아니다** — 그 counter 는 진입 유실 건수가 아니라 시장가 주문이 "
            "in-flight 인 **tick 의 평가 발화 횟수**이고, 실측 9 건은 전량 **청산** tick "
            "이었다 (PR #511, 2026-07-30 확정). 표에서 지우지 않고 반증됨으로 남긴다 — "
            "지우면 다음 사람이 또 넣는다."
        ),
        where="qb_live_conditional_reconcile_errors_total{stage=deferred_market_inflight}",
    ),
)


# C1 의 retCode 집합. 조회~발주 사이에 가격이 다시 움직여 생긴 거절만 여기 들어간다
# (`metrics._EXCHANGE_ORDER_RESPONSE_REASONS` 가 둘 다 `trigger_breached` 로 뭉갠다).
# ★잔고 부족(110004 등)이나 포지션 0(110034)을 여기 넣지 마라 — 다른 채널이다.
RESIDUAL_REJECTION_RET_CODES: frozenset[str] = frozenset({"110092", "110093"})

# 체결분을 보존한 채 종결될 수 있는 상태. `order_repository._STATES_THAT_CAN_CARRY_FILLS`
# 와 같은 집합이며, 같은 이유로 존재한다 — `filled` 만 보면 BL-544 형제 케이스를 놓친다.
_FILL_CARRYING_STATES: frozenset[OrderState] = frozenset(
    {OrderState.filled, OrderState.cancelled, OrderState.rejected}
)

# (트리거 가격, 창 시작, 창 끝) -> 그 창 안에서 시장이 그 수준을 건드렸나.
# `None` = **봉이 없어서 모른다**. 호출부는 그것을 `unmeasured` 로 떨어뜨린다.
BreakoutProbe = Callable[[Decimal, datetime, datetime], bool | None]



def _c1_verdict(attempt: ClassifiedAttempt) -> ChannelVerdict | None:
    """C1 — 조회~발주 사이 가격이 다시 움직여 생긴 거절.

    술어: `state=rejected` AND 거절 출처가 `exchange` AND retCode ∈ {110092, 110093}.

    ★`unknown` 출처(retCode 가 원문에 없다)는 `not_matched` 가 아니라 **`unmeasured`** 다.
    이 레포는 이미 "비동기 확정 거절 경로가 retCode 를 싣지 않는다" 는 선재 결함을
    알고 있다(`RejectionOrigin` 주석). 그 행이 110092 였는지 아니었는지 우리는 **모른다**.
    `not_matched` 로 떨어뜨리면 C1 이 구조적으로 작아 보인다.
    """
    if attempt.fact.state != OrderState.rejected:
        return None
    origin = classify_rejection_origin(attempt.fact.error_message)
    if origin is RejectionOrigin.local:
        # 거래소에 도달조차 못 했다 = 가격이 움직여서 거절된 것일 수 없다. 확정적으로 아니다.
        return ChannelVerdict.not_matched
    if origin is RejectionOrigin.unknown:
        return ChannelVerdict.unmeasured
    code = _ret_code(attempt.fact.error_message)
    return (
        ChannelVerdict.matched
        if code in RESIDUAL_REJECTION_RET_CODES
        else ChannelVerdict.not_matched
    )


def _c3_verdict(attempt: ClassifiedAttempt) -> ChannelVerdict | None:
    """C3 — 전환 주문의 부분체결.

    술어: `reduce_only=false` AND `state ∈ {filled, cancelled, rejected}` AND
    `0 < filled_quantity < quantity`.

    ★`reduce_only=true` 는 후보조차 아니다. **이번 회차의 핵심 결함이 정확히 이것이다** —
    손으로 센 표의 "부분체결 7 건" 은 전부 청산측이었다. 청산 부분체결은 진입 유실이 아니다.

    ★`state == filled` 만 보면 안 된다. `transition_to_cancelled`/`_rejected` 가 체결분을
    보존한 채 종결한다(BL-544 형제 케이스).

    ★`filled_quantity` 가 NULL 일 때의 판정은 **상태에 따라 다르다**. 이 갈림은 내가 정한
    것이 아니라 `order_repository._STATES_THAT_CAN_CARRY_FILLS` 가 이미 정한 해석이다:

    - `filled` 인데 수량이 NULL = **판독 불가**(`unmeasured`). BL-544 소비처가 정확히 그 행을
      `unreadable` 로 보고 fail-closed 한다.
    - `cancelled`/`rejected` 인데 수량이 NULL = **그냥 취소**(`not_matched`). 두 전이는
      체결분이 있을 때만 수량을 쓰므로, NULL 은 "체결이 보고되지 않았다" 는 기록이다.

    ★둘을 하나로 뭉쳐 전부 `unmeasured` 로 두면 실측 창에서 판정불가가 **194** 가 되어
    (진입 280 행 중 취소·거절 NULL 이 그만큼이다) C3 의 분모가 통째로 증발한다.
    보수적으로 보이지만 정본과 어긋나는 해석이고, "재보니 모르겠더라" 는 답도 거짓말이다.
    """
    fact = attempt.fact
    if fact.reduce_only or fact.state not in _FILL_CARRYING_STATES:
        return None
    filled = fact.filled_quantity
    if filled is None:
        return (
            ChannelVerdict.unmeasured
            if fact.state == OrderState.filled
            else ChannelVerdict.not_matched
        )
    if filled <= 0:
        # 체결이 아예 없다 = 부분체결이 아니다 (그냥 취소·거절).
        return ChannelVerdict.not_matched
    return ChannelVerdict.matched if filled < fact.quantity else ChannelVerdict.not_matched


def _c4_verdict(attempt: ClassifiedAttempt, probe: BreakoutProbe | None) -> ChannelVerdict | None:
    """C4 — 취소가 트리거를 이겼다.

    술어(봉 없이 판정 가능한 절반): `kind == cond`(resting) AND `state=cancelled`.
    술어(봉이 필요한 절반): `[created_at, terminal_at)` 안에 시장이 `trigger_price` 를 건드렸나
    — 이것은 **주입된 `BreakoutProbe`** 가 답한다. 봉이 없으면 `None` 이고 `unmeasured` 다.

    ★`condmkt` 는 후보가 아니다. 시장가 전환 주문은 호가창에 남지 않아 "트리거를 기다린다"
    는 개념 자체가 없다(`parse_conditional_entry_key` 가 같은 이유로 condmkt 를 거부한다).

    ★부분체결을 보존한 채 취소된 행은 `bucket` 이 `has_fill` 이지만 `state` 는 `cancelled`
    라 여기 후보로 들어온다. 그 행은 트리거가 실제로 발화한 행이므로 probe 가 `matched` 를
    낼 수 있고, 동시에 C3 에도 걸린다 — **채널은 상호배타가 아니다**(아래 참조).
    """
    fact = attempt.fact
    if attempt.kind != "cond" or fact.state != OrderState.cancelled:
        return None
    trigger = attempt.trigger_price
    if trigger is None or fact.terminal_at is None or probe is None:
        # 트리거 가격을 못 읽거나 취소 시각이 없거나 봉이 없다 = **판정하지 않는다**.
        return ChannelVerdict.unmeasured
    crossed = probe(trigger, fact.created_at, fact.terminal_at)
    if crossed is None:
        return ChannelVerdict.unmeasured
    return ChannelVerdict.matched if crossed else ChannelVerdict.not_matched


def channel_verdict(
    attempt: ClassifiedAttempt,
    channel: LedgerChannel,
    *,
    breakout_probe: BreakoutProbe | None = None,
) -> ChannelVerdict | None:
    """행 하나에 대한 채널 판정. `None` 이면 **그 채널의 후보가 아니다**(무판정).

    ★"후보 아님" 과 "후보인데 아니다(`not_matched`)" 를 같은 값으로 뭉개면 분모가 사라진다.
    """
    if channel is LedgerChannel.c1_residual_rejection:
        return _c1_verdict(attempt)
    if channel is LedgerChannel.c3_partial_fill:
        return _c3_verdict(attempt)
    return _c4_verdict(attempt, breakout_probe)


CHANNEL_PREDICATES: dict[LedgerChannel, str] = {
    LedgerChannel.c1_residual_rejection: (
        "state=rejected AND 거절출처=exchange AND retCode ∈ {110092,110093} "
        "(retCode 없음 = unmeasured)"
    ),
    LedgerChannel.c3_partial_fill: (
        "reduce_only=false AND state ∈ {filled,cancelled,rejected} AND "
        "0 < filled_quantity < quantity "
        "(filled+NULL = unmeasured · cancelled/rejected+NULL = 그냥 취소)"
    ),
    LedgerChannel.c4_cancel_beats_trigger: (
        "kind=cond AND state=cancelled AND [created_at, terminal_at) 안에서 시장이 "
        "trigger_price 를 건드렸나 (probe 미주입/봉 없음 = unmeasured)"
    ),
}

CHANNEL_TITLES: dict[LedgerChannel, str] = {
    LedgerChannel.c1_residual_rejection: "잔여 거절 (조회~발주 사이 가격 재이동)",
    LedgerChannel.c3_partial_fill: "부분체결 (전환 주문)",
    LedgerChannel.c4_cancel_beats_trigger: "취소가 트리거를 이김",
}


@dataclass(frozen=True, slots=True)
class ChannelTally:
    """채널 하나의 집계. 후보 집합 위에서 `matched + not_matched + unmeasured` 가 파티션이다.

    ★`rows` 는 입력 전체이고 `candidates` 는 그중 이 채널이 묻는 질문이 성립하는 행이다.
    둘을 하나로 합치면 "후보 아님" 이 분모에 섞여 채널이 작아 보인다.
    """

    channel: LedgerChannel
    title: str
    predicate: str
    rows: int
    candidates: int
    matched: int
    not_matched: int
    unmeasured: int
    # --- 겹치는 진단 (파티션 아님) ---
    # `matched` 의 **부분집합** — 조건부 파이프라인(cond/condmkt) 행만 센 값.
    # ★이 칸이 있는 이유: 손으로 센 표의 C3 12 건은 전부 시장가 진입(trigger 없음)이었고
    #   조건부 진입 부분체결은 0 건이었다. 한 숫자로만 내면 그 사실이 표에서 사라진다.
    matched_conditional: int
    matched_order_ids: tuple[UUID, ...]

    @property
    def measured(self) -> int:
        """판정이 난 후보 수. `unmeasured` 를 분모에 넣으면 비율이 조용히 낮아진다."""
        return self.matched + self.not_matched

    @property
    def matched_rate(self) -> Decimal | None:
        """판정된 후보 중 이 채널에 해당한 비율. 분모가 0 이면 **비율이 없다**(0 이 아니다)."""
        if self.measured == 0:
            return None
        return Decimal(self.matched) / Decimal(self.measured)

    @property
    def provisional(self) -> bool:
        """`unmeasured` 가 하나라도 있으면 이 채널의 크기는 **하한**이다."""
        return self.unmeasured > 0


@dataclass(frozen=True, slots=True)
class ChannelOverlap:
    order_id: UUID
    channels: tuple[LedgerChannel, ...]


@dataclass(frozen=True, slots=True)
class ChannelTable:
    """층위 3 전체. ★**총합 프로퍼티가 없다** — 채널은 서로 배타가 아니고 C5 는 원장 밖이다.

    요구사항 2 의 답은 "상호배타가 아님을 명시한다" 쪽이다. 근거: 같은 주문이 C3 와 C4 에
    동시에 걸릴 수 있다(부분체결을 남긴 채 취소된 resting 조건부 진입). 그래서 채널 수를
    더하면 그 주문이 두 번 세어진다. 암묵적으로 두지 않기 위해 (a) 이 프로퍼티가 `False` 를
    **명시**하고 (b) `overlaps` 가 실제로 겹친 주문을 이름으로 내놓는다.
    """

    ledger: tuple[ChannelTally, ...]
    non_ledger: tuple[NonLedgerChannel, ...]
    overlaps: tuple[ChannelOverlap, ...]
    breakout_probe_supplied: bool

    @property
    def mutually_exclusive(self) -> bool:
        return False


def assert_channel_partition(tally: ChannelTally) -> None:
    """채널 하나의 3분할을 **실제로 집행한다**.

    ★`assert` 문이 아니라 `ValueError` 다 — `python -O` 는 assert 를 통째로 지운다
    (`assert_partitions` 와 같은 이유, 같은 규율).
    """
    verdict_sum = tally.matched + tally.not_matched + tally.unmeasured
    if verdict_sum != tally.candidates:
        raise ValueError(
            f"채널 분할 위반 [{tally.channel.value}]: matched {tally.matched} + "
            f"not_matched {tally.not_matched} + unmeasured {tally.unmeasured} = {verdict_sum} "
            f"!= candidates {tally.candidates}"
        )
    if tally.candidates > tally.rows:
        raise ValueError(
            f"후보가 입력보다 많다 [{tally.channel.value}]: {tally.candidates} > {tally.rows}"
        )
    if tally.matched_conditional > tally.matched:
        raise ValueError(
            f"조건부 부분집합이 전체보다 크다 [{tally.channel.value}]: "
            f"{tally.matched_conditional} > {tally.matched}"
        )


def build_channel_table(
    attempts: Sequence[ClassifiedAttempt], *, breakout_probe: BreakoutProbe | None = None
) -> ChannelTable:
    """층위 3 을 만든다. 입력은 **진입 시도 전량**(`reduce_only=false` 인 행)이다.

    ★조건부 행만 넣지 마라 — 손으로 센 표의 C3 12 건이 전부 시장가 진입이었으므로,
    조건부로 좁히면 그 12 건이 표에서 사라지고 "부분체결 0 건" 이라는 다른 거짓말이 된다.
    조건부만의 수는 `ChannelTally.matched_conditional` 로 함께 낸다.
    """
    tallies: list[ChannelTally] = []
    per_order: dict[UUID, list[LedgerChannel]] = {}
    for channel in LedgerChannel:
        counts: _Counter[ChannelVerdict] = _Counter()
        matched_ids: list[UUID] = []
        matched_conditional = 0
        for attempt in attempts:
            verdict = channel_verdict(attempt, channel, breakout_probe=breakout_probe)
            if verdict is None:
                continue
            counts[verdict] += 1
            if verdict is ChannelVerdict.matched:
                matched_ids.append(attempt.fact.order_id)
                per_order.setdefault(attempt.fact.order_id, []).append(channel)
                if attempt.attribution is Attribution.conditional_ours:
                    matched_conditional += 1
        tally = ChannelTally(
            channel=channel,
            title=CHANNEL_TITLES[channel],
            predicate=CHANNEL_PREDICATES[channel],
            rows=len(attempts),
            candidates=sum(counts.values()),
            matched=counts[ChannelVerdict.matched],
            not_matched=counts[ChannelVerdict.not_matched],
            unmeasured=counts[ChannelVerdict.unmeasured],
            matched_conditional=matched_conditional,
            matched_order_ids=tuple(matched_ids),
        )
        assert_channel_partition(tally)
        tallies.append(tally)

    overlaps = tuple(
        ChannelOverlap(order_id=order_id, channels=tuple(channels))
        for order_id, channels in sorted(per_order.items(), key=lambda item: str(item[0]))
        if len(channels) > 1
    )
    return ChannelTable(
        ledger=tuple(tallies),
        non_ledger=NON_LEDGER_CHANNELS,
        overlaps=overlaps,
        breakout_probe_supplied=breakout_probe is not None,
    )


@dataclass(frozen=True, slots=True)
class Bar:
    """봉 하나. `start` 는 봉 시작 시각이고 구간은 `[start, start + interval)` 이다."""

    start: datetime
    high: Decimal
    low: Decimal


def bars_breakout_probe(
    bars: Sequence[Bar], *, interval: timedelta | None = None
) -> BreakoutProbe:
    """봉 배열로 C4 포트를 만든다. **덮이지 않은 창은 `None`** 이다.

    계약 (이 함수가 지키는 것):

    1. 창 `[start, end)` 가 봉으로 **빈틈없이 덮이지 않으면 `None`** 이다. 구멍이 있는데
       "안 건드렸다(False)" 를 돌려주면, 봉을 못 구한 것이 채널 크기 0 으로 위장한다.
    2. 덮였고 어느 봉이든 `low <= trigger <= high` 면 `True`. 방향을 묻지 않는 이유 —
       resting stop 은 발주 시점에 아직 발화하지 않은 상태이므로, 그 수준을 **건드리는
       것 자체**가 발화 조건이다(위든 아래든). 그래서 side 없이 판정 가능하다.
    3. `end <= start` 면 `None`. 취소 시각이 생성 시각보다 앞서거나 같은 것은 시계 왜곡이라
       "창 안에서 아무 일도 없었다" 로 읽으면 안 된다.
    4. 봉이 2 개 미만이고 `interval` 도 안 주면 봉 길이를 모르므로 항상 `None`.
    """
    ordered = sorted(bars, key=lambda bar: bar.start)
    step = interval
    if step is None and len(ordered) >= 2:
        step = min(
            (later.start - earlier.start for earlier, later in pairwise(ordered)),
            default=None,
        )
    if step is not None and step <= timedelta(0):
        step = None

    def probe(trigger: Decimal, start: datetime, end: datetime) -> bool | None:
        if step is None or end <= start:
            return None
        cursor = start
        touched = False
        for bar in ordered:
            bar_end = bar.start + step
            if bar_end <= cursor:
                continue
            if bar.start > cursor:
                return None  # 구멍 — 이 창은 봉으로 덮이지 않았다
            if bar.low <= trigger <= bar.high:
                touched = True
            cursor = bar_end
            if cursor >= end:
                return touched
        return None  # 창 끝까지 못 덮었다

    return probe


def build_report(
    facts: Sequence[AttemptFact],
    *,
    session_id: UUID,
    since: datetime,
    until: datetime | None,
    queried_at: datetime,
    truncated: bool,
    breakout_probe: BreakoutProbe | None = None,
) -> EntryCompletenessReport:
    """조회 결과를 세 층위로 분해한다. 이 모듈의 유일한 진입점.

    `breakout_probe` 를 주지 않으면 C4 는 전부 `unmeasured` 다 — 그것이 정확한 상태다.
    """
    classified = classify_attempts(facts, since=since, until=until)
    conditional = [
        attempt for attempt in classified if attempt.attribution is Attribution.conditional_ours
    ]
    attribution_counts: _Counter[Attribution] = _Counter(
        attempt.attribution for attempt in classified
    )
    return EntryCompletenessReport(
        session_id=session_id,
        since=since,
        until=until,
        queried_at=queried_at,
        truncated=truncated,
        attribution=AttributionSplit(
            conditional_ours=attribution_counts[Attribution.conditional_ours],
            nonconditional_ours=attribution_counts[Attribution.nonconditional_ours],
            unattributable=attribution_counts[Attribution.unattributable],
        ),
        scope_attempts=build_attempt_layer(
            classified, label="세션 스코프 진입 주문 전량 (reduce_only=false)"
        ),
        conditional_attempts=build_attempt_layer(
            conditional, label="조건부 진입 (우리 cond/condmkt key 만)"
        ),
        primary=build_episode_layer(
            conditional,
            rule=EpisodeRule.fill_closes,
            label="에피소드 = 체결에서 끊는다 (채택). 의도가 결국 포지션이 됐나",
        ),
        alternative=build_episode_layer(
            conditional,
            rule=EpisodeRule.fill_or_rejection_closes,
            label="에피소드 = 체결 또는 거절에서 끊는다 (반대 해석). 놓친 기회가 얼마나 되나",
        ),
        # ★조건부만 넣지 않는다 — 시장가 진입의 부분체결이 통째로 사라진다.
        channels=build_channel_table(classified, breakout_probe=breakout_probe),
    )
