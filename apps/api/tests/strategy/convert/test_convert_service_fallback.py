"""ConvertService의 Gemini fallback과 응답 경계 회귀 테스트."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import pytest
from pydantic import SecretStr
from tenacity import Future, RetryError

from src.core.config import Settings
from src.strategy.convert.prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.convert.schemas import ConvertIndicatorRequest
from src.strategy.convert.service import ConvertService

_SOURCE_CODE = '//@version=5\nindicator("Source")\nplot(close)'
_CONVERTED_CODE = '//@version=5\nstrategy("Converted")\nstrategy.entry("Long", strategy.long)'
_LEAK_MARKERS = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash",
    "model=gemini-2.0-flash",
    "request_id=req_0xDEADBEEF",
)


def _settings(*, anthropic_key: bool = False, gemini_key: bool = False) -> Settings:
    return Settings(
        anthropic_api_key=SecretStr("sk-ant-test") if anthropic_key else None,
        gemini_api_key=SecretStr("gemini-test") if gemini_key else None,
    )


def _gemini_response(
    text: str = _CONVERTED_CODE,
    *,
    usage: object | None = SimpleNamespace(prompt_token_count=11, candidates_token_count=7),
) -> SimpleNamespace:
    return SimpleNamespace(text=text, usage_metadata=usage)


def _gemini_client(response: object | None = None, *, error: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if error is not None:
        client.models.generate_content.side_effect = error
    else:
        client.models.generate_content.return_value = response
    return client


def _anthropic_client(*, error: Exception) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = error
    return client


def test_gemini_failure_hides_sdk_exception_message() -> None:
    """[BL-772] Gemini SDK 상세가 RuntimeError 응답 메시지로 반사되지 않는다."""
    sdk_error = RuntimeError(" ".join(_LEAK_MARKERS))
    client = _gemini_client(error=sdk_error)
    service = ConvertService(_settings(gemini_key=True))

    with (
        patch("src.strategy.convert.service.genai.Client", return_value=client),
        pytest.raises(RuntimeError, match=r"^Gemini 변환 실패$") as raised,
    ):
        service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert raised.value.__cause__ is sdk_error
    for marker in _LEAK_MARKERS:
        assert marker not in str(raised.value)


def test_anthropic_failure_gemini_success_warning_hides_sdk_exception_message() -> None:
    """[BL-772] 성공한 fallback의 warnings에는 provider 상태만 남긴다."""
    sdk_error = RuntimeError(" ".join(_LEAK_MARKERS))
    anthropic_client = _anthropic_client(error=sdk_error)
    gemini_client = _gemini_client(_gemini_response())
    service = ConvertService(_settings(anthropic_key=True, gemini_key=True))

    with (
        patch("src.strategy.convert.service.anthropic.Anthropic", return_value=anthropic_client),
        patch("src.strategy.convert.service.genai.Client", return_value=gemini_client),
    ):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert result.warnings == [
        f"Gemini {service._settings.gemini_model} 로 변환 완료 (fallback)",
        "Anthropic 실패 → Gemini fallback",
    ]
    for marker in _LEAK_MARKERS:
        assert marker not in " ".join(result.warnings)


def test_both_provider_failures_have_distinct_message() -> None:
    """Anthropic 실패 뒤 Gemini도 실패하면 양쪽 실패 메시지를 낸다."""
    anthropic_client = _anthropic_client(error=RuntimeError("anthropic unavailable"))
    gemini_client = _gemini_client(error=RuntimeError("gemini unavailable"))
    service = ConvertService(_settings(anthropic_key=True, gemini_key=True))

    with (
        patch("src.strategy.convert.service.anthropic.Anthropic", return_value=anthropic_client),
        patch("src.strategy.convert.service.genai.Client", return_value=gemini_client),
        pytest.raises(RuntimeError, match=r"^양쪽 provider 모두 실패$") as raised,
    ):
        service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert isinstance(raised.value.__cause__, RuntimeError)


def test_gemini_only_failure_has_gemini_message() -> None:
    """Gemini 단독 구성의 실패는 양쪽 실패와 구분한다."""
    service = ConvertService(_settings(gemini_key=True))
    gemini_client = _gemini_client(error=RuntimeError("gemini unavailable"))

    with (
        patch("src.strategy.convert.service.genai.Client", return_value=gemini_client),
        pytest.raises(RuntimeError, match=r"^Gemini 변환 실패$") as raised,
    ):
        service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert str(raised.value) != "양쪽 provider 모두 실패"


def test_anthropic_only_failure_has_no_fallback_message() -> None:
    """Anthropic 단독 구성은 Gemini fallback 미설정을 명시한다."""
    service = ConvertService(_settings(anthropic_key=True))
    anthropic_client = _anthropic_client(error=RuntimeError("anthropic unavailable"))

    with (
        patch("src.strategy.convert.service.anthropic.Anthropic", return_value=anthropic_client),
        pytest.raises(RuntimeError, match=r"^Anthropic 변환 실패 \(Gemini fallback 미설정\)$"),
    ):
        service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))


def test_no_provider_key_does_not_create_llm_clients() -> None:
    """키가 없으면 어떤 provider client도 생성하지 않는다."""
    service = ConvertService(_settings())

    with (
        patch("src.strategy.convert.service.anthropic.Anthropic") as anthropic_constructor,
        patch("src.strategy.convert.service.genai.Client") as gemini_constructor,
        pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY 또는 GEMINI_API_KEY"),
    ):
        service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    anthropic_constructor.assert_not_called()
    gemini_constructor.assert_not_called()


def test_gemini_success_passes_shared_prompt_and_template() -> None:
    """Gemini fallback은 공용 system prompt와 user template을 전달한다."""
    service = ConvertService(_settings(gemini_key=True))
    client = _gemini_client(_gemini_response())

    with patch("src.strategy.convert.service.genai.Client", return_value=client):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert result.converted_code == _CONVERTED_CODE
    assert result.warnings[0] == f"Gemini {service._settings.gemini_model} 로 변환 완료 (fallback)"
    client.models.generate_content.assert_called_once()
    call = client.models.generate_content.call_args
    assert call.kwargs["model"] == service._settings.gemini_model
    assert call.kwargs["contents"] == USER_TEMPLATE.format(code=_SOURCE_CODE)
    assert call.kwargs["config"].system_instruction == SYSTEM_PROMPT


@pytest.mark.parametrize(
    ("response_text", "expected_code"),
    [
        ('```pine\n//@version=5\nstrategy("Fence")\n```', '//@version=5\nstrategy("Fence")'),
        ('```pine\n//@version=5\nstrategy("Open only")', '//@version=5\nstrategy("Open only")'),
    ],
)
def test_gemini_code_fence_removal(response_text: str, expected_code: str) -> None:
    """닫는 fence 유무와 관계없이 여는 Gemini 코드 fence를 제거한다."""
    service = ConvertService(_settings(gemini_key=True))
    client = _gemini_client(_gemini_response(response_text))

    with patch("src.strategy.convert.service.genai.Client", return_value=client):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert result.converted_code == expected_code


@pytest.mark.parametrize(
    "usage",
    [None, SimpleNamespace(prompt_token_count=None, candidates_token_count=None)],
)
def test_gemini_missing_usage_values_become_zero(usage: object | None) -> None:
    """Gemini usage metadata와 개별 토큰 값의 None을 0으로 정규화한다."""
    service = ConvertService(_settings(gemini_key=True))
    client = _gemini_client(_gemini_response(usage=usage))

    with patch("src.strategy.convert.service.genai.Client", return_value=client):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert (result.input_tokens, result.output_tokens) == (0, 0)


def test_empty_quality_warning_returns_early() -> None:
    """빈 결과는 뒤의 드로잉 흔적 검사를 생략하고 단일 경고만 낸다."""

    class _BlankResultWithDrawingTrace(str):
        def strip(self, chars: str | None = None) -> str:
            return ""

        def __contains__(self, item: object) -> bool:
            return item == "plotshape"

    warnings = ConvertService._heuristic_quality_warnings(
        _SOURCE_CODE, _BlankResultWithDrawingTrace("plotshape(close)")
    )

    assert warnings == ["⚠️ 변환 결과가 비어있습니다. provider 응답 형식 확인 필요."]


def test_quality_warning_lists_all_leftover_patterns() -> None:
    """여러 미지원/그리기 흔적은 한 경고에서 모두 나열한다."""
    warnings = ConvertService._heuristic_quality_warnings(
        _SOURCE_CODE,
        'array.new_float()\nplotshape(close)\nalertcondition(close > open, "T")',
    )

    assert len(warnings) == 1
    assert "array., plotshape, alertcondition" in warnings[0]


def test_quality_warning_identity_requires_more_than_100_characters() -> None:
    """원본 동일 경고는 100자를 초과할 때만 낸다."""
    boundary = "x" * 100
    over_boundary = "x" * 101

    assert ConvertService._heuristic_quality_warnings(boundary, boundary) == []
    assert ConvertService._heuristic_quality_warnings(over_boundary, over_boundary) == [
        "⚠️ 변환 결과가 원본과 100% 동일합니다. LLM 이 변환을 거부했을 가능성."
    ]


def test_sliced_runnable_code_skips_both_llm_clients() -> None:
    """직접 실행 가능한 AST slice는 어느 provider도 호출하지 않는다."""
    extractor_result = SimpleNamespace(
        sliced_code='//@version=5\nstrategy("Runnable")',
        is_runnable=True,
        token_reduction_pct=42.5,
        removed_functions=[],
    )
    extractor = MagicMock()
    extractor.extract.return_value = extractor_result
    service = ConvertService(_settings(anthropic_key=True, gemini_key=True))

    with (
        patch("src.strategy.convert.service.SignalExtractor", return_value=extractor),
        patch("src.strategy.convert.service.anthropic.Anthropic") as anthropic_constructor,
        patch("src.strategy.convert.service.genai.Client") as gemini_constructor,
    ):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE, mode="sliced"))

    assert result.input_tokens == 0
    assert result.warnings == ["AST 슬라이싱으로 직접 실행 가능한 코드 추출 (LLM 미사용)"]
    anthropic_constructor.assert_not_called()
    gemini_constructor.assert_not_called()


class _ObservingAttempt(Future):
    """RetryError가 마지막 provider 예외를 읽는지 관측하는 tenacity Future."""

    def __init__(self, error: Exception) -> None:
        super().__init__(3)
        self._exception_calls = 0
        self.set_exception(error)

    def exception(self, timeout: float | None = None) -> BaseException | None:
        self._exception_calls += 1
        return super().exception(timeout)


@pytest.mark.parametrize(
    ("failure_kind", "provider_error"),
    [
        ("retry", RuntimeError("last transient error")),
        ("anthropic", anthropic.AnthropicError("permanent provider error")),
        ("unexpected", RuntimeError("unexpected provider error")),
    ],
)
def test_all_anthropic_failures_fall_back_to_gemini(
    failure_kind: str, provider_error: Exception
) -> None:
    """RetryError·AnthropicError·일반 예외 모두 Gemini fallback으로 이어진다."""
    observing_attempt: _ObservingAttempt | None = None
    if failure_kind == "retry":
        observing_attempt = _ObservingAttempt(provider_error)
        anthropic_error: Exception = RetryError(observing_attempt)
    else:
        anthropic_error = provider_error

    anthropic_client = _anthropic_client(error=anthropic_error)
    gemini_client = _gemini_client(_gemini_response())
    service = ConvertService(_settings(anthropic_key=True, gemini_key=True))

    with (
        patch("src.strategy.convert.service.anthropic.Anthropic", return_value=anthropic_client),
        patch("src.strategy.convert.service.genai.Client", return_value=gemini_client),
    ):
        result = service.convert(ConvertIndicatorRequest(code=_SOURCE_CODE))

    assert "Anthropic 실패 → Gemini fallback" in result.warnings
    gemini_client.models.generate_content.assert_called_once()
    if observing_attempt is not None:
        assert observing_attempt._exception_calls == 1
