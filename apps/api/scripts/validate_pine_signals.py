"""수집한 원본 Pine·독립 Python·TradingView 사건을 외부 호출 없이 대조한다."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from scripts.pine_validation.compare import compare_events  # noqa: E402
from scripts.pine_validation.futures import compare_futures, simulate_futures  # noqa: E402
from scripts.pine_validation.models import SignalEvent, coerce_events, utc_time  # noqa: E402
from scripts.pine_validation.oracles import compute_oracle  # noqa: E402
from scripts.pine_validation.strategy_adapter import (  # noqa: E402
    StrategyAdapterError,
    adapt_strategy,
    compare_app_backtest,
)

RUNS_DIR = _BACKEND_DIR.parents[1] / "runs"
TIMEFRAMES = {"1h": 3600, "4h": 14400, "1d": 86400}
MINIMUM_INDICATORS = 10
_DIRECTIONS = {"long", "short", "long_exit", "short_exit"}
# 이 원본의 h=false는 security를 포함한 ternary 분기를 실행하지 않는다고 검토했다.
# 일반 seen=[]는 Pine 버전별 단축평가 차이 때문에 임의 코드의 미실행 증명이 아니다.
_REVIEWED_UTBOT_SHA256 = "d17fdc1d34a20107dbb853316886ac8c27803b159f379e66c685810d7e10410c"


class ManifestError(ValueError):
    """실행 전에 확인할 수 있는 입력 계약 위반."""


def required_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    cutoff = utc_time(now or datetime.now(UTC)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (pd.Timestamp(cutoff) - pd.DateOffset(years=1)).to_pydatetime(), cutoff


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["version"] != 1 or data["symbol"] != "BYBIT:BTCUSDT.P":
            raise ValueError("version=1, symbol=BYBIT:BTCUSDT.P가 필요합니다")
        start, end = (utc_time(data["window"][name]) for name in ("start", "end"))
        if start >= end or end > required_window()[1]:
            raise ValueError("window는 시작 < 종료 ≤ 최근 확정 UTC 일봉 cutoff여야 합니다")
        if not isinstance(data["ohlcv"], dict) or not isinstance(data["indicators"], list):
            raise ValueError("ohlcv 객체와 indicators 배열이 필요합니다")
        if any(not isinstance(filename, str) for filename in data["ohlcv"].values()):
            raise ValueError("ohlcv 파일 경로는 문자열이어야 합니다")
        ids, publications = set(), set()
        for item in data["indicators"]:
            for name in ("id", "title", "url", "author", "source_file", "source_sha256"):
                if not isinstance(item[name], str) or not item[name].strip():
                    raise ValueError(f"지표의 {name} 문자열이 필요합니다")
            url = urlsplit(item["url"])
            match = re.match(r"^/script/([A-Za-z0-9]{8})(?:[-/]|$)", url.path)
            if (
                url.scheme not in {"http", "https"}
                or not (
                    url.hostname == "tradingview.com"
                    or (url.hostname or "").endswith(".tradingview.com")
                )
                or match is None
            ):
                raise ValueError("실제 TradingView publication URL이 필요합니다")
            publication_id = match.group(1)
            if item["id"] in ids or publication_id in publications:
                raise ValueError("지표 id와 TradingView publication id는 중복될 수 없습니다")
            ids.add(item["id"])
            publications.add(publication_id)
            item["publication_id"] = publication_id
            utc_time(item["observed_at"])
            if not isinstance(item["boosts"], int) or isinstance(item["boosts"], bool):
                raise ValueError("boosts는 정수여야 합니다")
            if any(
                not isinstance(item.get(name, {}), dict)
                for name in ("inputs", "params", "tv_events")
            ):
                raise ValueError("inputs·params·tv_events는 객체여야 합니다")
            if not isinstance(item.get("signal_bindings", []), list):
                raise ValueError("signal_bindings는 배열이어야 합니다")
            for binding in item.get("signal_bindings", []):
                if (
                    binding["function"]
                    not in {"plotshape", "plotchar", "plotarrow", "alertcondition", "alert"}
                    or binding["direction"] not in _DIRECTIONS
                    or not isinstance(binding["line"], int)
                    or binding["line"] < 1
                    or binding.get("when", "truthy") not in {"truthy", "positive", "negative"}
                    or (
                        "column" in binding
                        and (not isinstance(binding["column"], int) or binding["column"] < 0)
                    )
                ):
                    raise ValueError("signal_binding의 함수·방향·줄·열·조건을 확인하세요")
        return data
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ManifestError(str(exc)) from exc


def load_ohlcv(path: Path, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if not {"time", "open", "high", "low", "close", "volume"} <= set(frame.columns):
        raise ValueError("CSV에는 time,open,high,low,close,volume이 필요합니다")
    frame.index = pd.DatetimeIndex([utc_time(value) for value in frame.pop("time")])
    step = pd.Timedelta(seconds=TIMEFRAMES[timeframe])
    if frame.empty or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("OHLCV는 중복 없이 시간순인 비어 있지 않은 자료여야 합니다")
    if any(value != value.floor(step) for value in frame.index):
        raise ValueError("OHLCV 봉 시각이 타임프레임 격자와 다릅니다")
    frame = frame.loc[frame.index + step <= end].copy()
    if frame.empty or any(gap != step for gap in frame.index.to_series().diff().dropna()):
        raise ValueError("OHLCV 봉이 비어 있거나 중간 봉이 누락됐습니다")
    expected = pd.date_range(pd.Timestamp(start).ceil(step), pd.Timestamp(end) - step, freq=step)
    actual = frame.index[frame.index >= start]
    if expected.empty or not actual.equals(expected):
        raise ValueError("OHLCV가 비교창의 모든 완결봉을 포함하지 않습니다")
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not all(math.isfinite(float(value)) for value in frame[column]):
            raise ValueError("OHLCV에 비유한 값이 있습니다")
    if (
        (frame[["open", "high", "low", "close"]] <= 0).any().any()
        or (frame["volume"] < 0).any()
        or (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any()
        or (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any()
    ):
        raise ValueError("OHLCV 가격 범위·거래량이 유효하지 않습니다")
    return frame


def execute_pine(source: str, frame: pd.DataFrame, inputs: dict[str, Any], timeframe: str) -> Any:
    from src.strategy.pine_v2.event_loop import run_historical

    return run_historical(
        source,
        frame,
        capture_history=False,
        capture_signals=True,
        input_overrides=inputs,
        timeframe=timeframe,
    )


def bind_events(
    trace: list[Any], bindings: list[dict[str, Any]], timeframe: str
) -> list[SignalEvent]:
    events = []
    step = timedelta(seconds=TIMEFRAMES[timeframe])
    for binding in bindings:
        matched = [
            observation
            for observation in trace
            if observation.function == binding["function"]
            and observation.source_line == binding["line"]
            and ("column" not in binding or observation.source_column == binding["column"])
        ]
        if "column" not in binding and len({row.source_column for row in matched}) > 1:
            raise ValueError("같은 줄의 여러 신호 호출은 column으로 구분해야 합니다")
        for row in matched:
            value = row.value
            if value is None or not math.isfinite(float(value)):
                continue
            when = binding.get("when", "truthy")
            active = (
                bool(value) if when == "truthy" else value > 0 if when == "positive" else value < 0
            )
            if active:
                at = utc_time(row.bar_open_time)
                events.append(
                    SignalEvent(
                        bar_time=at,
                        direction=binding["direction"],
                        confirmed_at=at + step,
                        display_time=at + step * row.marker_offset,
                        source_line=row.source_line,
                    )
                )
    return events


def _window_events(
    events: Any, frame: pd.DataFrame, start: datetime, end: datetime
) -> list[SignalEvent]:
    selected = [event for event in coerce_events(events) if start <= event.bar_time < end]
    if any(event.bar_time not in frame.index for event in selected):
        raise ValueError("사건 시각이 완결 OHLCV 봉에 대응하지 않습니다")
    return selected


def validate_cell(
    item: dict[str, Any], timeframe: str, manifest: dict[str, Any], base: Path
) -> dict[str, Any]:
    row: dict[str, Any] = {"indicator_id": item["id"], "timeframe": timeframe, "failures": []}
    start, end = (utc_time(manifest["window"][name]) for name in ("start", "end"))
    try:
        source_bytes = (base / item["source_file"]).read_bytes()
    except OSError as exc:
        return {**row, "status": "missing_source", "detail": str(exc)}
    if hashlib.sha256(source_bytes).hexdigest() != item["source_sha256"]:
        return {**row, "status": "source_hash_mismatch"}
    if item["boosts"] < 100:
        return {**row, "status": "insufficient_boosts"}
    from src.strategy.pine_v2.coverage import analyze_coverage

    try:
        source = source_bytes.decode("utf-8")
        coverage = analyze_coverage(source)
    except (UnicodeError, ValueError) as exc:
        return {**row, "status": "invalid_pine", "detail": str(exc)}
    blocking_degraded = [name for name in coverage.degraded_calls if name != "timeframe.period"]
    if not coverage.is_runnable:
        return {
            **row,
            "status": "unsupported_pine",
            "unsupported": list(coverage.all_unsupported),
            "degraded": blocking_degraded,
        }
    if "timeframe.period" in coverage.degraded_calls:
        row["resolved_by_context"] = ["timeframe.period"]
    if not item.get("signal_bindings"):
        return {**row, "status": "missing_signal_bindings"}
    relative_csv = manifest["ohlcv"].get(timeframe)
    if not relative_csv or not (base / relative_csv).is_file():
        return {**row, "status": "missing_ohlcv"}
    try:
        frame = load_ohlcv(base / relative_csv, timeframe, start, end)
        row["ohlcv_sha256"] = hashlib.sha256((base / relative_csv).read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError) as exc:
        return {**row, "status": "invalid_ohlcv", "detail": str(exc)}
    row["bars"] = len(frame)
    try:
        result = execute_pine(source, frame, item.get("inputs", {}), timeframe)
        if result.errors or result.bars_processed != len(frame):
            raise ValueError("Pine이 전체 봉을 오류 없이 실행하지 못했습니다")
        if blocking_degraded:
            seen = getattr(result, "degraded_calls_seen", None)
            if seen is None:
                return {**row, "status": "missing_degraded_execution_evidence"}
            row["degraded_calls_seen"] = list(seen)
            if seen:
                return {**row, "status": "degraded_pine_executed", "degraded": list(seen)}
            if not (
                item["source_sha256"] == _REVIEWED_UTBOT_SHA256
                and item.get("inputs", {}).get("h", False) is False
                and set(blocking_degraded) <= {"heikinashi", "security"}
            ):
                return {**row, "status": "unreviewed_degraded_branch"}
            row["unexecuted_degraded_calls"] = blocking_degraded
        pine_full = bind_events(result.signal_trace, item["signal_bindings"], timeframe)
        pine = _window_events(pine_full, frame, start, end)
    except Exception as exc:
        return {**row, "status": "pine_execution_failed", "detail": str(exc)}
    row["pine_events"] = [event.to_dict() for event in pine]
    oracle_name = item.get("oracle")
    python = None
    python_full = None
    if not oracle_name:
        row["failures"].append("missing_python_adapter")
    else:
        try:
            python_full = compute_oracle(oracle_name, frame, item.get("params", {}))
            python = _window_events(python_full, frame, start, end)
            row["python_events"] = [event.to_dict() for event in python]
        except Exception as exc:
            row["failures"].append("python_adapter_failed")
            row["python_error"] = str(exc)
    tv = None
    reference = item.get("tv_events", {}).get(timeframe)
    if not reference or not (base / reference).is_file():
        row["failures"].append("missing_tv_reference")
    else:
        try:
            reference_bytes = (base / reference).read_bytes()
            payload = json.loads(reference_bytes)
            tv = _window_events(payload, frame, start, end)
            row["tv_reference_sha256"] = hashlib.sha256(reference_bytes).hexdigest()
            row["tv_events"] = [event.to_dict() for event in tv]
            provenance = payload.get("provenance") if isinstance(payload, dict) else None
            row["tv_provenance"] = provenance
            reference_window = provenance.get("window") if isinstance(provenance, dict) else None
            try:
                same_window = (
                    isinstance(reference_window, dict)
                    and utc_time(reference_window.get("start")) == start
                    and utc_time(reference_window.get("end")) == end
                )
            except (ValueError, TypeError):
                same_window = False
            trusted = (
                isinstance(provenance, dict)
                and provenance.get("source_sha256") == item["source_sha256"]
                and provenance.get("symbol") == manifest["symbol"]
                and provenance.get("timeframe") == timeframe
                and json.dumps(provenance.get("inputs"), sort_keys=True)
                == json.dumps(item.get("inputs", {}), sort_keys=True)
                and same_window
                and (
                    provenance.get("kind") == "native_original"
                    or (
                        provenance.get("kind") == "reviewed_port"
                        and provenance.get("native_original_verified") is True
                    )
                )
            )
            if not trusted:
                row["failures"].append("unverified_tv_reference")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            row["failures"].append("invalid_tv_reference")
            row["tv_error"] = str(exc)
    for label, left, right in (
        ("pine_python", pine, python),
        ("tv_pine", tv, pine),
        ("tv_python", tv, python),
    ):
        if left is not None and right is not None:
            comparison = compare_events(
                left, right, window_start=start, window_end=end, bar_times=frame.index
            )
            row[label] = comparison.to_dict()
            if comparison.status != "exact_match":
                row["failures"].append(comparison.status)
    if python is not None:
        try:
            evaluation = frame.loc[frame.index >= start]
            futures = compare_futures(
                simulate_futures(evaluation, pine), simulate_futures(evaluation, python)
            )
            row["futures"] = futures
            if futures["status"] != "exact_match":
                row["failures"].append(f"futures_{futures['status']}")
        except ValueError as exc:
            row["failures"].append("futures_failed")
            row["futures_error"] = str(exc)
    if python_full is not None:
        try:
            adaptation = adapt_strategy(source, item["signal_bindings"])
            row["strategy_adaptation"] = adaptation.to_dict()
            row["app_backtest"] = compare_app_backtest(
                adaptation.strategy_source,
                frame,
                item.get("inputs", {}),
                timeframe,
                python_full,
                window_start=start,
                window_end=end,
            )
            if row["app_backtest"]["status"] != "exact_match":
                row["failures"].append(f"app_{row['app_backtest']['status']}")
        except StrategyAdapterError as exc:
            row["failures"].append("strategy_adapter_failed")
            row["app_backtest"] = {"status": exc.code, "detail": str(exc)}
        except (ValueError, TypeError) as exc:
            row["failures"].append("app_backtest_failed")
            row["app_backtest"] = {"status": "app_backtest_failed", "detail": str(exc)}
    if not {"long", "short"} <= {event.direction for event in pine}:
        row["failures"].append("one_sided_signal" if pine else "no_signal")
    row["failures"] = list(dict.fromkeys(row["failures"]))
    row["status"] = row["failures"][0] if row["failures"] else "exact_match"
    return row


def run_validation(manifest_path: Path, *, limit: int = 10) -> dict[str, Any]:
    if not 1 <= limit <= 100:
        raise ManifestError("limit은 1~100이어야 합니다")
    manifest = load_manifest(manifest_path)
    selected = manifest["indicators"][:limit]
    rows = [
        validate_cell(item, tf, manifest, manifest_path.parent)
        for item in selected
        for tf in TIMEFRAMES
    ]
    source_groups: dict[str, list[str]] = {}
    for item in selected:
        source_groups.setdefault(item["source_sha256"], []).append(item["id"])
    duplicate_sources = [
        {"source_sha256": digest, "indicator_ids": ids}
        for digest, ids in source_groups.items()
        if len(ids) > 1
    ]
    duplicate_ids = {identifier: ids[0] for ids in source_groups.values() for identifier in ids[1:]}
    for row in rows:
        if row["indicator_id"] in duplicate_ids:
            row["duplicate_source_of"] = duplicate_ids[row["indicator_id"]]
            row["failures"].append("duplicate_source")
            if row["status"] == "exact_match":
                row["status"] = "duplicate_source"
    exact = sum(row["status"] == "exact_match" for row in rows)
    expected = max(MINIMUM_INDICATORS, len(selected)) * len(TIMEFRAMES)
    required_start, required_end = required_window()
    start, end = (utc_time(manifest["window"][name]) for name in ("start", "end"))
    failures = []
    if (start, end) != (required_start, required_end):
        failures.append("window_not_recent_calendar_year")
    if len(selected) < MINIMUM_INDICATORS:
        failures.append("insufficient_indicators")
    if len(source_groups) < MINIMUM_INDICATORS:
        failures.append("insufficient_unique_sources")
    if duplicate_sources:
        failures.append("duplicate_sources")
    if exact != expected:
        failures.append("inexact_pairs")
    return {
        "status": "passed" if not failures else "incomplete",
        "symbol": manifest["symbol"],
        "window": manifest["window"],
        "cutoff": manifest["window"]["end"],
        "required_window": {"start": required_start.isoformat(), "end": required_end.isoformat()},
        "completion_failures": failures,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "selected_indicators": len(selected),
        "minimum_indicators": MINIMUM_INDICATORS,
        "unique_sources": len(source_groups),
        "duplicate_sources": duplicate_sources,
        "expected_pairs": expected,
        "evaluated_pairs": len(rows),
        "exact_pairs": exact,
        "pine_python_exact_pairs": sum(
            row.get("pine_python", {}).get("status") == "exact_match" for row in rows
        ),
        "futures_exact_pairs": sum(
            row.get("futures", {}).get("status") == "exact_match" for row in rows
        ),
        "app_backtest_exact_pairs": sum(
            row.get("app_backtest", {}).get("status") == "exact_match" for row in rows
        ),
        "indicators": selected,
        "results": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if not output.is_relative_to(RUNS_DIR.resolve()):
        parser.error("output은 레포지토리 runs/ 하위여야 합니다")
    try:
        report = run_validation(args.manifest.resolve(), limit=args.limit)
        code = 0 if report["status"] == "passed" else 1
    except ManifestError as exc:
        report, code = {"status": "invalid_manifest", "detail": str(exc)}, 2
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# Pine 신호 대조", "", f"판정: {report['status']}"]
    if "results" in report:
        lines += [
            f"전체 {report['expected_pairs']}개 중 일치 {report['exact_pairs']}개",
            f"Pine↔Python {report['pine_python_exact_pairs']}개 · "
            f"선물 원장 {report['futures_exact_pairs']}개 · "
            f"앱 백테스트 {report['app_backtest_exact_pairs']}개 일치",
            f"완료 조건 미충족: {', '.join(report['completion_failures']) or '없음'}",
            "",
            "| 지표 | TF | Pine↔Python | 선물 원장 | 앱 백테스트 | 전체 판정 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {row['indicator_id']} | {row['timeframe']} | "
            f"{row.get('pine_python', {}).get('status', '—')} | "
            f"{row.get('futures', {}).get('status', '—')} | "
            f"{row.get('app_backtest', {}).get('status', '—')} | {row['status']} |"
            for row in report["results"]
        ]
    else:
        lines += [report["detail"]]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{report['status']}: {output / 'report.json'}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
