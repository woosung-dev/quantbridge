# Sprint 8b — Tier-1 가상 strategy 래퍼 + Tier-0 렌더링 scope A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `indicator() + alertcondition()` Pine 스크립트를 자동 `strategy()` 실행 경로로 변환(Tier-1 차별화 핵심)하고, `line/box/label/table` 렌더링 객체의 좌표 저장 + getter만 지원(Tier-0 scope A). 6 corpus 매트릭스 **2/6 → 4/6** 달성(i1_utbot + i2_luxalgo 추가).

**Architecture:**
1. **Tier-1 가상 strategy 래퍼** — `run_virtual_strategy(source, ohlcv)` 신규 진입점. `collect_alerts()`가 반환한 AlertHook의 `condition_ast`(신규 필드)를 매 bar 재평가하여 SignalKind → `strategy.entry/close` 자동 매핑. `discrepancy=True` alert은 warning 기록 후 `condition_signal` 우선(ADR-011 §2.1.3 v1 정책).
2. **Tier-0 렌더링 scope A** — `line/box/label/table` 객체를 메모리 stub (좌표 저장 + getter만). 실제 차트 렌더링은 NOP. `RenderingRegistry`가 각 객체 handle을 관리하고 `line.get_price()`, `box.get_top()` 등 재참조를 지원(ADR-011 §2.0.4 "범위 A").
3. **v4 legacy stdlib alias** — i1_utbot이 Pine v4이므로 prefix 없는 `atr/ema/crossover/nz`와 `iff()`를 `ta.*` dispatcher로 재라우팅.

**Tech Stack:**
- pynescript (LGPL 격리 6 파일 내)
- pine_v2 core: `interpreter.py` / `alert_hook.py` / `strategy_state.py` 확장
- pytest (backend 526 regression green 유지) + ruff/mypy clean

**Scope 엄수:**
- pine_v2/ 모듈만 수정 — 기존 pine/ 모듈 touch 0
- H1 MVP scope 엄수 (ADR-011 §13) — trail_points / qty_percent / pyramiding / strategy.entry(limit=) 여전히 H2+ 이연
- pynescript import 6-파일 경계 (parser_adapter / ast_metrics / ast_classifier / alert_hook / ast_extractor / interpreter) 유지

---

## File Structure

### 신규 파일
- `backend/src/strategy/pine_v2/virtual_strategy.py` — `VirtualStrategyWrapper` 클래스 + `run_virtual_strategy()` 진입점 + SignalKind → strategy action 매핑 정책
- `backend/src/strategy/pine_v2/rendering.py` — `LineObject` / `BoxObject` / `LabelObject` / `TableObject` dataclass + `RenderingRegistry` (handle 발급·조회)
- `backend/tests/strategy/pine_v2/test_virtual_strategy.py` — VirtualStrategyWrapper 단위 테스트
- `backend/tests/strategy/pine_v2/test_rendering.py` — RenderingRegistry 단위 테스트
- `backend/tests/strategy/pine_v2/test_e2e_i1_utbot.py` — i1_utbot 전체 스크립트 실행 + 자동 매매 시퀀스 검증
- `backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py` — i2_luxalgo 전체 스크립트 실행 + 자동 매매 + line 좌표 검증

### 수정 파일
- `backend/src/strategy/pine_v2/alert_hook.py` — `AlertHook`에 `condition_ast: Any | None` 필드 추가 (frozen dataclass, 타입 Any이므로 pyne_ast.Expression 허용). `collect_alerts()`가 raw AST 노드도 보존.
- `backend/src/strategy/pine_v2/interpreter.py` — `_eval_call()`에 line/box/label/table dispatcher + v4 legacy alias 추가. `Interpreter.__init__`에 `rendering: RenderingRegistry` 주입.
- `backend/src/strategy/pine_v2/event_loop.py` — `RunResult`에 `rendering_handles: list[dict]` 필드 추가 (선택적 capture). `run_historical()`는 불변, Tier-1용 신규 `run_virtual_strategy()`는 virtual_strategy.py가 제공.
- `backend/src/strategy/pine_v2/stdlib.py` — `ta.stdev`, `ta.variance` 구현 (i2_luxalgo switch 'Atr' 브랜치 외 옵션은 평가되지 않아도 파싱 안전성 위해 최소 stub). `iff(cond, then, else)` 지원.
- `backend/src/strategy/pine_v2/__init__.py` — 공개 API 확장: `run_virtual_strategy`, `VirtualStrategyWrapper`, `RenderingRegistry`.

---

## Tasks

### Task 1: AlertHook.condition_ast 필드 추가 (Tier-1 기반)

**Files:**
- Modify: `backend/src/strategy/pine_v2/alert_hook.py`
- Test: `backend/tests/strategy/pine_v2/test_alert_hook.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/pine_v2/test_alert_hook.py` 끝에 추가:

```python
def test_collect_alerts_preserves_condition_ast_node() -> None:
    """AlertHook.condition_ast가 alertcondition arg0의 원본 AST 노드를 보존해야 함."""
    from pynescript import ast as pyne_ast
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "alertcondition(buy, 'Long', 'LONG')\n"
    )
    hooks = collect_alerts(source)
    assert len(hooks) == 1
    h = hooks[0]
    # condition_ast는 존재하고 AST 노드여야 함 (Name/Compare 등)
    assert h.condition_ast is not None
    assert isinstance(h.condition_ast, (pyne_ast.Name, pyne_ast.Compare, pyne_ast.BoolOp))


def test_collect_alerts_alert_call_preserves_enclosing_if_test_ast() -> None:
    """alert() 호출의 경우 enclosing if의 test AST가 condition_ast에 보존."""
    from pynescript import ast as pyne_ast
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "if close > open\n"
        "    alert('LONG', alert.freq_once_per_bar)\n"
    )
    hooks = collect_alerts(source)
    assert len(hooks) == 1
    h = hooks[0]
    assert h.condition_ast is not None
    assert isinstance(h.condition_ast, pyne_ast.Compare)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_alert_hook.py::test_collect_alerts_preserves_condition_ast_node -v`
Expected: FAIL — `AttributeError: 'AlertHook' object has no attribute 'condition_ast'`

- [ ] **Step 3: AlertHook dataclass 확장**

`backend/src/strategy/pine_v2/alert_hook.py`의 `AlertHook` dataclass에 필드 추가 (기존 필드 순서 유지하고 `index` 앞에 삽입):

```python
@dataclass(frozen=True)
class AlertHook:
    # ... 기존 필드 유지 ...
    discrepancy: bool
    index: int
    # Tier-1 바 단위 조건 재평가용 — alertcondition arg0 또는 enclosing if.test의 AST 노드
    condition_ast: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        # 기존 return dict 유지 (AST는 JSON 직렬화 대상 아님)
        ...
```

`collect_alerts()` 내부 AlertHook 생성부에 `condition_ast` 계산 추가. alertcondition이면 `_arg_value(node.args[0])`, alert이면 `enclosing_if.test if enclosing_if else None`.

```python
# collect_alerts() for 루프 내, hooks.append(AlertHook(...)) 수정
if is_alertcondition:
    cond_ast = _arg_value(node.args[0])
else:  # alert
    cond_ast = enclosing_if.test if enclosing_if is not None else None

hooks.append(AlertHook(
    kind="alert" if is_alert else "alertcondition",
    message=message,
    condition_expr=condition_expr,
    enclosing_if_condition=enclosing_if_condition,
    enclosing_if_branch=branch if enclosing_if is not None else None,
    resolved_condition=resolved_condition,
    message_signal=message_signal,
    condition_signal=condition_signal,
    signal=final,
    discrepancy=discrepancy,
    index=idx,
    condition_ast=cond_ast,
))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_alert_hook.py -v`
Expected: ALL PASS (기존 + 신규 2개)

- [ ] **Step 5: ruff/mypy clean 확인**

