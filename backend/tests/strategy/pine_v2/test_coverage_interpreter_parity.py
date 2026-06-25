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
from src.strategy.pine_v2.exit_orders import ExitOrderKind


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
# BL-104 — strategy.exit 본격 구현 (NOP 교체). 과거 NOP-warning assert 테스트를
# real-exit assert 로 전환 (T0-pine-oco C3).
# ----------------------------------------------------------------------


def test_strategy_exit_limit_triggers_close_when_price_reached() -> None:
    """strategy.exit 의 limit(TP) 가 도달하면 포지션이 청산된다 (NOP 교체).

    과거: codex G.0 P1 #1 보수적 NOP (open trade 유지). BL-104 본격 구현 후 =
    target 도달 시 exit order 체결. _ohlcv 는 close=100.5+i 단조 상승이라 limit=105
    는 bar4 즈음 high(101+i) 가 도달 → TP 체결.
    """
    source = """//@version=5
strategy("exit limit test", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", "L", limit=105.0)
"""
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    assert result.historical is not None
    state = result.historical.strategy_state
    assert state is not None
    # limit 도달 → 포지션 청산 (entry-only 아님).
    assert len(state.closed_trades) == 1
    assert state.closed_trades[0].exit_kind == ExitOrderKind.TAKE_PROFIT
    assert "L" not in state.open_trades


def test_strategy_exit_no_longer_emits_nop_warning() -> None:
    """본격 구현 후 strategy.exit 는 더 이상 NOP warning 을 남기지 않는다.

    과거 codex G.0 P1 #2 = from_entry/limit/stop/profit 를 NOP warning 에 기록.
    BL-104 후 = 실제 exit order 배치 → NOP warning 제거.
    """
    source = """//@version=5
strategy("exit kwargs test", overlay=true)
if bar_index == 1
    strategy.entry("L", strategy.long)
strategy.exit("X", from_entry="L", limit=200.0, stop=80.0)
"""
    result = parse_and_run_v2(source, _ohlcv(), strict=True)
    assert result.historical is not None
    state = result.historical.strategy_state
    assert state is not None
    # NOP warning 부재 (실제 exit order 배치됨).
    assert not any("strategy.exit" in w and "NOP" in w for w in state.warnings)


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


def test_synthetic_source_history_lag() -> None:
    """hl2[1]/hlc3[1]/ohlc4[1] = 직전 bar 의 합성 source 값 (na 아님).

    coverage 가 hl2/hlc3/ohlc4 를 SUPPORTED 표기하므로 현재 bar 뿐 아니라 lagged 참조도
    정확해야 한다 (codex challenge Finding 1 — `hl2[1]` 이 history series 누락으로 na 반환 →
    silent 오값). `hl2 > hl2[1]` 같은 흔한 패턴이 망가지지 않도록 회귀 차단.
    """
    import math as _math

    source = (
        "//@version=5\n"
        'indicator("synthetic history")\n'
        "h2 = hl2[1]\n"
        "h3 = hlc3[1]\n"
        "o4 = ohlc4[1]\n"
        "plot(close)\n"
    )
    result = parse_and_run_v2(source, _ohlcv(30), strict=True)
    assert result.historical is not None
    vs = result.historical.var_series
    # _ohlcv: bar i → open=100+i, high=101+i, low=99+i, close=100.5+i.
    # bar 1 의 hl2[1] = bar 0 의 (high+low)/2 = (101+99)/2 = 100.0
    assert vs["h2"][1] == 100.0
    assert vs["h3"][1] == (101.0 + 99.0 + 100.5) / 3  # bar0 hlc3
    assert vs["o4"][1] == (100.0 + 101.0 + 99.0 + 100.5) / 4  # bar0 ohlc4
    # bar 0 에서 hl2[1] = na (이력 없음)
    assert _math.isnan(vs["h2"][0])
