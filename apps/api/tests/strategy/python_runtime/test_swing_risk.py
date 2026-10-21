"""고정 R·부분 청산·계획 세대와 분봉 내부 경로의 회귀 계약."""

from dataclasses import replace
from decimal import Decimal
from random import Random

import pytest

from src.strategy.python_runtime import swing_risk
from src.strategy.python_runtime.swing_risk import (
    CandleOutcome,
    RiskEvent,
    StaleRiskGeneration,
    _marked_pnl,
    _replay_path,
    apply_event,
    create_plan,
    initial_state,
    queue_close,
    replace_plan,
    replay_candle,
)

D = Decimal


def plan(direction="long", generation=1, qty="1"):
    return create_plan(
        entry_price=D("100"),
        qty=D(qty),
        direction=direction,
        previous_bars=[
            {"low": D("90"), "high": D("110")},
            {"low": D("91"), "high": D("109")},
        ],
        generation=generation,
    )


def candle(state, open_, high, low, close):
    return replay_candle(state, open_=D(open_), high=D(high), low=D(low), close=D(close))


@pytest.mark.parametrize(
    ("direction", "extreme", "stop", "target", "activation"),
    [("long", "90", "89", "116.5", "122"), ("short", "110", "111", "83.5", "78")],
)
def test_fixed_r_includes_buffer_and_short_is_symmetric(
    direction, extreme, stop, target, activation
):
    result = plan(direction)
    assert result.reference_extreme == D(extreme)
    assert result.stop_loss == D(stop)
    assert result.risk == D("11")
    assert result.tp_price == D(target)
    assert result.trailing_activation == D(activation)
    assert result.trailing_distance == D("22")


@pytest.mark.parametrize("direction", ["long", "short"])
def test_two_completed_bars_are_required(direction):
    with pytest.raises(ValueError, match="정확히 두"):
        create_plan(
            entry_price=D("100"),
            qty=D("1"),
            direction=direction,
            previous_bars=[{"low": D("90"), "high": D("110")}],
            generation=1,
        )


@pytest.mark.parametrize("price", ["100", "101"])
def test_long_swing_at_or_above_entry_is_rejected(price):
    with pytest.raises(ValueError, match="손실 방향"):
        create_plan(
            entry_price=D("100"),
            qty=D("1"),
            direction="long",
            previous_bars=[{"low": D(price), "high": D("110")}] * 2,
            generation=1,
        )


@pytest.mark.parametrize("price", ["100", "99"])
def test_short_swing_at_or_below_entry_is_rejected(price):
    with pytest.raises(ValueError, match="손실 방향"):
        create_plan(
            entry_price=D("100"),
            qty=D("1"),
            direction="short",
            previous_bars=[{"low": D("90"), "high": D(price)}] * 2,
            generation=1,
        )


@pytest.mark.parametrize("entry", [D("NaN"), D("Infinity"), D("0"), 100.0])
def test_entry_must_be_a_finite_positive_decimal(entry):
    with pytest.raises(ValueError, match="Decimal"):
        create_plan(
            entry_price=entry,
            qty=D("1"),
            direction="long",
            previous_bars=[{"low": D("90"), "high": D("110")}] * 2,
            generation=1,
        )


def test_partial_tp_is_exactly_half_and_only_fills_once():
    before = initial_state(plan(qty="3"))
    result = candle(before, "100", "117", "99", "116.5")
    assert result.events == (RiskEvent(1, "partial_tp", D("116.5"), D("1.5")),)
    assert result.state.remaining_qty == D("1.5")
    assert result.state.tp_filled
    assert not result.state.trailing_active
    assert candle(result.state, "116.5", "120", "115", "119").events == ()
    assert before.remaining_qty == D("3") and not before.tp_filled


@pytest.mark.parametrize(
    ("direction", "open_", "high", "low", "close"),
    [("long", "110", "122", "110", "122"), ("short", "90", "90", "78", "78")],
)
def test_exact_two_r_activation_sets_break_even(direction, open_, high, low, close):
    result = candle(initial_state(plan(direction)), open_, high, low, close)
    assert result.state.trailing_active
    assert result.state.stop_price == D("100")
    assert result.state.remaining_qty == D("0.5")
    assert [event.kind for event in result.events] == ["partial_tp"]


@pytest.mark.parametrize(
    ("direction", "first", "second", "retreat", "stop"),
    [
        (
            "long",
            ("110", "122", "110", "122"),
            ("125", "130", "124", "129"),
            ("129", "129", "120", "121"),
            "108",
        ),
        (
            "short",
            ("90", "90", "78", "78"),
            ("75", "76", "70", "71"),
            ("71", "80", "71", "79"),
            "92",
        ),
    ],
)
def test_trailing_ratchets_only_in_favorable_direction(direction, first, second, retreat, stop):
    active = candle(initial_state(plan(direction)), *first).state
    advanced = candle(active, *second).state
    retreated = candle(advanced, *retreat).state
    assert advanced.stop_price == D(stop) == retreated.stop_price
    assert advanced.plan.risk == active.plan.risk == D("11")


