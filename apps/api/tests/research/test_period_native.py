"""부분창 native 증거의 거절·경로별 판정을 검증한다. DB·전략 실행 미사용."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import period_native as native
from tools.research.period_study.state import read, sha, write

from scripts.pine_validation.models import SignalEvent
from scripts.pine_validation.native_capture import NativeCapture
from tests.scripts.test_pine_validation_native_capture import BINDINGS, SOURCE, _payload


@pytest.fixture
def study(tmp_path: Path) -> tuple[Path, dict]:
    item = {
        "id": "example",
        "source_file": "sources/example.pine",
        "review_file": "reviews/example.json",
    }
    (tmp_path / "sources").mkdir()
    (tmp_path / item["source_file"]).write_text(SOURCE)
    digest = sha(SOURCE.encode())
    write(tmp_path / "catalogue.json", {"items": [item]})
    write(tmp_path / "source_receipts/example.json", {"source_sha256": digest})
    write(
        tmp_path / item["review_file"],
        {
            "source_sha256": digest,
            "reviewer": "test-reviewer",
            "basis": "테스트 원문의 명시 alertcondition 대조",
            "signal_bindings": BINDINGS,
            "inputs": {},
            "signal_mode": "shared_events",
            "warmup_bars": 1,
        },
    )
    return tmp_path, item


def capture() -> NativeCapture:
    index = pd.date_range("2025-12-24", periods=4, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1}, index=index
    )
    return NativeCapture(
        observations=pd.DataFrame({"probe": range(4)}, index=index),
        ohlcv=frame,
        events=[SignalEvent(index[1], "long"), SignalEvent(index[2], "short")],
        metadata={
            "timeframe": "1h",
            "observed_at": "2025-12-24T04:00:00+00:00",
            "common_bars": 4,
            "study_bars": 4,
            "ohlcv_bars": 4,
        },
    )


def probe_payload() -> dict:
    return {
        "compiled_source": SOURCE + '\nplot(bar_index, "__QB_BAR_INDEX__", display=display.none)\n',
        "compile_responses": [
            {
                "data": {
                    "result": {
                        "metaInfo": {
                            "styles": {"probe": {"title": native.PROBE_TITLE}},
                        }
                    }
                }
            }
        ],
    }


def prepared(study, monkeypatch) -> tuple[Path, dict, NativeCapture]:
    root, item = study
    reference = capture()
    write(root / "native/example/1h.json", _payload())
    write(root / "native/example/1h-initialization.json", probe_payload())
    monkeypatch.setattr(native, "parse", lambda *args: reference)
    monkeypatch.setattr(native, "verify_initial_history", lambda *args: {"status": "verified"})
    return root, item, reference


def test_missing_native_evidence_never_starts_code_or_passes(study, monkeypatch):
    root, _ = study
    monkeypatch.setattr(native, "compare_path", lambda *args: pytest.fail("증거 없이 실행"))
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "unverified"
    assert result["evidence_verified"] is False
    assert result["evidence"] == []
    assert result["passed_paths"] == []
    assert all(value["status"] == "not_run" for value in result["paths"].values())
    assert read(root / "native-verification/example-1h.json") == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "other"),
        ("symbol", "BYBIT:ETHUSDT.P"),
        ("timeframe", "4h"),
        ("source_sha256", "a" * 64),
        ("compiled_source", SOURCE + "\n"),
        ("compile_request_source", SOURCE + "\n"),
        ("resolved_inputs", {"length": 3}),
        ("compile_responses", []),
        ("wire", []),
    ],
)
def test_unverified_raw_capture_is_rejected_before_either_code_path(
    study, monkeypatch, field, value
):
    root, _ = study
    payload = _payload()
    payload[field] = value
    write(root / "native/example/1h.json", payload)
    monkeypatch.setattr(
        native, "compare_path", lambda *args: pytest.fail("거절한 원시 증거로 실행")
    )
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "unverified"
    assert result["evidence_verified"] is False
    assert "raw_capture_verified" not in result
    assert result["passed_paths"] == []


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("prefix", "only_append_bar_index"),
        ("extra_signal", "only_append_bar_index"),
        ("first_bar", "first_bar_differs"),
        ("partial", "partial_cohort"),
        ("price", "ohlcv_differs"),
        ("events", "changes_original_events"),
        ("column", "column_missing_or_ambiguous"),
        ("index", "does_not_start_at_zero"),
    ],
)
def test_initial_history_rejects_modified_probe_or_incomplete_evidence(
    monkeypatch, mutation, reason
):
    original, probe, payload = capture(), capture(), probe_payload()
    if mutation == "prefix":
        payload["compiled_source"] = payload["compiled_source"].replace(
            'indicator("demo")', 'indicator("changed")'
        )
    elif mutation == "extra_signal":
        payload["compiled_source"] += 'alertcondition(close > open, title="New")\n'
    elif mutation == "first_bar":
        probe = replace(probe, ohlcv=probe.ohlcv.iloc[1:])
    elif mutation == "partial":
        probe.metadata["study_bars"] += 1
    elif mutation == "price":
        probe.ohlcv.iloc[1, probe.ohlcv.columns.get_loc("close")] = 101
    elif mutation == "events":
        probe = replace(probe, events=probe.events[:1])
    elif mutation == "column":
        payload["compile_responses"][0]["data"]["result"]["metaInfo"]["styles"]["duplicate"] = {
            "title": native.PROBE_TITLE
        }
    elif mutation == "index":
        probe.observations["probe"] += 10
    monkeypatch.setattr(native, "parse", lambda *args: probe)
    with pytest.raises(ValueError, match=reason):
        native.verify_initial_history(original, SOURCE.encode(), payload, {}, "example", "1h")


def test_initial_history_is_proven_by_a_separate_append_only_probe(monkeypatch):
    reference = capture()
    monkeypatch.setattr(native, "parse", lambda *args: reference)
    result = native.verify_initial_history(
        reference, SOURCE.encode(), probe_payload(), {}, "example", "1h"
    )
    assert result["status"] == "verified"
    assert result["first_bar_index"] == 0
    assert result["probe_is_unmodified_original"] is False


@pytest.mark.parametrize("bad_phase", ["repeat", "prefix"])
def test_native_exact_is_insufficient_when_repeat_or_prefix_changes(study, monkeypatch, bad_phase):
    root, item = study
    reference = capture()
    monkeypatch.setattr(native, "artifact", lambda *args: ("never executed", "a" * 64, {}))
    monkeypatch.setattr(native, "image_identity", lambda path: "sha256:" + "b" * 64)

    def actions(source, path, frame, params, phase):
        value = ["hold", "long", "short", "hold"][: len(frame)]
        if phase == bad_phase:
            value[1] = "hold"
        return value

    monkeypatch.setattr(native, "collect", actions)
    result = native.compare_path(
        root, item, "python", reference, native.event_keys(reference.events), 1
    )
    assert result["native_exact"] is True
    assert result["status"] == "mismatch"
    assert result[bad_phase] is False
    assert set(result["passes"]) == {"full", "repeat", "prefix"}
    assert result["passes"]["full"]["bars"] == 4
    assert result["passes"]["prefix"]["bars"] == 2
    assert all(value["elapsed_seconds"] >= 0 for value in result["passes"].values())


def test_one_direction_match_cannot_claim_native_pass(study, monkeypatch):
    root, item = study
    reference = capture()
    monkeypatch.setattr(native, "artifact", lambda *args: ("never executed", "a" * 64, {}))
    monkeypatch.setattr(native, "image_identity", lambda path: "sha256:" + "b" * 64)
    monkeypatch.setattr(
        native,
        "collect",
        lambda source, path, frame, params, phase: ["hold", "long", "hold", "hold"][: len(frame)],
    )
    result = native.compare_path(
        root, item, "python", reference, native.event_keys(reference.events[:1]), 1
    )
    assert result["native_exact"] is True
    assert result["both_directions"] is False
    assert result["status"] == "mismatch"


def test_isolated_execution_failure_remains_an_attempted_failure(study, monkeypatch):
    root, item = study
    monkeypatch.setattr(native, "artifact", lambda *args: ("never executed", "a" * 64, {}))
    monkeypatch.setattr(native, "image_identity", lambda path: "sha256:" + "b" * 64)

    def failed(*args):
        raise RuntimeError("isolated worker failed")

    monkeypatch.setattr(native, "collect", failed)
    result = native.compare_path(root, item, "python", capture(), [], 1)
    assert result["status"] == "failed"
    assert result["execution_attempted"] is True
    assert result["failed_phase"] == "full"
    assert result["completed_passes"] == []


def test_market_context_guard_only_blocks_pine(study, monkeypatch):
    root, item = study
    monkeypatch.setattr(
        native, "reviewed_source", lambda *args: ("tick = syminfo . mintick", "a" * 64, {})
    )
    monkeypatch.setattr(native, "artifact", lambda *args: ("never executed", "a" * 64, {}))
    monkeypatch.setattr(native, "image_identity", lambda path: "sha256:" + "b" * 64)
    monkeypatch.setattr(
        native,
        "collect",
        lambda source, path, frame, params, phase: ["hold", "long", "short", "hold"][: len(frame)],
    )
    reference = capture()
    events = native.event_keys(reference.events)
    pine = native.compare_path(root, item, "pine", reference, events, 1)
    assert pine["status"] == "not_run"
    assert pine["reason"] == "unsupported_market_context"
    assert native.compare_path(root, item, "python", reference, events, 1)["status"] == "passed"


def test_success_in_one_code_path_never_promotes_the_other(study, monkeypatch):
    root, _, _ = prepared(study, monkeypatch)
    monkeypatch.setattr(
        native,
        "compare_path",
        lambda root, item, path, *args: {
            "status": "passed" if path == "python" else "not_run",
        },
    )
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "passed"
    assert result["evidence_verified"] is True
    assert result["passed_paths"] == ["python"]
    assert result["paths"]["pine"]["status"] == "not_run"
    assert len(result["evidence"]) == 3


@pytest.mark.parametrize("selected", [("pine",), ("python",)])
def test_policy_selection_never_executes_an_unneeded_native_path(study, monkeypatch, selected):
    root, _, _ = prepared(study, monkeypatch)
    called = []
    monkeypatch.setattr(native, "native_code_paths", lambda *args: selected)

    def compare(root, item, path, *args):
        called.append(path)
        return {"status": "passed"}

    monkeypatch.setattr(native, "compare_path", compare)
    result = native.verify(root, "example", "1h", None)

    assert called == list(selected)
    assert result["passed_paths"] == list(selected)
    omitted = "python" if selected == ("pine",) else "pine"
    assert result["paths"][omitted] == {
        "status": "not_run",
        "reason": "pine_first_policy_path_not_required",
        "execution_attempted": False,
    }


def test_unobserved_position_feedback_never_enters_strict_native_comparison(study, monkeypatch):
    root, item, _ = prepared(study, monkeypatch)
    review = read(root / item["review_file"])
    review["signal_mode"] = "position_feedback"
    write(root / item["review_file"], review)
    monkeypatch.setattr(native, "compare_path", lambda *args: pytest.fail("포지션 증거 없이 실행"))
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "unverified"
    assert result["passed_paths"] == []
    assert "native_policy_position_feedback_not_observed" in result["reason"]


def test_evidence_changed_during_execution_revokes_all_path_passes(study, monkeypatch):
    root, _, _ = prepared(study, monkeypatch)

    def changed(*args):
        (root / "native/example/1h.json").write_text("changed after proof")
        return {"status": "passed"}

    monkeypatch.setattr(native, "compare_path", changed)
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "unverified"
    assert result["evidence_verified"] is False
    assert result["passed_paths"] == []
    assert all(value["status"] == "unverified" for value in result["paths"].values())
    assert all(
        value["reason"] == "native_evidence_chain_changed" for value in result["paths"].values()
    )
    assert "SHA" in result["reason"]


def test_native_request_binds_the_exact_generated_code_approval(study, monkeypatch):
    root, _, _ = prepared(study, monkeypatch)
    review_path = root / "generation/example/0/code-review.json"
    write(root / "generation/example/status.json", {"attempt": 0})
    write(review_path, {"reviewer": "first"})
    monkeypatch.setattr(
        native,
        "artifact",
        lambda *args: (
            "never executed",
            "a" * 64,
            {"generated_code_review_sha256": sha(review_path.read_bytes())},
        ),
    )
    monkeypatch.setattr(native, "image_identity", lambda path: "sha256:" + "b" * 64)
    monkeypatch.setattr(
        native,
        "collect",
        lambda source, path, frame, params, phase: ["hold", "long", "short", "hold"][: len(frame)],
    )
    real_compare = native.compare_path

    def compare(root, item, path, *args):
        return real_compare(root, item, path, *args) if path == "python" else {"status": "not_run"}

    monkeypatch.setattr(native, "compare_path", compare)
    first = native.verify(root, "example", "1h", None)
    assert first["status"] == "passed"
    assert first["evidence"][-1] == {
        "path": "generation/example/0/code-review.json",
        "sha256": sha(review_path.read_bytes()),
    }
    write(review_path, {"reviewer": "second"})
    second = native.verify(root, "example", "1h", None)
    assert first["request_hash"] != second["request_hash"]
    assert first["paths"]["python"]["source_hash"] == second["paths"]["python"]["source_hash"]
    assert (
        first["paths"]["python"]["generated_code_review_sha256"]
        != second["paths"]["python"]["generated_code_review_sha256"]
    )


def test_generated_code_approval_changed_during_execution_revokes_native_pass(study, monkeypatch):
    root, _, _ = prepared(study, monkeypatch)
    review_path = root / "generation/example/0/code-review.json"
    write(root / "generation/example/status.json", {"attempt": 0})
    write(review_path, {"reviewer": "first"})
    digest = sha(review_path.read_bytes())
    monkeypatch.setattr(
        native,
        "artifact",
        lambda *args: (
            "never executed",
            "a" * 64,
            {"generated_code_review_sha256": digest},
        ),
    )
    monkeypatch.setattr(native, "image_identity", lambda path: "sha256:" + "b" * 64)

    def actions(source, path, frame, params, phase):
        write(review_path, {"reviewer": "changed during execution"})
        return ["hold", "long", "short", "hold"][: len(frame)]

    monkeypatch.setattr(native, "collect", actions)
    real_compare = native.compare_path
    monkeypatch.setattr(
        native,
        "compare_path",
        lambda root, item, path, *args: (
            real_compare(root, item, path, *args) if path == "python" else {"status": "not_run"}
        ),
    )
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "unverified"
    assert result["evidence_verified"] is False
    assert result["paths"]["python"]["status"] == "unverified"
    assert "SHA" in result["reason"]


def test_source_review_changed_during_execution_cannot_relabel_native_pass(study, monkeypatch):
    root, item, _ = prepared(study, monkeypatch)
    file = root / item["review_file"]
    start_hash = sha(file.read_bytes())

    def changed(*args):
        review = read(file)
        review["inputs"] = {"length": 3}
        write(file, review)
        return {"status": "passed"}

    monkeypatch.setattr(native, "compare_path", changed)
    result = native.verify(root, "example", "1h", None)
    assert result["status"] == "unverified"
    assert result["evidence_verified"] is False
    assert result["source_review_sha256"] == start_hash
    assert any(
        value == {"path": item["review_file"], "sha256": start_hash} for value in result["evidence"]
    )
    assert result["passed_paths"] == []
    assert all(value["status"] == "unverified" for value in result["paths"].values())
    assert "SHA" in result["reason"]
