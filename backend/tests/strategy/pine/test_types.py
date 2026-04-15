"""SourceSpan, SignalResult, ParseOutcome 타입 테스트."""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine.types import ParseOutcome, SignalResult, SourceSpan

# ── SourceSpan ────────────────────────────────────────────────────────────────

def test_source_span_fields() -> None:
    """SourceSpan이 line/column/length 필드를 올바르게 저장한다."""
    span = SourceSpan(line=3, column=7, length=5)
    assert span.line == 3
    assert span.column == 7
    assert span.length == 5


def test_source_span_is_frozen() -> None:
    """SourceSpan은 frozen dataclass여야 한다."""
    span = SourceSpan(line=1, column=0, length=10)
    with pytest.raises(Exception):
        span.line = 99  # type: ignore[misc]


# ── SignalResult ──────────────────────────────────────────────────────────────

def test_signal_result_required_fields() -> None:
    """SignalResult은 entries/exits pd.Series를 받는다."""
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    entries = pd.Series([True, False, False], index=idx)
    exits = pd.Series([False, True, False], index=idx)

    result = SignalResult(entries=entries, exits=exits)

    pd.testing.assert_series_equal(result.entries, entries)
    pd.testing.assert_series_equal(result.exits, exits)


def test_signal_result_optional_fields_default_none() -> None:
    """sprint 1에서 vectorbt 전용 선택 필드는 모두 None이어야 한다."""
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    result = SignalResult(
        entries=pd.Series([True, False], index=idx),
        exits=pd.Series([False, True], index=idx),
    )
    assert result.direction is None
    assert result.sl_stop is None
    assert result.tp_limit is None
    assert result.position_size is None
    assert result.metadata == {}


# ── ParseOutcome ──────────────────────────────────────────────────────────────

def test_parse_outcome_ok() -> None:
    """status='ok'일 때 result가 채워지고 error는 None이다."""
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    signals = SignalResult(
        entries=pd.Series([True, False], index=idx),
        exits=pd.Series([False, True], index=idx),
    )
    outcome = ParseOutcome(
        status="ok",
        source_version="v5",
        result=signals,
    )
    assert outcome.status == "ok"
    assert outcome.result is signals
    # signals 프로퍼티는 result의 하위 호환 별칭
    assert outcome.signals is signals
    assert outcome.error is None


def test_parse_outcome_unsupported() -> None:
    """status='unsupported'일 때 signals는 None이고 error가 설정된다."""
    from src.strategy.pine.errors import PineUnsupportedError

    err = PineUnsupportedError(
        "barssince() is not supported",
        feature="barssince",
        category="function",
    )
    outcome = ParseOutcome(
        status="unsupported",
        source_version="v4",
        error=err,
    )
    assert outcome.status == "unsupported"
    assert outcome.result is None
    assert outcome.signals is None
    assert outcome.error is err
