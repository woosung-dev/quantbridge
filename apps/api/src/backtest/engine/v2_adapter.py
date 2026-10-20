"""pine_v2 → BacktestOutcome 어댑터.

`parse_and_run_v2` 가 반환하는 `V2RunResult` (Track S/A/M) 의 `StrategyState`
를 기존 엔진이 기대하는 `BacktestOutcome(BacktestResult(metrics, equity,
trades))` 형태로 변환한다. bar-by-bar 누적 PnL
방식으로 equity curve 를 재구성한다.

Decimal-first 합산 규칙 (CLAUDE.md LESSON) 준수 — 금융 수치는 float 공간에서
합산 후 Decimal 로 바꾸지 않는다. equity 시리즈는 dtype=object 로 Decimal 을
보관하고, Sharpe/DD 같은 근사 지표만 float 으로 변환해 계산한다.
"""

from __future__ import annotations

import bisect
import logging
import math
import re
from decimal import Decimal
from typing import Literal

import pandas as pd
from pynescript.ast.error import SyntaxError as PyneSyntaxError

from src.backtest.engine.holding_period import HoldingPeriod
from src.backtest.engine.metrics import (
    calmar_ratio,
    compute_excursion_stats,
    compute_side_metrics,
    sharpe_ratio,
    sortino_ratio,
)
from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.backtest.exceptions import TradingSessionTzNaiveReject
from src.strategy.pine.types import ParseOutcome, SignalResult
from src.strategy.pine_v2.compat import V2RunResult, parse_and_run_v2
from src.strategy.pine_v2.exit_orders import fill_type_for
from src.strategy.pine_v2.interpreter import PineRuntimeError
from src.strategy.pine_v2.leverage_model import is_leverage_active
from src.strategy.pine_v2.strategy_state import StrategyState, Trade

logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)", re.MULTILINE)


def run_backtest_v2(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
    funding_rates: pd.Series | None = None,
) -> BacktestOutcome:
    """pine_v2 엔진으로 Pine 을 실행한 뒤 `BacktestOutcome` 으로 변환.

    실패 분기
    ---------
    - `PineRuntimeError` (bar-level 실행 오류) → status="error". "부분 실행 금지"
      규칙에 따라 silent skip 하지 않는다.
    - `SyntaxError` (pynescript 파싱 실패) → status="parse_failed"
    - `ValueError` (_validate_ohlcv 같은 데이터 오류) → status="error"
    - classify 가 unknown track 반환 (`ValueError` 에 포함) → status="error"
    """
    cfg = config if config is not None else BacktestConfig()
    # config_mapper의 pandas freq를 실제 Pine 봉 context로 전달한다. 기존에 사용한
    # 비표준 freq는 context 없이 실행하던 호환 동작을 유지한다.
    timeframe = None
    frequency = re.fullmatch(r"([1-9]\d*)?(min|[sSmhHdDwWM])", cfg.freq)
    if frequency is not None:
        count, unit = frequency.groups()
        if unit == "min":
            unit = "m"
        elif unit != "M":
            unit = unit.lower()
        timeframe = f"{count or '1'}{unit}"

    # Sprint 38 BL-188 v3 A2 — tz-naive sessions-only fail-closed (422).
    # sessions 비어있으면 reject 안 함 (회귀 0). DatetimeIndex 아님 또는 tz=None 시 reject.
    # Live `is_allowed` 가 tz-aware 강제하므로 backtest 도 동일 invariant 유지.
    if cfg.trading_sessions:
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            raise TradingSessionTzNaiveReject(
                detail=(
                    "trading_sessions 활성 시 OHLCV index 가 DatetimeIndex 필수 — "
                    "현재 type: " + type(ohlcv.index).__name__
                )
            )
        if ohlcv.index.tz is None:
            raise TradingSessionTzNaiveReject(
                detail=(
                    "trading_sessions 활성 시 OHLCV index 가 tz-aware 필수 — "
                    "naive index 를 silent UTC 가정으로 처리 시 Live `is_allowed` 와 "
                    "결과 불일치 risk."
                )
            )

    try:
        # strict=True — bar-level PineRuntimeError 를 raise 시켜 상위에서 status=error 로 변환.
        # Sprint 37 BL-185: cfg.init_cash 를 initial_capital 로 전달 → configure_sizing 호출.
        # Sprint 37 BL-188a: cfg.default_qty_type/value (폼 입력) 도 전달.
        # Sprint 38 BL-188 v3 A2: cfg.live_position_size_pct + cfg.trading_sessions 를
        # compat 으로 propagate. priority chain (Pine > form > Live > None) 은
        # compat.parse_and_run_v2 안에서 결정.
        v2 = parse_and_run_v2(
            source,
            ohlcv,
            strict=True,
            initial_capital=float(cfg.init_cash),
            live_position_size_pct=cfg.live_position_size_pct,
            form_default_qty_type=cfg.default_qty_type,
            form_default_qty_value=cfg.default_qty_value,
            leverage=cfg.leverage,
            # BL-460 — 증거금 게이트가 gross 가 아닌 net 자본으로 판정하도록 leg 비용률을
            # 넘긴다. 진입과 시장가 청산은 taker 라 fees + slippage 가 그 leg 의 비용률이다.
            # ★TP(resting limit) 청산만 maker 인데(BL-104) 게이트는 그것도 taker 로 쳐서
            # 비용을 과대계상한다 — 진입을 막는 방향이라 안전하다. 상세 =
            # `StrategyState._leg_cost` docstring. leverage<=1 이면 게이트 자체가
            # no-op 이라 이 값은 아무 데도 안 쓰인다 → L=1 경로 byte-identical.
            taker_cost_rate=cfg.fees + cfg.slippage,
            sessions_allowed=cfg.trading_sessions,
            # Sprint 51 BL-220 — pine_v2 input override (Param Stability grid sweep).
            # cfg.input_overrides=None 일 때 = 회귀 0 (기존 backtest path 변경 X).
            input_overrides=cfg.input_overrides,
            # TV parity — 시장가 체결 타이밍 (기본 bar_close = 회귀 0).
            fill_timing=cfg.fill_timing,
            timeframe=timeframe,
        )
    except PineRuntimeError as exc:
        logger.info("v2_adapter_runtime_error: %s", exc)
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )
    except (SyntaxError, PyneSyntaxError) as exc:
        logger.info("v2_adapter_parse_failed (syntax): %s", exc)
        return BacktestOutcome(
            status="parse_failed",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )
    except ValueError as exc:
        # 데이터 오류 (empty OHLCV 등) 또는 classify unknown — parse 자체는 성공했을 가능성이 높다.
        logger.info("v2_adapter_data_error: %s", exc)
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )
    except Exception as exc:
        # 이 경계에서는 파싱/실행 중 어느 단계인지 알 수 없다. 원인 미지 오류를
        # 사용자 Pine 문법 탓으로 단정하지 않도록 약한 주장인 error로 노출한다.
        logger.exception("v2_adapter_unexpected_error")
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )

    state, _errors = _extract_state_and_errors(v2)
    if state is None:
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=f"pine_v2: strategy state 수집 실패 (track={v2.track})",
        )

    try:
        trades = _build_raw_trades(state, cfg, ohlcv=ohlcv)
        # C6 funding accrual — 비용/결측을 한 번만 계산해 모든 equity 경로와 metric 에 공유.
        funding_costs, funding_incomplete = (
            _funding_cost_by_bar(
                trades, ohlcv, funding_rates, freq=cfg.freq, warnings=state.warnings
            )
            if funding_rates is not None
            else (None, None)
        )
        total_funding = (
            sum(funding_costs, start=Decimal("0")) if funding_costs is not None else None
        )
        equity = _compute_equity_curve(
            trades, ohlcv, cfg, funding_rates=funding_rates, funding_costs=funding_costs
        )
        # TV parity — intrabar equity 극값 근사 (별도 pass, close 커브 무변경).
        extremes = (
            _compute_equity_extremes(
                trades,
                ohlcv,
                cfg,
                close_equity=equity,
                funding_costs=funding_costs,
                warnings=state.warnings,
            )
            if trades
            else None
        )
        metrics = _compute_metrics(
            trades,
            equity,
            cfg,
            ohlcv,
            funding_data_incomplete=funding_incomplete,
            total_funding=total_funding,
            equity_extremes=extremes,
        )
    except Exception as exc:
        logger.exception("v2_adapter_build_failed")
        return BacktestOutcome(
            status="error",
            parse=_stub_parse_outcome(source, status="error"),
            result=None,
            error=str(exc),
        )

    result = BacktestResult(
        metrics=metrics,
        equity_curve=equity,
        trades=trades,
        config_used=cfg,
    )
    logger.info(
        "v2_adapter_ok",
        extra={
            "track": v2.track,
            "num_trades": metrics.num_trades,
            "total_return": str(metrics.total_return),
        },
    )
    return BacktestOutcome(
        status="ok",
        # Sprint 23 codex G.2 P1 #2 — strategy.exit NOP 등 state.warnings 전파.
        # 사용자가 silent success 받지 않도록 BacktestOutcome.parse.warnings 노출.
        parse=_stub_parse_outcome(
            source, status="ok", warnings=list(state.warnings) if state else None
        ),
        result=result,
        error=None,
    )


