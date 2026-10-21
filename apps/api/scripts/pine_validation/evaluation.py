"""검증 일치 판정과 분리한 실제 엔진의 시간 구간별 비용 포함 성과 측정."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.pine_validation.models import utc_time
from scripts.pine_validation.strategy_adapter import adapt_strategy
from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import run_backtest_v2


def validate_evaluation(plan: Mapping[str, Any], window: Mapping[str, Any]) -> None:
    """결과를 보기 전에 고정할 정책을 읽는다. 시각 선언은 사전등록의 증거가 아니다."""
    start, end = (utc_time(window[key]) for key in ("start", "end"))
    validation, holdout = (utc_time(plan[key]) for key in ("validation_start", "holdout_start"))
    utc_time(plan["registered_at"])
    if not start < validation < holdout < end:
        raise ValueError("성과 구간은 train < validation < holdout 순서여야 합니다")
    if any(
        at != at.replace(hour=0, minute=0, second=0, microsecond=0)
        for at in (start, validation, holdout, end)
    ):
        raise ValueError("세 타임프레임에 공통인 UTC 일봉 경계가 필요합니다")
    for key in ("init_cash", "position_size_pct", "fees", "slippage"):
        try:
            value = Decimal(str(plan[key]))
        except InvalidOperation as exc:
            raise ValueError(f"유효한 {key}가 필요합니다") from exc
        if not value.is_finite() or value < 0:
            raise ValueError(f"{key}는 유한한 음이 아닌 값이어야 합니다")
        if key in {"init_cash", "position_size_pct"} and value == 0:
            raise ValueError(f"{key}는 양수여야 합니다")
        if key == "position_size_pct" and value > 100:
            raise ValueError("포지션 크기는 자본의 100% 이하여야 합니다")
        if key in {"fees", "slippage"} and value >= 1:
            raise ValueError("비용률은 소수 비율로 1 미만이어야 합니다")
    if not isinstance(plan.get("cost_basis"), str) or not plan["cost_basis"].strip():
        raise ValueError("비용 가정의 출처 cost_basis가 필요합니다")


def load_funding(
    provenance: Mapping[str, Any] | None,
    base: Path,
) -> tuple[pd.Series | None, dict[str, Any] | None]:
    """관측 정산만 전달하며 빈 파일이나 출처 없는 수열을 비용 0의 증거로 쓰지 않는다."""
    if provenance is None:
        return None, None
    path = base / provenance["file"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != provenance["sha256"]:
        raise ValueError("펀딩 원본 hash가 다릅니다")
    if provenance["symbol"] != "BYBIT:BTCUSDT.P" or not provenance["source"]:
        raise ValueError("같은 시장의 펀딩 출처가 필요합니다")
    utc_time(provenance["observed_at"])
    data = pd.read_csv(path, dtype=str)
    index = pd.DatetimeIndex([utc_time(value) for value in data["time"]])
    try:
        rates = [Decimal(value) for value in data["rate"]]
    except InvalidOperation as exc:
        raise ValueError("유효한 펀딩 rate가 필요합니다") from exc
    if (
        data.empty
        or index.has_duplicates
        or not index.is_monotonic_increasing
        or any(not rate.is_finite() for rate in rates)
    ):
        raise ValueError("펀딩은 중복 없는 시간순 유한 관측값이어야 합니다")
    return pd.Series(rates, index=index), dict(provenance)


def _json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def evaluate_performance(
    source: str,
    bindings: Sequence[Mapping[str, Any]],
    frame: pd.DataFrame,
    inputs: Mapping[str, Any],
    timeframe: str,
    window: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    funding_rates: pd.Series | None = None,
) -> dict[str, Any]:
    """고정 입력으로 세 구간과 전체 기간을 실행한다. 후보/파라미터를 탐색하지 않는다."""
    validate_evaluation(plan, window)
    start, end = (utc_time(window[key]) for key in ("start", "end"))
    validation, holdout = (utc_time(plan[key]) for key in ("validation_start", "holdout_start"))
    initial_cash = Decimal(str(plan["init_cash"]))
    step = pd.Timedelta({"1h": "1h", "4h": "4h", "1d": "1d"}[timeframe])
    runs = []
    for label, first, last in (
        ("train", start, validation),
        ("validation", validation, holdout),
        ("holdout", holdout, end),
        ("full", start, end),
    ):
        # 이전 이력은 지표 계산에만 쓰고 미래 봉은 실행기에 전달하지 않는다.
        prefix = frame.loc[frame.index + step <= last].copy()
        evaluation_index = prefix.index[prefix.index >= first]
        expected = pd.date_range(first, last, freq=step, inclusive="left")
        if prefix.empty or not evaluation_index.equals(expected):
            raise ValueError("성과 구간의 완결 OHLCV가 누락됐습니다")
        adaptation = adapt_strategy(source, bindings, trade_start=first, fixed_quantity=None)
        observed_funding = (
            funding_rates.loc[(funding_rates.index >= first) & (funding_rates.index < last)]
            if funding_rates is not None
            else None
        )
        for multiplier in (1, 2):
            config = BacktestConfig(
                init_cash=initial_cash,
                fees=float(Decimal(str(plan["fees"])) * multiplier),
                slippage=float(Decimal(str(plan["slippage"])) * multiplier),
                maker_fee=0,
                include_funding=observed_funding is not None,
                default_qty_type="strategy.percent_of_equity",
                default_qty_value=float(Decimal(str(plan["position_size_pct"]))),
                leverage=1,
                input_overrides=dict(inputs),
                freq="1D" if timeframe == "1d" else timeframe,
                fill_timing="next_bar_open",
            )
            outcome = run_backtest_v2(
                adaptation.strategy_source, prefix, config, funding_rates=observed_funding
            )
            run: dict[str, Any] = {
                "split": label,
                "cost_multiplier": multiplier,
                "status": outcome.status,
                "window": {"start": first, "end": last},
                "history_start": utc_time(prefix.index[0]),
                "execution_end": utc_time(prefix.index[-1] + step),
                "source_sha256": adaptation.converted_sha256,
                "config": {
                    "fees": str(config.fees),
                    "slippage": str(config.slippage),
                    "include_funding": config.include_funding,
                },
            }
            if outcome.status != "ok" or outcome.result is None:
                run["error"] = str(outcome.error)
                runs.append(run)
                continue
            result = outcome.result
            equity = [
                Decimal(str(value))
                for value in result.equity_curve.loc[result.equity_curve.index >= first]
            ]
            peak, drawdown = initial_cash, Decimal("0")
            for value in equity:
                peak = max(peak, value)
                drawdown = min(drawdown, value / peak - 1)
            metrics = result.metrics
            run["metrics"] = {
                "net_pnl": equity[-1] - initial_cash,
                "total_return": equity[-1] / initial_cash - 1,
                "max_drawdown": drawdown,
                "closed_trades": sum(trade.status == "closed" for trade in result.trades),
                "open_trades": sum(trade.status != "closed" for trade in result.trades),
                "total_fees": metrics.total_fees,
                "total_slippage": metrics.total_slippage,
                "total_funding": metrics.total_funding,
                "funding_data_incomplete": metrics.funding_data_incomplete,
            }
            run["trades"] = [
                {
                    **asdict(trade),
                    "entry_time": utc_time(prefix.index[trade.entry_bar_index]),
                    "exit_time": utc_time(prefix.index[trade.exit_bar_index])
                    if trade.exit_bar_index is not None
                    else None,
                }
                for trade in result.trades
            ]
            run["warnings"] = outcome.parse.warnings
            runs.append(run)
    return _json(
        {
            "status": "completed" if all(run["status"] == "ok" for run in runs) else "incomplete",
            "registered_at": utc_time(plan["registered_at"]),
            "holdout_status": "retrospective_not_untouched"
            if utc_time(plan["registered_at"]) >= holdout
            else "declared_preregistered_unverified",
            "funding_status": "not_provided"
            if funding_rates is None
            else "observed_settlements_only",
            "assumptions": {
                "init_cash": str(initial_cash),
                "position_size_pct": str(plan["position_size_pct"]),
                "sizing": "strategy.percent_of_equity",
                "cost_basis": plan["cost_basis"],
                "fill_timing": "next_bar_open",
                "position_reset_per_split": True,
                "forced_close_at_end": False,
                "net_pnl_includes_open_mark_to_market": True,
                "funding_stress_multiplied": False,
                "parameter_search_performed": False,
            },
            "runs": runs,
        }
    )
