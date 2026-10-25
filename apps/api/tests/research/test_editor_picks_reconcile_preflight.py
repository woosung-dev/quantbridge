"""Pine 정적 거절은 실제 증거와 동결 선택을 대조하고 native 통과로 승격하지 않는다."""

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


def rejected_matrix(tmp_path, monkeypatch, statuses=("unsupported",)):
    items, jobs = [], []
    for index, status in enumerate(statuses):
        identifier = f"source{index:03}"
        source = f"//@version=5\nindicator('{identifier}')\nplot(close)\n".encode()
        relative = f"sources/{identifier}.pine"
        (tmp_path / relative).parent.mkdir(exist_ok=True)
        (tmp_path / relative).write_bytes(source)
        evidence = f"screening/{identifier}.json"
        write(
            tmp_path / evidence,
            {
                "id": identifier,
                "status": status,
                "source_sha256": sha(source),
                "detail": "trusted static fixture",
            },
        )
        proof = {
            "status": status,
            "source_sha256": sha(source),
            "evidence_file": evidence,
            "evidence_sha256": sha((tmp_path / evidence).read_bytes()),
        }
        items.append(
            {
                "id": identifier,
                "source_file": relative,
                "source_sha256": sha(source),
                "pine_preflight": proof,
                "warmup_bars": 1000,
            }
        )
        jobs.extend(
            {"id": identifier, "arm": arm, "timeframe": tf, "months": months, "scenario": scenario}
            for arm, tf, months, scenario in itertools.product(ARMS, TIMEFRAMES, PERIODS, SCENARIOS)
        )
    write(tmp_path / "cohort.json", {"target": len(items), "items": items})
    write(tmp_path / "data/dataset.json", {"trusted": "no market prices"})
    frozen = {
        "phase": "full",
        "jobs": jobs,
        "cohort_file": "cohort.json",
        "cohort_sha256": sha((tmp_path / "cohort.json").read_bytes()),
        "dataset_sha256": sha((tmp_path / "data/dataset.json").read_bytes()),
        "implementation": {},
        "artifacts": {
            item["id"]: {
                "pine": {"preflight_failure": item["pine_preflight"]},
                "terra": {"language": "python", "source_sha256": "f" * 64},
                "gemini": {"unavailable_reason": "completed_generation_missing"},
            }
            for item in items
        },
    }
    path = tmp_path / "full-plan.json"
    write(path, frozen)
    for item in items:
        write(
            tmp_path / f"native-checks/{item['id']}.json",
            {
                "id": item["id"],
                "source_sha256": item["source_sha256"],
                "plan_sha256": identity(frozen),
                "images": {"pine": "p", "python": "y"},
                # 부정확한 원시 통과 플래그가 있더라도 정적 거절을 통과로 승격하면 안 된다.
                "arms": {arm: {"native_prefix_repeat_passed": True} for arm in ARMS},
            },
        )
    monkeypatch.setattr(v, "implementation", lambda: {})
    monkeypatch.setattr(v, "receipts", lambda *_: {})

    def artifact(_, item, arm):
        assert arm == "terra", "정적 거절 Pine 또는 미확보 Gemini 원문을 읽으면 안 됩니다"
        return "trusted synthetic source", "python", "f" * 64

    def no_native(*_):
        raise ValueError("trusted_native_unavailable")

    monkeypatch.setattr(v, "artifact", artifact)
    monkeypatch.setattr(v, "native_export_gate", no_native)
    return path, frozen, items


def refreeze(tmp_path, path, frozen):
    write(path, frozen)
    for raw_path in (tmp_path / "native-checks").glob("*.json"):
        raw = read(raw_path)
        raw["plan_sha256"] = identity(frozen)
        write(raw_path, raw)


def test_actual_reconcile_preserves_all_148_static_failure_denominators(tmp_path, monkeypatch):
    statuses = ["unsupported"] * 133 + ["parser_timeout"] * 11 + ["screen_failed"] * 4
    path, _, items = rejected_matrix(tmp_path, monkeypatch, statuses)
    before = {
        item["id"]: (tmp_path / f"native-checks/{item['id']}.json").read_bytes() for item in items
    }
    assert v.reconcile(tmp_path, path) == {"source_count": 148, "passed_arms": 0}
    for item in items:
        result = read(tmp_path / f"verification/{item['id']}.json")
        assert result["arms"]["pine"] == {
            "status": "incomplete",
            "exact_economic_cells": 0,
            "expected_economic_cells": 36,
            "native_prefix_repeat_passed": False,
            "native_gate_error": f"pine_static_preflight_failed:{item['pine_preflight']['status']}",
        }
        assert result["arms"]["gemini"]["native_gate_error"] == "completed_generation_missing"
        assert result["arms"]["gemini"]["status"] == "incomplete"
        assert (tmp_path / f"native-checks/{item['id']}.json").read_bytes() == before[item["id"]]


@pytest.mark.parametrize(
    "mutation",
    [
        "selection_status",
        "selection_extra",
        "source_bytes",
        "evidence_bytes",
        "cohort_proof",
        "terra_preflight",
        "gemini_preflight",
    ],
)
def test_reconcile_rejects_changed_preflight_or_wrong_arm(tmp_path, monkeypatch, mutation):
    path, frozen, items = rejected_matrix(tmp_path, monkeypatch)
    item = items[0]
    selection = frozen["artifacts"][item["id"]]["pine"]
    if mutation == "selection_status":
        selection["preflight_failure"] = {
            **selection["preflight_failure"],
            "status": "screen_failed",
        }
    elif mutation == "selection_extra":
        selection["unavailable_reason"] = "should not be accepted"
    elif mutation == "source_bytes":
        (tmp_path / item["source_file"]).write_bytes(b"changed original")
    elif mutation == "evidence_bytes":
        (tmp_path / item["pine_preflight"]["evidence_file"]).write_bytes(b"{}")
    elif mutation == "cohort_proof":
        cohort = read(tmp_path / "cohort.json")
        cohort["items"][0]["pine_preflight"]["source_sha256"] = "wrong"
        write(tmp_path / "cohort.json", cohort)
        frozen["cohort_sha256"] = sha((tmp_path / "cohort.json").read_bytes())
    else:
        arm = mutation.split("_")[0]
        frozen["artifacts"][item["id"]][arm] = selection
    refreeze(tmp_path, path, frozen)
    with pytest.raises(ValueError):
        v.reconcile(tmp_path, path)


def test_preflight_exact_count_is_zero_even_if_economic_lookup_reports_36(tmp_path, monkeypatch):
    path, _, _ = rejected_matrix(tmp_path, monkeypatch)
    monkeypatch.setattr(v, "exact_cells", lambda *_: 36)
    assert v.reconcile(tmp_path, path)["passed_arms"] == 0
    result = read(tmp_path / "verification/source000.json")["arms"]["pine"]
    assert result["exact_economic_cells"] == 0
    assert result["native_prefix_repeat_passed"] is False
    assert result["status"] == "incomplete"
