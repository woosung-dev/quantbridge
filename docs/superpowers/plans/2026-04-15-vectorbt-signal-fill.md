# Sprint 2 — vectorbt Engine + SignalResult Fill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unlock `strategy.exit(stop=, limit=)` in the Pine interpreter and wire a pure-library `run_backtest()` function that wraps vectorbt `Portfolio.from_signals()` to produce 5 standard metrics.

**Architecture:** Path 1 — interpreter extension first, engine second. Parser unchanged. A new `src/backtest/engine/` submodule (types/adapter/metrics/public API) consumes `SignalResult` and delegates to vectorbt. No Celery, no HTTP endpoints in this sprint.

**Tech Stack:** Python 3.12, pandas, vectorbt (new: BSD, `>=0.26,<0.27`), pytest.

**Spec:** `docs/superpowers/specs/2026-04-15-vectorbt-signal-fill-design.md`

---

## File Structure

**Create:**
- `backend/src/backtest/engine/__init__.py` — public API (`run_backtest`, type re-exports)
- `backend/src/backtest/engine/types.py` — `BacktestConfig`, `BacktestMetrics`, `BacktestResult`, `BacktestOutcome`
- `backend/src/backtest/engine/adapter.py` — `to_portfolio_kwargs`
- `backend/src/backtest/engine/metrics.py` — `extract_metrics`
- `backend/tests/backtest/__init__.py`
- `backend/tests/backtest/engine/__init__.py`
- `backend/tests/backtest/engine/test_types.py`
- `backend/tests/backtest/engine/test_adapter.py`
- `backend/tests/backtest/engine/test_metrics.py`
- `backend/tests/backtest/engine/test_run_backtest.py`
- `backend/tests/backtest/engine/test_smoke_vectorbt.py`
- `backend/tests/backtest/engine/golden/__init__.py`
- `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/strategy.pine`
- `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv`
- `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/expected.json`
- `backend/tests/backtest/engine/test_golden_backtest.py`

**Modify:**
- `backend/pyproject.toml` — add `vectorbt>=0.26,<0.27` to dependencies
- `backend/src/strategy/pine/interpreter.py` — remove `strategy.exit` blanket Unsupported, add `_BracketState` + kwarg eval, populate `direction`/`sl_stop`/`tp_limit`/`position_size` in `execute_program`
- `backend/src/strategy/pine/__init__.py` — (no changes; public API unchanged)
- `backend/tests/strategy/pine/golden/ema_cross_v4/expected.json` — add `backtest` property
- `backend/tests/strategy/pine/golden/ema_cross_v5/expected.json` — add `backtest` property
- `backend/tests/strategy/pine/test_golden.py` — extend runner to assert `backtest` snapshot when present

---

## Task 1: `strategy.exit(stop=, limit=)` — interpreter support + sl_stop/tp_limit fill

**Files:**
- Modify: `backend/src/strategy/pine/interpreter.py` (current strategy.exit branch at lines 298-310; `execute_program` at 204-226; `_SignalAccumulator` at 191-201)
- Test: `backend/tests/strategy/pine/test_interpreter_bracket.py` (new)

### Step 1.1: Write failing test — sl_stop filled on entry bar, NaN at flat, carry-forward, cleared at exit

- [ ] Create test file:

```python
# backend/tests/strategy/pine/test_interpreter_bracket.py
"""strategy.exit(stop=, limit=) 해금 후 SignalResult 브래킷 필드 채움 검증."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.strategy.pine import parse_and_run


def _ohlcv(close_values: list[float]) -> pd.DataFrame:
    n = len(close_values)
    close = pd.Series(close_values, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": pd.Series([100.0] * n),
        }
    )


def test_strategy_exit_stop_limit_produces_bracket_series():
    """한 번의 long 포지션 동안 sl_stop/tp_limit이 carry forward 되고, 청산 후 NaN."""
    src = """//@version=5
strategy("bracket")
entry_cond = bar_index == 2
exit_cond = bar_index == 5
if entry_cond
    strategy.entry("Long", strategy.long)
if exit_cond
    strategy.close("Long")
strategy.exit("Exit", stop=close * 0.9, limit=close * 1.1)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok", f"expected ok, got {outcome.status}: {outcome.error}"
    signal = outcome.result
    assert signal is not None

    # entry at bar 2, close at bar 5. position open at bars 2,3,4 (exit bar 5 closes at bar-open).
    # Our vectorized semantic: position_open = (entries.cumsum() - exits.cumsum()).clip(0,1)
    # bar: 0  1  2  3  4  5  6  7
    # ent: 0  0  1  0  0  0  0  0  cumsum: 0 0 1 1 1 1 1 1
    # ext: 0  0  0  0  0  1  0  0  cumsum: 0 0 0 0 0 1 1 1
    # pos: 0  0  1  1  1  0  0  0
    assert signal.sl_stop is not None
    assert signal.tp_limit is not None

    # sl_stop at entry bar = close[2] * 0.9 = 10.8; carry forward bars 2,3,4; NaN elsewhere
    expected_sl = [math.nan, math.nan, 12.0 * 0.9, 12.0 * 0.9, 12.0 * 0.9, math.nan, math.nan, math.nan]
    expected_tp = [math.nan, math.nan, 12.0 * 1.1, 12.0 * 1.1, 12.0 * 1.1, math.nan, math.nan, math.nan]

    np.testing.assert_allclose(signal.sl_stop.to_numpy(), expected_sl, equal_nan=True)
    np.testing.assert_allclose(signal.tp_limit.to_numpy(), expected_tp, equal_nan=True)


def test_strategy_exit_only_stop_leaves_tp_limit_none():
    """stop= 만 주면 tp_limit Series는 None 유지."""
    src = """//@version=5
strategy("stop only")
if bar_index == 1
    strategy.entry("Long", strategy.long)
if bar_index == 3
    strategy.close("Long")
strategy.exit("Exit", stop=close * 0.95)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0, 13.0, 14.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok"
    signal = outcome.result
    assert signal is not None
    assert signal.sl_stop is not None
    assert signal.tp_limit is None


def test_strategy_exit_no_args_still_unsupported():
    """stop/limit 둘 다 없으면 여전히 Unsupported — 현재 스프린트는 value-less exit 미지원."""
    src = """//@version=5
strategy("bare exit")
if bar_index == 1
    strategy.entry("Long", strategy.long)
strategy.exit("Exit")
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    # Spec §3.2: no stop/limit kwargs → PineUnsupportedError with feature "strategy.exit(no-args)"
    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "strategy.exit" in outcome.error.feature
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_bracket.py -v`
Expected: FAIL (currently strategy.exit with stop/limit raises `PineUnsupportedError` → outcome.status="unsupported", but our new test expects "ok")

- [ ] **Step 1.3: Implement `_BracketState` and update `_execute_fncall_stmt` / `execute_program`**

In `backend/src/strategy/pine/interpreter.py`:

Add after `_SignalAccumulator` class (around line 201):

```python
@dataclass
class _BracketState:
    """strategy.exit 호출 시 평가된 stop/limit 가격 Series."""

    stop_series: pd.Series | None = None
    limit_series: pd.Series | None = None
```

Update `execute_program` (lines 204-226) to thread the bracket state and build bracket fields at the end:

