"""[ADR-041] 자연어 → 전략 생성. **Pine 이 정본**이고 판정은 LLM 이 하지 않는다.

흐름 넷.
  ⑴ LLM 이 **Pine + Python 을 둘 다** 산출한다(사용자 결정 2026-08-27).
  ⑵ **`analyze_coverage` all-or-nothing 이 판정한다** — 미지원 1개라도 있으면 저장 거부([ADR-003] 결정 2).
  ⑶ 통과한 Pine 을 [ADR-042] 렌더러로 Python 화해 LLM 이 쓴 Python 과 **대조**한다.
  ⑷ 어긋나면 **렌더링본을 정본으로 제시**한다.

★★**⑶ 은 드리프트를 제거하지 못한다.** 식별자 집합 비교라 「의미가 같은데 표현이 다름」과
「표현이 같은데 의미가 다름」을 완전히 못 가른다. 그래서 이 모듈이 내는 것은 판정이 아니라
**「다를 수 있습니다」라는 신호**다([ADR-041] §트레이드오프에 되돌릴 자리를 적어 뒀다).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.core.config import Settings
from src.strategy.narrative.catalog import resolve_override
from src.strategy.narrative.generate_prompt import SYSTEM_PROMPT, USER_TEMPLATE
from src.strategy.narrative.providers import complete_json
from src.strategy.narrative.schemas import (
    DriftReport,
    GenerateStrategyRequest,
    GenerateStrategyResponse,
)
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.py_renderer import render_python

logger = logging.getLogger(__name__)

_TOOL_NAME = "emit_strategy"

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pine_source": {
            "type": "string",
            "description": "//@version=5 로 시작하는 실행 가능한 Pine 전략. 이것이 정본입니다.",
        },
        "python_view": {
            "type": "string",
            "description": "같은 전략을 읽기 쉽게 옮긴 파이썬. 실행되지 않습니다. import 금지.",
        },
        "notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "사용자가 알아야 할 것. 손절 부재 등. 성과를 약속하지 마세요.",
        },
    },
    "required": ["pine_source", "python_view", "notes"],
}

# 식별자 = 이름·속성 체인. 드리프트 대조의 단위다.
_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
# 두 산출물이 문법상 다를 수밖에 없는 것들 — 이것으로 어긋났다고 말하면 항상 어긋난다.
_DRIFT_NOISE = frozenset(
    {
        "True",
        "False",
        "None",
        "true",
        "false",
        "na",
        "if",
        "else",
        "elif",
        "for",
        "in",
        "and",
        "or",
        "not",
        "def",
        "return",
        "range",
        "var",
        "varip",
        "int",
        "float",
        "bool",
        "string",
        "strategy",
        "input",
        "ta",
        "math",
        "pass",
    }
)


def _identifiers(text: str) -> set[str]:
    """주석·문자열을 걷어낸 뒤 식별자를 모은다.

    ★주석을 안 걷으면 **렌더러가 붙인 한국어 해설**이 통째로 드리프트로 잡힌다.
    """
    without_strings = re.sub(r'"[^"]*"|\'[^\']*\'', " ", text)
    without_comments = re.sub(r"(#|//)[^\n]*", " ", without_strings)
    return {
        m.group(1) for m in _IDENT_RE.finditer(without_comments) if m.group(1) not in _DRIFT_NOISE
    }


def detect_drift(*, pine_source: str, llm_python: str) -> DriftReport:
    """[ADR-041] 결정 4 — 위험을 **제거하지 않고 가시화**한다."""
    rendered = render_python(pine_source).code
    a = _identifiers(llm_python)
    b = _identifiers(rendered)
    return DriftReport(
        rendered_python=rendered,
        only_in_llm=sorted(a - b),
        only_in_rendered=sorted(b - a),
    )


class GenerateService:
    """LLM 전용. **DB 세션을 쥐지 않는다**(`narrative/` 와 같은 형태).

    ★provider 선택·fallback·스키마 강제는 `providers.complete_json` 이 맡는다.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(self, req: GenerateStrategyRequest) -> GenerateStrategyResponse:
        user = USER_TEMPLATE.format(prompt=req.prompt, symbol=req.symbol, timeframe=req.timeframe)
        effective = resolve_override(self._settings, provider=req.provider, model=req.model)
        raw, provider = complete_json(
            effective,
            system=SYSTEM_PROMPT,
            user=user,
            schema=_OUTPUT_SCHEMA,
            tool_name=_TOOL_NAME,
        )
        return self._build(raw, provider=provider)

    # ── 판정 + 대조 ──────────────────────────────────────────────────────
    def _build(self, raw: dict[str, Any], *, provider: str) -> GenerateStrategyResponse:
        pine = str(raw.get("pine_source") or "").strip()
        llm_python = str(raw.get("python_view") or "").strip()
        notes = [str(n) for n in (raw.get("notes") or []) if str(n).strip()]

        # ★판정은 LLM 이 하지 않는다 — 결정론 분석기가 한다([ADR-003] 결정 2).
        coverage = analyze_coverage(pine) if pine else None
        is_runnable = bool(coverage and coverage.is_runnable and pine)
        unsupported = list(coverage.all_unsupported) if coverage else []

        drift: DriftReport | None = None
        if is_runnable:
            try:
                drift = detect_drift(pine_source=pine, llm_python=llm_python)
            except Exception:
                # 렌더 실패는 판정을 뒤집지 않는다 — 대조를 못 했다는 뜻일 뿐이다.
                logger.exception("generate drift detection failed")
                drift = None

        return GenerateStrategyResponse(
            provider=provider,  # type: ignore[arg-type]
            pine_source=pine,
            llm_python=llm_python,
            notes=notes,
            is_runnable=is_runnable,
            unsupported=unsupported,
            drift=drift,
        )
