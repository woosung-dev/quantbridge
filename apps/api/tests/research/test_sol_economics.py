"""선정·native ABI·입력 cache·경제 분모 검사. Docker·거래소·모델은 실행하지 않는다."""

import itertools
import json
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import sol_economics as economics
from tools.research.data import digest, json_write
from tools.research.sol_economic_data import stress_scenarios


def artifact(tmp_path, *, language="python"):
    source = tmp_path / "candidate.txt"
    source.write_text("def on_bar(ctx, state):\n    return {'action': 'hold'}\n")
    values = [
        {
            "case_id": "01",
            "language": language,
            "source_path": source.name,
            "source_hash": digest(source),
            "arm": "A",
            "repetition": 0,
        }
    ]
    path = tmp_path / "artifacts.json"
    json_write(path, values)
    return economics.read_artifacts(path)[0], path


def selection(tmp_path):
    evidence = tmp_path / "full-quality.json"
    rows = [
        {
            "case_id": f"{number:02}",
            "language": "python",
            "source_path": None,
            "source_hash": None,
            "arm": "A",
            "repetition": None,
        }
        for number in range(1, 31)
    ]
    path = tmp_path / "artifacts.json"
    json_write(path, rows)
    values = economics.read_artifacts(path)
    spec = {
        "policy": economics.POLICY,
        "quality_stage": "full_eval",
        "decided_before_economics": True,
        "arm": "A",
        "language": "python",
        "quality_evidence": {"path": evidence.name, "sha256": None},
        "semantic_pass_repetitions": {x["case_id"]: [] for x in rows},
        "selected_source_hashes": {x["case_id"]: None for x in rows},
    }
    write_quality_proof(tmp_path, spec)
    proof = tmp_path / "selection.json"
    json_write(proof, spec)
    return values, proof, spec


def write_quality_proof(tmp_path, spec):
    rows, files = [], {}
    for case, arm, language, repetition in itertools.product(
        (f"{n:02}" for n in range(1, 31)), "ABC", ("pine", "python", "typescript"), range(5)
    ):
        passed = (
            arm == spec["arm"]
            and language == spec["language"]
            and repetition in spec["semantic_pass_repetitions"][case]
        )
        checksum = spec["selected_source_hashes"][case] if passed else None
        rows.append(
            {
                "case_id": case,
                "arm": arm,
                "language": language,
                "repetition": repetition,
                "observation": "complete",
                "public_status": "public_pass" if passed else "failed",
                "semantic_status": "passed" if passed else "generation_or_public_failure",
                "source_hash": checksum,
            }
        )
        if passed:
            files[f"trials/{arm}/{language}/{case}/{repetition}/source.txt"] = checksum
    report = {
        "schema_version": 1,
        "stage": "evaluation",
        "complete": True,
        "final_selection_allowed": True,
        "expected_artifacts": 1350,
        "manifest_sha256": "a" * 64,
        "input_files": files,
        "implementation_hashes": {},
        "artifact_scores": rows,
    }
    report["input_proof_sha256"] = economics.quality_digest(
        {"manifest_sha256": report["manifest_sha256"], "files": files, "implementations": {}}
    )
    path = tmp_path / "full-quality.json"
    json_write(path, report)
    spec.update(
        manifest_sha256=report["manifest_sha256"], input_proof_sha256=report["input_proof_sha256"]
    )
    spec["quality_evidence"]["sha256"] = digest(path)


def data():
    index = pd.date_range("2026-01-01", periods=5, freq="h", tz="UTC")
    parent = pd.DataFrame(
        {"open": "100", "high": "102", "low": "99", "close": "101", "volume": "20"}, index=index
    )
    funding = pd.Series(["0.0001"], index=index[:1])
    return parent, funding, None


class Tape:
    def __init__(self, bad=False):
        self.bad = bad
        self.closed = False

    def exchange(self, message):
        if message["type"] == "init":
            return {"ready": 1}
        intent = {"action": "hold"}
        if self.bad:
            intent["net_profit"] = "999999"
        return {"intent": intent}

    def close(self):
        self.closed = True


def job(tmp_path, *, language="python", builder=None, **changes):
    item, _ = artifact(tmp_path, language=language)
    cell = {
        "id": "historical_parent/BTCUSDT/1h",
        "family": "historical_parent",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "start": "2026-01-01T00:00Z",
        "end": "2026-01-01T05:00Z",
        "execution": False,
    }
    options = {
        "artifact": item,
        "cell": cell,
        "scenario": stress_scenarios()[0],
        "data": data(),
        "data_error": None,
        "snapshot_id": "snapshot",
        "runtime": {"image_ids": dict.fromkeys(economics.IMAGES.values(), "sha256:" + "1" * 64)},
        "warmup": 0,
        "cache": tmp_path / "cache",
        "transport_builder": builder or (lambda *_: Tape()),
    }
    options.update(changes)
    return economics.run_job(**options), options