```python
def execute_program(
    program: Program,
    *,
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> SignalResult:
    """AST 프로그램 실행 → SignalResult 반환."""
    env = Environment.with_ohlcv(
        open_=open_, high=high, low=low, close=close, volume=volume,
    )
    signals = _SignalAccumulator.zero_like(close)
    brackets = _BracketState()

    for stmt in program.statements:
        _execute_statement(stmt, env, signals, brackets=brackets, gate=None)

    return _assemble_signal_result(signals, brackets, env)


def _assemble_signal_result(
    signals: _SignalAccumulator,
    brackets: _BracketState,
    env: Environment,
) -> SignalResult:
    entries = signals.entries.astype(bool)
    exits = signals.exits.astype(bool)

    # 포지션 상태: entries.cumsum() - exits.cumsum() → 0=flat, 1=long
    pos_change = entries.astype(int) - exits.astype(int)
    position = pos_change.cumsum().clip(lower=0, upper=1)

    sl_stop = _carry_bracket(brackets.stop_series, entries, position)
    tp_limit = _carry_bracket(brackets.limit_series, entries, position)

    # direction: 진입이 한 번이라도 있으면 "long" 상수 Series. 없으면 None (Sprint 1 호환).
    direction = pd.Series("long", index=entries.index) if bool(entries.any()) else None

    # position_size는 Task 2에서 채움. 이 Task에선 None 유지.
    return SignalResult(
        entries=entries,
        exits=exits,
        direction=direction,
        sl_stop=sl_stop,
        tp_limit=tp_limit,
        position_size=None,
        metadata={"vars": dict(env.variables)},
    )


def _carry_bracket(
    value_at_call: pd.Series | None,
    entries: pd.Series,
    position: pd.Series,
) -> pd.Series | None:
    """진입 바에서 value를 샘플링, 포지션 기간 동안 carry forward, flat에선 NaN."""
    if value_at_call is None:
        return None
    # strategy.exit이 매 바 호출된다고 가정 → value_at_call은 bar별 가격 Series.
    # 진입 바에서만 캡처 → forward fill → 포지션 기간 외에는 NaN.
    sampled = value_at_call.where(entries)
    carried = sampled.ffill()
    masked = carried.where(position == 1)
    return masked.astype(float)
```

Update `_execute_statement` signature to thread `brackets`:

```python
def _execute_statement(
    node: Node,
    env: Environment,
    signals: _SignalAccumulator,
    *,
    brackets: _BracketState,
    gate: pd.Series | bool | None,
) -> None:
    """문 실행. `gate`는 상위 if의 누적 조건."""
    if isinstance(node, VarDecl):
        env.bind(node.name, evaluate_expression(node.expr, env))
        return

    if isinstance(node, Assign):
        assert isinstance(node.target, Ident)
        env.bind(node.target.name, evaluate_expression(node.value, env))
        return

    if isinstance(node, IfStmt):
        cond_value = evaluate_expression(node.cond, env)
        new_gate = _combine_gate(gate, cond_value)
        for s in node.body:
            _execute_statement(s, env, signals, brackets=brackets, gate=new_gate)
        if node.else_body:
            neg = ~cond_value if isinstance(cond_value, pd.Series) else (not cond_value)
            else_gate = _combine_gate(gate, neg)
            for s in node.else_body:
                _execute_statement(s, env, signals, brackets=brackets, gate=else_gate)
        return

    if isinstance(node, FnCall):
        _execute_fncall_stmt(node, env, signals, brackets=brackets, gate=gate)
        return

    if isinstance(node, ForLoop):
        raise PineUnsupportedError(
            "for loop execution is not supported in sprint 1",
            feature="for",
            category="syntax",
            line=node.source_span.line,
            column=node.source_span.column,
        )

    evaluate_expression(node, env)
```

Replace the current `strategy.exit` branch inside `_execute_fncall_stmt` (lines 299-310):

```python
def _execute_fncall_stmt(
    node: FnCall,
    env: Environment,
    signals: _SignalAccumulator,
    *,
    brackets: _BracketState,
    gate: pd.Series | bool | None,
) -> None:
    name = node.name

    if name == "strategy.exit":
        kwargs = {kw.name: kw.value for kw in node.kwargs}
        has_stop = "stop" in kwargs
        has_limit = "limit" in kwargs
        # profit/loss (포인트 오프셋) 구문은 본 스프린트에서 미지원 유지
        if "profit" in kwargs or "loss" in kwargs:
            raise PineUnsupportedError(
                "strategy.exit(profit=, loss=) offset-based brackets are deferred",
                feature="strategy.exit(profit/loss)",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )
        if not has_stop and not has_limit:
            raise PineUnsupportedError(
                "strategy.exit requires stop= or limit= argument",
                feature="strategy.exit(no-args)",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )
        if has_stop:
            brackets.stop_series = _ensure_series(
                evaluate_expression(kwargs["stop"], env), signals.entries.index
            )
        if has_limit:
            brackets.limit_series = _ensure_series(
                evaluate_expression(kwargs["limit"], env), signals.entries.index
            )
        return

    if name == "strategy.entry":
        signals.entries = signals.entries | _gate_as_bool_series(gate, signals.entries.index)
        return

    if name == "strategy.close":
        signals.exits = signals.exits | _gate_as_bool_series(gate, signals.exits.index)
        return

    if name in (
        "plot", "plotshape", "bgcolor", "barcolor", "fill",
        "alert", "alertcondition",
        "indicator", "strategy",
    ):
        return

    evaluate_expression(node, env)


def _ensure_series(value: Any, index: pd.Index) -> pd.Series:
    """스칼라 → 동일 값 Series, Series → 그대로."""
    if isinstance(value, pd.Series):
        return value.astype(float)
    return pd.Series(float(value), index=index)
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_bracket.py -v`
Expected: PASS (3 tests)

Also run the full suite to catch regressions:

Run: `cd backend && uv run pytest tests/ -q`
Expected: previous 201 tests still pass + 3 new → 204 passed (Sprint 1 golden may need `None` unchanged — check the next step).

- [ ] **Step 1.5: Verify Sprint 1 golden still green**

The existing golden test (`test_golden_case`) only asserts `entries_indices` / `exits_indices`. The SignalResult fields `direction`/`sl_stop`/`tp_limit` now have non-`None` values for the EMA Cross cases (because entries exist → direction Series). Our interpreter change only populates these when triggers fire; the existing expected.json doesn't assert on them.

Run: `cd backend && uv run pytest tests/strategy/pine/test_golden.py -v`
Expected: PASS (EMA Cross v4, v5)

- [ ] **Step 1.6: Commit**

```bash
cd backend && git add src/strategy/pine/interpreter.py tests/strategy/pine/test_interpreter_bracket.py
git commit -m "feat(strategy/pine): unlock strategy.exit(stop,limit) and fill SignalResult bracket fields

BracketState captures per-bar stop/limit series evaluated at strategy.exit call-time.
_assemble_signal_result builds sl_stop/tp_limit via sample-at-entry + ffill + position mask.
direction populated as 'long' Series when entries exist. strategy.exit(profit=,loss=) and
bare strategy.exit() remain PineUnsupportedError.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Fill `position_size` from `strategy.entry(qty=<literal>)`

**Files:**
- Modify: `backend/src/strategy/pine/interpreter.py` (`_execute_fncall_stmt` strategy.entry branch; `_SignalAccumulator`; `_assemble_signal_result`)
- Test: `backend/tests/strategy/pine/test_interpreter_bracket.py` (add cases)

### Step 2.1: Write failing tests — position_size constant Series when qty literal; None otherwise

- [ ] Add to `backend/tests/strategy/pine/test_interpreter_bracket.py`:

```python
def test_strategy_entry_qty_literal_populates_position_size():
    """strategy.entry(qty=2) 리터럴 → position_size는 2.0 상수 Series."""
    src = """//@version=5
strategy("qty literal")
if bar_index == 1
    strategy.entry("Long", strategy.long, qty=2)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok"
    signal = outcome.result
    assert signal is not None
    assert signal.position_size is not None
    np.testing.assert_allclose(signal.position_size.to_numpy(), [2.0, 2.0, 2.0])


def test_strategy_entry_without_qty_leaves_position_size_none():
    """qty 생략 → position_size None 유지 (vectorbt 기본값 사용 예정)."""
    src = """//@version=5
