"""pine_v2 백테스트 한 번의 pynescript 파스 호출 수를 고정한다."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

import pytest
from pynescript import ast as pyne_ast
from pynescript.ast.error import SyntaxError as PyneSyntaxError

from src.backtest.engine.v2_adapter import run_backtest_v2
from src.strategy.pine_v2.ast_classifier import classify_script
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from tests.strategy.pine_v2.test_execution_speed import _CORPUS_DIR, _load_frozen_ohlcv

_EXPECTED_TRACK_S_PARSES = 1
_EXPECTED_TRACK_A_PARSES = 1
_DIRECT_PARSE_CALLS = 3
_TRACK_S_CORPUS_ID = "s5_ema_trend"
_SYNTAX_ERROR_SOURCE = '//@version=5\nindicator("x"\n  ['


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
    parse_to_ast.cache_clear()
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
    """Track S 백테스트 한 번은 동일 source를 한 번만 파싱한다."""
    source = _load_source(_TRACK_S_CORPUS_ID)
    assert classify_script(source).track == "S"
    calls = _install_parse_census(monkeypatch)

    outcome = run_backtest_v2(source, _load_frozen_ohlcv())

    assert outcome.status == "ok" and outcome.result is not None
    _assert_single_source_parse_count(calls, source, _EXPECTED_TRACK_S_PARSES)


def test_run_backtest_v2_track_a_parse_call_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Track A 백테스트는 alert hook 경로를 포함해도 한 번만 파싱한다."""
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


def test_parse_census_cache_miss_for_changed_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """양성 대조: source가 달라지면 캐시가 아닌 새 파스가 실행된다."""
    source = _load_source(_TRACK_S_CORPUS_ID)
    calls = _install_parse_census(monkeypatch)

    first = run_backtest_v2(source, _load_frozen_ohlcv())
    first_count = len(calls)
    second_source = f"{source}\n"
    second = run_backtest_v2(second_source, _load_frozen_ohlcv())

    assert first.status == "ok" and first.result is not None
    assert second.status == "ok" and second.result is not None
    assert first_count == _EXPECTED_TRACK_S_PARSES
    assert len(calls) == first_count + 1
    assert calls[-1] == (hashlib.sha1(second_source.encode()).hexdigest(), len(second_source))


def test_parse_census_does_not_cache_syntax_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """음성 대조: 파싱 예외는 캐시하지 않아 같은 source도 매번 파싱한다."""
    calls = _install_parse_census(monkeypatch)

    with pytest.raises(PyneSyntaxError):
        parse_to_ast(_SYNTAX_ERROR_SOURCE)
    with pytest.raises(PyneSyntaxError):
        parse_to_ast(_SYNTAX_ERROR_SOURCE)

    _assert_single_source_parse_count(calls, _SYNTAX_ERROR_SOURCE, 2)
