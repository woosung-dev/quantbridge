"""실제 native 원본·초기이력 증거와 각 격리 코드 경로를 독립 대조한다."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from tools.research.period_study.controller import artifact, implementation  # noqa: E402
from tools.research.period_study.generation import reviewed_source  # noqa: E402
from tools.research.period_study.state import (  # noqa: E402
    checked,
    identity,
    lock,
    now,
    read,
    sha,
    write,
)
from tools.research.review_tradingview import code_mask  # noqa: E402

from scripts.pine_validation.native_capture import NativeCapture, parse_native_capture  # noqa: E402

SYMBOL = "BYBIT:BTCUSDT.P"
STEPS = {"1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1)}
PROBE_TITLE = "__QB_BAR_INDEX__"


def proof(root: Path, path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("native_evidence_path_missing_or_outside_run")
    return {"path": str(resolved.relative_to(root.resolve())), "sha256": sha(resolved.read_bytes())}


def parse(payload: dict, source: bytes, review: dict, pid: str, timeframe: str) -> NativeCapture:
    return parse_native_capture(
        payload,
        source=source,
        signal_bindings=review["signal_bindings"],
        expected_indicator_id=pid,
        expected_symbol=SYMBOL,
        expected_timeframe=timeframe,
        expected_inputs=review.get("inputs", {}),
    )


def event_keys(events) -> list[list[str]]:
    return [[event.bar_time.isoformat(), event.direction] for event in events]


def verify_initial_history(
    native: NativeCapture,
    original: bytes,
    probe_payload: dict,
    review: dict,
    pid: str,
    timeframe: str,
) -> dict:
    """원문 뒤의 단일 bar_index 관측만 허용하며 원본·진단본 사건과 OHLCV를 대조한다."""
    probe_source = probe_payload.get("compiled_source")
    if not isinstance(probe_source, str):
        raise ValueError("initial_history_probe_source_missing")
    source = original.decode("utf-8-sig").replace("\r\n", "\n")
    normalized = probe_source.replace("\r\n", "\n")
    suffix = normalized[len(source) :] if normalized.startswith(source) else ""
    if not re.fullmatch(
        r"""\s*plot\(\s*bar_index\s*,\s*(?:title\s*=\s*)?["']__QB_BAR_INDEX__["']"""
        r"\s*,\s*display\s*=\s*display\.none\s*\)\s*",
        suffix,
    ):
        raise ValueError("initial_history_probe_must_only_append_bar_index_plot")
    probe = parse(probe_payload, probe_source.encode(), review, pid, timeframe)
    step = STEPS[timeframe]
    if native.ohlcv.index[0] != probe.ohlcv.index[0]:
        raise ValueError("initial_history_first_bar_differs")
    for capture in (native, probe):
        if not (
            capture.metadata["common_bars"]
            == capture.metadata["study_bars"]
            == capture.metadata["ohlcv_bars"]
        ):
            raise ValueError("initial_history_partial_cohort")
    common = native.ohlcv.index.intersection(probe.ohlcv.index)
    if not common.equals(native.ohlcv.index) or not native.ohlcv.equals(probe.ohlcv.loc[common]):
        raise ValueError("initial_history_probe_ohlcv_differs")
    start, end = common[0], common[-1] + step
    if event_keys(native.window_events(start, end)) != event_keys(probe.window_events(start, end)):
        raise ValueError("initial_history_probe_changes_original_events")
    meta = probe_payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    columns = [key for key, style in meta["styles"].items() if style.get("title") == PROBE_TITLE]
    if len(columns) != 1 or columns[0] not in probe.observations:
        raise ValueError("initial_history_probe_column_missing_or_ambiguous")
    values = probe.observations[columns[0]].tolist()
    if values != list(range(len(probe.ohlcv))):
        raise ValueError("initial_history_bar_index_does_not_start_at_zero_and_advance_once")
    return {
        "status": "verified",
        "kind": "separate_append_only_bar_index_probe",
        "first_bar": start.isoformat(),
        "bars": len(native.ohlcv),
        "probe_source_sha256": sha(probe_source.encode()),
        "probe_is_unmodified_original": False,
        "original_events_exact": True,
        "ohlcv_exact": True,
        "first_bar_index": 0,
    }


def image_identity(path: str) -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("docker_missing")
    response = subprocess.run(  # noqa: S603 — 고정 docker argv이며 전략 원문을 실행하지 않는다.
        [docker, "image", "inspect", "--format", "{{.Id}}", f"quantbridge-{path}-runner:local"],
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    result = response.stdout.strip()
    if not result.startswith("sha256:"):
        raise RuntimeError("isolated_image_identity_missing")
    return result


def collect(source: str, path: str, frame: pd.DataFrame, params: dict, phase: str) -> list[str]:
    """소스 실행은 네트워크 없는 gVisor CodeExecutionSession만 사용한다."""
    from src.strategy.code_runtime.session import CodeExecutionSession

    actions = []
    position = {"direction": "flat", "size": "0", "average_price": None}
    started = time.monotonic()
    with CodeExecutionSession(source, path, params, frame) as session:
        for index, (timestamp, row) in enumerate(frame.iterrows()):
            bar = {
                "index": index,
                "timestamp": timestamp.isoformat(),
                **{key: str(row[key]) for key in ("open", "high", "low", "close", "volume")},
            }
            actions.append(session.action(bar, position))
            if (index + 1) % 500 == 0:
                print(
                    json.dumps(
                        {
                            "path": path,
                            "phase": phase,
                            "bars": index + 1,
                            "elapsed_seconds": time.monotonic() - started,
                        }
                    ),
                    flush=True,
                )
    return actions


def action_events(actions: list[str], frame: pd.DataFrame, warmup: int) -> list[list[str]]:
    return [
        [frame.index[index].isoformat(), action]
        for index, action in enumerate(actions)
        if index >= warmup and action != "hold"
    ]


def compare_path(
    root: Path,
    item: dict,
    path: str,
    native: NativeCapture,
    native_events: list[list[str]],
    warmup: int,
) -> dict:
    if path == "pine":
        original, _, _ = reviewed_source(root, item)
        references = sorted(
            {
                re.sub(r"\s+", "", value)
                for value in re.findall(
                    r"\bsyminfo\s*\.\s*(?:mintick|tickerid|ticker|prefix)\b", code_mask(original)
                )
            }
        )
        if references:
            return {
                "status": "not_run",
                "reason": "unsupported_market_context",
                "references": references,
            }
    source, source_hash, review = artifact(root, root, item, path)
    before = image_identity(path)
    frame = native.ohlcv
    prefix_size = max(warmup + 1, len(frame) // 2)
    if prefix_size >= len(frame):
        raise ValueError("insufficient_history_for_nontrivial_prefix")
    completed: dict[str, list[str]] = {}
    for phase in ("full", "repeat", "prefix"):
        try:
            completed[phase] = collect(
                source,
                path,
                frame.iloc[:prefix_size] if phase == "prefix" else frame,
                review.get("inputs", {}),
                phase,
            )
        except Exception as error:
            return {
                "status": "failed",
                "execution_attempted": True,
                "source_hash": source_hash,
                "image_id": before,
                "failed_phase": phase,
                "completed_passes": list(completed),
                "reason": f"{type(error).__name__}:{error}",
            }
    full, repeat, prefix = (completed[phase] for phase in ("full", "repeat", "prefix"))
    after = image_identity(path)
    if after != before:
        return {
            "status": "failed",
            "execution_attempted": True,
            "source_hash": source_hash,
            "image_id": before,
            "final_image_id": after,
            "reason": "runner_image_changed_during_validation",
        }
    actual = action_events(full, frame, warmup)
    exact, repeated, causal = actual == native_events, full == repeat, prefix == full[:prefix_size]
    both_directions = {event[1] for event in native_events} >= {"long", "short"}
    return {
        "status": "passed" if exact and repeated and causal and both_directions else "mismatch",
        "source_hash": source_hash,
        "execution_attempted": True,
        "image_id": before,
        "signal_hash": identity(actual),
        "native_exact": exact,
        "repeat": repeated,
        "prefix": causal,
        "prefix_bars": prefix_size,
        "native_events": len(native_events),
        "code_events": len(actual),
        "both_directions": both_directions,
        "events": actual,
        "difference_examples": []
        if exact
        else {
            "native_only": [event for event in native_events if event not in actual][:10],
            "code_only": [event for event in actual if event not in native_events][:10],
        },
    }


def verify(root: Path, pid: str, timeframe: str, probe_path: Path | None) -> dict:
    catalogue = read(root / "catalogue.json")
    item = next(value for value in catalogue["items"] if value["id"] == pid)
    capture_path = root / "native" / pid / f"{timeframe}.json"
    probe_path = probe_path or root / "native" / pid / f"{timeframe}-initialization.json"
    code_hashes = implementation()
    code_hashes["tools/research/period_native.py"] = sha(Path(__file__).read_bytes())
    code_hashes["apps/api/scripts/pine_validation/native_capture.py"] = sha(
        (ROOT / "apps/api/scripts/pine_validation/native_capture.py").read_bytes()
    )
    result: dict[str, Any] = {
        "publication_id": pid,
        "timeframe": timeframe,
        "status": "unverified",
        "evidence_verified": False,
        "evidence": [],
        "observed_at": now(),
        "paths": {path: {"status": "not_run"} for path in ("pine", "python")},
        "implementation_hashes": code_hashes,
        "reference_kind": "native_original_partial_window",
        "limitations": [
            "관측한 부분창만 대조하며 과거 P1~P5 전체 native 검증이 아닙니다",
            "TradingView Strategy Tester의 수익률·체결 재현 판정이 아닙니다",
        ],
    }
    try:
        _, source_hash, review = reviewed_source(root, item)
        source_bytes = checked(root, item["source_file"], source_hash).read_bytes()
        result.update(source_sha256=source_hash, signal_mode=review.get("signal_mode"))
        result["evidence"].append(proof(root, capture_path))
        payload = read(capture_path)
        native = parse(payload, source_bytes, review, pid, timeframe)
        result.update(raw_capture_verified=True, native_metadata=native.metadata)
        result["parser"] = {
            "source_sha256": code_hashes["apps/api/scripts/pine_validation/native_capture.py"],
            "pynescript_version": version("pynescript"),
        }
        result["compiler"] = {
            "response_sha256": identity(payload["compile_responses"]),
            "compiled_source_sha256": sha(payload["compiled_source"].encode()),
            "request_source_sha256": sha(payload["compile_request_source"].encode()),
        }
        result["evidence"].append(proof(root, probe_path))
        history = verify_initial_history(
            native, source_bytes, read(probe_path), review, pid, timeframe
        )
        result["initial_history"] = history
        result["evidence_verified"] = True
        if review.get("signal_mode") != "shared_events":
            raise ValueError("native_policy_position_feedback_not_observed")
        warmup = review["warmup_bars"]
        if type(warmup) is not int or len(native.ohlcv) <= warmup + 1:
            raise ValueError("native_history_insufficient_for_reviewed_warmup_and_prefix")
        start, end = native.ohlcv.index[warmup], native.ohlcv.index[-1] + STEPS[timeframe]
        events = event_keys(native.window_events(start, end))
        result["window"] = {
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "warmup_bars": warmup,
            "evaluated_bars": len(native.ohlcv) - warmup,
        }
        result["native_signal_hash"] = identity(events)
        for path in ("pine", "python"):
            try:
                result["paths"][path] = compare_path(root, item, path, native, events, warmup)
            except Exception as error:
                result["paths"][path] = {
                    "status": "not_run",
                    "reason": f"{type(error).__name__}:{error}",
                }
        result["passed_paths"] = [
            path for path, value in result["paths"].items() if value["status"] == "passed"
        ]
        for descriptor in result["evidence"]:
            checked(root, descriptor["path"], descriptor["sha256"])
        result["status"] = "passed" if result["passed_paths"] else "not_passed"
    except Exception as error:
        result["reason"] = f"{type(error).__name__}:{error}"
        result["evidence_verified"] = False
        for value in result["paths"].values():
            if value["status"] == "passed":
                value.update(status="unverified", reason="native_evidence_chain_changed")
        result["passed_paths"] = []
    request = {
        "id": pid,
        "timeframe": timeframe,
        "evidence": result["evidence"],
        "source_sha256": result.get("source_sha256"),
        "implementation": code_hashes,
        "review_sha256": sha((root / item["review_file"]).read_bytes())
        if (root / item["review_file"]).exists()
        else None,
        "generation_status_sha256": sha((root / "generation" / pid / "status.json").read_bytes())
        if (root / "generation" / pid / "status.json").exists()
        else None,
    }
    result["request_hash"] = identity(request)
    attempts = root / "native-attempts" / pid / timeframe
    number = len(list(attempts.glob("*.json"))) + 1
    result["attempt"] = number
    write(attempts / f"{number:03}-{result['request_hash']}.json", result)
    write(root / "native-verification" / f"{pid}-{timeframe}.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--timeframe", choices=STEPS, required=True)
    parser.add_argument("--initialization-probe", type=Path)
    args = parser.parse_args()
    root = args.run.resolve()
    with lock(root / "native-locks" / f"{args.id}-{args.timeframe}.lock"):
        result = verify(root, args.id, args.timeframe, args.initialization_probe)
    print(
        json.dumps(
            {
                "id": args.id,
                "timeframe": args.timeframe,
                "status": result["status"],
                "reason": result.get("reason"),
                "paths": {key: value["status"] for key, value in result["paths"].items()},
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