strategy("no qty")
if bar_index == 1
    strategy.entry("Long", strategy.long)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "ok"
    signal = outcome.result
    assert signal is not None
    assert signal.position_size is None
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_bracket.py::test_strategy_entry_qty_literal_populates_position_size -v`
Expected: FAIL (`position_size is None` currently)

- [ ] **Step 2.3: Implement qty capture in `_execute_fncall_stmt` + `_assemble_signal_result`**

In `backend/src/strategy/pine/interpreter.py`, extend `_SignalAccumulator`:

```python
@dataclass
class _SignalAccumulator:
    """if-문 조건을 시그널로 누적."""

    entries: pd.Series
    exits: pd.Series
    entry_qty_literal: float | None = None  # Task 2: strategy.entry(qty=<literal>) 캡처

    @classmethod
    def zero_like(cls, series: pd.Series) -> _SignalAccumulator:
        false_like = pd.Series(False, index=series.index)
        return cls(entries=false_like.copy(), exits=false_like.copy())
```

In the `strategy.entry` branch of `_execute_fncall_stmt`:

```python
if name == "strategy.entry":
    signals.entries = signals.entries | _gate_as_bool_series(gate, signals.entries.index)
    # qty=<Literal> 만 지원. 표현식/qty_percent/Ident 는 Task 3에서 Unsupported 처리.
    for kw in node.kwargs:
        if kw.name == "qty":
            from src.strategy.pine.ast_nodes import Literal as _Lit
            if isinstance(kw.value, _Lit) and isinstance(kw.value.value, (int, float)):
                signals.entry_qty_literal = float(kw.value.value)
            # 비-리터럴 qty는 Task 3에서 Unsupported 처리
    return
```

In `_assemble_signal_result`, populate `position_size`:

```python
# position_size
if signals.entry_qty_literal is not None:
    position_size: pd.Series | None = pd.Series(
        signals.entry_qty_literal, index=entries.index
    )
else:
    position_size = None

return SignalResult(
    entries=entries,
    exits=exits,
    direction=direction,
    sl_stop=sl_stop,
    tp_limit=tp_limit,
    position_size=position_size,
    metadata={"vars": dict(env.variables)},
)
```

- [ ] **Step 2.4: Run tests**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_bracket.py -v`
Expected: PASS (5 tests total)

Run: `cd backend && uv run pytest tests/ -q`
Expected: all pre-existing tests still pass.

- [ ] **Step 2.5: Commit**

```bash
cd backend && git add src/strategy/pine/interpreter.py tests/strategy/pine/test_interpreter_bracket.py
git commit -m "feat(strategy/pine): fill SignalResult.position_size from strategy.entry(qty=<literal>)

Captures literal qty value on strategy.entry call; emits constant Series across all bars.
Non-literal qty (expression, Ident) currently ignored — Task 3 converts to Unsupported.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Explicit Unsupported for `strategy.short`, pyramiding, `qty_percent=`, non-literal qty

**Files:**
- Modify: `backend/src/strategy/pine/interpreter.py` (`_execute_fncall_stmt`)
- Test: `backend/tests/strategy/pine/test_interpreter_bracket.py` (add cases)

### Step 3.1: Write failing tests

- [ ] Add to `backend/tests/strategy/pine/test_interpreter_bracket.py`:

```python
def test_strategy_short_entry_is_unsupported():
    """strategy.entry(direction=strategy.short)는 Sprint 2에서 Unsupported."""
    src = """//@version=5
strategy("short")
if bar_index == 1
    strategy.entry("Short", strategy.short)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "short" in outcome.error.feature.lower()


def test_strategy_entry_qty_percent_is_unsupported():
    """qty_percent= 는 Sprint 2에서 Unsupported."""
    src = """//@version=5
strategy("qty percent")
if bar_index == 1
    strategy.entry("Long", strategy.long, qty_percent=50)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "qty_percent" in outcome.error.feature


def test_strategy_entry_qty_non_literal_is_unsupported():
    """qty=<expression> (non-literal)은 Sprint 2에서 Unsupported."""
    src = """//@version=5
strategy("qty expr")
sz = 2
if bar_index == 1
    strategy.entry("Long", strategy.long, qty=sz)
"""
    ohlcv = _ohlcv([10.0, 11.0, 12.0])

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert "qty" in outcome.error.feature.lower()
```

- [ ] **Step 3.2: Run tests**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_bracket.py -k "unsupported" -v`
Expected: FAIL (currently short/qty_percent/non-literal qty go through as no-op or partial handling)

- [ ] **Step 3.3: Implement Unsupported guards**

Update the `strategy.entry` branch in `_execute_fncall_stmt`:

```python
if name == "strategy.entry":
    from src.strategy.pine.ast_nodes import Ident as _Ident, Literal as _Lit

    # direction 인자 (2번째 positional): strategy.short 는 Unsupported
    if len(node.args) >= 2:
        dir_arg = node.args[1]
        # 'strategy.short' Ident 또는 "short" 문자열 리터럴
        if isinstance(dir_arg, _Ident) and dir_arg.name == "strategy.short":
            raise PineUnsupportedError(
                "strategy.entry(direction=strategy.short) is deferred to a future sprint",
                feature="strategy.short",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )
        if isinstance(dir_arg, _Lit) and dir_arg.value == "short":
            raise PineUnsupportedError(
                "strategy.entry with short direction is deferred",
                feature="strategy.short",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )

    for kw in node.kwargs:
        if kw.name == "direction":
            # direction=strategy.short 키워드 형식
            v = kw.value
            if (isinstance(v, _Ident) and v.name == "strategy.short") or (
                isinstance(v, _Lit) and v.value == "short"
            ):
                raise PineUnsupportedError(
                    "strategy.entry(direction=strategy.short) is deferred",
                    feature="strategy.short",
                    category="function",
                    line=node.source_span.line,
                    column=node.source_span.column,
                )
        if kw.name == "qty_percent":
            raise PineUnsupportedError(
                "strategy.entry(qty_percent=...) is deferred",
                feature="strategy.entry(qty_percent)",
                category="function",
                line=node.source_span.line,
                column=node.source_span.column,
            )
        if kw.name == "qty":
            if not (isinstance(kw.value, _Lit) and isinstance(kw.value.value, (int, float))):
                raise PineUnsupportedError(
                    "strategy.entry(qty=<non-literal>) is deferred; only literal qty supported",
                    feature="strategy.entry(qty-non-literal)",
                    category="function",
                    line=node.source_span.line,
                    column=node.source_span.column,
                )
            signals.entry_qty_literal = float(kw.value.value)

    signals.entries = signals.entries | _gate_as_bool_series(gate, signals.entries.index)
    return
```

Remove the earlier (Task 2) qty capture block — now centralized in the new loop above.

- [ ] **Step 3.4: Run tests**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_bracket.py -v`
Expected: PASS (8 tests total)

Run: `cd backend && uv run pytest tests/ -q`
Expected: all previous + new tests pass (204 + 3 new = 207 or similar).

- [ ] **Step 3.5: Commit**

```bash
cd backend && git add src/strategy/pine/interpreter.py tests/strategy/pine/test_interpreter_bracket.py
git commit -m "feat(strategy/pine): explicit Unsupported for strategy.short, qty_percent, non-literal qty