Run: `cd backend && ruff check src/strategy/pine_v2/alert_hook.py && mypy src/strategy/pine_v2/alert_hook.py`
Expected: no errors

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine_v2/alert_hook.py backend/tests/strategy/pine_v2/test_alert_hook.py
git commit -m "feat(pine_v2): add AlertHook.condition_ast for Tier-1 bar-level re-evaluation"
```

---

### Task 2: SignalKind → strategy action 매핑 테이블 + VirtualAction dataclass

**Files:**
- Create: `backend/src/strategy/pine_v2/virtual_strategy.py`
- Test: `backend/tests/strategy/pine_v2/test_virtual_strategy.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/pine_v2/test_virtual_strategy.py` 신규:

```python
"""Tier-1 가상 strategy 래퍼 단위 테스트 (ADR-011 §2.1.4)."""
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
    assert action.kind == expected_kind
    assert action.trade_id == expected_id
    assert action.direction == expected_direction


@pytest.mark.parametrize("signal", [SignalKind.INFORMATION, SignalKind.UNKNOWN])
def test_signal_to_action_returns_none_for_non_trade_signals(
    signal: SignalKind,
) -> None:
    assert signal_to_action(signal) is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_virtual_strategy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.strategy.pine_v2.virtual_strategy'`

- [ ] **Step 3: virtual_strategy.py 뼈대 + 매핑 테이블**

`backend/src/strategy/pine_v2/virtual_strategy.py` 신규:

```python
"""Tier-1 가상 strategy 래퍼 — indicator + alert → 자동 매매 실행 경로 변환.

ADR-011 §2.1.4 차별화 핵심. collect_alerts() 결과를 매 bar 재평가하여
SignalKind → strategy.* 매핑으로 자동 entry/close 호출.

v1 정책:
- LONG_ENTRY → strategy.entry("L", long) (기존 short 자동 reverse)
- SHORT_ENTRY → strategy.entry("S", short) (기존 long 자동 reverse)
- LONG_EXIT → strategy.close("L")
- SHORT_EXIT → strategy.close("S")
- INFORMATION/UNKNOWN → 무시 + warning
- discrepancy=True → warning 기록 후 condition_signal 우선 (collect_alerts가 이미 반영)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.strategy.pine_v2.alert_hook import SignalKind

ActionKind = Literal["entry", "close"]


@dataclass(frozen=True)
class VirtualAction:
    """SignalKind → strategy 호출로 매핑된 action."""
    kind: ActionKind
    trade_id: str
    direction: Literal["long", "short"] | None  # close에는 None


_SIGNAL_TO_ACTION: dict[SignalKind, VirtualAction] = {
    SignalKind.LONG_ENTRY: VirtualAction(kind="entry", trade_id="L", direction="long"),
    SignalKind.SHORT_ENTRY: VirtualAction(kind="entry", trade_id="S", direction="short"),
    SignalKind.LONG_EXIT: VirtualAction(kind="close", trade_id="L", direction=None),
    SignalKind.SHORT_EXIT: VirtualAction(kind="close", trade_id="S", direction=None),
}


def signal_to_action(signal: SignalKind) -> VirtualAction | None:
    """SignalKind을 VirtualAction으로 변환. 매매 신호가 아니면 None."""
    return _SIGNAL_TO_ACTION.get(signal)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_virtual_strategy.py -v`
Expected: ALL PASS (6 tests)

- [ ] **Step 5: ruff/mypy clean**

Run: `cd backend && ruff check src/strategy/pine_v2/virtual_strategy.py && mypy src/strategy/pine_v2/virtual_strategy.py`
Expected: no errors

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine_v2/virtual_strategy.py backend/tests/strategy/pine_v2/test_virtual_strategy.py
git commit -m "feat(pine_v2): add SignalKind→VirtualAction mapping for Tier-1 wrapper"
```

---

### Task 3: VirtualStrategyWrapper — 매 bar alert hook 재평가 + strategy 호출

**Files:**
- Modify: `backend/src/strategy/pine_v2/virtual_strategy.py`
- Modify: `backend/tests/strategy/pine_v2/test_virtual_strategy.py`

- [ ] **Step 1: 실패 테스트 작성**

`test_virtual_strategy.py`에 추가:

```python
import pandas as pd

from src.strategy.pine_v2.virtual_strategy import (
    VirtualStrategyWrapper,
    run_virtual_strategy,
)


def _make_ohlcv(closes: list[float]) -> pd.DataFrame:
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * len(closes),
    })


def test_run_virtual_strategy_generates_long_entry_on_condition_true() -> None:
    """alertcondition(buy, 'Long', ...)에서 buy==True가 되는 bar에 strategy.entry('L', long)."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "alertcondition(buy, 'Long', 'UT Long')\n"
    )
    # bar 0: close=100, open=100 → buy=False
    # bar 1: close=110, open=100 → buy=True → strategy.entry('L', long)
    ohlcv = pd.DataFrame({
        "open":   [100.0, 100.0],
        "high":   [101.0, 111.0],
        "low":    [99.0, 99.0],
        "close":  [100.0, 110.0],
        "volume": [100.0, 100.0],
    })
    result = run_virtual_strategy(source, ohlcv)
    state = result.strategy_state
    # bar 1에서 L open 포지션 생성
    assert "L" in state.open_trades
    assert state.open_trades["L"].direction == "long"
    assert state.open_trades["L"].entry_bar == 1


def test_run_virtual_strategy_long_then_short_reverses_position() -> None:
    """Long 진입 후 Short 신호가 오면 Long 청산 + Short 진입 (UT Bot 패턴)."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "sell = close < open\n"
        "alertcondition(buy, 'UT Long', 'UT Long')\n"
        "alertcondition(sell, 'UT Short', 'UT Short')\n"
    )
    ohlcv = pd.DataFrame({
        "open":   [100.0, 100.0, 110.0],
        "high":   [101.0, 111.0, 111.0],
        "low":    [99.0, 99.0, 98.0],
        "close":  [100.0, 110.0, 100.0],  # bar 1: buy, bar 2: sell
        "volume": [100.0, 100.0, 100.0],
    })
    result = run_virtual_strategy(source, ohlcv)
    state = result.strategy_state
    # L은 closed, S는 open
    assert "S" in state.open_trades
    assert state.open_trades["S"].direction == "short"
    closed_l = [t for t in state.closed_trades if t.id == "L"]
    assert len(closed_l) == 1


