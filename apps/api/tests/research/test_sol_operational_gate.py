"""수동 fake clock/transport만 사용한다. native·DB·주문·모델 실행 증거가 아니다."""

import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tools.research import sol_operational_gate as gate

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_live_replay import input_hash
from src.strategy.python_runtime.protocol import PythonRunnerTimeout


@pytest.fixture
def code():
    return CodeSnapshot(
        execution_policy="code_v1",
        language="python",
        source_code="def on_bar(ctx,state):\n return {'action':'hold'}\n",
        warmup_bars=1,
        provenance={},
    )


@pytest.fixture
def quality_code(code):
    return code.model_copy(update={"warmup_bars": 200})


def payload(code):
    result = []
    for index in range(max(3, code.warmup_bars + 1)):
        bar = {
            "index": index,
            "timestamp": (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=index)).isoformat(),
            "open": "100",
            "high": "101",
            "low": "99",
            "close": "100",
            "volume": "1",
        }
        warmup = index < code.warmup_bars
        result.append(
            {
                "sequence": index,
                "execution_hash": code.execution_hash,
                "input_hash": input_hash(code.execution_hash, bar, gate.FLAT, is_warmup=warmup),
                "bar": bar,
                "position": dict(gate.FLAT),
                "delivery_args": {},
                "is_warmup": warmup,
                "intent": "hold",
                "status": "warmup" if warmup else "delivered",
            }
        )
    return result


class Clock:
    value = 0

    def __call__(self):
        return self.value

    def add(self, value):
        self.value += value


class Transport:
    name = "own-development-guest"
    image_id = "sha256:" + "a" * 64

    def __init__(self, clock, *, init=1, bar=1, close=1, fail=None):
        self.clock, self.init, self.bar, self.cleanup, self.fail = clock, init, bar, close, fail
        self.bars, self.closed = 0, False

    def exchange(self, message):
        stage = message["type"]
        self.clock.add(self.init if stage == "init" else self.bar)
        if self.fail == stage or self.fail == self.bars:
            raise PythonRunnerTimeout("manual test timeout")
        if stage == "bar":
            self.bars += 1
            return {"intent": {"action": "hold"}}
        return {"ready": 1}

    def close(self):
        self.closed = True
        self.clock.add(self.cleanup)


def measure(code, **kwargs):
    clock = Clock()
    transport = Transport(clock, **kwargs)

    def factory():
        clock.add(2)
        return transport

    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, payload(code)),
        expected_image_id=transport.image_id,
        clock=clock,
        transport_factory=factory,
        removed_probe=lambda name: True,
    )
    return result, transport


def test_full_timing_and_test_double_are_explicit(code):
    result, transport = measure(code)
    assert result["status"] == "PASS" and result["elapsed_seconds"] == 7
    assert result["construct_seconds"] == 2 and result["init_seconds"] == 1
    assert result["bars_seconds"] == 3 and result["cleanup_seconds"] == 1
    assert result["completed_bar_replies"] == 3 and transport.closed
    assert result["last_observed_phase"] == "close" and result["failure_phase"] is None
    assert result["execution_backend"] == "injected_test_transport"
    assert result["native_executed"] is False


def test_successful_transport_but_total_including_cleanup_exceeds_30_fails(code):
    result, transport = measure(code, init=25, bar=0, close=4)
    assert result["status"] == "FAIL" and result["elapsed_seconds"] == 31
    assert result["error_type"] == "total_wall_budget_exceeded" and transport.closed
    assert result["failure_phase"] == "total_gate"


@pytest.mark.parametrize("failure,completed,phase", [("init", 0, "init"), (1, 1, "bar")])
def test_timeout_retains_partial_denominator_and_cleans_up(code, failure, completed, phase):
    result, transport = measure(code, fail=failure)
    assert result["status"] == "FAIL" and result["error_type"] == "PythonRunnerTimeout"
    assert result["input_bars"] == 3 and result["completed_bar_replies"] == completed
    assert result["last_observed_phase"] == "close" and transport.closed
    assert result["failure_phase"] == phase


def test_missing_recovery_stays_unknown_without_starting_transport(code):
    factory = Mock(side_effect=AssertionError("must not execute"))
    result = gate.measure_profile(code, None, expected_image_id="none", transport_factory=factory)
    assert result["status"] == "UNKNOWN" and result["native_executed"] is False
    factory.assert_not_called()


def test_wrong_image_rejected_before_init_and_cleaned(code):
    clock = Clock()
    transport = Transport(clock)
    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, payload(code)),
        expected_image_id="wrong",
        clock=clock,
        transport_factory=lambda: transport,
        removed_probe=lambda _: True,
    )
    assert result["status"] == "FAIL" and result["error_type"] == "ValueError"
    assert result["completed_bar_replies"] == 0 and transport.closed
    assert result["last_observed_phase"] == "close" and result["failure_phase"] == "construct"