Guards enumerate every path (positional direction arg, keyword direction, qty_percent, qty=<expr>).
Error messages include feature label for analytics/coverage reporting.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Add `vectorbt` dependency + smoke test

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/backtest/__init__.py`, `backend/tests/backtest/engine/__init__.py`, `backend/tests/backtest/engine/test_smoke_vectorbt.py`

### Step 4.1: Add dependency

- [ ] Edit `backend/pyproject.toml` — add to `[project] dependencies`:

```toml
dependencies = [
    # ... existing deps ...
    "pandas-ta>=0.3.14b",
    "vectorbt>=0.26,<0.27",   # Sprint 2: 백테스트 엔진
]
```

- [ ] Run: `cd backend && uv sync`
Expected: vectorbt 및 transitive deps (numba, llvmlite 등) 설치. (경고가 있어도 설치 성공이면 계속.)

- [ ] **Step 4.2: Write smoke test**

Create `backend/tests/backtest/__init__.py`:
```python
```
(빈 파일)

Create `backend/tests/backtest/engine/__init__.py`:
```python
```
(빈 파일)

Create `backend/tests/backtest/engine/test_smoke_vectorbt.py`:

```python
"""vectorbt import 및 Portfolio.from_signals 최소 호출 smoke test."""
from __future__ import annotations

import pandas as pd
import pytest


def test_vectorbt_importable():
    import vectorbt as vbt  # noqa: F401


def test_portfolio_from_signals_minimal():
    """가장 단순한 entries/exits로 Portfolio가 생성되고 total_return이 숫자로 나오는지."""
    import vectorbt as vbt

    close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0], name="close")
    entries = pd.Series([False, True, False, False, False])
    exits = pd.Series([False, False, False, True, False])

    pf = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )
    tr = pf.total_return()
    # total_return은 float 또는 Series(단일 컬럼)
    value = float(tr) if not hasattr(tr, "iloc") else float(tr.iloc[0])
    assert value == pytest.approx((11.5 - 11.0) / 11.0, rel=0.05)
```

- [ ] **Step 4.3: Run smoke test**

Run: `cd backend && uv run pytest tests/backtest/engine/test_smoke_vectorbt.py -v`
Expected: PASS (2 tests)

If `total_return()` returns a different shape in the installed vectorbt version, adjust the extraction (the value conversion already handles both scalar and Series).

- [ ] **Step 4.4: Commit**

```bash
cd backend && git add pyproject.toml uv.lock tests/backtest/
git commit -m "feat(backtest): add vectorbt dependency + smoke test

Pins vectorbt>=0.26,<0.27. Smoke test verifies import + minimal Portfolio.from_signals
returning a finite total_return. Foundation for Task 5+ engine build-out.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Define engine types — `BacktestConfig`, `BacktestMetrics`, `BacktestResult`, `BacktestOutcome`

**Files:**
- Create: `backend/src/backtest/engine/__init__.py` (placeholder — filled in Task 8)
- Create: `backend/src/backtest/engine/types.py`
- Create: `backend/tests/backtest/engine/test_types.py`

### Step 5.1: Write failing tests

- [ ] Create `backend/tests/backtest/engine/test_types.py`:

```python
"""backtest.engine.types dataclass 계약 검증."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
)


def test_backtest_config_defaults():
    cfg = BacktestConfig()
    assert cfg.init_cash == Decimal("10000")
    assert cfg.fees == 0.001
    assert cfg.slippage == 0.0005
    assert cfg.freq == "1D"


def test_backtest_config_is_frozen():
    cfg = BacktestConfig()
    with pytest.raises((AttributeError, Exception)):
        cfg.init_cash = Decimal("1")  # type: ignore[misc]


def test_backtest_metrics_fields():
    m = BacktestMetrics(
        total_return=Decimal("0.0842"),
        sharpe_ratio=Decimal("1.23"),
        max_drawdown=Decimal("-0.045"),
        win_rate=Decimal("0.5"),
        num_trades=7,
    )
    assert m.num_trades == 7
    assert m.total_return == Decimal("0.0842")


def test_backtest_result_holds_metrics_and_equity_curve():
    m = BacktestMetrics(
        total_return=Decimal("0"),
        sharpe_ratio=Decimal("0"),
        max_drawdown=Decimal("0"),
        win_rate=Decimal("0"),
        num_trades=0,
    )
    curve = pd.Series([10000.0, 10010.0, 10020.0])
    cfg = BacktestConfig()
    res = BacktestResult(metrics=m, equity_curve=curve, config_used=cfg)
    assert res.metrics is m
    assert res.config_used is cfg
    assert len(res.equity_curve) == 3


def test_backtest_outcome_parse_failed_shape():
    from src.strategy.pine import ParseOutcome

    parse = ParseOutcome(
        status="error",
        source_version="v5",
        result=None,
        error=None,
    )
    out = BacktestOutcome(status="parse_failed", parse=parse, result=None, error="parser blew up")
    assert out.result is None
    assert out.error == "parser blew up"
```