@pytest.mark.parametrize(
    ("direction", "open_", "high", "low", "close", "stop"),
    [("long", "100", "130", "99", "125", "108"), ("short", "100", "101", "70", "75", "92")],
)
def test_new_trailing_stop_cannot_fill_retroactively_at_prior_open(
    direction, open_, high, low, close, stop
):
    result = candle(initial_state(plan(direction)), open_, high, low, close)
    assert result.ambiguous
    assert [event.kind for event in result.events] == ["partial_tp", "trailing_stop"]
    assert result.events[-1].price == D(stop)
    assert result.events[-1].price != D(open_)
    assert result.state.remaining_qty == 0


def test_ambiguous_tp_and_stop_selects_lower_marked_pnl_path():
    result = candle(initial_state(plan()), "100", "120", "88", "100")
    assert result.ambiguous
    assert result.path == "O-L-H-C"
    assert result.events == (RiskEvent(1, "stop_loss", D("89"), D("1")),)


@pytest.mark.parametrize(
    ("direction", "ohlc", "fill"),
    [("long", ("80", "90", "79", "85"), "80"), ("short", ("120", "121", "112", "115"), "120")],
)
def test_adverse_opening_gap_fills_at_open_instead_of_stale_stop(direction, ohlc, fill):
    result = candle(initial_state(plan(direction)), *ohlc)
    assert result.events == (RiskEvent(1, "stop_loss", D(fill), D("1")),)
    assert not result.ambiguous


def test_favorable_tp_gap_fills_at_open_and_activation_does_not_fill():
    result = candle(initial_state(plan()), "125", "125", "124", "125")
    assert result.events == (RiskEvent(1, "partial_tp", D("125"), D("0.5")),)
    assert result.state.trailing_active and result.state.stop_price == D("103")


@pytest.mark.parametrize(
    ("direction", "ohlc", "fill"),
    [
        ("long", ("120", "120", "119", "120"), "120"),
        ("short", ("80", "81", "80", "80"), "80"),
    ],
)
def test_resting_partial_tp_gets_favorable_opening_gap_price(direction, ohlc, fill):
    result = candle(initial_state(plan(direction)), *ohlc)
    assert result.events == (RiskEvent(1, "partial_tp", D(fill), D("0.5")),)
    assert result.state.remaining_qty == D("0.5")
    assert not result.state.trailing_active


def test_explicit_plan_replacement_keeps_fills_and_discards_old_pending_exits():
    first = candle(initial_state(plan()), "110", "122", "110", "122")
    pending = queue_close(first.state, generation=1)
    new_plan = create_plan(
        entry_price=D("100"),
        qty=D("1"),
        direction="long",
        previous_bars=[{"low": D("95"), "high": D("105")}] * 2,
        generation=2,
    )
    fresh = replace_plan(pending, new_plan)
    assert fresh.remaining_qty == fresh.plan.initial_qty == D("0.5")
    assert fresh.stop_price == D("94.5")
    assert fresh.plan.tp_price == D("108.25")
    assert not fresh.pending_close and not fresh.tp_filled and not fresh.trailing_active
    # 첫 계획의 체결 기록과 입력 상태를 새 계획이 되돌려 쓰지 않는다.
    assert first.events == (RiskEvent(1, "partial_tp", D("116.5"), D("0.5")),)
    assert pending.tp_filled and pending.trailing_active and pending.pending_close
    result = candle(fresh, "100", "109", "99", "108")
    assert result.events == (RiskEvent(2, "partial_tp", D("108.25"), D("0.25")),)


def test_stale_generation_close_and_partial_events_are_rejected():
    fresh = replace_plan(initial_state(plan()), plan(generation=2))
    with pytest.raises(StaleRiskGeneration):
        queue_close(fresh, generation=1)
    for kind, qty in (("partial_tp", "0.5"), ("close", "1"), ("stop_loss", "1")):
        with pytest.raises(StaleRiskGeneration):
            apply_event(fresh, RiskEvent(1, kind, D("100"), D(qty)))


def test_current_generation_close_executes_at_next_candle_open():
    pending = queue_close(initial_state(plan()), generation=1)
    result = candle(pending, "105", "120", "80", "100")
    assert result.events == (RiskEvent(1, "close", D("105"), D("1")),)
    assert result.state.remaining_qty == 0 and not result.state.pending_close
    assert not result.ambiguous


def test_duplicate_partial_fill_and_excess_quantity_are_rejected():
    state = initial_state(plan())
    event = RiskEvent(1, "partial_tp", D("116.5"), D("0.5"))
    partial = apply_event(state, event)
    with pytest.raises(ValueError, match="한 번"):
        apply_event(partial, event)
    with pytest.raises(ValueError, match="초과"):
        apply_event(partial, RiskEvent(1, "close", D("100"), D("1")))


