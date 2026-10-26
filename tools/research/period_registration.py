"""완료한 연구 정의의 등록 후보·정확한 API 요청만 만든다. 서버에 쓰지 않는다."""

from __future__ import annotations

import argparse
import ast
import copy
import difflib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from tools.research import period_native  # noqa: E402
from tools.research.period_study.controller import artifact, cell_key, implementation  # noqa: E402
from tools.research.period_study.encoding import restore  # noqa: E402
from tools.research.period_study.generation import reviewed_source  # noqa: E402
from tools.research.period_study.schema import COSTS, PERIODS, TIMEFRAMES  # noqa: E402
from tools.research.period_study.state import (  # noqa: E402
    checked,
    identity,
    immutable,
    now,
    read,
    sha,
    write,
)

from src.strategy.code_runtime.backtest import _hash as signal_hash  # noqa: E402
from src.strategy.code_schemas import CodeStrategyResponse, SaveCodeStrategyRequest  # noqa: E402
from src.strategy.research_contract import ResearchExecution  # noqa: E402

ENDPOINT = "/api/v1/strategies/code"


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def mapping_hash(review: dict) -> str:
    return identity(
        {
            "source_sha256": review["source_sha256"],
            "inputs": review.get("inputs", {}),
            "signal_bindings": review["signal_bindings"],
            "signal_mode": review["signal_mode"],
        }
    )


def frozen_implementation(root: Path, recorded: dict) -> dict:
    current = implementation()
    require(
        set(recorded) == set(current)
        or set(recorded)
        == set(current)
        | {
            "tools/research/period_native.py",
            "apps/api/scripts/pine_validation/native_capture.py",
        },
        "native_implementation_file_set_mismatch",
    )
    computation = {
        key: value
        for key, value in current.items()
        if key != "tools/research/period_study/controller.py"
    }
    require(
        bool(computation) and all(recorded.get(key) == value for key, value in computation.items()),
        "native_execution_implementation_mismatch",
    )
    archives, changes = [], []
    for relative, digest in recorded.items():
        file = ROOT / relative
        data = file.read_bytes()
        archive = root / "registration-candidates/harness" / f"{digest}-{Path(relative).name}"
        if sha(data) != digest:
            require(relative not in computation, "native_execution_implementation_mismatch")
            changes.append(relative)
            if archive.exists():
                data = checked(root, str(archive.relative_to(root)), digest).read_bytes()
        if sha(data) != digest:
            git = shutil.which("git")
            require(git is not None, "git_required_for_frozen_harness_source")
            revisions = subprocess.run(  # noqa: S603 — 허용한 코드 경로의 Git 이력을 읽기만 한다.
                [git, "log", "-30", "--format=%H", "--", relative],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            ).stdout.splitlines()
            for revision in revisions:
                historical = subprocess.run(  # noqa: S603 — Git이 반환한 revision의 허용 코드 경로만 읽는다.
                    [git, "show", f"{revision}:{relative}"],
                    cwd=ROOT,
                    capture_output=True,
                    check=True,
                    timeout=15,
                ).stdout
                if sha(historical) == digest:
                    data = historical
                    break
            require(sha(data) == digest, "frozen_harness_source_unavailable")
        if relative not in computation:
            archive.parent.mkdir(parents=True, exist_ok=True)
            if archive.exists():
                checked(root, str(archive.relative_to(root)), digest)
            else:
                archive.write_bytes(data)
            archives.append({"source_file": relative, **period_native.proof(root, archive)})
    receipt = {
        "frozen_harness": archives,
        "currently_changed": sorted(changes),
        "execution_epoch_not_relabelled_as_current_gate": True,
    }
    receipt_file = root / "registration-candidates/harness" / f"{identity(receipt)}.json"
    immutable(receipt_file, receipt)
    return {
        "_implementation": {key: recorded[key] for key in current},
        "execution_epoch": {
            "computation_sha256": identity(computation),
            "harness_receipt": period_native.proof(root, receipt_file),
            "harness_changed_since_execution": sorted(changes),
        },
    }


