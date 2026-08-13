# pine_v2 array.* 최소 서브셋 실행/coverage 테스트 (G2 — 2026-07-12 pine-batch QA)
"""Pine v5/v6 array.* 최소 서브셋.

지원 (bs_indicator + DrFXGOD 실사용 표면):
- 생성: new_float / new_int / new_bool / new_string / new_line / new_label / new_box
- 조작: push / pop / get / set / clear / size / shift / unshift

시멘틱:
- Pine array 는 **참조 타입** — `var float[] x = array.new_float(0)` 후 in-place
  mutation 이 bar 간 영속 (PersistentStore 는 객체 identity 보관).
- 범위 밖 index → PineRuntimeError (TV runtime error 와 동일하게 loud).
- 미지원 array 함수 (array.avg 등) 는 coverage preflight + runtime 양쪽에서 fail
  (부분 실행 금지 Golden Rule).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
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


def _final(source: str, name: str, bars: int = 3) -> object:
    result = run_historical(source, _ohlcv(bars), strict=True)
    assert result.errors == []
    return result.final_state[name]


def _wrap(body: str) -> str:
    return f'//@version=6\nindicator("t")\n{body}\nplot(close)\n'


class TestArrayOps:
    def test_new_float_empty_size(self) -> None:
        src = _wrap("a = array.new_float(0)\nn = array.size(a)")
        assert _final(src, "n") == 0

    def test_new_float_with_initial(self) -> None:
        src = _wrap("a = array.new_float(3, 1.5)\ns = array.get(a, 0) + array.get(a, 2)")
        assert _final(src, "s") == 3.0

    def test_push_get_size(self) -> None:
        src = _wrap(
            "a = array.new_float(0)\n"
            "array.push(a, 10)\n"
            "array.push(a, 20)\n"
            "n = array.size(a)\n"
            "v = array.get(a, 1)"
        )
        assert _final(src, "n") == 2
        assert _final(src, "v") == 20

    def test_set_overwrites(self) -> None:
        src = _wrap("a = array.new_int(2, 0)\narray.set(a, 1, 7)\nv = array.get(a, 1)")
        assert _final(src, "v") == 7

    def test_pop_returns_last(self) -> None:
        src = _wrap(
            "a = array.new_float(0)\narray.push(a, 1)\narray.push(a, 2)\n"
            "v = array.pop(a)\nn = array.size(a)"
        )
        assert _final(src, "v") == 2
        assert _final(src, "n") == 1

    def test_shift_unshift(self) -> None:
        src = _wrap(
            "a = array.new_float(0)\narray.push(a, 1)\narray.push(a, 2)\n"
            "array.unshift(a, 99)\nfirst = array.shift(a)\nn = array.size(a)"
        )
        assert _final(src, "first") == 99
        assert _final(src, "n") == 2

    def test_clear(self) -> None:
        src = _wrap("a = array.new_bool(3, true)\narray.clear(a)\nn = array.size(a)")
        assert _final(src, "n") == 0

    def test_get_out_of_bounds_raises(self) -> None:
        src = _wrap("a = array.new_float(1, 0.0)\nv = array.get(a, 5)")
        with pytest.raises(PineRuntimeError, match="out of bounds"):
            run_historical(src, _ohlcv(1), strict=True)

    def test_unsupported_array_fn_raises(self) -> None:
        src = _wrap("a = array.new_float(2, 1.0)\nv = array.avg(a)")
        with pytest.raises(PineRuntimeError, match="array"):
            run_historical(src, _ohlcv(1), strict=True)


class TestArrayPersistence:
    def test_var_array_persists_across_bars(self) -> None:
        """bs_indicator 패턴 — var 배열 + bar 마다 push → 크기 누적."""
        src = _wrap("var a = array.new_float(0)\narray.push(a, close)\nn = array.size(a)")
        assert _final(src, "n", bars=5) == 5

    def test_typed_var_array_declaration(self) -> None:
        """v6 typed 선언 `var float[] a = ...` 파싱+실행."""
        src = _wrap(
            "var float[] a = array.new_float(0)\narray.push(a, 1.0)\nn = array.size(a)"
        )
        assert _final(src, "n", bars=4) == 4


class TestArrayWithLoops:
    def test_fill_and_sum_via_for_loop(self) -> None:
        src = _wrap(
            "a = array.new_float(0)\n"
            "for i = 1 to 3\n"
            "    array.push(a, i)\n"
            "s = 0.0\n"
            "for j = 0 to array.size(a) - 1\n"
            "    s := s + array.get(a, j)"
        )
        assert _final(src, "s") == 6

    def test_for_in_over_array(self) -> None:
        src = _wrap(
            "a = array.new_float(0)\n"
            "array.push(a, 2)\narray.push(a, 3)\narray.push(a, 4)\n"
            "s = 0.0\n"
            "for x in a\n"
            "    s := s + x"
        )
        assert _final(src, "s") == 9

    def test_bs_tp_levels_pattern(self) -> None:
        """bs_indicator 핵심 패턴 재현 — TP 레벨 생성 + hit flag 마킹."""
        src = _wrap(
            "var float[] tpLevels = array.new_float(0)\n"
            "var bool[] tpHit = array.new_bool(0)\n"
            "if barstate.isfirst\n"
            "    entry = 100.0\n"
            "    risk = 10.0\n"
            "    for i = 1 to 2\n"
            "        array.push(tpLevels, entry + risk * i)\n"
            "        array.push(tpHit, false)\n"
            "if array.size(tpLevels) > 0\n"
            "    for i = 0 to array.size(tpLevels) - 1\n"
            "        if not array.get(tpHit, i) and high >= array.get(tpLevels, i)\n"
            "            array.set(tpHit, i, true)\n"
            "n = array.size(tpLevels)"
        )
        assert _final(src, "n") == 2


class TestArrayCoverage:
    def test_supported_array_fns_runnable(self) -> None:
        src = _wrap(
            "a = array.new_float(0)\narray.push(a, 1)\n"
            "v = array.get(a, 0)\narray.set(a, 0, 2)\n"
            "array.clear(a)\nn = array.size(a)"
        )
        cov = analyze_coverage(src)
        assert cov.is_runnable, cov.all_unsupported

    def test_unlisted_array_fn_still_unsupported(self) -> None:
        """array namespace 잔여 함수는 여전히 preflight 하드 fail (부분 실행 금지)."""
        src = _wrap("a = array.new_float(2, 1.0)\nv = array.avg(a)")
        cov = analyze_coverage(src)
        assert not cov.is_runnable
        assert "array.avg" in cov.all_unsupported

    def test_bs_indicator_now_runnable(self) -> None:
        """G2 종착 검증 — bs (i4_bs.pine, array 8종+루프 사용) 가 coverage 통과.

        i4_bs 는 tmp_code/pine_code/bs_indicator_medium.pine 의 고정 사본.
        trust-layer baseline 등록은 별도 결정 (RUNNABLE_CORPUS 는 명시 튜플이라 자동 미포함).
        """
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2] / "fixtures" / "pine_corpus_v2" / "i4_bs.pine"
        ).read_text()
        cov = analyze_coverage(source)
        assert cov.is_runnable, cov.all_unsupported


class TestSecurityDegradedFix:
    def test_bare_v4_security_flagged_degraded(self) -> None:
        """G3 — v4 bare `security()` 도 request.security 와 동일하게 degraded 플래그."""
        src = (
            "//@version=4\n"
            'study("t")\n'
            "s = security(syminfo.tickerid, timeframe.period, close)\n"
            "plot(s)\n"
        )
        cov = analyze_coverage(src)
        assert cov.is_runnable  # graceful — 실행은 가능
        assert "security" in set(cov.degraded_calls)