# --- extraction ----------------------------------------------------------


def _extract_state_and_errors(
    v2: V2RunResult,
) -> tuple[StrategyState | None, list[tuple[int, str]]]:
    if v2.track in ("S", "M") and v2.historical is not None:
        return v2.historical.strategy_state, list(v2.historical.errors)
    if v2.track == "A" and v2.virtual is not None:
        return v2.virtual.strategy_state, list(v2.virtual.errors)
    return None, []


# --- cost model ----------------------------------------------------------


def _leg_cost(
    notional: Decimal,
    *,
    fill_type: Literal["taker", "maker"],
    taker_fee: Decimal,
    slippage: Decimal,
    maker_fee: Decimal = Decimal("0"),
) -> tuple[Decimal, Decimal]:
    """단일 체결(leg)의 (수수료, 슬리피지) 비용 — C8 선물형 비용모델 SSOT.

    - taker(시장가·트리거 체결): taker_fee 적용 + slippage 적용.
    - maker(resting post-only limit 체결): maker_fee 적용 + slippage 면제(limit 제외).

    grounding: pine_v2 엔진의 모든 실제 체결은 taker 이다(strategy.entry/close/
    close_all = 시장가 current_close, stop= = 트리거; limit/strategy.exit 은 H2
    NOP, BL-098/BL-104). 따라서 엔진 caller 는 항상 fill_type="taker" 이며 maker_fee
    인자를 전달하지 않는다. maker 분기 + 비용모델은 resting-limit fill producer
    (BL-104) 도입 시 활성될 forward 모델로, 본 helper 단위 테스트가 정확성을 고정.
    본 helper 가 _build_raw_trades / _compute_metrics / _compute_equity_curve 3 경로의
    비용 공식 단일 출처(Slice 1 ponytail 중복 제거).
    """
    if fill_type == "maker":
        return notional * maker_fee, Decimal("0")
    return notional * taker_fee, notional * slippage


# --- trades --------------------------------------------------------------


def _trade_excursion(
    t: Trade,
    highs: list[Decimal],
    lows: list[Decimal],
    entry_price: Decimal,
    qty: Decimal,
) -> tuple[Decimal, Decimal]:
    """확실한 보유 봉과 체결가의 gross excursion. 부분 봉의 경로는 추측하지 않는다."""
    period = HoldingPeriod(t.entry_bar, t.exit_bar, t.entry_phase, t.exit_phase)
    bars = period.full_bars(len(highs) - 1)
    endpoints = [entry_price]
    if t.exit_price is not None:
        endpoints.append(Decimal(str(t.exit_price)))
    window_high = max(endpoints + [highs[i] for i in bars])
    window_low = min(endpoints + [lows[i] for i in bars])
    if t.direction == "long":
        favorable = (window_high - entry_price) * qty
        adverse = (entry_price - window_low) * qty
    else:
        favorable = (entry_price - window_low) * qty
        adverse = (window_high - entry_price) * qty
    zero = Decimal("0")
    return max(zero, favorable), max(zero, adverse)


