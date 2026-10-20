"""브라우저 Pine Logs의 QB1 관측값 파서. 원본 지표의 native 검증과 구분한다.

QB1 probe가 TradingView에서 계산했다는 증거일 뿐, 원본 지표와 probe의 동등성을
증명하지 않는다. 바깥 로그의 표시 시각 대신 payload의 epoch 밀리초를 봉 시각으로 쓴다.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.pine_validation.compare import compare_events
from scripts.pine_validation.models import SignalEvent, utc_time
from scripts.pine_validation.oracles import atr, compute_oracle, utbot

_STEPS = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}
_OHLCV = ("open", "high", "low", "close", "volume")


@dataclass
class TVLogDataset:
    ohlcv: pd.DataFrame
    diagnostics: pd.DataFrame
    events: list[SignalEvent]
    metadata: dict[str, Any]

    def window(self, start: datetime | str, end: datetime | str) -> pd.DataFrame:
        start, end = utc_time(start), utc_time(end)
        step = _STEPS[self.metadata["timeframe"]]
        if (
            start >= end
            or start.timestamp() % step.total_seconds()
            or end.timestamp() % step.total_seconds()
        ):
            raise ValueError("비교창은 시간 격자에 맞는 [시작, 종료)여야 합니다")
        expected = pd.date_range(start, end, freq=step, inclusive="left")
        selected = self.ohlcv.loc[(self.ohlcv.index >= start) & (self.ohlcv.index < end)]
        if not selected.index.equals(expected):
            missing = expected.difference(selected.index)
            raise ValueError(f"요청 비교창에 봉이 누락됐습니다: {len(missing)}개")
        return selected


def _number(raw: str, *, field: str, location: str, allow_nan: bool = False) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{location}: {field} 숫자가 잘못됐습니다") from exc
    if allow_nan and raw == "NaN":
        return value
    if not math.isfinite(value):
        raise ValueError(f"{location}: {field}에 비유한 값이 있습니다")
    return value


def parse_tv_logs(logs: list[str] | str, timeframe: str) -> TVLogDataset:
    """중복은 같은 값이어도 실패한다. 재수집·충돌을 자동으로 숨기지 않는다."""
    if timeframe not in _STEPS:
        raise ValueError("TV 로그 타임프레임은 1h, 4h, 1d 중 하나여야 합니다")
    if isinstance(logs, str):
        logs = json.loads(logs)
    if not isinstance(logs, list) or not logs or not all(isinstance(log, str) for log in logs):
        raise ValueError("브라우저 로그는 비어 있지 않은 문자열 배열이어야 합니다")
    step = _STEPS[timeframe]
    records: dict[int, tuple[Any, ...]] = {}
    for log_index, log in enumerate(logs):
        location = f"log[{log_index}]"
        if log.count("QB1|") != 1:
            raise ValueError(f"{location}: QB1 표시가 없거나 여러 개입니다")
        payload = log.split("QB1|", 1)[1]
        if not payload.endswith(";"):
            raise ValueError(f"{location}: 끝 구분자가 없어 잘린 로그입니다")
        for row_index, row in enumerate(payload[:-1].split(";")):
            location = f"log[{log_index}] row[{row_index}]"
            fields = row.split(",")
            if len(fields) != 10:
                raise ValueError(f"{location}: 필드가 {len(fields)}개입니다(필수 10개)")
            if not fields[0].isdigit():
                raise ValueError(f"{location}: 봉 시각은 정수 epoch 밀리초여야 합니다")
            epoch = int(fields[0])
            if epoch % int(step.total_seconds() * 1000):
                raise ValueError(f"{location}: 봉 시각이 {timeframe} 시간 격자와 다릅니다")
            prices = tuple(
                _number(value, field=name, location=location)
                for name, value in zip(_OHLCV, fields[1:6], strict=True)
            )
            open_, high, low, close, volume = prices
            if (
                min(open_, high, low, close) <= 0
                or volume < 0
                or low > min(open_, close, high)
                or high < max(open_, close, low)
            ):
                raise ValueError(f"{location}: OHLC 가격 범위 또는 거래량이 잘못됐습니다")
            if fields[6] not in {"true", "false"} or fields[7] not in {"true", "false"}:
                raise ValueError(f"{location}: buy/sell은 true 또는 false여야 합니다")
            buy, sell = fields[6] == "true", fields[7] == "true"
            if buy and sell:
                raise ValueError(f"{location}: 같은 봉의 매수·매도 신호가 충돌합니다")
            diagnostic = tuple(
                _number(value, field=name, location=location, allow_nan=True)
                for name, value in zip(("stop", "atr"), fields[8:], strict=True)
            )
            signature = (
                *prices,
                buy,
                sell,
                *(None if math.isnan(value) else value for value in diagnostic),
            )
            if epoch in records:
                kind = "중복" if records[epoch] == signature else "충돌"
                raise ValueError(f"{location}: {epoch} 봉 로그 {kind}")
            records[epoch] = signature
    ordered = sorted(records)
    step_ms = int(step.total_seconds() * 1000)
    for previous, current in pairwise(ordered):
        if current - previous != step_ms:
            raise ValueError(f"시간 격자에 봉이 누락됐습니다: {previous} → {current}")
    index = pd.DatetimeIndex(
        [datetime.fromtimestamp(epoch / 1000, UTC) for epoch in ordered], name="time"
    )
    rows = [records[epoch] for epoch in ordered]
    ohlcv = pd.DataFrame([row[:5] for row in rows], columns=list(_OHLCV), index=index)
    diagnostics = pd.DataFrame(
        [row[5:] for row in rows], columns=["buy", "sell", "stop", "atr"], index=index
    )
    warmup = {}
    for name in ("stop", "atr"):
        values = pd.to_numeric(diagnostics[name]).to_numpy(dtype=float)
        valid = np.flatnonzero(~np.isnan(values))
        if len(valid) and np.isnan(values[valid[0] :]).any():
            raise ValueError(f"{name}: 초기 warmup 뒤에 NaN 진단값이 있습니다")
        warmup[name] = int(np.isnan(values).sum())
    events = []
    for at, row in diagnostics.iterrows():
        for direction, active in (("long", row["buy"]), ("short", row["sell"])):
            if active:
                events.append(
                    SignalEvent(
                        at.to_pydatetime(), direction, at.to_pydatetime() + step, at.to_pydatetime()
                    )
                )  # type: ignore[arg-type]
    metadata = {
        "provenance": "tradingview_browser_ui_pine_logs",
        "reference_kind": "derived_probe",
        "native_original_verified": False,
        "scope_note": "파생 QB1 probe의 TradingView 실행 로그이며 원본 지표 native 검증을 뜻하지 않습니다.",
        "timeframe": timeframe,
        "log_count": len(logs),
        "bars": len(index),
        "first_bar": index[0].isoformat(),
        "last_bar": index[-1].isoformat(),
        "duplicate_bars": 0,
        "missing_bars": 0,
        "warmup_nan": warmup,
        "raw_logs_sha256": hashlib.sha256(
            json.dumps(logs, ensure_ascii=False).encode()
        ).hexdigest(),
    }
    return TVLogDataset(ohlcv, diagnostics, events, metadata)


def load_tv_logs(
    path: Path,
    timeframe: str,
    *,
    probe_path: Path | None = None,
    original_source_path: Path | None = None,
) -> TVLogDataset:
    raw = path.read_bytes()
    dataset = parse_tv_logs(raw.decode(), timeframe)
    dataset.metadata["raw_logs_sha256"] = hashlib.sha256(raw).hexdigest()
    for label, source in (("probe", probe_path), ("original_source", original_source_path)):
        if source is not None:
            dataset.metadata[f"{label}_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    return dataset


def export_tv_logs(
    dataset: TVLogDataset,
    output_dir: Path,
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    prefix: str = "tv-probe",
) -> dict[str, Path]:
    """CSV에는 warmup도 보존한다. 사건 JSON과 분모는 요청 비교창으로 자른다."""
    start, end = utc_time(window_start), utc_time(window_end)
    window = dataset.window(start, end)
    events = [event for event in dataset.events if start <= event.bar_time < end]
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        name: output_dir / f"{prefix}-{suffix}"
        for name, suffix in (
            ("ohlcv", "ohlcv.csv"),
            ("events", "events.json"),
            ("diagnostics", "diagnostics.csv"),
            ("metadata", "metadata.json"),
        )
    }
    history = dataset.ohlcv.loc[dataset.ohlcv.index < end]
    history.to_csv(paths["ohlcv"], index_label="time")
    dataset.diagnostics.loc[history.index].to_csv(
        paths["diagnostics"], index_label="time", na_rep="NaN"
    )
    paths["events"].write_text(json.dumps([event.to_dict() for event in events], indent=2) + "\n")
    metadata = {
        **dataset.metadata,
        "window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "bars": len(window),
            "buy_count": sum(event.direction == "long" for event in events),
            "sell_count": sum(event.direction == "short" for event in events),
        },
        "warmup_bars_before_window": int((history.index < start).sum()),
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    return paths


def compare_utbot_logs(
    dataset: TVLogDataset,
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    key_value: float = 1,
    atr_period: int = 10,
) -> dict[str, Any]:
    """파생 probe 대 독립 Python을 대조한다. 원본 native 지표 합격을 반환하지 않는다."""
    start, end = utc_time(window_start), utc_time(window_end)
    window = dataset.window(start, end)
    python = compute_oracle(
        "utbot", dataset.ohlcv, {"key_value": key_value, "atr_period": atr_period}
    )
    comparison = compare_events(
        dataset.events, python, window_start=start, window_end=end, bar_times=dataset.ohlcv.index
    )
    stop, _, _ = utbot(dataset.ohlcv, key_value=key_value, atr_period=atr_period)
    diagnostics = {}
    for name, computed in (("stop", stop), ("atr", atr(dataset.ohlcv, atr_period))):
        observed = dataset.diagnostics[name].to_numpy(dtype=float)
        mask = (dataset.ohlcv.index >= start) & (dataset.ohlcv.index < end)
        finite = np.isfinite(observed[mask]) & np.isfinite(computed[mask])
        differences = np.abs(observed[mask][finite] - computed[mask][finite])
        diagnostics[name] = {
            "compared": int(finite.sum()),
            "nan_mask_mismatches": int(
                (np.isnan(observed[mask]) != np.isnan(computed[mask])).sum()
            ),
            "mismatches_at_1e_7": int((differences > 1e-7).sum()),
            "max_abs_difference": float(differences.max()) if len(differences) else None,
        }
    return {
        "reference_kind": "derived_probe",
        "native_original_verified": False,
        "bars": len(window),
        "signal_comparison": comparison.to_dict(),
        "diagnostics": diagnostics,
    }
