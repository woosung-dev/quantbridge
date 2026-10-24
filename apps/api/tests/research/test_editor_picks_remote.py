"""격리 실행 결과의 인증·분모·불변 수거를 DB 없이 확인한다."""

import io
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import remote, report, verification
from tools.research.editor_picks.common import identity, read, sha, write
from tools.research.editor_picks.crypto import transform


def bundle(tmp_path, phase="pilot", run_id="123"):
    root = tmp_path / "worker"
    plan = {"phase": phase, "jobs": [{"id": "a"}, {"id": "b"}]}
    if phase == "full":
        write(root / "cohort.json", {"items": []})
        plan.update(
            cohort_file="cohort.json", cohort_sha256=sha((root / "cohort.json").read_bytes())
        )
    write(root / f"{phase}-plan.json", plan)
    provenance = {
        "head": "a" * 40,
        "run_id": run_id,
        "attempt": "1",
        "input_sha256": "b" * 64,
        "plan": f"{phase}-plan.json",
        "plan_sha256": identity(plan),
        "shards": 1,
        "shard": 0,
    }
    terminal = {"actual_returncode": 0, "plan_sha256": identity(plan)}
    if phase == "full":
        terminal.update(economic_returncode=0, native_returncodes={})
    write(root / "terminal-0.json", terminal)
    write(
        root / f"worker-{phase}-0.json",
        {
            "status": "finished",
            "plan_sha256": identity(plan),
            "shard": 0,
            "shards": 1,
            "jobs_consumed": 2,
        },
    )
    cell = "cell" if phase == "pilot" else "full-cell"
    write(root / f"results/{cell}/receipt.json", {"status": "failed"})
    archive = tmp_path / "result.tar.gz"
    remote.pack_result(root, archive, 0, provenance)
    return root, archive, provenance


def test_collect_binds_attempt_and_preserves_existing_results(tmp_path):
    _, archive, provenance = bundle(tmp_path)
    destination = tmp_path / "received"
    with pytest.raises(ValueError, match="provenance"):
        remote.collect_result(archive, destination, {**provenance, "attempt": "2"})
    assert not destination.exists()
    remote.collect_result(archive, destination, provenance)
    remote.collect_result(archive, destination, provenance)
    receipt = destination / "results/cell/receipt.json"
    write(receipt, {"status": "changed"})
    with pytest.raises(ValueError, match="충돌"):
        remote.collect_result(archive, destination, provenance)
    assert read(receipt)["status"] == "changed"


def test_extract_preflights_every_collision_before_writing(tmp_path):
    archive = tmp_path / "input.tar"
    with tarfile.open(archive, "w") as output:
        for name in ("new", "existing"):
            member = tarfile.TarInfo(name)
            member.size = 1
            output.addfile(member, io.BytesIO(b"x"))
    destination = tmp_path / "received"
    destination.mkdir()
    (destination / "existing").write_text("old")
    with pytest.raises(ValueError):
        remote.safe_extract(archive, destination)
    assert not (destination / "new").exists()


def test_pilot_and_full_same_shard_keep_separate_remote_evidence(tmp_path, monkeypatch):
    pilot = bundle(tmp_path / "pilot")
    full = bundle(tmp_path / "full", phase="full", run_id="456")
    destination = tmp_path / "received"
    monkeypatch.setattr(report, "build", lambda *_: {"complete": True})
    monkeypatch.setattr(verification, "reconcile", lambda *_: None, raising=False)
    namespaces = []
    for root, archive, provenance in (pilot, full):
        remote.collect_result(archive, destination, provenance)
        write(destination / provenance["plan"], read(root / provenance["plan"]))
        if (root / "cohort.json").exists():
            write(destination / "cohort.json", read(root / "cohort.json"))
        expected = {key: value for key, value in provenance.items() if key != "shard"}
        assert remote.finalize(destination, destination / provenance["plan"], expected)["complete"]
        namespace = remote.remote_namespace(provenance)
        assert (destination / namespace / "0/envelope.json").is_file()
        namespaces.append(namespace)
    assert namespaces[0] != namespaces[1]
    assert all(
        (destination / namespace / "finalization.json").is_file() for namespace in namespaces
    )
    assert len(list((destination / "results").glob("*/receipt.json"))) == 2


def test_cipher_rejects_wrong_attempt_and_removes_partial_plaintext(tmp_path):
    source = tmp_path / "plain"
    source.write_bytes(b"private source")
    cipher = tmp_path / "cipher"
    recovered = tmp_path / "recovered"
    key = bytes(32)
    transform("encrypt", source, cipher, key, "attempt-1")
    with pytest.raises(Exception):
        transform("decrypt", cipher, recovered, key, "attempt-2")
    assert not recovered.exists()
    transform("decrypt", cipher, recovered, key, "attempt-1")
    assert recovered.read_bytes() == source.read_bytes()


def test_finalize_requires_actual_exit_and_every_allocated_cell(tmp_path, monkeypatch):
    root, archive, provenance = bundle(tmp_path)
    destination = tmp_path / "received"
    remote.collect_result(archive, destination, provenance)
    write(destination / "pilot-plan.json", read(root / "pilot-plan.json"))
    monkeypatch.setattr(report, "build", lambda *_: {"complete": True})
    expected = {key: value for key, value in provenance.items() if key != "shard"}
    result = remote.finalize(destination, destination / "pilot-plan.json", expected)
    assert result["complete"]
    # 암호화된 봉투의 파일 해시가 맞더라도 실패 종료를 성공으로 바꾸지 않는다.
    terminal = root / "terminal-0.json"
    write(terminal, {"actual_returncode": 1, "plan_sha256": provenance["plan_sha256"]})
    second_archive = tmp_path / "failed.tar.gz"
    remote.pack_result(root, second_archive, 0, provenance)
    failed = tmp_path / "failed"
    remote.collect_result(second_archive, failed, provenance)
    write(failed / "pilot-plan.json", read(root / "pilot-plan.json"))
    result = remote.finalize(failed, failed / "pilot-plan.json", expected)
    assert not result["complete"]
    assert result["failures"][0]["shard"] == 0


def test_runtime_install_is_refused_on_local_host(tmp_path):
    with pytest.raises(ValueError, match="일회용 GitHub ARM"):
        remote.install_runtime(tmp_path)
