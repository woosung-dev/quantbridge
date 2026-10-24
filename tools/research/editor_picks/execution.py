"""동결 작업만 gVisor에서 실행하고 원시 곡선·신호·실패 분모를 보존한다."""

from __future__ import annotations

import gzip
import itertools
import json
import shutil
import subprocess
import time
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pandas as pd
from tools.research.editor_picks.common import (
    ARMS,
    PERIODS,
    ROOT,
    SCENARIOS,
    TIMEFRAMES,
    cached,
    checked_file,
    identity,
    immutable,
    lock,
    now,
    read,
    receipt,
    sha,
    write,
)


def implementation() -> dict:
    paths = sorted((ROOT / "tools/research/editor_picks").glob("*.py"))
    paths += sorted((ROOT / "apps/api/src/strategy/code_runtime").glob("*.py"))
    paths += sorted((ROOT / "apps/api/src/strategy/python_runtime").glob("*.py"))
    paths += sorted((ROOT / "apps/api/src/backtest/engine").glob("*.py"))
    paths += sorted((ROOT / "apps/api/src/strategy/pine_v2").rglob("*.py"))
    paths += [
        ROOT / relative
        for relative in (
            "tools/research/cli.py",
            "tools/research/data.py",
            "tools/research/sol_economics.py",
            "tools/research/sol_economic_data.py",
            "apps/api/src/core/config.py",
            "apps/api/src/strategy/pine/types.py",
            "apps/api/scripts/pine_validation/native_capture.py",
            "infra/python-runner/main.py",
        )
    ]
    return {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in paths}


def plan(root: Path, pilot: bool = False) -> dict:
    cohort_file = "pilot-cohort.json" if pilot else "cohort.json"
    cohort = read(root / cohort_file)
    dataset = read(root / "data/dataset.json")
    selected = cohort["items"][:6] if pilot else cohort["items"]
    artifacts = {}
    for item in selected:
        artifacts[item["id"]] = {}
        for arm in ARMS:
            try:
                _, language, digest = artifact(root, item, arm)
                artifacts[item["id"]][arm] = {
                    "language": language,
                    "source_sha256": digest,
                }
            except ValueError as error:
                artifacts[item["id"]][arm] = {"unavailable_reason": str(error)}
    # 실제 확보 수와 별도로 목표 슬롯을 남겨 미확보 분모가 사라지지 않게 한다.
    identifiers = [item["id"] for item in selected]
    target = 6 if pilot else cohort["target"]
    identifiers += [f"UNFILLED-{n:03}" for n in range(len(identifiers), target)]
    period_options, costs = ((6,), ("baseline",)) if pilot else (PERIODS, SCENARIOS)
    jobs = [
        {
            "id": identifier,
            "arm": arm,
            "timeframe": tf,
            "months": months,
            "scenario": scenario,
        }
        for identifier, arm, tf, months, scenario in itertools.product(
            identifiers, ARMS, TIMEFRAMES, period_options, costs
        )
    ]
    value = {
        "schema_version": 1,
        "phase": "pilot" if pilot else "full",
        "jobs": jobs,
        "expected_cells": target * len(ARMS) * len(TIMEFRAMES) * len(period_options) * len(costs),
        "cohort_file": cohort_file,
        "cohort_sha256": sha((root / cohort_file).read_bytes()),
        "dataset_sha256": sha((root / "data/dataset.json").read_bytes()),
        "implementation": implementation(),
        "artifacts": artifacts,
        "dataset": dataset,
        "policy": "swing_two_bar_v1",
        "created_at": now(),
    }
    path = root / f"{value['phase']}-plan.json"
    if path.exists():
        value["created_at"] = read(path)["created_at"]
    immutable(path, value)
    return value


def artifact(root: Path, item: dict, arm: str) -> tuple[str, str, str]:
    if arm == "pine":
        path = checked_file(root, item["adapted_file"], item["adapted_sha256"])
        return path.read_bytes().decode(), "pine", item["adapted_sha256"]
    # 구문 오류 수정의 첫 성공만 선택한다. 수익·비공개 의미 점수는 읽지 않는다.
    for attempt in range(3):
        folder = root / "generation" / item["id"] / arm / str(attempt)
        if not (folder / "receipt.json").exists():
            continue
        value = read(folder / "receipt.json")
        if value["status"] == "completed":
            request_path = checked_file(folder, "request.json", value["files"]["request.json"])
            request = read(request_path)
            if value["job_hash"] != identity(request):
                raise ValueError("생성 완료 기록의 요청 해시가 다릅니다")
            for name, expected in value["files"].items():
                checked_file(folder, name, expected)
            from tools.research.editor_picks.common import MODELS
            from tools.research.editor_picks.generation import CONTRACT

            if not request["prompt"].startswith(CONTRACT + "\n"):
                raise ValueError("생성 공개 계약이 현재 코호트와 다릅니다")
            context = json.loads(request["prompt"][len(CONTRACT) + 1 :])
            if (
                request["arm"] != arm
                or request["attempt"] != attempt
                or request["requested_model"] != MODELS[arm]
                or request["source_sha256"] != item["source_sha256"]
                or sha(context["source"].encode()) != item["source_sha256"]
                or context["bindings"] != item["signal_bindings"]
                or context["inputs"] != item.get("inputs", {})
            ):
                raise ValueError("생성 요청의 모델·원문·입력이 코호트와 다릅니다")
            path = checked_file(folder, "source.py", value["files"]["source.py"])
            return path.read_bytes().decode(), "python", sha(path.read_bytes())
    raise ValueError("completed_generation_missing")


