"""원본 실험을 실행하지 않고 분모·증거·전략 단위 통계·경제 선정 계약을 검증한다."""

import itertools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import sol_score_report as subject
from tools.research.sol_codegen import digest, strict_schema


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def run(tmp_path, *, cases=2, repetitions=2, full=False):
    manifest = {
        "model": "gpt-6.1-sol",
        "effort": "high",
        "stage": "evaluation" if full else "pilot",
        "cases": [{"id": f"{i:02}", "prompt": f"rule {i}"} for i in range(1, cases + 1)],
        "repetitions": repetitions,
        "arms": list("ABC") if full else ["A"],
        "languages": ["pine", "python", "typescript"] if full else ["python"],
        "contract": "common",
        "language_contracts": {x: x for x in ("pine", "python", "typescript")},
    }
    manifest["total_jobs"] = (
        cases * repetitions * len(manifest["arms"]) * len(manifest["languages"])
    )
    write(tmp_path / "manifest.json", manifest)
    return manifest


def trial(
    root,
    manifest,
    case_id,
    repetition,
    *,
    arm="A",
    language="python",
    public=True,
    semantic_pass=True,
):
    folder = root / "trials" / arm / language / case_id / str(repetition)
    case = next(x for x in manifest["cases"] if x["id"] == case_id)
    prompt = (
        manifest["contract"]
        + "\n"
        + manifest["language_contracts"][language]
        + "\n전략의 정확한 요구:\n"
        + case["prompt"]
    )
    if arm == "C":
        prompt += subject.C_SUFFIX
    schema = subject._schema(arm)
    identity = digest(
        {
            "prompt": prompt,
            "schema": schema,
            "model": manifest["model"],
            "effort": manifest["effort"],
            "arm": arm,
            "language": language,
            "repetition": repetition,
            "manifest_hash": subject.file_hash(root / "manifest.json"),
        }
    )
    source = f"# {case_id} {repetition}\ndef on_bar(ctx, state):\n    return {{'action': 'hold'}}\n"
    payload = {"source_code": source, "assumptions": []}
    request = {
        "model": manifest["model"],
        "effort": manifest["effort"],
        "prompt": prompt,
        "schema": strict_schema(schema),
    }
    generation = {
        "status": "completed" if arm != "C" else "failed",
        "job_hash": digest(request),
        "usage": {"output_tokens": 100},
        "duration_seconds": 2,
    }
    if arm != "C":
        generation["payload_hash"] = digest(payload)
        write(folder / "attempt-0/payload.json", payload)
    write(folder / "attempt-0/request.json", request)
    write(folder / "attempt-0/generation.json", generation)
    value = {
        "case_id": case_id,
        "arm": arm,
        "language": language,
        "repetition": repetition,
        "input_identity": identity,
        "status": "public_pass" if public else "failed",
        "attempts": [{"generation": generation, "validation": {"passed": public}}],
        "generation_output_tokens": 100,
        "generation_seconds": 2,
        "source_hash": None,
    }
    if public:
        (folder / "source.txt").write_text(source)
        value["source_hash"] = subject.file_hash(folder / "source.txt")
    write(folder / "trial.json", value)
    semantic = {
        "input_identity": identity,
        "source_hash": value["source_hash"],
        "status": "generation_or_public_failure"
        if not public
        else "passed"
        if semantic_pass
        else "failed",
        "contract_points": 40 if public else 0,
        "ledger_points": 25 if public else 0,
        "reproducibility_points": 15 if public else 0,
    }
    if public:
        semantic["action_quality"] = {"expected_counts": dict.fromkeys(subject.ACTIONS, 3)}
    write(folder / "semantic.json", semantic)
    return folder


