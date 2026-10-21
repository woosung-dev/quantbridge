"""원격 실행에 쓰는 Decimal 보존 직렬화·재현 정보."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import TypeAdapter

from src.backtest.engine.types import BacktestConfig, BacktestMetrics, BacktestResult, RawTrade
from src.strategy.python_runtime.protocol import PROTOCOL_VERSION, PythonRuntimeError


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def bars_payload(ohlcv: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {
            "timestamp": pd.Timestamp(str(ts)).isoformat(),
            **{name: str(row[name]) for name in ("open", "high", "low", "close", "volume")},
        }
        for ts, row in ohlcv.iterrows()
    ]


def funding_payload(funding: pd.Series | None) -> list[dict[str, str]] | None:
    return (
        [
            {"timestamp": pd.Timestamp(str(ts)).isoformat(), "rate": str(rate)}
            for ts, rate in funding.items()
        ]
        if funding is not None
        else None
    )


def frame_from_payload(bars: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(bars)
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop("timestamp"), utc=True))
    for name in ("open", "high", "low", "close", "volume"):
        frame[name] = frame[name].map(lambda value: Decimal(str(value)))
    return frame


def funding_from_payload(values: list[dict[str, Any]] | None) -> pd.Series | None:
    if values is None:
        return None
    return pd.Series(
        [Decimal(str(value["rate"])) for value in values],
        index=pd.DatetimeIndex(pd.to_datetime([value["timestamp"] for value in values], utc=True)),
        dtype=object,
    )


def config_from_payload(value: dict[str, Any]) -> BacktestConfig:
    return TypeAdapter(BacktestConfig).validate_python(value)


def result_payload(result: BacktestResult) -> dict[str, Any]:
    return {
        "metrics": json_value(result.metrics),
        "trades": json_value(result.trades),
        "equity_curve": [
            {"timestamp": pd.Timestamp(str(ts)).isoformat(), "value": str(value)}
            for ts, value in result.equity_curve.items()
        ],
        "config_used": json_value(result.config_used),
    }


def result_from_payload(value: dict[str, Any]) -> BacktestResult:
    try:
        curve = value["equity_curve"]
        return BacktestResult(
            metrics=TypeAdapter(BacktestMetrics).validate_python(value["metrics"]),
            trades=TypeAdapter(list[RawTrade]).validate_python(value["trades"]),
            equity_curve=pd.Series(
                [Decimal(item["value"]) for item in curve],
                index=pd.DatetimeIndex(
                    pd.to_datetime([item["timestamp"] for item in curve], utc=True)
                ),
                dtype=object,
            ),
            config_used=config_from_payload(value["config_used"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PythonRuntimeError("원격 Python 실행기 결과 형식이 올바르지 않습니다") from exc


def engine_digest() -> str:
    """체결·지표 계산 구현을 포함한다. 사용자 소스는 읽거나 실행하지 않는다."""
    source_root = Path(__file__).resolve().parents[2]
    files = sorted((source_root / "backtest" / "engine").glob("*.py"))
    files += [
        source_root / "strategy" / "pine_v2" / name
        for name in ("strategy_state.py", "exit_orders.py", "leverage_model.py")
    ]
    files += [source_root / "strategy" / "trading_sessions.py"]
    return digest(
        {
            str(path.relative_to(source_root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }
    )


def provenance(
    source: str,
    bars: list[dict[str, Any]],
    funding: list[dict[str, Any]] | None,
    params: dict[str, Any],
    config: BacktestConfig,
    warmup_bars: int,
    image_id: str,
) -> dict[str, Any]:
    engine_hash = engine_digest()
    return {
        "source_hash": hashlib.sha256(source.encode()).hexdigest(),
        "data_hash": digest({"bars": bars, "funding": funding}),
        "parameters_hash": digest(params),
        "environment_digest": digest(
            {"image_id": image_id, "engine_hash": engine_hash, "protocol": PROTOCOL_VERSION}
        ),
        "runner_image_id": image_id,
        "engine_hash": engine_hash,
        "protocol": PROTOCOL_VERSION,
        "config": json_value(config),
        "warmup_bars": warmup_bars,
        "actual_start": bars[warmup_bars]["timestamp"],
        "actual_end": bars[-1]["timestamp"],
    }
