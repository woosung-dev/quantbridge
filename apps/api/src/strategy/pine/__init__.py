# Pine Script v1 legacy module — pine_v2 SSOT 전환 후 types/errors 만 유지.
"""Pine v1 legacy shim — production 은 `src.strategy.pine_v2` SSOT 사용.

본 모듈은 ADR-011 §6/§8 + Sprint 8a PR #20 이후 *지표 계산 전용* 으로 강등됐다.
lexer/parser/interpreter/stdlib/v4_to_v5/ast_nodes 6 module (2146L) 은 Tier 2
refactor audit 시 제거됐다. 본 모듈은 backtest engine adapter (`src.backtest.engine.{types,adapter,v2_adapter,__init__}`)
가 import 하는 `ParseOutcome / SignalResult / SourceSpan / PineError` 4 종 타입만
재export 한다. 새 Pine 작업은 `src.strategy.pine_v2` 사용.
"""

from __future__ import annotations

from src.strategy.pine.errors import (
    PineError,
    PineLexError,
    PineParseError,
    PineRuntimeError,
    PineUnsupportedError,
)
from src.strategy.pine.types import ParseOutcome, SignalResult, SourceSpan

__all__ = [
    "ParseOutcome",
    "PineError",
    "PineLexError",
    "PineParseError",
    "PineRuntimeError",
    "PineUnsupportedError",
    "SignalResult",
    "SourceSpan",
]
