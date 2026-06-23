# Optimizer 엔진 3종(grid/bayesian/genetic) 공유 헬퍼.
from __future__ import annotations

from dataclasses import replace as dc_replace
from decimal import Decimal

from src.backtest.engine.types import BacktestConfig


def build_cell_config(
    base: BacktestConfig | None,
    *,
    overrides: dict[str, Decimal],
) -> BacktestConfig:
    """BacktestConfig override — base 의 기존 input_overrides 보존 + cell key 갱신.

    Sprint 51 BL-222 fix pattern: base 의 sizing 5필드 / init_cash / freq / fees /
    slippage / trading_sessions 모두 cell 마다 보존. dict merge → cell key 덮어쓰기.
    LESSON-063: grid/bayesian/genetic 3-engine 의 _build_cell_config 1:1 통합.
    """
    merged: dict[str, Decimal | int | bool | str] = {}
    if base is not None and base.input_overrides is not None:
        merged.update(base.input_overrides)
    merged.update(overrides)
    if base is None:
        return BacktestConfig(input_overrides=merged)
    return dc_replace(base, input_overrides=merged)
