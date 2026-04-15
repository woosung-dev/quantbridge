"""Pine Script 파싱 결과 타입 정의."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from src.strategy.pine.errors import PineError


@dataclass(frozen=True)
class SourceSpan:
    """소스 코드 내 위치 정보."""

    line: int
    column: int
    length: int


@dataclass
class SignalResult:
    """vectorbt.Portfolio.from_signals() 파라미터와 1:1 매핑되는 시그널 결과.

    sprint 1에서는 entries/exits만 채워지고 나머지는 None 기본값.
    """

    # vectorbt from_signals() 필수 파라미터
    entries: pd.Series
    exits: pd.Series

    # vectorbt from_signals() 선택 파라미터 — sprint 2에서 채울 예정
    direction: str | None = None
    sl_stop: float | None = None
    tp_limit: float | None = None
    position_size: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ParseOutcome:
    """Pine Script 파싱 전체 결과."""

    status: Literal["ok", "unsupported", "error"]
    source_version: Literal["v4", "v5"]
    # result: 실행 성공 시 SignalResult, 실패 시 None (signals의 공개 API 별칭)
    result: SignalResult | None = None
    error: PineError | None = None
    supported_feature_report: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def signals(self) -> SignalResult | None:
        """하위 호환성을 위한 별칭 (result와 동일)."""
        return self.result