- [ ] **Step 5.2: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_types.py -v`
Expected: FAIL — ImportError (`src.backtest.engine.types` 아직 없음)

- [ ] **Step 5.3: Implement types**

Create `backend/src/backtest/engine/__init__.py`:

```python
"""백테스트 엔진 공개 API (Task 8에서 run_backtest 등 re-export)."""
```

Create `backend/src/backtest/engine/types.py`:

```python
"""백테스트 엔진 타입 정의."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import pandas as pd

from src.strategy.pine import ParseOutcome, PineError


@dataclass(frozen=True)
class BacktestConfig:
    """vectorbt Portfolio.from_signals() 호출 파라미터."""

    init_cash: Decimal = Decimal("10000")
    fees: float = 0.001        # 0.1%
    slippage: float = 0.0005   # 0.05%
    freq: str = "1D"           # pandas offset alias


@dataclass(frozen=True)
class BacktestMetrics:
    """5개 표준 지표. 금융 수치는 Decimal."""

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal      # 음수 (-0.25 = -25%)
    win_rate: Decimal          # 0.0 ~ 1.0
    num_trades: int


@dataclass(frozen=True)
class BacktestResult:
    """백테스트 실행 결과."""

    metrics: BacktestMetrics
    equity_curve: pd.Series
    config_used: BacktestConfig


@dataclass
class BacktestOutcome:
    """run_backtest() 공개 반환 타입. ParseOutcome을 래핑."""

    status: Literal["ok", "unsupported", "error", "parse_failed"]
    parse: ParseOutcome
    result: BacktestResult | None = None
    error: PineError | str | None = None
```

- [ ] **Step 5.4: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_types.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5.5: Commit**

```bash
cd backend && git add src/backtest/engine/__init__.py src/backtest/engine/types.py tests/backtest/engine/test_types.py
git commit -m "feat(backtest/engine): define BacktestConfig/Metrics/Result/Outcome dataclasses

Frozen dataclasses for inputs and metrics; mutable BacktestOutcome wraps ParseOutcome.
Public API (run_backtest) to be added in Task 8.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Implement `adapter.to_portfolio_kwargs`

**Files:**
- Create: `backend/src/backtest/engine/adapter.py`
- Create: `backend/tests/backtest/engine/test_adapter.py`

### Step 6.1: Write failing tests

- [ ] Create `backend/tests/backtest/engine/test_adapter.py`:

```python
"""SignalResult → vectorbt Portfolio.from_signals kwargs 변환기 검증."""
from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine.adapter import to_portfolio_kwargs
from src.backtest.engine.types import BacktestConfig
from src.strategy.pine.types import SignalResult


def _ohlcv(n: int = 5) -> pd.DataFrame:
    close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0][:n])
    return pd.DataFrame(
        {"open": close, "high": close + 0.5, "low": close - 0.5, "close": close, "volume": 100.0}
    )


def _minimal_signal(idx: pd.Index) -> SignalResult:
    return SignalResult(
        entries=pd.Series([False, True, False, False, False], index=idx),
        exits=pd.Series([False, False, False, True, False], index=idx),
    )


def test_adapter_passes_required_kwargs():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert kwargs["close"] is ohlcv["close"]
    pd.testing.assert_series_equal(kwargs["entries"], signal.entries)
    pd.testing.assert_series_equal(kwargs["exits"], signal.exits)
    assert kwargs["init_cash"] == 10000.0
    assert kwargs["fees"] == 0.001
    assert kwargs["slippage"] == 0.0005
    assert kwargs["freq"] == "1D"


def test_adapter_omits_optional_fields_when_none():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    for k in ("sl_stop", "tp_stop", "size"):
        assert k not in kwargs, f"{k} should be omitted when SignalResult field is None"


def test_adapter_passes_sl_stop_as_price():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    signal.sl_stop = pd.Series([float("nan"), 10.0, 10.0, float("nan"), float("nan")], index=ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert "sl_stop" in kwargs
    pd.testing.assert_series_equal(kwargs["sl_stop"], signal.sl_stop)


def test_adapter_converts_tp_limit_price_to_ratio():
    """tp_stop은 비율만 받으므로, 가격 Series를 (target/close - 1)로 변환."""
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    # close = [10, 11, 12, 11.5, 13]; tp_limit at entry=11 → 13.2 (20% 위)
    signal.tp_limit = pd.Series(
        [float("nan"), 13.2, 13.2, float("nan"), float("nan")], index=ohlcv.index
    )
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    tp = kwargs["tp_stop"]
    # close=11, target=13.2 → ratio = (13.2 - 11) / 11 = 0.2
    assert tp.iloc[1] == pytest.approx(0.2, rel=1e-9)
    assert tp.iloc[2] == pytest.approx((13.2 - 12.0) / 12.0, rel=1e-9)
    assert math.isnan(tp.iloc[0])
    assert math.isnan(tp.iloc[3])


def test_adapter_passes_position_size_as_size():
    ohlcv = _ohlcv()
    signal = _minimal_signal(ohlcv.index)
    signal.position_size = pd.Series([2.0] * 5, index=ohlcv.index)
    cfg = BacktestConfig()

    kwargs = to_portfolio_kwargs(signal, ohlcv, cfg)

    assert "size" in kwargs
    pd.testing.assert_series_equal(kwargs["size"], signal.position_size)


def test_adapter_raises_on_index_misalignment():
    ohlcv = _ohlcv()
    signal = SignalResult(
        entries=pd.Series([False, True], index=[99, 100]),  # 다른 인덱스
        exits=pd.Series([False, True], index=[99, 100]),
    )
    cfg = BacktestConfig()

    with pytest.raises(ValueError, match="index"):
        to_portfolio_kwargs(signal, ohlcv, cfg)
```

- [ ] **Step 6.2: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_adapter.py -v`
Expected: FAIL — ImportError (`src.backtest.engine.adapter` 없음)

- [ ] **Step 6.3: Implement adapter**

Create `backend/src/backtest/engine/adapter.py`:

```python
"""SignalResult → vectorbt Portfolio.from_signals() kwargs 변환."""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.backtest.engine.types import BacktestConfig
from src.strategy.pine.types import SignalResult


def to_portfolio_kwargs(
    signal: SignalResult,
    ohlcv: pd.DataFrame,
    config: BacktestConfig,
) -> dict[str, Any]:
    """SignalResult + OHLCV + config → Portfolio.from_signals kwargs."""
    _assert_aligned(signal, ohlcv)

    kwargs: dict[str, Any] = {
        "close": ohlcv["close"],
        "entries": signal.entries,
        "exits": signal.exits,
        "init_cash": float(config.init_cash),
        "fees": config.fees,
        "slippage": config.slippage,
        "freq": config.freq,
    }

    if signal.sl_stop is not None:
        kwargs["sl_stop"] = signal.sl_stop  # 가격 직접

    if signal.tp_limit is not None:
        kwargs["tp_stop"] = _price_to_ratio(signal.tp_limit, ohlcv["close"])

    if signal.position_size is not None:
        kwargs["size"] = signal.position_size

    return kwargs


def _assert_aligned(signal: SignalResult, ohlcv: pd.DataFrame) -> None:
    if not signal.entries.index.equals(ohlcv.index):
        raise ValueError(
            "SignalResult.entries index must align with OHLCV index "
            f"(got {signal.entries.index!r} vs {ohlcv.index!r})"
        )
    if not signal.exits.index.equals(ohlcv.index):
        raise ValueError("SignalResult.exits index must align with OHLCV index")


def _price_to_ratio(target_price: pd.Series, close: pd.Series) -> pd.Series:
    """tp_stop은 비율. target_price가 NaN이면 NaN 유지."""
    return (target_price - close) / close
```

- [ ] **Step 6.4: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_adapter.py -v`
Expected: PASS (6 tests)

- [ ] **Step 6.5: Commit**

```bash
cd backend && git add src/backtest/engine/adapter.py tests/backtest/engine/test_adapter.py
git commit -m "feat(backtest/engine): SignalResult → Portfolio.from_signals kwargs adapter

Required kwargs always included. Optional fields (sl_stop/tp_stop/size) omitted when None.
tp_limit price Series converted to ratio (vectorbt tp_stop expects ratio).
Explicit ValueError on index misalignment.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Implement `metrics.extract_metrics`

**Files:**
- Create: `backend/src/backtest/engine/metrics.py`
- Create: `backend/tests/backtest/engine/test_metrics.py`

### Step 7.1: Write failing tests

- [ ] Create `backend/tests/backtest/engine/test_metrics.py`:

```python
"""Portfolio → BacktestMetrics 추출기 검증."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest
import vectorbt as vbt

from src.backtest.engine.metrics import extract_metrics
from src.backtest.engine.types import BacktestMetrics


def _run_vbt(entries, exits, close=None):
    if close is None:
        close = pd.Series([10.0, 11.0, 12.0, 11.5, 13.0, 12.5])
    return vbt.Portfolio.from_signals(
        close=close,
        entries=pd.Series(entries),
        exits=pd.Series(exits),
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )


def test_extract_metrics_returns_all_five_fields():
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert isinstance(m, BacktestMetrics)
    assert isinstance(m.total_return, Decimal)
    assert isinstance(m.sharpe_ratio, Decimal)
    assert isinstance(m.max_drawdown, Decimal)
    assert isinstance(m.win_rate, Decimal)
    assert isinstance(m.num_trades, int)


def test_extract_metrics_zero_trades_gives_zero_win_rate():
    pf = _run_vbt(
        entries=[False, False, False, False, False, False],
        exits=[False, False, False, False, False, False],
    )
    m = extract_metrics(pf)
    assert m.num_trades == 0
    assert m.win_rate == Decimal("0")


def test_extract_metrics_num_trades_is_integer():
    pf = _run_vbt(
        entries=[False, True, False, False, False, False],
        exits=[False, False, False, True, False, False],
    )
    m = extract_metrics(pf)
    assert m.num_trades == 1
```

- [ ] **Step 7.2: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_metrics.py -v`
Expected: FAIL — ImportError

- [ ] **Step 7.3: Implement metrics**

Create `backend/src/backtest/engine/metrics.py`:

```python
"""vectorbt Portfolio → BacktestMetrics 추출."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.backtest.engine.types import BacktestMetrics


def extract_metrics(pf: Any) -> BacktestMetrics:
    """vectorbt.Portfolio 인스턴스에서 5개 지표 추출."""
    trades = pf.trades
    num_trades = int(trades.count())

    total_return = _as_decimal(pf.total_return())
    sharpe_ratio = _as_decimal(pf.sharpe_ratio())
    max_drawdown = _as_decimal(pf.max_drawdown())
    win_rate = _as_decimal(trades.win_rate()) if num_trades > 0 else Decimal("0")

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
    )


def _as_decimal(value: Any) -> Decimal:
    """vectorbt 지표 반환(스칼라 또는 단일 원소 Series) → Decimal. NaN은 Decimal('NaN')."""
    if hasattr(value, "iloc"):  # Series
        value = value.iloc[0] if len(value) > 0 else float("nan")
    return Decimal(str(float(value)))
```

- [ ] **Step 7.4: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_metrics.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7.5: Commit**

```bash
cd backend && git add src/backtest/engine/metrics.py tests/backtest/engine/test_metrics.py
git commit -m "feat(backtest/engine): extract_metrics returns 5-metric BacktestMetrics

Coerces vectorbt scalar/Series outputs to Decimal (str-constructed to avoid binary-float drift).
Zero-trade portfolios short-circuit to win_rate=0. NaN tolerated via Decimal('NaN').

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Public API `run_backtest()` in `backtest/engine/__init__.py`

**Files:**
- Modify: `backend/src/backtest/engine/__init__.py`
- Create: `backend/tests/backtest/engine/test_run_backtest.py`

### Step 8.1: Write failing tests

- [ ] Create `backend/tests/backtest/engine/test_run_backtest.py`:

```python
"""공개 API run_backtest() 통합 검증."""
from __future__ import annotations

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import BacktestConfig, BacktestOutcome, run_backtest


def _ohlcv(n: int = 30) -> pd.DataFrame:
    seg1 = np.linspace(10.0, 20.0, 10)
    seg2 = np.full(5, 20.0)
    seg3 = np.linspace(20.0, 12.0, 10)
    seg4 = np.linspace(12.0, 18.0, 5)
    close = np.concatenate([seg1, seg2, seg3, seg4])[:n]
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": [100.0] * n,
        }
    )


def test_run_backtest_ok_path_produces_metrics():
    src = """//@version=5
strategy("EMA Cross")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
    ohlcv = _ohlcv()

    out = run_backtest(src, ohlcv)

    assert isinstance(out, BacktestOutcome)
    assert out.status == "ok"
    assert out.result is not None
    assert out.result.metrics.num_trades >= 0
    assert isinstance(out.result.metrics.total_return, Decimal)
    assert out.parse.status == "ok"


def test_run_backtest_parse_failed_returns_parse_failed_status():
    # 미지원: 빈 strategy.exit (Task 1에서 Unsupported 처리)
    src = """//@version=5
strategy("bad")
if bar_index == 1
    strategy.entry("Long", strategy.long)
strategy.exit("Exit")
"""
    ohlcv = _ohlcv()

    out = run_backtest(src, ohlcv)

    assert out.status == "parse_failed"
    assert out.result is None
    assert out.parse.status == "unsupported"


def test_run_backtest_accepts_custom_config():
    src = """//@version=5
strategy("EMA Cross")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
"""
    ohlcv = _ohlcv()
    cfg = BacktestConfig(init_cash=Decimal("5000"), fees=0.002)

    out = run_backtest(src, ohlcv, cfg)

    assert out.status == "ok"
    assert out.result is not None
    assert out.result.config_used.init_cash == Decimal("5000")
    assert out.result.config_used.fees == 0.002


def test_run_backtest_returns_error_status_on_adapter_failure():
    # 인덱스 미정렬은 adapter에서 ValueError → status="error"
    src = """//@version=5
strategy("EMA")
if bar_index == 1
    strategy.entry("Long", strategy.long)
