# CLI 가 단일 스냅샷을 "차분" 이라고 부르지 않는지 고정한다

"""BL-536 R1 — 결함 그 자체의 회귀 테스트.

앞 회차 CLI 는 `--metrics-after` 만 받으면 `after - 0` 을 계산해 **"차분 N"** 이라고
출력했다. 그것은 차분이 아니라 **절대값**이고, 그 값으로 교차 항등식을 검산했다.
`placed_total` 과 `guard_total` 의 도입 시점이 하루 다르므로 그 검산은 반드시 깨진다
(실측 126 vs 99). 즉 도구가 스스로 함정을 재생산하고 있었다.
"""

from __future__ import annotations

from scripts.entry_completeness_report import _basis_note, _reading, _summed_reading
from src.trading.entry_completeness import (
    CounterBasis,
    CounterReading,
    cancel_inequality_check,
    placement_identity_check,
)

_AFTER = """
qb_live_conditional_placed_total{direction="long"} 70.0
qb_live_conditional_placed_total{direction="short"} 56.0
qb_live_conditional_guard_total{outcome="conditional_placed"} 92.0
qb_live_conditional_guard_total{outcome="market_converted"} 7.0
qb_live_conditional_cancelled_total{reason="replaced"} 25.0
"""

# 창 안에서는 항등식이 성립하도록 맞춘 값이다 —
#   placed  (70-60) + (56-54) = 12
#   guard   (92-82) + (7-5)   = 12
# 절대값은 여전히 126 vs 99 로 어긋난다. 그것이 이 픽스처의 요점이다.
_BEFORE = """
qb_live_conditional_placed_total{direction="long"} 60.0
qb_live_conditional_placed_total{direction="short"} 54.0
qb_live_conditional_guard_total{outcome="conditional_placed"} 82.0
qb_live_conditional_guard_total{outcome="market_converted"} 5.0
qb_live_conditional_cancelled_total{reason="replaced"} 20.0
"""


def _snapshot(text: str):  # type: ignore[no-untyped-def]
    from scripts.entry_completeness_report import parse_metrics_text

    return parse_metrics_text(text)


def test_single_snapshot_is_labelled_absolute_not_delta() -> None:
    """★결함의 직접 회귀 — before 가 없으면 그것은 차분이 아니다."""
    reading = _reading(
        None, _snapshot(_AFTER), "qb_live_conditional_cancelled_total", reason="replaced"
    )
    assert reading is not None
    assert reading.basis is CounterBasis.absolute
    assert reading.comparable is False
    assert reading.value == 25.0


def test_two_snapshots_produce_a_comparable_delta() -> None:
    reading = _reading(
        _snapshot(_BEFORE),
        _snapshot(_AFTER),
        "qb_live_conditional_cancelled_total",
        reason="replaced",
    )
    assert reading is not None
    assert reading.basis is CounterBasis.delta
    assert reading.value == 5.0


def test_summed_reading_carries_the_basis_too() -> None:
    """label 을 합칠 때 basis 가 사라지면 가드에 구멍이 난다."""
    absolute = _summed_reading(None, _snapshot(_AFTER), "qb_live_conditional_placed_total")
    assert absolute is not None
    assert absolute.basis is CounterBasis.absolute
    assert absolute.value == 126.0

    delta = _summed_reading(
        _snapshot(_BEFORE), _snapshot(_AFTER), "qb_live_conditional_placed_total"
    )
    assert delta is not None
    assert delta.basis is CounterBasis.delta
    assert delta.value == 12.0


def test_the_measured_trap_is_now_refused_end_to_end() -> None:
    """★실측 126 vs 99 를 CLI 경로 그대로 재현하고, 도구가 **거부**하는지 본다."""
    after = _snapshot(_AFTER)
    check = placement_identity_check(
        placed=_summed_reading(None, after, "qb_live_conditional_placed_total"),  # type: ignore[arg-type]
        conditional_placed=_reading(
            None, after, "qb_live_conditional_guard_total", outcome="conditional_placed"
        ),  # type: ignore[arg-type]
        market_converted=_reading(
            None, after, "qb_live_conditional_guard_total", outcome="market_converted"
        ),  # type: ignore[arg-type]
    )
    assert check.comparable is False, "예전 도구는 여기서 126 != 99 를 '★깨짐' 으로 출력했다"
    assert check.holds is None


