"""동결 가설의 기존 청산과 2봉 swing 청산을 분리해 비교한다. DB·주문 미사용."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from tools.research.catalogue import candidates, pilot_candidates, source_for  # noqa: E402
from tools.research.cli import (  # noqa: E402
    RESEARCH_POLICY,
    acceptance,
    append_journal,
    cells,
    exclusive,
    hash_json,
    load_dataset,
    output_dir,
    read_journal,
)
from tools.research.data import (  # noqa: E402
    ASSETS,
    TIMEFRAMES,
    digest,
    json_write,
    load_candles,
    load_funding,
    public_api,
    validate_candles,
    validate_funding,
)
from tools.research.swing_signals import entry_source  # noqa: E402

SWING_POLICY = {
    "version": 1,
    "anchor": "same_parent_timeframe_last_two_completed_candles",
    "stop_buffer_distance_ratio": "0.10",
    "risk_distance": "fixed_from_actual_entry_and_initial_stop",
    "partial_profit_r": "1.5",
    "partial_initial_quantity_ratio": "0.5",
    "trailing_activation_r": "2",
    "trailing_distance_r": "2",
    "trailing_activation_stop": "entry_price_before_costs",
    "original_exit_actions": "ignored",
    "execution_resolution": "1min",
    "same_minute_path": "worse_close_equity_of_OHLC_and_OLHC_paths_no_tick_path_claim",
    "trade_count_basis": "fully_closed_position_episode_not_exit_fills",
    "new_order_generation": "cancel_previous_exits_before_replace",
    "same_direction_signal": "preserve_existing_plan",
    "comparison_baseline": "original_source_exit_signals_on_same_1m_net_equity_ledger",
    "evaluation": RESEARCH_POLICY,
    "period_status": "retrospective_development_comparison",
    "promotable": False,
}

RECORD_FIELDS = {
    "job_hash",
    "status",
    "started_at",
    "finished_at",
    "metrics",
    "acceptance",
    "closed_position_episodes",
    "comparison",
    "result_path",
    "result_sha256",
    "error",
}


def validate_execution(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """하위봉 누락을 상위봉으로 메우지 않고 요청 기간 전체를 검사한다."""
    expected = pd.date_range(start, end, freq="1min", inclusive="left")
    if not frame.index.equals(expected):
        raise ValueError(
            f"1분봉 누락·중복·순서·기간 불일치: 요청 {len(expected)} / 실제 {len(frame)}"
        )
    numeric = frame.astype(float)
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("유효하지 않은 1분봉 숫자")
    if (
        (numeric[["open", "high", "low", "close"]] <= 0).any().any()
        or (numeric["volume"] < 0).any()
        or (numeric["high"] < numeric[["open", "close", "low"]].max(axis=1)).any()
        or (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1)).any()
    ):
        raise ValueError("1분봉 OHLCV 불변식 위반")


def development_window(parent: dict) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = pd.Timestamp(parent["holdout_start"])
    return end - pd.DateOffset(months=6), end


def fetch_execution(
    root: Path, symbol: str, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
    """공개 API 페이지를 보존해 중단 이후에도 동일 요청부터 재개한다."""
    pages = root / "pages" / symbol
    pages.mkdir(parents=True, exist_ok=True)
    start_ms, cursor = int(start.timestamp() * 1000), int(end.timestamp() * 1000) - 1
    rows: dict[int, list] = {}
    page_count = 0
    while cursor >= start_ms:
        request = {
            "category": "linear",
            "symbol": symbol,
            "interval": "1",
            "start": start_ms,
            "end": cursor,
            "limit": 1000,
        }
        page_path = pages / (hash_json(request) + ".json")
        if page_path.exists():
            saved = json.loads(page_path.read_text())
            if saved["request"] != request or saved["rows_sha256"] != hash_json(saved["rows"]):
                raise ValueError("재개할 1분봉 페이지의 요청 또는 hash가 다릅니다")
            page = saved["rows"]
        else:
            payload = public_api("kline", **request)
            if payload.get("symbol") != symbol:
                raise ValueError("Bybit가 다른 symbol을 반환했습니다")
            page = payload["list"]
            json_write(
                page_path, {"request": request, "rows": page, "rows_sha256": hash_json(page)}
            )
        if not page:
            raise ValueError("요청한 개발 기간의 1분봉이 없습니다")
        for row in page:
            timestamp = int(row[0])
            if not start_ms <= timestamp <= cursor or timestamp in rows:
                raise ValueError("1분봉 페이지의 기간 외 데이터 또는 중복 봉")
            rows[timestamp] = row
        next_cursor = min(int(row[0]) for row in page) - 1
        if next_cursor >= cursor:
            raise ValueError("1분봉 pagination이 진전되지 않습니다")
        cursor = next_cursor
        page_count += 1
        if page_count % 25 == 0:
            print(f"freeze {symbol}: {len(rows)} 1m candles", file=sys.stderr, flush=True)
    raw = [rows[key] for key in sorted(rows)]
    frame = pd.DataFrame(
        [row[1:6] for row in raw], columns=["open", "high", "low", "close", "volume"]
    )
    frame.index = pd.DatetimeIndex(
        pd.to_datetime([int(row[0]) for row in raw], unit="ms", utc=True)
    )
    validate_execution(frame, start, end)
    return frame


def freeze_execution(root: Path, baseline: Path) -> dict:
    parent = load_dataset(baseline)
    start, end = development_window(parent)
    destination = root / "execution-dataset.json"
    if destination.exists():
        return load_execution_dataset(root, baseline)
    files = []
    for symbol in ASSETS:
        path = root / f"{symbol}-1m.csv"
        if path.exists():
            frame = load_candles(path)
            validate_execution(frame, start, end)
        else:
            frame = fetch_execution(root, symbol, start, end)
            frame.to_csv(path, index_label="timestamp")
        files.append(
            {"symbol": symbol, "path": path.name, "sha256": digest(path), "bars": len(frame)}
        )
    manifest = {
        "version": 1,
        "exchange": "bybit",
        "category": "linear",
        "resolution": "1min",
        "source": "https://api.bybit.com/v5/market/kline",
        "start": str(start),
        "end_exclusive": str(end),
        "parent_dataset_sha256": digest(baseline / "dataset.json"),
        "files": files,
        "period_status": "retrospective_development_comparison",
        "historical_funding_schedule_assumption": True,
        "promotable": False,
    }
    json_write(destination, manifest)
    return manifest


def load_execution_dataset(root: Path, baseline: Path) -> dict:
    parent = load_dataset(baseline)
    manifest = json.loads((root / "execution-dataset.json").read_text())
    start, end = development_window(parent)
    if (
        manifest.get("parent_dataset_sha256") != digest(baseline / "dataset.json")
        or pd.Timestamp(manifest["start"]) != start
        or pd.Timestamp(manifest["end_exclusive"]) != end
        or manifest.get("resolution") != "1min"
        or manifest.get("exchange") != "bybit"
        or manifest.get("category") != "linear"
        or {row["symbol"] for row in manifest["files"]} != set(ASSETS)
        or len(manifest["files"]) != 2
    ):
        raise ValueError("별도 개발 6개월의 Bybit 1분봉 명세와 일치하지 않습니다")
    for item in manifest["files"]:
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path) != item["sha256"]:
            raise ValueError("동결 1분봉 경로 또는 hash가 다릅니다")
        frame = load_candles(path)
        validate_execution(frame, start, end)
        if len(frame) != item["bars"]:
            raise ValueError("동결 1분봉 개수가 다릅니다")
    return manifest


@lru_cache(maxsize=10)
def cached_candles(path: str) -> pd.DataFrame:
    frame = load_candles(Path(path))
    return frame.map(Decimal)


def verify_parent_aggregation(root: Path, baseline: Path, manifest: dict) -> dict:
    """원본 1분봉으로 모든 부모 OHLC를 재구성하고 volume 차이는 별도 기록한다."""
    parent = load_dataset(baseline)
    start, end = pd.Timestamp(manifest["start"]), pd.Timestamp(manifest["end_exclusive"])
    audits = []
    for item in manifest["files"]:
        minute = cached_candles(str(root / item["path"]))
        for timeframe, (_, frequency) in TIMEFRAMES.items():
            parent_metadata = next(
                row
                for row in parent["files"]
                if row["symbol"] == item["symbol"] and row["timeframe"] == timeframe
            )
            expected = cached_candles(str(baseline / parent_metadata["path"]))
            expected = expected.loc[(expected.index >= start) & (expected.index < end)]
            aggregated = minute.resample(frequency).agg(
                {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
            )
            if not aggregated.index.equals(expected.index) or any(
                aggregated[name].tolist() != expected[name].tolist()
                for name in ("open", "high", "low", "close")
            ):
                raise ValueError(
                    f"{item['symbol']} {timeframe}: 1분봉 집계와 동결 부모 OHLC가 다릅니다"
                )
            volume_delta = (aggregated["volume"] - expected["volume"]).abs()
            audits.append(
                {
                    "symbol": item["symbol"],
                    "timeframe": timeframe,
                    "parent_candles": len(expected),
                    "ohlc_exact_match": True,
                    "maximum_absolute_volume_difference": str(volume_delta.max()),
                    "volume_difference_blocks_price_replay": False,
                }
            )
    audit = {
        "execution_dataset_sha256": digest(root / "execution-dataset.json"),
        "parent_dataset_sha256": digest(baseline / "dataset.json"),
        "cells": audits,
    }
    json_write(root / "aggregation-audit.json", audit)
    return audit


def cell_inputs(root: Path, baseline: Path, parent: dict, execution: dict, cell: dict) -> tuple:
    start, end = pd.Timestamp(cell["start"]), pd.Timestamp(cell["end_exclusive"])
    frequency = TIMEFRAMES[cell["timeframe"]][1]
    first = start - 200 * pd.Timedelta(frequency)
    metadata = next(
        row
        for row in parent["files"]
        if row["symbol"] == cell["symbol"] and row["timeframe"] == cell["timeframe"]
    )
    frame = cached_candles(str(baseline / metadata["path"]))
    frame = frame.loc[(frame.index >= first) & (frame.index < end)]
    validate_candles(frame, cell["timeframe"], first, end)
    minute_metadata = next(row for row in execution["files"] if row["symbol"] == cell["symbol"])
    minute_frame = cached_candles(str(root / minute_metadata["path"]))
    minute_frame = minute_frame.loc[(minute_frame.index >= start) & (minute_frame.index < end)]
    # 전체 파일은 load_execution_dataset에서 검사하고 셀의 정확한 1분 구간은 엔진이 재검사한다.
    fund_metadata = parent["funding"][cell["symbol"]]
    funding = load_funding(baseline / fund_metadata["path"])
    funding = funding.loc[(funding.index >= start) & (funding.index < end)]
    validate_funding(funding, start, end, fund_metadata["interval_minutes"])
    return frame, minute_frame, funding


def baseline_records(baseline: Path) -> tuple[dict, dict]:
    batch = json.loads((baseline / "batch.json").read_text())
    if (
        batch.get("status") != "completed"
        or batch.get("completed") != 1200
        or batch.get("dataset_sha256") != digest(baseline / "dataset.json")
    ):
        raise ValueError("동결 baseline 1,200개 완료 근거가 필요합니다")
    records = {
        (
            row["candidate_id"],
            row["cell"]["symbol"],
            row["cell"]["timeframe"],
            row["cell"]["months"],
        ): row
        for row in read_journal(baseline / "journal.jsonl").values()
        if row.get("stage") == "development"
        and row.get("status") == "completed"
        and row.get("cost_multiplier") == 1
        and row.get("engine") == batch["engine"]
        and row.get("dataset_sha256") == batch["dataset_sha256"]
    }
    if len(records) != 1200:
        raise ValueError("baseline의 1,200개 고유 완료 결과가 일치하지 않습니다")
    return batch, records


def baseline_reference(baseline: Path, record: dict, source_metadata: dict) -> dict:
    path = (baseline / record["result_path"]).resolve()
    if (
        record["source_sha256"] != source_metadata["original_source_sha256"]
        or not path.is_relative_to(baseline.resolve())
        or digest(path) != record["result_sha256"]
    ):
        raise ValueError("baseline 원본 소스 또는 결과 hash가 다릅니다")
    result = json.loads(path.read_text())
    if result["job_hash"] != record["job_hash"] or any(
        result["metrics"].get(key) != value for key, value in record["metrics"].items()
    ):
        raise ValueError("baseline 요약과 원본 결과가 다릅니다")
    return {
        "kind": "referenced_existing_result_not_rerun",
        "job_hash": record["job_hash"],
        "result_path": str(path),
        "result_sha256": record["result_sha256"],
        "source_sha256": record["source_sha256"],
        "engine": record["engine"],
        "metrics": record["metrics"],
        "acceptance": record["acceptance"],
        "closed_position_episodes": sum(trade["status"] == "closed" for trade in result["trades"]),
    }


def engine_identity() -> dict:
    from src.strategy.python_runtime.sandbox import DockerPythonTransport
    from src.strategy.python_runtime.serialization import engine_digest

    transport = DockerPythonTransport()
    try:
        return {
            "engine_digest": engine_digest(),
            "image_id": transport.image_id,
            "policy_sha256": hash_json(SWING_POLICY),
            "driver_sha256": digest(Path(__file__)),
            "signal_transform_sha256": digest(Path(__file__).with_name("swing_signals.py")),
            "baseline_driver_sha256": digest(Path(__file__).with_name("cli.py")),
            "risk_implementation_sha256": digest(
                ROOT / "apps/api/src/strategy/python_runtime/swing_risk.py"
            ),
            "sandbox_sha256": digest(ROOT / "apps/api/src/strategy/python_runtime/sandbox.py"),
        }
    finally:
        transport.close()


def run_cell(
    root: Path,
    baseline: Path,
    parent: dict,
    execution: dict,
    candidate: dict,
    cell: dict,
    identity: dict,
    reference: dict,
) -> dict:
    from src.backtest.engine.swing_risk_adapter import run_swing_risk_backtest
    from src.backtest.engine.types import BacktestConfig
    from src.strategy.python_runtime.sandbox import DockerPythonTransport

    source, source_metadata = entry_source(candidate)
    config = BacktestConfig(
        init_cash=Decimal(RESEARCH_POLICY["init_cash"]),
        fees=float(RESEARCH_POLICY["fees"]),
        slippage=float(RESEARCH_POLICY["slippage"]),
        maker_fee=float(RESEARCH_POLICY["maker_fee"]),
        freq=TIMEFRAMES[cell["timeframe"]][1],
        include_funding=True,
        fill_timing="next_bar_open",
        live_position_size_pct=100.0,
        sizing_source="form",
        sizing_basis="form_equity",
        leverage=1.0,
        leverage_basis=1.0,
    )
    job = {
        "stage": "development_swing_comparison",
        "candidate_id": candidate["id"],
        **source_metadata,
        "params": candidate["params"],
        "cell": cell,
        "parent_dataset_sha256": digest(baseline / "dataset.json"),
        "execution_dataset_sha256": digest(root / "execution-dataset.json"),
        "engine": identity,
        "risk_policy": SWING_POLICY,
        "config": dataclasses.asdict(config),
        "baseline_job_hash": reference["job_hash"],
        "baseline_result_sha256": reference["result_sha256"],
        "promotable": False,
    }
    job_hash = hash_json(job)
    journal = root / "swing-journal.jsonl"
    previous = read_journal(journal).get(job_hash)
    if previous and previous["status"] in {"completed", "error", "timeout", "blocked"}:
        if previous["status"] == "completed":
            result_path = (root / previous["result_path"]).resolve()
            if (
                not result_path.is_relative_to(root.resolve())
                or digest(result_path) != previous["result_sha256"]
            ):
                raise ValueError("완료한 swing 결과가 유실·변조되었습니다")
        return previous
    record = {
        **job,
        "job_hash": job_hash,
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
    }
    append_journal(journal, record)
    try:
        frame, minute_frame, funding = cell_inputs(root, baseline, parent, execution, cell)
        paired_baseline = run_swing_risk_backtest(
            source_for(candidate),
            frame,
            minute_frame,
            config,
            funding_rates=funding,
            params=candidate["params"],
            warmup_bars=200,
            transport_factory=lambda: DockerPythonTransport(image=identity["image_id"]),
            exit_policy="source",
        )
        result = run_swing_risk_backtest(
            source,
            frame,
            minute_frame,
            config,
            funding_rates=funding,
            params=candidate["params"],
            warmup_bars=200,
            transport_factory=lambda: DockerPythonTransport(image=identity["image_id"]),
            exit_policy="swing",
        )
        metrics = result["metrics"]
        closed = sum(trade["status"] == "closed" for trade in result["trades"])
        gate = acceptance(metrics, closed)
        baseline_metrics = paired_baseline["metrics"]
        baseline_closed = sum(trade["status"] == "closed" for trade in paired_baseline["trades"])
        paired_reference = {
            "kind": "executed_original_source_exits_on_same_1m_ledger",
            "source_sha256": source_metadata["original_source_sha256"],
            "metrics": {
                key: value
                for key, value in baseline_metrics.items()
                if key not in {"drawdown_curve", "buy_and_hold_curve", "monthly_returns"}
            },
            "acceptance": acceptance(baseline_metrics, baseline_closed),
            "closed_position_episodes": baseline_closed,
        }
        compact_metrics = {
            key: value
            for key, value in metrics.items()
            if key not in {"drawdown_curve", "buy_and_hold_curve", "monthly_returns"}
        }
        comparison = {
            "entry_rules": "identical_position_neutral_opportunities",
            "executed_entries": "may_differ_due_to_exit_timing",
            "baseline": paired_reference,
            "historical_reference": reference,
            "new_closed_position_episodes": closed,
            "delta_total_return": str(
                Decimal(str(metrics["total_return"]))
                - Decimal(str(baseline_metrics["total_return"]))
            ),
            "delta_absolute_max_drawdown": str(
                abs(Decimal(str(metrics["max_drawdown"])))
                - abs(Decimal(str(baseline_metrics["max_drawdown"])))
            ),
            "paired_ledger": "same 1m equity/funding/net sizing/cost model; original vs swing exit policy",
            "historical_reference_caveat": "old 1200 snapshot uses different sizing/funding/PF/parent-bar resolution; do not attribute its delta to exits",
        }
        parent_mdd = result.get("comparison_metrics", {}).get("parent_close_max_drawdown")
        baseline_parent_mdd = paired_baseline.get("comparison_metrics", {}).get(
            "parent_close_max_drawdown"
        )
        if parent_mdd is not None and baseline_parent_mdd is not None:
            comparison["new_parent_close_max_drawdown"] = parent_mdd
            comparison["delta_parent_close_absolute_max_drawdown"] = str(
                abs(Decimal(str(parent_mdd))) - abs(Decimal(str(baseline_parent_mdd)))
            )
        record.update(
            status="completed",
            metrics=compact_metrics,
            acceptance=gate,
            closed_position_episodes=closed,
            comparison=comparison,
        )
        result_path = root / "results" / (job_hash + ".json")
        result_path.parent.mkdir(exist_ok=True)
        json_write(result_path, {**record, "result": result, "baseline_result": paired_baseline})
        record.update(
            result_path=str(result_path.relative_to(root)), result_sha256=digest(result_path)
        )
    except Exception as exc:
        record.update(
            status="timeout"
            if "timeout" in str(exc).lower() or "timeout" in type(exc).__name__.lower()
            else "error",
            error=f"{type(exc).__name__}: {exc}",
        )
    record["finished_at"] = datetime.now(UTC).isoformat()
    append_journal(journal, record)
    print(
        f"{candidate['id']} {cell['symbol']} {cell['timeframe']} {cell['months']}m: {record['status']}",
        file=sys.stderr,
        flush=True,
    )
    return record


def validate_completed_record(root: Path, record: dict, frozen: dict, candidate: dict) -> None:
    """직렬·병렬 실행이 공유하는 완료 증거 검사. 요약 수치만으로 통과시키지 않는다."""
    _, metadata = entry_source(candidate)
    original_job = {name: value for name, value in record.items() if name not in RECORD_FIELDS}
    # 완료 시 comparison 설명 문자열이 결과 dict로 교체되므로 원래 job 설명을 복원한다.
    original_job.update(metadata)
    if (
        record["status"] != "completed"
        or record["engine"] != frozen["engine"]
        or record["execution_dataset_sha256"] != frozen["execution_dataset_sha256"]
        or record["parent_dataset_sha256"] != frozen["parent_dataset_sha256"]
        or any(
            record.get(name) != value for name, value in metadata.items() if name != "comparison"
        )
        or record["job_hash"] != hash_json(original_job)
    ):
        raise ValueError("완료 결과의 소스·정책·데이터·job hash가 동결 실험과 다릅니다")
    path = (root / record["result_path"]).resolve()
    if not path.is_relative_to(root.resolve()) or digest(path) != record["result_sha256"]:
        raise ValueError("완료 결과 파일이 유실·변조되었습니다")
    result = json.loads(path.read_text())
    if (
        result["job_hash"] != record["job_hash"]
        or result["metrics"] != record["metrics"]
        or result["comparison"] != record["comparison"]
    ):
        raise ValueError("완료 원장과 원본 결과가 다릅니다")


def validate_pilot_evidence(root: Path, frozen: dict, parent: dict) -> None:
    expected = {
        hash_json({"candidate_id": candidate["id"], "cell": cell}): candidate
        for candidate in pilot_candidates()
        for cell in cells(parent)
    }
    completed = set()
    for record in read_journal(root / "swing-journal.jsonl").values():
        key = hash_json({"candidate_id": record["candidate_id"], "cell": record["cell"]})
        if key in expected and record["status"] == "completed":
            validate_completed_record(root, record, frozen, expected[key])
            completed.add(key)
    if len(expected) != 120 or completed != set(expected):
        raise ValueError("실제 master 원장에 동일 실험의 유효한 pilot 120셀 완료 증거가 필요합니다")


def run_batch(root: Path, baseline: Path, pilot: bool) -> dict:
    parent = load_dataset(baseline)
    execution = load_execution_dataset(root, baseline)
    baseline_batch, previous = baseline_records(baseline)
    try:
        identity = engine_identity()
    except Exception as exc:
        blocked = {
            "status": "blocked",
            "reason": f"{type(exc).__name__}: {exc}",
            "completed": 0,
            "planned_cells": 120 if pilot else 1200,
            "promotable": False,
        }
        json_write(root / ("swing-pilot.json" if pilot else "swing-batch.json"), blocked)
        return blocked
    cohort = pilot_candidates() if pilot else candidates()
    frozen = {
        "parent_dataset_sha256": digest(baseline / "dataset.json"),
        "execution_dataset_sha256": digest(root / "execution-dataset.json"),
        "baseline_batch_sha256": digest(baseline / "batch.json"),
        "baseline_engine": baseline_batch["engine"],
        "engine": identity,
        "risk_policy": SWING_POLICY,
        "sources_sha256": hash_json([entry_source(item)[1] for item in candidates()]),
    }
    frozen_path = root / "experiment.json"
    if frozen_path.exists():
        if json.loads(frozen_path.read_text()) != frozen:
            raise ValueError(
                "동결 실험의 코드·소스·정책·데이터가 변경되었습니다. 별도 실행 디렉터리가 필요합니다"
            )
    else:
        json_write(frozen_path, frozen)
    if not pilot:
        pilot_summary = json.loads((root / "swing-pilot.json").read_text())
        if pilot_summary.get("completed") != 120 or pilot_summary.get(
            "experiment_sha256"
        ) != digest(frozen_path):
            raise ValueError("동일 실험의 120개 pilot이 모두 완료되어야 100개로 확대합니다")
        validate_pilot_evidence(root, frozen, parent)
    records = []
    for candidate in cohort:
        source, source_metadata = entry_source(candidate)
        source_path = root / "sources" / (candidate["id"] + "-entry.py")
        source_path.parent.mkdir(exist_ok=True)
        source_path.write_text(source)
        for cell in cells(parent):
            prior = previous[(candidate["id"], cell["symbol"], cell["timeframe"], cell["months"])]
            if prior["cell"] != cell:
                raise ValueError("baseline 비교 기간이 다릅니다")
            reference = baseline_reference(baseline, prior, source_metadata)
            records.append(
                run_cell(root, baseline, parent, execution, candidate, cell, identity, reference)
            )
    summary = {
        "status": "completed"
        if all(row["status"] == "completed" for row in records)
        else "incomplete",
        "completed": sum(row["status"] == "completed" for row in records),
        "planned_cells": len(records),
        "planned_backtests": len(records) * 2,
        "completed_backtests": sum(row["status"] == "completed" for row in records) * 2,
        "errors": sum(row["status"] != "completed" for row in records),
        "passing_cells": sum(row.get("acceptance", {}).get("passed", False) for row in records),
        "improved_net_return_cells": sum(
            Decimal(row["comparison"]["delta_total_return"]) > 0
            for row in records
            if row["status"] == "completed"
        ),
        "experiment_sha256": digest(frozen_path),
        "candidate_ids": [row["id"] for row in cohort],
        "period_status": "retrospective_development_comparison",
        "funding_status": "observed_settlements_only",
        "promotable": False,
    }
    json_write(root / ("swing-pilot.json" if pilot else "swing-batch.json"), summary)
    return summary


def write_report(root: Path) -> dict:
    """해시가 같은 완료 결과만 집계한다. 최고 성적을 검증 후보로 승격하지 않는다."""
    frozen = json.loads((root / "experiment.json").read_text())
    records = [
        row
        for row in read_journal(root / "swing-journal.jsonl").values()
        if row.get("engine") == frozen["engine"]
        and row.get("execution_dataset_sha256") == frozen["execution_dataset_sha256"]
    ]
    completed = [row for row in records if row["status"] == "completed"]
    for row in completed:
        path = (root / row["result_path"]).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path) != row["result_sha256"]:
            raise ValueError("집계할 swing 결과가 유실·변조되었습니다")
    by_timeframe = {}
    for timeframe in TIMEFRAMES:
        rows = [row for row in completed if row["cell"]["timeframe"] == timeframe]
        by_timeframe[timeframe] = {
            "completed": len(rows),
            "baseline_passing_cells": sum(
                row["comparison"]["baseline"]["acceptance"]["passed"] for row in rows
            ),
            "new_passing_cells": sum(row["acceptance"]["passed"] for row in rows),
            "improved_net_return_cells": sum(
                Decimal(row["comparison"]["delta_total_return"]) > 0 for row in rows
            ),
        }
    summary = {
        "completed": len(completed),
        "errors_or_interrupted": len(records) - len(completed),
        "hypotheses_evaluated": len({row["candidate_id"] for row in completed}),
        "by_timeframe": by_timeframe,
        "completed_backtests": len(completed) * 2,
        "comparison": "same entry rules and 1m trusted ledger; actual trades can differ due to exits",
        "baseline_kind": "original_source_exit_policy_rerun_on_same_1m_ledger",
        "historical_reference": "old 1200 results verified by hash; contextual only and not rerun with old engine",
        "mdd_comparison": "both primary MDDs are 1m close; parent_close delta separately reported when available",
        "period_status": "retrospective_development_comparison",
        "funding_status": "observed_settlements_only",
        "promotable": False,
        "cells": [
            {
                "candidate_id": row["candidate_id"],
                "cell": row["cell"],
                "job_hash": row["job_hash"],
                "result_path": row["result_path"],
                "metrics": row["metrics"],
                "acceptance": row["acceptance"],
                "comparison": row["comparison"],
            }
            for row in completed
        ],
    }
    json_write(root / "swing-summary.json", summary)
    lines = [
        "# 동일 진입 규칙의 swing 청산 비교",
        "",
        f"완료 {len(completed)}셀 · 평가 가설 {summary['hypotheses_evaluated']}개 · 오류/중단 {summary['errors_or_interrupted']}셀",
        "",
        "| 시간봉 | 완료 셀 | 기존 기준 통과 | 새 기준 통과 | 순수익률 증가 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for timeframe, counts in by_timeframe.items():
        lines.append(
            f"| {timeframe} | {counts['completed']} | {counts['baseline_passing_cells']} | {counts['new_passing_cells']} | {counts['improved_net_return_cells']} |"
        )
    lines += [
        "",
        "각 셀에서 원본 청산 정책과 새 swing 정책을 같은 1분봉 원장·수수료·순자산 sizing·펀딩 모형으로 각각 실행했다. 진입 기회 규칙은 같지만 청산 시점에 따라 실제 진입 거래 수가 달라진다. 기존 close/SL/TP는 새 정책에서 사용하지 않는다.",
        "",
        "비교한 두 정책의 기본 MDD는 모두 1분봉 종가 기준이다. 기존 1,200개 스냅샷은 hash를 확인한 참고 자료로만 보존한다. 그 스냅샷은 sizing·펀딩·PF·실행 해상도가 달라 새 정책과의 차이를 청산 효과로 사용하지 않는다.",
        "",
        "동일 TF 직전 완료 2봉의 저고점 바깥 10% SL, 1.5R 50% 반익절, 2R에서 BE 후 2R 거리 trailing을 평가한다. 1분봉 안에서도 실제 tick 순서는 알 수 없고 두 OHLC 경로의 비용 전 종가 평가가 불리한 시나리오를 선택한다.",
        "",
        "개발 기간을 재사용한 회고 비교이며 독립 최종 검증 통과·자동 등록·배포를 뜻하지 않는다. 관측 펀딩과 현재 정산 간격에 의존하며 과거 전체 정산 일정은 독립 확인되지 않았다.",
        "",
    ]
    (root / "swing-summary.md").write_text("\n".join(lines))
    return {key: value for key, value in summary.items() if key != "cells"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", default="runs/indicator-research-data")
    parser.add_argument("--run-dir", default="runs/swing-exits-v1")
    parser.add_argument("command", choices=["freeze", "validate", "pilot", "batch", "report"])
    args = parser.parse_args()
    try:
        root, baseline = output_dir(args.run_dir), Path(args.baseline_dir).resolve()
        if (
            not baseline.is_relative_to(ROOT / "runs")
            or root == baseline
            or root.is_relative_to(baseline)
            or baseline.is_relative_to(root)
        ):
            raise ValueError("baseline과 swing 결과는 runs/ 안의 서로 분리된 디렉터리여야 합니다")
        with exclusive(root):
            if args.command == "freeze":
                result = freeze_execution(root, baseline)
            elif args.command == "validate":
                manifest = load_execution_dataset(root, baseline)
                result = {
                    "dataset": manifest,
                    "aggregation_audit": verify_parent_aggregation(root, baseline, manifest),
                }
            elif args.command == "report":
                result = write_report(root)
            else:
                result = run_batch(root, baseline, args.command == "pilot")
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result.get("status", "completed") == "completed" else 1
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
