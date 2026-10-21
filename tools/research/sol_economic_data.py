"""기존 관측 시세를 읽기 전용 검증·복사하고 경제 결과를 방법 품질과 분리한다.

create_snapshot: 원본 hash/grid/1분봉 OHLC 집계 검증 후 새 디렉터리에만 기록한다.
load_economic_cell: 요청 구간을 줄이거나 상위봉으로 실행 분봉을 대체하지 않는다.
economic_verdict/summarize_strategy_results: 과거 성과 판정이며 생성 품질 점수가 아니다.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from tools.research.cli import acceptance, hash_json, load_dataset  # noqa: E402
from tools.research.data import (  # noqa: E402
    ASSETS,
    TIMEFRAMES,
    digest,
    json_write,
    load_candles,
    load_funding,
    validate_candles,
    validate_funding,
)
from tools.research.swing_exits import validate_execution  # noqa: E402

RETROSPECTIVE = "retrospective_not_untouched"
FUNDING_STATUS = "observed_settlements_only"


def _time(value: str | pd.Timestamp) -> pd.Timestamp:
    result = pd.Timestamp(value)
    if result.tz is None:
        raise ValueError("시각은 timezone이 있는 UTC 시각이어야 합니다")
    return result.tz_convert("UTC")


def _safe_file(root: Path, relative: str, expected_hash: str) -> Path:
    path = (root / relative).resolve()
    if (
        not path.is_relative_to(root.resolve())
        or not path.is_file()
        or digest(path) != expected_hash
    ):
        raise ValueError("데이터 경로 또는 SHA256이 동결 증거와 다릅니다")
    return path


def _funding_audit(
    series: pd.Series, start: pd.Timestamp, end: pd.Timestamp, interval: int
) -> dict:
    selected = series.loc[(series.index >= start) & (series.index < end)]
    validate_funding(selected, start, end, interval)
    return {
        "start": str(start),
        "end_exclusive": str(end),
        "observations": len(selected),
        "interval_minutes": interval,
        "observed_grid_complete": True,
        "historical_schedule_independently_verified": False,
        "status": FUNDING_STATUS,
    }


def _verify_sources(
    parent_path: Path, execution_path: Path
) -> tuple[dict, dict, list[dict], list[dict]]:
    parent_root, execution_root = (
        parent_path.resolve().parent,
        execution_path.resolve().parent,
    )
    if (
        parent_path.name != "dataset.json"
        or execution_path.name != "execution-dataset.json"
    ):
        raise ValueError("기존 dataset.json/execution-dataset.json 계약이 필요합니다")
    parent = load_dataset(parent_root)
    expected = {(s, t) for s in ASSETS for t in TIMEFRAMES}
    if (
        len(parent["files"]) != len(expected)
        or {(x["symbol"], x["timeframe"]) for x in parent["files"]} != expected
    ):
        raise ValueError("부모 데이터 키가 중복되거나 누락되었습니다")
    execution = json.loads(execution_path.read_text())
    if (
        execution.get("exchange"),
        execution.get("category"),
        execution.get("resolution"),
    ) != ("bybit", "linear", "1min"):
        raise ValueError("Bybit linear 1분봉만 실행 데이터로 허용합니다")
    if execution.get("parent_dataset_sha256") != digest(parent_path):
        raise ValueError("실행 분봉이 다른 부모 dataset을 참조합니다")
    if len(execution["files"]) != len(ASSETS) or {
        x["symbol"] for x in execution["files"]
    } != set(ASSETS):
        raise ValueError("실행 분봉 symbol이 중복되거나 누락되었습니다")
    execution_start, execution_end = (
        _time(execution["start"]),
        _time(execution["end_exclusive"]),
    )
    historical_start, historical_end = (
        _time(parent["start"]),
        _time(parent["end_exclusive"]),
    )
    if not historical_start <= execution_start < execution_end <= historical_end:
        raise ValueError("실행 분봉 기간은 역사 부모 기간 안에 있어야 합니다")
    files = []
    parents = {}
    for item in parent["files"]:
        path = _safe_file(parent_root, item["path"], item["sha256"])
        frame = load_candles(path)
        start, end = _time(item["start"]), _time(item["end_exclusive"])
        validate_candles(frame, item["timeframe"], start, end)
        if len(frame) != item["bars"]:
            raise ValueError("부모 봉 수가 manifest와 다릅니다")
        parents[(item["symbol"], item["timeframe"])] = frame
        files.append(
            {
                **item,
                "role": "parent",
                "source_path": str(path),
                "snapshot_path": "parent/" + path.name,
            }
        )
    for symbol, item in parent["funding"].items():
        path = _safe_file(parent_root, item["path"], item["sha256"])
        funding = load_funding(path)
        if len(funding) != item["count"]:
            raise ValueError("펀딩 관측 수가 manifest와 다릅니다")
        coverage = _funding_audit(
            funding, historical_start, historical_end, int(item["interval_minutes"])
        )
        files.append(
            {
                **item,
                "symbol": symbol,
                "role": "funding",
                "source_path": str(path),
                "snapshot_path": "parent/" + path.name,
                "coverage": coverage,
            }
        )
    audits = []
    for item in execution["files"]:
        path = _safe_file(execution_root, item["path"], item["sha256"])
        minute = load_candles(path)
        validate_execution(minute, execution_start, execution_end)
        if len(minute) != item["bars"]:
            raise ValueError("실행 분봉 수가 manifest와 다릅니다")
        exact = minute.map(Decimal)
        for timeframe, (_, frequency) in TIMEFRAMES.items():
            parent_frame = parents[(item["symbol"], timeframe)]
            selected = parent_frame.loc[
                (parent_frame.index >= execution_start)
                & (parent_frame.index < execution_end)
            ].map(Decimal)
            aggregated = exact.resample(frequency).agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            if not aggregated.index.equals(selected.index) or any(
                aggregated[k].tolist() != selected[k].tolist()
                for k in ("open", "high", "low", "close")
            ):
                raise ValueError(
                    f"{item['symbol']} {timeframe}: 실행 분봉과 부모 OHLC가 다릅니다"
                )
            audits.append(
                {
                    "symbol": item["symbol"],
                    "timeframe": timeframe,
                    "parent_bars": len(selected),
                    "ohlc_decimal_exact": True,
                    "maximum_absolute_volume_difference": str(
                        (aggregated["volume"] - selected["volume"]).abs().max()
                    ),
                    "volume_difference_is_reported_not_silently_replaced": True,
                }
            )
        files.append(
            {
                **item,
                "role": "execution",
                "resolution": "1min",
                "source_path": str(path),
                "snapshot_path": "execution/" + path.name,
                "start": str(execution_start),
                "end_exclusive": str(execution_end),
            }
        )
    return parent, execution, files, audits


def create_snapshot(
    parent_manifest: Path, execution_manifest: Path, destination: Path
) -> dict:
    """원본은 쓰지 않는다. 이미 존재하는 출력 디렉터리는 덮어쓰지 않는다."""
    parent_manifest, execution_manifest, destination = (
        parent_manifest.resolve(),
        execution_manifest.resolve(),
        destination.resolve(),
    )
    if destination.exists():
        raise ValueError("기존 snapshot은 덮어쓰지 않습니다")
    if any(
        destination.is_relative_to(source.parent)
        or source.parent.is_relative_to(destination)
        for source in (parent_manifest, execution_manifest)
    ):
        raise ValueError("출력과 원본 데이터 디렉터리는 분리해야 합니다")
    parent, execution, files, audits = _verify_sources(
        parent_manifest, execution_manifest
    )
    manifest = {
        "schema_version": 1,
        "exchange": "bybit",
        "category": "linear",
        "holdout_status": RETROSPECTIVE,
        "promotable": False,
        "funding_status": FUNDING_STATUS,
        "historical_schedule_independently_verified": False,
        "sources": {
            "parent": {"path": str(parent_manifest), "sha256": digest(parent_manifest)},
            "execution": {
                "path": str(execution_manifest),
                "sha256": digest(execution_manifest),
            },
        },
        "historical_window": {
            "start": parent["start"],
            "end_exclusive": parent["end_exclusive"],
            "purpose": "historical_economics_parent_bar_resolution",
        },
        "execution_window": {
            "start": execution["start"],
            "end_exclusive": execution["end_exclusive"],
            "purpose": "retrospective_1min_execution_validation",
            "resolution": "1min",
        },
        "warmup_bars": parent["warmup_bars"],
        "files": files,
        "aggregation_audit": audits,
        "validator_sha256": digest(Path(__file__)),
    }
    # 검증이 끝난 뒤에만 디렉터리를 만든다. manifest는 모든 복사/hash 확인 후 마지막에 쓴다.
    destination.mkdir(parents=True)
    for item in files:
        target = destination / item["snapshot_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item["source_path"], target)
        if digest(target) != item["sha256"]:
            raise ValueError(
                "복사한 데이터의 SHA256이 다릅니다; 불완전한 출력은 성공으로 읽지 않습니다"
            )
    for key, source in (("parent", parent_manifest), ("execution", execution_manifest)):
        shutil.copyfile(source, destination / (key + "-manifest.json"))
    manifest["snapshot_id"] = hash_json(manifest)
    json_write(destination / "snapshot.json", manifest)
    return manifest


def load_snapshot(manifest_path: Path) -> dict:
    """복사된 파일을 매번 SHA256으로 검사한다. 원본 파일은 다시 필요하지 않다."""
    path = manifest_path.resolve()
    manifest = json.loads(path.read_text())
    identity = manifest.pop("snapshot_id")
    if (
        hash_json(manifest) != identity
        or manifest.get("holdout_status") != RETROSPECTIVE
        or manifest.get("promotable") is not False
    ):
        raise ValueError("snapshot identity 또는 회고 분석 표시가 다릅니다")
    for item in manifest["files"]:
        _safe_file(path.parent, item["snapshot_path"], item["sha256"])
    for key, source in manifest["sources"].items():
        _safe_file(path.parent, key + "-manifest.json", source["sha256"])
    manifest["snapshot_id"] = identity
    return manifest


def load_economic_cell(
    manifest_path: Path,
    symbol: str,
    timeframe: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    execution: bool = False,
    warmup_bars: int = 200,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame | None]:
    """부모봉은 warmup 포함, funding/1분봉은 평가 [start,end)만 반환한다."""
    manifest = load_snapshot(manifest_path)
    if symbol not in ASSETS or timeframe not in TIMEFRAMES or warmup_bars < 0:
        raise ValueError("지원하지 않는 symbol/timeframe/warmup입니다")
    start, end = _time(start), _time(end)
    window = manifest["execution_window" if execution else "historical_window"]
    if not _time(window["start"]) <= start < end <= _time(window["end_exclusive"]):
        raise ValueError("요청 평가 구간을 snapshot이 완전히 덮지 않습니다")
    first = start - warmup_bars * pd.Timedelta(TIMEFRAMES[timeframe][1])
    parent_item = next(
        x
        for x in manifest["files"]
        if x["role"] == "parent"
        and x["symbol"] == symbol
        and x["timeframe"] == timeframe
    )
    frame = load_candles(manifest_path.parent / parent_item["snapshot_path"])
    frame = frame.loc[(frame.index >= first) & (frame.index < end)]
    validate_candles(frame, timeframe, first, end)
    fund_item = next(
        x for x in manifest["files"] if x["role"] == "funding" and x["symbol"] == symbol
    )
    funding = load_funding(manifest_path.parent / fund_item["snapshot_path"])
    funding = funding.loc[(funding.index >= start) & (funding.index < end)]
    _funding_audit(funding, start, end, int(fund_item["interval_minutes"]))
    minute = None
    if execution:
        item = next(
            x
            for x in manifest["files"]
            if x["role"] == "execution" and x["symbol"] == symbol
        )
        minute = load_candles(manifest_path.parent / item["snapshot_path"])
        minute = minute.loc[(minute.index >= start) & (minute.index < end)]
        validate_execution(minute, start, end)
    return frame, funding, minute


def stress_scenarios() -> list[dict[str, str]]:
    """펀딩 부호는 보존한다. 경제 스트레스는 모델 생성 점수가 아니다."""
    return [
        {
            "id": name,
            "fee_multiplier": fee,
            "slippage_multiplier": slip,
            "funding_multiplier": fund,
        }
        for name, fee, slip, fund in (
            ("baseline", "1", "1", "1"),
            ("fees_x2", "2", "1", "1"),
            ("slippage_x2", "1", "2", "1"),
            ("funding_x2", "1", "1", "2"),
        )
    ]


def signal_trace_digest(trace: list[dict[str, Any]]) -> str:
    """같은 평가 구간의 봉별 action을 dedup한다. fill/위험 상태·비용은 제외한다."""
    signals = []
    previous = -1
    for item in trace:
        if item.get("type") != "intent":
            continue
        index = item["bar_index"]
        if (
            not isinstance(index, int)
            or index <= previous
            or item.get("action") not in {"hold", "long", "short", "close"}
        ):
            raise ValueError("중복·역순·잘못된 action trace입니다")
        signals.append(
            {
                "bar_index": index,
                "timestamp": str(_time(item["timestamp"])),
                "action": item["action"],
            }
        )
        previous = index
    if not signals:
        raise ValueError("빈 signal trace는 동등성 증거가 아닙니다")
    return hash_json(signals)


def economic_verdict(metrics: dict[str, Any], closed_trades: int) -> dict:
    """기존 연구 수치선을 재사용하며 미래 성과·독립 holdout 통과를 뜻하지 않는다."""
    for key in ("total_return", "max_drawdown"):
        value = Decimal(str(metrics[key]))
        if not value.is_finite():
            raise ValueError("경제 지표는 유한한 수여야 합니다")
    for key in ("profit_factor", "gross_profit_abs", "gross_loss_abs"):
        if metrics.get(key) is not None and not Decimal(str(metrics[key])).is_finite():
            raise ValueError("경제 지표는 유한한 수여야 합니다")
    if closed_trades < 0:
        raise ValueError("완료 거래 수가 음수입니다")
    verdict = acceptance(metrics, closed_trades)
    # 미기록(None)은 funding 완전성의 증거가 아니다.
    verdict["checks"]["engine_funding_range_not_incomplete"] = (
        metrics.get("funding_data_incomplete") is False
    )
    verdict["passed"] = all(verdict["checks"].values())
    return {
        **verdict,
        "holdout_status": RETROSPECTIVE,
        "promotable": False,
        "method_quality_score": None,
    }


def summarize_strategy_results(records: list[dict[str, Any]]) -> list[dict]:
    """동일 전략·cell·비용·signal은 한 번만 집계하고 다른 결과면 충돌로 거부한다."""
    unique = {}
    for row in records:
        key = (
            row["strategy_id"],
            row["cell_id"],
            row["scenario"],
            row["signal_sha256"],
        )
        economic = {"metrics": row["metrics"], "closed_trades": row["closed_trades"]}
        if key in unique and unique[key] != economic:
            raise ValueError("동일 signal/cell/scenario의 경제 결과가 다릅니다")
        unique[key] = economic
    summaries = []
    for strategy in sorted({key[0] for key in unique}):
        scenarios = {}
        for scenario in sorted({key[2] for key in unique if key[0] == strategy}):
            rows = [
                value
                for key, value in unique.items()
                if key[0] == strategy and key[2] == scenario
            ]
            verdicts = [
                economic_verdict(row["metrics"], row["closed_trades"]) for row in rows
            ]
            returns = [Decimal(str(row["metrics"]["total_return"])) for row in rows]
            scenarios[scenario] = {
                "unique_signal_cells": len(rows),
                "median_net_return": str(median(returns)),
                "minimum_net_return": str(min(returns)),
                "maximum_absolute_drawdown": str(
                    max(
                        abs(Decimal(str(row["metrics"]["max_drawdown"])))
                        for row in rows
                    )
                ),
                "economic_threshold_passes": sum(v["passed"] for v in verdicts),
            }
        summaries.append(
            {
                "strategy_id": strategy,
                "scenarios": scenarios,
                "all_stress_scenarios_present": set(scenarios)
                == {s["id"] for s in stress_scenarios()},
                "holdout_status": RETROSPECTIVE,
                "promotable": False,
                "method_quality_score": None,
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-manifest", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    manifest = create_snapshot(
        args.parent_manifest, args.execution_manifest, args.destination
    )
    print(
        json.dumps(
            {
                "snapshot_id": manifest["snapshot_id"],
                "files": len(manifest["files"]),
                "holdout_status": manifest["holdout_status"],
            }
        )
    )


if __name__ == "__main__":
    main()