def harness_comparison(root: Path, financial: dict, native: dict, review: dict) -> dict:
    expected = native["_implementation"]
    changed = {
        key for key in set(financial) | set(expected) if financial.get(key) != expected.get(key)
    }
    if not changed:
        return {"same_execution_epoch": True, "implementation_sha256": identity(financial)}
    controller = "tools/research/period_study/controller.py"
    require(changed == {controller}, "financial_execution_implementation_mismatch")
    require(
        review.get("market_context_proof") is None,
        "cross_epoch_market_context_requires_separate_review",
    )
    epoch = frozen_implementation(root, financial)
    before = (
        root / "registration-candidates/harness" / f"{financial[controller]}-controller.py"
    ).read_bytes()
    after = (
        root / "registration-candidates/harness" / f"{expected[controller]}-controller.py"
    ).read_bytes()
    old_tree, new_tree = ast.parse(before), ast.parse(after)
    bodies = []
    for tree in (old_tree, new_tree):
        function = copy.deepcopy(
            next(
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "run_group"
            )
        )
        removed = 0
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "base"
                and node.func.attr == "update"
            ):
                removed += sum(keyword.arg == "market_context_proof" for keyword in node.keywords)
                node.keywords = [
                    keyword for keyword in node.keywords if keyword.arg != "market_context_proof"
                ]
        require(removed in (0, 1), "controller_metadata_field_ambiguous")
        bodies.append(ast.dump(function, include_attributes=False))
        tree.body = [
            node
            for node in tree.body
            if not isinstance(node, ast.FunctionDef) or node.name not in {"artifact", "run_group"}
        ]
    require(
        bodies[0] == bodies[1]
        and ast.dump(old_tree, include_attributes=False)
        == ast.dump(new_tree, include_attributes=False),
        "controller_calculation_changed_between_epochs",
    )
    diff = "".join(
        difflib.unified_diff(
            before.decode().splitlines(True),
            after.decode().splitlines(True),
            fromfile="financial-harness",
            tofile="native-harness",
        )
    )
    diff_file = root / "registration-candidates/harness" / f"{sha(before)}-{sha(after)}.diff"
    if diff_file.exists():
        require(diff_file.read_bytes() == diff.encode(), "frozen_harness_diff_changed")
    else:
        diff_file.write_bytes(diff.encode())
    receipt = {
        "financial_epoch": epoch["execution_epoch"],
        "native_epoch": native["execution_epoch"],
        "controller_diff": period_native.proof(root, diff_file),
        "run_group_calculation_ast_sha256": sha(bodies[0].encode()),
        "same_computation_after_removing_only_market_context_metadata": True,
        "executed_source_bytes_inputs_approval_exact": True,
        "source_market_context_added": False,
        "financial_reexecution_performed": False,
        "past_execution_of_new_gate_claimed": False,
    }
    receipt_file = root / "registration-candidates/harness" / f"comparison-{identity(receipt)}.json"
    immutable(receipt_file, receipt)
    return {"same_execution_epoch": False, "comparison": period_native.proof(root, receipt_file)}


def native_evidence(
    root: Path, item: dict, path: str, timeframe: str, source_hash: str, review: dict
) -> dict:
    pid = item["id"]
    file = root / "native-verification" / f"{pid}-{timeframe}.json"
    gate = read(file)
    selected = gate.get("paths", {}).get(path, {})
    require(
        gate.get("status") == "passed"
        and gate.get("evidence_verified") is True
        and selected.get("status") == "passed"
        and all(
            selected.get(key) is True
            for key in ("native_exact", "repeat", "prefix", "both_directions")
        ),
        "native_selected_code_path_not_passed",
    )
    require(
        gate.get("publication_id") == pid
        and gate.get("timeframe") == timeframe
        and gate.get("source_sha256") == review["source_sha256"]
        and gate.get("signal_mode") == review["signal_mode"] == "shared_events"
        and selected.get("source_hash") == source_hash
        and gate.get("window", {}).get("warmup_bars") == review["warmup_bars"],
        "native_source_mapping_mode_or_warmup_mismatch",
    )
    recorded = gate["implementation_hashes"]
    epoch = frozen_implementation(root, recorded)
    require(bool(gate.get("evidence")), "native_evidence_missing")
    for evidence in gate["evidence"]:
        checked(root, evidence["path"], evidence["sha256"])
    approval = review.get("generated_code_review_sha256")
    require(
        selected.get("generated_code_review_sha256") == approval,
        "native_generated_approval_mismatch",
    )
    request = {
        "id": pid,
        "timeframe": timeframe,
        "evidence": gate["evidence"],
        "source_sha256": gate["source_sha256"],
        "generated_code_reviews": {
            key: value["generated_code_review_sha256"]
            for key, value in gate["paths"].items()
            if value.get("generated_code_review_sha256")
        },
        "implementation": recorded,
        "review_sha256": sha((root / item["review_file"]).read_bytes()),
        "generation_status_sha256": sha((root / "generation" / pid / "status.json").read_bytes())
        if (root / "generation" / pid / "status.json").exists()
        else None,
    }
    require(identity(request) == gate["request_hash"], "native_request_or_review_epoch_mismatch")
    raw = read(root / "native" / pid / f"{timeframe}.json")
    original = (root / item["source_file"]).read_bytes()
    capture = period_native.parse(raw, original, review, pid, timeframe)
    probe = next(
        proof
        for proof in gate["evidence"]
        if proof["path"].startswith(f"native/{pid}/")
        and proof["path"] != f"native/{pid}/{timeframe}.json"
    )
    history = period_native.verify_initial_history(
        capture, original, read(root / probe["path"]), review, pid, timeframe
    )
    require(history == gate["initial_history"], "native_initial_history_mismatch")
    require(len(capture.ohlcv) > review["warmup_bars"] + 1, "native_evaluation_window_missing")
    start, end = (
        capture.ohlcv.index[review["warmup_bars"]],
        capture.ohlcv.index[-1] + period_native.STEPS[timeframe],
    )
    events = period_native.event_keys(capture.window_events(start, end))
    require(
        identity(events) == gate["native_signal_hash"] == selected["signal_hash"]
        and {event[1] for event in events} >= {"long", "short"},
        "native_event_hash_mismatch",
    )
    return {
        **epoch,
        "gate": period_native.proof(root, file),
        "code_path": path,
        "image_id": selected["image_id"],
        "signal_hash": selected["signal_hash"],
        "window": gate["window"],
        "scope": "observed_partial_window_only",
        "generated_code_review_sha256": approval,
    }


