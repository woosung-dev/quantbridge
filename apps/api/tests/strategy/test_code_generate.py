"""무료 Gemini Python preview의 호출·검토·비밀·기존 저장 계약 경계."""

from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr, ValidationError

from src.auth.dependencies import get_current_user
from src.common.rate_limit import limiter
from src.core.config import Settings
from src.strategy.code_generate_prompt import (
    CODE_GENERATION_SCHEMA,
    MAX_OUTPUT_TOKENS,
    PUBLIC_CONTRACT,
    RISK_CONTRACT,
    TIMEOUT_SECONDS,
    build_generation_prompt,
)
from src.strategy.code_generate_service import CodeGenerateService
from src.strategy.code_schemas import GenerateCodeStrategyRequest, SaveCodeStrategyRequest
from src.strategy.dependencies import get_code_generate_service
from src.strategy.narrative.providers import JsonCompletion, ProviderCallError
from src.strategy.router import router

SOURCE = 'def on_bar(ctx, state):\n    return {"action": "hold"}\n'


def settings(order="gemini", *, key=True):
    return Settings.model_construct(
        llm_provider_order=order,
        gemini_api_key=SecretStr("test-secret-not-a-real-key") if key else None,
        gemini_model="requested-gemini-model",
    )


def completion(**changes):
    return JsonCompletion(
        **{
            "payload": {"source_code": SOURCE, "assumptions": ["신호는 완료 봉에서 계산합니다."]},
            "provider": "gemini",
            "actual_model": "reported-gemini-model",
            "input_tokens": 20,
            "output_tokens": 10,
            "thinking_tokens": 7,
            "total_tokens": 37,
            "usage_known": True,
            **changes,
        }
    )


def stub(monkeypatch, result):
    call = Mock(return_value=result)
    monkeypatch.setattr("src.strategy.code_generate_service.complete_json", call)
    return call


def test_preview_preserves_user_inputs_and_is_accepted_by_existing_save_contract(monkeypatch):
    call = stub(monkeypatch, completion())
    req = GenerateCodeStrategyRequest(
        prompt="SMA 교차 신호를 long과 short로 대칭 계산하세요",
        warmup_bars=80,
        params={"length": 12},
    )
    result = CodeGenerateService(settings("anthropic,gemini,openai")).generate(req)
    assert result.status == "preview"
    assert result.code.execution_policy == "code_v1"
    assert result.code.language.value == "python"
    assert result.code.source_code == SOURCE
    assert result.code.warmup_bars == 80 and result.code.params == {"length": 12}
    assert result.requested_model == "requested-gemini-model"
    assert result.actual_model == "reported-gemini-model"
    assert result.usage.model_dump() == {
        "input_tokens": 20,
        "output_tokens": 10,
        "thinking_tokens": 7,
        "total_tokens": 37,
    }
    assert req.prompt not in str(result.code.provenance)
    assert result.code.provenance["kind"] == "gemini_generated"
    SaveCodeStrategyRequest(name="검토 후 저장", code=result.code)
    effective = call.call_args.args[0]
    assert effective.llm_provider_order == "gemini"
    assert effective.gemini_model == "requested-gemini-model"
    assert call.call_args.kwargs["schema"] is CODE_GENERATION_SCHEMA
    assert call.call_args.kwargs["max_output_tokens"] == MAX_OUTPUT_TOKENS
    assert call.call_args.kwargs["timeout_seconds"] == TIMEOUT_SECONDS


@pytest.mark.parametrize("order,key", [("", True), ("openai", True), ("gemini", False)])
def test_disabled_or_missing_gemini_never_calls_any_provider(monkeypatch, order, key):
    call = stub(monkeypatch, completion())
    with pytest.raises(ProviderCallError, match="unavailable"):
        CodeGenerateService(settings(order, key=key)).generate(
            GenerateCodeStrategyRequest(prompt="SMA 교차 전략을 만드세요")
        )
    call.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"source_code": "def broken(", "assumptions": []},
        {"source_code": "pass", "assumptions": []},
        {"source_code": "async def on_bar(ctx, state):\n    return {}", "assumptions": []},
        {"source_code": "def on_bar():\n    return {}", "assumptions": []},
        {"source_code": SOURCE, "assumptions": "not-a-list"},
        {"source_code": SOURCE, "assumptions": [], "is_runnable": True},
    ],
)
def test_invalid_payload_is_a_safe_validation_failure(monkeypatch, payload):
    stub(monkeypatch, completion(payload=payload))
    with pytest.raises(ProviderCallError) as error:
        CodeGenerateService(settings()).generate(
            GenerateCodeStrategyRequest(prompt="SMA 교차 전략을 만드세요")
        )
    assert error.value.category == "validation"