def test_source_file_mutation_is_retained_as_failed_input(tmp_path):
    _, path = artifact(tmp_path)
    (tmp_path / "candidate.txt").write_text("changed source")
    result = economics.read_artifacts(path)
    assert len(result) == 1 and result[0]["source_code"] is None
    assert "source_integrity" in result[0]["source_error"]
    assert result[0]["observed_source_hash"] != result[0]["source_hash"]


def test_final_selection_preserves_all_thirty_and_rejects_best_return_repeat(tmp_path):
    values, proof, spec = selection(tmp_path)
    assert economics.validate_selection(proof, values)["selection_file_sha256"] == digest(proof)
    spec["semantic_pass_repetitions"]["01"] = [0, 2]
    spec["selected_source_hashes"]["01"] = "1" * 64
    values[0].update(repetition=2, source_hash="1" * 64)
    write_quality_proof(tmp_path, spec)
    json_write(proof, spec)
    with pytest.raises(ValueError, match="첫 semantic"):
        economics.validate_selection(proof, values)
    values[0]["repetition"] = 0
    economics.validate_selection(proof, values)
    with pytest.raises(ValueError, match="01~30"):
        economics.validate_selection(proof, values[:-1])


def test_quality_evidence_and_selected_source_are_hash_bound(tmp_path):
    values, proof, _ = selection(tmp_path)
    values[0]["source_hash"] = "2" * 64
    with pytest.raises(ValueError):
        economics.validate_selection(proof, values)
    values[0]["source_hash"] = None
    (tmp_path / "full-quality.json").write_text("changed evidence")
    with pytest.raises(ValueError, match="해시"):
        economics.validate_selection(proof, values)


@pytest.mark.parametrize("mutation", ["opaque_report", "manifest", "proof", "later_rep", "source"])
def test_selection_cannot_relabel_evidence_or_first_pass(tmp_path, mutation):
    values, proof, spec = selection(tmp_path)
    spec["semantic_pass_repetitions"]["01"] = [0, 2]
    spec["selected_source_hashes"]["01"] = "1" * 64
    values[0].update(repetition=0, source_hash="1" * 64)
    write_quality_proof(tmp_path, spec)
    if mutation == "opaque_report":
        path = tmp_path / "full-quality.json"
        json_write(path, {"not_a_quality_report": True})
        spec["quality_evidence"]["sha256"] = digest(path)
    elif mutation in {"manifest", "proof"}:
        spec["manifest_sha256" if mutation == "manifest" else "input_proof_sha256"] = "b" * 64
    elif mutation == "later_rep":
        spec["semantic_pass_repetitions"]["01"] = [2]
        values[0]["repetition"] = 2
    else:
        spec["selected_source_hashes"]["01"] = "2" * 64
        values[0]["source_hash"] = "2" * 64
    json_write(proof, spec)
    with pytest.raises(ValueError, match=r"보고서|proof"):
        economics.validate_selection(proof, values)


@pytest.mark.parametrize("language", ["pine", "python", "typescript"])
def test_each_language_uses_common_broker_and_action_only_abi(tmp_path, language):
    seen = []

    def build(*args):
        seen.append(args)
        return Tape()

    row, _ = job(tmp_path, language=language, builder=build)
    assert row["status"] == "ok" and row["metrics"]["total_return"] == "0"
    assert seen[0][0] == language
    assert row["funding_price"] == "parent_open_proxy_at_observed_8h_settlement"
    assert row["method_quality_score"] is None and row["promotable"] is False


def test_generated_profit_fields_cannot_override_broker_metrics(tmp_path):
    row, _ = job(tmp_path, builder=lambda *_: Tape(bad=True))
    assert row["status"] == "failed" and "action" in row["error"]
    assert "metrics" not in row


def test_identical_input_hits_cache_but_changed_input_or_image_does_not(tmp_path):
    row, options = job(tmp_path)
    assert row["status"] == "ok"
    no_run = Mock(side_effect=AssertionError("cache must not execute source"))
    cached = economics.run_job(**{**options, "runner": no_run})
    assert cached["cache_hit"] is True
    changed = deepcopy(options)
    changed["data"][0].iloc[0, changed["data"][0].columns.get_loc("volume")] = "21"
    changed["runner"] = no_run
    assert economics.run_job(**changed)["status"] == "failed"
    changed = deepcopy(options)
    changed["runtime"]["image_ids"][economics.IMAGES["python"]] = "sha256:" + "2" * 64
    changed["runner"] = no_run
    assert economics.run_job(**changed)["status"] == "failed"