def period_evidence(
    root: Path,
    item: dict,
    path: str,
    timeframe: str,
    policy: ResearchExecution,
    period,
    source_hash: str,
    review: dict,
    native: dict,
) -> dict:
    cell = {
        "publication_id": item["id"],
        "code_path": path,
        "timeframe": timeframe,
        "period": period.id,
        "policy": "A" if policy.exit_policy == "signal_only_v1" else "B",
    }
    folder = root / "cells" / cell_key(cell)
    latest = read(folder / "latest.json")
    require(
        latest.get("status") == "completed"
        and all(latest.get(key) == value for key, value in cell.items()),
        "required_period_not_completed_or_wrong_cell",
    )
    result_file = checked(root, latest["result_file"], latest["result_sha256"])
    result = read(result_file)
    request = result["request"]
    require(
        identity(request) == latest["request_hash"]
        and read(folder / f"request-{latest['request_hash']}.json") == request
        and request["cell"] == cell,
        "financial_request_hash_or_cell_mismatch",
    )
    digest = policy.signal_mapping_hash
    require(
        latest.get("original_source_sha256") == review["source_sha256"]
        and latest.get("executable_sha256") == request.get("source_sha256") == source_hash
        and latest.get("signal_mapping_hash") == request.get("mapping_hash") == digest
        and latest.get("signal_mode") == request.get("signal_mode") == review["signal_mode"]
        and request.get("parameters") == review.get("inputs", {})
        and request.get("warmup_bars") == review["warmup_bars"]
        and request.get("policy") == policy.model_dump(mode="json"),
        "financial_source_mapping_inputs_or_policy_mismatch",
    )
    require(
        request.get("image_ids", {}).get(path) == native["image_id"],
        "financial_native_image_mismatch",
    )
    require(
        request.get("generated_code_review_sha256") == native.get("generated_code_review_sha256"),
        "financial_native_approval_mismatch",
    )
    epoch_comparison = harness_comparison(root, request["implementation"], native, review)
    dataset = read(root / "data/dataset.json")
    require(request.get("dataset_sha256") == identity(dataset), "financial_dataset_mismatch")
    records = dict(dataset["files"][period.id])
    if review["warmup_bars"] > dataset["warmup_bars"]:
        records[timeframe] = read(
            root / "data/extensions" / period.id / f"{timeframe}-{review['warmup_bars']}.json"
        )
    require(
        request.get("data_files") == records and request.get("costs") == COSTS,
        "financial_data_or_cost_mismatch",
    )
    for record in records.values():
        checked(root / "data", record["path"], record["sha256"])
        require(
            record["evaluation_start"] == period.start
            and record["evaluation_end_exclusive"] == period.end_exclusive,
            "financial_period_boundary_mismatch",
        )
    config = result["config_used"]
    expected = {
        "init_cash": "10000",
        "leverage": "1",
        "fees": COSTS["taker"],
        "maker_fee": COSTS["maker"],
        "slippage": COSTS["slippage"],
    }
    require(
        all(Decimal(str(config.get(key))) == Decimal(value) for key, value in expected.items())
        and config.get("fill_timing") == "next_bar_open"
        and config.get("include_funding") is True
        and config.get("freq") == {"1h": "1h", "4h": "4h", "1d": "1D"}[timeframe]
        and config.get("default_qty_type") in (None, "strategy.percent_of_equity")
        and config.get("default_qty_value") in (None, 100),
        "financial_capital_cost_sizing_or_execution_mismatch",
    )
    summaries = [event for event in result["trace"] if event.get("type") == "research_summary"]
    require(
        len(summaries) == 1
        and summaries[0]["policy"] == request["policy"]
        and summaries[0]["signal_hash"] == latest["signal_hash"] == signal_hash(result["signals"]),
        "financial_signal_tape_mismatch",
    )
    recipe = result.get("curve_encoding", {})
    require(
        recipe.get("kind") == "event_ledger_recipe_v1"
        and recipe.get("restoration_verified") is True,
        "ledger_restoration_recipe_missing",
    )
    restored = restore(result, root / "data")
    rows = len(restored["equity_curve"])
    expected_rows = (
        int(
            (
                datetime.fromisoformat(period.end_exclusive) - datetime.fromisoformat(period.start)
            ).total_seconds()
        )
        // 60
    )
    require(
        rows == recipe["row_count"] == latest["curve_rows"] == expected_rows,
        "restored_period_rows_mismatch",
    )
    receipt = {
        "kind": "full_ledger_curve_restoration_v1",
        "result_sha256": latest["result_sha256"],
        "verified": True,
        "row_count": rows,
        "canonical_hashes": recipe["canonical_hashes"],
        "metric_helper_sha256": recipe["metric_helper_sha256"],
        "pandas_version": recipe["pandas_version"],
        "numpy_version": recipe["numpy_version"],
    }
    receipt_file = root / "registration-candidates/restoration" / f"{latest['result_sha256']}.json"
    immutable(receipt_file, receipt)
    print(json.dumps({"unit": cell_key(cell), "ledger_rows_verified": rows}), flush=True)
    return {
        "period": period.id,
        "start": period.start,
        "end_exclusive": period.end_exclusive,
        "request_hash": latest["request_hash"],
        "result": period_native.proof(root, result_file),
        "signal_hash": latest["signal_hash"],
        "restoration": period_native.proof(root, receipt_file),
        "curve_rows": rows,
        "harness_comparison": epoch_comparison,
    }