def test_missing_failed_and_interrupted_keep_full_denominator(tmp_path):
    manifest = run(tmp_path)
    trial(tmp_path, manifest, "01", 0)
    trial(tmp_path, manifest, "01", 1, public=False)
    (tmp_path / "trials/A/python/02/0").mkdir(parents=True)
    report = subject.build_report(tmp_path, draws=100)
    assert report["expected_artifacts"] == 4
    assert report["observations"] == {"complete": 2, "interrupted": 1, "missing": 1}
    cell = report["score100_ranking"][0]
    assert cell["semantic_pass_rate"] == 0.25
    assert cell["quality90"] == 22.5
    assert cell["score100"] < 25
    assert cell["action_observations"] == dict.fromkeys(subject.ACTIONS, 3)
    assert cell["generation_metric_observations"] == 2
    assert not report["complete"] and not report["final_selection_allowed"]
    assert len(report["artifact_scores"]) == 4
    assert [
        row["score100"]
        for row in report["artifact_scores"]
        if row["observation"] in ("missing", "interrupted")
    ] == [0, 0]
    path = tmp_path / "quality.json"
    write(path, report)
    with pytest.raises(ValueError, match="pilot/불완료"):
        subject.export_selection(tmp_path, path, "A/python")
    assert not (tmp_path / "quality.selection.json").exists()


def test_missing_semantic_scores_zero_even_after_public_pass(tmp_path):
    manifest = run(tmp_path, cases=1, repetitions=1)
    folder = trial(tmp_path, manifest, "01", 0)
    (folder / "semantic.json").unlink()
    report = subject.build_report(tmp_path, draws=100)
    assert report["score100_ranking"][0]["score100"] == 0
    assert report["observations"] == {"semantic_missing": 1}
    assert report["artifact_scores"][0]["public_status"] == "public_pass"


def test_failed_unreported_usage_is_unknown_not_measured_zero(tmp_path):
    manifest = run(tmp_path, cases=1, repetitions=1)
    folder = trial(tmp_path, manifest, "01", 0, public=False)
    generation_path = folder / "attempt-0/generation.json"
    generation = json.loads(generation_path.read_text())
    generation.update(status="timeout", usage={})
    write(generation_path, generation)
    trial_path = folder / "trial.json"
    value = json.loads(trial_path.read_text())
    value["attempts"][0]["generation"] = generation
    value["generation_output_tokens"] = 0
    write(trial_path, value)
    report = subject.build_report(tmp_path, draws=100)
    cell = report["score100_ranking"][0]
    assert cell["generation_output_tokens"] == 0
    assert cell["unknown_output_usage_calls"] == 1
    assert cell["score100"] == 0


def test_replica_correlation_uses_strategy_means_before_bootstrap(tmp_path):
    reports = []
    for repetitions in (1, 5):
        root = tmp_path / str(repetitions)
        manifest = run(root, repetitions=repetitions)
        for case, rep in itertools.product(("01", "02"), range(repetitions)):
            trial(root, manifest, case, rep, public=case == "01")
        reports.append(subject.build_report(root, draws=500))
    assert reports[0]["bootstrap100"] == reports[1]["bootstrap100"]
    assert reports[1]["bootstrap100"]["strategies"] == 2
    assert reports[0]["strategy_means100"] == reports[1]["strategy_means100"]
    assert reports[1]["ranking_is_provisional"]
    assert not reports[1]["final_selection_allowed"]


@pytest.mark.parametrize("mutation", ["source", "source_and_trial", "semantic", "trial", "request"])
def test_rejects_wrong_source_or_input_binding(tmp_path, mutation):
    manifest = run(tmp_path, cases=1, repetitions=1)
    folder = trial(tmp_path, manifest, "01", 0)
    if mutation.startswith("source"):
        (folder / "source.txt").write_text("changed")
        if mutation == "source_and_trial":
            path = folder / "trial.json"
            value = json.loads(path.read_text())
            value["source_hash"] = subject.file_hash(folder / "source.txt")
            write(path, value)
    else:
        path = (
            folder
            / {
                "semantic": "semantic.json",
                "trial": "trial.json",
                "request": "attempt-0/request.json",
            }[mutation]
        )
        value = json.loads(path.read_text())
        value["input_identity" if mutation != "request" else "prompt"] = "changed"
        write(path, value)
    with pytest.raises(ValueError, match="hash"):
        subject.build_report(tmp_path, draws=100)


