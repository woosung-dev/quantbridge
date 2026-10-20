"""UI가 생성한 TradingView 원본 study 응답의 검증과 사건 추출.

네트워크를 호출하지 않는다. 원본·실제 compiled 소스·응답 metadata의 연결을 확인하고,
수집 시점에 닫히지 않은 봉은 raw에 보존하되 비교 사건에서 제외한다.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import combinations, pairwise
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.pine_validation.compare import compare_events
from scripts.pine_validation.models import EventInput, SignalEvent, utc_time

_STEPS = {"1h": timedelta(hours=1), "4h": timedelta(hours=4), "1d": timedelta(days=1)}
_COLUMNS = [
    "time",
    "buy_plotshape",
    "sell_plotshape",
    "barcolor_0",
    "barcolor_1",
    "long_alertcondition",
    "short_alertcondition",
]
_CAPTURE = "Playwright CDP observed UI-generated native chart study response"


@dataclass
class NativeCapture:
    observations: pd.DataFrame
    events: list[SignalEvent]
    metadata: dict[str, Any]
    raw_bytes: bytes
    ohlcv: pd.DataFrame

    def window_events(self, start: datetime | str, end: datetime | str) -> list[SignalEvent]:
        start, end = utc_time(start), utc_time(end)
        step = _STEPS[self.metadata["timeframe"]]
        if (
            start >= end
            or start.timestamp() % step.total_seconds()
            or end.timestamp() % step.total_seconds()
        ):
            raise ValueError("native 비교창은 시간 격자에 맞는 [시작, 종료)여야 합니다")
        if end > utc_time(self.metadata["observed_at"]):
            raise ValueError("native 수집 시점보다 뒤의 확정 봉을 주장할 수 없습니다")
        expected = pd.date_range(start, end, freq=step, inclusive="left")
        actual = self.observations.index[
            (self.observations.index >= start) & (self.observations.index < end)
        ]
        if not actual.equals(expected):
            raise ValueError(f"native 비교창 확정 봉 누락: {len(expected.difference(actual))}개")
        return [event for event in self.events if start <= event.bar_time < end]


def _epoch(value: Any, step: timedelta) -> datetime:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or int(value) != value
    ):
        raise ValueError("native 봉 시각은 정수 epoch 초여야 합니다")
    if value % step.total_seconds():
        raise ValueError("native 봉 시각이 타임프레임 격자와 다릅니다")
    try:
        return datetime.fromtimestamp(value, UTC)
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError("native 봉 시각이 날짜 범위를 벗어났습니다") from exc


def parse_native_capture(
    payload: Mapping[str, Any],
    *,
    source: bytes,
    compiled_source: bytes,
    expected_symbol: str | None = None,
    expected_timeframe: str | None = None,
    expected_inputs: Mapping[str, Any] | None = None,
) -> NativeCapture:
    if not isinstance(payload, Mapping):
        raise ValueError("native 응답은 metadata와 rows를 가진 객체여야 합니다")
    if payload.get("capture") != _CAPTURE:
        raise ValueError("native source provenance: UI create_study 관측 출처가 필요합니다")
    for key in ("symbol", "timeframe", "study_id", "observed_at"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ValueError(f"native source provenance: {key}가 없습니다")
    symbol, timeframe = payload["symbol"], payload["timeframe"]
    if timeframe not in _STEPS:
        raise ValueError("native 타임프레임은 1h, 4h, 1d만 지원합니다")
    if expected_symbol is not None and symbol != expected_symbol:
        raise ValueError("native 심볼이 기대한 원본 데이터와 다릅니다")
    if expected_timeframe is not None and timeframe != expected_timeframe:
        raise ValueError("native 타임프레임이 기대한 원본 데이터와 다릅니다")
    source_hash, compiled_hash = (
        hashlib.sha256(source).hexdigest(),
        hashlib.sha256(compiled_source).hexdigest(),
    )
    if (
        payload.get("source_sha256") != source_hash
        or payload.get("compiled_source_sha256") != compiled_hash
    ):
        raise ValueError("native source provenance: 원본 또는 compiled 소스 hash 불일치")
    if payload.get("compiled_source_matches_original_lf_normalized") is not True or source.replace(
        b"\r\n", b"\n"
    ) != compiled_source.replace(b"\r\n", b"\n"):
        raise ValueError("native source provenance: 실제 compiled 소스가 무수정 원본과 다릅니다")
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {"a", "c", "h"}:
        raise ValueError("native UT Bot 입력 a/c/h가 필요합니다")
    if (
        type(inputs["a"]) not in (int, float)
        or not math.isfinite(inputs["a"])
        or inputs["a"] <= 0
        or type(inputs["c"]) is not int
        or inputs["c"] < 1
        or type(inputs["h"]) is not bool
    ):
        raise ValueError("native UT Bot 입력 타입 또는 범위가 잘못됐습니다")
    if expected_inputs is not None and inputs != dict(expected_inputs):
        raise ValueError("native UT Bot 입력이 기대한 파라미터와 다릅니다")
    if payload.get("plot_columns") != _COLUMNS:
        raise ValueError("native plot/alert 컬럼 순서가 확인한 원본과 다릅니다")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("native 원시 행이 비어 있습니다")
    observed_at, step = utc_time(payload["observed_at"]), _STEPS[timeframe]
    times, values = [], []
    for row_number, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(_COLUMNS):
            raise ValueError(f"native row[{row_number}]: 필수 7개 컬럼이 아닙니다")
        at = _epoch(row[0], step)
        if at > observed_at:
            raise ValueError("native 응답에 수집 시각보다 미래인 봉이 있습니다")
        for column in (1, 2, 5, 6):
            if type(row[column]) not in (int, float) or row[column] not in (0, 1):
                raise ValueError(f"native row[{row_number}]: 신호는 숫자 0/1이어야 합니다")
        if row[1] != row[5] or row[2] != row[6]:
            raise ValueError(f"native row[{row_number}]: plotshape와 alertcondition 신호 불일치")
        if row[1] and row[2]:
            raise ValueError(f"native row[{row_number}]: 매수·매도 신호 충돌")
        for column in (3, 4):
            if row[column] is not None and (
                type(row[column]) not in (int, float) or not math.isfinite(row[column])
            ):
                raise ValueError(f"native row[{row_number}]: barcolor 원시 값이 유효하지 않습니다")
        times.append(at)
        values.append(row[1:])
    for previous, current in pairwise(times):
        if current <= previous:
            raise ValueError("native 봉 시각이 중복되거나 역순입니다")
        if current - previous != step:
            raise ValueError("native 시간 격자에 중간 봉이 누락됐습니다")
    frame = pd.DataFrame(values, columns=_COLUMNS[1:], index=pd.DatetimeIndex(times, name="time"))
    closed = frame.loc[frame.index + step <= observed_at]
    events = []
    for at, row in closed.iterrows():
        for direction, active in (("long", row["buy_plotshape"]), ("short", row["sell_plotshape"])):
            if active:
                events.append(
                    SignalEvent(
                        at.to_pydatetime(), direction, at.to_pydatetime() + step, at.to_pydatetime()
                    )
                )  # type: ignore[arg-type]
    ohlcv_rows = payload.get("ohlcv", [])
    if not isinstance(ohlcv_rows, list):
        raise ValueError("native OHLCV 관측값은 행 배열이어야 합니다")
    ohlcv_times, ohlcv_values = [], []
    for row in ohlcv_rows:
        if not isinstance(row, list) or len(row) != 6:
            raise ValueError("native OHLCV에는 time/OHLCV 6개 컬럼이 필요합니다")
        at = _epoch(row[0], step)
        if at not in frame.index:
            raise ValueError("native OHLCV 봉이 관측한 study 응답 범위를 벗어났습니다")
        numbers = row[1:]
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in numbers):
            raise ValueError("native OHLCV에 비유한 값이 있습니다")
        open_, high, low, close, volume = numbers
        if (
            min(open_, high, low, close) <= 0
            or volume < 0
            or high < max(open_, close, low)
            or low > min(open_, close, high)
        ):
            raise ValueError("native OHLCV 가격 범위 또는 거래량이 잘못됐습니다")
        ohlcv_times.append(at)
        ohlcv_values.append(numbers)
    if any(current <= previous for previous, current in pairwise(ohlcv_times)):
        raise ValueError("native OHLCV 시각이 중복되거나 역순입니다")
    ohlcv = pd.DataFrame(
        ohlcv_values,
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex(ohlcv_times, tz="UTC", name="time"),
    )
    metadata = {
        "reference_kind": "native_original",
        "native_original_source_verified": True,
        "source_provenance": {
            "capture": payload["capture"],
            "source_sha256": source_hash,
            "compiled_source_sha256": compiled_hash,
            "compiled_source_matches_original_lf_normalized": True,
            "study_id": payload["study_id"],
            "symbol": symbol,
            "timeframe": timeframe,
            "inputs": inputs,
        },
        "symbol": symbol,
        "timeframe": timeframe,
        "observed_at": observed_at.isoformat(),
        "raw_rows": len(frame),
        "closed_rows": len(closed),
        "excluded_unconfirmed_rows": len(frame) - len(closed),
        "plot_alert_match": True,
        "ohlcv_rows_in_capture": len(ohlcv),
        "scope_note": "무수정 원본 study의 UI 응답이며 엔진 동등성은 별도 사건 비교가 판정합니다.",
    }
    return NativeCapture(
        closed, events, metadata, json.dumps(dict(payload), ensure_ascii=False).encode(), ohlcv
    )


def load_native_capture(
    path: Path,
    *,
    source_path: Path,
    compiled_source_path: Path,
    expected_symbol: str | None = None,
    expected_timeframe: str | None = None,
    expected_inputs: Mapping[str, Any] | None = None,
) -> NativeCapture:
    raw = path.read_bytes()
    result = parse_native_capture(
        json.loads(raw),
        source=source_path.read_bytes(),
        compiled_source=compiled_source_path.read_bytes(),
        expected_symbol=expected_symbol,
        expected_timeframe=expected_timeframe,
        expected_inputs=expected_inputs,
    )
    result.raw_bytes = raw
    result.metadata["raw_capture_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def export_native_capture(
    capture: NativeCapture,
    output_dir: Path,
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    prefix: str = "native-tv",
) -> dict[str, Path]:
    events = capture.window_events(window_start, window_end)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {name: output_dir / f"{prefix}-{name}.json" for name in ("raw", "events", "metadata")}
    paths["raw"].write_bytes(capture.raw_bytes)
    paths["events"].write_text(json.dumps([event.to_dict() for event in events], indent=2) + "\n")
    metadata = {
        **capture.metadata,
        "window": {
            "start": utc_time(window_start).isoformat(),
            "end": utc_time(window_end).isoformat(),
            "buy_count": sum(event.direction == "long" for event in events),
            "sell_count": sum(event.direction == "short" for event in events),
        },
    }
    paths["metadata"].write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    return paths


def compare_native_events(
    capture: NativeCapture,
    references: Mapping[str, EventInput],
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    bar_times: pd.DatetimeIndex | None = None,
) -> dict[str, Any]:
    if set(references) != {"probe", "python", "pine"}:
        raise ValueError("native 교차검증에는 probe/python/pine 세 참조가 필요합니다")
    events = {"native": capture.window_events(window_start, window_end), **references}
    comparisons = {}
    for first, second in combinations(events, 2):
        comparisons[f"{first}_{second}"] = compare_events(
            events[first],
            events[second],
            window_start=window_start,
            window_end=window_end,
            bar_times=bar_times,
        ).to_dict()
    statuses = {result["status"] for result in comparisons.values()}
    status = (
        "mismatch"
        if "mismatch" in statuses
        else "no_signal"
        if "no_signal" in statuses
        else "exact_match"
    )
    return {
        "status": status,
        "native_original_verified": status == "exact_match",
        "native_reference": capture.metadata,
        "comparisons": comparisons,
    }


def compare_native_ohlcv(
    capture: NativeCapture,
    reference: pd.DataFrame,
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    reference_symbol: str,
) -> dict[str, Any]:
    """없는 native OHLCV를 probe 값으로 채워 데이터 동등성을 지어내지 않는다."""
    if reference_symbol != capture.metadata["symbol"]:
        raise ValueError("native와 참조 OHLCV 심볼이 다릅니다")
    start, end = utc_time(window_start), utc_time(window_end)
    capture.window_events(start, end)
    step = _STEPS[capture.metadata["timeframe"]]
    expected = pd.date_range(start, end, freq=step, inclusive="left")
    selected = reference.loc[(reference.index >= start) & (reference.index < end)]
    if not selected.index.equals(expected):
        raise ValueError("참조 OHLCV가 native 비교창 전체를 포함하지 않습니다")
    native = capture.ohlcv.loc[(capture.ohlcv.index >= start) & (capture.ohlcv.index < end)]
    mismatches = []
    maximum = 0.0
    for at in expected.intersection(native.index):
        for field_name in ("open", "high", "low", "close", "volume"):
            first, second = float(native.loc[at, field_name]), float(selected.loc[at, field_name])
            if not math.isfinite(second):
                raise ValueError("참조 OHLCV에 비유한 값이 있습니다")
            delta = abs(first - second)
            maximum = max(maximum, delta)
            if delta > 1e-8:
                mismatches.append(
                    {
                        "bar_time": at.isoformat(),
                        "field": field_name,
                        "native": first,
                        "reference": second,
                    }
                )
    missing = expected.difference(native.index)
    status = (
        "mismatch"
        if mismatches
        else "unverified"
        if not len(native)
        else "partial"
        if len(missing)
        else "exact_match"
    )
    return {
        "status": status,
        "expected_bars": len(expected),
        "native_bars": len(native),
        "reference_bars": len(selected),
        "missing_native_bars": len(missing),
        "max_abs_difference": maximum if len(native) else None,
        "mismatches": mismatches,
    }


def export_native_reference(
    capture: NativeCapture,
    path: Path,
    references: Mapping[str, EventInput],
    window_start: datetime | str,
    window_end: datetime | str,
    *,
    bar_times: pd.DatetimeIndex | None = None,
) -> Path:
    """세 참조와 사건·확정·표시 시각이 모두 맞는 창만 CLI 원본 참조로 내보낸다."""
    comparison = compare_native_events(
        capture, references, window_start, window_end, bar_times=bar_times
    )
    if comparison["status"] != "exact_match":
        raise ValueError(
            "native 원본 참조 승격에는 probe/python/pine 사건의 완전 일치가 필요합니다"
        )
    provenance = capture.metadata["source_provenance"]
    payload = {
        "events": [event.to_dict() for event in capture.window_events(window_start, window_end)],
        "provenance": {
            **provenance,
            "kind": "native_original",
            "native_original_verified": True,
            "raw_capture_sha256": hashlib.sha256(capture.raw_bytes).hexdigest(),
            "window": {
                "start": utc_time(window_start).isoformat(),
                "end": utc_time(window_end).isoformat(),
            },
            "event_comparison_status": comparison["status"],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path
