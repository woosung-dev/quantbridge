"""이전 shard 암호문에서 인증된 현 배정 결과만 재사용하는지 검사한다."""

import argparse
import base64
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import remote  # noqa: E402
from tools.research.editor_picks.common import identity, read, sha, write  # noqa: E402
from tools.research.editor_picks.crypto import transform  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "resume_cache", ROOT / "tools/scripts/editor-picks-resume-cache.py"
)
resume_cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume_cache)


@pytest.fixture
def cache(tmp_path, monkeypatch):
    source, target = tmp_path / "old", tmp_path / "new"
    jobs = [{"id": str(index), "arm": "pine"} for index in range(5)]
    plan = {
        "phase": "full",
        "jobs": jobs,
        "artifacts": {job["id"]: {"pine": {"source_sha256": "c" * 64}} for job in jobs},
    }
    write(source / "cohort.json", {"items": [{"id": "0"}]})
    write(target / "cohort.json", {"items": [{"id": "0"}]})
    plan.update(cohort_file="cohort.json", cohort_sha256=sha((source / "cohort.json").read_bytes()))
    write(source / "full-plan.json", plan)
    write(target / "full-plan.json", plan)
    images = {"pine": "sha256:pine", "python": "sha256:python"}
    provenance = {
        "head": "a" * 40,
        "run_id": "123",
        "attempt": "1",
        "input_sha256": "b" * 64,
        "plan": "full-plan.json",
        "plan_sha256": identity(plan),
        "shards": 2,
        "shard": 0,
    }
    folders = {}
    for index in (0, 2, 4):
        request = {
            "plan": identity(plan),
            "job": jobs[index],
            "images": images,
            "source_sha256": "c" * 64,
        }
        folder = source / "results" / identity(request)
        folders[index] = folder.name
        write(folder / "request.json", request)
        if index == 4:
            continue
        (folder / "result.json.gz").write_bytes(b"compressed economic evidence")
        (folder / "signals.json.gz").write_bytes(b"compressed signals")
        files = {
            name: sha((folder / name).read_bytes())
            for name in ("request.json", "result.json.gz", "signals.json.gz")
        }
        write(
            folder / "receipt.json",
            {
                "job_hash": identity(request),
                "job": jobs[index],
                "status": "completed",
                "files": files,
            },
        )
    write(source / "verification/0.json", {"id": "0", "plan_sha256": identity(plan)})
    write(source / "terminal-0.json", {"actual_returncode": 130})
    write(source / "worker-full-0.json", {"status": "partial"})
    archive, cipher = tmp_path / "old.tar.gz", tmp_path / "old.enc"
    remote.pack_result(source, archive, 0, provenance)
    key = bytes(range(32))
    secret = base64.urlsafe_b64encode(key).decode()
    monkeypatch.setenv("RESUME_TEST_KEY", secret)
    monkeypatch.setattr(resume_cache, "require_runtime", lambda: images)
    transform("encrypt", archive, cipher, key, f"{remote.CONTEXT}/result/{identity(provenance)}")
    args = argparse.Namespace(
        run_dir=target,
        plan="full-plan.json",
        shard=0,
        shards=3,
        cipher=cipher,
        source_head=provenance["head"],
        source_run_id="123",
        source_attempt="1",
        source_input_sha=provenance["input_sha256"],
        source_shard=0,
        source_shards=2,
        key_env="RESUME_TEST_KEY",
    )
    return args, folders, source, secret


def test_resume_only_owned_complete_records_and_is_idempotent(cache, capsys):
    args, folders, _, secret = cache
    first = resume_cache.resume(args)
    assert first["cached_records"] == 1
    assert first["skipped_incomplete_folders"] == 1
    assert (args.run_dir / "results" / folders[0] / "receipt.json").exists()
    assert not (args.run_dir / "results" / folders[2]).exists()
    assert not (args.run_dir / "results" / folders[4]).exists()
    assert not (args.run_dir / "remote").exists()
    assert not (args.run_dir / "native-checks").exists()
    assert not list(args.run_dir.glob("terminal-*.json"))
    assert resume_cache.resume(args) == first
    report = read(args.run_dir / "results/resume-cache-0.json")
    assert report["helper_sha256"] == resume_cache.digest(Path(resume_cache.__file__))
    assert secret not in str(report)
    assert secret not in capsys.readouterr().out


@pytest.mark.parametrize(
    "change", ("cipher", "plan", "image", "input", "head", "attempt", "source_shard")
)
def test_resume_rejects_tampered_auth_plan_images_or_provenance(cache, monkeypatch, change):
    args, _, _, _ = cache
    if change == "cipher":
        data = bytearray(args.cipher.read_bytes())
        data[-1] ^= 1
        args.cipher.write_bytes(data)
    elif change == "plan":
        plan = read(args.run_dir / args.plan)
        plan["changed"] = True
        write(args.run_dir / args.plan, plan)
    elif change == "image":
        monkeypatch.setattr(resume_cache, "require_runtime", lambda: {"pine": "different"})
    elif change == "input":
        args.source_input_sha = "different"
    elif change == "head":
        args.source_head = "different"
    elif change == "attempt":
        args.source_attempt = "2"
    else:
        args.source_shard = 1
    with pytest.raises(Exception):
        resume_cache.resume(args)
    assert not (args.run_dir / "results").exists()


def test_resume_preflights_collision_without_overwriting(cache):
    args, folders, _, _ = cache
    target = args.run_dir / "results" / folders[0] / "result.json.gz"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing different evidence")
    with pytest.raises(ValueError, match="충돌"):
        resume_cache.resume(args)
    assert target.read_bytes() == b"existing different evidence"
    assert not (target.parent / "receipt.json").exists()
    assert not (args.run_dir / "results/resume-cache-0.json").exists()


def test_plaintext_temporary_directory_is_removed_on_success_and_auth_failure(
    cache, monkeypatch, tmp_path
):
    args, _, _, _ = cache
    original = resume_cache.tempfile.TemporaryDirectory
    pool = tmp_path / "plaintext"
    pool.mkdir()
    monkeypatch.setattr(
        resume_cache.tempfile, "TemporaryDirectory", lambda **kwargs: original(dir=pool, **kwargs)
    )
    resume_cache.resume(args)
    assert list(pool.iterdir()) == []
    args.source_attempt = "wrong"
    with pytest.raises(Exception):
        resume_cache.resume(args)
    assert list(pool.iterdir()) == []


def test_cli_does_not_echo_secret_exception_body(cache, monkeypatch):
    args, _, _, secret = cache
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda *_: args)

    def failed(_):
        raise ValueError(secret)

    monkeypatch.setattr(resume_cache, "resume", failed)
    with pytest.raises(SystemExit) as error:
        resume_cache.main()
    assert secret not in str(error.value)
    assert str(error.value) == "resume_cache_failed: ValueError"
