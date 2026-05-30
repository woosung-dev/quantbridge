"""Sprint 23 BL-098/099 — coverage.py supported list ↔ interpreter dispatch parity.

coverage.py 가 supported 라고 약속하는 함수가 interpreter runtime 에서 fail 하지
않는지 검증. preflight pass 후 silent runtime fail risk 차단.

- BL-099 vline: `coverage.py:88 _PLOT_FUNCTIONS` ✅ → `interpreter.py:_NOP_NAMES`
  에 `vline` 추가 (silent NOP, 시각 요소라 backtest 영향 없음).
- BL-098 strategy.exit: `coverage.py:62 _STRATEGY_FUNCTIONS` ✅ → `interpreter.py`
  에서 NOP + unsupported_kwargs metadata 기록 (codex G.0 P1 #1+#2 — close-fallback
  은 wrong-id close + Pine semantic 위반, 보수적 NOP 채택).
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2.compat import parse_and_run_v2
from src.strategy.pine_v2.coverage import (
    _MATH_FUNCTIONS,
    _STRING_FUNCTIONS,
    SUPPORTED_ATTRIBUTES,
)


def _ohlcv(n: int = 30) -> pd.DataFrame:
    """Minimal OHLCV — 테스트가 backtest 결과 본체엔 관심 없음."""
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(n)],
            "high": [101.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [100.5 + i for i in range(n)],
            "volume": [1000.0] * n,
        },
        index=pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"),
    )


# ----------------------------------------------------------------------
# BL-099 — vline
# ----------------------------------------------------------------------


def test_vline_coverage_interpreter_parity_nop() -> None:
    """vline 호출 시 PineRuntimeError 없이 silent NOP.

    coverage.py:88 의 _PLOT_FUNCTIONS 에 vline 등록되어 preflight pass.
    Sprint 23 이전: interpreter._NOP_NAMES 에 vline 빠짐 → runtime fail.
    Sprint 23 fix: _NOP_NAMES 에 vline 추가 (1줄).
    """
    source = """//@version=5
indicator("vline test", overlay=true)
vline(bar_index, color=color.red, linewidth=1)
"""
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    # NOP 이므로 indicator 트랙 (M) 으로 분류 + historical run 성공
    assert result.track in ("S", "M")
    assert result.historical is not None


# ----------------------------------------------------------------------
# BL-098 — strategy.exit (codex G.0 P1 #1+#2 — 보수적 NOP)
# ----------------------------------------------------------------------


def test_strategy_exit_nop_does_not_close_open_trade() -> None:
    """strategy.exit 호출이 open trade 를 close 하지 않음.

    codex G.0 P1 #1: Pine strategy.exit 는 exit order 예약 (target price trigger),
    즉시 close 아님. close-fallback 시 entry 직후 거짓 close (양성).
    Sprint 23 fix: silent NOP — open trade 그대로 유지. backtest 결과 = entry-only.
    """
    source = """//@version=5
