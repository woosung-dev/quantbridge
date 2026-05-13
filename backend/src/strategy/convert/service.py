# indicator → strategy LLM 변환 서비스 (Anthropic 우선 + Gemini fallback)
from __future__ import annotations

import logging

import anthropic
from google import genai
from google.genai import types as genai_types
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import Settings
from src.strategy.convert.prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.convert.schemas import ConvertIndicatorRequest, ConvertIndicatorResponse
from src.strategy.pine_v2.signal_extractor import SignalExtractor

logger = logging.getLogger(__name__)

_ANTHROPIC_TRANSIENT = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class ConvertService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def convert(self, req: ConvertIndicatorRequest) -> ConvertIndicatorResponse:
        anthropic_key = self._settings.anthropic_api_key
        gemini_key = self._settings.gemini_api_key

        if anthropic_key is None and gemini_key is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 또는 GEMINI_API_KEY 중 하나가 필요합니다. "
                ".env.local에 키를 추가하세요."
            )

        code_to_send = req.code
        sliced_from: int | None = None
        sliced_to: int | None = None
        token_reduction_pct: float | None = None
        warnings: list[str] = []

        if req.mode == "sliced":
            extractor = SignalExtractor()
            result = extractor.extract(req.code, mode="ast")
            sliced_from = len(req.code.splitlines())
            sliced_to = len(result.sliced_code.splitlines())
            token_reduction_pct = result.token_reduction_pct

            if result.is_runnable:
                return ConvertIndicatorResponse(
                    converted_code=result.sliced_code,
                    input_tokens=0,
                    output_tokens=0,
                    warnings=["AST 슬라이싱으로 직접 실행 가능한 코드 추출 (LLM 미사용)"],
                    sliced_from=sliced_from,
                    sliced_to=sliced_to,
                    token_reduction_pct=token_reduction_pct,
                )

            code_to_send = result.sliced_code
            if result.removed_functions:
                warnings.append(f"제거된 드로잉 함수: {', '.join(result.removed_functions)}")

        anthropic_error: Exception | None = None
        if anthropic_key is not None:
            try:
                return self._convert_with_anthropic(
                    code_to_send,
                    anthropic_key.get_secret_value(),
                    warnings,
                    sliced_from,
                    sliced_to,
                    token_reduction_pct,
                )
            except RetryError as exc:
                last = exc.last_attempt.exception()
                anthropic_error = last if isinstance(last, Exception) else exc
                logger.exception("Anthropic 변환 transient retry 모두 실패")
            except anthropic.AnthropicError as exc:
                anthropic_error = exc
                logger.exception("Anthropic 변환 영구 실패 (%s)", type(exc).__name__)
            except Exception as exc:
                anthropic_error = exc
                logger.exception("Anthropic 변환 중 예상치 못한 예외")

        if gemini_key is not None:
            try:
                fallback_warnings = list(warnings)
                if anthropic_error is not None:
                    fallback_warnings.append(
                        f"Anthropic 실패 → Gemini fallback ({type(anthropic_error).__name__}: "
                        f"{anthropic_error})"
                    )
                return self._convert_with_gemini(
                    code_to_send,
                    gemini_key.get_secret_value(),
                    fallback_warnings,
                    sliced_from,
                    sliced_to,
                    token_reduction_pct,
                )
            except Exception as exc:
                logger.exception("Gemini fallback 도 실패")
                if anthropic_error is not None:
                    raise RuntimeError(
                        f"양쪽 provider 모두 실패. "
                        f"Anthropic: {type(anthropic_error).__name__}: {anthropic_error}. "
                        f"Gemini: {type(exc).__name__}: {exc}"
                    ) from exc
                raise RuntimeError(
                    f"Gemini 변환 실패: {type(exc).__name__}: {exc}"
                ) from exc

        assert anthropic_error is not None
        raise RuntimeError(
            f"Anthropic 변환 실패 (Gemini fallback 미설정): "
            f"{type(anthropic_error).__name__}: {anthropic_error}"
        ) from anthropic_error

    @retry(
        retry=retry_if_exception_type(_ANTHROPIC_TRANSIENT),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_anthropic(self, client: anthropic.Anthropic, code: str) -> anthropic.types.Message:
        return client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(code=code)}],
        )

    def _convert_with_anthropic(
        self,
        code: str,
        api_key: str,
        warnings: list[str],
        sliced_from: int | None,
        sliced_to: int | None,
        token_reduction_pct: float | None,
    ) -> ConvertIndicatorResponse:
        client = anthropic.Anthropic(api_key=api_key)
        response = self._call_anthropic(client, code)

        first_block = response.content[0] if response.content else None
        converted = first_block.text if first_block and hasattr(first_block, "text") else ""

        provider_warnings = [
            f"Anthropic {self._settings.anthropic_model} 로 변환 완료",
            *warnings,
        ]
        provider_warnings.extend(self._heuristic_quality_warnings(code, converted))

        return ConvertIndicatorResponse(
            converted_code=converted,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            warnings=provider_warnings,
            sliced_from=sliced_from,
            sliced_to=sliced_to,
            token_reduction_pct=token_reduction_pct,
        )

    def _convert_with_gemini(
        self,
        code: str,
        api_key: str,
        warnings: list[str],
        sliced_from: int | None,
        sliced_to: int | None,
        token_reduction_pct: float | None,
    ) -> ConvertIndicatorResponse:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self._settings.gemini_model,
            contents=USER_TEMPLATE.format(code=code),
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=4096,
            ),
        )

        converted = (response.text or "").strip()
        if converted.startswith("```"):
            lines = converted.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            converted = "\n".join(lines)

        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count if usage else None) or 0
        output_tokens = (usage.candidates_token_count if usage else None) or 0

        provider_warnings = [
            f"Gemini {self._settings.gemini_model} 로 변환 완료 (fallback)",
            *warnings,
        ]
        provider_warnings.extend(self._heuristic_quality_warnings(code, converted))

        return ConvertIndicatorResponse(
            converted_code=converted,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            warnings=provider_warnings,
            sliced_from=sliced_from,
            sliced_to=sliced_to,
            token_reduction_pct=token_reduction_pct,
        )

    @staticmethod
    def _heuristic_quality_warnings(original: str, converted: str) -> list[str]:
        msgs: list[str] = []
        if not converted.strip():
            msgs.append("⚠️ 변환 결과가 비어있습니다. provider 응답 형식 확인 필요.")
            return msgs

        leftover_patterns = ("array.", "plotshape", "plot(", "alertcondition", "label.", "box.", "line.")
        leftover_found = [p for p in leftover_patterns if p in converted]
        if leftover_found:
            msgs.append(
                f"⚠️ 변환 결과에 미지원/그리기 함수 흔적이 남아있습니다 ({', '.join(leftover_found)}). "
                "LLM 이 제거 규칙을 완전히 따르지 못함 — 결과를 직접 검토하세요."
            )

        if len(converted) > 100 and converted.strip() == original.strip():
            msgs.append("⚠️ 변환 결과가 원본과 100% 동일합니다. LLM 이 변환을 거부했을 가능성.")

        return msgs