def test_the_same_window_as_deltas_holds() -> None:
    """같은 두 스냅샷을 차분으로 읽으면 항등식이 실제로 성립한다 — 구조는 맞았다."""
    before, after = _snapshot(_BEFORE), _snapshot(_AFTER)
    check = placement_identity_check(
        placed=_summed_reading(before, after, "qb_live_conditional_placed_total"),  # type: ignore[arg-type]
        conditional_placed=_reading(
            before, after, "qb_live_conditional_guard_total", outcome="conditional_placed"
        ),  # type: ignore[arg-type]
        market_converted=_reading(
            before, after, "qb_live_conditional_guard_total", outcome="market_converted"
        ),  # type: ignore[arg-type]
    )
    assert check.comparable is True
    assert check.holds is True, "placed 12 == conditional 10 + market 2"


def test_basis_note_never_calls_an_absolute_a_delta() -> None:
    assert "차분" in _basis_note(CounterBasis.delta)
    note = _basis_note(CounterBasis.absolute)
    assert "절대값" in note
    assert "비교 금지" in note


# --- R2-④ before 스냅샷은 있는데 그 series 만 없는 경우 -----------------------

# ★R1 가드가 **자기가 만들어진 시나리오**에서 뚫렸던 자리다.
#   `guard_total` 이 태어나기 전에 뜬 before 스냅샷에는 그 series 가 없다.
#   없는 key 를 0 으로 읽으면 `after - 0 = 절대값` 이 `delta` 라벨을 달고 통과한다.
_BEFORE_MISSING_GUARD = """
qb_live_conditional_placed_total{direction="long"} 60.0
qb_live_conditional_placed_total{direction="short"} 54.0
qb_live_conditional_cancelled_total{reason="replaced"} 20.0
"""


def test_missing_series_in_before_is_not_a_delta() -> None:
    """★가드가 뚫렸던 정확한 시나리오 — counter 도입 전 스냅샷."""
    reading = _reading(
        _snapshot(_BEFORE_MISSING_GUARD),
        _snapshot(_AFTER),
        "qb_live_conditional_guard_total",
        outcome="conditional_placed",
    )
    assert reading is not None
    assert reading.basis is CounterBasis.unknown
    assert reading.comparable is False, "절대값이 delta 로 위장하면 안 된다"


def test_identity_check_refuses_when_one_side_is_from_before_the_counter_existed() -> None:
    before, after = _snapshot(_BEFORE_MISSING_GUARD), _snapshot(_AFTER)
    check = placement_identity_check(
        placed=_summed_reading(before, after, "qb_live_conditional_placed_total"),  # type: ignore[arg-type]
        conditional_placed=_reading(
            before, after, "qb_live_conditional_guard_total", outcome="conditional_placed"
        ),  # type: ignore[arg-type]
        market_converted=_reading(
            before, after, "qb_live_conditional_guard_total", outcome="market_converted"
        ),  # type: ignore[arg-type]
    )
    assert check.comparable is False
    assert check.holds is None
    assert "series 가 없다" in check.detail


def test_summed_reading_takes_the_weakest_basis() -> None:
    """★합산이 basis 를 씻어내면 구멍이다 — series 하나만 판독 불가여도 합계는 판독 불가다."""
    partial_before = _snapshot(
        'qb_live_conditional_placed_total{direction="long"} 60.0\n'
    )
    reading = _summed_reading(partial_before, _snapshot(_AFTER), "qb_live_conditional_placed_total")
    assert reading is not None
    assert reading.basis is CounterBasis.unknown, "short series 가 before 에 없다"
    assert reading.comparable is False


# --- R2-⑤ 음수 델타 = counter 리셋 ---------------------------------------------


def test_negative_delta_is_flagged_as_a_counter_reset() -> None:
    """★절대값은 거부하면서 음수는 통과시키는 비대칭을 남기지 않는다.

    `ledger >= 음수` 는 무조건 성립한다 — 부등식의 검정력이 0 이 된다.
    """
    before = _snapshot('qb_live_conditional_cancelled_total{reason="replaced"} 900.0\n')
    reading = _reading(
        before, _snapshot(_AFTER), "qb_live_conditional_cancelled_total", reason="replaced"
    )
    assert reading is not None
    assert reading.basis is CounterBasis.counter_reset
    assert reading.comparable is False