def _build_raw_trades(
    state: StrategyState,
    cfg: BacktestConfig,
    ohlcv: pd.DataFrame | None = None,
) -> list[RawTrade]:
    """StrategyState → RawTrade 목록.

    ohlcv 전달 시 per-trade run-up/drawdown(MFE/MAE) 을 bar high/low 로 계산
    (TV Trades parity). None 이면 excursion 필드만 None — 기존 직접 호출
    테스트 호환 (keyword-optional, blast radius 0).

    ★3단 계약 1/3 (BL-391) — 이 함수가 내는 `RawTrade.pnl` 은 수수료·슬리피지를
    차감한 **net** 이다(`net_pnl = gross_pnl - fees_total`). 다음 두 단계가 그것을
    전제로 한다: `_compute_equity_curve` 는 exit bar 에서 이 값을 그대로 실현
    누적하고, `_compute_metrics` 는 `net_profit_abs` 로 합산한다. 여기서 비용 규약을
    바꾸면 세 단계가 함께 움직여야 한다.
    불변식 검증 = `tests/backtest/test_cross_stage_reconciliation.py`.
    """
    all_trades: list[Trade] = list(state.closed_trades) + list(state.open_trades.values())
    # 체결 순서 = entry_bar 오름차순 (같은 bar 면 기존 리스트 순서 유지)
    all_trades.sort(key=lambda t: (t.entry_bar, 0 if t.is_open else 1))

    # excursion 용 high/low Decimal 프리컴퓨트 (1회, per-trade 스캔 공유).
    highs: list[Decimal] | None = None
    lows: list[Decimal] | None = None
    if ohlcv is not None and len(ohlcv) > 0:
        highs = [Decimal(str(v)) for v in ohlcv["high"]]
        lows = [Decimal(str(v)) for v in ohlcv["low"]]

    raw: list[RawTrade] = []
    running_pnl = Decimal("0")  # cumulative_pnl — trade_index(entry 순) 누적
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    maker_fee = Decimal(str(cfg.maker_fee))
    for idx, t in enumerate(all_trades):
        entry_price = Decimal(str(t.entry_price))
        qty = Decimal(str(t.qty))
        exit_price: Decimal | None = (
            Decimal(str(t.exit_price)) if t.exit_price is not None else None
        )

        # 수수료/슬리피지 = _leg_cost SSOT 위임. 현재 모든 체결 taker (grounding
        # _leg_cost docstring). entry leg 항상 + exit leg 는 closed 만.
        entry_fee, entry_slip = _leg_cost(
            entry_price * qty,
            fill_type="taker",
            taker_fee=taker_fee,
            slippage=slip_rate,
        )
        if exit_price is not None:
            # BL-104 — exit leg fill_type 라우팅: TP=maker(slippage 면제), SL/Trail=taker.
            # exit_kind 미태그(market close/flip) → taker (byte-identical).
            exit_fill = fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"
            exit_fee, exit_slip = _leg_cost(
                exit_price * qty,
                fill_type=exit_fill,
                taker_fee=taker_fee,
                slippage=slip_rate,
                maker_fee=maker_fee,
            )
        else:
            exit_fee = exit_slip = Decimal("0")
        fees_total = entry_fee + exit_fee + entry_slip + exit_slip

        # PnL (수수료 차감 전 원시값 → 수수료 차감)
        if exit_price is not None:
            # Trade.pnl은 float 공간의 차감 결과다. 종료된 거래는 원래 가격·수량을
            # Decimal로 바꾼 뒤 계산해야 100.3 - 100.1이 정확히 0.2가 된다.
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            gross_pnl = (exit_price - entry_price) * qty * direction_sign
        elif t.pnl is not None:
            gross_pnl = Decimal(str(t.pnl))
        else:
            gross_pnl = Decimal("0")
        net_pnl = gross_pnl - fees_total

        # return_pct = net_pnl / (entry_price * qty)
        notional = entry_price * qty
        return_pct = net_pnl / notional if notional != 0 else Decimal("0")

        # --- TV Trades parity 확장 필드 ---
        runup_abs: Decimal | None = None
        runup_pct: Decimal | None = None
        drawdown_abs: Decimal | None = None
        drawdown_pct: Decimal | None = None
        if highs is not None and lows is not None:
            runup_abs, drawdown_abs = _trade_excursion(t, highs, lows, entry_price, qty)
            runup_pct = runup_abs / notional if notional != 0 else Decimal("0")
            drawdown_pct = drawdown_abs / notional if notional != 0 else Decimal("0")
        bars_in_trade = int(t.exit_bar - t.entry_bar) if t.exit_bar is not None else None
        running_pnl += net_pnl

        raw.append(
            RawTrade(
                trade_index=idx,
                direction=t.direction,
                status="closed" if t.exit_bar is not None else "open",
                entry_bar_index=int(t.entry_bar),
                exit_bar_index=int(t.exit_bar) if t.exit_bar is not None else None,
                entry_price=entry_price,
                exit_price=exit_price,
                size=qty,
                pnl=net_pnl,
                return_pct=return_pct,
                fees=fees_total,
                exit_kind=t.exit_kind,
                runup_abs=runup_abs,
                runup_pct=runup_pct,
                drawdown_abs=drawdown_abs,
                drawdown_pct=drawdown_pct,
                bars_in_trade=bars_in_trade,
                fee_paid=entry_fee + exit_fee,
                slippage_paid=entry_slip + exit_slip,
                comment=t.comment or None,
                cumulative_pnl=running_pnl,
                liquidated=t.liquidated,
                entry_phase=t.entry_phase,
                exit_phase=t.exit_phase,
            )
        )
    return raw


# --- equity curve --------------------------------------------------------


def _funding_coverage_incomplete(trades: list[RawTrade]) -> bool | None:
    """정산 일정의 증거가 없으면 완전성을 단정하지 않는다.

    저장된 rate의 min/max나 샘플 간격은 상품별 과거 정산 일정이 아니다.
    보유가 없을 때만 False이며, 실제 보유의 완전성은 현재 입력으로 미검증(None)이다.
    관측 정산을 반영하지 못한 사실이 있으면 호출부가 True로 올린다.
    """
    return None if trades else False


def _funding_cost_by_bar(
    trades: list[RawTrade],
    ohlcv: pd.DataFrame,
    funding_rates: pd.Series,
    *,
    freq: str,
    warnings: list[str] | None = None,
) -> tuple[list[Decimal], bool | None]:
    """관측 정산 비용 + 완전성(True=미반영 확인, False=불필요, None=미검증).

    funding은 수집된 정산 시각마다 보유 perp 포지션에 부과. settlement ts는
    이를 포함하는 bar 에 귀속(searchsorted). cost = notional(close*qty) * rate *
    direction_sign (long=+1 → rate>0 시 지불 equity↓ / short=-1 → 수취).
    닫힌 봉의 범위는 [시가 시각, 시가 시각 + cfg.freq)다. OHLCV 내부 gap은
    이전 봉으로 늘려 잡지 않는다. 정산 주기는 추측하지 않는다.
    """
    n = len(ohlcv)
    costs = [Decimal("0")] * n
    if freq not in _FREQ_HOURS_V2:
        raise ValueError(f"펀딩 계산의 봉 폭을 알 수 없습니다: freq={freq!r}")
    # 기존 봉 폭 매핑을 재사용하되, 미지원값의 24h fallback은 허용하지 않는다.
    bar_width_ns = int(_freq_to_hours_v2(freq) * 3600) * 1_000_000_000
    # int64 ns 로 변환해 bisect — pandas searchsorted overload/Hashable 타입 마찰 회피.
    bar_ns: list[int] = [t.value for t in pd.DatetimeIndex(ohlcv.index)]
    funding_ns: list[int] = [t.value for t in pd.DatetimeIndex(funding_rates.index)]
    funding_vals = list(funding_rates)
    periods = [
        HoldingPeriod(t.entry_bar_index, t.exit_bar_index, t.entry_phase, t.exit_phase)
        for t in trades
    ]
    uncertain = False
    missing_candle = False
    for ts_ns, rate_raw in zip(funding_ns, funding_vals, strict=True):
        rate = rate_raw if isinstance(rate_raw, Decimal) else Decimal(str(rate_raw))
        if not bar_ns or ts_ns < bar_ns[0] or ts_ns >= bar_ns[-1] + bar_width_ns:
            continue
        pos = bisect.bisect_right(bar_ns, ts_ns) - 1
        if ts_ns >= bar_ns[pos] + bar_width_ns:
            # 이전 봉 종료 시 열린 포지션만 이 gap의 정산과 관련된다.
            missing_candle |= any(
                t.entry_bar_index <= pos and (t.exit_bar_index is None or t.exit_bar_index > pos)
                for t in trades
            )
            continue
        close_px = Decimal(str(ohlcv["close"].iloc[pos]))
        for t, period in zip(trades, periods, strict=True):
            held = period.holds_at(pos)
            if held is None:
                uncertain = True
            if held is not True:
                continue
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            costs[pos] += close_px * t.size * rate * direction_sign
    if uncertain and warnings is not None:
        warnings.append(
            "봉 내부 체결 시각을 알 수 없어 해당 체결 봉의 펀딩 정산을 반영하지 못했습니다."
        )
    if missing_candle and warnings is not None:
        warnings.append(
            "보유 중 관측된 펀딩 정산에 해당하는 OHLCV 봉이 없어 해당 정산을 반영하지 못했습니다."
        )
    incomplete = True if uncertain or missing_candle else _funding_coverage_incomplete(trades)
    return costs, incomplete