def test_replace_requires_new_generation_and_the_same_open_position():
    state = initial_state(plan())
    with pytest.raises(StaleRiskGeneration):
        replace_plan(state, plan())
    with pytest.raises(ValueError, match="같은 포지션"):
        replace_plan(state, plan(direction="short", generation=2))
    with pytest.raises(ValueError, match="청산된"):
        replace_plan(replace(state, remaining_qty=D("0")), plan(generation=2))


def test_invalid_ohlc_is_rejected_and_closed_state_does_not_refill():
    with pytest.raises(ValueError, match="OHLC"):
        candle(initial_state(plan()), "100", "99", "90", "100")
    closed = candle(initial_state(plan()), "100", "100", "80", "90").state
    result = candle(closed, "100", "140", "70", "120")
    assert result.state == closed and result.events == () and not result.ambiguous


def reference_replay(state, open_, high, low, close):
    """최적화 전의 두 경로 전량 재생을 비교 오라클로 보존한다."""
    first = _replay_path(state, (open_, high, low, close), "O-H-L-C")
    second = _replay_path(state, (open_, low, high, close), "O-L-H-C")
    sign = D("1") if state.plan.direction == "long" else D("-1")
    selected = min(
        (first, second),
        key=lambda result: (
            _marked_pnl(result, close),
            result.state.trailing_active,
            sign * result.state.stop_price,
        ),
    )
    return CandleOutcome(
        selected.state,
        selected.events,
        first.state != second.state or first.events != second.events,
        selected.path,
    )


@pytest.mark.parametrize("direction", ["long", "short"])
def test_fast_paths_match_original_two_path_replay_across_stages(direction):
    rng = Random(20261021)
    initial = initial_state(plan(direction))
    partial = apply_event(initial, RiskEvent(1, "partial_tp", initial.plan.tp_price, D("0.5")))
    active = replace(partial, trailing_active=True, stop_price=D("100"))
    advanced = replace(active, stop_price=D("108") if direction == "long" else D("92"))
    states = [initial, partial, active, advanced, queue_close(active, generation=1)]
    for state in states:
        for _ in range(500):
            open_ = D(rng.randrange(7000, 14001)) / 100
            close = D(rng.randrange(7000, 14001)) / 100
            high = max(open_, close) + D(rng.randrange(0, 1501)) / 100
            low = min(open_, close) - D(rng.randrange(0, 1501)) / 100
            assert replay_candle(
                state, open_=open_, high=high, low=low, close=close
            ) == reference_replay(state, open_, high, low, close)


@pytest.mark.parametrize(
    ("direction", "stage", "ohlc"),
    [
        ("long", "initial", ("100", "110", "95", "105")),
        ("short", "initial", ("100", "105", "90", "95")),
        ("long", "partial", ("117", "121", "110", "120")),
        ("short", "partial", ("83", "90", "79", "80")),
        ("long", "active", ("125", "130", "120", "128")),
        ("short", "active", ("75", "80", "70", "72")),
        # 경계와 정확한 접촉은 원본 재생에 넘겨 체결을 놓치지 않는다.
        ("long", "initial", ("100", "116.5", "89", "100")),
        ("short", "initial", ("100", "111", "83.5", "100")),
        ("long", "partial", ("117", "122", "110", "120")),
        ("short", "partial", ("83", "90", "78", "80")),
        ("long", "active", ("125", "130", "108", "120")),
        ("short", "active", ("75", "92", "70", "80")),
    ],
)
def test_fast_path_representatives_and_exact_boundaries_match(direction, stage, ohlc):
    state = initial_state(plan(direction))
    if stage != "initial":
        state = apply_event(state, RiskEvent(1, "partial_tp", state.plan.tp_price, D("0.5")))
    if stage == "active":
        state = replace(state, trailing_active=True, stop_price=D("100"))
    open_, high, low, close = map(D, ohlc)
    assert replay_candle(state, open_=open_, high=high, low=low, close=close) == reference_replay(
        state, open_, high, low, close
    )


@pytest.mark.parametrize(
    ("direction", "stage", "ohlc"),
    [
        ("long", "initial", ("100", "110", "95", "105")),
        ("short", "initial", ("100", "105", "90", "95")),
        ("long", "partial", ("117", "121", "110", "120")),
        ("short", "partial", ("83", "90", "79", "80")),
        ("long", "active", ("125", "130", "120", "128")),
        ("short", "active", ("75", "80", "70", "72")),
    ],
)
def test_proven_no_fill_fast_paths_skip_full_path_replay(monkeypatch, direction, stage, ohlc):
    state = initial_state(plan(direction))
    if stage != "initial":
        state = apply_event(state, RiskEvent(1, "partial_tp", state.plan.tp_price, D("0.5")))
    if stage == "active":
        state = replace(state, trailing_active=True, stop_price=D("100"))

    def unexpected_replay(*args, **kwargs):
        pytest.fail("체결 없음이 증명된 분봉이 전체 경로 재생을 호출했습니다")

    monkeypatch.setattr(swing_risk, "_replay_path", unexpected_replay)
    result = candle(state, *ohlc)
    assert result.events == () and not result.ambiguous
