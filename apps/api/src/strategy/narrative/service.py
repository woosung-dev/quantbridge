"""[ADR-040] 해설 층 서비스 — LLM 이 **설명만** 하고 판정하지 않는다.

provider 선택·fallback·**스키마 강제**는 `providers.complete_json` 이 맡는다(설정
`LLM_PROVIDER_ORDER` 가 순서를 정한다). 이 파일이 갖는 것은 **프롬프트와 근거 검증** 둘뿐이다.
★`convert/service.py` 는 아직 그 층을 안 쓴다 — 거기는 스키마 강제가 0이라 문자열을 손으로
파싱하고 Gemini 의 ``` 펜스를 벗긴다. 옮기려면 그쪽 계약부터 세워야 한다.

★**근거 검증은 서버가 한다.** 실재하지 않는 줄을 가리키는 항목은 여기서 버린다.
클라이언트에 맡기면 규칙이 두 곳에 살고 언젠가 한쪽만 고쳐진다.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast, get_args

from src.core.config import Settings
from src.strategy.narrative.prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.narrative.providers import complete_json
from src.strategy.narrative.schemas import (
    NarrativeNote,
    NarrativeStyle,
    StrategyNarrativeResponse,
)

logger = logging.getLogger(__name__)

_TOOL_NAME = "report_strategy_narrative"

# ★사본을 만들지 마라 — 허용 집합의 SSOT 는 `NarrativeStyle` 하나다.
# 손으로 나열하면 「타입 · 런타임 멤버십 · LLM 에 보내는 enum」 셋이 갈리고,
# 갈린 순간 모델이 스키마상 허용된 값을 내도 조용히 `"other"` 로 접힌다.
_NARRATIVE_STYLES: tuple[NarrativeStyle, ...] = get_args(NarrativeStyle)

# 세 provider 가 **같은 스키마**를 쓴다. OpenAI strict 모드가 요구하는
# `additionalProperties: false` 는 `providers._strict` 가 한 번만 채운다.
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
            # 위와 같은 이유로 여기도 파생이다 — LLM 이 받는 enum 과 우리가 받아들이는
            # 집합이 갈리면 그 차이는 예외가 아니라 침묵한 강등으로 나타난다.
            "enum": list(_NARRATIVE_STYLES),
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
    """LLM 전용. **DB 세션을 쥐지 않는다**(`convert/` 와 같은 예외 형태).

    ★provider 선택·fallback·스키마 강제는 `providers.complete_json` 이 맡는다 — 종전에는 그
    로직이 이 파일과 `generate_service.py` 에 **복제**돼 있었다.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def explain(
        self,
        *,
        source: str,
        facts: dict[str, Any],
        source_hash: str,
        settings_override: Settings | None = None,
    ) -> StrategyNarrativeResponse:
        """★`settings_override` 는 **요청이 고른 provider/model** 이다.

        검증은 라우터가 `catalog.resolve_override` 로 이미 했다 — 여기서 다시 하지 않는다.
        규칙이 두 곳에 살면 갈린다.
        """
        user = USER_TEMPLATE.format(
            facts=json.dumps(facts, ensure_ascii=False, indent=2),
            numbered_source=number_source(source),
        )
        raw, provider = complete_json(
            settings_override or self._settings,
            system=SYSTEM_PROMPT,
            user=user,
            schema=_OUTPUT_SCHEMA,
            tool_name=_TOOL_NAME,
        )
        return self._build(raw, source, source_hash, provider=provider)

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

        raw_style = raw.get("style")
        # 닫힌 허용 집합 멤버십을 통과한 값만 NarrativeStyle로 취급한다.
        style = cast(NarrativeStyle, raw_style) if raw_style in _NARRATIVE_STYLES else "other"
        return StrategyNarrativeResponse(
            source_hash=source_hash,
            provider=provider,  # type: ignore[arg-type]
            summary=str(raw.get("summary") or "").strip(),
            style=style,
            assumptions=ground(raw.get("assumptions")),
            risks=ground(raw.get("risks")),
            dropped_ungrounded=dropped,
        )
