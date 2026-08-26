"""[ADR-040] 해설 층 서비스 — LLM 이 **설명만** 하고 판정하지 않는다.

`convert/service.py` 의 배선(anthropic 우선 → gemini fallback · tenacity 3회 · 예외 문자열 미반사)을
따르되 **한 가지를 새로 세운다 — 스키마 강제.** convert 는 `tools=`/`response_schema=` 가 0건이라
문자열을 수동 파싱하고 Gemini 의 ``` 펜스를 손으로 벗긴다(`convert/service.py`). 브리핑은 JSON 이어야
하므로 SDK 가 형식을 지키게 만든다 — 프롬프트로 부탁하면 모델이 안 지킬 수 있지만 스키마는 지킨다.

★**근거 검증은 서버가 한다.** 실재하지 않는 줄을 가리키는 항목은 여기서 버린다.
클라이언트에 맡기면 규칙이 두 곳에 살고 언젠가 한쪽만 고쳐진다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from google import genai
from google.genai import types as genai_types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import Settings
from src.strategy.narrative.prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.narrative.schemas import (
    NarrativeNote,
    StrategyNarrativeResponse,
)

logger = logging.getLogger(__name__)

_ANTHROPIC_TRANSIENT = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

_TOOL_NAME = "report_strategy_narrative"

# 두 provider 가 공유하는 JSON Schema. `additionalProperties: false` 로 모델이 필드를 늘리지 못하게 한다.
_NOTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "한 문장. 한국어."},
        "pine_lines": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "이 문장의 근거가 되는 Pine 소스 줄번호. 못 대면 이 항목을 쓰지 마세요.",
        },
    },
    "required": ["text", "pine_lines"],
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "한 문단. 무엇을 보고 언제 사고 언제 파는가."},
        "style": {
            "type": "string",
            "enum": ["trend_following", "mean_reversion", "breakout", "volatility", "other"],
        },
        "assumptions": {"type": "array", "items": _NOTE_SCHEMA},
        "risks": {"type": "array", "items": _NOTE_SCHEMA},
    },
    "required": ["summary", "style", "assumptions", "risks"],
}


def number_source(source: str) -> str:
    """줄번호를 붙인다 — 모델이 근거로 댈 좌표가 이것이다."""
    return "\n".join(f"{i}: {line}" for i, line in enumerate(source.splitlines(), start=1))


class NarrativeService:
    """LLM 전용. **DB 세션을 쥐지 않는다**(`convert/` 와 같은 예외 형태)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ── 공개 ─────────────────────────────────────────────────────────────
    def explain(
        self, *, source: str, facts: dict[str, Any], source_hash: str
    ) -> StrategyNarrativeResponse:
        anthropic_key = self._secret(self._settings.anthropic_api_key)
        gemini_key = self._secret(self._settings.gemini_api_key)
        if not anthropic_key and not gemini_key:
            raise RuntimeError("ANTHROPIC_API_KEY 또는 GEMINI_API_KEY 중 하나가 필요합니다")

        user = USER_TEMPLATE.format(
            facts=json.dumps(facts, ensure_ascii=False, indent=2),
            numbered_source=number_source(source),
        )

        if anthropic_key:
            try:
                raw = self._call_anthropic(anthropic_key, user)
                return self._build(raw, source, source_hash, provider="anthropic")
            except Exception as exc:
                # ★[BL-772] 계약 — SDK 예외 문자열(엔드포인트·모델·요청 ID)을 위로 흘리지 않는다.
                logger.exception("narrative anthropic failed exc_type=%s", type(exc).__name__)
                if not gemini_key:
                    raise RuntimeError("Anthropic 해설 실패 (Gemini fallback 미설정)") from exc

        try:
            raw = self._call_gemini(gemini_key, user)
        except Exception as exc:
            logger.exception("narrative gemini failed exc_type=%s", type(exc).__name__)
            raise RuntimeError("해설 provider 를 사용할 수 없습니다") from exc
        return self._build(raw, source, source_hash, provider="gemini")

    # ── provider ─────────────────────────────────────────────────────────
    @retry(
        retry=retry_if_exception_type(_ANTHROPIC_TRANSIENT),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call_anthropic(self, api_key: str, user: str) -> dict[str, Any]:
        """★tool use 로 **형식을 SDK 가 지키게** 한다 — 문자열 파싱이 없다."""
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=[
                {
                    "name": _TOOL_NAME,
                    "description": "전략 해설을 구조화해 보고합니다.",
                    "input_schema": _OUTPUT_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": user}],
        )
        for block in response.content or []:
            if (
                getattr(block, "type", None) == "tool_use"
                and getattr(block, "name", "") == _TOOL_NAME
            ):
                payload = getattr(block, "input", None)
                if isinstance(payload, dict):
                    return payload
        raise RuntimeError("도구 호출 응답이 오지 않았습니다")

    def _call_gemini(self, api_key: str, user: str) -> dict[str, Any]:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self._settings.gemini_model,
            contents=user,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=_OUTPUT_SCHEMA,
            ),
        )
        payload = json.loads(response.text or "{}")
        if not isinstance(payload, dict):
            raise RuntimeError("JSON 객체가 아닙니다")
        return payload

    # ── 근거 검증 ────────────────────────────────────────────────────────
    def _build(
        self, raw: dict[str, Any], source: str, source_hash: str, *, provider: str
    ) -> StrategyNarrativeResponse:
        max_line = len(source.splitlines())
        dropped = 0

        def ground(items: Any) -> list[NarrativeNote]:
            nonlocal dropped
            out: list[NarrativeNote] = []
            for item in items if isinstance(items, list) else []:
                if not isinstance(item, dict):
                    dropped += 1
                    continue
                text = str(item.get("text") or "").strip()
                lines = [
                    n
                    for n in (item.get("pine_lines") or [])
                    if isinstance(n, int) and 1 <= n <= max_line
                ]
                # ★근거가 없거나 **실재하지 않는 줄만** 가리키면 버린다.
                if not text or not lines:
                    dropped += 1
                    continue
                out.append(NarrativeNote(text=text, pine_lines=sorted(set(lines))))
            return out

        style = raw.get("style")
        return StrategyNarrativeResponse(
            source_hash=source_hash,
            provider=provider,  # type: ignore[arg-type]
            summary=str(raw.get("summary") or "").strip(),
            style=style if style in _OUTPUT_SCHEMA["properties"]["style"]["enum"] else "other",
            assumptions=ground(raw.get("assumptions")),
            risks=ground(raw.get("risks")),
            dropped_ungrounded=dropped,
        )

    @staticmethod
    def _secret(value: Any) -> str:
        if value is None:
            return ""
        getter = getattr(value, "get_secret_value", None)
        return (getter() if callable(getter) else str(value)) or ""
