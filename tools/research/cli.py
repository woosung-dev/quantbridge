"""로컬 출처 수집 → 동결 데이터 → 파일럿 → 100개 후보 → 단일 holdout."""

from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import os
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from tools.research.catalogue import candidates, pilot_candidates, source_for  # noqa: E402
from tools.research.data import (  # noqa: E402
    ASSETS,
    TIMEFRAMES,
    digest,
    freeze,
    json_write,
    load_candles,
    load_funding,
    validate_candles,
    validate_funding,
)
from tools.research.sources import collect_sources  # noqa: E402

RESEARCH_POLICY = {
    "version": 1,
    "net_return_min_exclusive": "0",
    "profit_factor_min": "1.1",
    "absolute_drawdown_max": "0.25",
    "closed_trades_min": 30,
    "init_cash": "10000",
    "fees": "0.00055",
    "slippage": "0.00014",
    "maker_fee": "0.0002",
    "cost_basis": "프로젝트 BacktestConfig의 Bybit demo 원장 실측 기본 가정; 현재 거래소 공시 실측을 뜻하지 않음",
    "position_size_pct": "100",
    "leverage": "1",
    "warmup_bars": 200,
    "fill_timing": "next_bar_open",
    "funding_policy": "관측 funding grid 사전 검사 + 엔진 incomplete=True 차단; 과거 일정 완전성 미확증",
    "holdout_status": "retrospective_not_untouched",
    "promotable": False,
}


def output_dir(value: str) -> Path:
    root = Path(value).resolve()
    if not root.is_relative_to(ROOT / "runs"):
        raise ValueError("연구 산출물은 레포 runs/ 안에만 기록합니다")
    root.mkdir(parents=True, exist_ok=True)
    return root