def _compute_equity_curve(
    trades: list[RawTrade],
    ohlcv: pd.DataFrame,
    cfg: BacktestConfig,
    funding_rates: pd.Series | None = None,
    funding_costs: list[Decimal] | None = None,
) -> pd.Series:
    """bar-by-bar equity 재구성.

    각 bar 에 대해:
      equity[bar] = init_cash
                  + Σ net_pnl (exit_bar_index <= bar)
                  + Σ unrealized_position_pnl (open/aboutToExit, entry 비용 차감 포함)

    unrealized_position_pnl = (close[bar] - entry_price) * qty * direction_sign
                            - entry_cost (fee + slip at entry)

    exit 비용은 실현 시점에 net_pnl 에 반영되므로 MTM 구간에서는 entry 비용만
    차감한다. 수수료/슬리피지 미반영 equity 로 Sharpe/DD 가 낙관 편향되는
    것을 방지 (Codex review P1).

    Decimal-first 합산을 위해 반환 Series 는 dtype=object 로 Decimal 을 보관한다.

    ★3단 계약 2/3 (BL-391) — 전 trade 가 closed 이고 funding 이 없으면
    `equity[-1] - init_cash == Σ trade.pnl` 이어야 한다. exit bar 에서 실현과
    평가가 겹치면(`exit_bar_index <= bar_idx` 를 `<` 로 쓰면) 그 trade 의 pnl 이
    두 번 셰여 이 등식이 깨진다.
    불변식 검증 = `tests/backtest/test_cross_stage_reconciliation.py`.
    """
    n = len(ohlcv)
    init_cash = cfg.init_cash
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))

    values: list[Decimal] = []

    # C6 funding accrual — funding_rates 제공 시 정산 경계마다 보유 포지션 funding
    # 누적 차감 (None = 회귀 0, 기존 동작 byte-identical).
    funding_by_bar = funding_costs
    if funding_by_bar is None and funding_rates is not None:
        funding_by_bar = _funding_cost_by_bar(trades, ohlcv, funding_rates, freq=cfg.freq)[0]

    # exit bar 별 realized pnl 누적
    exits_by_bar: dict[int, list[RawTrade]] = {}
    for t in trades:
        if t.exit_bar_index is not None:
            exits_by_bar.setdefault(t.exit_bar_index, []).append(t)

    realized_cum = Decimal("0")
    funding_cum = Decimal("0")
    for bar_idx in range(n):
        # 이 bar 에 exit 된 trade pnl 을 실현 누적에 추가 (bar 종료 시점 관점)
        for t in exits_by_bar.get(bar_idx, []):
            realized_cum += t.pnl
        if funding_by_bar is not None:
            funding_cum += funding_by_bar[bar_idx]

        # close price — numpy/float 소스라도 str() 경유로 Decimal 진입
        close_raw = ohlcv["close"].iloc[bar_idx]
        close_px = Decimal(str(close_raw))

        unrealized = Decimal("0")
        for t in trades:
            if t.entry_bar_index > bar_idx:
                continue
            # 아직 exit 안 된 포지션만 mark-to-market — open 이거나 (closed 이지만 이 bar 이후 exit)
            if t.status == "closed":
                assert t.exit_bar_index is not None
                if t.exit_bar_index <= bar_idx:
                    continue
            direction_sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            price_pnl = (close_px - t.entry_price) * t.size * direction_sign
            # entry leg 비용 (taker fee + slippage) — _leg_cost SSOT 위임.
            entry_fee, entry_slip = _leg_cost(
                t.entry_price * t.size,
                fill_type="taker",
                taker_fee=taker_fee,
                slippage=slip_rate,
            )
            unrealized += price_pnl - (entry_fee + entry_slip)

        values.append(init_cash + realized_cum + unrealized - funding_cum)

    # object dtype 으로 Decimal 을 보관 — float drift 방지.
    return pd.Series(values, index=ohlcv.index, dtype=object)


# --- metrics -------------------------------------------------------------


def _compute_equity_extremes(
    trades: list[RawTrade],
    ohlcv: pd.DataFrame,
    cfg: BacktestConfig,
    *,
    close_equity: pd.Series,
    funding_costs: list[Decimal] | None = None,
    warnings: list[str] | None = None,
) -> tuple[list[Decimal], list[Decimal]]:
    """확실한 시가·종가 equity와 전체 보유 봉의 고저가로 계산하는 근사.

    미상 체결이 노출을 바꾼 봉은 wick을 합성하지 않는다. 고저가의 실제 발생
    순서는 복원하지 않으며, 펀딩은 기존처럼 봉 총액을 모든 후보에 선차감한다.
    따라서 정산과 고저가의 선후관계까지 재현한 equity 경로는 아니다.
    """
    n = len(ohlcv)
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    positions = []
    exits_by_bar: dict[int, list[RawTrade]] = {}
    uncertain_bars: set[int] = set()
    for t in trades:
        period = HoldingPeriod(t.entry_bar_index, t.exit_bar_index, t.entry_phase, t.exit_phase)
        entry_fee, entry_slip = _leg_cost(
            t.entry_price * t.size,
            fill_type="taker",
            taker_fee=taker_fee,
            slippage=slip_rate,
        )
        signed_qty = t.size if t.direction == "long" else -t.size
        positions.append((t, period.full_bars(n - 1), signed_qty, entry_fee + entry_slip))
        if t.entry_phase == "intrabar_unknown":
            uncertain_bars.add(t.entry_bar_index)
        if t.exit_bar_index is not None:
            exits_by_bar.setdefault(t.exit_bar_index, []).append(t)
            if t.exit_phase == "intrabar_unknown":
                uncertain_bars.add(t.exit_bar_index)
    if uncertain_bars and warnings is not None:
        warnings.append(
            "봉 내부 체결 시각을 알 수 없는 봉은 확실한 가격점만 반영해 "
            "봉내 상승·하락 근사를 계산했습니다."
        )

    highs_out: list[Decimal] = []
    lows_out: list[Decimal] = []
    realized_cum = Decimal("0")
    funding_cum = Decimal("0")
    for bar_idx in range(n):
        if funding_costs is not None:
            funding_cum += funding_costs[bar_idx]
        base = cfg.init_cash + realized_cum - funding_cum
        open_px = Decimal(str(ohlcv["open"].iloc[bar_idx]))
        high_px = Decimal(str(ohlcv["high"].iloc[bar_idx]))
        low_px = Decimal(str(ohlcv["low"].iloc[bar_idx]))
        # 시가 주문을 처리하기 전의 기존 보유 평가: 갭과 청산 직전 비용을 보존한다.
        before_open = base
        open_exits = sum(
            (t.pnl for t in exits_by_bar.get(bar_idx, []) if t.exit_phase == "bar_open"),
            start=Decimal("0"),
        )
        at_high = at_low = base + open_exits
        for t, full_bars, signed_qty, entry_cost in positions:
            if t.entry_bar_index < bar_idx and (
                t.exit_bar_index is None or t.exit_bar_index >= bar_idx
            ):
                before_open += (open_px - t.entry_price) * signed_qty - entry_cost
            if bar_idx in full_bars:
                # 같은 가격에서 평가한다. 서로 다른 포지션의 유리한 극값을 더하지 않는다.
                at_high += (high_px - t.entry_price) * signed_qty - entry_cost
                at_low += (low_px - t.entry_price) * signed_qty - entry_cost
        candidates = [before_open, close_equity.iloc[bar_idx]]
        if bar_idx not in uncertain_bars:
            candidates.extend((at_high, at_low))
        highs_out.append(max(candidates))
        lows_out.append(min(candidates))
        # 종가/미상 청산의 실현손익은 현재 봉 wick에 소급하지 않는다.
        realized_cum += sum((t.pnl for t in exits_by_bar.get(bar_idx, [])), start=Decimal("0"))
    return highs_out, lows_out


