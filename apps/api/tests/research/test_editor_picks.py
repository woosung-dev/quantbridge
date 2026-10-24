"""재현 비교의 실패 분모·구독 CLI 완료·입력 변조를 검증한다."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import catalogue, execution, generation  # noqa: E402
from tools.research.editor_picks.common import (  # noqa: E402
    cached,
    identity,
    immutable,
    receipt,
    sha,
    write,
)
from tools.research.editor_picks.dataset import aggregate_minutes, validate_minutes  # noqa: E402
from tools.research.editor_picks.report import (  # noqa: E402
    build,
    signal_quality,
)


def stream(response, *, status="SUCCESS", turns=1, tool=False):
    events = [{"event": "init", "init": {"model": "gemini-3.8-flash-high"}}]
    if tool:
        events.append({"event": "step_update", "step_update": {"step_type": "tool_call"}})
    events.append(
        {
            "event": "result",
            "result": {
                "status": status,
                "num_turns": turns,
                "response": response,
                "usage": {"output_tokens": 100},
            },
        }
    )
    return "\n".join(json.dumps(event) for event in events)


def test_gemini_single_completion_and_source_are_required():
    payload = {"source_code": 'def on_bar(ctx, state): return {"action":"hold"}', "assumptions": []}
    assert generation.parse_stream(stream(json.dumps(payload)), "gemini")[0] == payload
    for kwargs in ({"turns": 3}, {"status": "RUNNING"}, {"tool": True}):
        with pytest.raises(ValueError):
            generation.parse_stream(stream(json.dumps(payload), **kwargs), "gemini")
    with pytest.raises(ValueError):
        generation.parse_stream(stream(json.dumps(payload) + json.dumps(payload)), "gemini")
    payload["source_code"] = "def broken("
    with pytest.raises(ValueError, match="python_syntax"):
        generation.parse_stream(stream(json.dumps(payload)), "gemini")


def test_terra_requires_final_turn_and_rejects_tools():
    events = [
        {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": json.dumps(
                    {
                        "source_code": "def on_bar(ctx,state): return {'action':'hold'}",
                        "assumptions": [],
                    }
                ),
            },
        },
        {"type": "turn.completed", "usage": {"output_tokens": 20}},
    ]
    generation.parse_stream("\n".join(map(json.dumps, events)), "terra")
    events.insert(0, {"type": "item.completed", "item": {"type": "command_execution"}})
    with pytest.raises(ValueError, match="도구"):
        generation.parse_stream("\n".join(map(json.dumps, events)), "terra")


def test_interrupted_generation_is_not_recalled_and_corruption_is_rejected(tmp_path):
    request = {"model": "terra", "source": "a"}
    immutable(tmp_path / "request.json", request)
    assert cached(tmp_path, request)["status"] == "interrupted"
    (tmp_path / "source.py").write_text("original")
    receipt(tmp_path, request, "completed")
    assert cached(tmp_path, request)["status"] == "completed"
    (tmp_path / "source.py").write_text("changed")
    with pytest.raises(ValueError, match="SHA256"):
        cached(tmp_path, request)
    with pytest.raises(ValueError, match="동결"):
        cached(tmp_path, {**request, "model": "gemini"})


def test_full_cohort_cannot_be_sealed_with_only_six_sources(tmp_path):
    rows = [{"id": str(i), "source_sha256": str(i), "status": "static_eligible"} for i in range(6)]
    write(tmp_path / "screening.json", rows)
    with pytest.raises(ValueError):
        catalogue.seal(tmp_path)
    assert catalogue.seal(tmp_path, 6, pilot=True)["execution_verified"] is False
    assert not (tmp_path / "cohort.json").exists()


def test_plan_and_report_keep_all_21600_cells_when_no_jobs_ran(tmp_path):
    (tmp_path / "one.pine").write_text("example")
    item = {"id": "one", "adapted_file": "one.pine", "adapted_sha256": sha(b"example")}
    write(tmp_path / "cohort.json", {"target": 200, "items": [item]})
    write(tmp_path / "data/dataset.json", {"end": "2026-10-24T00:00:00+00:00"})
    plan = execution.plan(tmp_path)
    assert len(plan["jobs"]) == plan["expected_cells"] == 21600
    assert len({identity(job) for job in plan["jobs"]}) == 21600
    report = build(tmp_path, tmp_path / "full-plan.json")
    assert report["status_counts"] == {"not_run": 21600}
    assert report["complete"] is False
    assert report["promotable"] is False


def test_pilot_has_54_cells_and_cannot_be_called_full(tmp_path):
    (tmp_path / "one.pine").write_text("example")
    write(
        tmp_path / "pilot-cohort.json",
        {
            "target": 6,
            "items": [
                {"id": str(i), "adapted_file": "one.pine", "adapted_sha256": sha(b"example")}
                for i in range(6)
            ],
        },
    )
    write(tmp_path / "data/dataset.json", {})
    plan = execution.plan(tmp_path, pilot=True)
    assert plan["expected_cells"] == 54
    assert plan["cohort_file"] == "pilot-cohort.json"


def test_minute_grid_and_ohlc_integrity_are_checked():
    start, end = pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-01T01:00Z")
    minutes = pd.DataFrame(
        {"open": "100", "high": "102", "low": "99", "close": "101", "volume": "1"},
        index=pd.date_range(start, end, freq="1min", inclusive="left"),
    )
    validate_minutes(minutes, start, end)
    assert str(aggregate_minutes(minutes, "1h").iloc[0]["volume"]) == "60"
    with pytest.raises(ValueError, match="누락"):
        validate_minutes(minutes.iloc[1:], start, end)
    minutes.iloc[0, minutes.columns.get_loc("high")] = "90"
    with pytest.raises(ValueError, match="불변식"):
        validate_minutes(minutes, start, end)


def test_signal_metrics_do_not_count_dominant_hold_as_direction_accuracy():
    expected = [
        {"timestamp": str(i), "action": action}
        for i, action in enumerate(["hold", "long", "short"])
    ]
    observed = [{**row, "action": "hold"} for row in expected]
    result = signal_quality(expected, observed)
    assert result["signal_mismatches"] == 2
    assert result["long_recall"] == result["short_recall"] == "0"
    assert result["long_precision"] is None
    observed[0]["timestamp"] = "changed"
    with pytest.raises(ValueError, match="시각"):
        signal_quality(expected, observed)


def test_authenticated_bundle_rejects_tampering_and_wrong_context(tmp_path):
    from tools.research.editor_picks.crypto import transform

    plain, cipher, restored = [tmp_path / name for name in ["plain", "cipher", "restored"]]
    plain.write_bytes(b"private source\n" * 50)
    key = b"x" * 32
    transform("encrypt", plain, cipher, key, "experiment")
    transform("decrypt", cipher, restored, key, "experiment")
    assert restored.read_bytes() == plain.read_bytes()
    with pytest.raises(Exception):
        transform("decrypt", cipher, tmp_path / "wrong", key, "different-context")
    changed = bytearray(cipher.read_bytes())
    changed[-2] ^= 1
    cipher.write_bytes(changed)
    with pytest.raises(Exception):
        transform("decrypt", cipher, tmp_path / "tampered", key, "experiment")
    assert not (tmp_path / "tampered").exists()


def test_archive_rejects_path_escape_before_any_file_is_written(tmp_path):
    import io
    import tarfile

    from tools.research.editor_picks.remote import safe_extract

    archive = tmp_path / "input.tar"
    with tarfile.open(archive, "w") as output:
        member = tarfile.TarInfo("../escape")
        member.size = 1
        output.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="링크"):
        safe_extract(archive, tmp_path / "target")
    assert not (tmp_path / "escape").exists()