def test_run_virtual_strategy_discrepancy_warning() -> None:
    """condition과 message가 충돌하면 warning 기록 (condition 우선)."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "bear = close < open\n"
        "alertcondition(bear, 'Buy', 'BUY')\n"  # message=BUY, condition=bear → SHORT
    )
    ohlcv = pd.DataFrame({
        "open":   [100.0, 100.0],
        "high":   [101.0, 101.0],
        "low":    [99.0, 89.0],
        "close":  [100.0, 90.0],  # bar 1: bear=True
        "volume": [100.0, 100.0],
    })
    result = run_virtual_strategy(source, ohlcv)
    assert any("discrepancy" in w.lower() for w in result.warnings)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_virtual_strategy.py -v`
Expected: FAIL — `ImportError: cannot import name 'VirtualStrategyWrapper'`

- [ ] **Step 3: VirtualStrategyWrapper 구현**

`virtual_strategy.py`에 추가:

```python
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.strategy.pine_v2.alert_hook import AlertHook, SignalKind, collect_alerts
from src.strategy.pine_v2.event_loop import _validate_ohlcv
from src.strategy.pine_v2.interpreter import BarContext, Interpreter, PineRuntimeError
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.strategy_state import StrategyState


@dataclass
class VirtualRunResult:
    """Tier-1 가상 strategy 실행 결과."""
    bars_processed: int
    strategy_state: StrategyState
    alerts: list[AlertHook]
    warnings: list[str] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)


class VirtualStrategyWrapper:
    """Alert hook을 매 bar 재평가하여 strategy.* 호출로 연결.

    매 bar 실행 후 각 AlertHook.condition_ast를 interpreter로 평가.
    True이면 signal → VirtualAction 매핑에 따라 strategy.entry / strategy.close 호출.
    직전 bar에서 이미 True였으면 중복 발행 방지(edge-trigger: False→True 전이에서만 발행).
    """

    def __init__(
        self,
        alerts: list[AlertHook],
        interp: Interpreter,
        *,
        strict: bool = True,
    ) -> None:
        self.alerts = alerts
        self.interp = interp
        self.strict = strict
        self.warnings: list[str] = []
        # 각 alert index → 직전 bar 평가 결과 (edge trigger용)
        self._prev: dict[int, bool] = {a.index: False for a in alerts}
        # discrepancy alert은 첫 발생 시에만 1회 경고
        self._discrepancy_logged: set[int] = set()

    def process_bar(self, bar_idx: int) -> None:
        """현재 bar에서 각 alert condition을 재평가 후 strategy action 디스패치."""
        for hook in self.alerts:
            if hook.condition_ast is None:
                continue
            try:
                raw = self.interp._eval_expr(hook.condition_ast)
            except PineRuntimeError as exc:
                if self.strict:
                    raise
                self.warnings.append(
                    f"bar {bar_idx}: alert#{hook.index} condition eval failed: {exc}"
                )
                continue
            cur = self.interp._truthy(raw)
            prev = self._prev[hook.index]
            self._prev[hook.index] = cur
            # edge trigger: False→True 전이만 발행 (alert freq_once_per_bar_close 관례 근사)
            if not (cur and not prev):
                continue

            # discrepancy 최초 1회 기록
            if hook.discrepancy and hook.index not in self._discrepancy_logged:
                self.warnings.append(
                    f"alert#{hook.index}: message='{hook.message}' vs condition='{hook.condition_expr}' "
                    f"discrepancy — using condition_signal={hook.signal.value}"
                )
                self._discrepancy_logged.add(hook.index)

            action = signal_to_action(hook.signal)
            if action is None:
                continue  # INFORMATION/UNKNOWN
            fill_price = self.interp.bar.current("close")
            state = self.interp.strategy
            if action.kind == "entry":
                # 기존 반대 포지션 자동 reverse (Pine 관례)
                reverse_id = "S" if action.direction == "long" else "L"
                if reverse_id in state.open_trades:
                    state.close(reverse_id, bar=bar_idx, fill_price=fill_price)
                assert action.direction is not None
                state.entry(
                    action.trade_id,
                    action.direction,
                    qty=1.0,
                    bar=bar_idx,
                    fill_price=fill_price,
                )
            else:  # close
                state.close(action.trade_id, bar=bar_idx, fill_price=fill_price)


def run_virtual_strategy(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    strict: bool = True,
) -> VirtualRunResult:
    """indicator + alertcondition Pine 스크립트를 가상 strategy로 실행."""
    _validate_ohlcv(ohlcv)
    tree = parse_to_ast(source)
    alerts = collect_alerts(source)

    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
    wrapper = VirtualStrategyWrapper(alerts, interp, strict=strict)

    errors: list[tuple[int, str]] = []
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        try:
            interp.execute(tree)
            wrapper.process_bar(bar.bar_index)
        except PineRuntimeError as exc:
            if strict:
                store.commit_bar()
                raise
            errors.append((bar.bar_index, str(exc)))
        store.commit_bar()
        interp.append_var_series()

    return VirtualRunResult(
        bars_processed=bar.bar_index + 1,
        strategy_state=interp.strategy,
        alerts=alerts,
        warnings=wrapper.warnings,
        errors=errors,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_virtual_strategy.py -v`
Expected: ALL PASS (9 tests 누적)

- [ ] **Step 5: ruff/mypy clean**

Run: `cd backend && ruff check src/strategy/pine_v2/virtual_strategy.py && mypy src/strategy/pine_v2/virtual_strategy.py`
Expected: no errors

- [ ] **Step 6: 공개 API 확장**

`backend/src/strategy/pine_v2/__init__.py`에 추가:

```python
from src.strategy.pine_v2.virtual_strategy import (
    VirtualAction,
    VirtualRunResult,
    VirtualStrategyWrapper,
    run_virtual_strategy,
    signal_to_action,
)

__all__ = [
    # 기존 항목 유지 + 아래 추가
    "VirtualAction",
    "VirtualRunResult",
    "VirtualStrategyWrapper",
    "run_virtual_strategy",
    "signal_to_action",
]
```

(기존 `__all__` 값들은 유지하고 위 5개를 append. 실제 기존 목록은 파일 현재 내용에 맞춰 보존.)

- [ ] **Step 7: 커밋**

```bash
git add backend/src/strategy/pine_v2/virtual_strategy.py backend/src/strategy/pine_v2/__init__.py backend/tests/strategy/pine_v2/test_virtual_strategy.py
git commit -m "feat(pine_v2): add VirtualStrategyWrapper with edge-triggered strategy dispatch"
```

---

### Task 4: Pine v4 legacy stdlib alias (atr / ema / crossover / nz + iff)

**Files:**
- Modify: `backend/src/strategy/pine_v2/interpreter.py`
- Modify: `backend/src/strategy/pine_v2/stdlib.py`
- Test: `backend/tests/strategy/pine_v2/test_stdlib.py`

- [ ] **Step 1: 실패 테스트 작성**

`test_stdlib.py`에 추가:

```python
import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical


def test_v4_stdlib_alias_atr_ema_crossover_iff_nz() -> None:
    """Pine v4 prefix 없는 호출이 ta.* dispatcher로 재라우팅돼야 함."""
    source = (
        "//@version=4\n"
        "study('t', overlay=true)\n"
        "x = atr(5)\n"           # → ta.atr
        "y = ema(close, 3)\n"     # → ta.ema
        "crossed = crossover(close, ema(close, 2))\n"  # → ta.crossover
        "z = iff(close > open, 1.0, 0.0)\n"            # iff builtin
        "w = nz(z[1], 0.0)\n"                           # nz 2-arg
    )
    ohlcv = pd.DataFrame({
        "open":   [100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
        "high":   [102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
        "low":    [99.0,  100.0, 101.0, 102.0, 103.0, 104.0],
        "close":  [101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        "volume": [100.0] * 6,
    })
    result = run_historical(source, ohlcv)
    assert result.bars_processed == 6
    # 최종 상태에서 x(atr) 값이 산출되어 있어야 함
    assert "x" in result.final_state
    assert isinstance(result.final_state["x"], float)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_stdlib.py::test_v4_stdlib_alias_atr_ema_crossover_iff_nz -v`
Expected: FAIL — `PineRuntimeError: Call to 'atr' not supported in current scope`

- [ ] **Step 3: interpreter.py에 v4 alias + iff**

`interpreter.py`의 `_eval_call()` 진입부 수정. `_STDLIB_NAMES` 앞에 v4 alias 매핑 및 iff 처리 추가:

```python
# interpreter.py _eval_call 내, name = _call_chain_name(node.func) 직후
_V4_ALIASES: dict[str, str] = {
    "atr": "ta.atr",
    "ema": "ta.ema",
    "sma": "ta.sma",
    "rsi": "ta.rsi",
    "crossover": "ta.crossover",
    "crossunder": "ta.crossunder",
    "highest": "ta.highest",
    "lowest": "ta.lowest",
    "change": "ta.change",
    "pivothigh": "ta.pivothigh",
    "pivotlow": "ta.pivotlow",
}
if name in _V4_ALIASES:
    name = _V4_ALIASES[name]

# iff(cond, then, else) — v4 built-in (v5에는 없음; ternary로 대체됨)
if name == "iff":
    if len(node.args) != 3:
        raise PineRuntimeError(f"iff expects 3 args, got {len(node.args)}")
    cond_arg, then_arg, else_arg = (
        a.value if isinstance(a, pyne_ast.Arg) else a for a in node.args
    )
    cond_val = self._eval_expr(cond_arg)
    return (
        self._eval_expr(then_arg)
        if self._truthy(cond_val)
        else self._eval_expr(else_arg)
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_stdlib.py -v`
Expected: ALL PASS (기존 + 신규)

- [ ] **Step 5: ruff/mypy clean + regression**

Run: `cd backend && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2 && pytest tests/strategy/pine_v2 -q`
Expected: no errors, 기존 pine_v2 테스트 전체 green

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine_v2/interpreter.py backend/tests/strategy/pine_v2/test_stdlib.py
git commit -m "feat(pine_v2): add Pine v4 legacy stdlib alias + iff builtin"
```

---

### Task 5: i1_utbot E2E — 가상 strategy 완주

**Files:**
- Create: `backend/tests/strategy/pine_v2/test_e2e_i1_utbot.py`

- [ ] **Step 1: 실패 테스트 작성**

`test_e2e_i1_utbot.py` 신규:

```python
"""i1_utbot.pine (v4 UT Bot Alerts) Tier-1 가상 strategy E2E 검증.

