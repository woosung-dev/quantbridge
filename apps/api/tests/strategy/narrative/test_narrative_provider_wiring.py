"""[ADR-040] 해설 층 provider 배선 — **스키마 강제**와 **예외 문자열 미반사**.

★`convert/service.py` 는 `tools=`/`response_schema=` 가 **0건**이고 응답을 문자열로 수동 파싱한다
(Gemini 는 ``` 펜스를 손으로 벗긴다). 브리핑은 JSON 이어야 하므로 SDK 가 형식을 지키게 만들었고,
이 파일이 **그 인자가 실제로 실려 나가는지**를 잰다 — 프롬프트로 부탁하는 것과 스키마로 강제하는
것은 다르고, 인자가 빠지면 조용히 전자로 돌아간다.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from src.strategy.narrative.service import _TOOL_NAME, NarrativeService

_PAYLOAD = {"summary": "요약", "style": "breakout", "assumptions": [], "risks": []}
SOURCE = '//@version=5\nstrategy("T")\nx = 1\n'
FACTS: dict[str, Any] = {"inputs": []}


def _settings(*, anthropic: str | None, gemini: str | None) -> Any:
    return SimpleNamespace(
        anthropic_api_key=SecretStr(anthropic) if anthropic else None,
        gemini_api_key=SecretStr(gemini) if gemini else None,
        anthropic_model="claude-sonnet-4-6",
        gemini_model="gemini-2.0-flash",
    )


def test_anthropic_call_forces_the_tool_schema(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    class _Messages:
        def create(self, **kwargs: Any) -> Any:
            captured.update(kwargs)
            block = SimpleNamespace(type="tool_use", name=_TOOL_NAME, input=_PAYLOAD)
            return SimpleNamespace(content=[block])

    monkeypatch.setattr(
        "src.strategy.narrative.service.anthropic.Anthropic",
        lambda api_key: SimpleNamespace(messages=_Messages()),
    )

    svc = NarrativeService(_settings(anthropic="k", gemini=None))
    out = svc.explain(source=SOURCE, facts=FACTS, source_hash="h" * 64)

    assert out.provider == "anthropic"
    assert out.summary == "요약"
    # ★스키마 강제 — 이 둘이 빠지면 조용히 「프롬프트로 부탁하기」로 돌아간다.
    assert captured["tools"][0]["name"] == _TOOL_NAME
    assert captured["tool_choice"] == {"type": "tool", "name": _TOOL_NAME}
    assert captured["tools"][0]["input_schema"]["required"] == [
        "summary",
        "style",
        "assumptions",
        "risks",
    ]


def test_gemini_call_forces_response_schema(monkeypatch: pytest.MonkeyPatch):
    import json

    captured: dict[str, Any] = {}

    class _Models:
        def generate_content(self, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return SimpleNamespace(text=json.dumps(_PAYLOAD))

    monkeypatch.setattr(
        "src.strategy.narrative.service.genai.Client",
        lambda api_key: SimpleNamespace(models=_Models()),
    )

    svc = NarrativeService(_settings(anthropic=None, gemini="k"))
    out = svc.explain(source=SOURCE, facts=FACTS, source_hash="h" * 64)

    assert out.provider == "gemini"
    config = captured["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is not None


def test_anthropic_failure_falls_back_to_gemini_without_leaking_sdk_strings(
    monkeypatch: pytest.MonkeyPatch,
):
    """★[BL-772] 계약 — 엔드포인트·모델·요청 ID 가 예외 문자열로 새면 안 된다."""
    import json

    leak = "https://api.anthropic.com/v1/messages request_id=req_LEAK"

    class _Messages:
        def create(self, **kwargs: Any) -> Any:
            raise RuntimeError(leak)

    class _Models:
        def generate_content(self, **kwargs: Any) -> Any:
            return SimpleNamespace(text=json.dumps(_PAYLOAD))

    monkeypatch.setattr(
        "src.strategy.narrative.service.anthropic.Anthropic",
        lambda api_key: SimpleNamespace(messages=_Messages()),
    )
    monkeypatch.setattr(
        "src.strategy.narrative.service.genai.Client",
        lambda api_key: SimpleNamespace(models=_Models()),
    )

    svc = NarrativeService(_settings(anthropic="k", gemini="g"))
    out = svc.explain(source=SOURCE, facts=FACTS, source_hash="h" * 64)

    assert out.provider == "gemini"
    assert leak not in out.model_dump_json()


def test_no_key_at_all_is_a_runtime_error_not_a_crash():
    svc = NarrativeService(_settings(anthropic=None, gemini=None))
    with pytest.raises(RuntimeError, match="필요합니다"):
        svc.explain(source=SOURCE, facts=FACTS, source_hash="h" * 64)


def test_anthropic_without_tool_use_block_is_a_failure_not_an_empty_narrative(
    monkeypatch: pytest.MonkeyPatch,
):
    """★도구 응답이 안 오면 **실패**다. 빈 해설을 성공으로 내면 화면이 침묵으로 거짓말한다."""

    class _Messages:
        def create(self, **kwargs: Any) -> Any:
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="설명드리자면...")])

    monkeypatch.setattr(
        "src.strategy.narrative.service.anthropic.Anthropic",
        lambda api_key: SimpleNamespace(messages=_Messages()),
    )
    svc = NarrativeService(_settings(anthropic="k", gemini=None))
    with pytest.raises(RuntimeError):
        svc.explain(source=SOURCE, facts=FACTS, source_hash="h" * 64)