def _compute_metrics(
    trades: list[RawTrade],
    equity: pd.Series,
    cfg: BacktestConfig,
    ohlcv: pd.DataFrame | None = None,
    funding_data_incomplete: bool | None = None,
    total_funding: Decimal | None = None,
    equity_extremes: tuple[list[Decimal], list[Decimal]] | None = None,
) -> BacktestMetrics:
    """RawTrade list + equity curve → BacktestMetrics.

    필드 수의 SSOT 는 dataclass + `tests/backtest/test_metrics_field_parity.py`
    tripwire 이다.

    Sprint 31 BL-154: pine_v2 엔진 production path 에 신규 12 metric 직접
    계산 (RawTrade + equity Series 만 사용). 구 vectorbt 기반
    `extract_metrics` (engine/metrics.py — 파일은 남아 있다) 와 알고리즘 정합:
      - avg_holding_hours: (exit_bar - entry_bar) * freq_to_hours
      - consecutive_*_max: closed PnL 부호 streak
      - long/short_win_rate_pct: direction 별 win_rate
      - monthly_returns: equity → daily returns → resample('ME') → cumprod
      - drawdown_curve / drawdown_duration: running_max 대비 % + 연속 음수 bars
      - annual_return_pct (CAGR): (1+total)^(1/years)-1
      - avg/best/worst_trade_pct: closed return_pct mean/max/min
      - total_trades: num_trades alias

    `ohlcv` 는 monthly_returns / drawdown_curve 의 timestamp 매핑용. None
    이면 monthly/drawdown_curve 는 None 반환 (graceful degrade — 기존
    fixture 호환).

    ★3단 계약 3/3 (BL-391) — 이 함수는 **서로 다른 두 입력**에서 같은 사실을
    두 번 센다: `net_profit_abs` 는 trade 목록에서, `total_return` 은 equity
    종가에서. 코드가 둘의 일치를 강제하지 않으므로
    `net_profit_abs == total_return * init_cash` 는 동어반복이 아니라 검증 가능한
    계약이다(closed-trade · no-funding 조건). 실측 — `net_profit_abs` 에서 비용을
    한 번 더 빼는 변조는 기존 backtest 스위트 557건을 **전부 통과**했고 이 계약만
    잡았다. 불변식 검증 = `tests/backtest/test_cross_stage_reconciliation.py`.
    """
    closed = [t for t in trades if t.status == "closed"]
    num_trades = len(closed)
    init_cash = cfg.init_cash

    # equity 는 dtype=object 에 Decimal 을 보관. 마지막 원소를 Decimal 그대로 사용해
    # float drift 없이 total_return 을 계산한다.
    if len(equity) > 0:
        last = equity.iloc[-1]
        final_equity = last if isinstance(last, Decimal) else Decimal(str(last))
    else:
        final_equity = init_cash

    total_return = (final_equity - init_cash) / init_cash if init_cash != 0 else Decimal("0")
    if total_return.is_nan():
        total_return = Decimal("0")

    # Sharpe/MDD 는 근사 지표 — float 변환하여 numpy/pandas 연산 활용.
    equity_float = _as_float_series(equity)
    sharpe_ratio_value, sharpe_convention = sharpe_ratio(equity_float)
    max_drawdown = _max_drawdown(equity_float)
    # Sprint 32-D BL-156: MDD 수학 정합 메타.
    # leverage=1 가정 하에서 MDD < -1.0 (= -100%) 는 수학적으로 자본 초과 손실
    # → 사용자 신뢰 quality 측면에서 명시적 표시 의무. pine_v2 엔진은 leverage
    # 를 PnL 에 직접 적용 안 함 (qty=절대 수량) → equity 음수 가능 → MDD 가
    # 자유롭게 -1.0 미만으로 갈 수 있음. 응답에 명시적 boolean 으로 노출하면
    # FE 가 "leverage Nx 가정" 라벨을 inline 으로 표시 가능.
    mdd_exceeds_capital = max_drawdown < Decimal("-1")

    win_count = sum(1 for t in closed if t.pnl > 0)
    win_rate = Decimal(win_count) / Decimal(num_trades) if num_trades > 0 else Decimal("0")

    long_count = sum(1 for t in closed if t.direction == "long") if num_trades > 0 else 0
    short_count = sum(1 for t in closed if t.direction == "short") if num_trades > 0 else 0

    if num_trades > 0:
        wins = [t.return_pct for t in closed if t.pnl > 0]
        losses = [t.return_pct for t in closed if t.pnl < 0]
        avg_win = _mean(wins) if wins else None
        avg_loss = _mean(losses) if losses else None
        gross_profit = sum((t.pnl for t in closed if t.pnl > 0), start=Decimal("0"))
        gross_loss_abs = sum((-t.pnl for t in closed if t.pnl < 0), start=Decimal("0"))
        profit_factor: Decimal | None = (
            gross_profit / gross_loss_abs if gross_loss_abs > 0 else None
        )
    else:
        avg_win = None
        avg_loss = None
        profit_factor = None

    # --- Sprint 31 BL-154: 신규 12 metric (RawTrade + equity 기반 직접 계산) ---
    avg_holding_hours = _v2_avg_holding_hours(closed, cfg.freq) if num_trades > 0 else None
    consecutive_wins_max, consecutive_losses_max = (
        _v2_streaks(closed) if num_trades > 0 else (None, None)
    )
    long_win_rate_pct = _v2_side_win_rate(closed, "long") if num_trades > 0 else None
    short_win_rate_pct = _v2_side_win_rate(closed, "short") if num_trades > 0 else None
    monthly_returns = _v2_monthly_returns(equity_float, ohlcv)
    drawdown_curve, drawdown_duration = _v2_drawdown_extract(equity_float, ohlcv)
    annual_return_pct = _v2_annual_return(total_return, ohlcv)
    avg_trade_pct, best_trade_pct, worst_trade_pct = (
        _v2_trade_returns_stats(closed) if num_trades > 0 else (None, None, None)
    )
    total_trades_alias: int | None = num_trades  # PRD parity alias
    # Sprint 34 BL-175: Buy & Hold curve (정확 OHLCV close 기반).
    buy_and_hold_curve = _v2_buy_and_hold_curve(ohlcv, init_cash)

    # --- TV Strategy Tester parity 팩 ---
    # 절대금액 계열 (closed net pnl, Decimal 정확 합산).
    net_profit_abs = sum((t.pnl for t in closed), start=Decimal("0"))
    gross_profit_abs = sum((t.pnl for t in closed if t.pnl > 0), start=Decimal("0"))
    gross_loss_abs_v = sum((-t.pnl for t in closed if t.pnl < 0), start=Decimal("0"))
    win_pnls = [t.pnl for t in closed if t.pnl > 0]
    loss_pnls = [t.pnl for t in closed if t.pnl < 0]
    largest_win_abs = max(win_pnls) if win_pnls else None
    largest_loss_abs = min(loss_pnls) if loss_pnls else None
    avg_trade_abs = net_profit_abs / num_trades if num_trades > 0 else None
    avg_win_abs = _mean(win_pnls) if win_pnls else None
    avg_loss_abs = _mean(loss_pnls) if loss_pnls else None
    ratio_avg_win_loss = (
        avg_win_abs / abs(avg_loss_abs)
        if avg_win_abs is not None and avg_loss_abs is not None and avg_loss_abs != 0
        else None
    )
    open_trades = [t for t in trades if t.status == "open"]
    total_open_trades = len(open_trades)
    # open_pnl = Σ open [(last_close - entry)*size*sign - 비용(fees=entry leg)].
    # equity 커브의 미실현 정의와 동일. ohlcv 미전달 + open 존재 시 None (mark 불가).
    open_pnl: Decimal | None
    if not open_trades:
        open_pnl = Decimal("0")
    elif ohlcv is None or len(ohlcv) == 0:
        open_pnl = None
    else:
        last_close = Decimal(str(ohlcv["close"].iloc[-1]))
        open_pnl = Decimal("0")
        for t in open_trades:
            sign = Decimal("1") if t.direction == "long" else Decimal("-1")
            open_pnl += (last_close - t.entry_price) * t.size * sign - t.fees
    # 보유 bar 수 (closed, exit-entry — RawTrade.bars_in_trade 유무와 무관하게 산출).
    bars_all = [
        Decimal(t.exit_bar_index - t.entry_bar_index)
        for t in closed
        if t.exit_bar_index is not None
    ]
    bars_win = [
        Decimal(t.exit_bar_index - t.entry_bar_index)
        for t in closed
        if t.exit_bar_index is not None and t.pnl > 0
    ]
    bars_loss = [
        Decimal(t.exit_bar_index - t.entry_bar_index)
        for t in closed
        if t.exit_bar_index is not None and t.pnl < 0
    ]
    avg_bars_in_trade = _mean(bars_all) if bars_all else None
    avg_bars_in_winning = _mean(bars_win) if bars_win else None
    avg_bars_in_losing = _mean(bars_loss) if bars_loss else None
    per_side = compute_side_metrics(closed)
    extremes_high, extremes_low = equity_extremes if equity_extremes is not None else (None, None)
    excursion_stats = compute_excursion_stats(equity, extremes_high, extremes_low)
    # sortino/calmar 실구현 (TV convention — engine/metrics.py docstring ground).
    # trades 0건 = flat equity → sortino 가 항상 -1 (전 기간 RFR 미달) 로 무의미
    # → None 게이트 (TV 도 무거래 시 공란).
    sortino = sortino_ratio(equity_float) if trades else None
    calmar = calmar_ratio(annual_return_pct, max_drawdown)
    liquidation_count = (
        sum(t.liquidated is True for t in closed) if is_leverage_active(cfg.leverage) else None
    )
    liquidation_occurred = liquidation_count > 0 if liquidation_count is not None else None

    # C14 (정직성) — 총 수수료/슬리피지 분해 집계. TV Trades parity 확장으로
    # RawTrade 가 fee_paid/slippage_paid split 을 직접 보유 → 재계산 없이 합산
    # (production path 의 _leg_cost 중복 루프 제거). split 미보유 trade (테스트가
    # RawTrade 를 직접 조립한 경우) 만 legacy _leg_cost 재계산 fallback.
    # 불변식 보존: total_fees + total_slippage == Σ RawTrade.fees.
    taker_fee = Decimal(str(cfg.fees))
    slip_rate = Decimal(str(cfg.slippage))
    maker_fee = Decimal(str(cfg.maker_fee))
    total_fees = Decimal("0")
    total_slippage = Decimal("0")
    for t in trades:
        if t.fee_paid is not None and t.slippage_paid is not None:
            total_fees += t.fee_paid
            total_slippage += t.slippage_paid
            continue
        entry_fee, entry_slip = _leg_cost(
            t.entry_price * t.size,
            fill_type="taker",
            taker_fee=taker_fee,
            slippage=slip_rate,
        )
        total_fees += entry_fee
        total_slippage += entry_slip
        if t.exit_price is not None:
            # BL-104 — exit leg fill_type 라우팅 (_build_raw_trades 와 동일 SSOT).
            exit_fill = fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"
            exit_fee, exit_slip = _leg_cost(
                t.exit_price * t.size,
                fill_type=exit_fill,
                taker_fee=taker_fee,
                slippage=slip_rate,
                maker_fee=maker_fee,
            )
            total_fees += exit_fee
            total_slippage += exit_slip

    return BacktestMetrics(
        total_return=total_return,
        sharpe_ratio=sharpe_ratio_value,
        sharpe_convention=sharpe_convention,
        liquidation_occurred=liquidation_occurred,
        liquidation_count=liquidation_count,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        num_trades=num_trades,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        long_count=long_count,
        short_count=short_count,
        avg_holding_hours=avg_holding_hours,
        consecutive_wins_max=consecutive_wins_max,
        consecutive_losses_max=consecutive_losses_max,
        long_win_rate_pct=long_win_rate_pct,
        short_win_rate_pct=short_win_rate_pct,
        monthly_returns=monthly_returns,
        drawdown_duration=drawdown_duration,
        annual_return_pct=annual_return_pct,
        total_trades=total_trades_alias,
        avg_trade_pct=avg_trade_pct,
        best_trade_pct=best_trade_pct,
        worst_trade_pct=worst_trade_pct,
        drawdown_curve=drawdown_curve,
        # Sprint 32-D BL-156: MDD 수학 정합 메타 (FE 카드 inline 표시용).
        mdd_unit="equity_ratio",
        mdd_exceeds_capital=mdd_exceeds_capital,
        # Sprint 34 BL-175: Buy & Hold curve (정확 OHLCV 기반).
        buy_and_hold_curve=buy_and_hold_curve,
        # C14 (정직성) — 총 수수료/슬리피지 분해 (헤드라인 net 표시용).
        total_fees=total_fees,
        total_slippage=total_slippage,
        # C6 (정직성) — funding 차감 시 보유 구간 일부가 funding 데이터 범위 밖이면 True.
        funding_data_incomplete=funding_data_incomplete,
        total_funding=total_funding,
        # TV parity 팩.
        net_profit_abs=net_profit_abs,
        gross_profit_abs=gross_profit_abs,
        gross_loss_abs=gross_loss_abs_v,
        open_pnl=open_pnl,
        largest_win_abs=largest_win_abs,
        largest_loss_abs=largest_loss_abs,
        avg_trade_abs=avg_trade_abs,
        avg_win_abs=avg_win_abs,
        avg_loss_abs=avg_loss_abs,
        ratio_avg_win_loss=ratio_avg_win_loss,
        total_open_trades=total_open_trades,
        avg_bars_in_trade=avg_bars_in_trade,
        avg_bars_in_winning_trades=avg_bars_in_winning,
        avg_bars_in_losing_trades=avg_bars_in_losing,
        per_side=per_side,
        excursion_stats=excursion_stats,
    )


