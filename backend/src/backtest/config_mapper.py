# Backtest 의 DB row 를 engine BacktestConfig 로 복원하는 module-level helper
"""Sprint 52 BL-222 P1 — `backend/src/backtest/service.py` 의 private
`BacktestService._build_engine_config(bt)` 를 module-level 로 추출.

추출 동기 (codex G.0 P1, 2026-05-11): StressTestService 의 worker entry
(`_execute_cost_assumption_sensitivity` + `_execute_param_stability`) 가 parent
backtest 의 BL-188 v3 sizing + trading_sessions + fees/slippage + initial_capital
을 cell 마다 보존해야 하는데, BacktestService 의 private method 를 직접 호출하면
layering/DI 위반. module-level helper 로 분리 → BacktestService 와 StressTestService
양쪽 import.

Sprint 31 BL-162a 진입 시점 매핑 (service.py L360-431 본문 그대로 이동).
"""

from __future__ import annotations

from typing import Any, Literal, cast

from src.backtest.engine.types import BacktestConfig
from src.backtest.models import Backtest

# CreateBacktestRequest 의 6 timeframe Literal 과 정합. v2_adapter 의
# `_FREQ_HOURS_V2` 와 정합 (avg_holding_hours 변환 매핑 한 쌍).
_TIMEFRAME_TO_FREQ: dict[str, str] = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


def timeframe_to_freq(timeframe: str) -> str:
    """timeframe Literal → pandas offset alias. 미매핑 시 '1D' fallback (안전)."""
    return _TIMEFRAME_TO_FREQ.get(timeframe, "1D")


_VALID_SIZING_BASIS: frozenset[str] = frozenset(
    {
        "pine_native",
        "live_available_balance_approx_equity",
        "form_equity",
        "fallback_qty1",
    }
)


def build_engine_config_from_db(bt: Backtest) -> BacktestConfig:
    """Backtest row 의 사용자 입력 config + initial_capital + timeframe → engine BacktestConfig.

    Sprint 52 BL-222 P1 — Sprint 31 BL-162a 진입 시점 매핑을 module-level 로 추출.

    bt.config NULL (legacy / Sprint 30 이전) 시 engine default 사용 (init_cash /
    freq 만 bt 값 적용). bt.config 채워진 경우 leverage/fees/slippage/include_funding
    모두 사용자 입력값으로 override.

    Sprint 38 BL-188 v3 (codex iter 2 [P1] #3) — submit() 시점 helper 가 결정한
    sizing canonical 5 필드 + trading_sessions 를 BacktestConfig 로 propagate.
    본 매핑 누락 시 worker 가 Live mirror 결정 silent ignore = 거짓 trust 회복 실패.
    """
    default = BacktestConfig()
    cfg_dict: dict[str, Any] = bt.config if bt.config is not None else {}
    # BL-188a: 폼 입력 default_qty_type / default_qty_value 도 engine 으로 전달.
    # BL-188 v3 의 service helper 가 결정한 결과는 동일 키에 저장 (Pine 명시 시 Pine
    # 값, 폼 manual 시 사용자 입력값, Live mirror 시 None — live_position_size_pct
    # 만 채움). priority chain 최종 적용은 compat.parse_and_run_v2 에서.
    form_qty_type_raw = cfg_dict.get("default_qty_type")
    form_qty_value_raw = cfg_dict.get("default_qty_value")
    form_qty_type: str | None = str(form_qty_type_raw) if form_qty_type_raw is not None else None
    form_qty_value: float | None = (
        float(form_qty_value_raw) if form_qty_value_raw is not None else None
    )
    # BL-188 v3 — Live mirror canonical 5 필드 (codex iter 2 [P1] #3 매핑).
    live_pct_raw = cfg_dict.get("live_position_size_pct")
    live_pct: float | None = float(live_pct_raw) if live_pct_raw is not None else None
    sessions_raw = cfg_dict.get("trading_sessions") or []
    trading_sessions_tuple: tuple[str, ...] = tuple(sessions_raw)
    # sizing_source / sizing_basis Literal validation (legacy NULL → fallback).
    sizing_source_raw = cfg_dict.get("sizing_source") or "fallback"
    if sizing_source_raw not in {"pine", "live", "form", "fallback"}:
        sizing_source_raw = "fallback"
    sizing_source = cast(Literal["pine", "live", "form", "fallback"], sizing_source_raw)
    sizing_basis_raw = cfg_dict.get("sizing_basis") or "fallback_qty1"
    if sizing_basis_raw not in _VALID_SIZING_BASIS:
        sizing_basis_raw = "fallback_qty1"
    sizing_basis = cast(
        Literal[
            "pine_native",
            "live_available_balance_approx_equity",
            "form_equity",
            "fallback_qty1",
        ],
        sizing_basis_raw,
    )
    leverage_basis: float = float(cfg_dict.get("leverage_basis", default.leverage_basis))
    return BacktestConfig(
        init_cash=bt.initial_capital,
        fees=float(cfg_dict.get("fees", default.fees)),
        slippage=float(cfg_dict.get("slippage", default.slippage)),
        freq=timeframe_to_freq(bt.timeframe),
        trading_sessions=trading_sessions_tuple,
        leverage=float(cfg_dict.get("leverage", default.leverage)),
        include_funding=bool(cfg_dict.get("include_funding", default.include_funding)),
        default_qty_type=form_qty_type,
        default_qty_value=form_qty_value,
        live_position_size_pct=live_pct,
        sizing_source=sizing_source,
        sizing_basis=sizing_basis,
        leverage_basis=leverage_basis,
    )


__all__ = [
    "build_engine_config_from_db",
    "timeframe_to_freq",
]