def require_runtime() -> dict:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker 실행 파일이 없습니다")
    process = subprocess.run(  # noqa: S603 — 고정 Docker 조회 명령만 실행
        [docker, "info", "--format", "{{json .Runtimes}}"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    if "runsc" not in json.loads(process.stdout):
        raise RuntimeError("gVisor runsc 미등록: 호스트 실행으로 우회하지 않습니다")
    images = {}
    for language in ("pine", "python"):
        name = f"quantbridge-{language}-runner:local"
        images[language] = subprocess.run(  # noqa: S603 — 내부 고정 이미지 이름만 조회
            [docker, "image", "inspect", "--format", "{{.Id}}", name],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        ).stdout.strip()
        if not images[language].startswith("sha256:"):
            raise ValueError("실행 이미지 ID가 없습니다")
    return images


@lru_cache(maxsize=1)
def data(root_text: str, dataset_hash: str) -> dict:
    from tools.research.data import load_candles, load_funding
    from tools.research.editor_picks.dataset import validate

    root = Path(root_text)
    if sha((root / "data/dataset.json").read_bytes()) != dataset_hash:
        raise ValueError("동결 시세 명세가 다릅니다")
    manifest = validate(root)
    return {
        key: (load_funding if key == "funding" else load_candles)(
            checked_file(root / "data", value["path"], value["sha256"])
        )
        for key, value in manifest["files"].items()
    }


def episode_metrics(payload: dict, trace: list[dict]) -> dict:
    """부분 익절을 합친 episode의 비용 후 R과 분봉 보유 비율을 계산한다."""
    trades = payload["trades"]
    closed = [trade for trade in trades if trade["status"] == "closed"]
    entries = {
        fill["generation"] - 1: fill["plan"]
        for fill in trace
        if fill["type"] == "fill" and fill["kind"] == "entry"
    }
    multiples = []
    intervals = []
    bars = len(payload["equity_curve"])
    for trade in trades:
        start = trade["entry_bar_index"]
        end = trade["exit_bar_index"]
        stop = bars if end is None else end + (trade["exit_phase"] != "bar_open")
        if not 0 <= start <= stop <= bars:
            raise ValueError("episode 보유 구간이 실행 분봉 범위를 벗어납니다")
        intervals.append((start, stop))
        if trade["status"] == "closed":
            plan = entries.get(trade["trade_index"])
            if plan is None:
                raise ValueError("완료 episode의 초기 위험 근거가 없습니다")
            initial_risk = Decimal(plan["risk"]) * Decimal(plan["initial_qty"])
            if initial_risk <= 0:
                raise ValueError("완료 episode의 초기 위험은 양수여야 합니다")
            multiples.append(Decimal(trade["pnl"]) / initial_risk)
    exposed, previous_end = 0, 0
    for start, stop in sorted(intervals):
        exposed += max(0, stop - max(start, previous_end))
        previous_end = max(previous_end, stop)
    wins = sum(Decimal(trade["pnl"]) > 0 for trade in closed)
    return {
        "avg_closed_episode_r": str(sum(multiples, Decimal(0)) / len(multiples))
        if multiples
        else None,
        "closed_episode_win_rate_pct": str(Decimal(wins) * 100 / len(closed)) if closed else None,
        "exposure_minute_pct": str(Decimal(exposed) * 100 / bars) if bars else None,
        "closed_episodes": len(closed),
    }


def execute_job(root: Path, frozen: dict, job: dict, images: dict) -> dict:
    from tools.research.sol_economic_data import economic_verdict, stress_scenarios
    from tools.research.sol_economics import scenario_config

    from src.strategy.code_runtime.backtest import run_code_backtest
    from src.strategy.code_runtime.session import create_code_transport
    from src.strategy.python_runtime.serialization import json_value, result_payload

    if (
        sha((root / frozen["cohort_file"]).read_bytes()) != frozen["cohort_sha256"]
        or frozen["implementation"] != implementation()
    ):
        raise ValueError("동결 코호트 또는 구현이 다릅니다")
    items = {item["id"]: item for item in read(root / frozen["cohort_file"])["items"]}
    item = items.get(job["id"])
    request = {"plan": identity(frozen), "job": job, "images": images}
    source = language = None
    if item is None:
        request["unavailable_reason"] = "source_not_acquired"
    else:
        selection = frozen["artifacts"][job["id"]][job["arm"]]
        if "unavailable_reason" in selection:
            request["unavailable_reason"] = selection["unavailable_reason"]
        else:
            source, language, source_hash = artifact(root, item, job["arm"])
            if selection != {"language": language, "source_sha256": source_hash}:
                raise ValueError("경제 측정 전에 동결한 생성물이 바뀌었습니다")
            request["source_sha256"] = source_hash
    folder = root / "results" / identity(request)
    with lock(folder / ".lock"):
        previous = cached(folder, request)
        if previous is not None and previous["status"] != "interrupted":
            return previous
        immutable(folder / "request.json", request)
        if source is None:
            return receipt(
                folder,
                request,
                "not_available",
                job=job,
                reason=request["unavailable_reason"],
            )
        started = time.monotonic()
        try:
            loaded = data(str(root), frozen["dataset_sha256"])
            end = pd.Timestamp(frozen["dataset"]["end"])
            start = end - pd.DateOffset(months=job["months"])
            warmup = item["warmup_bars"]
            if warmup > frozen["dataset"]["warmup"]:
                raise ValueError("동결 데이터보다 긴 준비봉이 필요합니다")
            tf = job["timeframe"]
            freq = {"1h": "1h", "4h": "4h", "1d": "1D"}[tf]
            frame = loaded[tf].loc[
                (loaded[tf].index >= start - warmup * pd.Timedelta(freq)) & (loaded[tf].index < end)
            ]
            minute = loaded["1min"].loc[
                (loaded["1min"].index >= start) & (loaded["1min"].index < end)
            ]
            funding = loaded["funding"].loc[
                (loaded["funding"].index >= start) & (loaded["funding"].index < end)
            ]
            scenario = next(s for s in stress_scenarios() if s["id"] == job["scenario"])
            funding = funding.map(
                lambda rate: Decimal(str(rate)) * Decimal(scenario["funding_multiplier"])
            )
            config = scenario_config(tf, scenario)
            trace = []

            def transport():
                instance = create_code_transport(language, frame)
                if instance.image_id != images[language]:
                    instance.close()
                    raise ValueError("동결 실행 이미지가 바뀌었습니다")
                return instance

            result = run_code_backtest(
                source,
                language,
                frame,
                config,
                funding,
                item.get("inputs", {}),
                warmup,
                transport_factory=transport,
                execution_ohlcv=minute,
                trace=trace,
            )
            payload = result_payload(result)
            payload["metrics"].update(episode_metrics(payload, json_value(trace)))
            raw = json.dumps(
                {"result": payload, "trace": json_value(trace)}, allow_nan=False
            ).encode()
            (folder / "result.json.gz").write_bytes(gzip.compress(raw, mtime=0))
            actions = [
                event
                for event in trace
                if event["type"] == "intent" and event["bar_index"] >= warmup
            ]
            action_hash = identity(
                [{key: row[key] for key in ("timestamp", "action")} for row in actions]
            )
            signal_rows = [{key: row[key] for key in ("timestamp", "action")} for row in actions]
            (folder / "signals.json.gz").write_bytes(
                gzip.compress(json.dumps(signal_rows).encode(), mtime=0)
            )
            closed = sum(trade.status == "closed" for trade in result.trades)
            details = {
                # 원시 full payload는 gzip에 보존하고 receipt의 대형 중복 배열만 제외한다.
                "metrics": {
                    key: value for key, value in payload["metrics"].items()
                    if key not in {"drawdown_curve", "buy_and_hold_curve"}
                },
                "action_sha256": action_hash,
                "closed_episodes": closed,
                "intent_count": len(actions),
                "ledger_sha256": identity(
                    {"trades": payload["trades"], "equity": payload["equity_curve"]}
                ),
                "economic_verdict": economic_verdict(payload["metrics"], closed),
                "funding_status": "observed_settlements_only",
                "native_verified": False,
                "promotable": False,
            }
            status = "completed"
        except Exception as error:
            details, status = {"error": f"{type(error).__name__}: {error}"}, "failed"
        return receipt(
            folder,
            request,
            status,
            job=job,
            duration_seconds=time.monotonic() - started,
            **details,
        )


def execute(root: Path, plan_path: Path, shard: int = 0, shards: int = 1) -> dict:
    frozen = read(plan_path)
    if not 0 <= shard < shards:
        raise ValueError("shard 범위가 잘못됐습니다")
    try:
        images = require_runtime()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        blocked = {
            "status": "blocked",
            "error": str(error),
            "plan_sha256": identity(frozen),
            "observed_at": now(),
        }
        write(root / f"runtime-blocked-{shard}.json", blocked)
        return blocked
    rows = [
        execute_job(root, frozen, job, images)
        for index, job in enumerate(frozen["jobs"])
        if index % shards == shard
    ]
    value = {
        "status": "finished",
        "plan_sha256": identity(frozen),
        "shard": shard,
        "shards": shards,
        "jobs_consumed": len(rows),
        "observed_at": now(),
    }
    write(root / f"worker-{frozen['phase']}-{shard}.json", value)
    return value