def test_unconfirmed_cleanup_never_passes(code):
    clock = Clock()
    transport = Transport(clock)
    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, payload(code)),
        expected_image_id=transport.image_id,
        clock=clock,
        transport_factory=lambda: transport,
        removed_probe=lambda _: False,
    )
    assert result["status"] == "FAIL" and result["error_type"] == "cleanup_unconfirmed"
    assert result["last_observed_phase"] == result["failure_phase"] == "close"


@pytest.mark.parametrize("mutation", ["position", "hash", "gap", "warmup", "extra"])
def test_checkpoint_export_changes_fail_closed(code, mutation):
    values = deepcopy(payload(code))
    if mutation == "position":
        values[-1]["position"] = {"direction": "long", "size": "1", "average_price": "100"}
    elif mutation == "hash":
        values[-1]["execution_hash"] = "b" * 64
    elif mutation == "gap":
        values[-1]["bar"]["timestamp"] = "2026-01-02T00:00:00+00:00"
    elif mutation == "warmup":
        values[-1]["is_warmup"] = True
    else:
        values[-1]["account_id"] = "private"
    with pytest.raises(ValueError):
        gate.records_from_payload(code, values)


@pytest.fixture
def bound_inputs(tmp_path, quality_code, monkeypatch):
    code = quality_code
    import pandas as pd
    from tools.research.data import json_write

    source = tmp_path / "source.txt"
    source.write_text(code.source_code)
    paths = {
        name: tmp_path / (name + ".json")
        for name in ("artifacts", "selection", "code", "environment", "snapshot")
    }
    json_write(
        paths["artifacts"],
        [
            {
                "case_id": "01",
                "arm": "A",
                "language": "python",
                "repetition": 2,
                "source_path": source.name,
                "source_hash": code.source_hash,
            }
        ],
    )
    json_write(paths["code"], code.model_dump(mode="json"))
    json_write(paths["environment"], {})
    paths["selection"].write_text("{}")
    paths["snapshot"].write_text("{}")
    selection = Mock(return_value={"manifest_sha256": gate.digest(paths["environment"])})
    monkeypatch.setattr(gate, "validate_selection", selection)
    monkeypatch.setattr(
        gate,
        "runtime_binding",
        lambda _: {"image_ids": {gate.IMAGES["python"]: "sha256:" + "a" * 64}},
    )
    monkeypatch.setattr(gate, "load_snapshot", lambda _: {"snapshot_id": "fixture-data"})
    frame = pd.DataFrame(
        [
            {key: row["bar"][key] for key in ("open", "high", "low", "close", "volume")}
            for row in payload(code)
        ],
        index=pd.date_range("2026-01-01", periods=code.warmup_bars + 1, freq="h", tz="UTC"),
    )
    monkeypatch.setattr(gate, "load_economic_cell", lambda *a, **kw: (frame, None, None))
    kwargs = {
        "artifacts_path": paths["artifacts"],
        "selection_path": paths["selection"],
        "case_id": "01",
        "code_path": paths["code"],
        "execution_hash": code.execution_hash,
        "environment_path": paths["environment"],
        "snapshot_path": paths["snapshot"],
        "symbol": "BTCUSDT",
        "start": "2026-01-01T01:00:00+00:00",
    }
    return kwargs, selection


def test_first_activation_uses_warmup_plus_one_flat_and_does_not_invent_observed_intents(
    bound_inputs, quality_code
):
    code = quality_code
    kwargs, validator = bound_inputs
    _, profiles, proof = gate.load_inputs(**kwargs)
    validator.assert_called_once()
    assert proof["first_pass_repetition"] == 2 and proof["source_hash"] == code.source_hash
    assert len(profiles["first_activation_flat"]) == code.warmup_bars + 1
    assert all(
        row.position == gate.FLAT and row.intent == "" for row in profiles["first_activation_flat"]
    )
    assert profiles["observed_checkpoint"] is None


@pytest.mark.parametrize("failure", ["selection", "source", "execution", "manifest"])
def test_locked_selection_source_version_environment_fail_before_execution(
    bound_inputs, quality_code, failure
):
    code = quality_code
    kwargs, validator = bound_inputs
    if failure == "selection":
        validator.side_effect = ValueError("not the first semantic pass")
    elif failure == "source":
        value = code.model_dump(mode="json")
        value["source_code"] += "# altered\n"
        kwargs["code_path"].write_text(__import__("json").dumps(value))
    elif failure == "execution":
        kwargs["execution_hash"] = "f" * 64
    else:
        validator.return_value["manifest_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        gate.load_inputs(**kwargs)


def test_observed_checkpoint_preserves_actual_historical_position_and_hash_binding(
    bound_inputs, quality_code, tmp_path
):
    import json

    code = quality_code
    kwargs, _ = bound_inputs
    rows = payload(code)
    rows[-1]["position"] = {"direction": "short", "size": "0.5", "average_price": "100"}
    rows[-1]["input_hash"] = input_hash(
        code.execution_hash, rows[-1]["bar"], rows[-1]["position"], is_warmup=False
    )
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "origin": "persisted_live_code_bars",
                "source_hash": code.source_hash,
                "execution_hash": code.execution_hash,
                "snapshot_id": "fixture-data",
                "records": rows,
            }
        )
    )
    kwargs.update(checkpoint_path=checkpoint, checkpoint_sha256=gate.digest(checkpoint))
    _, profiles, proof = gate.load_inputs(**kwargs)
    assert profiles["observed_checkpoint"][-1].position["direction"] == "short"
    assert proof["checkpoint_file_sha256"] == gate.digest(checkpoint)
    checkpoint.write_text(checkpoint.read_text() + "\n")
    with pytest.raises(ValueError, match="SHA256"):
        gate.load_inputs(**kwargs)


