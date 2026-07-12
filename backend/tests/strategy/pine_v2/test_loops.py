# pine_v2 for/while/break/continue 루프 실행 시멘틱 테스트 (G1 — 2026-07-12 pine-batch QA)
"""Pine v5/v6 루프 시멘틱 (TV 공식 문서 대조 완료).

TV 규칙 (pine-script-docs/language/loops):
- `for i = from to to [by step]` — **inclusive** 양 끝 포함.
- 방향 자동: to > from → 상향, to < from → 하향. `for i = 1 to 0` 은 1, 0 두 번 실행.
- `by step` 은 양수 크기(magnitude) — 방향은 여전히 from/to 비교로 결정.
- `while` 은 매 iteration 전 조건 평가.
- TV 는 loop 500ms 시간 제한 → 본 인터프리터는 iteration 상한(PineRuntimeError) 채택.

G1 이전 인터프리터는 루프 문을 **조용히 skip** (Trust Layer 구멍) — 본 테스트가 회귀 방어.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import PineRuntimeError


def _ohlcv(n: int = 3) -> pd.DataFrame:
    closes = [100.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [10.0] * n,
        }
    )


def _final(source: str, name: str) -> object:
    result = run_historical(source, _ohlcv(), strict=True)
    assert result.errors == []
    return result.final_state[name]


def _wrap(body: str) -> str:
    return f'//@version=6\nindicator("t")\n{body}\nplot(close)\n'


class TestForTo:
    def test_ascending_sum(self) -> None:
        src = _wrap("s = 0.0\nfor i = 0 to 5\n    s := s + i")
        assert _final(src, "s") == 15

    def test_descending_auto_direction(self) -> None:
        """to < from → 자동 하향 반복 (TV 문서: counts downward instead)."""
        src = _wrap("s = 0.0\nfor i = 5 to 1\n    s := s + i")
        assert _final(src, "s") == 15

    def test_reverse_edge_1_to_0_runs_twice(self) -> None:
        """Pine 함정: `for i = 1 to 0` 은 0회가 아니라 1, 0 으로 2회 실행."""
        src = _wrap("cnt = 0\nfor i = 1 to 0\n    cnt := cnt + 1")
        assert _final(src, "cnt") == 2

    def test_equal_bounds_single_iteration(self) -> None:
        src = _wrap("cnt = 0\nfor i = 3 to 3\n    cnt := cnt + 1")
        assert _final(src, "cnt") == 1

    def test_explicit_step_ascending(self) -> None:
        src = _wrap("s = 0.0\nfor i = 0 to 10 by 2\n    s := s + i")
        assert _final(src, "s") == 30

    def test_explicit_step_magnitude_descending(self) -> None:
        """하향에서도 by 는 양수 크기 — 방향은 from/to 가 결정."""
        src = _wrap("s = 0.0\nfor i = 10 to 0 by 2\n    s := s + i")
        assert _final(src, "s") == 30

    def test_loop_var_float_bound_expression(self) -> None:
        """bs_indicator 패턴: `for i = 1 to numTPs - 1` (bound 가 표현식)."""
        src = _wrap(
            "numTPs = math.floor(3.0)\ns = 0.0\nfor i = 1 to numTPs - 1\n    s := s + i"
        )
        assert _final(src, "s") == 3  # 1 + 2

    def test_break(self) -> None:
        src = _wrap("s = 0.0\nfor i = 0 to 5\n    s := s + i\n    if i == 3\n        break")
        assert _final(src, "s") == 6  # 0+1+2+3

    def test_continue(self) -> None:
        src = _wrap(
            "s = 0.0\nfor i = 0 to 5\n    if i % 2 == 1\n        continue\n    s := s + i"
        )
        assert _final(src, "s") == 6  # 0+2+4

    def test_nested_loops(self) -> None:
        src = _wrap(
            "cnt = 0\nfor i = 0 to 2\n    for j = 0 to 2\n        cnt := cnt + 1"
        )
        assert _final(src, "cnt") == 9

    def test_break_only_inner_loop(self) -> None:
        src = _wrap(
            "cnt = 0\n"
            "for i = 0 to 2\n"
            "    for j = 0 to 5\n"
            "        if j == 1\n"
            "            break\n"
            "        cnt := cnt + 1"
        )
        assert _final(src, "cnt") == 3  # 외부 3회 × 내부 j=0 1회


class TestWhile:
    def test_countdown(self) -> None:
        src = _wrap("j = 10\ncnt = 0\nwhile j > 0\n    j := j - 1\n    cnt := cnt + 1")
        assert _final(src, "cnt") == 10

    def test_condition_false_never_runs(self) -> None:
        src = _wrap("cnt = 0\nwhile false\n    cnt := cnt + 1")
        assert _final(src, "cnt") == 0

    def test_break(self) -> None:
        src = _wrap(
            "j = 0\nwhile j < 100\n    j := j + 1\n    if j == 7\n        break"
        )
        assert _final(src, "j") == 7

    def test_continue(self) -> None:
        src = _wrap(
            "j = 0\ns = 0\n"
            "while j < 6\n"
            "    j := j + 1\n"
            "    if j % 2 == 1\n"
            "        continue\n"
            "    s := s + j"
        )
        assert _final(src, "s") == 12  # 2+4+6

    def test_infinite_loop_iteration_cap(self) -> None:
        """TV 는 500ms 시간 제한 — 본 엔진은 iteration 상한으로 loud fail."""
        src = _wrap("cnt = 0\nwhile true\n    cnt := cnt + 1")
        with pytest.raises(PineRuntimeError, match=r"[Ll]oop"):
            run_historical(src, _ohlcv(1), strict=True)


class TestLoopScopes:
    def test_loop_inside_user_function(self) -> None:
        src = _wrap(
            "f(n) =>\n"
            "    acc = 0.0\n"
            "    for i = 0 to n\n"
            "        acc := acc + i\n"
            "    acc\n"
            "s = f(5)"
        )
        assert _final(src, "s") == 15

    def test_loop_inside_if_branch(self) -> None:
        src = _wrap(
            "s = 0.0\n"
            "if close > 0\n"
            "    for i = 1 to 3\n"
            "        s := s + i"
        )
        assert _final(src, "s") == 6

    def test_loop_accumulates_into_persistent_var(self) -> None:
        """var 영속 변수와 루프 조합 — bar 마다 +6 누적 (3 bars → 18)."""
        src = _wrap("var s = 0.0\nfor i = 1 to 3\n    s := s + i")
        assert _final(src, "main::s") == 18
