# 라이브 세션의 조건부 진입 차단 판정기를 검증한다.
"""BL-478 — 라이브 세션의 조건부 진입 차단 판정기 회귀 방어.

`strategy.entry(..., stop=)` 는 `strategy_state.py:598-609` 에서 `PendingOrder` 만
파킹하고 이벤트를 발행하지 않으며, 조건부 주문을 거래소에 등재하는 코드는 없다.
따라서 해당 전략은 라이브 세션을 시작하지 못하게 막아야 하고, 이 판정기가 그
게이트의 유일한 근거다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pynescript.ast.error import SyntaxError as PineSyntaxError

from src.strategy.pine_v2.ast_extractor import uses_stop_entry

_REPO_ROOT = Path(__file__).parents[5]
_CORPUS_DIR = _REPO_ROOT / "apps/api/tests/fixtures/pine_corpus_v2"
_EMA_CROSSOVER = _REPO_ROOT / "apps/web/public/samples/ema-crossover.pine"


# 아래 코퍼스 표는 사람이 `grep -c 'stop='`로 검산할 수 있어 파서만으로 증명하는 순환을 막는다.
@pytest.mark.parametrize(
    ("source_path", "expected"),
    [
        (_CORPUS_DIR / "s1_pbr.pine", True),
        (_CORPUS_DIR / "s2_utbot.pine", False),
        (_CORPUS_DIR / "s3_rsid.pine", False),
        (_CORPUS_DIR / "s4_hma_curvature.pine", False),
        (_EMA_CROSSOVER, False),
    ],
)
def test_uses_stop_entry_matches_corpus(source_path: Path, expected: bool) -> None:
    """실제 전략 코퍼스의 조건부 진입 여부를 고정한다."""
    assert uses_stop_entry(source_path.read_text()) is expected


def test_uses_stop_entry_ignores_literal_na_stop() -> None:
    """리터럴 `na` stop은 런타임에서 시장가 처리되므로 차단하지 않는다."""
    source = '''//@version=5
strategy("literal na")
strategy.entry("L", strategy.long, stop=na)
'''
    assert uses_stop_entry(source) is False


def test_uses_stop_entry_ignores_exit_stop() -> None:
    """exit stop은 이미 브래킷으로 발주되므로 진입 stop 차단 대상이 아니다."""
    source = '''//@version=5
strategy("exit stop")
strategy.entry("L", strategy.long)
strategy.exit("X", from_entry="L", stop=95)
'''
    assert uses_stop_entry(source) is False


def test_uses_stop_entry_blocks_variable_stop() -> None:
    """변수 stop은 정적으로 na인지 알 수 없어 과잉 차단을 알고 선택한다."""
    source = '''//@version=5
strategy("variable stop")
v = high
strategy.entry("L", strategy.long, stop=v)
'''
    assert uses_stop_entry(source) is True


def test_uses_stop_entry_ignores_strategy_without_entry() -> None:
    """기존 register 테스트의 `_make_strategy` 소스는 게이트에 걸리지 않는다."""
    assert uses_stop_entry("//@version=5\nstrategy('t')") is False


def test_uses_stop_entry_ignores_indicator() -> None:
    """indicator 선언은 strategy 진입이 아니므로 차단하지 않는다."""
    assert uses_stop_entry("//@version=5\nindicator('i')") is False


def test_uses_stop_entry_blocks_when_one_of_two_entries_has_stop() -> None:
    """진입 하나라도 조건부면 부분 실행을 금지하는 ADR-003 정신으로 차단한다."""
    source = '''//@version=5
strategy("partial stop")
strategy.entry("L", strategy.long)
strategy.entry("S", strategy.short, stop=95)
'''
    assert uses_stop_entry(source) is True


def test_uses_stop_entry_propagates_syntax_error() -> None:
    """파싱 오류는 호출자가 backstop을 둘 수 있도록 파서 SyntaxError로 전파한다."""
    with pytest.raises(PineSyntaxError):
        uses_stop_entry("//@version=5\nstrategy('t'")


def test_uses_stop_entry_ignores_stop_in_comment() -> None:
    """주석 속 stop 표기는 AST 진입 인자가 아니므로 현재 동작상 무시한다."""
    source = '''//@version=5
strategy("comment")
// strategy.entry("L", strategy.long, stop=95)
'''
    assert uses_stop_entry(source) is False


def test_uses_stop_entry_ignores_stop_in_string_literal() -> None:
    """문자열 리터럴의 stop 표기는 진입 인자가 아니므로 현재 동작상 무시한다."""
    source = '''//@version=5
strategy("stop=")
strategy.entry("L", strategy.long)
'''
    assert uses_stop_entry(source) is False