def test_corrupt_cache_is_rejected_and_preserved(tmp_path):
    row, options = job(tmp_path)
    path = options["cache"] / (row["job_hash"] + ".json")
    value = json.loads(path.read_text())
    value["metrics"]["total_return"] = "999999"
    json_write(path, value)
    with pytest.raises(ValueError, match="캐시"):
        economics.run_job(**options)
    assert json.loads(path.read_text())["metrics"]["total_return"] == "999999"


def test_fees_slippage_and_signed_funding_stresses_are_independent(tmp_path):
    seen = []

    def run(*args, **kwargs):
        seen.append((args[3], kwargs["funding_rates"].iloc[0]))
        return economics.run_code_backtest(*args, **kwargs)

    _, options = job(tmp_path)
    parent, _, minute = data()
    signed = pd.Series(["-0.0001"], index=parent.index[:1])
    for scenario in stress_scenarios():
        economics.run_job(
            **{**options, "scenario": scenario, "data": (parent, signed, minute), "runner": run}
        )
    baseline, fee, slip, fund = seen
    assert fee[0].fees == baseline[0].fees * 2 and fee[0].maker_fee == baseline[0].maker_fee * 2
    assert fee[0].slippage == baseline[0].slippage
    assert slip[0].slippage == baseline[0].slippage * 2 and slip[0].fees == baseline[0].fees
    assert fund[1] == Decimal("-0.0002")


def test_parent_daily_funding_is_na_without_any_execution(tmp_path):
    no_run = Mock(side_effect=AssertionError("not applicable"))
    _, options = job(tmp_path)
    cell = {**options["cell"], "timeframe": "1d"}
    row = economics.run_job(**{**options, "cell": cell, "runner": no_run})
    assert row["status"] == "not_applicable"
    no_run.assert_not_called()


@pytest.mark.parametrize(
    ("case_id", "allowed", "eligible_units", "na_units"),
    [
        ("08", ("1h", "4h", "1d"), 40, 8),
        ("21", ("1h", "4h"), 32, 16),
        ("30", ("1h",), 16, 32),
    ],
)
def test_case_timeframe_guard_preserves_48_units_without_running_incompatible_source(
    tmp_path, case_id, allowed, eligible_units, na_units
):
    item, _ = artifact(tmp_path)
    item["case_id"] = case_id
    original = deepcopy(item)
    window = {"start": "2026-01-01T00:00Z", "end_exclusive": "2026-01-03T00:00Z"}
    runner = Mock(side_effect=RuntimeError("eligible execution marker; no native runtime"))
    transport = Mock(side_effect=AssertionError("no native runtime"))
    records = []
    for cell in economics.cells({"historical_window": window, "execution_window": window}):
        for scenario in stress_scenarios():
            before = runner.call_count
            row = economics.run_job(
                item,
                cell,
                scenario,
                data=data(),
                data_error=None,
                snapshot_id="snapshot",
                runtime={},
                warmup=0,
                cache=tmp_path / "cache",
                runner=runner,
                transport_builder=transport,
            )
            records.append(row)
            if cell["timeframe"] not in allowed:
                assert row["status"] == "not_applicable"
                assert "case_timeframe_incompatible" in row["error"]
                assert runner.call_count == before
                assert row["binding"]["case_timeframe_compatibility"] == {
                    "supported_timeframes": list(allowed),
                    "error": economics.CASE_TIMEFRAME_REASONS[case_id],
                }
    assert len(records) == 48
    assert runner.call_count == eligible_units
    assert sum(row["status"] == "not_applicable" for row in records) == na_units
    assert item == original
    transport.assert_not_called()


def test_timeframe_compatibility_is_a_closed_catalogue_id_table():
    assert set(economics.CASE_TIMEFRAMES) == {f"{number:02}" for number in range(1, 31)}
    assert set(economics.CASE_TIMEFRAME_REASONS) == {"21", "30"}


def test_dedup_is_per_strategy_cell_scenario_and_families_are_separate(tmp_path):
    row, _ = job(tmp_path)
    records = [
        row,
        deepcopy(row),
        {**row, "cell_id": "minute_execution/BTCUSDT/1h", "family": "minute_execution"},
        {**row, "strategy_id": "02", "status": "failed"},
    ]
    result = economics.report(records)
    parent = result["families"]["historical_parent"]
    assert parent["planned_units"] == 3 and parent["failed"] == 1
    assert parent["strategies"][0]["scenarios"]["baseline"]["unique_signal_cells"] == 1
    assert result["families"]["minute_execution"]["planned_units"] == 1
    assert result["usd_cost"] is None


