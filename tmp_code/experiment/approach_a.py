# Approach A: 전체 Pine Script 코드를 Claude API에 직접 전달 (연구용 baseline)
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic

# backend 모듈 import 경로 추가
_REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from src.strategy.pine_v2.coverage import analyze_coverage  # noqa: E402
from src.strategy.convert.prompt import SYSTEM_PROMPT  # noqa: E402


@dataclass
class ApproachAResult:
    approach: str = "A"
    converted_code: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    is_runnable: bool = False
    output_lines: int = 0
    error: str | None = None


def run(source: str, model: str = "claude-sonnet-4-6") -> ApproachAResult:
    """전체 코드를 Claude API에 직접 전달."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return ApproachAResult(error="ANTHROPIC_API_KEY 환경변수 미설정")

    client = anthropic.Anthropic(api_key=key)
    start = time.perf_counter()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": source}],
        )
    except Exception as exc:
        return ApproachAResult(error=str(exc))

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    converted = response.content[0].text if response.content else ""
    is_runnable = analyze_coverage(converted).is_runnable

    return ApproachAResult(
        converted_code=converted,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=elapsed_ms,
        is_runnable=is_runnable,
        output_lines=len(converted.splitlines()),
    )
