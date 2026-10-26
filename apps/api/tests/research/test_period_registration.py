"""등록 후보의 필수 증거와 POST/GET 전량 대조를 검증한다. DB·네트워크 미사용."""

from __future__ import annotations

import copy
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import period_registration as registration
from tools.research.period_study.schema import COSTS, PERIODS
from tools.research.period_study.state import identity, read, sha, write

from src.strategy.code_schemas import SaveCodeStrategyRequest

REAL_NATIVE_EVIDENCE = registration.native_evidence


@pytest.fixture
def completed(tmp_path, monkeypatch):
    item = {
        "id": "example",
        "source_file": "sources/example.pine",
        "review_file": "reviews/example.json",
        "title": "Example",
        "url": "https://www.tradingview.com/script/example/",
        "author": "test",
    }
    source = "//@version=6\nindicator('example')\nplot(close)\n"
    (tmp_path / "sources").mkdir()
    (tmp_path / item["source_file"]).write_text(source)
    original_hash = sha(source.encode())
    review = {
        "source_sha256": original_hash,
        "reviewer": "test",
        "basis": "테스트 명시 매핑",
        "signal_mode": "shared_events",
        "warmup_bars": 2,
        "inputs": {},
        "signal_bindings": [{"direction": "long"}, {"direction": "short"}],
    }
    write(tmp_path / item["review_file"], review)
    write(tmp_path / "source_receipts/example.json", {"source_sha256": original_hash})
    write(tmp_path / "catalogue.json", {"items": [item]})
    sources = {
        "pine": "strategy('example')",
        "python": "def on_bar(ctx, state):\n return {'action': 'hold'}",
    }
    implementation = {"engine.py": "e" * 64}
    monkeypatch.setattr(registration, "implementation", lambda: implementation)
    monkeypatch.setattr(
        registration,
        "artifact",
        lambda root, source_root, item, path: (sources[path], sha(sources[path].encode()), review),
    )
    native = {
        "gate": {"path": "native-verification/example-1d.json", "sha256": "n" * 64},
        "code_path": "pine",
        "image_id": "sha256:" + "a" * 64,
        "signal_hash": "b" * 64,
        "window": {"warmup_bars": 2},
        "scope": "observed_partial_window_only",
        "generated_code_review_sha256": None,
        "_implementation": implementation,
    }
    monkeypatch.setattr(
        registration,
        "native_evidence",
        lambda root, item, path, *args: {**native, "code_path": path},
    )
    dataset = {"warmup_bars": 2, "files": {}}
    for period in PERIODS:
        file = tmp_path / "data" / period.id / "data.csv"
        file.parent.mkdir(parents=True)
        file.write_text("단위 테스트의 복원 의존성 대역 입력")
        record = {
            "path": f"{period.id}/data.csv",
            "sha256": sha(file.read_bytes()),
            "evaluation_start": period.start,
            "evaluation_end_exclusive": period.end_exclusive,
        }
        dataset["files"][period.id] = dict.fromkeys(("1d", "1min", "funding"), record)
    write(tmp_path / "data/dataset.json", dataset)
    for path in sources:
        for arm in ("A", "B"):
            for period in PERIODS:
                cell = {
                    "publication_id": "example",
                    "code_path": path,
                    "timeframe": "1d",
                    "period": period.id,
                    "policy": arm,
                }
                policy = {
                    "contract_version": 1,
                    "exit_policy": "signal_only_v1" if arm == "A" else "swing_two_bar_v1",
                    "reentry_policy": "close_then_reenter_v1",
                    "signal_mode": "shared_events",
                    "signal_mapping_hash": registration.mapping_hash(review),
                }
                source_hash = sha(sources[path].encode())
                request = {
                    "cell": cell,
                    "source_sha256": source_hash,
                    "mapping_hash": policy["signal_mapping_hash"],
                    "parameters": {},
                    "signal_mode": "shared_events",
                    "warmup_bars": 2,
                    "policy": policy,
                    "implementation": implementation,
                    "image_ids": {path: native["image_id"]},
                    "generated_code_review_sha256": None,
                    "dataset_sha256": identity(dataset),
                    "data_files": dataset["files"][period.id],
                    "costs": COSTS,
                }
                rows = (
                    int(
                        (
                            datetime.fromisoformat(period.end_exclusive)
                            - datetime.fromisoformat(period.start)
                        ).total_seconds()
                    )
                    // 60
                )
                result = {
                    "request": request,
                    "config_used": {
                        "init_cash": "10000",
                        "leverage": "1",
                        "fees": COSTS["taker"],
                        "maker_fee": COSTS["maker"],
                        "slippage": COSTS["slippage"],
                        "fill_timing": "next_bar_open",
                        "include_funding": True,
                        "freq": "1D",
                        "default_qty_type": None,
                        "default_qty_value": None,
                    },
                    "signals": [],
                    "trace": [
                        {
                            "type": "research_summary",
                            "policy": policy,
                            "signal_hash": registration.signal_hash([]),
                        }
                    ],
                    "curve_encoding": {
                        "kind": "event_ledger_recipe_v1",
                        "restoration_verified": True,
                        "row_count": rows,
                        "canonical_hashes": dict.fromkeys(
                            ("equity_curve", "drawdown_curve", "buy_and_hold_curve"), "c" * 64
                        ),
                        "metric_helper_sha256": "d" * 64,
                        "pandas_version": "test",
                        "numpy_version": "test",
                    },
                }
                folder = tmp_path / "cells" / registration.cell_key(cell)
                result_file = folder / "result.json"
                write(result_file, result)
                write(folder / f"request-{identity(request)}.json", request)
                write(
                    folder / "latest.json",
                    {
                        **cell,
                        "status": "completed",
                        "request_hash": identity(request),
                        "result_file": str(result_file.relative_to(tmp_path)),
                        "result_sha256": sha(result_file.read_bytes()),
                        "original_source_sha256": original_hash,
                        "executable_sha256": source_hash,
                        "signal_mapping_hash": policy["signal_mapping_hash"],
                        "signal_mode": "shared_events",
                        "signal_hash": registration.signal_hash([]),
                        "curve_rows": rows,
                    },
                )
    calls = []

    def restored(result, root):
        calls.append(result["request"]["cell"])
        return {"equity_curve": range(result["curve_encoding"]["row_count"])}

    monkeypatch.setattr(registration, "restore", restored)
    return tmp_path, item, review, sources, calls


