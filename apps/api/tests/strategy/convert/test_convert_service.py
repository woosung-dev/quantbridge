"""ConvertService는 공통 structured provider contract만 소비한다."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.strategy.convert.schemas import ConvertIndicatorRequest
from src.strategy.convert.service import _CONVERT_SCHEMA, ConvertService
from src.strategy.narrative.providers import JsonCompletion

_SOURCE = '//@version=5\nindicator("Source")\nplot(close)'
_CONVERTED = '//@version=5\nstrategy("Converted")\nstrategy.entry("Long", strategy.long)'


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        llm_provider_order="openai,gemini",
        openai_model="gpt-test",
        gemini_model="gemini-test",
    )


def test_full_mode_uses_shared_structured_completion_and_actual_usage() -> None:
    service = ConvertService(_settings())
    completion = JsonCompletion(
        payload={"converted_code": _CONVERTED},
        provider="openai",
        input_tokens=50,
        output_tokens=30,
    )

    with patch("src.strategy.convert.service.complete_json", return_value=completion) as complete:
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE, mode="full"))

    assert result.converted_code == _CONVERTED
    assert (result.input_tokens, result.output_tokens) == (50, 30)
    assert result.warnings[0] == "openai gpt-test 로 변환 완료"
    assert "fallback" not in " ".join(result.warnings).lower()
    assert complete.call_args.kwargs["schema"] == _CONVERT_SCHEMA
    assert complete.call_args.kwargs["tool_name"] == "convert_indicator"


@pytest.mark.parametrize("payload", [{}, {"converted_code": ""}, {"converted_code": 1}])
def test_empty_or_malformed_structured_code_fails_closed(payload: dict[str, object]) -> None:
    service = ConvertService(_settings())
    completion = JsonCompletion(payload=payload, provider="gemini")

    with (
        patch("src.strategy.convert.service.complete_json", return_value=completion),
        pytest.raises(RuntimeError, match="변환 결과가 비어"),
    ):
        service.convert(ConvertIndicatorRequest(code=_SOURCE))


def test_sliced_runnable_code_skips_provider() -> None:
    service = ConvertService(_settings())
    extractor_result = SimpleNamespace(
        sliced_code='//@version=5\nstrategy("Runnable")',
        is_runnable=True,
        token_reduction_pct=42.5,
        removed_functions=[],
    )

    with (
        patch(
            "src.strategy.convert.service.SignalExtractor",
            return_value=SimpleNamespace(extract=lambda *_args, **_kwargs: extractor_result),
        ),
        patch("src.strategy.convert.service.complete_json") as complete,
    ):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE, mode="sliced"))

    complete.assert_not_called()
    assert result.input_tokens == result.output_tokens == 0
    assert result.warnings == ["AST 슬라이싱으로 직접 실행 가능한 코드 추출 (LLM 미사용)"]
