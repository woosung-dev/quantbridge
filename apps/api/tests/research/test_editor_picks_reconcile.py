"""불변 원시 native 증거와 경제 36셀을 별도 단계에서 결합한다."""

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import verification as v
from tools.research.editor_picks.common import (
    ARMS,
    PERIODS,
    SCENARIOS,
    TIMEFRAMES,
    identity,
    read,
    sha,
    write,
)


def evidence(tmp_path, monkeypatch):
    item = {
        "id": "one", "source_sha256": "original", "warmup_bars": 1000,
        "url": "https://www.tradingview.com/script/one/", "author": "author",
        "title": "Original", "license_notices": [],
    }
    jobs = [
        {"id": "one", "arm": arm, "timeframe": tf, "months": months, "scenario": cost}
        for arm, tf, months, cost in itertools.product(ARMS, TIMEFRAMES, PERIODS, SCENARIOS)
    ]
    selected = {
        "pine": {"language": "pine", "source_sha256": "code-pine"},
        "terra": {"language": "python", "source_sha256": "code-terra"},
        "gemini": {"unavailable_reason": "not_generated"},
    }
    frozen = {
        "phase": "full", "jobs": jobs, "artifacts": {"one": selected},
        "policy": "swing_two_bar_v1",
    }
    path = tmp_path / "full-plan.json"
    write(path, frozen)
    images = {"pine": "pine-image", "python": "python-image"}
    completed = {
        identity(job): {
            "status": "completed", "action_sha256": "actions",
            "ledger_sha256": "ledger", "execution_images": images,
        }
        for job in jobs if job["arm"] != "gemini"
    }
    windows = {}
    for tf in TIMEFRAMES:
        capture = tmp_path / "native/one" / f"{tf}.json"
        write(capture, {"raw": tf})
        windows[tf] = {
            "status": "checked_partial_window", "capture_sha256": sha(capture.read_bytes()),
            "warmup_bars": 1000, "bars": 1500, "checked_bars": 500,
            "checks": {arm: {
                "passed": True, "source_sha256": f"code-{arm}", "prefix_bars": 1333,
            } for arm in ("pine", "terra")},
        }
    raw = {
        "id": "one", "source_sha256": "original", "plan_sha256": identity(frozen),
        "images": images, "native_windows": windows,
        "arms": {arm: {
            "status": "incomplete", "native_prefix_repeat_passed": arm != "gemini",
            "exact_economic_cells": 0,
        } for arm in ARMS},
    }
    write(tmp_path / "native-checks/one.json", raw)
    monkeypatch.setattr(v, "frozen_inputs", lambda *_: {"items": [item]})
    monkeypatch.setattr(v, "receipts", lambda *_: completed)
    monkeypatch.setattr(v, "artifact", lambda _, __, arm: (
        "source", selected[arm]["language"], selected[arm]["source_sha256"]
    ))
    return path, frozen, completed


def test_reconciliation_preserves_raw_proof_and_requires_all_economic_cells(tmp_path, monkeypatch):
    path, frozen, completed = evidence(tmp_path, monkeypatch)
    raw_path = tmp_path / "native-checks/one.json"
    before = raw_path.read_bytes()
    assert v.reconcile(tmp_path, path)["passed_arms"] == 2
    derived = read(tmp_path / "verification/one.json")
    assert derived["arms"]["terra"]["exact_economic_cells"] == 36
    assert derived["native_check_sha256"] == sha(before)
    assert raw_path.read_bytes() == before
    terra = next(job for job in frozen["jobs"] if job["arm"] == "terra")
    completed.pop(identity(terra))
    assert v.reconcile(tmp_path, path)["passed_arms"] == 1
    assert read(tmp_path / "verification/one.json")["arms"]["terra"]["status"] == "incomplete"


def test_changed_native_capture_cannot_pass_reconciliation(tmp_path, monkeypatch):
    path, _, _ = evidence(tmp_path, monkeypatch)
    write(tmp_path / "native/one/1h.json", {"changed": True})
    assert v.reconcile(tmp_path, path)["passed_arms"] == 0


def test_other_plan_native_proof_is_rejected(tmp_path, monkeypatch):
    path, _, _ = evidence(tmp_path, monkeypatch)
    raw_path = tmp_path / "native-checks/one.json"
    raw = read(raw_path)
    raw["plan_sha256"] = "another-plan"
    write(raw_path, raw)
    with pytest.raises(ValueError, match="원문·계획"):
        v.reconcile(tmp_path, path)


def test_registration_keeps_futures_settings_and_model_reporting_honest(tmp_path, monkeypatch):
    path, _, _ = evidence(tmp_path, monkeypatch)
    v.reconcile(tmp_path, path)
    assert v.export(tmp_path, path)["count"] == 2
    requests = read(tmp_path / "registration/requests.json")["requests"]
    for request in requests:
        assert request["settings"] == {
            "schema_version": 1, "leverage": 1, "margin_mode": "isolated",
            "position_size_pct": 100.0, "fill_timing": "next_bar_open",
            "max_trigger_breach_pct": None, "max_reversal_overshoot_ratio": None,
        }
        metadata = request["code"]["provenance"]
        assert metadata["actual_model"] is None
        assert metadata["research_assumptions"]["risk_policy"] == "swing_two_bar_v1"
        assert metadata["research_assumptions"]["fees"] == "0.00055"
    assert requests[1]["code"]["provenance"]["requested_model"] == "gpt-5.6-terra"
