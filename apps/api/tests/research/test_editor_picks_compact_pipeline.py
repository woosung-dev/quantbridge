"""108개 합성 셀을 원래 패킹·AES 수거·종결·검증·보고·수출 경로에 연결한다."""

import gzip
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tools.research.editor_picks import compact, execution, remote, verification
from tools.research.editor_picks.common import (
    ARMS,
    NATIVE_POLICY,
    TIMEFRAMES,
    identity,
    read,
    receipt,
    sha,
    write,
)
from tools.research.editor_picks.crypto import transform


def test_compact_full_pipeline_preserves_static_failures_remote_storage_and_zero_export(
    tmp_path, monkeypatch
):
    sender = tmp_path / "sender"
    sender.mkdir()
    source = b"//@version=5\nindicator('trusted static fixture')\nplot(close)\n"
    original = sender / "sources/one.pine"
    original.parent.mkdir()
    original.write_bytes(source)
    write(
        sender / "screening/one.json",
        {
            "id": "one",
            "status": "unsupported",
            "source_sha256": sha(source),
            "detail": "trusted static fixture",
        },
    )
    preflight = {
        "status": "unsupported",
        "source_sha256": sha(source),
        "evidence_file": "screening/one.json",
        "evidence_sha256": sha((sender / "screening/one.json").read_bytes()),
    }
    item = {
        "id": "one",
        "source_file": "sources/one.pine",
        "source_sha256": sha(source),
        "pine_preflight": preflight,
        "warmup_bars": 1000,
    }
    write(sender / "cohort.json", {"target": 1, "items": [item]})
    write(sender / "data/dataset.json", {"scope": "trusted synthetic metadata without market data"})
    trusted_source = "trusted synthetic artifact; never executed"
    trusted_sha = sha(trusted_source.encode())

    def artifact(_, candidate, arm):
        assert candidate["id"] == "one"
        if arm == "terra":
            return trusted_source, "python", trusted_sha
        raise ValueError("completed_generation_missing")

    # 원문이나 생성 코드를 실행하지 않고 고정 artifact 문자열만 제공한다.
    monkeypatch.setattr(execution, "artifact", artifact)
    monkeypatch.setattr(verification, "artifact", artifact)
    frozen = execution.plan(sender)
    assert len(frozen["jobs"]) == frozen["expected_cells"] == 108
    assert frozen["artifacts"]["one"]["pine"] == {"preflight_failure": preflight}
    images = {"pine": "trusted-pine-image", "python": "trusted-python-image"}
    omitted = {}
    for job in frozen["jobs"]:
        request = {"plan": identity(frozen), "job": job, "images": images}
        details = {"job": job, "source_present": True, "runtime_attempted": False}
        if job["arm"] == "pine":
            request["preflight_failure"] = preflight
            details.update(
                error="pine_static_preflight_failed:unsupported", failure_stage="static_preflight"
            )
            status = "failed"
        elif job["arm"] == "gemini":
            request["unavailable_reason"] = "completed_generation_missing"
            details["reason"] = "completed_generation_missing"
            status = "not_available"
        else:
            request["source_sha256"] = trusted_sha
            details.update(
                runtime_attempted=True,
                action_sha256="trusted-actions",
                ledger_sha256="trusted-ledger",
                metrics={},
            )
            status = "completed"
        folder = sender / "results" / identity(request)
        write(folder / "request.json", request)
        if status == "completed":
            raw = gzip.compress(b'{"scope":"trusted synthetic payload, no strategy executed"}')
            (folder / "result.json.gz").write_bytes(raw)
            (folder / "signals.json.gz").write_bytes(gzip.compress(b"[]"))
            omitted[str((folder / "result.json.gz").relative_to(sender))] = sha(raw)
        receipt(folder, request, status, **details)
    native = {
        "id": "one",
        "source_sha256": sha(source),
        "plan_sha256": identity(frozen),
        "images": images,
        "native_policy": dict(NATIVE_POLICY),
        "native_windows": {tf: {"status": "missing_native_capture"} for tf in TIMEFRAMES},
        "arms": {
            arm: {
                "status": "incomplete",
                "native_prefix_repeat_passed": False,
                "exact_economic_cells": 0,
            }
            for arm in ARMS
        },
    }
    write(sender / "verification/one.json", native)
    write(
        sender / "terminal-0.json",
        {
            "actual_returncode": 0,
            "economic_returncode": 0,
            "native_returncodes": {"one": 0},
            "plan_sha256": identity(frozen),
        },
    )
    write(
        sender / "worker-full-0.json",
        {
            "status": "finished",
            "plan_sha256": identity(frozen),
            "shard": 0,
            "shards": 1,
            "jobs_consumed": 108,
        },
    )
    expected = {
        "head": "a" * 40,
        "run_id": "12345",
        "attempt": "1",
        "input_sha256": "b" * 64,
        "plan": "full-plan.json",
        "plan_sha256": identity(frozen),
        "shards": 1,
    }
    provenance = {**expected, "shard": 0}
    full_archive = tmp_path / "full.tar.gz"
    remote.pack_result(sender, full_archive, 0, provenance)
    full_cipher = tmp_path / "full.enc"
    key = b"c" * 32
    transform(
        "encrypt", full_archive, full_cipher, key, f"{remote.CONTEXT}/result/{identity(provenance)}"
    )
    cipher_sha = sha(full_cipher.read_bytes())
    part = {
        "name": "full.enc",
        "sha256": cipher_sha,
        "bytes": full_cipher.stat().st_size,
        "asset_id": 101,
        "browser_download_url": "https://github.com/woosung-dev/quantbridge/releases/download/editor-picks-research-20261024/full.enc",
    }
    descriptor = {
        "schema_version": 1,
        "sha256": cipher_sha,
        "bytes": full_cipher.stat().st_size,
        "parts": [part],
    }
    stage = tmp_path / "stage"
    certificate = compact.prepare(full_archive, provenance, stage)
    assert {name: value["sha256"] for name, value in certificate["omitted"].items()} == omitted
    small_archive = tmp_path / "compact.tar.gz"
    compact.seal(stage, descriptor, small_archive)
    small_cipher = tmp_path / "compact.enc"
    aad = f"{remote.CONTEXT}/compact-result/{identity(provenance)}"
    transform("encrypt", small_archive, small_cipher, key, aad)
    authenticated_archive = tmp_path / "authenticated.tar.gz"
    transform("decrypt", small_cipher, authenticated_archive, key, aad)
    collected = tmp_path / "collected"
    collected.mkdir()
    for directory in ("sources", "screening", "data"):
        shutil.copytree(sender / directory, collected / directory)
    for name in ("cohort.json", "full-plan.json"):
        shutil.copy2(sender / name, collected / name)
    metadata = [
        {
            "id": 101,
            "name": part["name"],
            "size": part["bytes"],
            "digest": "sha256:" + cipher_sha,
            "state": "uploaded",
            "browser_download_url": part["browser_download_url"],
        }
    ]
    compact.collect(
        authenticated_archive,
        collected,
        provenance,
        metadata,
        small_cipher,
        sha(small_cipher.read_bytes()),
    )
    assert len(omitted) == 36 and all(not (collected / name).exists() for name in omitted)
    with pytest.raises(ValueError):
        verification.receipts(collected, frozen)
    raw_native = (collected / "native-checks/one.json").read_bytes()
    with compact.context(collected, key, expected):
        final = remote.finalize(collected, collected / "full-plan.json", expected)
        assert final == {"provenance": expected, "failures": [], "complete": True}
        proof = read(collected / "verification/one.json")
        assert all(arm["status"] == "incomplete" for arm in proof["arms"].values())
        assert (
            proof["arms"]["pine"]["native_gate_error"] == "pine_static_preflight_failed:unsupported"
        )
        assert proof["arms"]["pine"]["exact_economic_cells"] == 0
        assert proof["arms"]["pine"]["native_prefix_repeat_passed"] is False
        summary = read(collected / "report/full/report.json")["summary"]
        assert summary["complete"] is True and summary["observed_cells"] == 108
        assert summary["status_counts"] == {"failed": 36, "completed": 36, "not_available": 36}
        assert summary["raw_result_storage"] == {"authenticated_remote_payload": 36}
        assert summary["runtime_evidence"]["pine"]["static_preflight_rejected_cells"] == 36
        assert summary["runtime_evidence"]["pine"]["requested_cells"] == 0
        assert summary["runtime_evidence"]["terra"]["requested_cells"] == 36
        assert summary["runtime_evidence"]["gemini"]["requested_cells"] == 0
        assert verification.export(collected, collected / "full-plan.json") == {
            "status": "exported",
            "count": 0,
        }
        assert read(collected / "registration/requests.json")["requests"] == []
    assert (collected / "native-checks/one.json").read_bytes() == raw_native
    with pytest.raises(ValueError):
        verification.receipts(collected, frozen)
