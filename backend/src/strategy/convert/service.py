# indicator → strategy LLM 변환 서비스
from __future__ import annotations

import anthropic

from src.core.config import Settings
from src.strategy.convert.prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.convert.schemas import ConvertIndicatorRequest, ConvertIndicatorResponse
from src.strategy.pine_v2.signal_extractor import SignalExtractor


class ConvertService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def convert(self, req: ConvertIndicatorRequest) -> ConvertIndicatorResponse:
        key = self._settings.anthropic_api_key
        if key is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                ".env.local에 ANTHROPIC_API_KEY를 추가하세요."
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

        client = anthropic.Anthropic(api_key=key.get_secret_value())
        response = client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(code=code_to_send)}],
        )

        first_block = response.content[0] if response.content else None
        converted = first_block.text if first_block and hasattr(first_block, "text") else ""

        return ConvertIndicatorResponse(
            converted_code=converted,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            warnings=warnings,
            sliced_from=sliced_from,
            sliced_to=sliced_to,
            token_reduction_pct=token_reduction_pct,
        )