"""
    ohlcv = _ohlcv()
    ohlcv.index = pd.RangeIndex(start=100, stop=100 + len(ohlcv))  # SignalResult와 인덱스 불일치 유발

    out = run_backtest(src, ohlcv)

    # 현재 parse_and_run은 ohlcv["close"]의 index를 그대로 사용하므로 실제로 정렬됨.
    # 따라서 이 케이스는 실제로는 ok가 나올 수 있음. 대신, adapter 직접 테스트로 error path를
    # 검증하는 것이 더 안정적 — 아래 유닛 테스트로 대체 가능.
    # 여기선 status가 'ok' 또는 'error' 중 하나임을 허용.
    assert out.status in ("ok", "error")
```

Note on the last test: `parse_and_run` builds signals with the OHLCV-derived index, so misalignment is effectively prevented. This test is weakened to a sanity check; explicit adapter failure is already covered in Task 6.

- [ ] **Step 8.2: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/test_run_backtest.py -v`
Expected: FAIL — `run_backtest` not yet exported.

- [ ] **Step 8.3: Implement public API**

Replace `backend/src/backtest/engine/__init__.py`:

```python
"""백테스트 엔진 공개 API."""
from __future__ import annotations

import logging

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.adapter import to_portfolio_kwargs
from src.backtest.engine.metrics import extract_metrics
from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
)
from src.strategy.pine import parse_and_run

logger = logging.getLogger(__name__)


def run_backtest(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestOutcome:
    """Pine source + OHLCV → BacktestOutcome.

    파서가 ok로 반환하면 vectorbt로 백테스트를 실행하고 지표를 추출한다.
    파서가 ok 외 상태를 반환하면 status='parse_failed'로 즉시 반환한다.
    """
    cfg = config if config is not None else BacktestConfig()
    parse = parse_and_run(source, ohlcv)

    if parse.status != "ok" or parse.result is None:
        return BacktestOutcome(
            status="parse_failed",
            parse=parse,
            result=None,
            error=parse.error,
        )

    try:
        kwargs = to_portfolio_kwargs(parse.result, ohlcv, cfg)
        pf = vbt.Portfolio.from_signals(**kwargs)
        metrics = extract_metrics(pf)
        equity_curve = _as_series(pf.value())
    except Exception as exc:  # noqa: BLE001
        logger.exception("backtest_engine_error")
        return BacktestOutcome(
            status="error",
            parse=parse,
            result=None,
            error=str(exc),
        )

    result = BacktestResult(metrics=metrics, equity_curve=equity_curve, config_used=cfg)
    logger.info(
        "backtest_ok",
        extra={"num_trades": metrics.num_trades, "total_return": str(metrics.total_return)},
    )
    return BacktestOutcome(status="ok", parse=parse, result=result, error=None)


def _as_series(value: object) -> pd.Series:
    """pf.value() 반환이 Series/DataFrame 어느 쪽이든 1-D Series로 정규화."""
    if isinstance(value, pd.DataFrame):
        return value.iloc[:, 0]
    if isinstance(value, pd.Series):
        return value
    return pd.Series([value])


__all__ = [
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestResult",
    "run_backtest",
]
```

- [ ] **Step 8.4: Run tests**

Run: `cd backend && uv run pytest tests/backtest/engine/ -v`
Expected: PASS (all Task 4-8 tests)

Run: `cd backend && uv run pytest tests/ -q`
Expected: full suite green (new tests added, no regressions).

- [ ] **Step 8.5: Commit**

```bash
cd backend && git add src/backtest/engine/__init__.py tests/backtest/engine/test_run_backtest.py
git commit -m "feat(backtest/engine): public run_backtest() wiring parser → vectorbt → metrics

Thin orchestrator: delegates to parse_and_run, adapter, Portfolio.from_signals, extract_metrics.
parse_failed short-circuits before touching vectorbt. Unexpected adapter/engine exceptions
logged with stack trace and surfaced as status='error' with string message.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Extend EMA Cross v4/v5 golden — snapshot 5 metrics

**Files:**
- Modify: `backend/tests/strategy/pine/test_golden.py` (extend runner to assert `backtest` when present)
- Modify: `backend/tests/strategy/pine/golden/ema_cross_v4/expected.json`
- Modify: `backend/tests/strategy/pine/golden/ema_cross_v5/expected.json`

### Step 9.1: Extend runner to handle optional `backtest` section

- [ ] Edit `backend/tests/strategy/pine/test_golden.py` — replace `test_golden_case` with:

```python
@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_golden_case(case_dir: Path) -> None:
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = _load_ohlcv(case_dir)

    outcome = parse_and_run(src, ohlcv)

    assert outcome.status == expected["status"], (
        f"status mismatch: got {outcome.status!r}, expected {expected['status']!r}; "
        f"error={outcome.error}"
    )
    assert outcome.source_version == expected.get("source_version", "v5")

    if expected["status"] == "ok":
        assert outcome.result is not None
        expected_entries = expected.get("entries_indices", [])
        expected_exits = expected.get("exits_indices", [])
        actual_entries = [int(i) for i, v in enumerate(outcome.result.entries) if bool(v)]
        actual_exits = [int(i) for i, v in enumerate(outcome.result.exits) if bool(v)]
        assert actual_entries == expected_entries, (
            f"entries mismatch:\n  expected: {expected_entries}\n  actual:   {actual_entries}"
        )
        assert actual_exits == expected_exits, (
            f"exits mismatch:\n  expected: {expected_exits}\n  actual:   {actual_exits}"
        )

        # Sprint 2: optional backtest snapshot
        if "backtest" in expected:
            from src.backtest.engine import run_backtest

            bt_out = run_backtest(src, ohlcv)
            assert bt_out.status == "ok", f"backtest status={bt_out.status}, error={bt_out.error}"
            assert bt_out.result is not None
            expected_metrics = expected["backtest"]["metrics"]
            actual = bt_out.result.metrics
            # num_trades는 정확히 일치
            assert actual.num_trades == expected_metrics["num_trades"]
            # 나머지는 문자열 Decimal 비교 (snapshot 고정)
            for field in ("total_return", "sharpe_ratio", "max_drawdown", "win_rate"):
                assert str(actual.__dict__[field]) == expected_metrics[field], (
                    f"{field}: expected {expected_metrics[field]}, got {actual.__dict__[field]}"
                )
    elif expected["status"] == "unsupported":
        assert outcome.error is not None
        assert isinstance(outcome.error, PineUnsupportedError)
        if "feature" in expected:
            assert outcome.error.feature == expected["feature"]
```

- [ ] **Step 9.2: Run test on an un-extended fixture (should still pass)**

Run: `cd backend && uv run pytest tests/strategy/pine/test_golden.py -v`
Expected: PASS (EMA Cross v4/v5 — no `backtest` key yet, so snapshot branch skipped)

- [ ] **Step 9.3: Record actual snapshot values**

Run the following to capture the real numbers:

```bash
cd backend && uv run python -c "
import json
import numpy as np
import pandas as pd
from src.backtest.engine import run_backtest

close = np.concatenate([
    np.linspace(10.0, 20.0, 10),
    np.full(5, 20.0),
    np.linspace(20.0, 12.0, 10),
    np.linspace(12.0, 18.0, 5),
])[:30]
ohlcv = pd.DataFrame({
    'open': close - 0.1,
    'high': close + 0.5,
    'low': close - 0.5,
    'close': close,
    'volume': [100.0] * 30,
})

for ver, path in [('v5', 'tests/strategy/pine/golden/ema_cross_v5/strategy.pine'),
                  ('v4', 'tests/strategy/pine/golden/ema_cross_v4/strategy.pine')]:
    src = open(path).read()
    out = run_backtest(src, ohlcv)
    m = out.result.metrics
    print(ver, {
        'total_return': str(m.total_return),
        'sharpe_ratio': str(m.sharpe_ratio),
        'max_drawdown': str(m.max_drawdown),
        'win_rate': str(m.win_rate),
        'num_trades': m.num_trades,
    })
"
```

Record the printed values. Use them for the `expected.json` updates below.

- [ ] **Step 9.4: Write the recorded snapshots into `expected.json`**

Update `backend/tests/strategy/pine/golden/ema_cross_v5/expected.json`:

```json
{
  "status": "ok",
  "source_version": "v5",
  "entries_indices": [1, 28],
  "exits_indices": [17],
  "description": "EMA(3)/EMA(8) crossover — ground zero v5 case",
  "backtest": {
    "metrics": {
      "total_return": "<FROM_STEP_9.3>",
      "sharpe_ratio": "<FROM_STEP_9.3>",
      "max_drawdown": "<FROM_STEP_9.3>",
      "win_rate": "<FROM_STEP_9.3>",
      "num_trades": <FROM_STEP_9.3>
    }
  }
}
```

Replace each `<FROM_STEP_9.3>` with the literal string/number printed in Step 9.3. Repeat for `ema_cross_v4/expected.json` (same values expected; v4→v5 normalization should yield identical signals).

- [ ] **Step 9.5: Run golden to verify snapshot**

Run: `cd backend && uv run pytest tests/strategy/pine/test_golden.py -v`
Expected: PASS (both cases — signal + backtest snapshot match)

- [ ] **Step 9.6: Commit**

```bash
cd backend && git add tests/strategy/pine/test_golden.py tests/strategy/pine/golden/ema_cross_v4/expected.json tests/strategy/pine/golden/ema_cross_v5/expected.json
git commit -m "test(strategy/pine): extend ground zero golden with backtest metrics snapshot

Runner reads optional 'backtest' key and asserts 5 metrics via str(Decimal) equality.
v4 snapshot mirrors v5 (normalization path). Values recorded from vectorbt's output on
fixed synthetic OHLCV — purpose is regression defense, not TV parity.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Synthetic bracket golden — `ema_cross_atr_sltp_v5`

**Files:**
- Create: `backend/tests/backtest/engine/golden/__init__.py`
- Create: `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/strategy.pine`
- Create: `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv`
- Create: `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/expected.json`
- Create: `backend/tests/backtest/engine/test_golden_backtest.py`

### Step 10.1: Create `.pine` fixture using EMA cross + ATR-based SL/TP

- [ ] Create `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/strategy.pine`:

```
//@version=5
strategy("EMA Cross ATR SLTP")
fast = ta.ema(close, 3)
slow = ta.ema(close, 8)
atr = ta.atr(14)
if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
strategy.exit("Exit", stop=close - 2 * atr, limit=close + 3 * atr)
```

- [ ] **Step 10.2: Generate 200-bar fixture OHLCV CSV**

Create `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv` — 200 rows of reproducible synthetic OHLCV. Use this one-liner to generate:

```bash
cd backend && uv run python -c "
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
close = 100 + np.cumsum(rng.normal(0, 1, 200))
ohlcv = pd.DataFrame({
    'open': close - 0.1,
    'high': close + 0.5,
    'low': close - 0.5,
    'close': close,
    'volume': [100.0] * 200,
})
ohlcv.to_csv('tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv', index=False)
"
```

- [ ] **Step 10.3: Record expected snapshot**

Run:

```bash
cd backend && uv run python -c "
import json
import pandas as pd
from src.backtest.engine import run_backtest

ohlcv = pd.read_csv('tests/backtest/engine/golden/ema_cross_atr_sltp_v5/ohlcv.csv')
src = open('tests/backtest/engine/golden/ema_cross_atr_sltp_v5/strategy.pine').read()
out = run_backtest(src, ohlcv)
print('status:', out.status)
if out.status != 'ok':
    print('error:', out.error)
    raise SystemExit(1)
parse = out.parse
entries_idx = [i for i, v in enumerate(parse.result.entries) if bool(v)]
exits_idx = [i for i, v in enumerate(parse.result.exits) if bool(v)]
m = out.result.metrics
print(json.dumps({
    'status': 'ok',
    'source_version': 'v5',
    'entries_indices': entries_idx,
    'exits_indices': exits_idx,
    'description': 'EMA cross with ATR-based stop and limit bracket order',
    'backtest': {
        'metrics': {
            'total_return': str(m.total_return),
            'sharpe_ratio': str(m.sharpe_ratio),
            'max_drawdown': str(m.max_drawdown),
            'win_rate': str(m.win_rate),
            'num_trades': m.num_trades,
        }
    }
}, indent=2))
"
```

- [ ] **Step 10.4: Write recorded values into `expected.json`**

Paste the printed JSON into `backend/tests/backtest/engine/golden/ema_cross_atr_sltp_v5/expected.json` verbatim.

- [ ] **Step 10.5: Write golden runner**

Create `backend/tests/backtest/engine/golden/__init__.py`:
```python
```
(빈 파일)

Create `backend/tests/backtest/engine/test_golden_backtest.py`:

```python
"""백테스트 엔진 골든 러너 — .pine + ohlcv.csv + expected.json 스냅샷 비교."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.engine import run_backtest

