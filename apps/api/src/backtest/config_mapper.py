# Backtest 의 DB row 를 engine BacktestConfig 로 복원하는 module-level helper
"""Sprint 52 BL-222 P1 — `Backtest` row → engine `BacktestConfig` 매핑을
`BacktestService` 의 method 가 아니라 module-level 에 둔다.

추출 동기 (codex G.0 P1, 2026-05-11): StressTestService 의 worker entry
(`_execute_cost_assumption_sensitivity` + `_execute_param_stability`) 가 parent
backtest 의 BL-188 v3 sizing + trading_sessions + fees/slippage + initial_capital
을 cell 마다 보존해야 하는데, BacktestService 의 private method 를 직접 호출하면
layering/DI 위반. module-level helper 로 분리 → BacktestService 와 StressTestService
양쪽 import.

Sprint 31 BL-162a 진입 시점 매핑 (service.py L360-431 본문 그대로 이동).
"""

from __future__ import annotations

from collections.abc import Mapping
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


class StoredAssumptions:
    """`Backtest.config` JSONB 의 공통 6 가정을 읽는 단일 규칙.

    엔진 config(`build_engine_config_from_db`)와 응답 config(`BacktestService._to_detail`)
    가 같은 키 이름·같은 기본값·같은 coerce 로 읽는다 — 화면에 보이는 가정과 엔진이 쓴
    가정이 갈리지 않게 하는 자리다. 누락 키(또는 NULL config 전체)는 engine
    `BacktestConfig()` 기본값으로 fallback 한다.

    필드별로 지연해서 읽는다. 호출자가 읽지 않는 필드(예: Pine 응답의 maker_fee)는
    파싱하지 않고, 잘못 저장된 값의 예외도 호출자가 읽는 순서대로 난다.
    """

    def __init__(self, config: Mapping[str, Any] | None) -> None:
        self._cfg: Mapping[str, Any] = config if config is not None else {}
        self._default = BacktestConfig()

    @property
    def leverage(self) -> float:
        return float(self._cfg.get("leverage", self._default.leverage))

    @property
    def fees(self) -> float:
        return float(self._cfg.get("fees", self._default.fees))

    @property
    def maker_fee(self) -> float:
        # code 제출은 Decimal 문자열("0.00010")로, Pine 제출은 키 없이 저장한다.
        return float(self._cfg.get("maker_fee", self._default.maker_fee))

    @property
    def slippage(self) -> float:
        return float(self._cfg.get("slippage", self._default.slippage))

    @property
    def include_funding(self) -> bool:
        return bool(self._cfg.get("include_funding", self._default.include_funding))

    @property
    def fill_timing(self) -> str:
        # TV parity — 시장가 체결 타이밍 (구 row = bar_close fallback).
        return str(self._cfg.get("fill_timing", self._default.fill_timing))


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
    assumptions = StoredAssumptions(bt.config)
    # engine 기본 인스턴스는 StoredAssumptions 가 만든 하나를 같이 쓴다.
    leverage_basis: float = float(
        cfg_dict.get("leverage_basis", assumptions._default.leverage_basis)
    )
    return BacktestConfig(
        init_cash=bt.initial_capital,
        fees=assumptions.fees,
        maker_fee=assumptions.maker_fee,
        slippage=assumptions.slippage,
        freq=timeframe_to_freq(bt.timeframe),
        trading_sessions=trading_sessions_tuple,
        leverage=assumptions.leverage,
        include_funding=assumptions.include_funding,
        fill_timing=cast(Literal["bar_close", "next_bar_open"], assumptions.fill_timing),
        default_qty_type=form_qty_type,
        default_qty_value=form_qty_value,
        live_position_size_pct=live_pct,
        sizing_source=sizing_source,
        sizing_basis=sizing_basis,
        leverage_basis=leverage_basis,
    )


__all__ = [
    "StoredAssumptions",
    "build_engine_config_from_db",
    "timeframe_to_freq",
]
