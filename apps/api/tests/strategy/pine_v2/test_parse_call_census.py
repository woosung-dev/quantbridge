"""pine_v2 백테스트 한 번의 pynescript 파스 호출 수를 고정한다."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

import pytest
from pynescript import ast as pyne_ast

from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.ast_classifier import classify_script
from tests.strategy.pine_v2.test_execution_speed import _CORPUS_DIR, _load_frozen_ohlcv

_EXPECTED_TRACK_S_PARSES = 4  # step1 에서 1 로 바뀐다
_EXPECTED_TRACK_A_PARSES = 5  # step1 에서 1 로 바뀐다
_DIRECT_PARSE_CALLS = 3
_TRACK_S_CORPUS_ID = "s5_ema_trend"


def _load_source(corpus_id: str) -> str:
    return (_CORPUS_DIR / f"{corpus_id}.pine").read_text(encoding="utf-8")


def _track_a_corpus() -> tuple[str, str]:
    """indicator corpus 중 alert를 실제 분류 결과로 찾아 반환한다."""
    for path in sorted(_CORPUS_DIR.glob("i*.pine")):
        source = path.read_text(encoding="utf-8")
        if classify_script(source).track == "A":
            return path.stem, source
    raise AssertionError("Track A인 i*.pine corpus가 없습니다")


def _install_parse_census(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, int]]:
    calls: list[tuple[str, int]] = []
    original_parse: Callable[..., Any] = pyne_ast.parse

    def wrapper(source: str, *args: Any, **kwargs: Any) -> Any:
        calls.append((hashlib.sha1(source.encode()).hexdigest(), len(source)))
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr("pynescript.ast.parse", wrapper)
    return calls


def _assert_single_source_parse_count(
    calls: list[tuple[str, int]], source: str, expected_count: int
) -> None:
    expected_call = (hashlib.sha1(source.encode()).hexdigest(), len(source))
    assert len(calls) == expected_count
    assert set(calls) == {expected_call}


def test_run_backtest_v2_track_s_parse_call_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Track S 백테스트 한 번은 동일 source를 현재 네 번 파싱한다."""
    source = _load_source(_TRACK_S_CORPUS_ID)
    assert classify_script(source).track == "S"
    calls = _install_parse_census(monkeypatch)

    outcome = run_backtest_v2(source, _load_frozen_ohlcv())

    assert outcome.status == "ok" and outcome.result is not None
    _assert_single_source_parse_count(calls, source, _EXPECTED_TRACK_S_PARSES)


def test_run_backtest_v2_track_a_parse_call_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Track A 백테스트 한 번은 alert hook 경로를 포함해 현재 다섯 번 파싱한다."""
    corpus_id, source = _track_a_corpus()
    assert classify_script(source).track == "A", f"{corpus_id}는 Track A여야 합니다"
    calls = _install_parse_census(monkeypatch)

    outcome = run_backtest_v2(source, _load_frozen_ohlcv())

    assert outcome.status == "ok" and outcome.result is not None
    _assert_single_source_parse_count(calls, source, _EXPECTED_TRACK_A_PARSES)


def test_parse_census_counts_direct_parse_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """양성 대조: wrapper가 캐시와 무관하게 직접 parse 호출을 모두 센다."""
    calls = _install_parse_census(monkeypatch)
    source = _load_source(_TRACK_S_CORPUS_ID)

    for _ in range(_DIRECT_PARSE_CALLS):
        pyne_ast.parse(source)

    _assert_single_source_parse_count(calls, source, _DIRECT_PARSE_CALLS)


def test_parse_census_starts_at_zero_without_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    """음성 대조: parse를 호출하지 않으면 계수는 0이다."""
    calls = _install_parse_census(monkeypatch)

    assert calls == []