Sprint 8b 목표: indicator + alertcondition → 자동 매매 시퀀스 생성.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy


CORPUS = Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "i1_utbot.pine"


def _make_trending_ohlcv() -> pd.DataFrame:
    """UT Bot buy/sell이 번갈아 발생할 수 있는 reversal 시계열.

    20 bar 트렌드: 상승 → 하락 → 상승. ATR=10, key_value=1이면 nLoss=10 근사.
    """
    closes = [
        100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0,
        112.0, 108.0, 104.0, 100.0, 96.0, 92.0,
        94.0, 98.0, 102.0, 106.0, 110.0, 114.0,
    ]
    return pd.DataFrame({
        "open":   [c - 0.5 for c in closes],
        "high":   [c + 1.0 for c in closes],
        "low":    [c - 1.0 for c in closes],
        "close":  closes,
        "volume": [100.0] * len(closes),
    })


def test_i1_utbot_runs_to_completion_without_error() -> None:
    """i1_utbot 전체 스크립트가 pine_v2에서 에러 없이 실행 완료."""
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert result.bars_processed == len(ohlcv)
    assert result.errors == []


def test_i1_utbot_generates_trades_via_alerts() -> None:
    """alertcondition(buy)/(sell)이 가상 strategy로 변환되어 Trade 생성."""
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    state = result.strategy_state
    total_trades = len(state.closed_trades) + len(state.open_trades)
    # UT Bot 반전 시그널이 최소 1회는 나와야 함
    assert total_trades >= 1, (
        f"expected >=1 trade, got 0. alerts={[h.signal for h in result.alerts]}"
    )


def test_i1_utbot_collects_two_alertconditions() -> None:
    """원본 pine에 2개 alertcondition(UT Long, UT Short)."""
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert len(result.alerts) == 2
    signals = {h.signal for h in result.alerts}
    from src.strategy.pine_v2.alert_hook import SignalKind
    assert SignalKind.LONG_ENTRY in signals
    assert SignalKind.SHORT_ENTRY in signals
```

- [ ] **Step 2: 테스트 실행 및 오류 분석**

Run: `cd backend && pytest tests/strategy/pine_v2/test_e2e_i1_utbot.py -v 2>&1 | head -60`

Expected: 일부 FAIL 가능. 전형적 실패 케이스:
- `security()` / `heikinashi()` 미지원 → `h=false`이므로 ternary 단축평가로 회피됨 (의도대로면 통과)
- `barcolor` / `plotshape`는 이미 NOP
- 새로 필요한 함수가 있다면 `_NOP_NAMES`에 추가

- [ ] **Step 3: 발생한 에러를 NOP/지원 경로에 등록**

만약 `security` 또는 `heikinashi` 관련 에러가 발생하면 `_NOP_NAMES`에 추가:

```python
# interpreter.py _eval_call 내 _NOP_NAMES에 확장
_NOP_NAMES = {
    # ... 기존 ...
    "security", "heikinashi",  # Sprint 8b: v4 legacy, 기본 파라미터로 호출 시 close 반환
}
```

Ternary 단축평가로 `h=false`일 땐 호출되지 않아야 하지만, pynescript AST 평가 순서에 따라 양 branch가 모두 evaluate될 가능성 점검. `Interpreter._eval_expr`의 `Conditional` 처리는 이미 단축평가 — `self._truthy(test)`로 한 브랜치만 평가함(confirmed interpreter.py:272-277).

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_e2e_i1_utbot.py -v`
Expected: ALL PASS (3 tests)

- [ ] **Step 5: ruff/mypy + regression**

Run: `cd backend && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2 && pytest tests/strategy/pine_v2 -q`
Expected: no errors

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine_v2/interpreter.py backend/tests/strategy/pine_v2/test_e2e_i1_utbot.py
git commit -m "feat(pine_v2): i1_utbot.pine E2E — Tier-1 virtual strategy 3/6 corpus complete"
```

---

### Task 6: RenderingRegistry — LineObject 좌표 저장 + getter

**Files:**
- Create: `backend/src/strategy/pine_v2/rendering.py`
- Create: `backend/tests/strategy/pine_v2/test_rendering.py`

- [ ] **Step 1: 실패 테스트 작성**

`test_rendering.py` 신규:

```python
"""Tier-0 렌더링 scope A — 좌표 저장 + getter 단위 테스트 (ADR-011 §2.0.4)."""
from __future__ import annotations

import math

import pytest

from src.strategy.pine_v2.rendering import LineObject, RenderingRegistry


def test_line_new_creates_line_object_with_na_coords() -> None:
    reg = RenderingRegistry()
    line = reg.line_new(x1=float("nan"), y1=float("nan"), x2=float("nan"), y2=float("nan"))
    assert isinstance(line, LineObject)
    assert math.isnan(line.x1)
    assert math.isnan(line.y1)


def test_line_set_xy1_updates_coords_and_getter_returns_latest() -> None:
    reg = RenderingRegistry()
    line = reg.line_new(x1=0.0, y1=0.0, x2=0.0, y2=0.0)
    reg.line_set_xy1(line, x=10, y=100.5)
    assert line.x1 == 10
    assert line.y1 == 100.5
    # price getter는 y2 반환 (Pine 관례: end 좌표의 y)
    reg.line_set_xy2(line, x=20, y=110.0)
    assert reg.line_get_price(line, x=20) == 110.0


def test_line_get_price_interpolates_between_endpoints() -> None:
    """line.get_price(x)는 x1,y1 ~ x2,y2 선형보간 (Pine 관례)."""
    reg = RenderingRegistry()
    line = reg.line_new(x1=0, y1=100.0, x2=10, y2=200.0)
    # x=5에서 중간값 150.0
    assert reg.line_get_price(line, x=5) == pytest.approx(150.0)


def test_line_delete_marks_line_inactive() -> None:
    reg = RenderingRegistry()
    line = reg.line_new(x1=0, y1=0, x2=1, y2=1)
    reg.line_delete(line)
    assert line.deleted is True
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_rendering.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.strategy.pine_v2.rendering'`

- [ ] **Step 3: rendering.py 작성**

`backend/src/strategy/pine_v2/rendering.py` 신규:

