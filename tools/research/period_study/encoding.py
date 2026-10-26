"""원시 곡선 대신 검증된 사건 원장·동결 시세·완전 복원 해시를 보관한다."""

from __future__ import annotations

import copy
import sys
from collections import defaultdict
from decimal import Context, Decimal, getcontext, localcontext
from pathlib import Path

import numpy as np
import pandas as pd
from tools.research.data import load_candles
from tools.research.period_study.state import checked, identity, sha

ROOT = Path(__file__).resolve().parents[3]
CURVES = ("equity_curve", "drawdown_curve", "buy_and_hold_curve")


def decimal_context() -> dict:
    context = getcontext()
    return {key: getattr(context, key) for key in ("prec", "rounding", "Emin", "Emax", "capitals", "clamp")}


def restore(payload: dict, data_root: Path) -> dict:
    """저장된 순서와 Decimal 문맥으로 모든 분봉 equity와 파생 곡선을 복원한다."""
    recipe = payload.get("curve_encoding")
    if recipe is None:
        return payload
    if recipe.get("kind") != "event_ledger_recipe_v1":
        raise ValueError("알 수 없는 곡선 저장 형식입니다")
    if recipe["pandas_version"] != pd.__version__ or recipe["numpy_version"] != np.__version__:
        raise ValueError("곡선 복원의 pandas/numpy 버전이 동결 환경과 다릅니다")
    helper = ROOT / "apps/api/src/backtest/engine/v2_adapter.py"
    if sha(helper.read_bytes()) != recipe["metric_helper_sha256"]:
        raise ValueError("곡선 복원의 지표 계산 코드가 동결 구현과 다릅니다")
    record = recipe["execution_data"]
    data = load_candles(checked(data_root, record["path"], record["sha256"]))
    events = defaultdict(list)
    for event in payload["trace"]:
        if event.get("type") in {"fill", "funding"}:
            events[pd.Timestamp(event["timestamp"]).value].append(event)
    if not set(events) <= set(data.index.asi8):
        raise ValueError("원장 사건이 동결 1분 시계 밖에 있습니다")
    with localcontext(Context(**recipe["decimal_context"])):
        cash = Decimal(recipe["initial_capital"])
        remaining, entry_price, sign, generation = Decimal(0), Decimal(0), Decimal(0), None
        curve = []
        for when, close in zip(data.index, data["close"], strict=True):
            for event in events.get(when.value, []):
                if event["type"] == "funding":
                    cash -= Decimal(event["amount"])
                elif event["kind"] == "entry":
                    if remaining != 0:
                        raise ValueError("새 진입 전에 이전 포지션 잔량이 남았습니다")
                    cash -= Decimal(event["fee"]) + Decimal(event["slippage"])
                    remaining, entry_price = Decimal(event["quantity"]), Decimal(event["price"])
                    sign = Decimal(1) if event["direction"] == "long" else Decimal(-1)
                    generation = event["generation"]
                else:
                    if event["generation"] != generation:
                        raise ValueError("청산 원장의 포지션 세대가 다릅니다")
                    cash += Decimal(event["gross_pnl"]) - Decimal(event["fee"]) - Decimal(event["slippage"])
                    remaining -= Decimal(event["quantity"])
                    if remaining < 0:
                        raise ValueError("청산 원장 수량이 잔량을 초과합니다")
            value = cash if remaining == 0 else cash + (Decimal(str(close)) - entry_price) * remaining * sign
            curve.append({"timestamp": when.isoformat(), "value": str(value)})
        if len(curve) != recipe["row_count"] or identity(curve) != recipe["canonical_hashes"]["equity_curve"]:
            raise ValueError("복원 equity 곡선이 원시 전량 해시와 다릅니다")
        sys.path.insert(0, str(ROOT / "apps/api"))
        from src.backtest.engine.v2_adapter import (
            _as_float_series,
            _v2_buy_and_hold_curve,
            _v2_drawdown_extract,
        )
        from src.strategy.python_runtime.serialization import json_value

        equity = pd.Series([Decimal(row["value"]) for row in curve], index=data.index, dtype=object)
        drawdown, _ = _v2_drawdown_extract(_as_float_series(equity), data)
        hold = _v2_buy_and_hold_curve(data, Decimal(recipe["initial_capital"]))
        restored_curves = {"equity_curve": curve, "drawdown_curve": json_value(drawdown),
                           "buy_and_hold_curve": json_value(hold)}
        for key in CURVES:
            if identity(restored_curves[key]) != recipe["canonical_hashes"][key]:
                raise ValueError(f"복원 {key} 곡선이 원시 전량 해시와 다릅니다")
    result = copy.deepcopy(payload)
    result["equity_curve"] = curve
    result["metrics"]["drawdown_curve"] = restored_curves["drawdown_curve"]
    result["metrics"]["buy_and_hold_curve"] = restored_curves["buy_and_hold_curve"]
    return result


def compact(payload: dict, data_root: Path) -> dict:
    """복원 전량·해시 일치가 입증된 경우에만 중복 곡선을 recipe로 치환한다."""
    original = {"equity_curve": payload["equity_curve"],
                "drawdown_curve": payload["metrics"]["drawdown_curve"],
                "buy_and_hold_curve": payload["metrics"]["buy_and_hold_curve"]}
    result = copy.deepcopy(payload)
    result["curve_encoding"] = {
        "kind": "event_ledger_recipe_v1",
        "execution_data": payload["request"]["data_files"]["1min"],
        "initial_capital": str(payload["config_used"]["init_cash"]),
        "decimal_context": decimal_context(),
        "pandas_version": pd.__version__, "numpy_version": np.__version__,
        "metric_helper_sha256": sha((ROOT / "apps/api/src/backtest/engine/v2_adapter.py").read_bytes()),
        "row_count": len(original["equity_curve"]),
        "canonical_hashes": {key: identity(value) for key, value in original.items()},
        "event_order": "original_trace_funding_then_fill_order_per_execution_minute",
        "raw_minute_curves_stored": False,
        "restoration_verified": True,
    }
    result.pop("equity_curve")
    result["metrics"].pop("drawdown_curve")
    result["metrics"].pop("buy_and_hold_curve")
    restored = restore(result, data_root)
    if restored["equity_curve"] != original["equity_curve"]:
        raise ValueError("분봉 equity 전량 값이 원시 결과와 다릅니다")
    for key in ("drawdown_curve", "buy_and_hold_curve"):
        if restored["metrics"][key] != original[key]:
            raise ValueError(f"{key} 전량 값이 원시 결과와 다릅니다")
    return result