def test_four_independent_candidates_validate_exact_api_payload_without_server_writes(completed):
    root, _, _, _, calls = completed
    manifest = registration.prepare(root, "example", "1d")
    assert manifest["validated_candidates"] == 4
    assert manifest["server_writes"] == 0
    assert len(calls) == 20
    for unit in manifest["candidates"]:
        assert unit["get_verified"] is False
        assert unit["post"]["sent"] is False
        payload = read(root / unit["payload"]["path"])
        request = SaveCodeStrategyRequest.model_validate(payload)
        assert request.code.execution_policy == "code_research_v1"
        assert request.code.language.value == unit["code_path"]
        assert request.code.execution_hash == unit["execution_hash"]
        assert len(request.code.provenance["periods"]) == 5
        assert unit["provenance_bytes"] <= 32768


@pytest.mark.parametrize(
    "change,pattern",
    [
        ("status", "required_period"),
        ("missing_period", "No such file"),
        ("result_bytes", "SHA"),
        ("request_hash", "request_hash"),
        ("source", "source_mapping"),
        ("mapping", "source_mapping"),
        ("params", "source_mapping"),
        ("policy", "source_mapping"),
        ("image", "image_mismatch"),
        ("approval", "approval_mismatch"),
        ("implementation", "implementation_mismatch"),
        ("cost", "data_or_cost"),
        ("config", "capital_cost"),
        ("signals", "signal_tape"),
        ("recipe", "recipe_missing"),
        ("curve_rows", "period_rows"),
    ],
)
def test_required_financial_gate_cannot_be_replaced_by_completed_label(completed, change, pattern):
    root, item, _, _, _ = completed
    folder = root / "cells/example/pine/1d/P5/A"
    latest = read(folder / "latest.json")
    file = root / latest["result_file"]
    result = read(file)
    if change == "status":
        latest["status"] = "failed"
    elif change == "missing_period":
        (folder / "latest.json").unlink()
    elif change == "result_bytes":
        file.write_text("changed")
    elif change == "request_hash":
        latest["request_hash"] = "0" * 64
    else:
        request = result["request"]
        if change == "source":
            request["source_sha256"] = "0" * 64
        elif change == "mapping":
            request["mapping_hash"] = "0" * 64
        elif change == "params":
            request["parameters"] = {"length": 3}
        elif change == "policy":
            request["policy"]["exit_policy"] = "swing_two_bar_v1"
        elif change == "image":
            request["image_ids"]["pine"] = "sha256:" + "0" * 64
        elif change == "approval":
            request["generated_code_review_sha256"] = "0" * 64
        elif change == "implementation":
            request["implementation"] = {}
        elif change == "cost":
            request["costs"]["maker"] = "0"
        elif change == "config":
            result["config_used"]["fees"] = "0"
        elif change == "signals":
            result["signals"] = [{"action": "long"}]
        elif change == "recipe":
            result["curve_encoding"]["restoration_verified"] = False
        elif change == "curve_rows":
            result["curve_encoding"]["row_count"] -= 1
        latest["request_hash"] = identity(request)
        write(folder / f"request-{identity(request)}.json", request)
        write(file, result)
        latest["result_sha256"] = sha(file.read_bytes())
    if change != "missing_period":
        write(folder / "latest.json", latest)
    with pytest.raises((ValueError, FileNotFoundError), match=pattern):
        registration.candidate(root, item, "pine", "1d", "A")