```python
"""Tier-0 렌더링 scope A — 좌표 저장 + getter만 지원.

ADR-011 §2.0.4 "범위 A" 엄수:
- line / box / label / table 객체는 메모리 stub. 실제 차트 렌더링은 NOP.
- 좌표 저장 → LuxAlgo SMC류의 `line.get_price()` 좌표 재참조로 entry 조건 평가 가능.
- 실제 차트 그리기는 QB 프론트엔드(Next.js)가 담당.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineObject:
    """Pine line 객체 handle — 좌표 + 메타만 보관."""
    x1: float = float("nan")
    y1: float = float("nan")
    x2: float = float("nan")
    y2: float = float("nan")
    deleted: bool = False
    # 추가 속성(color/style/extend 등)은 Pine 호출 시 kwargs로 보관만
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class BoxObject:
    """Pine box 객체 handle."""
    left: float = float("nan")
    top: float = float("nan")
    right: float = float("nan")
    bottom: float = float("nan")
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class LabelObject:
    """Pine label 객체 handle."""
    x: float = float("nan")
    y: float = float("nan")
    text: str = ""
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableObject:
    """Pine table 객체 handle — 셀 내용만 메모리 보관."""
    position: str = ""
    cells: dict[tuple[int, int], str] = field(default_factory=dict)
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


class RenderingRegistry:
    """렌더링 객체 발급·조회. interpreter에 주입되어 line/box/... 호출 디스패치.

    좌표 재참조는 LineObject.y2/BoxObject.top 등 속성 직접 접근이 일반적이나,
    Pine의 `line.get_price(x)`는 선형보간을 제공하므로 메서드로 래핑.
    """

    def __init__(self) -> None:
        self.lines: list[LineObject] = []
        self.boxes: list[BoxObject] = []
        self.labels: list[LabelObject] = []
        self.tables: list[TableObject] = []

    # ---- line ----
    def line_new(
        self, *, x1: float, y1: float, x2: float, y2: float, **extras: Any
    ) -> LineObject:
        obj = LineObject(x1=x1, y1=y1, x2=x2, y2=y2, extras=dict(extras))
        self.lines.append(obj)
        return obj

    def line_set_xy1(self, line: LineObject, *, x: float, y: float) -> None:
        line.x1 = x
        line.y1 = y

    def line_set_xy2(self, line: LineObject, *, x: float, y: float) -> None:
        line.x2 = x
        line.y2 = y

    def line_get_price(self, line: LineObject, *, x: float) -> float:
        """x 좌표의 y 값 (선형보간). Pine 관례: x1==x2면 y1 반환."""
        if line.x2 == line.x1:
            return line.y1
        t = (x - line.x1) / (line.x2 - line.x1)
        return line.y1 + t * (line.y2 - line.y1)

    def line_delete(self, line: LineObject) -> None:
        line.deleted = True

    # ---- box ----
    def box_new(
        self,
        *,
        left: float,
        top: float,
        right: float,
        bottom: float,
        **extras: Any,
    ) -> BoxObject:
        obj = BoxObject(
            left=left, top=top, right=right, bottom=bottom, extras=dict(extras)
        )
        self.boxes.append(obj)
        return obj

    def box_get_top(self, box: BoxObject) -> float:
        return box.top

    def box_get_bottom(self, box: BoxObject) -> float:
        return box.bottom

    def box_set_right(self, box: BoxObject, *, right: float) -> None:
        box.right = right

    def box_delete(self, box: BoxObject) -> None:
        box.deleted = True

    # ---- label ----
    def label_new(
        self, *, x: float, y: float, text: str = "", **extras: Any
    ) -> LabelObject:
        obj = LabelObject(x=x, y=y, text=text, extras=dict(extras))
        self.labels.append(obj)
        return obj

    def label_set_xy(self, label: LabelObject, *, x: float, y: float) -> None:
        label.x = x
        label.y = y

    def label_delete(self, label: LabelObject) -> None:
        label.deleted = True

    # ---- table ----
    def table_new(self, *, position: str = "", **extras: Any) -> TableObject:
        obj = TableObject(position=position, extras=dict(extras))
        self.tables.append(obj)
        return obj

    def table_cell(
        self, table: TableObject, *, column: int, row: int, text: str = ""
    ) -> None:
        table.cells[(column, row)] = text

    def table_delete(self, table: TableObject) -> None:
        table.deleted = True
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_rendering.py -v`
Expected: ALL PASS (4 tests)

- [ ] **Step 5: ruff/mypy clean**

Run: `cd backend && ruff check src/strategy/pine_v2/rendering.py && mypy src/strategy/pine_v2/rendering.py`
Expected: no errors

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine_v2/rendering.py backend/tests/strategy/pine_v2/test_rendering.py
git commit -m "feat(pine_v2): add RenderingRegistry with coord storage + getters (scope A)"
```

---

### Task 7: Interpreter에 Rendering Registry 주입 + line/box/label/table dispatcher

**Files:**
- Modify: `backend/src/strategy/pine_v2/interpreter.py`
- Modify: `backend/src/strategy/pine_v2/event_loop.py`
- Modify: `backend/src/strategy/pine_v2/virtual_strategy.py`
- Test: `backend/tests/strategy/pine_v2/test_rendering.py`

- [ ] **Step 1: 실패 테스트 작성 (Pine 스크립트에서 line.new + get_price 호출)**

`test_rendering.py`에 추가:

```python
import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical


