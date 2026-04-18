"""Tier-1 가상 strategy 래퍼 단위 테스트 (ADR-011 §2.1.4).

Sprint 8b: indicator + alertcondition → 자동 매매 실행 경로 변환.
"""
from __future__ import annotations

import pytest

from src.strategy.pine_v2.alert_hook import SignalKind
from src.strategy.pine_v2.virtual_strategy import (
    VirtualAction,
    signal_to_action,
)


@pytest.mark.parametrize(
    "signal,expected_kind,expected_id,expected_direction",
    [
        (SignalKind.LONG_ENTRY, "entry", "L", "long"),
        (SignalKind.SHORT_ENTRY, "entry", "S", "short"),
        (SignalKind.LONG_EXIT, "close", "L", None),
        (SignalKind.SHORT_EXIT, "close", "S", None),
    ],
)
def test_signal_to_action_produces_correct_action(
    signal: SignalKind,
    expected_kind: str,
    expected_id: str,
    expected_direction: str | None,
) -> None:
    action = signal_to_action(signal)
    assert action is not None
    assert isinstance(action, VirtualAction)
    assert action.kind == expected_kind
    assert action.trade_id == expected_id
    assert action.direction == expected_direction


@pytest.mark.parametrize("signal", [SignalKind.INFORMATION, SignalKind.UNKNOWN])
def test_signal_to_action_returns_none_for_non_trade_signals(
    signal: SignalKind,
) -> None:
    assert signal_to_action(signal) is None