def test_ledger_restoration_failure_blocks_candidate_without_export(completed, monkeypatch):
    root, item, _, _, _ = completed

    def failed(*args):
        raise ValueError("restored equity hash mismatch")

    monkeypatch.setattr(registration, "restore", failed)
    with pytest.raises(ValueError, match="equity hash"):
        registration.candidate(root, item, "python", "1d", "A")
    assert not list((root / "registration-candidates").rglob("save-request.json"))


def response_for(payload):
    request = SaveCodeStrategyRequest.model_validate(payload)
    return {
        "id": str(uuid4()),
        "name": request.name,
        "description": request.description,
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        "is_archived": False,
        "settings": request.settings.model_dump(mode="json"),
        "version": {
            **request.code.model_dump(mode="json"),
            "id": str(uuid4()),
            "source_hash": request.code.source_hash,
            "execution_hash": request.code.execution_hash,
            "created_at": "2026-10-26T00:00:00+00:00",
        },
    }


def test_post_get_verification_requires_entire_immutable_definition(completed):
    root, item, _, _, _ = completed
    unit = registration.candidate(root, item, "python", "1d", "B")
    payload = read(root / unit["payload"]["path"])
    posted = response_for(payload)
    assert registration.verify_saved_definition(payload, posted, posted)["get_verified"] is True
    archived = copy.deepcopy(posted)
    archived["is_archived"] = True
    with pytest.raises(ValueError, match="unexpectedly_archived"):
        registration.verify_saved_definition(payload, posted, archived)
    for key in ("id", "execution_hash", "source_hash", "source_code", "provenance"):
        fetched = copy.deepcopy(posted)
        if key == "id":
            fetched["version"][key] = str(uuid4())
        elif key == "provenance":
            fetched["version"][key]["research_execution"]["signal_mode"] = "position_feedback"
        else:
            fetched["version"][key] = "changed"
        with pytest.raises(ValueError, match="saved_definition"):
            registration.verify_saved_definition(payload, posted, fetched)


@pytest.mark.parametrize("status", ["not_run", "mismatch", "failed", "unverified"])
def test_other_native_path_pass_never_promotes_a_failed_path(completed, monkeypatch, status):
    root, _, _, _, _ = completed
    write(
        root / "native-verification/example-1d.json",
        {
            "status": "passed",
            "evidence_verified": True,
            "paths": {"pine": {"status": status}, "python": {"status": "passed"}},
        },
    )
    fake = registration.native_evidence
    monkeypatch.setattr(
        registration,
        "native_evidence",
        lambda root, item, path, *args: (
            REAL_NATIVE_EVIDENCE(root, item, path, *args)
            if path == "pine"
            else fake(root, item, path, *args)
        ),
    )
    manifest = registration.prepare(root, "example", "1d")
    assert manifest["validated_candidates"] == 2
    assert all(unit["status"] == "blocked_registration_gate" for unit in manifest["candidates"][:2])
    assert all(
        "native_selected_code_path_not_passed" in unit["reason"]
        for unit in manifest["candidates"][:2]
    )


def test_source_bytes_cannot_silently_normalize_before_product_snapshot(completed, monkeypatch):
    root, item, review, sources, _ = completed
    source = sources["python"]
    monkeypatch.setattr(
        registration,
        "artifact",
        lambda *args: (
            source.replace("\n", "\r\n"),
            sha(source.encode()),
            review,
        ),
    )
    with pytest.raises(ValueError, match="executed_source_bytes"):
        registration.candidate(root, item, "python", "1d", "A")