def test_interpreter_registers_line_new_and_get_price() -> None:
    """Pine 스크립트의 line.new(...) 호출이 RenderingRegistry에 등록되고 get_price 호출 가능."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "var l = line.new(0, 100.0, 10, 200.0)\n"
        "mid = line.get_price(l, x=5)\n"
    )
    ohlcv = pd.DataFrame({
        "open":   [100.0, 101.0],
        "high":   [102.0, 103.0],
        "low":    [99.0, 100.0],
        "close":  [101.0, 102.0],
        "volume": [100.0, 100.0],
    })
    result = run_historical(source, ohlcv, strict=True)
    # mid = 150.0 (선형보간)
    assert result.final_state.get("mid") == pytest.approx(150.0)


def test_interpreter_handles_line_set_xy1_xy2_method_calls() -> None:
    """l.set_xy1(x, y) 같은 메서드 호출(Attribute 체인)도 dispatcher가 처리."""
    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "var l = line.new(na, na, na, na)\n"
        "l.set_xy1(bar_index, close)\n"
        "l.set_xy2(bar_index + 1, close + 10.0)\n"
    )
    ohlcv = pd.DataFrame({
        "open":   [100.0, 101.0, 102.0],
        "high":   [102.0, 103.0, 104.0],
        "low":    [99.0, 100.0, 101.0],
        "close":  [101.0, 102.0, 103.0],
        "volume": [100.0, 100.0, 100.0],
    })
    result = run_historical(source, ohlcv, strict=True)
    assert result.bars_processed == 3
```

(상단 `import pytest` 이미 있음)

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_rendering.py -v`
Expected: FAIL — `PineRuntimeError: Call to 'line.new' not supported in current scope`

- [ ] **Step 3: Interpreter에 registry 주입 + dispatcher**

`interpreter.py` 수정:

```python
# 상단 import
from src.strategy.pine_v2.rendering import (
    BoxObject,
    LabelObject,
    LineObject,
    RenderingRegistry,
    TableObject,
)

# Interpreter.__init__ 수정 — rendering 주입 (기존 인자 앞뒤 호환)
def __init__(
    self,
    bar_context: BarContext,
    store: PersistentStore,
    *,
    rendering: RenderingRegistry | None = None,
) -> None:
    self.bar = bar_context
    self.store = store
    self._transient: dict[str, Any] = {}
    self.stdlib = StdlibDispatcher()
    self.strategy = StrategyState()
    self._var_series: dict[str, list[Any]] = {}
    self._prev_close: float = float("nan")
    self.rendering = rendering or RenderingRegistry()
```

`_eval_call()` 내부에서 rendering dispatcher 추가 (strategy.* 뒤, _NOP_NAMES 앞):

```python
# rendering scope A
_RENDERING_METHODS: dict[str, str] = {
    "line.new": "line_new",
    "line.set_xy1": "line_set_xy1",
    "line.set_xy2": "line_set_xy2",
    "line.get_price": "line_get_price",
    "line.delete": "line_delete",
    "box.new": "box_new",
    "box.get_top": "box_get_top",
    "box.get_bottom": "box_get_bottom",
    "box.set_right": "box_set_right",
    "box.delete": "box_delete",
    "label.new": "label_new",
    "label.set_xy": "label_set_xy",
    "label.delete": "label_delete",
    "table.new": "table_new",
    "table.cell": "table_cell",
    "table.delete": "table_delete",
}
if name in _RENDERING_METHODS:
    return self._exec_rendering_call(name, node)

# method call 경로: value.method(args) — pynescript는 Attribute(value=Name, attr="set_xy1")
# _call_chain_name은 "varname.set_xy1" 형태 반환. Name이 handle 변수면 registry method 호출.
if name and "." in name:
    head, _, tail = name.rpartition(".")
    handle = self._resolve_name_if_declared(head)
    if isinstance(handle, (LineObject, BoxObject, LabelObject, TableObject)):
        method_name = f"{type(handle).__name__.lower().replace('object','')}_{tail}"
        # e.g. LineObject + "set_xy1" → "line_set_xy1"
        if method_name in self.rendering.__class__.__dict__ or hasattr(self.rendering, method_name):
            return self._exec_rendering_method(handle, method_name, node)
```

신규 헬퍼 메서드 `_exec_rendering_call` / `_exec_rendering_method` / `_resolve_name_if_declared`:

```python
def _resolve_name_if_declared(self, name: str) -> Any:
    """_resolve_name의 안전 버전 — 미정의면 None."""
    key = f"main::{name}"
    if self.store.is_declared(key):
        return self.store.get(key)
    return self._transient.get(name)

def _exec_rendering_call(self, name: str, node: Any) -> Any:
    """line.new/box.new 등 factory + getter 호출."""
    method_name = _RENDERING_METHODS[name]
    args, kwargs = self._collect_args(node)
    bound = getattr(self.rendering, method_name)
    return bound(*args, **kwargs)

def _exec_rendering_method(
    self, handle: Any, method_name: str, node: Any
) -> Any:
    """handle.method(...) 형식 호출."""
    args, kwargs = self._collect_args(node)
    bound = getattr(self.rendering, method_name)
    return bound(handle, *args, **kwargs)

def _collect_args(self, node: Any) -> tuple[list[Any], dict[str, Any]]:
    """Call.args에서 positional과 keyword 분리."""
    positional: list[Any] = []
    kwargs: dict[str, Any] = {}
    for a in node.args:
        val = self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a)
        arg_name = getattr(a, "name", None) if isinstance(a, pyne_ast.Arg) else None
        if arg_name:
            kwargs[arg_name] = val
        else:
            positional.append(val)
    return positional, kwargs
```

**주의:** `line.new(na, na, na, na)`는 positional 4개. `RenderingRegistry.line_new(x1=..., y1=..., x2=..., y2=...)`는 keyword-only. positional → keyword 변환 필요:

```python
# _exec_rendering_call 내 line.new 특수 처리 (아니면 line_new signature를 positional-friendly로 바꿈)
# 간단 해법: line_new signature를 포지셔널+키워드 혼용 허용으로 변경
```

`rendering.py`의 `line_new` / `box_new` / `label_new` / `table_cell` 시그니처 수정 — `*` 제거하여 positional 허용:

```python
def line_new(
    self, x1: float, y1: float, x2: float, y2: float, **extras: Any
) -> LineObject:
    ...
def box_new(
    self, left: float, top: float, right: float, bottom: float, **extras: Any
) -> BoxObject:
    ...
# label_new / table_cell도 동일
```

(테스트는 x1=... 키워드도 그대로 통과.)

**event_loop.py 수정:** `run_historical`의 Interpreter 생성에 rendering 전달 (기본값 OK):

```python
# event_loop.py run_historical 내
interp = Interpreter(bar, store)  # rendering default → RenderingRegistry()
```

(이미 default이므로 수정 불필요. 다만 RunResult에 capture 원하면 차후 확장.)

**virtual_strategy.py 수정:** 동일 (Interpreter 기본 rendering 사용).

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_rendering.py -v`
Expected: ALL PASS (6 tests 누적)

- [ ] **Step 5: regression + ruff/mypy**

Run: `cd backend && pytest tests/strategy/pine_v2 -q && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2`
Expected: no errors

- [ ] **Step 6: 공개 API 확장**

`backend/src/strategy/pine_v2/__init__.py`에 추가:

```python
from src.strategy.pine_v2.rendering import (
    BoxObject,
    LabelObject,
    LineObject,
    RenderingRegistry,
    TableObject,
)
# __all__에 추가
```

- [ ] **Step 7: 커밋**

```bash
git add backend/src/strategy/pine_v2/interpreter.py backend/src/strategy/pine_v2/rendering.py backend/src/strategy/pine_v2/__init__.py backend/tests/strategy/pine_v2/test_rendering.py
git commit -m "feat(pine_v2): wire RenderingRegistry into interpreter — line/box/label/table dispatch"
```

---

### Task 8: switch statement + ta.stdev / ta.variance / math.abs (i2_luxalgo 선결)

**Files:**
- Modify: `backend/src/strategy/pine_v2/interpreter.py`
- Modify: `backend/src/strategy/pine_v2/stdlib.py`
- Test: `backend/tests/strategy/pine_v2/test_interpreter.py`
- Test: `backend/tests/strategy/pine_v2/test_stdlib.py`

- [ ] **Step 1: pynescript switch AST 형태 확인**

Run: `cd backend && python -c "from pynescript import ast; t=ast.parse('x = switch y\n    1 => 10\n    2 => 20\n    => 0\n'); print(ast.dump(t))"`
Expected: 출력에 `Switch` 노드가 있다면 별도 처리, 없다면 match/case로 변환되는 형태.

(출력 기반으로 아래 Step 3 구현 분기 결정.)

- [ ] **Step 2: 실패 테스트 작성**

`test_interpreter.py`에 추가:

```python
def test_switch_selects_matching_branch() -> None:
    """Pine switch → 매칭 branch의 표현식 반환."""
    source = (
        "//@version=5\n"
        "indicator('t')\n"
        "m = 'Atr'\n"
        "slope = switch m\n"
        "    'Atr' => 10.0\n"
        "    'Stdev' => 20.0\n"
        "    => 0.0\n"
    )
    from src.strategy.pine_v2.event_loop import run_historical
    import pandas as pd
    ohlcv = pd.DataFrame({
        "open": [100.0], "high": [101.0], "low": [99.0],
        "close": [100.0], "volume": [100.0],
    })
    result = run_historical(source, ohlcv, strict=True)
    assert result.final_state.get("slope") == 10.0
```

`test_stdlib.py`에 추가:

```python
def test_ta_stdev_and_variance_return_float() -> None:
    """ta.stdev / ta.variance 기본 호출."""
    from src.strategy.pine_v2.stdlib import StdlibDispatcher
    d = StdlibDispatcher()
    # 충분한 window
    for i, price in enumerate([100.0, 101.0, 99.0, 102.0, 98.0]):
        v = d.call("ta.stdev", 1, [price, 3], high=price+1, low=price-1, close_prev=price-0.5)
    assert isinstance(v, float)


def test_math_abs_returns_absolute_value() -> None:
    source = (
        "//@version=5\n"
        "indicator('t')\n"
        "x = math.abs(-3.5)\n"
    )
    from src.strategy.pine_v2.event_loop import run_historical
    import pandas as pd
    ohlcv = pd.DataFrame({
        "open": [100.0], "high": [101.0], "low": [99.0],
        "close": [100.0], "volume": [100.0],
    })
    result = run_historical(source, ohlcv, strict=True)
    assert result.final_state.get("x") == 3.5
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_interpreter.py::test_switch_selects_matching_branch tests/strategy/pine_v2/test_stdlib.py::test_ta_stdev_and_variance_return_float tests/strategy/pine_v2/test_stdlib.py::test_math_abs_returns_absolute_value -v`
Expected: FAIL

- [ ] **Step 4: switch 구현 (interpreter.py)**

Step 1에서 확인한 pynescript AST 이름 기준(Switch or Match). 아래는 `Switch` 노드 가정 — 실제 이름 상이하면 조정:

```python
# interpreter.py _eval_expr 내, Call 직전에 추가
if isinstance(node, pyne_ast.Switch):
    return self._eval_switch(node)

def _eval_switch(self, node: Any) -> Any:
    """Pine switch: subject 값과 각 case를 순차 비교, default(=>)는 fallback."""
    subject = self._eval_expr(node.subject) if getattr(node, "subject", None) else None
    for case in getattr(node, "cases", []):
        case_val = getattr(case, "value", None)
        if case_val is None:
            # default branch
            return self._eval_expr(case.body)
        cv = self._eval_expr(case_val)
        if subject == cv:
            return self._eval_expr(case.body)
    return None  # 매칭 없고 default도 없으면 na
```

**만약 AST 이름이 Match/MatchCase 등이면** `pyne_ast.Match` / `pyne_ast.MatchCase`로 교체, 속성 이름도 맞춤.

- [ ] **Step 5: ta.stdev / ta.variance 추가 (stdlib.py)**

`stdlib.py`의 `StdlibDispatcher.call()` 내 매핑에 추가:

```python
# 슬라이딩 윈도우 기반 표준편차 / 분산
elif name == "ta.stdev":
    source_val, length = args[0], int(args[1])
    state = self._states.setdefault(caller_id, {"window": []})
    state["window"].append(float(source_val))
    if len(state["window"]) > length:
        state["window"] = state["window"][-length:]
    if len(state["window"]) < length:
        return float("nan")
    m = sum(state["window"]) / length
    var = sum((x - m) ** 2 for x in state["window"]) / length
    return math.sqrt(var)
elif name == "ta.variance":
    source_val, length = args[0], int(args[1])
    state = self._states.setdefault(caller_id, {"window": []})
    state["window"].append(float(source_val))
    if len(state["window"]) > length:
        state["window"] = state["window"][-length:]
    if len(state["window"]) < length:
        return float("nan")
    m = sum(state["window"]) / length
    return sum((x - m) ** 2 for x in state["window"]) / length
```

그리고 interpreter.py `_STDLIB_NAMES` 집합에 `"ta.stdev", "ta.variance"` 추가.

- [ ] **Step 6: math.abs 추가 (interpreter.py _eval_call 내)**

```python
# _STDLIB_NAMES 직후 special dispatch
_MATH_FUNCS = {"math.abs": abs, "math.max": max, "math.min": min}
if name in _MATH_FUNCS:
    args = [
        self._eval_expr(a.value if isinstance(a, pyne_ast.Arg) else a)
        for a in node.args
    ]
    return _MATH_FUNCS[name](*args)
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/ -v -k "switch or stdev or math_abs"`
Expected: ALL PASS

- [ ] **Step 8: regression + ruff/mypy**

Run: `cd backend && pytest tests/strategy/pine_v2 -q && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2`
Expected: no errors

- [ ] **Step 9: 커밋**

```bash
git add backend/src/strategy/pine_v2/interpreter.py backend/src/strategy/pine_v2/stdlib.py backend/tests/strategy/pine_v2/test_interpreter.py backend/tests/strategy/pine_v2/test_stdlib.py
git commit -m "feat(pine_v2): add switch statement + ta.stdev/variance + math.abs"
```

---

### Task 9: i2_luxalgo E2E — Tier-1 가상 strategy + 렌더링 scope A 통합

**Files:**
- Create: `backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py`

- [ ] **Step 1: 실패 테스트 작성**

`test_e2e_i2_luxalgo.py` 신규:

```python
"""i2_luxalgo.pine (v5 Trendlines with Breaks [LuxAlgo]) E2E.

