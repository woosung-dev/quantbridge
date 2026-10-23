"""Gemini 자연어 생성 preview. 저장·호스트 실행·Demo 활성화 권한은 없다."""

from __future__ import annotations

import ast
import hashlib
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from src.core.config import Settings
from src.strategy.code_generate_prompt import (
    CODE_GENERATION_SCHEMA,
    CONTRACT_VERSION,
    MAX_OUTPUT_TOKENS,
    TIMEOUT_SECONDS,
    build_generation_prompt,
)
from src.strategy.code_schemas import (
    GenerateCodeStrategyRequest,
    GenerateCodeStrategyResponse,
    GenerationUsage,
    PythonCodeSnapshot,
)
from src.strategy.narrative.providers import (
    ProviderCallError,
    complete_json,
    provider_order,
    secret,
)


class GeneratedPythonPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_code: str = Field(min_length=1, max_length=131072)
    assumptions: list[Annotated[str, Field(max_length=2000)]] = Field(max_length=30)


def validate_generated_python(value: dict[str, Any]) -> GeneratedPythonPayload:
    """구문·callback 모양만 검사한다. 소스를 실행하거나 의미 일치를 주장하지 않는다."""
    try:
        payload = GeneratedPythonPayload.model_validate(value)
        tree = ast.parse(payload.source_code)
        if not any(
            isinstance(node, ast.FunctionDef)
            and node.name == "on_bar"
            and len(node.args.posonlyargs + node.args.args) == 2
            for node in tree.body
        ):
            raise ValueError("on_bar 계약이 없습니다")
        return payload
    except (SyntaxError, ValueError, TypeError, RecursionError):
        raise ProviderCallError("validation") from None


class CodeGenerateService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(self, req: GenerateCodeStrategyRequest) -> GenerateCodeStrategyResponse:
        if "gemini" not in provider_order(self._settings) or not secret(
            self._settings.gemini_api_key
        ):
            raise ProviderCallError("unavailable")
        effective = self._settings.model_copy(update={"llm_provider_order": "gemini"})
        system, user = build_generation_prompt(
            req.prompt, warmup_bars=req.warmup_bars, params=req.params
        )
        completion = complete_json(
            effective,
            system=system,
            user=user,
            schema=CODE_GENERATION_SCHEMA,
            tool_name="emit_python_code_strategy",
            max_output_tokens=MAX_OUTPUT_TOKENS,
            timeout_seconds=TIMEOUT_SECONDS,
        )
        if completion.provider != "gemini":
            raise ProviderCallError("validation")
        payload = validate_generated_python(completion.payload)
        try:
            code = PythonCodeSnapshot(
                execution_policy="code_v1",
                source_code=payload.source_code,
                warmup_bars=req.warmup_bars,
                params=req.params,
                provenance={
                    "kind": "gemini_generated",
                    "provider": "gemini",
                    "requested_model": effective.gemini_model,
                    "actual_model": completion.actual_model,
                    "contract_version": CONTRACT_VERSION,
                    "prompt_sha256": hashlib.sha256(req.prompt.encode()).hexdigest(),
                },
            )
        except (SyntaxError, ValueError, TypeError, RecursionError):
            raise ProviderCallError("validation") from None
        usage = None
        if (
            completion.usage_known
            or completion.thinking_tokens is not None
            or completion.total_tokens is not None
        ):
            usage = GenerationUsage(
                input_tokens=completion.input_tokens if completion.usage_known else None,
                output_tokens=completion.output_tokens if completion.usage_known else None,
                thinking_tokens=completion.thinking_tokens,
                total_tokens=completion.total_tokens,
            )
        return GenerateCodeStrategyResponse(
            code=code,
            assumptions=payload.assumptions,
            requested_model=effective.gemini_model,
            actual_model=completion.actual_model,
            usage=usage,
        )