def test_frozen_harness_epoch_is_archived_without_relaxing_computation_hash(tmp_path, monkeypatch):
    from types import SimpleNamespace

    project = tmp_path / "project"
    paths = {
        "apps/api/src/engine.py": b"same computation",
        "tools/research/period_study/encoding.py": b"same curve computation",
        "tools/research/period_study/controller.py": b"new audit guard",
        "tools/research/period_native.py": b"native",
        "apps/api/scripts/pine_validation/native_capture.py": b"parser",
    }
    for relative, data in paths.items():
        file = project / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
    current = {
        key: sha(data)
        for key, data in paths.items()
        if key
        not in {
            "tools/research/period_native.py",
            "apps/api/scripts/pine_validation/native_capture.py",
        }
    }
    recorded = {key: sha(data) for key, data in paths.items()}
    recorded["tools/research/period_study/controller.py"] = sha(b"old audit guard")
    monkeypatch.setattr(registration, "ROOT", project)
    monkeypatch.setattr(registration, "implementation", lambda: current)
    monkeypatch.setattr(
        registration.subprocess,
        "run",
        lambda args, **kwargs: SimpleNamespace(
            stdout="old-revision\n" if args[1] == "log" else b"old audit guard"
        ),
    )
    result = registration.frozen_implementation(tmp_path, recorded)
    assert result["_implementation"]["tools/research/period_study/controller.py"] == sha(
        b"old audit guard"
    )
    assert result["execution_epoch"]["harness_changed_since_execution"] == [
        "tools/research/period_study/controller.py"
    ]
    receipt = read(tmp_path / result["execution_epoch"]["harness_receipt"]["path"])
    archived = next(
        value
        for value in receipt["frozen_harness"]
        if value["source_file"].endswith("controller.py")
    )
    assert (tmp_path / archived["path"]).read_bytes() == b"old audit guard"
    (project / "apps/api/src/engine.py").write_bytes(b"different computation")
    with pytest.raises(ValueError, match="execution_implementation_mismatch"):
        registration.frozen_implementation(tmp_path, recorded)
    (project / "apps/api/src/engine.py").write_bytes(paths["apps/api/src/engine.py"])
    (project / "tools/research/period_study/encoding.py").write_bytes(
        b"different curve computation"
    )
    with pytest.raises(ValueError, match="execution_implementation_mismatch"):
        registration.frozen_implementation(tmp_path, recorded)


@pytest.mark.parametrize("calculation_changed", [False, True])
def test_cross_epoch_harness_only_allows_the_reviewed_metadata_change(
    tmp_path, monkeypatch, calculation_changed
):
    from types import SimpleNamespace

    project = tmp_path / "project"
    old = b'def artifact():\n return "same source"\ndef run_group():\n base.update(costs=1)\n return value + 1\n'
    new = old.replace(
        b"base.update(costs=1)",
        b'base.update(costs=1, market_context_proof=review.get("market_context_proof"))',
    )
    if calculation_changed:
        new = new.replace(b"value + 1", b"value + 2")
    controller = "tools/research/period_study/controller.py"
    files = {
        controller: new,
        "apps/api/src/engine.py": b"same computation",
        "tools/research/period_native.py": b"native",
        "apps/api/scripts/pine_validation/native_capture.py": b"parser",
    }
    for relative, data in files.items():
        file = project / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
    current = {
        key: sha(value)
        for key, value in files.items()
        if key
        not in {
            "tools/research/period_native.py",
            "apps/api/scripts/pine_validation/native_capture.py",
        }
    }
    financial = {**current, controller: sha(old)}
    monkeypatch.setattr(registration, "ROOT", project)
    monkeypatch.setattr(registration, "implementation", lambda: current)
    monkeypatch.setattr(
        registration.subprocess,
        "run",
        lambda args, **kwargs: SimpleNamespace(
            stdout="old-revision\n" if args[1] == "log" else old
        ),
    )
    native = registration.frozen_implementation(
        tmp_path, {key: sha(value) for key, value in files.items()}
    )
    if calculation_changed:
        with pytest.raises(ValueError, match="controller_calculation_changed"):
            registration.harness_comparison(tmp_path, financial, native, {})
    else:
        result = registration.harness_comparison(tmp_path, financial, native, {})
        assert result["same_execution_epoch"] is False
        receipt = read(tmp_path / result["comparison"]["path"])
        assert receipt["past_execution_of_new_gate_claimed"] is False
        assert receipt["same_computation_after_removing_only_market_context_metadata"] is True