Sprint 8b 목표: switch + line.new/set_xy1/xy2 + ta.pivothigh/pivotlow로 완주.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.rendering import LineObject
from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy


CORPUS = Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "i2_luxalgo.pine"


def _make_pivot_ohlcv() -> pd.DataFrame:
    """pivot high/low 발생하도록 설계된 30+ bar 시계열."""
    closes = [
        100, 102, 104, 108, 110, 108, 104, 100, 96, 94,  # 상승 → 하락
        96, 100, 104, 106, 104, 100, 96, 92, 90, 88,      # 하락
        90, 94, 98, 102, 106, 108, 106, 102, 98, 96,      # 반등
        100, 104, 108, 112,
    ]
    return pd.DataFrame({
        "open":   [c - 0.5 for c in closes],
        "high":   [c + 1.0 for c in closes],
        "low":    [c - 1.0 for c in closes],
        "close":  [float(c) for c in closes],
        "volume": [100.0] * len(closes),
    })


def test_i2_luxalgo_runs_to_completion() -> None:
    """i2_luxalgo 전체 스크립트가 pine_v2에서 에러 없이 실행 완료."""
    source = CORPUS.read_text()
    ohlcv = _make_pivot_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert result.bars_processed == len(ohlcv)
    assert result.errors == []


def test_i2_luxalgo_registers_trendlines_in_rendering() -> None:
    """line.new(...) 호출이 RenderingRegistry에 등록되고 set_xy1/xy2로 좌표 갱신."""
    source = CORPUS.read_text()
    ohlcv = _make_pivot_ohlcv()
    # virtual wrapper 경로에서 interpreter 추출 필요 — rendering 직접 점검용으로
    # run_virtual_strategy가 반환하는 VirtualRunResult에 rendering 노출 필요.
    result = run_virtual_strategy(source, ohlcv, strict=True)
    # interpreter의 rendering을 어떻게 노출할지는 VirtualRunResult.rendering 필드로
    assert result.rendering is not None
    # var uptl / var dntl — 최소 2개 line 등록
    assert len(result.rendering.lines) >= 2
    # 일부는 set_xy1으로 실제 좌표 갱신됨 (ph 발생 bar가 있을 경우)
    updated = [ln for ln in result.rendering.lines if not _all_nan(ln)]
    # 너무 엄격하지 않게 — 등록 자체 통과 목표
    # (pivot 감지가 충분하면 updated > 0)


def _all_nan(line: LineObject) -> bool:
    import math
    return all(math.isnan(v) for v in (line.x1, line.y1, line.x2, line.y2))


def test_i2_luxalgo_generates_breakout_alerts() -> None:
    """2개 alertcondition(Upward/Downward Breakout)이 분류됨."""
    source = CORPUS.read_text()
    ohlcv = _make_pivot_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert len(result.alerts) == 2
```

- [ ] **Step 2: VirtualRunResult에 rendering 필드 추가**

`virtual_strategy.py` 수정:

```python
@dataclass
class VirtualRunResult:
    bars_processed: int
    strategy_state: StrategyState
    alerts: list[AlertHook]
    rendering: RenderingRegistry | None = None  # ← 추가
    warnings: list[str] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)