def test_cell_plan_has_48_units_including_eight_parent_daily_na():
    window = {"start": "2024-10-21T00:00Z", "end_exclusive": "2026-10-21T00:00Z"}
    plan = economics.cells({"historical_window": window, "execution_window": window})
    assert len(plan) * len(stress_scenarios()) == 48
    assert sum(not x["execution"] and x["timeframe"] == "1d" for x in plan) * 4 == 8


def test_runtime_binding_rejects_core_changes_without_running_docker(tmp_path):
    hashes = {}
    for directory in ("code_runtime", "pine_v2", "python_runtime"):
        for path in (economics.ROOT / "apps/api/src/strategy" / directory).rglob("*.py"):
            hashes[str(path.relative_to(economics.ROOT))] = digest(path)
    for path in (economics.ROOT / "apps/api/src/backtest/engine").rglob("*.py"):
        hashes[str(path.relative_to(economics.ROOT))] = digest(path)
    value = {
        "source_hashes": hashes,
        "image_ids": dict.fromkeys(economics.IMAGES.values(), "sha256:" + "1" * 64),
    }
    path = tmp_path / "environment.json"
    json_write(path, {"environment": value})
    actual = economics.runtime_binding(path)
    assert actual["source_hashes"] == hashes
    value["source_hashes"][next(iter(hashes))] = "0" * 64
    json_write(path, value)
    with pytest.raises(ValueError, match="실행 파일"):
        economics.runtime_binding(path)


def test_actual_transport_image_must_match_expected_id(monkeypatch):
    runtime = Mock()
    runtime.image_id = "sha256:" + "2" * 64
    monkeypatch.setattr("src.strategy.code_runtime.sandbox.create_transport", lambda *_: runtime)
    with pytest.raises(ValueError, match="이미지"):
        economics.native_transport("python", data()[0], "sha256:" + "1" * 64)
    runtime.close.assert_called_once()


def test_execute_preserves_missing_semantic_and_failed_source_denominators(tmp_path, monkeypatch):
    values, proof, spec = selection(tmp_path)
    values[0].update(source_hash="1" * 64, source_error="source_integrity: changed", repetition=0)
    spec["semantic_pass_repetitions"]["01"] = [0]
    spec["selected_source_hashes"]["01"] = "1" * 64
    write_quality_proof(tmp_path, spec)
    json_write(proof, spec)
    selected = economics.validate_selection(proof, values)
    window = {"start": "2026-01-01T00:00Z", "end_exclusive": "2026-01-03T00:00Z"}
    manifest = {
        "snapshot_id": "snap",
        "historical_window": window,
        "execution_window": window,
        "warmup_bars": 0,
        "files": [],
    }
    monkeypatch.setattr(economics, "load_snapshot", lambda _: manifest)
    journal = []
    monkeypatch.setattr(economics, "append_journal", lambda _, row: journal.append(row))
    no_execute = Mock(side_effect=AssertionError("no eligible sources"))
    result = economics.execute(
        values,
        tmp_path / "snapshot.json",
        {},
        tmp_path / "result",
        selected,
        loader=Mock(side_effect=ValueError("missing input")),
        runner=no_execute,
    )
    assert len(journal) == 30 * 48
    parent = result["families"]["historical_parent"]
    minute = result["families"]["minute_execution"]
    assert parent["planned_units"] == minute["planned_units"] == 720
    assert parent["strategy_coverage"]["01"] == {"ok": 0, "failed": 16, "not_applicable": 8}
    assert minute["strategy_coverage"]["01"] == {"ok": 0, "failed": 24, "not_applicable": 0}
    assert minute["strategy_coverage"]["30"]["not_applicable"] == 24
    no_execute.assert_not_called()


def test_cli_plan_only_does_not_execute_and_real_run_requires_selection(monkeypatch, capsys):
    monkeypatch.setattr(
        economics, "read_artifacts", lambda _: [{"case_id": "01", "source_error": None}]
    )
    monkeypatch.setattr(economics, "load_snapshot", lambda _: {"snapshot_id": "snap"})
    monkeypatch.setattr(economics, "runtime_binding", lambda _: {})
    execute = Mock(side_effect=AssertionError("no native execution"))
    monkeypatch.setattr(economics, "execute", execute)
    args = [
        "sol_economics",
        "--artifacts",
        "a.json",
        "--snapshot",
        "s.json",
        "--environment",
        "e.json",
        "--output",
        "unused",
    ]
    monkeypatch.setattr(sys, "argv", [*args, "--plan-only"])
    economics.main()
    result = json.loads(capsys.readouterr().out)
    assert result["native_execution"] is False and result["planned_units"] == 48
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as exc:
        economics.main()
    assert exc.value.code == 2
    execute.assert_not_called()
