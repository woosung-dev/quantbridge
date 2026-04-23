"""B-2: valuewhen deque cap 테스트.

- 501회 true → history len ≤ 500 (cap 보장)
- occurrence=-1 → nan
- occurrence=1.0 (float) → int(1) 으로 처리
"""
from __future__ import annotations

import math
from collections import deque

import pytest

from src.strategy.pine_v2.stdlib import IndicatorState, ta_valuewhen, _VALUEWHEN_MAX_HIST


def test_valuewhen_occurrence_cap() -> None:
    """501번 true 발생 시 history len ≤ 500 (deque maxlen cap)."""
    state = IndicatorState()
    node_id = 1

    # 501번 cond=True, source=i
    for i in range(501):
        ta_valuewhen(state, node_id, True, float(i), 0)

    hist: deque = state.buffers[node_id]["history"]
    assert len(hist) <= _VALUEWHEN_MAX_HIST
    assert len(hist) == _VALUEWHEN_MAX_HIST  # 정확히 500


def test_valuewhen_occurrence_cap_oldest_dropped() -> None:
    """500 cap에서 가장 오래된 값(0.0)이 드롭되고 최신값이 보존."""
    state = IndicatorState()
    node_id = 2

    for i in range(501):
        ta_valuewhen(state, node_id, True, float(i), 0)

    # occurrence=0 → 가장 최근 값 = 500.0
    val = ta_valuewhen(state, node_id, False, 0.0, 0)
    assert val == pytest.approx(500.0)

    # occurrence=499 → 499번째 최근 = 1.0 (0.0은 드롭됨)
    val_oldest = ta_valuewhen(state, node_id, False, 0.0, 499)
    assert val_oldest == pytest.approx(1.0)


def test_valuewhen_negative_occurrence() -> None:
    """occurrence=-1 → nan."""
    state = IndicatorState()
    node_id = 3
    ta_valuewhen(state, node_id, True, 42.0, 0)
    result = ta_valuewhen(state, node_id, False, 0.0, -1)
    assert math.isnan(result)


def test_valuewhen_float_occurrence() -> None:
    """occurrence=1.0 (float) → int(1) 으로 처리."""
    state = IndicatorState()
    node_id = 4

    ta_valuewhen(state, node_id, True, 10.0, 0)
    ta_valuewhen(state, node_id, True, 20.0, 0)

    # occurrence=1.0 → int(1) → 두 번째로 최근인 10.0
    result = ta_valuewhen(state, node_id, False, 0.0, 1)  # type: ignore[arg-type]
    assert result == pytest.approx(10.0)


def test_valuewhen_empty_history_nan() -> None:
    """아직 cond=True가 없으면 nan."""
    state = IndicatorState()
    node_id = 5
    result = ta_valuewhen(state, node_id, False, 0.0, 0)
    assert math.isnan(result)


def test_valuewhen_occurrence_exceeds_history() -> None:
    """occurrence가 history 길이 초과 → nan."""
    state = IndicatorState()
    node_id = 6
    ta_valuewhen(state, node_id, True, 5.0, 0)
    # history에 1개 있음, occurrence=1 → nan
    result = ta_valuewhen(state, node_id, False, 0.0, 1)
    assert math.isnan(result)


def test_valuewhen_deque_type() -> None:
    """내부 history가 deque 타입 확인."""
    state = IndicatorState()
    node_id = 7
    ta_valuewhen(state, node_id, True, 1.0, 0)
    hist = state.buffers[node_id]["history"]
    assert isinstance(hist, deque)
    assert hist.maxlen == _VALUEWHEN_MAX_HIST