def test_cancel_inequality_refuses_a_reset_counter() -> None:
    before = _snapshot('qb_live_conditional_cancelled_total{reason="replaced"} 900.0\n')
    replaced = _reading(
        before, _snapshot(_AFTER), "qb_live_conditional_cancelled_total", reason="replaced"
    )
    assert replaced is not None
    check = cancel_inequality_check(ledger_cancelled=15, replaced=replaced)
    assert check.comparable is False, "음수 차분으로 부등식을 '성립' 이라 말하면 안 된다"
    assert check.holds is None
    assert "음수" in check.detail


# --- R3-③ 거울상 구멍: after 에서 **사라진** series ---------------------------

# ★R2-④ 는 "before 에 없음" 을 막았다. 이건 **대칭인 반대쪽 문**이다 —
#   before 에 있던 series 가 after 에서 사라지면(리셋·부분 mmap 소실) `after.series()` 만
#   순회하는 코드는 **방문조차 하지 않아** 감지하지 못하고, 남은 series 만 합산한 값이
#   조용히 `delta` 로 라벨된다.
_BEFORE_TWO_DIRECTIONS = """
qb_live_conditional_placed_total{direction="long"} 5.0
qb_live_conditional_placed_total{direction="short"} 4.0
"""
_AFTER_ONE_DIRECTION = """
qb_live_conditional_placed_total{direction="long"} 5.0
"""


def test_series_disappearing_in_after_is_not_a_delta() -> None:
    """★before={long:5, short:4} · after={long:5} → `delta` 가 아니다."""
    reading = _summed_reading(
        _snapshot(_BEFORE_TWO_DIRECTIONS),
        _snapshot(_AFTER_ONE_DIRECTION),
        "qb_live_conditional_placed_total",
    )
    assert reading is not None
    assert reading.basis is not CounterBasis.delta
    assert reading.basis is CounterBasis.counter_reset, "사라짐은 리셋 신호다"
    assert reading.comparable is False


def test_disappeared_series_is_actually_visited() -> None:
    """★계측기 자기검증 — 합계가 남은 series 만 더한 값이면 방문조차 안 한 것이다.

    long 은 차분 0, short 는 0 - 4 = -4 이므로 합계는 -4 여야 한다. 5.0 이나 0.0 이 나오면
    사라진 series 를 건너뛴 것이다.
    """
    reading = _summed_reading(
        _snapshot(_BEFORE_TWO_DIRECTIONS),
        _snapshot(_AFTER_ONE_DIRECTION),
        "qb_live_conditional_placed_total",
    )
    assert reading is not None
    assert reading.value == -4.0


def test_identity_check_refuses_when_a_series_vanished() -> None:
    """가드가 합계까지 전파되는지 — basis 가 값에만 붙고 검산에 안 닿으면 무의미하다."""
    before, after = _snapshot(_BEFORE_TWO_DIRECTIONS), _snapshot(_AFTER_ONE_DIRECTION)
    check = placement_identity_check(
        placed=_summed_reading(before, after, "qb_live_conditional_placed_total"),  # type: ignore[arg-type]
        conditional_placed=CounterReading(
            name="qb_live_conditional_guard_total", value=0.0, basis=CounterBasis.delta
        ),
        market_converted=CounterReading(
            name="qb_live_conditional_guard_total", value=0.0, basis=CounterBasis.delta
        ),
    )
    assert check.comparable is False
    assert check.holds is None


def test_both_directions_present_still_reads_as_a_clean_delta() -> None:
    """★음성 대조 — 합집합 순회가 정상 케이스를 오염시키지 않는지."""
    after_grown = _snapshot(
        'qb_live_conditional_placed_total{direction="long"} 7.0\n'
        'qb_live_conditional_placed_total{direction="short"} 6.0\n'
    )
    reading = _summed_reading(
        _snapshot(_BEFORE_TWO_DIRECTIONS), after_grown, "qb_live_conditional_placed_total"
    )
    assert reading is not None
    assert reading.basis is CounterBasis.delta
    assert reading.value == 4.0


def test_new_series_in_after_only_is_still_unknown() -> None:
    """반대 방향(after 에만 새로 생김)은 R2-④ 규칙 그대로 `unknown` 이다."""
    reading = _summed_reading(
        _snapshot(_AFTER_ONE_DIRECTION),
        _snapshot(_BEFORE_TWO_DIRECTIONS),
        "qb_live_conditional_placed_total",
    )
    assert reading is not None
    assert reading.basis is CounterBasis.unknown
