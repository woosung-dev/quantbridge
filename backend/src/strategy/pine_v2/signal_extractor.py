# Pine Script 신호 조건 추출기 — indicator → strategy 변환 전처리
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.strategy.pine_v2.coverage import analyze_coverage


@dataclass(frozen=True)
class ExtractionResult:
    sliced_code: str
    signal_vars: list[str]
    removed_lines: int
    removed_functions: list[str]
    is_runnable: bool
    token_reduction_pct: float  # 0-100


class SignalExtractor:
    """Pine Script 소스에서 신호 조건만 추출해 최소 코드 반환."""

    def extract(
        self,
        source: str,
        mode: Literal["text", "ast"] = "ast",
    ) -> ExtractionResult:
        if mode == "text":
            return self._extract_text(source)
        return self._extract_ast(source)

    def _extract_text(self, source: str) -> ExtractionResult:
        raise NotImplementedError

    def _extract_ast(self, source: str) -> ExtractionResult:
        raise NotImplementedError
