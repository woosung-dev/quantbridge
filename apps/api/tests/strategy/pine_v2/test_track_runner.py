# pine_v2 — TrackRunner registry 단위 테스트 (BL-201)
"""Sprint 48 BL-201 — Track S/A/M dispatcher 통합 검증.

`TrackRunner._dispatch_table` 가 event_loop.run_historical / virtual_strategy.run_virtual_strategy
와 object identity 일치하는지 (`is` 비교) + invoke() 가 4 invariants 를 보존하는지 검증.

4 invariants:
  1. D2 sizing params forward (initial_capital / default_qty_type / default_qty_value)
  2. sessions_allowed forward
  3. V2RunResult shape (track / historical / virtual)
  4. unknown track 시 ValueError + compat.py 형식 메시지
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.strategy.pine_v2 import event_loop, virtual_strategy
from src.strategy.pine_v2.compat import V2RunResult
from src.strategy.pine_v2.track_runner import TrackRunner


def _ohlcv(n: int = 5) -> pd.DataFrame:
    closes = [10.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * n,
        }
    )


def test_track_s_dispatches_to_run_historical(monkeypatch: pytest.MonkeyPatch) -> None:
    """Track S → run_historical 호출 확인 (kwargs 전부 forward)."""
    captured: dict[str, object] = {}

    def _spy_run_historical(source: str, ohlcv: pd.DataFrame, **kwargs: object) -> object:
        captured["source"] = source
        captured["kwargs"] = kwargs
        return "HIST_S"

    # TrackRunner 의 dispatch table 에 직접 spy 주입 (event_loop 모듈 자체는 보존).
    monkeypatch.setitem(TrackRunner._dispatch_table, "S", _spy_run_historical)

    result = TrackRunner.invoke(
        "S",
        source="src",
        ohlcv=_ohlcv(),
        strict=True,
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=10.0,
        sessions_allowed=("asia",),
    )

    assert isinstance(result, V2RunResult)
    assert result.track == "S"
    assert result.historical == "HIST_S"
    assert result.virtual is None
    assert captured["source"] == "src"
    assert captured["kwargs"]["initial_capital"] == 10000.0
    assert captured["kwargs"]["default_qty_type"] == "strategy.percent_of_equity"
    assert captured["kwargs"]["default_qty_value"] == 10.0
    assert captured["kwargs"]["sessions_allowed"] == ("asia",)
    assert captured["kwargs"]["strict"] is True


def test_track_a_dispatches_to_run_virtual_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Track A → run_virtual_strategy 호출 확인."""
    captured: dict[str, object] = {}

    def _spy_virtual(source: str, ohlcv: pd.DataFrame, **kwargs: object) -> object:
        captured["source"] = source
        captured["kwargs"] = kwargs
        return "VIRT_A"

    monkeypatch.setitem(TrackRunner._dispatch_table, "A", _spy_virtual)

    result = TrackRunner.invoke(
        "A",
        source="src",
        ohlcv=_ohlcv(),
        strict=False,
        initial_capital=5000.0,
        default_qty_type="strategy.cash",
        default_qty_value=100.0,
        sessions_allowed=(),
    )

    assert result.track == "A"
    assert result.virtual == "VIRT_A"
    assert result.historical is None
    assert captured["kwargs"]["initial_capital"] == 5000.0
    assert captured["kwargs"]["default_qty_type"] == "strategy.cash"
    assert captured["kwargs"]["strict"] is False


def test_track_m_dispatches_to_run_historical(monkeypatch: pytest.MonkeyPatch) -> None:
    """Track M → run_historical 호출 확인 (S 와 같은 함수, 다른 dispatch entry)."""
    calls: list[str] = []

    def _spy_run_historical(source: str, ohlcv: pd.DataFrame, **kwargs: object) -> str:
        calls.append("M")
        return "HIST_M"

    monkeypatch.setitem(TrackRunner._dispatch_table, "M", _spy_run_historical)

    result = TrackRunner.invoke(
        "M",
        source="src",
        ohlcv=_ohlcv(),
        strict=True,
        initial_capital=None,
        default_qty_type=None,
        default_qty_value=None,
        sessions_allowed=(),
    )

    assert calls == ["M"]
    assert result.track == "M"
    assert result.historical == "HIST_M"
    assert result.virtual is None


def test_unknown_track_raises_value_error() -> None:
    """unknown track → ValueError + compat.py:137 형식 메시지 보존."""
    with pytest.raises(ValueError) as exc_info:
        TrackRunner.invoke(
            "X",  # type: ignore[arg-type]
            source="src",
            ohlcv=_ohlcv(),
            strict=True,
        )

    msg = str(exc_info.value)
    assert "unknown script track" in msg
    assert "X" in msg


def test_dispatch_table_identity_preserved() -> None:
    """invariant: _dispatch_table 4 entry 가 실제 runner 함수와 object identity 동일.

    BL-200 SSOT 패턴 (`is` 비교) 동일 적용 — re-bind drift 차단.
    """
    assert TrackRunner._dispatch_table["S"] is event_loop.run_historical
    assert TrackRunner._dispatch_table["M"] is event_loop.run_historical
    assert TrackRunner._dispatch_table["A"] is virtual_strategy.run_virtual_strategy
    # S 와 M 은 같은 함수를 가리킴 (compat.py 의 두 분기 모두 run_historical)
    assert TrackRunner._dispatch_table["S"] is TrackRunner._dispatch_table["M"]
