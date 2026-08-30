"""indicator → strategy 변환 서비스.

모든 LLM 호출은 narrative provider selector를 통해서만 수행한다. 따라서 provider
순서·fallback·structured output·usage 정규화가 narrative/generate/convert에 동일하게
적용된다.
"""

from __future__ import annotations

from typing import Any

from src.core.config import Settings
from src.strategy.convert.prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.convert.schemas import ConvertIndicatorRequest, ConvertIndicatorResponse
from src.strategy.narrative.providers import complete_json
from src.strategy.pine_v2.signal_extractor import SignalExtractor

_CONVERT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"converted_code": {"type": "string", "minLength": 1}},
    "required": ["converted_code"],
}


class ConvertService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def convert(self, req: ConvertIndicatorRequest) -> ConvertIndicatorResponse:
        code_to_send = req.code
        sliced_from: int | None = None
        sliced_to: int | None = None
        token_reduction_pct: float | None = None
        warnings: list[str] = []

        if req.mode == "sliced":
            result = SignalExtractor().extract(req.code, mode="ast")
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

        completion = complete_json(
            self._settings,
            system=SYSTEM_PROMPT,
            user=USER_TEMPLATE.format(code=code_to_send),
            schema=_CONVERT_SCHEMA,
            tool_name="convert_indicator",
        )
        converted = completion.payload.get("converted_code")
        if not isinstance(converted, str) or not converted.strip():
            raise RuntimeError("LLM 변환 결과가 비어 있습니다")

        model = getattr(self._settings, f"{completion.provider}_model", completion.provider)
        provider_warnings = [
            f"{completion.provider} {model} 로 변환 완료",
            *warnings,
            *self._heuristic_quality_warnings(code_to_send, converted),
        ]
        return ConvertIndicatorResponse(
            converted_code=converted,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
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

        leftover_patterns = (
            "array.",
            "plotshape",
            "plot(",
            "alertcondition",
            "label.",
            "box.",
            "line.",
        )
        leftover_found = [p for p in leftover_patterns if p in converted]
        if leftover_found:
            msgs.append(
                f"⚠️ 변환 결과에 미지원/그리기 함수 흔적이 남아있습니다 ({', '.join(leftover_found)}). "
                "LLM 이 제거 규칙을 완전히 따르지 못함 — 결과를 직접 검토하세요."
            )

        if len(converted) > 100 and converted.strip() == original.strip():
            msgs.append("⚠️ 변환 결과가 원본과 100% 동일합니다. LLM 이 변환을 거부했을 가능성.")

        return msgs
