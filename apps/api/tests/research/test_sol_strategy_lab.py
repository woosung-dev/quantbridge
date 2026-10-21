"""성공 캐시가 입력 변경이나 실행 소스 손상을 숨기지 못하도록 검증한다."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research import sol_strategy_lab as subject  # noqa: E402
from tools.research.sol_codegen import digest  # noqa: E402


@pytest.fixture
def cached_trial(tmp_path, monkeypatch):
    (tmp_path / "manifest.json").write_text("{}")

    def fake_generate(prompt, destination, *, schema, timeout):
        destination.mkdir(parents=True)
        payload = {"source_code": "code", "assumptions": []}
        request = {"prompt": prompt, "schema": schema, "timeout": timeout}
        result = {
            "status": "completed",
            "job_hash": digest(request),
            "payload_hash": digest(payload),
            "usage": {"output_tokens": 10},
            "duration_seconds": 1,
        }
        for name, value in (("request", request), ("generation", result), ("payload", payload)):
            (destination / f"{name}.json").write_text(json.dumps(value))
        return result

    monkeypatch.setattr(subject, "generate", fake_generate)
    monkeypatch.setattr(subject, "public_check", lambda source, language: {"passed": True})
    case = {"id": "D01", "prompt": "first"}
    result = subject.trial(tmp_path, case, "A", "python", 0)
    return tmp_path, case, result


def test_unchanged_evidence_is_resumable(cached_trial):
    root, case, expected = cached_trial
    assert subject.trial(root, case, "A", "python", 0) == expected


def test_changed_prompt_is_rejected(cached_trial):
    root, case, _ = cached_trial
    with pytest.raises(ValueError, match="입력"):
        subject.trial(root, {**case, "prompt": "changed"}, "A", "python", 0)


def test_missing_successful_source_is_rejected(cached_trial):
    root, case, _ = cached_trial
    (root / "trials/A/python/D01/0/source.txt").unlink()
    with pytest.raises(ValueError, match="소스"):
        subject.trial(root, case, "A", "python", 0)


def test_modified_generation_payload_is_rejected(cached_trial):
    root, case, _ = cached_trial
    (root / "trials/A/python/D01/0/attempt-0/payload.json").write_text('{"source_code":"altered"}')
    with pytest.raises(ValueError, match="응답"):
        subject.trial(root, case, "A", "python", 0)


@pytest.mark.parametrize("mutation", ["missing_hash", "changed_source", "changed_input"])
def test_semantic_cache_is_bound_to_actual_source_and_cannot_be_retrocertified(
    cached_trial, monkeypatch, mutation
):
    from tools.research import sol_semantic_eval

    root, _, result = cached_trial
    folder = root / "trials/A/python/D01/0"
    calls = []

    def evaluate(source, language, case_id):
        calls.append(source)
        return {"status": "passed", "source_hash": hashlib.sha256(source.encode()).hexdigest()}

    monkeypatch.setattr(sol_semantic_eval, "evaluate", evaluate)
    semantic = subject.semantic_result(folder, result)
    (folder / "semantic.json").write_text(json.dumps(semantic))
    assert subject.semantic_result(folder, result) == semantic
    assert len(calls) == 1
    if mutation == "missing_hash":
        del semantic["source_hash"]
        (folder / "semantic.json").write_text(json.dumps(semantic))
    elif mutation == "changed_source":
        (folder / "source.txt").write_text("new source")
        result = {**result, "source_hash": hashlib.sha256(b"new source").hexdigest()}
    else:
        result = {**result, "input_identity": "changed"}
    with pytest.raises(ValueError, match="캐시"):
        subject.semantic_result(folder, result)
    assert len(calls) == 1
