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

from src.strategy.pine_v2.compat import parse_and_run_v2


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