# --- Sprint 31 BL-154: pine_v2 path 신규 12 metric helper ---

# pandas offset alias → bar 1개 당 시간 (engine/metrics.py 와 정합).
# P1-5 (2026-05-30 정검): config_mapper.timeframe_to_freq 는 1m/5m/15m 을
# pandas 표준 alias '1min'/'5min'/'15min' 로 산출하므로 'min' alias 키도 필수.
# 누락 시 24h fallback 으로 avg_holding_hours 가 1440x/288x/96x 과대 계산.
_FREQ_HOURS_V2: dict[str, float] = {
    "1m": 1.0 / 60.0,
    "1min": 1.0 / 60.0,
    "5m": 5.0 / 60.0,
    "5min": 5.0 / 60.0,
    "15m": 15.0 / 60.0,
    "15min": 15.0 / 60.0,
    "30m": 30.0 / 60.0,
    "30min": 30.0 / 60.0,
    "1h": 1.0,
    "2h": 2.0,
    "4h": 4.0,
    "8h": 8.0,
    "12h": 12.0,
    "1d": 24.0,
    "1D": 24.0,
    "D": 24.0,
}


def _freq_to_hours_v2(freq: str) -> float:
    """매핑 없으면 24h fallback (engine/metrics.py 와 동일)."""
    return _FREQ_HOURS_V2.get(freq, 24.0)


