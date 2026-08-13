# Wave 1 C3 — close 주문 reduce-only over-fill 방지 검증.
"""close 이벤트의 반대편 시장청산이 reduceOnly 없으면 over-fill/포지션 반전 위험.

entry 는 reduce_only=False (신규 포지션 오픈). close 는 reduce_only=True (청산 전용).
"""
from __future__ import annotations


def test_action_is_reduce_only_close_true():
    from src.tasks.live_signal import _action_is_reduce_only

    assert _action_is_reduce_only("close") is True


def test_action_is_reduce_only_entry_false():
    from src.tasks.live_signal import _action_is_reduce_only

    assert _action_is_reduce_only("entry") is False
