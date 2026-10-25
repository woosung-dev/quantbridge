"""실제 암호화·compact 수거를 연결하고 외부 업로드와 runner 권한만 대체한다."""

import argparse
import base64
import importlib.util
import json
import os
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import compact  # noqa: E402
from tools.research.editor_picks.common import identity, read, sha, write  # noqa: E402
from tools.research.editor_picks.crypto import MAGIC, transform  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "compact_finish", ROOT / "tools/scripts/editor-picks-compact-finish.py"
)
finisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finisher)


class Upload:
    def __init__(self):
        self.calls = []
        self.payloads = {}
        self.descriptors = {}
        self.fail_full = False
        self.fail_compact = False
        self.full_confirmed = False

    def __call__(self, cipher, descriptor):
        self.calls.append(cipher.name)
        assert cipher.read_bytes().startswith(MAGIC)
        small = cipher.name.startswith("compact-")
        if small:
            assert self.full_confirmed, "원본 전체 업로드 확인 전에 compact를 업로드했습니다"
        if (small and self.fail_compact) or (not small and self.fail_full):
            raise ValueError("synthetic_upload_failure")
        body = cipher.read_bytes()
        result = {
            "schema_version": 1,
            "sha256": sha(body),
            "bytes": len(body),
            "parts": [
                {
                    "name": cipher.name,
                    "sha256": sha(body),
                    "bytes": len(body),
                    "asset_id": len(self.calls),
                    "browser_download_url": f"https://github.com/{finisher.REPO}/releases/download/{finisher.TAG}/{cipher.name}",
                }
            ],
        }
        self.payloads[cipher.name] = body
        self.descriptors[cipher.name] = result
        write(descriptor, result)
        if not small:
            self.full_confirmed = True
        return result


def case(tmp_path, monkeypatch):
    root, runner = (tmp_path / "run").resolve(), (tmp_path / "runner").resolve()
    root.mkdir()
    runner.mkdir()
    cohort = {"items": [{"id": "synthetic-original"}]}
    write(root / "cohort.json", cohort)
    plan = {
        "phase": "full",
        "cohort_file": "cohort.json",
        "cohort_sha256": sha((root / "cohort.json").read_bytes()),
    }
    write(root / "full-plan.json", plan)
    job = identity({"synthetic": "one"})
    folder = root / "results" / job
    folder.mkdir(parents=True)
    raw = b"synthetic original result payload\x00" * 300
    (folder / "result.json.gz").write_bytes(raw)
    write(folder / "request.json", {"plan": identity(plan), "source_sha256": "public-source"})
    write(
        folder / "receipt.json",
        {
            "status": "failed",
            "failure_stage": "static_preflight",
            "source_present": True,
            "runtime_attempted": False,
        },
    )
    (folder / "signals.json.gz").write_bytes(b"synthetic signals")
    write(
        root / "verification/synthetic-original.json",
        {
            "id": "synthetic-original",
            "plan_sha256": identity(plan),
        },
    )
    write(root / "terminal-0.json", {"actual_returncode": 0})
    write(root / "worker-full-0.json", {"status": "finished", "jobs_consumed": 1})
    args = argparse.Namespace(
        run_dir=root,
        head="a" * 40,
        run_id="123",
        attempt="1",
        input_sha="b" * 64,
        shard=0,
        shards=80,
        plan="full-plan.json",
        archive=runner / "full.tar.gz",
        cipher=runner / "result-123-1-0.enc",
        key_env="COMPACT_FINISH_SYNTHETIC_KEY",
    )
    key = os.urandom(32)
    monkeypatch.setenv(args.key_env, base64.urlsafe_b64encode(key).decode())

    def guard(actual_root, head, run):
        assert (actual_root, head, run) == (root, args.head, args.run_id)
        return runner

    def frozen_inputs(actual_root, actual_plan):
        assert actual_root == root and actual_plan == plan
        assert sha((actual_root / "cohort.json").read_bytes()) == actual_plan["cohort_sha256"]
        return cohort

    upload = Upload()
    monkeypatch.setattr(finisher, "require_runner", guard)
    monkeypatch.setattr(finisher, "frozen_inputs", frozen_inputs)
    monkeypatch.setattr(finisher, "upload", upload)
    return args, key, upload, folder, raw