def _v2_buy_and_hold_curve(
    ohlcv: pd.DataFrame | None, init_cash: Decimal
) -> list[tuple[str, Decimal]] | None:
    """Buy & Hold benchmark curve — OHLCV 첫 close 가격에 init_cash 매수 후 보유.

    공식: bh[i] = init_cash * close[i] / close[0]
    timestamp 형식: equity_curve / drawdown_curve 와 동일 ISO ("YYYY-MM-DDTHH:MM:SSZ").

    **fail-closed 정책 (P1-3, Sprint 34 BL-175):**
    - ohlcv None 또는 "close" 컬럼 부재 → None
    - len(ohlcv) < 2 (1 bar 이하 → BH 의미 없음) → None
    - DatetimeIndex 가 아닌 경우 → None
    - 첫 close NaN 또는 <=0 → None (zero division 차단)
    - **임의 close NaN 또는 <=0 1건이라도 → None** (partial silent line = 거짓 trust 차단)

    full curve 가 valid 한 경우만 반환 → frontend BH series 미렌더 + ChartLegend
    BH 항목 자동 hide (Surface Trust ADR-019 정합).

    Decimal-first 합산: close 는 OHLCV 원본 dtype 이 float 이지만 Decimal(str(...))
    경유로 Decimal 공간에서 곱셈/나눗셈. equity_curve 와 동일 패턴.
    """
    if ohlcv is None or "close" not in ohlcv.columns:
        return None
    if len(ohlcv) < 2:
        return None
    if not isinstance(ohlcv.index, pd.DatetimeIndex):
        return None

    # 1차 fail-closed gate — 첫 close 검증.
    try:
        first_close = Decimal(str(ohlcv["close"].iloc[0]))
    except Exception:
        return None
    if first_close.is_nan() or first_close <= 0:
        return None

    # 2차 fail-closed gate — 모든 close 검증 (1건이라도 invalid → None 반환).
    closes_decimal: list[Decimal] = []
    for raw in ohlcv["close"]:
        try:
            c = Decimal(str(raw))
        except Exception:
            return None
        if c.is_nan() or c <= 0:
            return None  # partial silent line 차단
        closes_decimal.append(c)

    # 검증 통과 후만 curve 생성.
    curve: list[tuple[str, Decimal]] = []
    for ts, close_dec in zip(ohlcv.index, closes_decimal, strict=True):
        ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
        iso = ts_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        bh_value = init_cash * close_dec / first_close
        curve.append((iso, bh_value))

    return curve


def _v2_avg_holding_hours(closed: list[RawTrade], freq: str) -> Decimal | None:
    """closed trade 의 (exit_bar - entry_bar) * freq_to_hours 평균."""
    if not closed:
        return None
    bars: list[int] = []
    for t in closed:
        if t.exit_bar_index is None:
            continue
        bars.append(int(t.exit_bar_index) - int(t.entry_bar_index))
    if not bars:
        return None
    avg_bars = sum(bars) / len(bars)
    if not math.isfinite(avg_bars):
        return None
    return Decimal(str(avg_bars * _freq_to_hours_v2(freq)))


def _v2_streaks(closed: list[RawTrade]) -> tuple[int | None, int | None]:
    """closed trade PnL 부호 streak 최대값. 0 → 양쪽 reset."""
    if not closed:
        return (None, None)
    max_win = 0
    max_loss = 0
    cur_win = 0
    cur_loss = 0
    for t in closed:
        pnl = t.pnl
        if pnl > 0:
            cur_win += 1
            cur_loss = 0
            if cur_win > max_win:
                max_win = cur_win
        elif pnl < 0:
            cur_loss += 1
            cur_win = 0
            if cur_loss > max_loss:
                max_loss = cur_loss
        else:
            cur_win = 0
            cur_loss = 0
    return (int(max_win), int(max_loss))