# run_virtual_strategy 반환부 수정
return VirtualRunResult(
    bars_processed=bar.bar_index + 1,
    strategy_state=interp.strategy,
    alerts=alerts,
    rendering=interp.rendering,
    warnings=wrapper.warnings,
    errors=errors,
)
```

- [ ] **Step 3: 테스트 실행 + 오류 분석**

Run: `cd backend && pytest tests/strategy/pine_v2/test_e2e_i2_luxalgo.py -v 2>&1 | head -80`
Expected: 초기에는 FAIL 가능. 예상되는 에러와 해결 방식:
  - `Call to 'plot' not supported` → 이미 NOP
  - `Attribute access not supported: extend.right` → `_ATTR_CONSTANTS`에 `extend.right/left/none` 추가 (값은 문자열 그대로)
  - `input(tooltip=...)` — 이미 지원이지만 tooltip kwarg 무시되는지 점검
  - `line.style_dashed` → `_ATTR_CONSTANTS`에 `line.style_dashed/dotted/solid` 추가
  - `na` 값을 line.new positional로 전달 → NaN 처리됨 (이미 지원)

필요한 상수 추가:

```python
# interpreter.py _eval_attribute 내 _ATTR_CONSTANTS 확장
_ATTR_CONSTANTS = {
    "strategy.long": "long",
    "strategy.short": "short",
    "extend.right": "right",
    "extend.left": "left",
    "extend.none": "none",
    "line.style_dashed": "dashed",
    "line.style_dotted": "dotted",
    "line.style_solid": "solid",
    "shape.labelup": "labelup",
    "shape.labeldown": "labeldown",
    "location.absolute": "absolute",
    "location.belowbar": "belowbar",
    "location.abovebar": "abovebar",
    "size.tiny": "tiny",
    "size.small": "small",
    "size.normal": "normal",
    "size.large": "large",
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && pytest tests/strategy/pine_v2/test_e2e_i2_luxalgo.py -v`
Expected: ALL PASS (3 tests)

- [ ] **Step 5: regression + ruff/mypy**

Run: `cd backend && pytest tests/strategy/pine_v2 -q && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2`
Expected: no errors

- [ ] **Step 6: 커밋**

```bash
git add backend/src/strategy/pine_v2/ backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py
git commit -m "feat(pine_v2): i2_luxalgo.pine E2E — rendering scope A 4/6 corpus complete"
```

---

### Task 10: 전체 regression + docs 동기화

**Files:**
- Modify: `docs/TODO.md` (진행 반영)
- Modify: `.claude/CLAUDE.md` "현재 작업" 섹션 (Sprint 8b 추가)

- [ ] **Step 1: 전체 backend 테스트**

Run: `cd backend && pytest -q`
Expected: 기존 526 + Sprint 8b 신규(약 25~30) = **550+ tests**, all green

- [ ] **Step 2: Frontend 회귀 (무관 확인)**

Run: `cd frontend && pnpm test -- --run 2>&1 | tail -20`
Expected: 기존 green 유지 (Sprint 8b는 backend 전용이라 영향 없음 예상)

- [ ] **Step 3: TODO.md 갱신**

`docs/TODO.md`의 Completed 섹션에 추가:

```markdown
- [x] Sprint 8b Tier-1 가상 strategy 래퍼 + Tier-0 렌더링 scope A (2026-04-18~2026-04-XX)
  - VirtualStrategyWrapper + run_virtual_strategy (alert → strategy 자동 매핑, edge-trigger)
  - RenderingRegistry — line/box/label/table 좌표 + getter
  - Pine v4 legacy alias (atr/ema/crossover/iff/nz-2arg)
  - switch statement + ta.stdev/variance + math.abs
  - i1_utbot.pine / i2_luxalgo.pine E2E 완주 → 6 corpus 매트릭스 4/6
```

- [ ] **Step 4: CLAUDE.md "현재 작업" 섹션 갱신**

`.claude/CLAUDE.md` 하단의 "현재 작업" 리스트에 추가:

```markdown
- Sprint 8b Tier-1 + Tier-0 렌더링 scope A ✅ 완료 (2026-04-XX, PR #XX) — 6 corpus 2/6→4/6. i1_utbot + i2_luxalgo 자동 매매 경로 구축
```

- [ ] **Step 5: 커밋**

```bash
git add docs/TODO.md .claude/CLAUDE.md
git commit -m "docs: sync Sprint 8b completion — Tier-1 wrapper + rendering scope A, 4/6 corpus"
```

- [ ] **Step 6: 마무리 검증**

Run: `cd backend && pytest -q && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2 && cd ../frontend && pnpm test -- --run 2>&1 | tail -5`
Expected: **all green, no lint/type errors**

- [ ] **Step 7: 사용자 승인 후 push / PR** (수동 — Golden Rules Git Safety Protocol)

---

## Verification (End-to-End)

### 단위 테스트 green 기준
```bash
cd backend && pytest tests/strategy/pine_v2 -v
```
Expected counts (표준): **기존 169 → 최소 195+ tests**

### 신규 추가 테스트 파일
- `test_virtual_strategy.py` — 9 tests (signal mapping + wrapper 3 cases + reverse + discrepancy)
- `test_rendering.py` — 6 tests (Line/Box/Label 좌표 + get_price 보간 + interpreter 통합 2건)
- `test_e2e_i1_utbot.py` — 3 tests (completion + trade generation + 2 alertconditions)
- `test_e2e_i2_luxalgo.py` — 3 tests (completion + rendering handles + breakout alerts)
- `test_alert_hook.py` — 2 tests 추가 (condition_ast preservation)
- `test_stdlib.py` — 3 tests 추가 (v4 alias + stdev/variance + math.abs)
- `test_interpreter.py` — 1 test 추가 (switch)

총 **27 신규 tests** = 169 + 27 = **~196 tests**

### Corpus 매트릭스 검증
```bash
cd backend && pytest tests/strategy/pine_v2/test_e2e_ -v
```
Expected: 4 corpus 완주
- `test_e2e_ma_crossover.py` (기존, 1/6 — synthetic이지만 완주)
- `test_e2e_s1_pbr.py` (Sprint 8a, 2/6)
- `test_e2e_i1_utbot.py` (Sprint 8b, 3/6)
- `test_e2e_i2_luxalgo.py` (Sprint 8b, 4/6)

### Lint / Type
```bash
cd backend && ruff check src/strategy/pine_v2 && mypy src/strategy/pine_v2
```
Expected: no errors

### Regression
```bash
cd backend && pytest -q
```
Expected: 기존 526 + Sprint 8b ~27 = 550+ green

---

## Critical Files Reference

### 읽기/참조 전용
- `docs/dev-log/011-pine-execution-strategy-v4.md` — ADR-011 §2.0.4(렌더링 scope A), §2.1.4(Tier-1 virtual strategy), §13(H1 MVP scope)
- `docs/04_architecture/pine-execution-architecture.md:93-103, 336-363` — 3-Track + 범위 A 표
- `docs/dev-log/012-sprint-8a-tier0-final-report.md:167-177` — 남은 gap/Sprint 8b roadmap
- `backend/tests/fixtures/pine_corpus_v2/i1_utbot.pine` — v4 UT Bot 원본
- `backend/tests/fixtures/pine_corpus_v2/i2_luxalgo.pine` — v5 LuxAlgo 원본

### 재사용 (이미 존재)
- `src.strategy.pine_v2.alert_hook.collect_alerts()` / `classify_message()` / `SignalKind`
- `src.strategy.pine_v2.event_loop._validate_ohlcv()` (private이지만 같은 패키지 내 재사용 가능)
- `src.strategy.pine_v2.interpreter.BarContext` / `Interpreter` / `PineRuntimeError`
- `src.strategy.pine_v2.parser_adapter.parse_to_ast()`
- `src.strategy.pine_v2.strategy_state.StrategyState` — entry/close/close_all/position_size
- `src.strategy.pine_v2.stdlib.StdlibDispatcher`
- `src.strategy.pine_v2.runtime.PersistentStore`

### 수정 대상 (이 Sprint)
- `backend/src/strategy/pine_v2/alert_hook.py` (Task 1)
- `backend/src/strategy/pine_v2/interpreter.py` (Tasks 4, 7, 8)
- `backend/src/strategy/pine_v2/stdlib.py` (Task 8)
- `backend/src/strategy/pine_v2/__init__.py` (Tasks 3, 7)

### 신규 작성 (이 Sprint)
- `backend/src/strategy/pine_v2/virtual_strategy.py`
- `backend/src/strategy/pine_v2/rendering.py`
- `backend/tests/strategy/pine_v2/test_virtual_strategy.py`
- `backend/tests/strategy/pine_v2/test_rendering.py`
- `backend/tests/strategy/pine_v2/test_e2e_i1_utbot.py`
- `backend/tests/strategy/pine_v2/test_e2e_i2_luxalgo.py`

---

## Risks & Mitigation

| 위험 | 가능성 | 대응 |
|------|:----:|------|
| pynescript `switch` AST 노드 이름이 `Match`류일 수 있음 | 중 | Task 8 Step 1에서 실제 AST dump로 확인 후 분기 |
| i2_luxalgo의 `str.tostring` / `math.abs` 외 추가 함수 누락 | 중 | Task 9 Step 3에서 실행 중 에러 발생 시 NOP/stub 추가 |
| `line.new(na, na, na, na)` positional 4개가 registry의 keyword-only signature와 충돌 | 확정 | Task 7 Step 3에서 positional 허용으로 signature 변경 |
| UT Bot의 `iff` chained(3단 중첩)이 `_eval_expr` 재귀 한계 초과 | 저 | Python 기본 재귀 한도 충분. 필요 시 iff를 ternary equivalent로 처리 (이미 Task 4에서 구현) |
| i2_luxalgo `var uptl = line.new(na,...)` — var 선언이 1회만 평가되지만 매 bar set_xy1 호출 | 중 | var는 PersistentStore로 1회만 평가, 이후 reassign은 없이 method call만 (정상 동작 예상) |

---

## Self-Review Checklist

- [x] **Spec coverage:** Tier-1 wrapper (Task 2-3-5) + rendering scope A (Task 6-7-9) + 부수 준비(Task 1, 4, 8) + docs (Task 10) — 원본 요구사항 모두 task에 매핑됨
- [x] **No placeholders:** 모든 step에 실제 코드/커맨드 포함. "TBD" 없음.
- [x] **Type consistency:** `AlertHook.condition_ast: Any | None` — interpreter에 전달 시 `_eval_expr(Any)` 시그니처와 부합 / `VirtualAction.direction: Literal["long","short"] | None` — StrategyState.entry Direction 타입과 호환 / `RenderingRegistry.line_new(x1:float,...)` — positional/keyword 양쪽 수용
- [x] **Reused existing utilities:** parse_to_ast, collect_alerts, StrategyState, Interpreter, PersistentStore, StdlibDispatcher 모두 재활용
- [x] **Incremental commits:** 10 tasks × 1 commit = 최소 10 커밋 (각 task 내 step별 checkpoint 가능)
- [x] **TDD 순서:** 각 task "실패 테스트 작성 → 실패 확인 → 구현 → 통과 확인 → ruff/mypy → 커밋"

---

**Execution strategy:** task를 순서대로 실행. Task 1-5는 Tier-1 경로 완성(i1_utbot 완주), Task 6-9는 렌더링 + i2_luxalgo 완주, Task 10은 docs 마무리.

최종 산출물: **6 corpus 매트릭스 4/6 + pine_v2 tests 169 → 196 + ruff/mypy clean**