def test_real_crypto_compact_roundtrip_preserves_remote_raw_and_failure_evidence(
    tmp_path, monkeypatch
):
    args, key, upload, original, raw = case(tmp_path, monkeypatch)
    result = finisher.finish(args)
    assert upload.calls == ["result-123-1-0.enc", "compact-result-123-1-0.enc"]
    assert not args.archive.exists()
    assert args.cipher.read_bytes() == upload.payloads[args.cipher.name]
    assert (original / "result.json.gz").read_bytes() == raw
    assert result["storage"] == "authenticated_remote_full_payloads"
    provenance = result["provenance"]
    assert provenance["plan_sha256"] == identity(read(args.run_dir / args.plan))
    assert provenance["shards"] == 80 and provenance["attempt"] == "1"
    full = tmp_path / "full-authenticated.tar.gz"
    transform(
        "decrypt", args.cipher, full, key, f"{finisher.CONTEXT}/result/{identity(provenance)}"
    )
    relative = f"results/{original.name}/result.json.gz"
    with tarfile.open(full) as bundle:
        assert bundle.extractfile(relative).read() == raw
    small = args.cipher.with_name("compact-" + args.cipher.name)
    archive = tmp_path / "compact-authenticated.tar.gz"
    transform(
        "decrypt", small, archive, key, f"{finisher.CONTEXT}/compact-result/{identity(provenance)}"
    )
    with tarfile.open(archive) as bundle:
        assert relative not in bundle.getnames()
        certificate = json.load(bundle.extractfile("compact-certificate.json"))
    assert certificate["full_cipher"] == result["full_cipher"]
    assert certificate["omitted"][relative] == {"sha256": sha(raw), "bytes": len(raw)}
    metadata = [
        {
            "name": p["name"],
            "id": p["asset_id"],
            "size": p["bytes"],
            "digest": "sha256:" + p["sha256"],
            "state": "uploaded",
            "browser_download_url": p["browser_download_url"],
        }
        for p in result["full_cipher"]["parts"]
    ]
    collected = tmp_path / "collected"
    record = compact.collect(
        archive, collected, provenance, metadata, small, sha(small.read_bytes())
    )
    assert not (collected / relative).exists()
    assert (collected / record["cipher_file"]).read_bytes() == small.read_bytes()
    receipt = read(collected / f"results/{original.name}/receipt.json")
    assert receipt["failure_stage"] == "static_preflight" and receipt["runtime_attempted"] is False
    with compact.context(collected, key, {k: v for k, v in provenance.items() if k != "shard"}):
        compact.check_file(collected, relative, sha(raw))
    with pytest.raises(ValueError):
        compact.check_file(collected, relative, sha(raw))


def test_full_upload_failure_never_creates_compact_and_preserves_full_cipher(tmp_path, monkeypatch):
    args, key, upload, original, raw = case(tmp_path, monkeypatch)
    upload.fail_full = True
    with pytest.raises(ValueError, match="synthetic_upload_failure"):
        finisher.finish(args)
    assert upload.calls == [args.cipher.name]
    assert args.cipher.read_bytes().startswith(MAGIC)
    assert (original / "result.json.gz").read_bytes() == raw
    assert not args.cipher.with_name("compact-" + args.cipher.name).exists()
    assert not args.archive.exists()
    assert not list(args.cipher.parent.glob("editor-picks-compact-*"))
    provenance = {
        "head": args.head,
        "run_id": args.run_id,
        "attempt": args.attempt,
        "input_sha256": args.input_sha,
        "plan": args.plan,
        "plan_sha256": identity(read(args.run_dir / args.plan)),
        "shard": args.shard,
        "shards": args.shards,
    }
    recovered = tmp_path / "failed-full-authenticated.tar.gz"
    transform(
        "decrypt", args.cipher, recovered, key, f"{finisher.CONTEXT}/result/{identity(provenance)}"
    )
    with tarfile.open(recovered) as bundle:
        assert bundle.extractfile(f"results/{original.name}/result.json.gz").read() == raw


def test_compact_upload_failure_preserves_both_ciphertexts(tmp_path, monkeypatch):
    args, _, upload, original, raw = case(tmp_path, monkeypatch)
    upload.fail_compact = True
    with pytest.raises(ValueError, match="synthetic_upload_failure"):
        finisher.finish(args)
    assert upload.full_confirmed and len(upload.calls) == 2
    assert args.cipher.read_bytes().startswith(MAGIC)
    assert args.cipher.with_name("compact-" + args.cipher.name).read_bytes().startswith(MAGIC)
    assert (original / "result.json.gz").read_bytes() == raw


@pytest.mark.parametrize(
    "field,value",
    [
        ("head", "short"),
        ("run_id", "../123"),
        ("attempt", "0"),
        ("input_sha", "invalid"),
        ("shard", -1),
        ("shard", 80),
        ("shards", 257),
        ("plan", "../full-plan.json"),
    ],
)
def test_invalid_provenance_is_rejected_before_runner_or_upload(
    tmp_path, monkeypatch, field, value
):
    args, _, upload, original, raw = case(tmp_path, monkeypatch)
    setattr(args, field, value)

    def forbidden(*unused):
        pytest.fail("잘못된 provenance가 runner 권한 검사까지 도달했습니다")

    monkeypatch.setattr(finisher, "require_runner", forbidden)
    with pytest.raises(ValueError, match="provenance"):
        finisher.finish(args)
    assert not upload.calls and (original / "result.json.gz").read_bytes() == raw


@pytest.mark.parametrize(
    "change", ["outside", "name", "same_path", "archive_exists", "cipher_exists"]
)
def test_output_guard_never_overwrites_existing_or_external_files(tmp_path, monkeypatch, change):
    args, _, upload, original, raw = case(tmp_path, monkeypatch)
    protected = None
    if change == "outside":
        args.archive = tmp_path / "outside.tar.gz"
    elif change == "name":
        args.cipher = args.cipher.with_name("wrong.enc")
    elif change == "same_path":
        args.archive = args.cipher
    else:
        protected = args.archive if change == "archive_exists" else args.cipher
        protected.write_bytes(b"keep existing user file")
    with pytest.raises(ValueError, match="임시 출력"):
        finisher.finish(args)
    assert not upload.calls and (original / "result.json.gz").read_bytes() == raw
    if protected:
        assert protected.read_bytes() == b"keep existing user file"


def test_invalid_key_is_rejected_before_pack_or_upload(tmp_path, monkeypatch):
    args, _, upload, _, _ = case(tmp_path, monkeypatch)
    monkeypatch.setenv(args.key_env, base64.urlsafe_b64encode(b"short").decode())
    with pytest.raises(ValueError, match="키 길이"):
        finisher.finish(args)
    assert not upload.calls and not args.archive.exists() and not args.cipher.exists()