def hash_json(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def catalogue_hash() -> str:
    return hash_json([{**item, "source": source_for(item)} for item in candidates()])


@contextmanager
def exclusive(root: Path):
    with (root / ".research.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("같은 연구 디렉터리에서 이미 실행 중입니다") from exc
        yield


def read_journal(path: Path) -> dict:
    records = {}
    if path.exists():
        lines = path.read_bytes().splitlines(keepends=True)
        for index, line in enumerate(lines):
            try:
                row = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                if index == len(lines) - 1 and not line.endswith(b"\n"):
                    break
                raise ValueError(
                    "연구 journal 중간 또는 완결 줄이 손상되었습니다"
                ) from None
            records[row["job_hash"]] = row
    return records


def append_journal(path: Path, record: dict) -> None:
    if path.exists():
        raw = path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            read_journal(path)  # 중간 손상은 자동 복구하지 않는다.
            boundary = raw.rfind(b"\n") + 1
            tail = raw[boundary:]
            try:
                json.loads(tail)
            except (ValueError, UnicodeDecodeError):
                # 잘린 증거는 별도 파일에 보존하고 정상 prefix부터 다시 기록한다.
                backup = path.with_name(
                    path.name + ".interrupted-" + hashlib.sha256(tail).hexdigest()
                )
                backup.write_bytes(tail)
                with path.open("r+b") as stream:
                    stream.truncate(boundary)
            else:
                with path.open("ab") as stream:
                    stream.write(b"\n")
    with path.open("a") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_dataset(root: Path) -> dict:
    manifest = json.loads((root / "dataset.json").read_text())
    if manifest["exchange"] != "bybit" or manifest["category"] != "linear":
        raise ValueError("Bybit linear 동결 데이터만 허용합니다")
    if {(item["symbol"], item["timeframe"]) for item in manifest["files"]} != {
        (symbol, timeframe) for symbol in ASSETS for timeframe in TIMEFRAMES
    }:
        raise ValueError("BTC·ETH × 3시간봉 데이터가 모두 필요합니다")
    for item in manifest["files"] + list(manifest["funding"].values()):
        path = (root / item["path"]).resolve()
        if not path.is_relative_to(root) or digest(path) != item["sha256"]:
            raise ValueError("동결 데이터 hash 또는 경로 불일치")
    return manifest


def cells(manifest: dict, stage: str = "development") -> list[dict]:
    end = pd.Timestamp(
        manifest["holdout_start"]
        if stage == "development"
        else manifest["end_exclusive"]
    )
    return [
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "months": months,
            "start": str(end - pd.DateOffset(months=months)),
            "end_exclusive": str(end),
        }
        for symbol in ASSETS
        for timeframe in TIMEFRAMES
        for months in (3, 6)
    ]


def cell_inputs(root: Path, manifest: dict, cell: dict):
    timeframe = cell["timeframe"]
    start, end = pd.Timestamp(cell["start"]), pd.Timestamp(cell["end_exclusive"])
    frequency = TIMEFRAMES[timeframe][1]
    first = start - 200 * pd.Timedelta(frequency)
    item = next(
        row
        for row in manifest["files"]
        if row["symbol"] == cell["symbol"] and row["timeframe"] == timeframe
    )
    frame = load_candles(root / item["path"])
    frame = frame.loc[(frame.index >= first) & (frame.index < end)]
    validate_candles(frame, timeframe, first, end)
    fund_meta = manifest["funding"][cell["symbol"]]
    fund = load_funding(root / fund_meta["path"])
    fund = fund.loc[(fund.index >= first) & (fund.index < end)]
    validate_funding(fund, first, end, fund_meta["interval_minutes"])
    return frame, fund


def acceptance(metrics: dict, closed_trades: int) -> dict:
    profit_factor = metrics.get("profit_factor")
    # 손실 0인 PF는 엔진 계약상 None이다. 양의 실현 이익이 있을 때만 무한대로 판정한다.
    unbounded_pf = (
        profit_factor is None
        and Decimal(str(metrics.get("gross_profit_abs") or 0)) > 0
        and Decimal(str(metrics.get("gross_loss_abs") or 0)) == 0
    )
    checks = {
        "positive_net_return": Decimal(str(metrics["total_return"]))
        > Decimal(RESEARCH_POLICY["net_return_min_exclusive"]),
        "profit_factor_at_least_1_1": unbounded_pf
        or (
            profit_factor is not None
            and Decimal(str(profit_factor))
            >= Decimal(RESEARCH_POLICY["profit_factor_min"])
        ),
        "drawdown_at_most_25pct": abs(Decimal(str(metrics["max_drawdown"])))
        <= Decimal(RESEARCH_POLICY["absolute_drawdown_max"]),
        "at_least_30_closed_trades": closed_trades
        >= RESEARCH_POLICY["closed_trades_min"],
        "engine_funding_range_not_incomplete": metrics.get("funding_data_incomplete")
        is not True,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "closed_trades": closed_trades,
        "profit_factor_unbounded": unbounded_pf,
        "funding_status": "observed_settlements_only",
        "historical_schedule_assumption": True,
    }


def engine_identity() -> dict:
    from src.strategy.python_runtime.sandbox import DockerPythonTransport
    from src.strategy.python_runtime.serialization import engine_digest

    transport = DockerPythonTransport()
    try:
        return {
            "adapter_sha256": digest(
                ROOT / "apps/api/src/backtest/engine/python_adapter.py"
            ),
            "transport": "DockerPythonTransport",
            "engine_digest": engine_digest(),
            "image_id": transport.image_id,
            "research_policy_sha256": hash_json(RESEARCH_POLICY),
            "research_driver_sha256": digest(Path(__file__)),
            "data_validator_sha256": digest(Path(__file__).with_name("data.py")),
            "sandbox_sha256": digest(
                ROOT / "apps/api/src/strategy/python_runtime/sandbox.py"
            ),
        }
    finally:
        transport.close()


def run_cell(
    root: Path,
    manifest: dict,
    candidate: dict,
    cell: dict,
    identity: dict,
    multiplier: int = 1,
    stage: str = "development",
) -> dict:
    from src.backtest.engine.python_adapter import run_python_backtest
    from src.backtest.engine.types import BacktestConfig
    from src.strategy.python_runtime.sandbox import DockerPythonTransport

    source = source_for(candidate)
    config = BacktestConfig(
        init_cash=Decimal(RESEARCH_POLICY["init_cash"]),
        fees=float(Decimal(RESEARCH_POLICY["fees"]) * multiplier),
        slippage=float(Decimal(RESEARCH_POLICY["slippage"]) * multiplier),
        maker_fee=float(Decimal(RESEARCH_POLICY["maker_fee"]) * multiplier),
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
        "stage": stage,
        "candidate_id": candidate["id"],
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "params": candidate["params"],
        "cell": cell,
        "dataset_sha256": digest(root / "dataset.json"),
        "engine": identity,
        "requested_config": dataclasses.asdict(config),
        "evaluation_policy": RESEARCH_POLICY,
        "cost_multiplier": multiplier,
        "hypothesis_status": "unverified_research_hypothesis",
        "holdout_status": "retrospective_not_untouched",
        "preregistration_status": "not_independently_verified",
        "funding_status": "observed_settlements_only",
        "historical_schedule_assumption": True,
    }
    job_hash = hash_json(job)
    journal = root / "journal.jsonl"
    previous = read_journal(journal).get(job_hash)
    if previous and previous["status"] in {"completed", "error", "timeout", "blocked"}:
        if previous["status"] == "completed":
            result_path = (root / previous["result_path"]).resolve()
            if (
                not result_path.is_relative_to(root)
                or digest(result_path) != previous["result_sha256"]
            ):
                raise ValueError("완료 결과가 유실·변조되어 재사용할 수 없습니다")
        return previous
    record = {
        **job,
        "job_hash": job_hash,
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
    }
    append_journal(journal, record)
    try:
        frame, funding = cell_inputs(root, manifest, cell)
        result = run_python_backtest(
            source,
            frame,
            config,
            funding_rates=funding,
            params=candidate["params"],
            warmup_bars=200,
            transport_factory=lambda: DockerPythonTransport(image=identity["image_id"]),
        )
        metrics = dataclasses.asdict(result.metrics)
        gate = acceptance(
            metrics, sum(trade.status == "closed" for trade in result.trades)
        )
        journal_metrics = {
            key: value
            for key, value in metrics.items()
            if key not in {"drawdown_curve", "buy_and_hold_curve", "monthly_returns"}
        }
        record.update(
            status="completed",
            metrics=journal_metrics,
            acceptance=gate,
            config_used=dataclasses.asdict(result.config_used),
            evaluated_bars=len(result.equity_curve),
        )
        result_dir = root / "results"
        result_dir.mkdir(exist_ok=True)
        result_path = result_dir / (job_hash + ".json")
        json_write(
            result_path,
            {
                **record,
                "metrics": metrics,
                "trades": [dataclasses.asdict(trade) for trade in result.trades],
                "equity_curve": [
                    [str(timestamp), str(value)]
                    for timestamp, value in result.equity_curve.items()
                ],
            },
        )
        record.update(
            result_path=str(result_path.relative_to(root)),
            result_sha256=digest(result_path),
        )
    except Exception as exc:
        category = (
            "timeout"
            if "timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower()
            else "error"
        )
        record.update(status=category, error=f"{type(exc).__name__}: {exc}")
    record["finished_at"] = datetime.now(UTC).isoformat()
    append_journal(journal, record)
    print(
        f"{candidate['id']} {cell['symbol']} {cell['timeframe']} {cell['months']}m cost={multiplier}: {record['status']}",
        flush=True,
    )
    return record


def run_batch(root: Path, pilot: bool) -> dict:
    manifest = load_dataset(root)
    stage_path = root / "pilot.json"
    if not pilot:
        if not stage_path.exists():
            raise ValueError("100개 확대 전에 pilot을 완료하세요")
        pilot_result = json.loads(stage_path.read_text())
        if (
            pilot_result.get("completed") != 120
            or pilot_result.get("dataset_sha256") != digest(root / "dataset.json")
            or pilot_result.get("catalogue_sha256") != catalogue_hash()
        ):
            raise ValueError(
                "같은 데이터에서 10후보 × 12셀 파일럿 120개가 모두 완료되어야 합니다"
            )
    try:
        identity = engine_identity()
    except Exception as exc:
        blocked = {
            "status": "blocked",
            "reason": f"{type(exc).__name__}: {exc}",
            "completed": 0,
            "planned_cells": 120 if pilot else 1200,
            "dataset_sha256": digest(root / "dataset.json"),
        }
        json_write(stage_path if pilot else root / "batch.json", blocked)
        return blocked
    if not pilot and pilot_result.get("engine") != identity:
        raise ValueError(
            "파일럿 후 실행 환경이 변경되었습니다. pilot을 다시 완료하세요"
        )
    selected = pilot_candidates() if pilot else candidates()
    records = [
        run_cell(root, manifest, candidate, cell, identity)
        for candidate in selected
        for cell in cells(manifest)
    ]
    summary = {
        "status": "completed"
        if all(record["status"] == "completed" for record in records)
        else "incomplete",
        "completed": sum(record["status"] == "completed" for record in records),
        "planned_cells": len(records),
        "passing_cells": sum(
            record.get("acceptance", {}).get("passed", False) for record in records
        ),
        "dataset_sha256": digest(root / "dataset.json"),
        "candidate_ids": [item["id"] for item in selected],
        "catalogue_sha256": catalogue_hash(),
        "engine": identity,
    }
    json_write(stage_path if pilot else root / "batch.json", summary)
    return summary


def freeze_champion(root: Path, candidate_id: str, symbol: str, timeframe: str) -> dict:
    if (root / "champion.json").exists() or (root / "holdout-opened.json").exists():
        raise ValueError("최종 후보는 한 번만 동결할 수 있습니다")
    load_dataset(root)
    batch = json.loads((root / "batch.json").read_text())
    identity = engine_identity()
    if (
        batch["status"] != "completed"
        or batch["dataset_sha256"] != digest(root / "dataset.json")
        or batch.get("catalogue_sha256") != catalogue_hash()
        or batch.get("engine") != identity
    ):
        raise ValueError("100후보 1,200셀 개발 평가 완료 후에만 동결합니다")
    candidate = next(item for item in candidates() if item["id"] == candidate_id)
    records = list(read_journal(root / "journal.jsonl").values())
    passing = [
        record
        for record in records
        if record.get("stage") == "development"
        and record.get("candidate_id") == candidate_id
        and record["cell"]["symbol"] == symbol
        and record["cell"]["timeframe"] == timeframe
        and record.get("cost_multiplier") == 1
        and record.get("source_sha256")
        == hashlib.sha256(source_for(candidate).encode()).hexdigest()
        and record.get("dataset_sha256") == digest(root / "dataset.json")
        and record.get("engine") == identity
        and record.get("acceptance", {}).get("passed")
    ]
    if not passing:
        raise ValueError("선택한 종목·시간봉에서 개발 통과 근거가 없습니다")
    champion = {
        "candidate": candidate,
        "symbol": symbol,
        "timeframe": timeframe,
        "source": source_for(candidate),
        "dataset_sha256": digest(root / "dataset.json"),
        "engine": identity,
        "frozen_at": datetime.now(UTC).isoformat(),
        "development_job_hashes": [record["job_hash"] for record in passing],
        "source_evidence": "독립 가설; 영상 실적 또는 최종 기간을 본 규칙으로 수정하지 말 것",
    }
    json_write(root / "champion.json", champion)
    return champion


def evaluate_champion(root: Path) -> dict:
    manifest = load_dataset(root)
    champion = json.loads((root / "champion.json").read_text())
    identity = engine_identity()
    if (
        champion["dataset_sha256"] != digest(root / "dataset.json")
        or champion["source"] != source_for(champion["candidate"])
        or champion["engine"] != identity
    ):
        raise ValueError("동결 후 코드·데이터·실행 환경이 변경되었습니다")
    opening = root / "holdout-opened.json"
    if opening.exists():
        raise ValueError(
            "이미 개봉한 holdout입니다. 실패 후 재선정·재평가할 수 없습니다"
        )
    # 결과가 나오기 전에 기록한다. 중단·오류도 이미 열어본 기간이다.
    json_write(
        opening,
        {
            "champion_sha256": digest(root / "champion.json"),
            "opened_at": datetime.now(UTC).isoformat(),
        },
    )
    selected = [
        cell
        for cell in cells(manifest, "holdout")
        if cell["symbol"] == champion["symbol"]
        and cell["timeframe"] == champion["timeframe"]
    ]
    records = [
        run_cell(
            root, manifest, champion["candidate"], cell, identity, multiplier, "holdout"
        )
        for cell in selected
        for multiplier in (1, 2)
    ]
    summary = {
        "status": "completed"
        if all(record["status"] == "completed" for record in records)
        else "incomplete",
        "thresholds_passed": all(
            record.get("acceptance", {}).get("passed", False)
            for record in records
            if record["cost_multiplier"] == 1
        ),
        "promotable": False,
        "promotion_blockers": [
            "retrospective_not_untouched",
            "historical_funding_schedule_not_independently_verified",
        ],
        "holdout_status": "retrospective_not_untouched",
        "preregistration_status": "not_independently_verified",
        "funding_status": "observed_settlements_only",
        "historical_schedule_assumption": True,
        "cost_2x_is_informational": True,
        "records": records,
        "server_deployment": "requires_explicit_approval",
    }
    json_write(root / "holdout.json", summary)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="runs/indicator-research")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sources", help="6채널 공개 metadata 수집 (규칙 검증 아님)")
    sub.add_parser("catalogue", help="100개 미검증 가설과 10개 파일럿 소스 생성")
    freeze_parser = sub.add_parser("freeze", help="Bybit 시세·펀딩 동결")
    freeze_parser.add_argument(
        "--end", required=True, help="UTC 날짜 YYYY-MM-DD; 이 날짜 봉부터 제외"
    )
    freeze_parser.add_argument("--months", type=int, default=24)
    sub.add_parser("validate", help="동결 hash·개발 셀 데이터 완전성 검증")
    sub.add_parser("pilot", help="10후보 × 12개 개발 셀")
    sub.add_parser("batch", help="100후보 × 12개 개발 셀")
    champion_parser = sub.add_parser("champion", help="개발 결과로 단일 후보 동결")
    champion_parser.add_argument("--candidate", required=True)
    champion_parser.add_argument("--symbol", choices=ASSETS, required=True)
    champion_parser.add_argument("--timeframe", choices=TIMEFRAMES, required=True)
    sub.add_parser("holdout", help="동결 후보만 최종 기간 1회 개봉")
    args = parser.parse_args(argv)
    try:
        root = output_dir(args.run_dir)
        with exclusive(root):
            if args.command == "sources":
                result = collect_sources()
                json_write(root / "sources.json", result)
                result = {
                    "channels": result["channels"],
                    "collected_sources": len(result["sources"]),
                }
            elif args.command == "catalogue":
                items = candidates()
                source_dir = root / "candidates"
                source_dir.mkdir(exist_ok=True)
                for candidate in items:
                    path = source_dir / (candidate["id"] + ".py")
                    path.write_text(source_for(candidate))
                    candidate["source_sha256"] = digest(path)
                json_write(
                    root / "candidates.json",
                    {
                        "candidates": items,
                        "pilot_ids": [row["id"] for row in pilot_candidates()],
                    },
                )
                result = {
                    "hypotheses": len(items),
                    "source_reproductions": 0,
                    "pilot": 10,
                }
            elif args.command == "freeze":
                result = freeze(root, pd.Timestamp(args.end, tz="UTC"), args.months)
            elif args.command == "validate":
                manifest = load_dataset(root)
                for cell in cells(manifest):
                    cell_inputs(root, manifest, cell)
                result = {"valid_development_cells": 12, "holdout_not_evaluated": True}
            elif args.command in {"pilot", "batch"}:
                result = run_batch(root, args.command == "pilot")
            elif args.command == "champion":
                result = freeze_champion(
                    root, args.candidate, args.symbol, args.timeframe
                )
            else:
                result = evaluate_champion(root)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 2 if result.get("status") in {"blocked", "incomplete"} else 0
    except (ValueError, KeyError, OSError, StopIteration) as exc:
        print(f"차단: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
