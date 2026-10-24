"""native 준비 이력과 실제 대조 구간을 구분하고 미래 제거 검사를 유지한다."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks.verification import native_action_match


def test_native_comparison_uses_warmup_but_repeat_and_prefix_check_all_actions():
    expected = ["long", "short", "hold", "long", "hold", "short", "hold"]
    first = ["hold", "hold", "hold", "long", "hold", "short", "hold"]
    assert native_action_match(expected, first, first, first[:5], 3)
    changed = ["long", *first[1:5]]
    assert not native_action_match(expected, first, first, changed, 3)
    assert not native_action_match(expected, first, expected, first[:5], 3)
    changed = [*first[:5], "hold", "hold"]
    assert not native_action_match(expected, changed, changed, changed[:5], 3)


def test_native_comparison_rejects_missing_checked_or_prefix_window():
    for actions, prefix in ((["hold"] * 4, ["hold"] * 3), (["hold"] * 7, ["hold"] * 3)):
        with pytest.raises(ValueError, match="준비봉"):
            native_action_match(actions, actions, actions, prefix, 3)