GOLDEN_DIR = Path(__file__).parent / "golden"


def _discover_cases() -> list[Path]:
    if not GOLDEN_DIR.exists():
        return []
    return [
        p
        for p in sorted(GOLDEN_DIR.iterdir())
        if p.is_dir() and (p / "strategy.pine").exists() and (p / "expected.json").exists()
    ]


@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_backtest_golden_case(case_dir: Path) -> None:
    src = (case_dir / "strategy.pine").read_text()
    expected = json.loads((case_dir / "expected.json").read_text())
    ohlcv = pd.read_csv(case_dir / "ohlcv.csv")

    out = run_backtest(src, ohlcv)

    assert out.status == expected["status"], f"status={out.status}, error={out.error}"

    if expected["status"] != "ok":
        return

    assert out.result is not None

    actual_entries = [int(i) for i, v in enumerate(out.parse.result.entries) if bool(v)]
    actual_exits = [int(i) for i, v in enumerate(out.parse.result.exits) if bool(v)]
    assert actual_entries == expected["entries_indices"]
    assert actual_exits == expected["exits_indices"]

    exp_metrics = expected["backtest"]["metrics"]
    actual = out.result.metrics
    assert actual.num_trades == exp_metrics["num_trades"]
    for field in ("total_return", "sharpe_ratio", "max_drawdown", "win_rate"):
        assert str(actual.__dict__[field]) == exp_metrics[field], (
            f"{field}: expected {exp_metrics[field]!r}, got {actual.__dict__[field]!r}"
        )
```

- [ ] **Step 10.6: Run golden**

Run: `cd backend && uv run pytest tests/backtest/engine/test_golden_backtest.py -v`
Expected: PASS (1 case `ema_cross_atr_sltp_v5`)

- [ ] **Step 10.7: Full regression check**

Run: `cd backend && uv run pytest tests/ -q`
Expected: all tests green.

- [ ] **Step 10.8: Commit**

```bash
cd backend && git add tests/backtest/engine/golden tests/backtest/engine/test_golden_backtest.py
git commit -m "test(backtest/engine): add ATR-based SL/TP bracket golden case

Exercises strategy.exit(stop=, limit=) end-to-end through run_backtest. Fixture OHLCV
generated from seeded numpy RNG for reproducibility. Expected values recorded from
current vectorbt output as regression snapshot.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 11 (optional): Extend `pine_coverage_report.py` with backtest snapshot mode

**Files:**
- Modify: `backend/scripts/pine_coverage_report.py`
- Test: `backend/tests/strategy/pine/test_coverage_script.py` (extend)

This task is **optional** — skip if Task 10 closes the Go/No-Go criteria. Include if you want the Go/No-Go script to print backtest summary alongside parse coverage.

### Step 11.1: Add `--with-backtest` flag

- [ ] Inspect current `backend/scripts/pine_coverage_report.py` (read file) to locate the main entrypoint.

- [ ] Add a `--with-backtest` CLI flag that, when passed, runs `run_backtest` in addition to `parse_and_run` and prints a one-line summary per case (`status | num_trades | total_return`). Do not change exit-code behavior.

- [ ] Add a test case in `test_coverage_script.py` that invokes the script with `--with-backtest` against the existing golden cases and asserts the stdout contains `num_trades=`.

- [ ] Commit:

```bash
cd backend && git add scripts/pine_coverage_report.py tests/strategy/pine/test_coverage_script.py
git commit -m "feat(strategy/pine): optional --with-backtest flag on coverage report

Adds summary line per case combining parse status and backtest metrics. Exit-code logic
unchanged; this is a diagnostic aid only.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Go/No-Go Verification

Run the full suite once more at the end:

```bash
cd backend && uv run pytest tests/ -v
```

Expected:
- Sprint 1's 201 tests still green.
- New Sprint 2 tests green:
  - `test_interpreter_bracket.py` (~8 tests)
  - `test_smoke_vectorbt.py` (2 tests)
  - `test_types.py` (5 tests)
  - `test_adapter.py` (6 tests)
  - `test_metrics.py` (3 tests)
  - `test_run_backtest.py` (4 tests)
  - `test_golden_backtest.py` (1 parametrized case)
  - `test_golden.py` (2 existing cases, now with backtest assertion)

**Sprint complete when:**
1. Ground zero EMA Cross v4/v5 golden passes with `backtest` snapshot (Task 9).
2. Synthetic bracket golden (`ema_cross_atr_sltp_v5`) passes (Task 10).

---

## Risks & Mitigations (from spec §7)

| Risk | Mitigation in this plan |
|------|-------------------------|
| vectorbt API differences (tp_stop ratio vs price) | Task 4 smoke test hits real API first. Task 6 encodes the ratio conversion with a dedicated unit test. |
| BracketState carry-forward complexity | Task 1 begins with explicit semantic tests (entry bar, carry, NaN at flat). |
| SignalResult field-nonoptional change breaks Sprint 1 golden | `direction` populated only when `entries.any()`; Sprint 1 golden only asserts `entries_indices`/`exits_indices` — Task 9 explicitly re-runs Sprint 1 golden. |
| `Decimal("NaN")` JSON serialization | Snapshot comparison uses `str(Decimal)` — NaN becomes literal string `"NaN"`, portable across JSON round-trips. |
| Parser kwarg support gap | Existing parser already emits `node.kwargs` as list-of-KV (proven by Sprint 1 strategy.exit Unsupported branch accessing `kw.name`). No parser change required. |
| CI slowdown from vectorbt install | Single install cached via uv lockfile. Test suite target < 5s end-to-end. |

---

## Out of Scope (tracked for future sprints)

- Celery task wrapper around `run_backtest`
- `/backtests` REST endpoint, Strategy domain CRUD
- `strategy.short`, pyramiding, `qty_percent=`, non-literal `qty=`
- Pine `strategy(initial_capital=...)` declaration-param auto-injection
- TradingView original-number comparison (separate "engine validation" sprint)
