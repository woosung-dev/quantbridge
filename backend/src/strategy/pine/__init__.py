"""Pine Script parser and interpreter (AST-based, no exec/eval).

공개 API:
- parse_and_run(source, ohlcv) -> ParseOutcome
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine.errors import (
    PineError,
    PineLexError,
    PineParseError,
    PineRuntimeError,
    PineUnsupportedError,
)
from src.strategy.pine.interpreter import execute_program
from src.strategy.pine.lexer import tokenize
from src.strategy.pine.parser import parse
from src.strategy.pine.stdlib import validate_functions
from src.strategy.pine.types import ParseOutcome, SignalResult, SourceSpan
from src.strategy.pine.v4_to_v5 import detect_version, normalize

# 구조적 호출 (stdlib 외) — 인터프리터가 직접 처리하는 함수들
_ALLOWED_STRUCTURAL: set[str] = {
    "strategy",
    "strategy.entry",
    "strategy.close",
    "strategy.exit",
    "indicator",
    "input",
    "input.int",
    "input.float",
    "input.bool",
    "input.string",
    "plot",
    "plotshape",
    "bgcolor",
    "barcolor",
    "fill",
    "alert",
    "alertcondition",
    "timestamp",
    "color.new",
    "color.red",
    "color.green",
    "color.blue",
    "color.white",
    "color.black",
}


def parse_and_run(source: str, ohlcv: pd.DataFrame) -> ParseOutcome:
    """Pine Script(v4 or v5)를 해석·실행. 미지원 감지 시 전체 중단.

    ohlcv는 open/high/low/close/volume 컬럼을 가진 DataFrame.
    """
    original_version = detect_version(source)

    try:
        normalized = normalize(source)
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        tokens = tokenize(normalized)
    except PineError as e:
        return ParseOutcome(
            status="error",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        program = parse(tokens)
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )
    except PineError as e:
        return ParseOutcome(
            status="error",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        report = validate_functions(program, allowed_structural=_ALLOWED_STRUCTURAL)
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report={},
            source_version=original_version,
        )

    try:
        result = execute_program(
            program,
            open_=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            volume=ohlcv["volume"],
        )
    except PineUnsupportedError as e:
        return ParseOutcome(
            status="unsupported",
            result=None,
            error=e,
            supported_feature_report=report,
            source_version=original_version,
        )
    except PineError as e:
        return ParseOutcome(
            status="error",
            result=None,
            error=e,
            supported_feature_report=report,
            source_version=original_version,
        )

    return ParseOutcome(
        status="ok",
        result=result,
        error=None,
        supported_feature_report=report,
        source_version=original_version,
    )


__all__ = [
    "ParseOutcome",
    "PineError",
    "PineLexError",
    "PineParseError",
    "PineRuntimeError",
    "PineUnsupportedError",
    "SignalResult",
    "SourceSpan",
    "parse_and_run",
]