def test_python_source_is_parsed_without_running_top_level_code(monkeypatch):
    source = 'raise RuntimeError("호스트에서 실행하면 안 됩니다")\n' + SOURCE
    stub(monkeypatch, completion(payload={"source_code": source, "assumptions": []}))
    result = CodeGenerateService(settings()).generate(
        GenerateCodeStrategyRequest(prompt="SMA 교차 전략을 만드세요")
    )
    assert result.code.source_code == source


def test_missing_usage_and_actual_model_remain_unknown(monkeypatch):
    stub(
        monkeypatch,
        completion(usage_known=False, thinking_tokens=None, total_tokens=None, actual_model=None),
    )
    result = CodeGenerateService(settings()).generate(
        GenerateCodeStrategyRequest(prompt="SMA 교차 전략을 만드세요")
    )
    assert result.usage is None and result.actual_model is None
    assert result.code.provenance["actual_model"] is None


def test_partial_usage_does_not_claim_zero_input_or_output(monkeypatch):
    stub(monkeypatch, completion(usage_known=False, total_tokens=37))
    result = CodeGenerateService(settings()).generate(
        GenerateCodeStrategyRequest(prompt="SMA 교차 전략을 만드세요")
    )
    assert result.usage.input_tokens is None and result.usage.output_tokens is None
    assert result.usage.total_tokens == 37


def test_partially_reported_usage_keeps_known_input_and_unknown_output(monkeypatch):
    stub(
        monkeypatch,
        completion(
            usage_known=False,
            input_tokens=23,
            output_tokens=0,
            reported_input_tokens=23,
            reported_output_tokens=None,
            thinking_tokens=None,
            total_tokens=23,
        ),
    )
    result = CodeGenerateService(settings()).generate(
        GenerateCodeStrategyRequest(prompt="SMA 교차 전략을 만드세요")
    )
    assert result.usage.input_tokens == 23
    assert result.usage.output_tokens is None
    assert result.usage.thinking_tokens is None
    assert result.usage.total_tokens == 23


def test_shared_prompt_contains_public_risk_numeric_and_user_contract_only():
    system, user = build_generation_prompt("SMA3/SMA8 교차", warmup_bars=80, params={"slow": 8})
    assert PUBLIC_CONTRACT in system and RISK_CONTRACT in system
    assert "1e-12*max(1,abs(a),abs(b))" in system
    assert "long R=1.1*(E-L), short R=1.1*(H-E)" in system
    assert "1.5R" in system and "2R 거리 trailing" in system
    assert "SMA3/SMA8 교차" in user and '"warmup_bars": 80' in user


@pytest.mark.parametrize(
    "changes",
    [
        {"provider": "openai"},
        {"model": "other"},
        {"warmup_bars": 0},
        {"params": {"n": float("nan")}},
    ],
)
def test_request_rejects_provider_override_and_invalid_runtime_inputs(changes):
    with pytest.raises(ValidationError):
        GenerateCodeStrategyRequest.model_validate(
            {"prompt": "SMA 교차 전략을 만드세요", **changes}
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category,expected",
    [
        ("forbidden", 503),
        ("not_found", 503),
        ("rate_limited", 503),
        ("validation", 502),
        ("timeout", 504),
    ],
)
async def test_preview_endpoint_preserves_only_safe_failure_metadata(
    category, expected, caplog, monkeypatch
):
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(router, prefix="/api/v1")
    service = SimpleNamespace(generate=Mock(side_effect=ProviderCallError(category, 429)))
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace()
    app.dependency_overrides[get_code_generate_service] = lambda: service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/strategies/code/generate", json={"prompt": "SMA 교차 전략을 만드세요"}
        )
    assert response.status_code == expected
    assert response.json()["detail"]["code"] == f"code_generate_{category}"
    assert "test-secret" not in response.text + caplog.text
    service.generate.assert_called_once()
