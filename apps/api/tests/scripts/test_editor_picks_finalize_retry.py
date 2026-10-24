"""실제 파일 fixture로 19+1 집계의 provenance·배정·실패 원본 보존을 검증한다."""

import gzip
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks.common import (  # noqa: E402
    ARMS,
    identity,
    read,
    receipt,
    sha,
    write,
)
from tools.research.editor_picks.execution import implementation  # noqa: E402
from tools.research.editor_picks.remote import remote_namespace  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "finalize_retry", ROOT / "tools/scripts/editor-picks-finalize-retry.py"
)
retry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retry)


@pytest.fixture
def evidence(tmp_path):
    root = tmp_path
    write(root / "data/dataset.json", {"fixture": True})
    source = "//@version=5\nstrategy('fixture')\n"
    (root / "adapted").mkdir()
    (root / "adapted/one.pine").write_text(source)
    item = {
        "id": "one",
        "source_sha256": sha(source.encode()),
        "adapted_file": "adapted/one.pine",
        "adapted_sha256": sha(source.encode()),
        "warmup_bars": 1000,
    }
    write(root / "cohort.json", {"items": [item]})
    jobs = [
        {"id": "one", "arm": "pine", "timeframe": "1h", "months": 6, "scenario": str(i)}
        for i in range(40)
    ]
    frozen = {
        "phase": "full",
        "jobs": jobs,
        "expected_cells": 40,
        "cohort_file": "cohort.json",
        "cohort_sha256": retry.digest(root / "cohort.json"),
        "dataset_sha256": retry.digest(root / "data/dataset.json"),
        "implementation": implementation(),
        "artifacts": {
            "one": {
                "pine": {"language": "pine", "source_sha256": item["adapted_sha256"]},
                "terra": {"unavailable_reason": "fixture"},
                "gemini": {"unavailable_reason": "fixture"},
            }
        },
    }
    write(root / "full-plan.json", frozen)
    base = {
        "head": "a" * 40,
        "run_id": "123",
        "input_sha256": "b" * 64,
        "plan": "full-plan.json",
        "plan_sha256": identity(frozen),
        "shards": 20,
    }
    images = {"pine": "pine-image", "python": "python-image"}
    manifest = {
        "image_ids": {f"quantbridge-{lang}-runner:local": value for lang, value in images.items()},
        "files": {"runsc": "runtime-hash"},
    }
    proof = {"fixture": "verified computation sources"}
    write(root / "runtime/manifest.json", manifest)
    write(root / "runtime/source-proof.json", proof)
    states = {
        attempt: {"provenance": {**base, "attempt": attempt}, "collected": {}}
        for attempt in ("1", "2")
    }

    def envelope(shard, attempt, failed=False):
        provenance = {**base, "attempt": attempt, "shard": shard}
        prefix = remote_namespace(provenance) / str(shard)
        paths = []

        def put(name, value):
            path = root / prefix / name
            write(path, value)
            paths.append(str(path.relative_to(root)))

        put(
            "runtime-installed.json",
            {"images": manifest["image_ids"], "runtime": manifest["files"], "source_proof": proof},
        )
        put(
            f"terminal-{shard}.json",
            {
                "actual_returncode": 1 if failed else 0,
                "economic_returncode": 1 if failed else 0,
                "native_returncodes": {"one": 0} if shard == 0 else {},
                "shard": shard,
                "shards": 20,
                "plan_sha256": identity(frozen),
            },
        )
        if failed:
            put(
                "runtime-blocked-15.json",
                {
                    "status": "blocked",
                    "plan_sha256": identity(frozen),
                    "error": "docker info timed out after 15 seconds",
                },
            )
        else:
            put(
                f"worker-full-{shard}.json",
                {
                    "status": "finished",
                    "plan_sha256": identity(frozen),
                    "shard": shard,
                    "shards": 20,
                    "jobs_consumed": 2,
                },
            )
            for job in jobs[shard::20]:
                request = {
                    "plan": identity(frozen),
                    "job": job,
                    "images": images,
                    "source_sha256": item["adapted_sha256"],
                }
                folder = root / "results" / identity(request)
                write(folder / "request.json", request)
                (folder / "result.json.gz").write_bytes(gzip.compress(b'{"result":{},"trace":[]}'))
                (folder / "signals.json.gz").write_bytes(gzip.compress(b"[]"))
                receipt(
                    folder,
                    request,
                    "completed",
                    job=job,
                    metrics={},
                    action_sha256=identity([]),
                    ledger_sha256=identity({}),
                    economic_verdict={"passed": False},
                )
                paths.extend(str(path.relative_to(root)) for path in folder.iterdir())
            if shard == 0:
                path = root / "native-checks/one.json"
                write(
                    path,
                    {
                        "id": "one",
                        "plan_sha256": identity(frozen),
                        "source_sha256": item["source_sha256"],
                        "images": images,
                        "arms": {arm: {"native_prefix_repeat_passed": False} for arm in ARMS},
                        "native_windows": {},
                    },
                )
                paths.append(str(path.relative_to(root)))
        path = root / prefix / "envelope.json"
        write(path, {**provenance, "files": {name: retry.digest(root / name) for name in paths}})
        states[attempt]["collected"][str(shard)] = {
            "asset_name": f"result-123-{attempt}-{shard}.enc",
            "cipher_sha256": "c" * 64,
            "envelope_sha256": retry.digest(path),
        }
        return prefix

    old = envelope(15, "1", True)
    for shard in range(20):
        envelope(shard, "2" if shard == 15 else "1")
    for attempt, state in states.items():
        write(root / f"private/stream-collection-123-{attempt}.json", state)
    old_files = read(root / old / "envelope.json")["files"]
    failed = {
        "shard": 15,
        "attempt": "1",
        "asset_name": "result-123-1-15.enc",
        "asset_digest": "sha256:" + "c" * 64,
        "envelope_sha256": retry.digest(root / old / "envelope.json"),
        "terminal_sha256": old_files[str(old / "terminal-15.json")],
        "runtime_blocked_sha256": old_files[str(old / "runtime-blocked-15.json")],
    }
    selection = {
        "schema_version": 1,
        "base": base,
        "selected": [
            {"shard": shard, "attempt": "2" if shard == 15 else "1"} for shard in range(20)
        ],
        "failed_source": failed,
    }
    path = root / "retry-selection.json"
    write(path, selection)
    write(
        root / remote_namespace({**base, "attempt": "1"}) / "finalization.json",
        {"complete": False, "original": True},
    )
    return root, path, selection, old


