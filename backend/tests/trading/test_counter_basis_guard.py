# 서로 다른 시점에 도입된 counter 의 절대값 비교를 도구가 거부하는지 고정한다

"""BL-536 R1 — counter 유효 시작점 가드.

## 이 파일이 존재하는 이유 (실측)

앞 회차의 ③-c(a) 답은 **구조적으로는 맞았지만 관측을 설명하지 못했다.**

    placed_total{long+short}  126
    guard{conditional_placed}  92  +  guard{market_converted}  7  =  99
    -> 27 이 남는다

두 counter 는 `live_signal.py` 의 **인접 두 줄**에서 `order_service.execute` 직후에
무조건 함께 오른다(코드 대조 확인). 그런데도 절대값이 어긋난 이유는 **출생일이 다르기
때문**이다:

    qb_live_conditional_placed_total  <- 30031efe (PR #489, 2026-07-27)
    qb_live_conditional_guard_total   <- 274dc645 (PR #493, 2026-07-28)   # 하루 뒤

그 사이 5 커밋 동안 `placed_total` 은 guard 가 **존재하지도 않던 구간**을 홀로 쌓았고,
그 값은 지워지지 않는다 — `metrics_multiproc.configure_multiprocess` 는 mmap 디렉터리를
`makedirs(exist_ok=True)` 할 뿐 비우지 않고, `mark_metrics_process_dead` 는 live gauge
파일만 지운다. **counter 파일은 배포를 넘어 산다.**

## 그래서 무엇을 잠그나

같은 사건을 세는 두 counter 라도 **유효 시작점이 다르면 절대값이 다를 수 있다.**
따라서 도구는 절대값 교차 비교를 **거부**해야 한다 — 경고 문구가 아니라 거부다.
경고는 숫자 옆에 붙어 있어도 사람이 숫자를 먼저 읽는다. 이 레포는 이미
"수용 기준은 자기 집행되지 않는다" 를 배웠다.
"""

from __future__ import annotations

import pytest

from src.trading.entry_completeness import (
    COUNTER_INTRODUCED,
    CounterBasis,
    CounterReading,
    cancel_inequality_check,
    placement_identity_check,
)

# 실측 그대로. 두 counter 가 같은 사건을 세는데 절대값이 27 어긋난다.
MEASURED_PLACED = 126.0
MEASURED_GUARD_CONDITIONAL = 92.0
MEASURED_GUARD_MARKET = 7.0


def _absolute(name: str, value: float) -> CounterReading:
    return CounterReading(name=name, value=value, basis=CounterBasis.absolute)


def _delta(name: str, value: float) -> CounterReading:
    return CounterReading(name=name, value=value, basis=CounterBasis.delta)


def test_measured_absolutes_really_do_disagree() -> None:
    """★대조군 — 이 전제가 깨지면 아래 가드 전체가 의미 없다.

    같은 사건을 세는 두 counter 의 절대값이 실제로 다르다는 사실 자체를 먼저 고정한다.
    """
    assert MEASURED_PLACED != MEASURED_GUARD_CONDITIONAL + MEASURED_GUARD_MARKET
    assert MEASURED_PLACED - (MEASURED_GUARD_CONDITIONAL + MEASURED_GUARD_MARKET) == 27.0


def test_identity_check_refuses_absolute_readings() -> None:
    """★R1-② 가드 본체 — 절대값이면 숫자를 내지 않고 거부한다."""
    check = placement_identity_check(
        placed=_absolute("qb_live_conditional_placed_total", MEASURED_PLACED),
        conditional_placed=_absolute(
            "qb_live_conditional_guard_total", MEASURED_GUARD_CONDITIONAL
        ),
        market_converted=_absolute("qb_live_conditional_guard_total", MEASURED_GUARD_MARKET),
    )
    assert check.comparable is False
    assert check.holds is None, "거부는 '깨짐'(False)이 아니라 '판정 안 함'(None)이다"
    assert "비교 거부" in check.detail
    # 거부 사유가 사람에게 증거를 준다 — 도입 커밋이 문구에 실린다.
    assert "30031efe" in check.detail
    assert "274dc645" in check.detail