def candidate(root: Path, item: dict, path: str, timeframe: str, arm: str) -> dict:
    _, original_hash, _ = reviewed_source(root, item)
    source, source_hash, review = artifact(root, root, item, path)
    require(sha(source.encode()) == source_hash, "artifact_executed_source_bytes_mismatch")
    policy = ResearchExecution(
        contract_version=1,
        exit_policy="signal_only_v1" if arm == "A" else "swing_two_bar_v1",
        reentry_policy="close_then_reenter_v1",
        signal_mode=review["signal_mode"],
        signal_mapping_hash=mapping_hash(review),
    )
    native = native_evidence(root, item, path, timeframe, source_hash, review)
    native_public = {key: value for key, value in native.items() if not key.startswith("_")}
    periods = [
        period_evidence(root, item, path, timeframe, policy, period, source_hash, review, native)
        for period in PERIODS
    ]
    provenance = {
        "origin": "tradingview_period_policy_study",
        "experiment": root.name,
        "publication_id": item["id"],
        "url": item["url"],
        "author": item.get("author"),
        "original_source_sha256": original_hash,
        "source_encoding": {
            "method": "utf8_decode_no_normalization",
            "executed_source_sha256": source_hash,
            "snapshot_source_sha256": sha(source.encode()),
            "source_bytes_preserved": True,
        },
        "source_review_sha256": sha((root / item["review_file"]).read_bytes()),
        "research_execution": policy.model_dump(mode="json"),
        "research_assumptions": {
            "costs": COSTS,
            "initial_capital": "10000",
            "leverage": "1",
            "allocation_pct": "100",
            "execution_timeframe": "1min",
            "fill_timing": "next_parent_open",
            "funding": "observed_historical_settlements",
            "period_end": "mark_without_synthetic_close",
        },
        "dataset_sha256": identity(read(root / "data/dataset.json")),
        "execution_implementation_sha256": identity(native["_implementation"]),
        "native": native_public,
        "periods": periods,
        "promotable_to_demo": False,
        "limitations": [
            "native는 관측한 부분창만 검증",
            "과거성과·현재인기도선정",
            "과거펀딩일정독립검증미완료",
        ],
    }
    request = SaveCodeStrategyRequest.model_validate(
        {
            "name": f"{item['title'][:75]} · {path} · {arm} · {timeframe} · {item['id']}",
            "description": "공개 원문 기간별 정책 연구. 5기간 원장 복원·해당 코드 경로의 부분창 native 대조이며 Demo 활성화·주문 승인이 아닙니다.",
            "symbol": "BTC/USDT:USDT",
            "timeframe": timeframe,
            "settings": {
                "leverage": 1,
                "margin_mode": "isolated",
                "position_size_pct": 100,
                "fill_timing": "next_bar_open",
            },
            "code": {
                "schema_version": 1,
                "execution_policy": "code_research_v1",
                "language": path,
                "source_code": source,
                "warmup_bars": review["warmup_bars"],
                "params": review.get("inputs", {}),
                "provenance": provenance,
            },
        }
    )
    payload = request.model_dump(mode="json")
    require(request.code.source_hash == source_hash, "product_snapshot_changed_executed_source")
    target = (
        root
        / "registration-candidates"
        / f"{item['id']}-{path}-{arm}-{timeframe}"
        / request.code.execution_hash
        / "save-request.json"
    )
    immutable(target, payload)
    return {
        "status": "validated_registration_pending_deployment",
        "get_verified": False,
        "publication_id": item["id"],
        "code_path": path,
        "policy": arm,
        "timeframe": timeframe,
        "payload": period_native.proof(root, target),
        "source_hash": request.code.source_hash,
        "execution_hash": request.code.execution_hash,
        "period_count": len(periods),
        "native": native_public,
        "provenance_bytes": len(
            json.dumps(provenance, ensure_ascii=False, allow_nan=False).encode()
        ),
        "post": {"method": "POST", "path": ENDPOINT, "expected_status": 201, "sent": False},
        "get": {"method": "GET", "path_template": ENDPOINT + "/{strategy_id}", "sent": False},
        "deployment_blocker": "current_server_does_not_support_code_research_v1",
    }


