"""ConvertService 단위 테스트 — LLM 호출 mocking."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import Settings
from src.strategy.convert.schemas import ConvertIndicatorRequest


@pytest.fixture()
def settings_with_key() -> Settings:
    return Settings(anthropic_api_key="sk-ant-test-key")  # type: ignore[arg-type]


@pytest.fixture()
def settings_no_key() -> Settings:
    return Settings(anthropic_api_key=None)


_SIMPLE_INDICATOR = """\
//@version=5
indicator("Test")
bull = ta.crossover(close, ta.sma(close, 20))
plotshape(bull, "Buy")
"""

_FAKE_STRATEGY = (
    '//@version=5\nstrategy("Test")\n'
    "bull = ta.crossover(close, ta.sma(close, 20))\n"
    'strategy.entry("Long", strategy.long, when=bull)'
)


def test_convert_raises_when_no_api_key(settings_no_key: Settings) -> None:
    from src.strategy.convert.service import ConvertService

    svc = ConvertService(settings_no_key)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        svc.convert(ConvertIndicatorRequest(code=_SIMPLE_INDICATOR))


def test_convert_full_mode_calls_llm(settings_with_key: Settings) -> None:
    from src.strategy.convert.service import ConvertService

    fake_msg = SimpleNamespace(
        content=[SimpleNamespace(text=_FAKE_STRATEGY)],
        usage=SimpleNamespace(input_tokens=50, output_tokens=30),
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake_msg

    svc = ConvertService(settings_with_key)
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = svc.convert(ConvertIndicatorRequest(code=_SIMPLE_INDICATOR, mode="full"))

    assert result.converted_code == _FAKE_STRATEGY
    assert result.input_tokens == 50
    assert result.output_tokens == 30
    assert result.sliced_from is None  # full 모드는 슬라이싱 없음


def test_convert_sliced_mode_skips_llm_when_runnable(settings_with_key: Settings) -> None:
    from src.strategy.convert.service import ConvertService

    # _SIMPLE_INDICATOR has no unsupported functions → C-ast slicing produces runnable code
    # → should NOT call LLM at all
    mock_client = MagicMock()

    svc = ConvertService(settings_with_key)
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = svc.convert(ConvertIndicatorRequest(code=_SIMPLE_INDICATOR, mode="sliced"))

    # LLM should NOT have been called (runnable after slicing)
    mock_client.messages.create.assert_not_called()
    assert result.input_tokens == 0  # no LLM call
    assert result.sliced_from is not None
    assert result.sliced_to is not None