def _v2_side_win_rate(closed: list[RawTrade], side: str) -> Decimal | None:
    """direction 별 win_rate. 해당 side 0건이면 None."""
    sub = [t for t in closed if t.direction == side]
    if not sub:
        return None
    win_count = sum(1 for t in sub if t.pnl > 0)
    return Decimal(win_count) / Decimal(len(sub))


def _v2_monthly_returns(
    equity_float: pd.Series, ohlcv: pd.DataFrame | None
) -> list[tuple[str, Decimal]] | None:
    """equity → daily returns → resample('ME') → ("YYYY-MM", Decimal). 1개월 미만 None."""
    if ohlcv is None or len(equity_float) < 2:
        return None
    try:
        # equity index 가 DatetimeIndex 라야 resample 가능. ohlcv.index 사용.
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            return None
        eq = pd.Series(equity_float.values, index=ohlcv.index, dtype=float)
        returns = eq.pct_change().dropna()
        if returns.empty:
            return None
        # 'ME' (Month End) — pandas 2.2+ deprecation 'M' → 'ME' 정합.
        monthly = returns.resample("ME").apply(lambda r: float((1.0 + r).prod() - 1.0))
        result: list[tuple[str, Decimal]] = []
        for ts, val in monthly.items():
            f = float(val)
            if not math.isfinite(f):
                continue
            ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
            key = ts_obj.strftime("%Y-%m")
            result.append((key, Decimal(str(f))))
        return result if result else None
    except Exception:
        return None


def _v2_drawdown_extract(
    equity_float: pd.Series, ohlcv: pd.DataFrame | None
) -> tuple[list[tuple[str, Decimal]] | None, int | None]:
    """equity → (running_max - equity) / running_max → curve + 최대 연속 음수 bars.

    drawdown_curve 는 timestamp 가 필요하므로 ohlcv 가 None 이면 (None, max_dur)
    반환 (max_dur 는 무관계로 계산 가능).
    """
    if len(equity_float) == 0:
        return (None, None)
    try:
        running_max = equity_float.cummax()
        # ZeroDivisionError 방어 — running_max 0 시 NaN 후 0 으로 fallback (math.isfinite 체크).
        dd = (equity_float - running_max) / running_max.replace(0, float("nan"))
        max_dur = 0
        cur_dur = 0
        curve: list[tuple[str, Decimal]] | None = None
        if ohlcv is not None and isinstance(ohlcv.index, pd.DatetimeIndex):
            curve_list: list[tuple[str, Decimal]] = []
            for ts, f in zip(ohlcv.index, dd.values, strict=True):
                f_val = float(f) if math.isfinite(float(f)) else 0.0
                ts_obj = pd.Timestamp(str(ts)) if not isinstance(ts, pd.Timestamp) else ts
                iso = ts_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
                curve_list.append((iso, Decimal(str(f_val))))
                if f_val < 0:
                    cur_dur += 1
                    if cur_dur > max_dur:
                        max_dur = cur_dur
                else:
                    cur_dur = 0
            curve = curve_list if curve_list else None
        else:
            for f in dd.values:
                f_val = float(f) if math.isfinite(float(f)) else 0.0
                if f_val < 0:
                    cur_dur += 1
                    if cur_dur > max_dur:
                        max_dur = cur_dur
                else:
                    cur_dur = 0
        return (curve, int(max_dur))
    except Exception:
        return (None, None)


def _v2_annual_return(total_return: Decimal, ohlcv: pd.DataFrame | None) -> Decimal | None:
    """CAGR = (1+total)^(1/years)-1. period < 1d 또는 base ≤ 0 시 None."""
    if ohlcv is None or len(ohlcv.index) < 2:
        return None
    try:
        idx = ohlcv.index
        if not isinstance(idx, pd.DatetimeIndex):
            return None
        start = pd.Timestamp(str(idx[0]))
        end = pd.Timestamp(str(idx[-1]))
        days = (end - start).total_seconds() / 86400.0
        if days <= 0:
            return None
        years = days / 365.25
        if years <= 0:
            return None
        total_f = float(total_return)
        if not math.isfinite(total_f):
            return None
        base = 1.0 + total_f
        if base <= 0:
            return None
        cagr = base ** (1.0 / years) - 1.0
        if not math.isfinite(cagr):
            return None
        return Decimal(str(cagr))
    except Exception:
        return None


def _v2_trade_returns_stats(
    closed: list[RawTrade],
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """closed return_pct mean / max / min. 빈 list 시 (None, None, None)."""
    if not closed:
        return (None, None, None)
    rets = [t.return_pct for t in closed]
    if not rets:
        return (None, None, None)
    avg = sum(rets, start=Decimal("0")) / Decimal(len(rets))
    best = max(rets)
    worst = min(rets)
    return (avg, best, worst)


def _as_float_series(equity: pd.Series) -> pd.Series:
    """Sharpe/MDD 계산용 Decimal → float 변환. object dtype 이면 원소별 float 화."""
    if equity.dtype == object:
        return pd.Series([float(v) for v in equity], index=equity.index, dtype=float)
    return equity.astype(float)


def _max_drawdown(equity: pd.Series) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max
    min_dd = float(dd.min())
    if not math.isfinite(min_dd):
        return Decimal("0")
    return Decimal(str(min_dd))


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


# --- ParseOutcome stub ---------------------------------------------------


def _stub_parse_outcome(
    source: str,
    *,
    status: Literal["ok", "unsupported", "error"] = "ok",
    warnings: list[str] | None = None,
) -> ParseOutcome:
    """pine_v2 경로는 ParseOutcome 을 생성하지 않음. legacy 필드 호환용 최소 stub.

    BacktestOutcome.parse 필드가 non-optional 이라 최소 구조를 채워주되, 실패
    경로에서는 status="error" 를 넘겨 소비자가 파싱 상태를 오해하지 않도록 한다.
    entries/exits 시리즈는 구 엔진 SignalResult 용이라 pine_v2 경로에선 빈 값.
    실제 파싱 판정은 strategy service `_parse` 가 pine_v2 기반으로 수행한다.

    Sprint 23 codex G.2 P1 #2: warnings= 인자로 strategy_state.warnings (BL-098
    strategy.exit NOP 등) 를 BacktestOutcome.parse.warnings 로 전파. 사용자가
    silent success 받지 않도록.
    """
    version: Literal["v4", "v5"] = _detect_version(source)
    empty = SignalResult(
        entries=pd.Series(dtype=bool),
        exits=pd.Series(dtype=bool),
    )
    return ParseOutcome(
        status=status,
        source_version=version,
        result=empty,
        error=None,
        supported_feature_report={"functions_used": []},
        warnings=list(warnings) if warnings else [],
    )


def _detect_version(source: str) -> Literal["v4", "v5"]:
    m = _VERSION_RE.search(source)
    if m is None:
        return "v5"
    try:
        v = int(m.group(1))
    except ValueError:
        return "v5"
    return "v4" if v == 4 else "v5"


__all__ = ["run_backtest_v2"]