def verify_saved_definition(payload: dict, posted: dict, fetched: dict) -> dict:
    """후속 POST/GET이 반환한 정의·불변 버전 전량이 후보와 같아야 한다."""
    request = SaveCodeStrategyRequest.model_validate(payload)
    responses = [CodeStrategyResponse.model_validate(value) for value in (posted, fetched)]
    for response in responses:
        require(response.is_archived is False, "saved_definition_unexpectedly_archived")
        for key in ("name", "description", "symbol", "timeframe", "settings"):
            require(
                getattr(response, key) == getattr(request, key),
                "saved_definition_metadata_mismatch",
            )
        for key, value in request.code.model_dump(mode="json").items():
            require(
                response.version.model_dump(mode="json")[key] == value,
                "saved_definition_code_contract_mismatch",
            )
        require(
            response.version.source_hash == request.code.source_hash
            and response.version.execution_hash == request.code.execution_hash,
            "saved_definition_hash_mismatch",
        )
    require(
        responses[0].id == responses[1].id and responses[0].version.id == responses[1].version.id,
        "saved_definition_version_or_strategy_changed",
    )
    return {
        "strategy_id": str(responses[1].id),
        "version_id": str(responses[1].version.id),
        "get_verified": True,
    }


def prepare(root: Path, pid: str, timeframe: str) -> dict:
    item = next(value for value in read(root / "catalogue.json")["items"] if value["id"] == pid)
    units = []
    for path in ("pine", "python"):
        for arm in ("A", "B"):
            try:
                value = candidate(root, item, path, timeframe, arm)
            except (
                ValueError,
                OSError,
                KeyError,
                StopIteration,
                TypeError,
                ArithmeticError,
            ) as error:
                value = {
                    "publication_id": pid,
                    "code_path": path,
                    "policy": arm,
                    "timeframe": timeframe,
                    "status": "blocked_registration_gate",
                    "get_verified": False,
                    "reason": f"{type(error).__name__}:{error}",
                }
            write(root / "registration" / f"{pid}-{path}-{arm}-{timeframe}.json", value)
            units.append(value)
    manifest = {
        "created_at": now(),
        "publication_id": pid,
        "timeframe": timeframe,
        "server_writes": 0,
        "candidates": units,
        "validated_candidates": sum(
            value["status"] == "validated_registration_pending_deployment" for value in units
        ),
    }
    write(root / "registration-candidates" / f"{pid}-{timeframe}.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--timeframe", choices=TIMEFRAMES, required=True)
    args = parser.parse_args()
    manifest = prepare(args.run.resolve(), args.id, args.timeframe)
    print(
        json.dumps({"validated_candidates": manifest["validated_candidates"], "server_writes": 0}),
        flush=True,
    )


if __name__ == "__main__":
    main()
