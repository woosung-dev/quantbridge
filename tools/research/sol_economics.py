"""품질 순위로 먼저 고정한 코드를 실제 언어 실행기로 회고 경제 검증한다.

--plan-only는 Docker·모델·거래소를 호출하지 않는다. 실행에는 30개 case의 품질 선정
증거가 필수다. 수익을 보고 반복·언어를 다시 고르거나 원본 CSV를 수정하지 않는다.

선정 JSON: policy=quality_winner_then_first_semantic_pass, quality_stage=full_eval,
decided_before_economics=true, arm, language, quality_evidence={path,sha256},
semantic_pass_repetitions={01:[0,2],...}, selected_source_hashes={01:sha256,...}.
pass 없음은 [] 및 null source hash다. --environment는 기존 pilot manifest 또는 그
environment 객체를 받는다. --output은 현재 checkout의 runs/ 아래에만 허용한다.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import platform
import re
import sys
import time
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from tools.research.cli import (  # noqa: E402
    RESEARCH_POLICY,
    append_journal,
    exclusive,
    hash_json,
    output_dir,
)
from tools.research.data import ASSETS, TIMEFRAMES, digest, json_write  # noqa: E402
from tools.research.sol_codegen import digest as quality_digest  # noqa: E402
from tools.research.sol_score_report import selection_decision  # noqa: E402
from tools.research.sol_economic_data import (  # noqa: E402
    RETROSPECTIVE,
    economic_verdict,
    load_economic_cell,
    load_snapshot,
    signal_trace_digest,
    stress_scenarios,
    summarize_strategy_results,
)

from src.backtest.engine.types import BacktestConfig  # noqa: E402
from src.strategy.code_runtime.backtest import run_code_backtest  # noqa: E402
from src.strategy.code_runtime.models import CodeLanguage  # noqa: E402
from src.strategy.code_runtime.session import create_code_transport  # noqa: E402
from src.strategy.python_runtime.protocol import validate_source_and_params  # noqa: E402
from src.strategy.python_runtime.serialization import json_value  # noqa: E402

POLICY = "quality_winner_then_first_semantic_pass"
# 카탈로그의 고정 시간봉 의미를 보존한다. 생성 소스의 문자열을 추측하지 않는다.
CASE_TIMEFRAMES = {
    **{f"{number:02}": ("1h", "4h", "1d") for number in range(1, 31)},
    "21": ("1h", "4h"),
    "30": ("1h",),
}
CASE_TIMEFRAME_REASONS = {
    "21": "UTC 일중 VWAP은 일봉마다 reset되어 일중 다중 봉 정의를 보존할 수 없습니다",
    "30": "1h EMA9/21과 직전 완료 4h regime 정의는 1h 부모 신호봉에서만 유지됩니다",
}
IMAGES = {
    language: f"quantbridge-{name}-runner:local"
    for language, name in (
        ("pine", "pine"),
        ("python", "python"),
        ("typescript", "typescript"),
    )
}


def read_artifacts(path: Path) -> list[dict]:
    """실패한 source도 행을 제거하지 않는다. null은 semantic pass 없음의 명시 표현이다."""
    values = json.loads(path.read_text())
    required = {"case_id", "language", "source_path", "source_hash", "arm", "repetition"}
    if not isinstance(values, list) or not values:
        raise ValueError("비어 있지 않은 artifact 목록이 필요합니다")
    result = []
    for item in values:
        if (
            not isinstance(item, dict)
            or set(item) != required
            or item["arm"] not in {"A", "B", "C"}
            or not isinstance(item["case_id"], str)
        ):
            raise ValueError("artifact의 정확한 6개 필드·arm·case_id가 필요합니다")
        CodeLanguage(item["language"])
        row = dict(item)
        row["observed_source_hash"] = None
        source = item["source_path"]
        if source is None:
            if item["source_hash"] is not None or item["repetition"] is not None:
                raise ValueError(
                    "semantic pass 없음은 source/hash/repetition 모두 null이어야 합니다"
                )
            row.update(source_code=None, source_error="no_semantic_pass")
        else:
            if (
                not isinstance(source, str)
                or not isinstance(item["source_hash"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["source_hash"])
                or type(item["repetition"]) is not int
                or item["repetition"] < 0
            ):
                raise ValueError("source 경로·SHA256·0부터 시작하는 반복 번호가 필요합니다")
            resolved = (path.parent / source).resolve()
            row["source_path"] = str(resolved)
            try:
                raw = resolved.read_bytes()
                row["observed_source_hash"] = hashlib.sha256(raw).hexdigest()
                code = raw.decode("utf-8")
                validate_source_and_params(code, {})
                if hashlib.sha256(raw).hexdigest() != item["source_hash"]:
                    raise ValueError("원문 해시가 다릅니다")
                row.update(source_code=code, source_error=None)
            except (OSError, UnicodeError, ValueError) as exc:
                row.update(source_code=None, source_error=f"source_integrity: {exc}")
        result.append(row)
    identities = [(x["case_id"], x["arm"], x["language"], x["repetition"]) for x in result]
    if len(set(identities)) != len(identities):
        raise ValueError("동일 artifact를 중복 선택할 수 없습니다")
    return result


def validate_selection(path: Path, artifacts: list[dict]) -> dict:
    """품질 증거의 파일 해시와 첫 semantic pass를 확인한다. 경제 수치를 읽지 않는다."""
    value = json.loads(path.read_text())
    if (
        value.get("policy") != POLICY
        or value.get("decided_before_economics") is not True
    ):
        raise ValueError("수익 열람 전 품질 선정 선언이 필요합니다")
    evidence = value["quality_evidence"]
    source = (path.parent / evidence["path"]).resolve()
    if (
        digest(source) != evidence["sha256"]
        or value.get("quality_stage") != "full_eval"
    ):
        raise ValueError("full-eval 품질 근거 파일 해시가 다릅니다")
    report = json.loads(source.read_text())
    proof = {
        "manifest_sha256": report.get("manifest_sha256"),
        "files": report.get("input_files"),
        "implementations": report.get("implementation_hashes"),
    }
    if (
        report.get("schema_version") != 1
        or report.get("stage") != "evaluation"
        or report.get("complete") is not True
        or report.get("final_selection_allowed") is not True
        or report.get("expected_artifacts") != 1350
        or not re.fullmatch(r"[0-9a-f]{64}", report.get("manifest_sha256", ""))
        or value.get("manifest_sha256") != report["manifest_sha256"]
        or value.get("input_proof_sha256") != report.get("input_proof_sha256")
        or quality_digest(proof) != report.get("input_proof_sha256")
    ):
        raise ValueError(
            "완료된 full-eval 품질 보고서·manifest·입력 proof가 필요합니다"
        )
    candidates = report.get("quality90_ranking", [])
    if (
        len(candidates) != 9
        or {cell["combination"] for cell in candidates}
        != {f"{arm}/{language}" for arm, language in itertools.product(
            "ABC", ("pine", "python", "typescript"))}
        or any(cell.get("expected_artifacts") != 150 for cell in candidates)
    ):
        raise ValueError("품질 보고서의 사전 선정 정책 분모가 다릅니다")
    decision = selection_decision(candidates)
    if (
        any(report.get(key) != expected for key, expected in decision.items())
        or value.get("candidate_selection") != decision
        or value.get("decision_authority") != decision["policy"]
        or f"{value.get('arm')}/{value.get('language')}"
        != decision["selected_candidate"]
    ):
        raise ValueError("품질 보고서의 사전 선정 정책 후보와 다릅니다")
    quality_rows = report.get("artifact_scores", [])
    identities = {
        (row["case_id"], row["arm"], row["language"], row["repetition"]) for row in quality_rows
    }
    expected_rows = set(
        itertools.product(
            [f"{number:02}" for number in range(1, 31)],
            "ABC",
            ("pine", "python", "typescript"),
            range(5),
        )
    )
    if (
        len(quality_rows) != 1350
        or identities != expected_rows
        or any(row.get("observation") != "complete" for row in quality_rows)
    ):
        raise ValueError("품질 보고서의 완료된 1350개 분모가 다릅니다")
    for cell in candidates:
        arm, language = cell["combination"].split("/")
        by_case = {}
        for row in quality_rows:
            if row["arm"] == arm and row["language"] == language:
                score = row.get("quality90")
                if type(score) not in (int, float) or not 0 <= score <= 90:
                    raise ValueError("품질 보고서의 quality90 관측치가 다릅니다")
                by_case.setdefault(row["case_id"], []).append(score)
        mean = sum(sum(scores) / len(scores) for scores in by_case.values()) / len(by_case)
        if cell["quality90"] != mean:
            raise ValueError("품질 보고서의 사전 선정 정책 전략 평균이 다릅니다")
    if len(artifacts) != 30 or {x["case_id"] for x in artifacts} != {
        f"{index:02}" for index in range(1, 31)
    }:
        raise ValueError("최종 경제 분모는 01~30을 한 번씩 포함해야 합니다")
    passes = value["semantic_pass_repetitions"]
    selected_hashes = value["selected_source_hashes"]
    if set(passes) != {x["case_id"] for x in artifacts} or set(selected_hashes) != set(passes):
        raise ValueError("30개 case의 semantic pass 목록이 필요합니다")
    for artifact in artifacts:
        reported = [
            row
            for row in quality_rows
            if row["case_id"] == artifact["case_id"]
            and row["arm"] == value.get("arm")
            and row["language"] == value.get("language")
        ]
        reported_passes = sorted(
            row["repetition"] for row in reported if row["semantic_status"] == "passed"
        )
        repetitions = passes[artifact["case_id"]]
        if not isinstance(repetitions, list) or any(
            type(x) is not int or x < 0 for x in repetitions
        ):
            raise ValueError("semantic 반복 번호가 유효하지 않습니다")
        expected = min(repetitions) if repetitions else None
        selected = next((row for row in reported if row["repetition"] == expected), None)
        expected_hash = selected.get("source_hash") if selected else None
        if repetitions != reported_passes or artifact["source_hash"] != expected_hash:
            raise ValueError("품질 보고서의 첫 semantic pass·source hash와 다릅니다")
        if selected is not None and (
            selected["public_status"] != "public_pass"
            or report["input_files"].get(
                f"trials/{artifact['arm']}/{artifact['language']}/{artifact['case_id']}/{expected}/source.txt"
            )
            != expected_hash
        ):
            raise ValueError("선정 source hash가 품질 보고서의 실행 원문과 다릅니다")
        if (
            artifact["arm"] != value.get("arm")
            or artifact["language"] != value.get("language")
            or artifact["repetition"] != expected
            or artifact["source_hash"] != selected_hashes.get(artifact["case_id"])
        ):
            raise ValueError("선정한 품질 1위 방식·언어·첫 semantic pass와 다릅니다")
    return {
        **value,
        "selection_file_sha256": digest(path),
        "selection_file": str(path.resolve()),
        "quality_evidence_path": str(source),
    }


def runtime_binding(path: Path) -> dict:
    """기존 동결 환경의 실제 실행 파일을 대조한다. 이미지 ID는 실행 transport에서도 재확인한다."""
    value = json.loads(path.read_text())
    environment = value.get("environment", value)
    selected = {}
    for directory in (
        "apps/api/src/strategy/code_runtime",
        "apps/api/src/strategy/pine_v2",
        "apps/api/src/strategy/python_runtime",
        "apps/api/src/backtest/engine",
    ):
        for file in sorted((ROOT / directory).rglob("*.py")):
            key = str(file.relative_to(ROOT))
            if environment["source_hashes"].get(key) != digest(file):
                raise ValueError(f"동결 실행 파일이 다릅니다: {key}")
            selected[key] = digest(file)
    for name in IMAGES.values():
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", environment["image_ids"].get(name, "")):
            raise ValueError("세 언어의 동결 이미지 ID가 필요합니다")
    return {
        "source_hashes": selected,
        "image_ids": environment["image_ids"],
        "environment_file_sha256": digest(path),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "machine": platform.machine(),
        "uv_lock_sha256": digest(ROOT / "apps/api/uv.lock"),
        "research_hashes": {
            str(file.relative_to(ROOT)): digest(file)
            for file in (
                Path(__file__),
                ROOT / "tools/research/sol_economic_data.py",
                ROOT / "tools/research/data.py",
                ROOT / "tools/research/cli.py",
                ROOT / "tools/research/swing_exits.py",
            )
        },
    }


def cells(snapshot: dict) -> list[dict]:
    return [
        {
            "id": f"{family}/{symbol}/{timeframe}",
            "family": family,
            "symbol": symbol,
            "timeframe": timeframe,
            "start": window["start"],
            "end": window["end_exclusive"],
            "execution": execution,
        }
        for family, execution, window in (
            ("historical_parent", False, snapshot["historical_window"]),
            ("minute_execution", True, snapshot["execution_window"]),
        )
        for symbol in ASSETS
        for timeframe in TIMEFRAMES
    ]


def frame_hash(frame: pd.DataFrame | pd.Series | None) -> str | None:
    if frame is None:
        return None
    state = hashlib.sha256()
    rows = frame.to_frame() if isinstance(frame, pd.Series) else frame
    state.update(json.dumps([str(x) for x in rows.columns]).encode())
    for index, row in zip(rows.index, rows.itertuples(index=False, name=None), strict=True):
        state.update(
            json.dumps(
                [pd.Timestamp(index).isoformat(), *[str(x) for x in row]], separators=(",", ":")
            ).encode()
        )
        state.update(b"\n")
    return state.hexdigest()


def scenario_config(timeframe: str, scenario: dict) -> BacktestConfig:
    return BacktestConfig(
        init_cash=Decimal(RESEARCH_POLICY["init_cash"]),
        freq=TIMEFRAMES[timeframe][1],
        fees=float(Decimal(RESEARCH_POLICY["fees"]) * Decimal(scenario["fee_multiplier"])),
        maker_fee=float(
            Decimal(RESEARCH_POLICY["maker_fee"]) * Decimal(scenario["fee_multiplier"])
        ),
        slippage=float(
            Decimal(RESEARCH_POLICY["slippage"]) * Decimal(scenario["slippage_multiplier"])
        ),
        include_funding=True,
        fill_timing="next_bar_open",
        leverage=1,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100,
        sizing_source="form",
        sizing_basis="form_equity",
        leverage_basis=1,
    )


def native_transport(language: str, parent: pd.DataFrame, expected_image: str):
    transport = create_code_transport(language, parent)
    if transport.image_id != expected_image:
        transport.close()
        raise ValueError("실행 이미지가 동결 ID와 다릅니다")
    return transport


def run_job(
    artifact: dict,
    cell: dict,
    scenario: dict,
    *,
    data: tuple | None,
    data_error: str | None,
    snapshot_id: str,
    runtime: dict,
    warmup: int,
    cache: Path,
    input_hashes: dict | None = None,
    runner=run_code_backtest,
    transport_builder=native_transport,
) -> dict:
    supported_timeframes = CASE_TIMEFRAMES[artifact["case_id"]]
    timeframe_error = (
        None
        if cell["timeframe"] in supported_timeframes
        else CASE_TIMEFRAME_REASONS[artifact["case_id"]]
    )
    parent, funding, minute = data if data is not None else (None, None, None)
    config = scenario_config(cell["timeframe"], scenario)
    stressed = (
        funding.map(lambda x: Decimal(str(x)) * Decimal(scenario["funding_multiplier"]))
        if funding is not None
        else None
    )
    hashes = input_hashes or {
        "parent": frame_hash(parent),
        "funding_observed": frame_hash(funding),
        "execution": frame_hash(minute),
    }
    binding = {
        "schema_version": 1,
        "artifact": artifact,
        "cell": cell,
        "scenario": scenario,
        "snapshot_id": snapshot_id,
        "runtime": runtime,
        "inputs": {**hashes, "funding_stressed": frame_hash(stressed)},
        "params": {},
        "warmup_bars": warmup,
        "config": json_value(config),
        "data_error": data_error,
        "risk_policy": "swing_two_bar_v1",
        "selection_policy": POLICY,
        "case_timeframe_compatibility": {
            "supported_timeframes": list(supported_timeframes),
            "error": timeframe_error,
        },
    }
    key = hash_json(binding)
    path = cache / (key + ".json")
    record = {
        "job_hash": key,
        "binding": binding,
        "strategy_id": artifact["case_id"],
        "cell_id": cell["id"],
        "family": cell["family"],
        "scenario": scenario["id"],
        "status": "failed",
        "cache_hit": False,
        "funding_rate_and_timestamp": "observed_settlements_only",
        "venue_funding_price_basis": "mark_price",
        "funding_price_is_proxy": True,
        "observed_grid_prevalidated": data_error is None and funding is not None,
        "funding_price": "execution_1min_open_proxy"
        if cell["execution"]
        else "parent_open_proxy_at_observed_8h_settlement",
        "historical_schedule_independently_verified": False,
        "intrabar_path": "conservative_OHLC_two_scenarios_1min"
        if cell["execution"]
        else "conservative_OHLC_two_scenarios_parent",
        "holdout_status": RETROSPECTIVE,
        "promotable": False,
        "method_quality_score": None,
    }
    na_reasons = []
    if artifact["source_error"] == "no_semantic_pass":
        na_reasons.append("no_semantic_pass")
    if timeframe_error:
        na_reasons.append(f"case_timeframe_incompatible: {timeframe_error}")
    if not cell["execution"] and cell["timeframe"] == "1d":
        na_reasons.append(
            "historical_daily_requires_minute_execution: "
            "24개월 일봉에는 정확한 봉 내부 펀딩·포지션 배분을 위한 1분봉이 없습니다"
        )
    if na_reasons:
        return {
            **record,
            "status": "not_applicable",
            "error": "; ".join(na_reasons),
            "not_applicable_reasons": na_reasons,
        }
    if path.exists():
        cached = json.loads(path.read_text())
        identity = cached.pop("record_sha256")
        if (
            hash_json(cached) != identity
            or cached["binding"] != binding
            or cached["status"] != "ok"
        ):
            raise ValueError("경제 캐시의 입력·결과 해시가 다릅니다")
        return {**cached, "record_sha256": identity, "cache_hit": True}
    if artifact["source_error"] or data_error:
        return {**record, "error": artifact["source_error"] or data_error}
    started = time.monotonic()
    try:
        if parent is None or funding is None:
            raise ValueError("경제 입력이 없습니다")
        if not cell["execution"] and any(
            timestamp not in parent.index for timestamp in funding.index
        ):
            raise ValueError("관측 펀딩 시각을 부모 봉 시가에서 평가할 수 없습니다")
        trace: list[dict] = []
        result = runner(
            artifact["source_code"],
            artifact["language"],
            parent,
            config,
            funding_rates=stressed,
            params={},
            warmup_bars=warmup,
            execution_ohlcv=minute,
            trace=trace,
            transport_factory=lambda: transport_builder(
                artifact["language"], parent, runtime["image_ids"][IMAGES[artifact["language"]]]
            ),
        )
        metrics = json_value(result.metrics)
        # 임의 사용자 출력은 경제 결과가 아니다. 이 값들은 공통 trusted broker 반환값뿐이다.
        completed = sum(trade.status == "closed" for trade in result.trades)
        json.dumps(metrics, allow_nan=False)
        economic_verdict(metrics, completed)
        signal = signal_trace_digest(
            [
                row
                for row in trace
                if row.get("type") == "intent" and row.get("disposition") != "warmup"
            ]
        )
        record.update(
            status="ok",
            metrics=metrics,
            closed_trades=completed,
            signal_sha256=signal,
            result_sha256=hash_json(
                {
                    "metrics": metrics,
                    "trades": json_value(result.trades),
                    "equity": frame_hash(result.equity_curve),
                }
            ),
            trace_sha256=hash_json(trace),
            runtime_seconds=time.monotonic() - started,
        )
        cache.mkdir(parents=True, exist_ok=True)
        record["record_sha256"] = hash_json(record)
        json_write(path, record)
        return record
    except Exception as exc:
        return {
            **record,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "runtime_seconds": time.monotonic() - started,
        }


def report(records: list[dict]) -> dict:
    families = {}
    for family in ("historical_parent", "minute_execution"):
        rows = [row for row in records if row["family"] == family]
        successes = [row for row in rows if row["status"] == "ok"]
        families[family] = {
            "planned_units": len(rows),
            "completed": len(successes),
            "failed": sum(x["status"] == "failed" for x in rows),
            "not_applicable": sum(x["status"] == "not_applicable" for x in rows),
            "strategy_coverage": {
                case: {
                    status: sum(
                        row["strategy_id"] == case and row["status"] == status for row in rows
                    )
                    for status in ("ok", "failed", "not_applicable")
                }
                for case in sorted({x["strategy_id"] for x in rows})
            },
            "strategies": summarize_strategy_results(successes),
        }
    return {
        "families": families,
        "holdout_status": RETROSPECTIVE,
        "promotable": False,
        "method_quality_score": None,
        "usd_cost": None,
        "usd_cost_status": "CLI subscription USD cost is unknown; not estimated",
    }


def execute(
    artifacts: list[dict],
    snapshot_path: Path,
    runtime: dict,
    destination: Path,
    selection: dict,
    *,
    loader=load_economic_cell,
    runner=run_code_backtest,
    transport_builder=native_transport,
) -> dict:
    if validate_selection(Path(selection["selection_file"]), artifacts) != selection:
        raise ValueError("경제 실행 전에 선정 증거가 변경되었습니다")
    snapshot = load_snapshot(snapshot_path)
    plan = {
        "artifacts": artifacts,
        "snapshot_id": snapshot["snapshot_id"],
        "runtime": runtime,
        "selection": selection,
        "cells": cells(snapshot),
        "scenarios": stress_scenarios(),
        "warmup_bars": snapshot["warmup_bars"],
    }
    destination.mkdir(parents=True, exist_ok=True)
    plan_path = destination / "plan.json"
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError("경제 계획이 달라졌습니다. 별도 출력 디렉터리가 필요합니다")
    json_write(plan_path, plan)
    records = []
    for cell in plan["cells"]:
        data, data_error = None, None
        if cell["execution"] or cell["timeframe"] != "1d":
            try:
                data = loader(
                    snapshot_path,
                    cell["symbol"],
                    cell["timeframe"],
                    cell["start"],
                    cell["end"],
                    execution=cell["execution"],
                    warmup_bars=plan["warmup_bars"],
                )
                if not cell["execution"]:
                    funding_items = [
                        x
                        for x in snapshot["files"]
                        if x["role"] == "funding" and x["symbol"] == cell["symbol"]
                    ]
                    if len(funding_items) != 1 or funding_items[0]["interval_minutes"] != 480:
                        raise ValueError("부모 봉 회고 검증은 관측된 8시간 펀딩 grid만 지원합니다")
            except Exception as exc:
                data_error = f"{type(exc).__name__}: {exc}"
        parent, funding, minute = data if data is not None else (None, None, None)
        input_hashes = {
            "parent": frame_hash(parent),
            "funding_observed": frame_hash(funding),
            "execution": frame_hash(minute),
        }
        for artifact in artifacts:
            for scenario in plan["scenarios"]:
                try:
                    row = run_job(
                        artifact,
                        cell,
                        scenario,
                        data=data,
                        data_error=data_error,
                        snapshot_id=snapshot["snapshot_id"],
                        runtime=runtime,
                        warmup=plan["warmup_bars"],
                        cache=destination / "cache",
                        input_hashes=input_hashes,
                        runner=runner,
                        transport_builder=transport_builder,
                    )
                except Exception as exc:
                    # 손상 cache도 분모에서 삭제하지 않는다. 파일은 보존하고 실패로 보고한다.
                    row = {
                        "job_hash": hash_json([artifact, cell, scenario]),
                        "strategy_id": artifact["case_id"],
                        "cell_id": cell["id"],
                        "family": cell["family"],
                        "scenario": scenario["id"],
                        "status": "failed",
                        "error": f"cache_or_input_integrity: {exc}",
                    }
                records.append(row)
                append_journal(destination / "journal.jsonl", row)
    result = {"plan_sha256": hash_json(plan), **report(records)}
    json_write(destination / "results.json", records)
    json_write(destination / "report.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("artifacts", "snapshot", "environment"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--quality-selection", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    artifacts = read_artifacts(args.artifacts.resolve())
    snapshot = load_snapshot(args.snapshot.resolve())
    runtime = runtime_binding(args.environment.resolve())
    if args.plan_only:
        print(
            json.dumps(
                {
                    "artifacts": len(artifacts),
                    "planned_units": len(artifacts) * 48,
                    "snapshot_id": snapshot["snapshot_id"],
                    "native_execution": False,
                    "source_errors": {
                        row["case_id"]: row["source_error"]
                        for row in artifacts
                        if row["source_error"]
                    },
                    "declared_images_not_probed": True,
                    "quality_selection_required_before_execution": True,
                }
            )
        )
        return
    if args.quality_selection is None:
        parser.error("native 경제 실행 전 --quality-selection이 필수입니다")
    selection = validate_selection(args.quality_selection.resolve(), artifacts)
    destination = output_dir(args.output)
    with exclusive(destination):
        print(
            json.dumps(
                execute(artifacts, args.snapshot.resolve(), runtime, destination, selection),
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
