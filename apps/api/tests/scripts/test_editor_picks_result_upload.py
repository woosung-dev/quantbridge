"""암호문 분할·실제 asset 결박·불변 재호출만 합성 GitHub 응답으로 검사한다."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "result_upload", ROOT / "tools/scripts/editor-picks-result-upload.py"
)
uploader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uploader)


class GitHub:
    def __init__(self):
        self.entries = []
        self.bodies = {}
        self.uploads = []
        self.fail_upload = False
        self.corrupt = None

    def __call__(self, *args):
        if args[:1] == ("api",):
            if "/tags/" in args[-1]:
                return json.dumps({"id": 7, "tag_name": uploader.TAG}).encode()
            assert args[1:3] == ("--paginate", "--slurp")
            return json.dumps([self.entries]).encode()
        assert args[:3] == ("release", "upload", uploader.TAG)
        assert args[4:] == ("--repo", uploader.REPO)
        assert "--clobber" not in args
        path = Path(args[3])
        self.uploads.append(path)
        if self.fail_upload:
            raise ValueError("synthetic_upload_failure")
        body = path.read_bytes()
        self.bodies[path.name] = body
        entry = {
            "id": len(self.entries) + 1,
            "name": path.name,
            "state": "uploaded",
            "size": len(body),
            "digest": "sha256:" + hashlib.sha256(body).hexdigest(),
            "browser_download_url": f"https://github.com/{uploader.REPO}/releases/download/{uploader.TAG}/{path.name}",
        }
        if self.corrupt:
            entry[self.corrupt] = {
                "digest": "sha256:" + "0" * 64,
                "size": len(body) + 1,
                "state": "starter",
                "id": True,
                "browser_download_url": "https://example.invalid/asset",
            }[self.corrupt]
        self.entries.append(entry)
        return b""


def fixture(tmp_path, monkeypatch):
    github = GitHub()
    monkeypatch.setattr(uploader, "gh", github)
    cipher = tmp_path / "original.enc"
    cipher.write_bytes(uploader.MAGIC + bytes(range(128)))
    return github, cipher, tmp_path / "descriptor.json"


def invoke(cipher, output, **kwargs):
    return uploader.upload(
        cipher, output, uploader.REPO, uploader.TAG, "result-123-1-0.enc", **kwargs
    )


def test_streamed_parts_restore_exact_cipher_and_remote_descriptor(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    before = cipher.read_bytes()
    descriptor = invoke(cipher, output, part_bytes=32)
    assert descriptor == json.loads(output.read_bytes())
    assert set(descriptor) == {"schema_version", "sha256", "bytes", "parts"}
    assert descriptor["sha256"] == hashlib.sha256(before).hexdigest()
    assert descriptor["bytes"] == len(before) == sum(part["bytes"] for part in descriptor["parts"])
    assert [part["name"] for part in descriptor["parts"]] == [
        f"result-123-1-0.enc.part{index:04d}" for index in range(5)
    ]
    assert b"".join(github.bodies[part["name"]] for part in descriptor["parts"]) == before
    for part in descriptor["parts"]:
        assert set(part) == {"name", "sha256", "bytes", "asset_id", "browser_download_url"}
        assert part["bytes"] <= 32
        assert part["sha256"] == hashlib.sha256(github.bodies[part["name"]]).hexdigest()
    assert cipher.read_bytes() == before
    assert all(not path.exists() and not path.parent.exists() for path in github.uploads)
    assert output.stat().st_mode & 0o777 == 0o600


def test_same_descriptor_and_remote_parts_are_reused_without_upload(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    first = invoke(cipher, output, part_bytes=32)
    before = output.read_bytes()
    uploads = len(github.uploads)
    assert invoke(cipher, output, part_bytes=32) == first
    assert len(github.uploads) == uploads
    assert output.read_bytes() == before


def test_small_cipher_keeps_original_asset_name(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    result = invoke(cipher, output)
    assert [part["name"] for part in result["parts"]] == ["result-123-1-0.enc"]
    assert len(github.uploads) == 1


@pytest.mark.parametrize("field", ["digest", "size", "state", "id", "browser_download_url"])
def test_actual_uploaded_metadata_must_match(tmp_path, monkeypatch, field):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    github.corrupt = field
    with pytest.raises(ValueError, match="remote_asset_conflict"):
        invoke(cipher, output, part_bytes=32)
    assert not output.exists()
    assert cipher.exists()
    assert all(not path.parent.exists() for path in github.uploads)


def test_failed_upload_leaves_no_descriptor_or_owned_parts(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    github.fail_upload = True
    with pytest.raises(ValueError, match="synthetic_upload_failure"):
        invoke(cipher, output, part_bytes=32)
    assert not output.exists() and cipher.exists()
    assert all(not path.parent.exists() for path in github.uploads)


def test_retry_reuses_only_verified_parts_after_partial_upload(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)

    def fail_third(*args):
        if args[:1] == ("release",) and len(github.uploads) == 2:
            raise ValueError("synthetic_partial_failure")
        return github(*args)

    monkeypatch.setattr(uploader, "gh", fail_third)
    with pytest.raises(ValueError, match="synthetic_partial_failure"):
        invoke(cipher, output, part_bytes=32)
    assert not output.exists() and len(github.entries) == 2
    monkeypatch.setattr(uploader, "gh", github)
    assert len(invoke(cipher, output, part_bytes=32)["parts"]) == 5
    assert len(github.uploads) == 5


def test_remote_name_collision_never_overwrites(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    invoke(cipher, output)
    github.entries[0]["digest"] = "sha256:" + "0" * 64
    before = output.read_bytes()
    with pytest.raises(ValueError, match="remote_asset_conflict"):
        invoke(cipher, output)
    assert len(github.uploads) == 1 and output.read_bytes() == before


def test_existing_descriptor_conflict_is_not_overwritten(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    output.write_text('{"private":"keep"}')
    before = output.read_bytes()
    with pytest.raises(ValueError, match="existing_descriptor_conflict"):
        invoke(cipher, output)
    assert output.read_bytes() == before and not github.uploads


def test_cipher_mutation_is_rejected_before_upload(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)

    def mutate(*args):
        if args[:1] == ("api",) and "/tags/" in args[-1]:
            cipher.write_bytes(b"PRIVATE_PLAINTEXT" * 20)
        return github(*args)

    monkeypatch.setattr(uploader, "gh", mutate)
    with pytest.raises(ValueError, match="cipher_changed_during_split"):
        invoke(cipher, output, part_bytes=32)
    assert not github.uploads and not output.exists()


def test_release_quota_is_checked_before_any_upload(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    github.entries = [{"name": f"other-{index}"} for index in range(1000)]
    with pytest.raises(ValueError, match="release_asset_limit_exceeded"):
        invoke(cipher, output)
    assert not github.uploads and not output.exists()


@pytest.mark.parametrize(
    "name",
    [
        "../result.enc",
        "--clobber.enc",
        "a;pwd.enc",
        "a.enc#label",
        "a\n.enc",
        "source.py",
        "/absolute.enc",
    ],
)
def test_asset_name_injection_is_rejected_before_network(tmp_path, monkeypatch, name):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="unsafe_cipher_asset_name"):
        uploader.upload(cipher, output, uploader.REPO, uploader.TAG, name)
    assert not github.uploads and not output.exists()


@pytest.mark.parametrize(
    "repo,tag",
    [("other/quantbridge", uploader.TAG), (uploader.REPO, "other"), (uploader.REPO, "../tag")],
)
def test_only_owner_release_is_allowed(tmp_path, monkeypatch, repo, tag):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="owner_release_only"):
        uploader.upload(cipher, output, repo, tag, "result.enc")
    assert not github.uploads and not output.exists()


@pytest.mark.parametrize(
    "body", [b"secret-value", b"//@version=6\nindicator('source')", uploader.MAGIC]
)
def test_plaintext_or_truncated_header_is_never_uploaded(tmp_path, monkeypatch, body):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    cipher.write_bytes(body)
    with pytest.raises(ValueError):
        invoke(cipher, output)
    assert not github.uploads and not output.exists() and cipher.read_bytes() == body


def test_descriptor_symlink_and_cipher_symlink_are_not_followed(tmp_path, monkeypatch):
    github, cipher, output = fixture(tmp_path, monkeypatch)
    other = tmp_path / "user-file"
    other.write_text("keep")
    output.symlink_to(other)
    with pytest.raises(ValueError, match="unsafe_local_path"):
        invoke(cipher, output)
    assert other.read_text() == "keep" and not github.uploads
    alias = tmp_path / "cipher-link"
    alias.symlink_to(cipher)
    with pytest.raises(ValueError, match="unsafe_local_path"):
        invoke(alias, tmp_path / "other.json")


def test_subprocess_uses_argv_and_redacts_failures(monkeypatch, capsys):
    def fail(args, **kwargs):
        assert args == ["gh", "api", "fixed"]
        assert kwargs["capture_output"] is True
        raise uploader.subprocess.CalledProcessError(
            1, args, output=b"token-value", stderr=b"private-body"
        )

    monkeypatch.setattr(uploader.subprocess, "run", fail)
    with pytest.raises(ValueError, match=r"^github_request_failed$"):
        uploader.gh("api", "fixed")
    assert capsys.readouterr() == ("", "")