def test_stored_intent_mismatch_is_failure_not_operational_pass(code):
    clock = Clock()
    rows = payload(code)
    rows[-1]["intent"] = "long"
    transport = Transport(clock)
    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, rows),
        expected_image_id=transport.image_id,
        transport_factory=lambda: transport,
        removed_probe=lambda _: True,
        clock=clock,
    )
    assert result["status"] == "FAIL" and result["error_type"] == "CodeRuntimeError"
    assert transport.closed


def test_constructor_timeout_keeps_unknown_container_identity(code):
    clock = Clock()

    def unavailable():
        clock.add(30)
        raise PythonRunnerTimeout("constructor failed")

    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, payload(code)),
        expected_image_id="sha256:" + "a" * 64,
        transport_factory=unavailable,
        removed_probe=lambda _: True,
        clock=clock,
    )
    assert result["status"] == "FAIL" and result["last_observed_phase"] == "construct"
    assert result["construct_seconds"] == 30 and result["completed_bar_replies"] == 0
    assert result["container_name"] is None and result["image_id"] is None


def test_cleanup_probe_failure_retains_original_timeout(code):
    clock = Clock()
    transport = Transport(clock, fail="init")

    def probe(_):
        raise TimeoutError("probe failed")

    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, payload(code)),
        expected_image_id=transport.image_id,
        transport_factory=lambda: transport,
        removed_probe=probe,
        clock=clock,
    )
    assert result["status"] == "FAIL" and result["error_type"] == "PythonRunnerTimeout"
    assert result["cleanup_error_type"] == "TimeoutError" and not result["cleanup_confirmed"]


def test_operator_interruption_is_separate_from_runtime_failure(code):
    clock = Clock()
    transport = Transport(clock)

    def exchange(_):
        raise KeyboardInterrupt

    transport.exchange = exchange
    result = gate.measure_profile(
        code,
        gate.records_from_payload(code, payload(code)),
        expected_image_id=transport.image_id,
        transport_factory=lambda: transport,
        removed_probe=lambda _: True,
        clock=clock,
    )
    assert result["status"] == "INTERRUPTED" and transport.closed


@pytest.mark.parametrize(
    "first_status,expected", [("PASS", "UNKNOWN"), ("INTERRUPTED", "INTERRUPTED")]
)
def test_overall_recovery_unknown_and_interrupt_does_not_start_next_profile(
    code, tmp_path, monkeypatch, first_status, expected
):
    import json

    profiles = {
        "first_activation_flat": gate.records_from_payload(code, payload(code)),
        "observed_checkpoint": None,
    }
    monkeypatch.setattr(
        gate, "load_inputs", lambda **kwargs: (code, profiles, {"expected_image_id": "image"})
    )
    measure = Mock(side_effect=[{"status": first_status}, {"status": "UNKNOWN"}])
    monkeypatch.setattr(gate, "measure_profile", measure)
    monkeypatch.setattr(gate, "output_dir", lambda _: tmp_path)
    args = ["operational-gate", "--execute"]
    for key in (
        "artifacts",
        "selection",
        "code-snapshot",
        "environment",
        "snapshot",
        "case-id",
        "execution-hash",
        "symbol",
        "start",
        "output",
    ):
        args.extend(["--" + key, "fixture"])
    monkeypatch.setattr(sys, "argv", args)
    gate.main()
    result = json.loads((tmp_path / "operational-gate.json").read_text())
    assert result["overall_status"] == expected
    assert measure.call_count == (1 if first_status == "INTERRUPTED" else 2)
    if first_status == "INTERRUPTED":
        assert result["profiles"]["observed_checkpoint"]["status"] == "NOT_RUN"


@pytest.mark.parametrize(
    "field,value", [("params", {"period": 3}), ("warmup_bars", 199), ("warmup_bars", 201)]
)
def test_source_matched_but_different_full_quality_inputs_rejected(
    bound_inputs, quality_code, field, value
):
    kwargs, _ = bound_inputs
    changed = quality_code.model_copy(update={field: value})
    kwargs["code_path"].write_text(changed.model_dump_json())
    # 새로운 execution hash까지 일치시켜도 품질 평가의 고정 입력과 달라 거부해야 한다.
    kwargs["execution_hash"] = changed.execution_hash
    with pytest.raises(ValueError, match=r"params=.*warmup_bars=200"):
        gate.load_inputs(**kwargs)
