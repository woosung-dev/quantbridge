# Interpreter input.* override hook 검증 (BL-220 Sprint 51 Slice 2)
"""Sprint 51 Slice 2 RED — Interpreter ctor input_overrides + _eval_call() override apply.

codex G.0 P1#2: _exec_assign push/pop pattern (assignment target stack).
codex G.0 P1#3: signature propagation 5 파일 (compat / track_runner / event_loop /
virtual_strategy / v2_adapter) — Slice 2 GREEN 에서 함께 적용.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def _make_ohlcv() -> pd.DataFrame:
    """1-bar dummy OHLCV (input.* eval 위해 1 bar 만 advance 하면 충분)."""
    return pd.DataFrame(
        {
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [1.0],
        }
    )


def _make_interp(input_overrides: dict | None = None) -> tuple[Interpreter, BarContext]:
    """Interpreter + BarContext 생성 helper."""
    ohlcv = _make_ohlcv()
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store, input_overrides=input_overrides)
    return interp, bar


class TestInputIntOverride:
    """input.int 동작 — override 미주입 / 주입."""

    def test_input_int_uses_default_when_no_override(self) -> None:
        """override 없을 때 = defval 반환 (회귀 0)."""
        source = "emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp()
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("emaPeriod") == 14

    def test_input_int_uses_override_when_provided(self) -> None:
        """override 주입 시 = override value 반환."""
        source = "emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides={"emaPeriod": 20})
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("emaPeriod") == 20


class TestInputFloatOverride:
    """input.float 동작."""

    def test_input_float_uses_override(self) -> None:
        """input.float override = Decimal value 반환 (Sprint 4 D8 Decimal-first)."""
        source = "stopLossPct = input.float(1.0, 'Stop Loss %')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides={"stopLossPct": Decimal("2.5")})
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("stopLossPct") == Decimal("2.5")


class TestInputBoolOverride:
    """input.bool 동작."""

    def test_input_bool_uses_override(self) -> None:
        """input.bool override = True 반환 (default=False)."""
        source = "useStopLoss = input.bool(false, 'Use Stop Loss')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides={"useStopLoss": True})
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("useStopLoss") is True


class TestInputStringOverride:
    """input.string 동작."""

    def test_input_string_uses_override(self) -> None:
        """input.string override = override str 반환."""
        source = "tf = input.string('1h', 'Timeframe')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides={"tf": "4h"})
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("tf") == "4h"


class TestInputOverrideFallthrough:
    """edge case — InputDecl 부재 var_name 또는 mismatched name."""

    def test_invalid_var_name_falls_through_to_default(self) -> None:
        """override 의 key 가 실제 input 변수명과 mismatch → defval 사용 (silent ignore)."""
        source = "emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        # override 가 'wrongKey' 로 mismatch — input declaration 의 var_name 'emaPeriod' 와 무관
        interp, bar = _make_interp(input_overrides={"wrongKey": 99})
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("emaPeriod") == 14

    def test_no_override_dict_does_not_crash(self) -> None:
        """input_overrides=None default = 회귀 0."""
        source = "emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides=None)
        bar.advance()
        interp.execute(tree)
        assert interp._transient.get("emaPeriod") == 14


class TestPersistentVarOverride:
    """codex Slice 2 review P1 회귀 가드 — `var x = input.*` / `varip x = input.*` 영속 path.

    factory() deferred eval 시점에도 _assignment_target_stack push/pop 적용 의무.
    누락 시 Param Stability grid 가 silent 하게 default 만 사용 → false 결과.
    """

    def test_var_input_int_uses_override(self) -> None:
        """`var emaPeriod = input.int(14)` + override → override value 사용."""
        source = "var emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides={"emaPeriod": 25})
        bar.advance()
        interp.execute(tree)
        # var 은 PersistentStore 안 'main::emaPeriod' 로 저장.
        snapshot = interp.store.snapshot_dict()
        assert snapshot.get("main::emaPeriod") == 25

    def test_varip_input_float_uses_override(self) -> None:
        """`varip stopLossPct = input.float(1.0)` + override → override value 사용."""
        source = "varip stopLossPct = input.float(1.0, 'Stop Loss %')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp(input_overrides={"stopLossPct": Decimal("3.0")})
        bar.advance()
        interp.execute(tree)
        snapshot = interp.store.snapshot_dict()
        assert snapshot.get("main::stopLossPct") == Decimal("3.0")

    def test_var_input_default_when_no_override(self) -> None:
        """`var x = input.int(14)` + override 없음 → defval (14) 사용 (회귀 0)."""
        source = "var emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp()
        bar.advance()
        interp.execute(tree)
        snapshot = interp.store.snapshot_dict()
        assert snapshot.get("main::emaPeriod") == 14


class TestAssignmentTargetStack:
    """codex G.0 P1#2 — _assignment_target_stack push/pop pattern.

    nested assignment 또는 _exec_assign 안 RHS eval 후 stack 정확 복원 검증.
    """

    def test_stack_empty_after_execute(self) -> None:
        """execute 끝나면 stack 은 비어있음 (모든 push 가 pop 으로 복원)."""
        source = "emaPeriod = input.int(14, 'EMA Period')"
        tree = parse_to_ast(source)
        interp, bar = _make_interp()
        bar.advance()
        interp.execute(tree)
        assert interp._assignment_target_stack == []

    def test_stack_initialized_empty(self) -> None:
        """ctor 직후 stack 은 빈 list."""
        interp, _ = _make_interp()
        assert interp._assignment_target_stack == []
