"""고정 분모·원자료 결박·bounded 생성·시도 보존의 회귀 검사. DB 미사용."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.period_study import controller, dataset, generation
from tools.research.period_study.controller import record
from tools.research.period_study.dataset import missing_ranges, validate_row
from tools.research.period_study.encoding import compact, restore
from tools.research.period_study.schema import PERIODS, plan
from tools.research.period_study.state import identity, read, sha, write


def reviewed(tmp_path: Path) -> dict:
    source = "//@version=5\nindicator('example')\nplot(close)\n"
    item = {"id": "Abcd1234", "title": "Example", "source_file": "sources/Abcd1234.pine"}
    (tmp_path / "sources").mkdir()
    (tmp_path / item["source_file"]).write_text(source)
    write(tmp_path / "source_receipts/Abcd1234.json", {"source_sha256": sha(source.encode())})
    write(tmp_path / "reviews/Abcd1234.json", {
        "source_sha256": sha(source.encode()), "reviewer": "test-reviewer",
        "basis": "원문 신호 구문 대조", "signal_bindings": [{"direction": "long", "condition": "cross"}],
        "inputs": {}, "signal_mode": "shared_events",
    })
    return item


def test_fixed_period_manifest_keeps_both_policies_and_failed_source_slots():
    catalogue = {"items": [{"id": "Abcd1234"}, {"id": "Efgh5678"}]}
    value = plan(catalogue, "a" * 64)
    assert value["expected_cells"] == 120
    assert len({identity(cell) for cell in value["cells"]}) == 120
    assert value["cost_scenarios"] == ["baseline"]
    assert value["reentry_version"] == "close_then_reenter_v1"
    assert PERIODS[-1].start == "2026-04-24T00:00:00+00:00"
    assert PERIODS[-1].end_exclusive == "2026-10-24T00:00:00+00:00"
    with pytest.raises(ValueError, match="고유"):
        plan({"items": [{"id": "Abcd1234"}] * 2}, "a" * 64)


def test_real_gaps_are_requested_without_fabricating_existing_prices():
    assert missing_ranges(0, 6, 1, {1: [], 2: [], 4: []}) == [(0, 1), (3, 4), (5, 6)]
    validate_row(["0", "100", "102", "99", "101", "0"])
    with pytest.raises(ValueError):
        validate_row(["0", "100", "98", "99", "101", "5"])


def test_modified_pine_cannot_reuse_review(tmp_path):
    item = reviewed(tmp_path)
    (tmp_path / item["source_file"]).write_text("modified")
    with pytest.raises(ValueError, match="SHA"):
        generation.reviewed_source(tmp_path, item)


def test_two_generation_failures_are_terminal_and_never_called_again(tmp_path, monkeypatch):
    item = reviewed(tmp_path)
    calls = []

    def failed(prompt, destination, **kwargs):
        calls.append((prompt, destination, kwargs))
        return {"status": "failed", "error": "fixed failure"}

    monkeypatch.setattr(generation, "generate", failed)
    value = generation.generate_one(tmp_path, tmp_path, item)
    assert value["status"] == "failed"
    assert len(calls) == 2
    assert all(call[2]["timeout"] == 180 for call in calls)
    assert generation.generate_one(tmp_path, tmp_path, item) == value
    assert len(calls) == 2


def test_successful_generation_model_is_unknown_without_provider_evidence(tmp_path, monkeypatch):
    item = reviewed(tmp_path)

    def generated(prompt, destination, **kwargs):
        write(destination / "payload.json", {"source_code": "def on_bar(ctx, state):\n return {'action': 'hold'}", "assumptions": []})
        return {"status": "completed", "job_hash": "b" * 64,
                "model_attestation": "requested_cli_flag_no_response_model_metadata"}

    monkeypatch.setattr(generation, "generate", generated)
    value = generation.generate_one(tmp_path, tmp_path, item)
    assert value["requested_model"] == "gpt-6.1-sol"
    assert value["provider_reported_model"] == "UNKNOWN"
    assert (tmp_path / value["generated_file"]).exists()


def test_attempt_history_keeps_failure_and_later_success_separate(tmp_path):
    cell = {"publication_id": "Abcd1234", "code_path": "pine", "policy": "A", "timeframe": "1h", "period": "P1"}
    request = {"policy_version": 1}
    first = record(tmp_path, cell, request, "failed", reason="timeout", execution_attempt=1)
    second = record(tmp_path, cell, request, "failed", reason="timeout", execution_attempt=2)
    assert (first["attempt"], second["attempt"]) == (1, 2)
    assert record(tmp_path, cell, request, "failed", reason="timeout", execution_attempt=2) == second
    third = record(tmp_path, cell, {"policy_version": 2}, "completed")
    assert third["attempt"] == 3
    attempts = sorted((tmp_path / "cells").rglob("attempt-*.json"))
    assert len(attempts) == 3
    assert read(attempts[0])["status"] == "failed"


def test_insufficient_warmup_is_not_run_for_both_policies_instead_of_stopping_controller(tmp_path, monkeypatch):
    item = {"id": "Abcd1234"}
    review = {"source_sha256": "a" * 64, "signal_mode": "shared_events", "warmup_bars": 3000,
              "signal_bindings": [{"direction": "long", "condition": "cross"}]}
    write(tmp_path / "data/dataset.json", {"warmup_bars": 1000})
    monkeypatch.setattr(controller, "artifact", lambda *args: ("source", "b" * 64, review))
    monkeypatch.setattr(controller, "runtime", lambda: {"pine": "image", "python": "image"})

    def unavailable(*args):
        raise ValueError("warmup_extension_missing:P1/1h/3000")

    monkeypatch.setattr(controller, "load_period", unavailable)
    records = controller.run_group(tmp_path, tmp_path, item, "pine", "1h", "P1")
    assert len(records) == 2
    assert {row["status"] for row in records} == {"not_run"}
    assert all("warmup_extension_missing" in row["reason"] for row in records)


@pytest.mark.parametrize(
    "policies,mode,tape",
    [(("A",), "shared_events", None),
     (("B",), "position_feedback", None),
     (("B",), "shared_events", [{"action": "hold"}])],
)
def test_selected_policy_scope_never_backtests_the_successful_other_policy(
    tmp_path, monkeypatch, policies, mode, tape,
):
    from types import SimpleNamespace

    from src.strategy.code_runtime import backtest
    from src.strategy.python_runtime import serialization

    review = {"source_sha256": "a" * 64, "signal_mode": mode,
              "signal_bindings": [{"direction": "long", "condition": "original"}]}
    write(tmp_path / "data/dataset.json", {})
    monkeypatch.setattr(controller, "artifact", lambda *args: ("source", "b" * 64, review))
    monkeypatch.setattr(controller, "runtime", lambda: {"python": "image"})
    monkeypatch.setattr(controller, "load_period", lambda *args: (None, None, None, {}))
    monkeypatch.setattr(controller, "compact", lambda payload, *args: payload)
    monkeypatch.setattr(serialization, "result_payload", lambda result: {"metrics": {}, "trades": []})
    calls = []

    def execute(*args, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(equity_curve=[])

    monkeypatch.setattr(backtest, "run_code_backtest", execute)
    rows = controller.run_group(tmp_path, tmp_path, {"id": "Abcd1234"}, "python", "1h", "P1",
                                policies=policies, signal_tape=tape)

    assert len(calls) == 1
    assert [row["policy"] for row in rows] == list(policies)
    assert rows[0]["status"] == "completed"
    assert calls[0]["research_policy"].exit_policy == (
        "signal_only_v1" if policies == ("A",) else "swing_two_bar_v1"
    )
    assert calls[0]["signal_tape"] == tape
    other = "B" if policies == ("A",) else "A"
    assert not (tmp_path / "cells/Abcd1234/python/1h/P1" / other).exists()


def test_warmup_extension_preserves_base_manifest_and_existing_data(tmp_path, monkeypatch):
    from tools.research.period_study.schema import Period

    period = Period("P1", "2024-01-01T00:00:00+00:00", "2024-01-01T03:00:00+00:00")
    start, end = dataset.milliseconds(period.start), dataset.milliseconds(period.end_exclusive)
    width = 3_600_000
    rows = {when: [str(when), "100", "101", "99", "100", "1"] for when in range(start - 2 * width, end, width)}
    path = tmp_path / "P1/1h.csv.gz"
    path.parent.mkdir()
    path.write_bytes(dataset.csv_bytes(rows))
    original = path.read_bytes()
    manifest = {"warmup_bars": 2, "files": {"P1": {"1h": {"path": "P1/1h.csv.gz", "sha256": sha(original)}}}}
    write(tmp_path / "dataset.json", manifest)
    monkeypatch.setattr(dataset, "PERIODS", (period,))

    def additional(root, interval, left, right):
        return {when: [str(when), "100", "101", "99", "100", "1"] for when in range(left, right, width)}

    monkeypatch.setattr(dataset, "page_rows", additional)
    extension = dataset.extend(tmp_path, "P1", "1h", 4)
    assert extension["rows"] == 7
    assert extension["new_public_rows"] == 2
    assert read(tmp_path / "dataset.json") == manifest
    assert path.read_bytes() == original


def test_compact_recipe_replays_funding_partial_exit_and_same_minute_reentry_exactly(tmp_path):
    from decimal import Decimal

    import pandas as pd

    from src.backtest.engine.v2_adapter import (
        _as_float_series,
        _v2_buy_and_hold_curve,
        _v2_drawdown_extract,
    )
    from src.strategy.python_runtime.serialization import json_value

    start = dataset.milliseconds("2024-01-01T00:00:00+00:00")
    closes = ("101", "104", "103", "100")
    rows = {start + index * 60_000: [str(start + index * 60_000), "100", "105", "99", close, "1"] for index, close in enumerate(closes)}
    content = dataset.csv_bytes(rows)
    path = tmp_path / "P1/1min.csv.gz"
    path.parent.mkdir()
    path.write_bytes(content)
    frame = dataset.load_candles(path)
    values = ["9998", "9999.9", "9998.3", "10001.3"]
    equity = pd.Series([Decimal(value) for value in values], index=frame.index, dtype=object)
    dd, _ = _v2_drawdown_extract(_as_float_series(equity), frame)

    def event(index, **fields):
        return {"timestamp": frame.index[index].isoformat(), **fields}

    trace = [
        event(0, type="fill", kind="entry", direction="long", generation=1, quantity="1", price="100", fee="2", slippage="1"),
        event(1, type="funding", amount="0.5"),
        event(1, type="fill", kind="partial_tp", generation=1, quantity="0.5", gross_pnl="1.5", fee="0.1", slippage="0"),
        event(2, type="fill", kind="close", generation=1, quantity="0.5", gross_pnl="1", fee="0.2", slippage="0.1"),
        event(2, type="fill", kind="entry", direction="short", generation=2, quantity="1", price="103", fee="0.2", slippage="0.1"),
    ]
    payload = {"equity_curve": [{"timestamp": ts.isoformat(), "value": value} for ts, value in zip(frame.index, values, strict=True)],
               "metrics": {"drawdown_curve": json_value(dd), "buy_and_hold_curve": json_value(_v2_buy_and_hold_curve(frame, Decimal("10000")))},
               "config_used": {"init_cash": "10000"}, "trace": trace,
               "request": {"data_files": {"1min": {"path": "P1/1min.csv.gz", "sha256": sha(content)}}}}
    encoded = compact(payload, tmp_path)
    assert "equity_curve" not in encoded
    assert encoded["curve_encoding"]["raw_minute_curves_stored"] is False
    assert len(payload["equity_curve"]) == 4
    rebuilt = restore(encoded, tmp_path)
    assert rebuilt["equity_curve"] == payload["equity_curve"]
    assert rebuilt["metrics"] == payload["metrics"]
    encoded["trace"][1]["amount"] = "0.6"
    with pytest.raises(ValueError, match="해시"):
        restore(encoded, tmp_path)


def test_disk_reserve_pauses_financial_work_without_turning_pending_cells_into_failures(tmp_path, monkeypatch):
    from argparse import Namespace
    from types import SimpleNamespace

    catalogue = {"items": [{"id": "Abcd1234", "title": "Example"}]}
    write(tmp_path / "catalogue.json", catalogue)
    write(tmp_path / "manifest.json", plan(catalogue, sha((tmp_path / "catalogue.json").read_bytes())))
    monkeypatch.setattr(controller.shutil, "disk_usage", lambda path: SimpleNamespace(free=11 * 1024**3))

    def must_not_run(*args):
        raise AssertionError("저장 공간이 부족한데 금융 실행이 시작됐습니다")

    monkeypatch.setattr(controller, "run_group", must_not_run)
    args = Namespace(run_dir=tmp_path, catalogue=None, source_root=None, command="execute", ids=None,
                     shard=0, shards=1, limit=None, periods=["P5"], timeframes=["1d"], code_paths=["python"])
    result = controller.command(args)
    assert result["storage_paused"] is True
    assert result["financial_cells"] == {}
    assert result["pending_cells"] == 60


def test_python_artifact_requires_explicit_review_of_the_same_source_and_generated_bytes(tmp_path):
    item = reviewed(tmp_path)
    original, original_hash, source_review = generation.reviewed_source(tmp_path, item)
    code = "def on_bar(ctx,state):\n return {'action':'hold'}\n"
    folder = tmp_path / "generation/Abcd1234/0"
    folder.mkdir(parents=True)
    (folder / "source.py").write_text(code)
    status = {"status": "completed", "attempt": 0, "source_sha256": original_hash,
              "generated_file": "generation/Abcd1234/0/source.py", "generated_sha256": sha(code.encode()),
              "input_hash": identity({"source": original, "signal_bindings": source_review["signal_bindings"],
                                      "inputs": {}, "signal_mode": "shared_events"})}
    write(tmp_path / "generation/Abcd1234/status.json", status)
    with pytest.raises(ValueError, match="review_missing"):
        controller.artifact(tmp_path, tmp_path, item, "python")
    proof = {"status": "rejected", "reason": "invented_same_bar_priority", "reviewer": "independent-review",
             "original_source_sha256": original_hash, "generated_sha256": status["generated_sha256"]}
    write(folder / "code-review.json", proof)
    with pytest.raises(ValueError, match="review_rejected"):
        controller.artifact(tmp_path, tmp_path, item, "python")
    proof["status"] = "reviewed_for_isolated_execution"
    proof["generated_sha256"] = "f" * 64
    write(folder / "code-review.json", proof)
    with pytest.raises(ValueError, match="hash_mismatch"):
        controller.artifact(tmp_path, tmp_path, item, "python")
    proof["generated_sha256"] = status["generated_sha256"]
    write(folder / "code-review.json", proof)
    source, expected, execution_review = controller.artifact(tmp_path, tmp_path, item, "python")
    assert source == code
    assert expected == status["generated_sha256"]
    assert execution_review["generated_code_review_sha256"] == sha((folder / "code-review.json").read_bytes())


def test_pine_does_not_treat_fixed_symbol_metadata_as_actual_bybit_metadata(tmp_path):
    item = reviewed(tmp_path)
    source = '//@version=5\nindicator("meta")\nx=syminfo . mintick\nplot(x)\n'
    (tmp_path / item["source_file"]).write_text(source)
    digest = sha(source.encode())
    write(tmp_path / "source_receipts/Abcd1234.json", {"source_sha256": digest})
    review = read(tmp_path / "reviews/Abcd1234.json")
    review["source_sha256"] = digest
    write(tmp_path / "reviews/Abcd1234.json", review)
    with pytest.raises(ValueError, match="pine_market_context_unavailable"):
        controller.artifact(tmp_path, tmp_path, item, "pine")
    source = '//@version=5\nindicator("syminfo.mintick")\n// syminfo.mintick\nplot(close)\n'
    (tmp_path / item["source_file"]).write_text(source)
    digest = sha(source.encode())
    write(tmp_path / "source_receipts/Abcd1234.json", {"source_sha256": digest})
    review["source_sha256"] = digest
    write(tmp_path / "reviews/Abcd1234.json", review)
    with pytest.raises(ValueError, match="reviewed_pine_executable_missing"):
        controller.artifact(tmp_path, tmp_path, item, "pine")


@pytest.mark.parametrize("corruption", ("missing", "modified"))
def test_declared_market_context_is_checked_instead_of_trusting_the_review_text(tmp_path, corruption):
    item = reviewed(tmp_path)
    original, original_hash, review = generation.reviewed_source(tmp_path, item)
    folder = tmp_path / "generation/Abcd1234/0"
    folder.mkdir(parents=True)
    code = "def on_bar(ctx, state):\n return {'action': 'hold'}\n"
    (folder / "source.py").write_text(code)
    generated_hash = sha(code.encode())
    write(tmp_path / "generation/Abcd1234/status.json", {
        "status": "completed", "attempt": 0, "source_sha256": original_hash,
        "generated_file": "generation/Abcd1234/0/source.py", "generated_sha256": generated_hash,
        "input_hash": identity({"source": original, "signal_bindings": review["signal_bindings"],
                                "inputs": {}, "signal_mode": "shared_events"}),
    })
    market = tmp_path / "market-context.json"
    write(market, {"tick_size": "0.10", "historical_rule_invariance_verified": False})
    market_hash = sha(market.read_bytes())
    write(folder / "code-review.json", {
        "status": "reviewed_for_isolated_execution", "reviewer": "independent-review",
        "original_source_sha256": original_hash, "generated_sha256": generated_hash,
        "market_context_file": "market-context.json", "market_context_sha256": market_hash,
    })
    _, _, execution_review = controller.artifact(tmp_path, tmp_path, item, "python")
    assert execution_review["market_context_proof"] == {"file": "market-context.json", "sha256": market_hash}
    if corruption == "missing":
        market.unlink()
    else:
        write(market, {"tick_size": "0.01"})
    with pytest.raises(ValueError, match="원자료"):
        controller.artifact(tmp_path, tmp_path, item, "python")


def test_pine_executable_keeps_the_exact_crlf_bytes_pinned_by_its_hash(tmp_path):
    item = reviewed(tmp_path)
    code = b"//@version=5\r\nstrategy('example')\r\nplot(close)\r\n"
    path = tmp_path / "adapted/Abcd1234.pine"
    path.parent.mkdir()
    path.write_bytes(code)
    review = read(tmp_path / "reviews/Abcd1234.json")
    review.update(adapted_file="adapted/Abcd1234.pine", adapted_sha256=sha(code))
    write(tmp_path / "reviews/Abcd1234.json", review)
    source, expected, _ = controller.artifact(tmp_path, tmp_path, item, "pine")
    assert source.encode() == code
    assert sha(source.encode()) == expected