def test_bonferroni_eight_descriptive_paired_comparisons_are_deterministic():
    groups = {
        f"{arm}/{lang}": [90, 70, 40]
        for arm, lang in itertools.product("ABC", ("pine", "python", "typescript"))
    }
    result = subject.paired_bootstrap(groups, draws=500)
    assert result == subject.paired_bootstrap(groups, draws=500)
    assert result["family_comparisons"] == 8 and result["descriptive_only"]
    assert all(row["bonferroni_family95_ci"] == [0, 0] for row in result["paired_differences"])


def test_old_semantic_score_cannot_follow_a_consistently_replaced_generated_source(tmp_path):
    manifest = run(tmp_path, cases=1, repetitions=1)
    folder = trial(tmp_path, manifest, "01", 0)
    replacement = "def on_bar(ctx, state):\n    return {'action':'long'}\n"
    payload = {"source_code": replacement, "assumptions": []}
    generation = json.loads((folder / "attempt-0/generation.json").read_text())
    generation["payload_hash"] = digest(payload)
    write(folder / "attempt-0/payload.json", payload)
    write(folder / "attempt-0/generation.json", generation)
    (folder / "source.txt").write_text(replacement)
    value = json.loads((folder / "trial.json").read_text())
    value["attempts"][0]["generation"] = generation
    value["source_hash"] = subject.file_hash(folder / "source.txt")
    write(folder / "trial.json", value)
    with pytest.raises(ValueError, match="semantic/trial 실행 source hash"):
        subject.build_report(tmp_path, draws=100)


def test_full_selection_matches_economic_exact_contract_and_first_pass(tmp_path):
    from tools.research.sol_economics import read_artifacts, validate_selection

    manifest = run(tmp_path, cases=30, repetitions=5, full=True)
    for case, arm, language, rep in itertools.product(
        manifest["cases"], manifest["arms"], manifest["languages"], range(5)
    ):
        passed = arm == "A" and language == "python" and case["id"] == "01" and rep in (1, 4)
        trial(tmp_path, manifest, case["id"], rep, arm=arm, language=language, public=passed)
    report = subject.build_report(tmp_path, draws=100)
    assert report["complete"] and report["final_selection_allowed"]
    assert len(report["score100_ranking"]) == 9
    path = tmp_path / "quality.json"
    write(path, report)
    selection, artifacts = subject.export_selection(tmp_path, path, "A/python")
    assert len(artifacts) == 30
    assert artifacts[0]["repetition"] == 1
    assert selection["semantic_pass_repetitions"]["01"] == [1, 4]
    assert all(row["source_path"] is None and row["repetition"] is None for row in artifacts[1:])
    assert set(artifacts[0]) == {
        "case_id",
        "language",
        "arm",
        "source_path",
        "source_hash",
        "repetition",
    }
    write(tmp_path / "artifacts.json", artifacts)
    write(tmp_path / "selection.json", selection)
    validate_selection(tmp_path / "selection.json", read_artifacts(tmp_path / "artifacts.json"))
    source = Path(artifacts[0]["source_path"])
    source.write_text("changed")
    with pytest.raises(ValueError, match="hash"):
        subject.export_selection(tmp_path, path, "A/python")


def test_incomplete_full_manifest_refuses_economic_selection(tmp_path):
    run(tmp_path, cases=30, repetitions=5, full=True)
    report = subject.build_report(tmp_path, draws=100)
    assert report["expected_artifacts"] == 1350
    assert report["observations"] == {"missing": 1350}
    assert all(
        row["score100"] == 0 and row["semantic_pass_rate"] == 0
        for row in report["score100_ranking"]
    )
    path = tmp_path / "quality.json"
    write(path, report)
    with pytest.raises(ValueError, match="pilot/불완료"):
        subject.export_selection(tmp_path, path, "A/python")