def test_identity_check_holds_on_deltas_over_a_window_where_both_exist() -> None:
    """두 counter 가 모두 존재하는 창의 **차분**은 비교 가능하고 실제로 성립한다."""
    check = placement_identity_check(
        placed=_delta("qb_live_conditional_placed_total", 12.0),
        conditional_placed=_delta("qb_live_conditional_guard_total", 9.0),
        market_converted=_delta("qb_live_conditional_guard_total", 3.0),
    )
    assert check.comparable is True
    assert check.holds is True


def test_identity_check_still_detects_a_real_break_on_deltas() -> None:
    """★가드가 검정력을 죽이지 않았는지 — 차분에서 진짜로 깨지면 잡아야 한다."""
    check = placement_identity_check(
        placed=_delta("qb_live_conditional_placed_total", 12.0),
        conditional_placed=_delta("qb_live_conditional_guard_total", 9.0),
        market_converted=_delta("qb_live_conditional_guard_total", 1.0),
    )
    assert check.comparable is True
    assert check.holds is False


@pytest.mark.parametrize(
    ("placed_basis", "conditional_basis", "market_basis"),
    [
        (CounterBasis.absolute, CounterBasis.delta, CounterBasis.delta),
        (CounterBasis.delta, CounterBasis.absolute, CounterBasis.delta),
        (CounterBasis.delta, CounterBasis.delta, CounterBasis.absolute),
    ],
)
def test_one_absolute_reading_poisons_the_whole_comparison(
    placed_basis: CounterBasis, conditional_basis: CounterBasis, market_basis: CounterBasis
) -> None:
    """셋 중 **하나만** 절대값이어도 비교는 성립하지 않는다."""
    check = placement_identity_check(
        placed=CounterReading(
            name="qb_live_conditional_placed_total", value=12.0, basis=placed_basis
        ),
        conditional_placed=CounterReading(
            name="qb_live_conditional_guard_total", value=9.0, basis=conditional_basis
        ),
        market_converted=CounterReading(
            name="qb_live_conditional_guard_total", value=3.0, basis=market_basis
        ),
    )
    assert check.comparable is False
    assert check.holds is None


def test_cancel_inequality_refuses_absolute_counter() -> None:
    """③-b 도 같은 가드를 쓴다.

    원장 쪽은 **창으로 자른 값**인데 counter 만 프로세스 수명 누적이면 부등식이 늘
    성립해 **검정력이 0** 이 된다. 성립하는 부등식이 아니라 무의미한 부등식이 된다.
    """
    check = cancel_inequality_check(
        ledger_cancelled=15,
        replaced=_absolute("qb_live_conditional_cancelled_total", 900.0),
    )
    assert check.comparable is False
    assert check.holds is None
    assert "비교 거부" in check.detail


def test_cancel_inequality_reports_residual_on_deltas() -> None:
    check = cancel_inequality_check(
        ledger_cancelled=15, replaced=_delta("qb_live_conditional_cancelled_total", 9.0)
    )
    assert check.comparable is True
    assert check.holds is True
    assert "미계측 취소(잔차) = 6" in check.detail


def test_cancel_inequality_flags_a_broken_inequality() -> None:
    """부등식이 깨지면 counter 나 조회 창이 틀렸다는 신호다 — 그것도 산출물이다."""
    check = cancel_inequality_check(
        ledger_cancelled=3, replaced=_delta("qb_live_conditional_cancelled_total", 9.0)
    )
    assert check.comparable is True
    assert check.holds is False


def test_comparable_is_exactly_the_delta_basis() -> None:
    assert _delta("x", 1.0).comparable is True
    assert _absolute("x", 1.0).comparable is False


def test_known_counter_birth_dates_are_recorded_as_evidence() -> None:
    """집행은 basis 로 하지만, 거부 사유를 사람에게 설명할 증거는 남아 있어야 한다."""
    assert COUNTER_INTRODUCED["qb_live_conditional_placed_total"].startswith("30031efe")
    assert COUNTER_INTRODUCED["qb_live_conditional_guard_total"].startswith("274dc645")
