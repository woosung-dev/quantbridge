"""격리 실행만 연결하고 예정·실행·실패·미실행 분모를 보존한다."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from tools.research.period_study.dataset import load_period
from tools.research.period_study.encoding import compact
from tools.research.period_study.generation import generate_one, reviewed_source
from tools.research.period_study.schema import (
    COSTS,
    PERIODS,
    TIMEFRAMES,
    plan,
    publication_id,
)
from tools.research.period_study.state import (
    checked,
    identity,
    immutable,
    lock,
    now,
    read,
    sha,
    write,
)

ROOT = Path(__file__).resolve().parents[3]


def implementation() -> dict:
    paths = sorted((ROOT / "tools/research/period_study").glob("*.py"))
    for directory in ("strategy/code_runtime", "strategy/python_runtime", "strategy/pine_v2", "backtest/engine"):
        paths += sorted((ROOT / "apps/api/src" / directory).rglob("*.py"))
    paths.append(ROOT / "apps/api/src/strategy/research_contract.py")
    return {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths if path.exists()}


def runtime() -> dict:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker_missing")
    response = subprocess.run(  # noqa: S603 — 고정 Docker 조회 인자이며 셸을 사용하지 않는다
        [docker, "info", "--format", "{{json .Runtimes}}"], capture_output=True,
        text=True, timeout=15, check=True,
    )
    if "runsc" not in json.loads(response.stdout):
        raise RuntimeError("gvisor_runsc_missing")
    images = {}
    for language in ("pine", "python"):
        response = subprocess.run(  # noqa: S603 — 내부 고정 언어의 이미지 ID만 조회한다
            [docker, "image", "inspect", "--format", "{{.Id}}", f"quantbridge-{language}-runner:local"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        images[language] = response.stdout.strip()
        if not images[language].startswith("sha256:"):
            raise RuntimeError("runner_image_identity_missing")
    return images


def artifact(run: Path, source_root: Path, item: dict, code_path: str) -> tuple[str, str, dict]:
    original, source_hash, review = reviewed_source(source_root, item)
    if code_path == "pine":
        executable = re.sub(r'//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', "", original)
        if re.search(r"\bsyminfo\s*\.\s*(?:mintick|tickerid|ticker|prefix)\b", executable):
            raise ValueError("pine_market_context_unavailable:fixed_interpreter_metadata_is_not_Bybit_symbol_metadata")
        relative = review.get("adapted_file", review.get("executable_file"))
        expected = review.get("adapted_sha256", review.get("executable_sha256"))
        if not relative or not expected:
            raise ValueError("reviewed_pine_executable_missing")
        return checked(source_root, relative, expected).read_bytes().decode(), expected, review
    status_file = run / "generation" / publication_id(item) / "status.json"
    if not status_file.exists():
        raise ValueError("sol_generation_missing")
    status = read(status_file)
    if status["status"] != "completed":
        raise ValueError("sol_generation_terminal_failure")
    current = identity({"source": original, "signal_bindings": review["signal_bindings"],
                        "inputs": review.get("inputs", {}), "signal_mode": review.get("signal_mode")})
    if status["source_sha256"] != source_hash or status["input_hash"] != current:
        raise ValueError("sol_generation_input_mismatch")
    review_file = run / "generation" / publication_id(item) / str(status["attempt"]) / "code-review.json"
    if not review_file.exists():
        raise ValueError("sol_generated_code_review_missing")
    generated_review = read(review_file)
    if (generated_review.get("original_source_sha256") != source_hash
            or generated_review.get("generated_sha256") != status["generated_sha256"]
            or not generated_review.get("reviewer")):
        raise ValueError("sol_generated_code_review_hash_mismatch")
    if generated_review.get("status") != "reviewed_for_isolated_execution":
        raise ValueError("sol_generated_code_review_rejected:" + str(generated_review.get("reason", generated_review.get("status"))))
    market_context_proof = None
    if "market_context_file" in generated_review or "market_context_sha256" in generated_review:
        relative = generated_review.get("market_context_file")
        expected = generated_review.get("market_context_sha256")
        if not isinstance(relative, str) or not relative or not isinstance(expected, str) or not expected:
            raise ValueError("sol_generated_market_context_proof_missing")
        actual = checked(run, relative, expected)
        market_context_proof = {"file": relative, "sha256": sha(actual.read_bytes())}
    review = {**review, "generated_code_review_sha256": sha(review_file.read_bytes()),
              "market_context_proof": market_context_proof}
    return checked(run, status["generated_file"], status["generated_sha256"]).read_bytes().decode(), status["generated_sha256"], review


def cell_key(cell: dict) -> str:
    return "/".join(cell[name] for name in ("publication_id", "code_path", "timeframe", "period", "policy"))


def record(run: Path, cell: dict, request: dict, status: str, **details) -> dict:
    folder = run / "cells" / cell_key(cell)
    latest = folder / "latest.json"
    request_hash = identity(request)
    if latest.exists():
        previous = read(latest)
        if (previous["request_hash"] == request_hash and previous["status"] == status
                and previous.get("execution_attempt") == details.get("execution_attempt")):
            return previous
    attempts = list(folder.glob("attempt-*.json"))
    value = {**cell, "status": status, "request_hash": request_hash,
             "attempt": len(attempts) + 1, "updated_at": now(), **details}
    write(folder / f"attempt-{value['attempt']:03}.json", value)
    write(latest, value)
    return value


def existing(run: Path, cell: dict, request: dict) -> dict | None:
    latest = run / "cells" / cell_key(cell) / "latest.json"
    if latest.exists():
        value = read(latest)
        if value["request_hash"] == identity(request) and value["status"] == "completed":
            checked(run, value["result_file"], value["result_sha256"])
            return value
    return None


def run_group(run: Path, source_root: Path, item: dict, path: str, timeframe: str, period: str,
              *, policies: tuple[str, ...] = ("A", "B"), signal_tape: list[dict] | None = None) -> list[dict]:
    if policies not in (("A", "B"), ("A",), ("B",)):
        raise ValueError("정책 범위는 A, B 또는 순서가 고정된 A/B여야 합니다")
    if signal_tape is not None and policies != ("B",):
        raise ValueError("기존 공통 신호열은 B 단독 실행에만 전달합니다")
    pid = publication_id(item)
    cells = [{"publication_id": pid, "code_path": path, "policy": policy,
              "timeframe": timeframe, "period": period} for policy in policies]
    base = {"cells": cells, "costs": COSTS, "implementation": implementation()}
    try:
        source, source_hash, review = artifact(run, source_root, item, path)
        mode = review.get("signal_mode")
        if mode not in {"shared_events", "position_feedback"}:
            raise ValueError("reviewed_signal_mode_missing")
        warmup = review.get("warmup_bars", 1000)
        if type(warmup) is not int or warmup < 2:
            raise ValueError("reviewed_warmup_invalid")
        if not (run / "data/dataset.json").exists():
            raise ValueError("frozen_dataset_missing")
        dataset = read(run / "data/dataset.json")
        images = runtime()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        reason = f"{type(error).__name__}:{error}"
        return [record(run, cell, {**base, "unavailable_reason": reason}, "not_run", reason=reason) for cell in cells]
    sys.path.insert(0, str(ROOT / "apps/api"))
    from src.backtest.engine.types import BacktestConfig
    from src.strategy.code_runtime.backtest import run_code_backtest
    from src.strategy.python_runtime.serialization import json_value, result_payload
    from src.strategy.research_contract import ResearchExecution

    mapping_hash = identity({"source_sha256": review["source_sha256"],
                             "inputs": review.get("inputs", {}), "signal_bindings": review["signal_bindings"],
                             "signal_mode": mode})
    base.update(source_sha256=source_hash, mapping_hash=mapping_hash,
                parameters=review.get("inputs", {}), signal_mode=mode, warmup_bars=warmup,
                dataset_sha256=identity(dataset), image_ids=images,
                generated_code_review_sha256=review.get("generated_code_review_sha256"),
                market_context_proof=review.get("market_context_proof"))
    config = BacktestConfig(
        init_cash=Decimal("10000"), fees=Decimal(COSTS["taker"]),
        maker_fee=Decimal(COSTS["maker"]), slippage=Decimal(COSTS["slippage"]),
        freq={"1h": "1h", "4h": "4h", "1d": "1D"}[timeframe],
        leverage=Decimal("1"), include_funding=True, fill_timing="next_bar_open",
    )
    try:
        parent, minutes, funding, data_record = load_period(run / "data", period, timeframe, warmup)
    except (OSError, ValueError) as error:
        reason = f"{type(error).__name__}:{error}"
        return [record(run, cell, {**base, "unavailable_reason": reason}, "not_run", reason=reason) for cell in cells]
    base["data_files"] = data_record
    tape = signal_tape if signal_tape is not None else []
    completed = []
    for cell in cells:
        policy = ResearchExecution(
            contract_version=1, exit_policy="signal_only_v1" if cell["policy"] == "A" else "swing_two_bar_v1",
            reentry_policy="close_then_reenter_v1", signal_mode=mode, signal_mapping_hash=mapping_hash,
        )
        request = {**base, "policy": policy.model_dump(), "cell": cell}
        previous = existing(run, cell, request)
        if previous is not None:
            completed.append(previous)
            if cell["policy"] == "A" and mode == "shared_events":
                saved = read(checked(run, previous["result_file"], previous["result_sha256"]))
                tape = saved["signals"]
            continue
        folder = run / "cells" / cell_key(cell)
        latest = folder / "latest.json"
        first_attempt = 1
        if latest.exists():
            previous = read(latest)
            if previous["request_hash"] == identity(request) and previous["status"] == "failed":
                if previous.get("execution_attempt") == 2:
                    completed.append(previous)
                    continue
                first_attempt = previous.get("execution_attempt", 0) + 1
        if cell["policy"] == "B" and mode == "shared_events" and not tape:
            completed.append(record(run, cell, request, "not_run", reason="shared_signal_tape_unavailable"))
            continue
        with lock(folder / ".lock"):
            immutable(folder / f"request-{identity(request)}.json", request)
            for attempt in range(first_attempt, 3):
                started, trace = time.monotonic(), []
                signals = []
                try:
                    result = run_code_backtest(
                        source, path, parent, config, funding, review.get("inputs", {}), warmup,
                        trace=trace, execution_ohlcv=minutes, research_policy=policy,
                        signal_tape=tape if cell["policy"] == "B" and mode == "shared_events" else None,
                        signal_output=signals,
                    )
                    payload = result_payload(result)
                    fills = [event for event in trace if event.get("type") == "fill"]
                    closed = [trade for trade in payload["trades"] if trade["status"] == "closed"]
                    wins = sum(Decimal(trade["pnl"]) > 0 for trade in closed)
                    metrics = payload["metrics"]
                    metrics.update({
                        "closed_episodes": len(closed), "episode_count": len(payload["trades"]),
                        "fill_count": len(fills), "closed_episode_win_rate_pct": str(Decimal(wins) * 100 / len(closed)) if closed else None,
                        "r_statistics": None if cell["policy"] == "A" else "initial_r_preserved_in_fill_plans",
                        "long_closed_episode_net_pnl": str(sum((Decimal(trade["pnl"]) for trade in closed if trade["direction"] == "long"), Decimal(0))),
                        "short_closed_episode_net_pnl": str(sum((Decimal(trade["pnl"]) for trade in closed if trade["direction"] == "short"), Decimal(0))),
                    })
                    payload.update(signals=signals, trace=json_value(trace), request=request,
                                   native_signal_verification="not_claimed_by_financial_execution")
                    payload = compact(payload, run / "data")
                    result_file = folder / f"result-{identity(request)}.json.gz"
                    write(result_file, payload)
                    scalar_metrics = {key: value for key, value in metrics.items()
                                      if key not in {"drawdown_curve", "buy_and_hold_curve"}}
                    value = record(run, cell, request, "completed", result_file=str(result_file.relative_to(run)),
                                   result_sha256=sha(result_file.read_bytes()), metrics=scalar_metrics,
                                   duration_seconds=time.monotonic() - started, execution_attempt=attempt,
                                   signal_mode=mode, signal_mapping_hash=mapping_hash,
                                   original_source_sha256=review["source_sha256"], executable_sha256=source_hash,
                                   signal_hash=next((event["signal_hash"] for event in trace if event.get("type") == "research_summary"), None),
                                   curve_encoding="event_ledger_recipe_v1", raw_minute_curves_stored=False,
                                   curve_rows=len(result.equity_curve))
                    completed.append(value)
                    if cell["policy"] == "A" and mode == "shared_events":
                        tape = signals
                    break
                except Exception as error:
                    value = record(run, cell, request, "failed",
                                   reason=f"{type(error).__name__}:{error}",
                                   duration_seconds=time.monotonic() - started, execution_attempt=attempt)
                    if attempt == 2:
                        completed.append(value)
            print(f"cell {cell_key(cell)} {completed[-1]['status']}", flush=True)
    return completed


def status(run: Path) -> dict:
    frozen = read(run / "manifest.json") if (run / "manifest.json").exists() else {}
    counts, model, sources, reviews = Counter(), Counter(), Counter(), Counter()
    for path in (run / "cells").rglob("latest.json"):
        counts[read(path)["status"]] += 1
    for path in (run / "generation").glob("*/status.json"):
        model[read(path)["status"]] += 1
    for path in (run / "source_receipts").glob("*.json"):
        sources[read(path).get("status", "source_receipt")] += 1
    for path in (run / "reviews").glob("*.json"):
        reviews[read(path).get("status", "reviewed")] += 1
    controllers = [read(path) for path in run.glob("controller-*.json")]
    return {"observed_at": now(), "planned_cells": frozen.get("expected_cells", 0),
            "financial_cells": dict(counts), "pending_cells": frozen.get("expected_cells", 0) - sum(counts.values()),
            "source_target": frozen.get("source_count", 0), "source_receipts": dict(sources),
            "signal_reviews": dict(reviews), "generation": dict(model),
            "storage_paused": any(value.get("status") == "storage_paused" for value in controllers),
            "native_verification": "reported_separately", "registration": "reported_separately"}


def export(run: Path, catalogue: dict) -> dict:
    titles = {publication_id(item): item for item in catalogue["items"]}
    rows = []
    for path in (run / "cells").rglob("latest.json"):
        value = read(path)
        row = {key: value[key] for key in ("publication_id", "code_path", "policy", "timeframe", "period", "status")}
        period = next(p for p in PERIODS if p.id == row["period"])
        row.update(title=titles[row["publication_id"]]["title"], start_utc=period.start,
                   end_exclusive_utc=period.end_exclusive, reason=value.get("reason"),
                   result_file=value.get("result_file"), result_sha256=value.get("result_sha256"))
        row.update(symbol="BTCUSDT", market="Bybit linear perpetual",
                   kind=titles[row["publication_id"]].get("kind"),
                   signal_mode=value.get("signal_mode"), signal_hash=value.get("signal_hash"),
                   curve_encoding=value.get("curve_encoding", "full_curves_v1"),
                   raw_minute_curves_stored=value.get("raw_minute_curves_stored", value["status"] == "completed"),
                   comparison_scope="exit_effect_shared_events" if value.get("signal_mode") == "shared_events" else "entry_and_exit_position_feedback" if value.get("signal_mode") == "position_feedback" else None)
        kst = timezone(timedelta(hours=9))
        row.update(start_kst=datetime.fromisoformat(period.start).astimezone(kst).isoformat(),
                   end_exclusive_kst=datetime.fromisoformat(period.end_exclusive).astimezone(kst).isoformat())
        row.update({key: value.get("metrics", {}).get(key) for key in (
            "total_return", "max_drawdown", "sharpe_ratio", "closed_episode_win_rate_pct",
            "closed_episodes", "episode_count", "fill_count", "profit_factor", "total_fees",
            "total_slippage", "total_funding", "open_pnl",
            "long_closed_episode_net_pnl", "short_closed_episode_net_pnl",
        )})
        rows.append(row)
    write(run / "report-input.json", {
        "schema_version": 1, "progress": status(run), "cells": rows,
        "units": {"total_return": "ratio", "max_drawdown": "ratio_negative",
                  "closed_episode_win_rate_pct": "percent_0_100", "profit_factor": "ratio_or_null",
                  "total_fees": "USDT", "total_slippage": "USDT", "total_funding": "USDT", "open_pnl": "USDT"},
        "empty_values": "null_is_unavailable_not_zero",
        "period_bounds": "start_inclusive_end_exclusive",
    })
    if rows:
        with (run / "cells.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return {"rows": len(rows), "json": str(run / "report-input.json"), "csv": str(run / "cells.csv") if rows else None}


def command(args) -> dict:
    run = args.run_dir
    catalogue_path = args.catalogue or run / "catalogue.json"
    catalogue = read(catalogue_path)
    source_root = args.source_root or catalogue_path.parent
    if args.command == "plan":
        value = plan(catalogue, sha(catalogue_path.read_bytes()))
        immutable(run / "manifest.json", value)
        return {"source_count": value["source_count"], "expected_cells": value["expected_cells"]}
    if args.command == "status":
        return status(run)
    if args.command == "export":
        return export(run, catalogue)
    frozen = read(run / "manifest.json")
    if sha(catalogue_path.read_bytes()) != frozen["catalogue_sha256"]:
        raise ValueError("선정 코호트가 동결 목록과 다릅니다")
    items = [item for item in catalogue["items"] if not args.ids or publication_id(item) in args.ids]
    if args.command == "generate":
        counts = Counter()
        selected = items[:args.limit]

        def generate_item(item):
            try:
                with lock(run / "generation" / publication_id(item) / ".lock"):
                    result = generate_one(run, source_root, item)
                return result
            except ValueError as error:
                write(run / "generation" / publication_id(item) / "prerequisite.json", {
                    "status": "not_run", "reason": str(error), "updated_at": now(),
                })
                return {"status": "not_run"}

        consecutive = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for offset in range(0, len(selected), args.workers):
                batch = selected[offset:offset + args.workers]
                for result in pool.map(generate_item, batch):
                    counts[result["status"]] += 1
                    consecutive = (consecutive + result.get("failure_classes", []))[-2:]
                    if result["status"] == "completed":
                        consecutive = []
                if len(consecutive) == 2 and len(set(consecutive)) == 1 and consecutive[0] in {"authentication", "quota_or_rate_limit"}:
                    value = {"status": "stopped", "reason": consecutive[0], "counts": dict(counts), "next_offset": offset + len(batch), "updated_at": now()}
                    write(run / "generation-controller.json", value)
                    return value
        return {"status": "completed", "counts": dict(counts)}
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        raise ValueError("shard는 0 이상 shards 미만이어야 합니다")
    groups = 0
    for index, item in enumerate(items):
        if index % args.shards != args.shard:
            continue
        for path in args.code_paths or ("pine", "python"):
            for timeframe in args.timeframes or TIMEFRAMES:
                for period in args.periods or [p.id for p in PERIODS]:
                    if args.limit is not None and groups >= args.limit:
                        write(run / f"controller-{args.shard}.json", {"pid": os.getpid(), "status": "completed", "last_normal_at": now(), "groups": groups, "limit_reached": True})
                        return status(run)
                    free = shutil.disk_usage(run).free
                    if free < 12 * 1024**3:
                        write(run / f"controller-{args.shard}.json", {
                            "pid": os.getpid(), "status": "storage_paused", "last_normal_at": now(),
                            "groups": groups, "available_bytes": free, "reserve_bytes": 12 * 1024**3,
                            "reason": "new_financial_execution_waits_for_storage",
                        })
                        return status(run)
                    write(run / f"controller-{args.shard}.json", {
                        "pid": os.getpid(), "status": "running", "last_normal_at": now(),
                        "publication_id": publication_id(item), "code_path": path,
                        "timeframe": timeframe, "period": period,
                        "shard": args.shard, "shards": args.shards,
                    })
                    run_group(run, source_root, item, path, timeframe, period)
                    groups += 1
    write(run / f"controller-{args.shard}.json", {"pid": os.getpid(), "status": "completed", "last_normal_at": now(), "groups": groups})
    return status(run)