def reauthenticate(root, selection, shard, change):
    attempt = "2" if shard == 15 else "1"
    prefix = remote_namespace({**selection["base"], "attempt": attempt}) / str(shard)
    path = root / prefix / "envelope.json"
    envelope = read(path)
    change(prefix, envelope)
    for name in envelope["files"]:
        envelope["files"][name] = retry.digest(root / name)
    write(path, envelope)
    state_path = root / f"private/stream-collection-123-{attempt}.json"
    state = read(state_path)
    state["collected"][str(shard)]["envelope_sha256"] = retry.digest(path)
    write(state_path, state)


def test_real_mixed_finalize_preserves_failed_attempt_and_original_finalization(evidence):
    root, path, selection, old = evidence
    before = {
        name: retry.digest(root / name) for name in read(root / old / "envelope.json")["files"]
    }
    result = retry.finalize(root, path)
    assert result["complete"] is True and result["provenance"] == selection["base"]
    assert result["selection_sha256"] == identity(selection)
    assert result["failed_source"]["economic_cells"] == 0
    assert len(result["selected_shards"]) == 20
    assert retry.validate(root, path) == {key: result[key] for key in retry.validate(root, path)}
    assert before == {name: retry.digest(root / name) for name in before}
    assert read(
        root / remote_namespace({**selection["base"], "attempt": "1"}) / "finalization.json"
    ) == {"complete": False, "original": True}
    assert (
        read(root / retry.mixed_namespace(identity(selection)) / "finalization.json")["complete"]
        is True
    )
    verification_sha = retry.digest(root / "verification/one.json")
    assert retry.finalize(root, path) == result
    assert retry.digest(root / "verification/one.json") == verification_sha
    with (root / "report/full/report.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="보고서"):
        retry.finalize(root, path)


@pytest.mark.parametrize("change", ("missing", "duplicate", "wrong_attempt"))
def test_selection_is_exact_and_fixed_before_performance(evidence, change):
    root, path, selection, _ = evidence
    if change == "missing":
        selection["selected"].pop()
    elif change == "duplicate":
        selection["selected"][1] = dict(selection["selected"][0])
    else:
        selection["selected"][15]["attempt"] = "1"
    write(path, selection)
    with pytest.raises(ValueError, match="20개 유일"):
        retry.validate(root, path)


@pytest.mark.parametrize(
    "kind",
    (
        "unlisted_terminal",
        "unlisted_runtime",
        "unlisted_allocation",
        "allocation",
        "nonzero",
        "ownership",
        "native_id",
        "head",
        "input",
    ),
)
def test_authenticated_but_invalid_shard_evidence_is_denied(evidence, kind):
    root, path, selection, _ = evidence

    def change(prefix, envelope):
        if kind == "unlisted_terminal":
            del envelope["files"][str(prefix / "terminal-1.json")]
        elif kind == "unlisted_runtime":
            del envelope["files"][str(prefix / "runtime-installed.json")]
        elif kind == "unlisted_allocation":
            del envelope["files"][str(prefix / "worker-full-1.json")]
        elif kind == "head":
            envelope["head"] = "other-head"
        elif kind == "input":
            envelope["input_sha256"] = "other-input"
        elif kind == "native_id":
            value = read(root / "native-checks/one.json")
            value["id"] = "another"
            write(root / "native-checks/one.json", value)
        elif kind == "allocation":
            value = read(root / prefix / "worker-full-1.json")
            value["jobs_consumed"] = 1
            write(root / prefix / "worker-full-1.json", value)
        elif kind == "nonzero":
            value = read(root / prefix / "terminal-1.json")
            value["actual_returncode"] = 1
            write(root / prefix / "terminal-1.json", value)
        else:
            own = [name for name in envelope["files"] if name.startswith("results/")]
            for name in own:
                del envelope["files"][name]
            foreign = read(
                root / remote_namespace({**selection["base"], "attempt": "1"}) / "2/envelope.json"
            )
            envelope["files"].update(
                {
                    name: value
                    for name, value in foreign["files"].items()
                    if name.startswith("results/")
                }
            )

    reauthenticate(root, selection, 0 if kind == "native_id" else 1, change)
    with pytest.raises(ValueError):
        retry.validate(root, path)


def test_raw_hash_tamper_and_failed_origin_tamper_are_denied(evidence):
    root, path, _selection, old = evidence
    (root / old / "runtime-blocked-15.json").write_text("{}")
    with pytest.raises(ValueError, match="SHA256"):
        retry.validate(root, path)


def test_missing_selected_shard_is_denied(evidence):
    root, path, selection, _ = evidence
    prefix = remote_namespace({**selection["base"], "attempt": "2"}) / "15"
    (root / prefix / "envelope.json").unlink()
    with pytest.raises(FileNotFoundError):
        retry.validate(root, path)
