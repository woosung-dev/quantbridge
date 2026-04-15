"""__init__.py (parse_and_run) 누락 브랜치 커버리지 보강.

누락 경로:
- 62-63: normalize 단계에서 PineUnsupportedError (v4 security 호출)
- 73-74: tokenize 단계에서 PineError (정규화 후 렉스 에러)
- 85: parse 단계에서 PineUnsupportedError (while 루프)
- 129-130: execute_program 단계에서 PineError (런타임 에러)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine import parse_and_run


def _ohlcv(n: int = 10) -> pd.DataFrame:
    close = pd.Series(np.linspace(10.0, 20.0, n))
    return pd.DataFrame({
        "open": close - 0.1,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": [100.0] * n,
    })


# ---------------------------------------------------------------------------
# lines 62-63: normalize 단계 PineUnsupportedError
# v4에서 security() 호출은 normalize() 안에서 PineUnsupportedError를 던진다
# ---------------------------------------------------------------------------


def test_v4_security_returns_unsupported_at_normalize_stage():
    """v4 security() → normalize 단계에서 즉시 Unsupported."""
    src = """//@version=4
strategy("X")
x = security(tickerid, "D", close)
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "unsupported"
    assert outcome.error is not None
    assert outcome.source_version == "v4"


# ---------------------------------------------------------------------------
# lines 73-74: tokenize 단계 PineError (정규화는 통과하지만 렉서가 에러)
# v5에서 렉서 에러 유발: 알 수 없는 문자 사용
# ---------------------------------------------------------------------------


def test_lex_error_returns_error_status():
    """렉서 에러 → error 상태 반환."""
    # $ 는 Pine Script에서 유효하지 않은 문자
    src = "//@version=5\nx = $100\n"
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "error"
    assert outcome.error is not None


# ---------------------------------------------------------------------------
# line 85: parse 단계 PineUnsupportedError
# while 루프는 파서에서 PineUnsupportedError를 던진다
# ---------------------------------------------------------------------------


def test_while_loop_returns_unsupported_at_parse_stage():
    """while 루프 → 파서 단계에서 PineUnsupportedError."""
    src = """//@version=5
strategy("X")
i = 0
while i < 5
    i := i + 1
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "unsupported"
    assert outcome.error is not None


# ---------------------------------------------------------------------------
# lines 129-130: execute_program 단계 PineError (runtime error)
# 정의되지 않은 변수 참조 → PineRuntimeError
# ---------------------------------------------------------------------------


def test_undefined_variable_returns_error_at_runtime_stage():
    """undefined identifier → runtime PineError."""
    src = """//@version=5
strategy("X")
x = undefined_variable_xyz + 1
"""
    outcome = parse_and_run(src, _ohlcv())
    assert outcome.status == "error"
    assert outcome.error is not None
