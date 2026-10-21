"""선정된 원문의 제품 cold replay 30초 gate. 연구 900초 결과를 운영 통과로 바꾸지 않는다."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from tools.research.cli import output_dir  # noqa: E402
from tools.research.data import digest, json_write  # noqa: E402
from tools.research.sol_economic_data import load_economic_cell, load_snapshot  # noqa: E402
from tools.research.sol_economics import (  # noqa: E402
    IMAGES,
    read_artifacts,
    runtime_binding,
    validate_selection,
)

from src.strategy.code_contract import CodeSnapshot  # noqa: E402
from src.strategy.code_live_replay import input_hash, replay_code_intents  # noqa: E402
from src.strategy.code_runtime.pine import PineSignalTransport  # noqa: E402
from src.strategy.code_runtime.sandbox import create_transport  # noqa: E402
from src.strategy.python_runtime.sandbox import _DOCKER  # noqa: E402
from src.strategy.python_runtime.serialization import (  # noqa: E402
    bars_payload,
    frame_from_payload,
)
from src.strategy.python_runtime.serialization import (  # noqa: E402
    digest as json_digest,
)
from src.trading.code_checkpoints import LiveCodeBar  # noqa: E402
from src.trading.services.code_evaluation_service import (  # noqa: E402
    FLAT,
    canonical_bar,
    checked_position,
)

BUDGET_SECONDS = 30
RECORD_FIELDS = {
    "sequence",
    "execution_hash",
    "input_hash",
    "bar",
    "position",
    "is_warmup",
    "delivery_args",
    "intent",
    "status",
}


def records_from_payload(code: CodeSnapshot, payload: list[dict]) -> list[LiveCodeBar]:
    """계정·세션 ID 없는 export를 검증한다. 실제 관찰 여부는 export 주체의 별도 근거다."""
    if not code.warmup_bars < len(payload) <= 50000:
        raise ValueError("전체 warmup과 평가 봉 1개 이상, 최대 50000봉이 필요합니다")
    records = []
    for index, value in enumerate(payload):
        if set(value) != RECORD_FIELDS or type(value["is_warmup"]) is not bool:
            raise ValueError("sanitized checkpoint의 정확한 필드가 필요합니다")
        bar = canonical_bar(value["bar"], index)
        position = checked_position(value["position"])
        if (
            type(value["sequence"]) is not int
            or type(value["bar"].get("index")) is not int
            or value["sequence"] != index
            or value["bar"] != bar
            or value["execution_hash"] != code.execution_hash
            or value["position"] != position
            or value["is_warmup"] != (index < code.warmup_bars)
            or (value["is_warmup"] and position != FLAT)
            or value["intent"] not in {"hold", "long", "short", "close"}
            or (
                value["status"] != "warmup"
                if value["is_warmup"]
                else value["status"] not in {"prepared", "delivered"}
            )
            or (value["status"] == "prepared" and index != len(payload) - 1)
            or value["input_hash"]
            != input_hash(
                code.execution_hash,
                bar,
                position,
                is_warmup=value["is_warmup"],
                delivery_args=value["delivery_args"],
            )
        ):
            raise ValueError("체크포인트 원문·관찰 포지션·순서·입력 hash가 다릅니다")
        at = datetime.fromisoformat(bar["timestamp"])
        if at.timestamp() % 3600 or (
            records and (at - records[-1].bar_time).total_seconds() != 3600
        ):
            raise ValueError("현재 제품과 같은 UTC 1h 완료 봉 연속 입력이 필요합니다")
        records.append(
            LiveCodeBar(
                session_id=UUID(int=0),
                bar_time=at,
                **value,
            )
        )
    return records


def load_inputs(
    *,
    artifacts_path: Path,
    selection_path: Path,
    case_id: str,
    code_path: Path,
    execution_hash: str,
    environment_path: Path,
    snapshot_path: Path,
    symbol: str,
    start: str,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str | None = None,
) -> tuple[CodeSnapshot, dict, dict]:
    """기존 full 선정 검증을 재사용한다. 다른 반복·원문으로 운영 gate를 대체하지 않는다."""
    artifacts = read_artifacts(artifacts_path)
    selection = validate_selection(selection_path, artifacts)
    artifact = next(row for row in artifacts if row["case_id"] == case_id)
    code = CodeSnapshot.model_validate_json(code_path.read_text())
    if code.params or code.warmup_bars != 200:
        raise ValueError("동결 full 품질 계약의 params={}·warmup_bars=200이 필요합니다")
    if (
        artifact["source_error"] is not None
        or code.source_code != artifact["source_code"]
        or code.source_hash != artifact["source_hash"]
        or code.language.value != artifact["language"]
        or code.execution_hash != execution_hash
    ):
        raise ValueError("선정 첫 semantic pass 원문과 불변 제품 snapshot이 다릅니다")
    if digest(environment_path) != selection["manifest_sha256"]:
        raise ValueError("운영 gate 환경은 품질 선정 full manifest 원문과 같아야 합니다")
    runtime = runtime_binding(environment_path)
    snapshot = load_snapshot(snapshot_path)
    end = pd.Timestamp(start) + pd.Timedelta(hours=1)
    bars, _, _ = load_economic_cell(
        snapshot_path, symbol, "1h", start, end, warmup_bars=code.warmup_bars
    )
    payload = []
    for index, raw in enumerate(bars_payload(bars)):
        bar = canonical_bar(raw, index)
        warmup = index < code.warmup_bars
        payload.append(
            {
                "sequence": index,
                "execution_hash": code.execution_hash,
                "input_hash": input_hash(code.execution_hash, bar, FLAT, is_warmup=warmup),
                "bar": bar,
                "position": dict(FLAT),
                "is_warmup": warmup,
                "delivery_args": {},
                "intent": "hold",
                "status": "warmup" if warmup else "prepared",
            }
        )
    # 최초 입력은 아직 관찰한 intent가 없다. 생성된 의도를 hold라고 인증하지 않는다.
    startup = records_from_payload(code, payload)
    for row in startup:
        row.intent = ""
    profiles = {"first_activation_flat": startup, "observed_checkpoint": None}
    if checkpoint_path is not None:
        if checkpoint_sha256 is None or digest(checkpoint_path) != checkpoint_sha256:
            raise ValueError("checkpoint export의 고정 파일 SHA256이 필요합니다")
        value = json.loads(checkpoint_path.read_text())
        if (
            set(value)
            != {
                "schema_version",
                "origin",
                "source_hash",
                "execution_hash",
                "snapshot_id",
                "records",
            }
            or value["schema_version"] != 1
            or value["origin"] != "persisted_live_code_bars"
            or value["source_hash"] != code.source_hash
            or value["execution_hash"] != code.execution_hash
            or value["snapshot_id"] != snapshot["snapshot_id"]
        ):
            raise ValueError("checkpoint source·version·시세 snapshot 연결이 다릅니다")
        profiles["observed_checkpoint"] = records_from_payload(code, value["records"])
    elif checkpoint_sha256 is not None:
        raise ValueError("checkpoint 경로 없이 hash만 제공할 수 없습니다")
    proof = {
        "case_id": case_id,
        "arm": artifact["arm"],
        "language": code.language.value,
        "first_pass_repetition": artifact["repetition"],
        "source_hash": code.source_hash,
        "execution_hash": code.execution_hash,
        "code_snapshot_file_sha256": digest(code_path),
        "artifact_list_sha256": digest(artifacts_path),
        "selection": selection,
        "runtime": runtime,
        "expected_image_id": runtime["image_ids"][IMAGES[code.language.value]],
        "snapshot_file_sha256": digest(snapshot_path),
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_holdout_status": snapshot.get("holdout_status"),
        "symbol": symbol,
        "timeframe": "1h",
        "checkpoint_file_sha256": checkpoint_sha256,
        "checkpoint_origin_attestation": "operator_export_not_independently_venue_verified",
        "product_replay_sources": {
            str(path.relative_to(ROOT)): digest(path)
            for path in (
                ROOT / "apps/api/src/strategy/code_live_replay.py",
                ROOT / "apps/api/src/strategy/code_contract.py",
                ROOT / "apps/api/src/trading/services/code_evaluation_service.py",
                Path(__file__),
            )
        },
    }
    return code, profiles, proof


def _removed(name: str) -> bool:
    result = subprocess.run(  # noqa: S603 — 자체 transport 이름만 고정 argv로 검사
        [_DOCKER, "container", "inspect", name],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    return result.returncode == 1 and (
        "No such object" in result.stderr or "No such container" in result.stderr
    )


def measure_profile(
    code: CodeSnapshot,
    records: list[LiveCodeBar] | None,
    *,
    expected_image_id: str,
    transport_factory=None,
    removed_probe=_removed,
    clock=time.monotonic,
) -> dict:
    """제품 함수를 그대로 호출한다. 시간은 검증부터 cleanup 확인까지의 전체 wall time이다."""
    if records is None:
        return {
            "status": "UNKNOWN",
            "reason": "observed_checkpoint_not_supplied",
            "native_executed": False,
        }
    timings = {
        "construct_seconds": 0.0,
        "init_seconds": 0.0,
        "bars_seconds": 0.0,
        "cleanup_seconds": 0.0,
    }
    observations = {
        "container_name": None,
        "image_id": None,
        "cleanup_confirmed": False,
        "cleanup_attempted": False,
    }
    bar_times = []
    phase = "validation"
    injected_transport = transport_factory is not None
    transport_attempted = False
    if transport_factory is None:

        def transport_factory():
            if code.language.value == "pine":
                return PineSignalTransport(
                    frame_from_payload([row.bar for row in records]), timeout=BUDGET_SECONDS
                )
            return create_transport(code.language, timeout=BUDGET_SECONDS)

    class Timed:
        def __init__(self):
            nonlocal phase, transport_attempted
            phase = "construct"
            transport_attempted = True
            begin = clock()
            self.inner = None
            try:
                self.inner = transport_factory()
                observations.update(container_name=self.inner.name, image_id=self.inner.image_id)
                if self.inner.image_id != expected_image_id:
                    raise ValueError("실제 실행 이미지가 동결 image ID와 다릅니다")
            except BaseException:
                timings["construct_seconds"] = clock() - begin
                if self.inner is not None:
                    self.close()
                raise
            else:
                timings["construct_seconds"] = clock() - begin

        def exchange(self, message):
            nonlocal phase
            phase = "init" if message["type"] == "init" else "bar"
            begin = clock()
            try:
                reply = self.inner.exchange(message)
                if phase == "bar":
                    bar_times.append(clock() - begin)
                return reply
            finally:
                timings["init_seconds" if phase == "init" else "bars_seconds"] += clock() - begin

        def close(self):
            observations["cleanup_attempted"] = True
            begin = clock()
            try:
                self.inner.close()
                observations["cleanup_confirmed"] = removed_probe(self.inner.name)
            except Exception as exc:
                observations["cleanup_error_type"] = type(exc).__name__
            finally:
                timings["cleanup_seconds"] += clock() - begin

    begin = clock()
    error = None
    status = "PASS"
    actions = []
    try:
        actions = replay_code_intents(code, records, transport_factory=Timed)
    except KeyboardInterrupt:
        status, error = "INTERRUPTED", "KeyboardInterrupt"
    except Exception as exc:
        status, error = "FAIL", type(exc).__name__
    elapsed = clock() - begin
    if status == "PASS" and (elapsed > BUDGET_SECONDS or not observations["cleanup_confirmed"]):
        status = "FAIL"
        error = "total_wall_budget_exceeded" if elapsed > BUDGET_SECONDS else "cleanup_unconfirmed"
    return {
        "status": status,
        "native_executed": (True if observations["image_id"] is not None else None)
        if transport_attempted and not injected_transport
        else False,
        "transport_attempted": transport_attempted,
        "execution_backend": "injected_test_transport" if injected_transport else "native_gvisor",
        "error_type": error,
        "last_observed_phase": "close" if observations["cleanup_attempted"] else phase,
        "failure_phase": (
            "total_gate"
            if error == "total_wall_budget_exceeded"
            else "close"
            if error == "cleanup_unconfirmed"
            else phase
        )
        if status != "PASS"
        else None,
        "product_budget_seconds": BUDGET_SECONDS,
        "research_budget_seconds": 900,
        "elapsed_seconds": elapsed,
        **timings,
        **observations,
        "input_bars": len(records),
        "completed_bar_replies": len(bar_times),
        "bar_seconds_max": max(bar_times, default=None),
        "bar_seconds_p95": sorted(bar_times)[math.ceil(len(bar_times) * 0.95) - 1]
        if bar_times
        else None,
        "record_digest": json_digest(
            [{key: getattr(row, key) for key in sorted(RECORD_FIELDS)} for row in records]
        ),
        "first_bar": records[0].bar["timestamp"],
        "last_bar": records[-1].bar["timestamp"],
        "actions_digest": json_digest(actions),
        "timing_scope": "product_replay_validation_construct_init_bars_close_and_cleanup_probe",
        "unexposed_phases": ["parser", "typescript_compiler"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("artifacts", "selection", "code_snapshot", "environment", "snapshot"):
        parser.add_argument("--" + field.replace("_", "-"), type=Path, required=True)
    for field in ("case_id", "execution_hash", "symbol", "start"):
        parser.add_argument("--" + field.replace("_", "-"), required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--checkpoint-sha256")
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    code, profiles, proof = load_inputs(
        artifacts_path=args.artifacts,
        selection_path=args.selection,
        case_id=args.case_id,
        code_path=args.code_snapshot,
        execution_hash=args.execution_hash,
        environment_path=args.environment,
        snapshot_path=args.snapshot,
        symbol=args.symbol,
        start=args.start,
        checkpoint_path=args.checkpoint,
        checkpoint_sha256=args.checkpoint_sha256,
    )
    results = {}
    interrupted = False
    for name, rows in profiles.items():
        if interrupted:
            results[name] = {
                "status": "NOT_RUN",
                "reason": "prior_profile_interrupted",
                "native_executed": False,
            }
            continue
        results[name] = (
            measure_profile(code, rows, expected_image_id=proof["expected_image_id"])
            if args.execute
            else {
                "status": "NOT_RUN" if rows else "UNKNOWN",
                "native_executed": False,
                "input_bars": len(rows) if rows else None,
            }
        )
        interrupted = results[name]["status"] == "INTERRUPTED"
    json_write(
        output_dir(args.output) / "operational-gate.json",
        {
            "schema_version": 1,
            "purpose": "product_cold_replay_gate_not_quality_or_profit_score",
            "proof": proof,
            "profiles": results,
            "overall_status": (
                "NOT_RUN"
                if not args.execute
                else next(
                    (
                        status
                        for status in ("FAIL", "INTERRUPTED", "UNKNOWN")
                        if any(row["status"] == status for row in results.values())
                    ),
                    "PASS",
                )
            ),
            "cold_definition": "fresh_container_no_host_mounts_preserved_local_image_not_cold_OS_or_image_pull",
        },
    )


if __name__ == "__main__":
    main()
