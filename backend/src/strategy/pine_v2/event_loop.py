"""Bar-by-bar 이벤트 루프 드라이버 (Week 2 Day 2).

Pine AST interpreter를 OHLCV DataFrame 위에서 반복 호출하여 시계열 실행.
ADR-011 §2.0.3 bar-by-bar 이벤트 루프 원칙 구현.

의미론:
- 각 bar 진입 시 `store.begin_bar()` → interpreter가 실행 → `store.commit_bar()`
- var/varip 상태는 bar 경계를 지나 유지됨 (PersistentStore 책임)
- transient(비영속) 변수는 매 bar 재초기화 (interpreter.reset_transient)
- realtime rollback은 현재 루프 범위 밖 (historical 백테스트 용)

공개 API:
- `run_historical(source, ohlcv) -> RunResult`
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from src.strategy.pine_v2.interpreter import (
    BarContext,
    Interpreter,
    PineRuntimeError,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


@dataclass
class RunResult:
    """이벤트 루프 실행 결과."""

    bars_processed: int
    final_state: dict[str, Any]  # PersistentStore snapshot (key → value)
    state_history: list[dict[str, Any]] = field(default_factory=list)  # 각 bar commit 후 state
    errors: list[tuple[int, str]] = field(default_factory=list)  # (bar_index, 메시지)

    def __len__(self) -> int:
        return self.bars_processed

    def to_dict(self) -> dict[str, Any]:
        return {
            "bars_processed": self.bars_processed,
            "final_state": self.final_state,
            "state_history_length": len(self.state_history),
            "errors": self.errors,
        }


def run_historical(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    capture_history: bool = True,
    strict: bool = True,
) -> RunResult:
    """Pine 소스를 OHLCV bar-by-bar 실행.

    Args:
        source: Pine 소스 코드.
        ohlcv: columns must include open/high/low/close/volume.
        capture_history: 각 bar commit 후 state를 기록할지 (디버깅/테스트용).
        strict: True면 interpreter 오류를 즉시 raise, False면 errors에 기록 후 계속.
    """
    _validate_ohlcv(ohlcv)
    tree = parse_to_ast(source)

    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
    result = RunResult(bars_processed=0, final_state={})

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()  # prev_close 갱신 (ta.atr 등에 사용)
        try:
            interp.execute(tree)
        except PineRuntimeError as e:
            msg = str(e)
            if strict:
                store.commit_bar()  # bar는 닫고 에러 전파
                raise
            result.errors.append((bar.bar_index, msg))
        store.commit_bar()
        interp.append_var_series()  # 이번 bar의 user 변수 값을 시리즈에 append
        # persistent("main::name") + transient(bare name) 병합하여 스냅샷
        combined = {**store.snapshot_dict(), **interp._transient}
        if capture_history:
            result.state_history.append(combined)
        result.bars_processed += 1

    # 마지막 bar의 병합 스냅샷
    result.final_state = {**store.snapshot_dict(), **interp._transient}
    return result


def _validate_ohlcv(df: pd.DataFrame) -> None:
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV DataFrame missing columns: {sorted(missing)}")
    if len(df) == 0:
        raise ValueError("OHLCV DataFrame is empty")