strategy("exit nop test", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 5
    strategy.exit("TP", "L", limit=200.0)
"""
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    assert result.historical is not None
    state = result.historical.strategy_state
    assert state is not None
    # strategy.exit 가 close 안 했으므로 open trade 그대로 유지
    assert len(state.open_trades) >= 1, "exit NOP 인데 open trade 가 닫힘 (codex G.0 P1 #1 회귀)"
    # exit 가 NOP 라서 _eval_call 실패 안 함 + warnings 에 기록됨
    warnings = state.warnings
    assert any("strategy.exit" in w and "NOP" in w for w in warnings), (
        f"expected NOP warning, got: {warnings}"
    )


def test_strategy_exit_records_from_entry_and_unsupported_kwargs() -> None:
    """codex G.0 P1 #2 verifier — from_entry / limit / stop / profit 모두 기록.

    Pine 첫 인자 id 는 exit order id, 청산 대상은 from_entry. close-fallback 시
    `close("TP")` 가 nonexistent → silent skip. NOP 패턴은 from_entry 를 명시
    warning 에 기록하여 사용자가 "어떤 entry 를 close 하려 했는지" 확인 가능.
    """
    source = """//@version=5
strategy("exit kwargs test", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 5
    strategy.exit("TP", from_entry="L", limit=200.0, stop=80.0, profit=10.0)
"""
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    assert result.historical is not None
    warnings = result.historical.strategy_state.warnings
    nop_warnings = [w for w in warnings if "strategy.exit" in w]
    assert len(nop_warnings) >= 1
    msg = nop_warnings[0]
    # from_entry 명시
    assert "'L'" in msg or "from_entry='L'" in msg
    # unsupported kwargs (limit / stop / profit) 모두 표시
    assert "limit" in msg
    assert "stop" in msg
    assert "profit" in msg


def test_strategy_exit_when_false_skips() -> None:
    """when=false 면 NOP 도 skip (entry/close 와 동일 정책)."""
    source = """//@version=5
strategy("exit when false", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("TP", "L", when=false)
"""
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    assert result.historical is not None
    # when=false 면 warning 기록도 안 됨
    warnings = result.historical.strategy_state.warnings
    assert not any("strategy.exit" in w for w in warnings)


# ----------------------------------------------------------------------
# S2 (전체 정검 P1-10/13) — 망라 parity: coverage SUPPORTED set 전체 순회.
#
# 기존 예시 기반 parity 테스트(vline/strategy.exit)는 hand-written 1건씩이라
# 신규 추가 심볼이 무방비로 누출됐다 (coverage SUPPORTED 인데 interpreter 미구현
# → preflight pass 후 runtime PineRuntimeError). 아래 3 망라 테스트가
# SUPPORTED set 전체를 순회해 누출 *클래스* 를 구조적으로 차단한다 (ADR-003
# 부분실행 금지 invariant). 향후 SUPPORTED 추가 시 interpreter 미구현이면
# 본 테스트가 CI 에서 자동 RED.
# ----------------------------------------------------------------------


def _run_indicator_snippet(body: str) -> None:
    """`x = <body>` 를 strict=True 로 실행 — PineRuntimeError 발생 시 테스트 실패."""
    source = f'//@version=5\nindicator("parity")\nx = {body}\nplot(close)\n'
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    assert result.historical is not None


@pytest.mark.parametrize("attr", sorted(SUPPORTED_ATTRIBUTES))
def test_all_supported_attributes_runnable(attr: str) -> None:
    """coverage.SUPPORTED_ATTRIBUTES 전 심볼이 interpreter 에서 PineRuntimeError 없이 평가.

    coverage 가 is_runnable=True 로 약속한 attribute 는 런타임에서 반드시 평가 가능해야
    한다. 누출 시 backtest=runtime fail(strict=True) / live=silent 오신호(strict=False).
    """
    _run_indicator_snippet(attr)


# 심볼별 대표 인자 템플릿. 신규 string 함수 추가 시 여기 보강 안 하면 KeyError 로
# 테스트가 강제 실패 → parity 유지 의무 (silent skip 차단).
_STRING_FUNCTION_CALLS: dict[str, str] = {
    "str.tostring": "str.tostring(close)",
    "tostring": "tostring(close)",
    "str.tonumber": 'str.tonumber("3.14")',
    "tonumber": 'tonumber("3.14")',
    "str.format": 'str.format("{0}", close)',
    "str.length": 'str.length("abc")',
}


@pytest.mark.parametrize("fn", sorted(_STRING_FUNCTIONS))
def test_all_string_functions_runnable(fn: str) -> None:
    """coverage._STRING_FUNCTIONS 전 심볼이 interpreter 에서 평가 가능 (str.* dotted 누출 검출)."""
    _run_indicator_snippet(_STRING_FUNCTION_CALLS[fn])


# math.pow/max/min 은 2 인자, 그 외는 1 인자.
_MATH_TWO_ARG: frozenset[str] = frozenset({"math.pow", "math.max", "math.min"})


@pytest.mark.parametrize("fn", sorted(_MATH_FUNCTIONS))
def test_all_math_functions_runnable(fn: str) -> None:
    """coverage._MATH_FUNCTIONS 전 심볼이 interpreter math dispatch 에서 평가 가능 (math.log10 누출 검출)."""
    args = "2.0, 3.0" if fn in _MATH_TWO_ARG else "2.0"
    _run_indicator_snippet(f"{fn}({args})")
