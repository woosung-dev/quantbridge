"""인증된 compact 결과만 원래 raw 해시 참조를 제공한다."""

import copy
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import compact as c
from tools.research.editor_picks.common import identity, read, sha, write
from tools.research.editor_picks.crypto import transform
from tools.research.editor_picks.remote import remote_namespace

KEY = b"k" * 32


def archive(path, files):
    with tarfile.open(path, "w:gz") as output:
        for name, value in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(value)
            output.addfile(member, io.BytesIO(value))


def setup_bundle(tmp_path):
    expected = {
        "plan_sha256": "a" * 64,
        "head": "f" * 40,
        "run_id": "1234",
        "attempt": 1,
        "shards": 2,
        "shard": 0,
        "input_sha256": "b" * 64,
    }
    job = "c" * 64
    prefix = str(remote_namespace(expected) / "0")
    files = {
        f"results/{job}/result.json.gz": b"original gzip bytes\x00" * 200,
        f"results/{job}/receipt.json": b'{"status":"completed","source_sha256":"source-original"}',
        f"results/{job}/request.json": b'{"source_sha256":"source-original"}',
        f"results/{job}/signals.json": b'{"events":[]}',
        f"results/{job}/other-result.json.gz": b"kept nonmatching filename",
        "native-checks/one.json": json.dumps(
            {"id": "one", "plan_sha256": expected["plan_sha256"]}
        ).encode(),
        prefix + "/terminal-0.json": b'{"complete":true}',
        prefix + "/runtime-installed.json": b'{"image":"frozen"}',
    }
    envelope = {**expected, "files": {name: sha(value) for name, value in files.items()}}
    files[prefix + "/envelope.json"] = json.dumps(envelope).encode()
    full = tmp_path / "full.tar.gz"
    archive(full, files)
    full_cipher = tmp_path / "full.enc"
    transform("encrypt", full, full_cipher, KEY, "original-full")
    descriptor = {
        "schema_version": 1,
        "sha256": sha(full_cipher.read_bytes()),
        "bytes": full_cipher.stat().st_size,
        "parts": [
            {
                "name": "full.enc",
                "sha256": sha(full_cipher.read_bytes()),
                "bytes": full_cipher.stat().st_size,
                "asset_id": 12,
                "browser_download_url": "https://github.com/woosung-dev/quantbridge/releases/download/editor-picks-research-20261024/full.enc",
            }
        ],
    }
    stage = tmp_path / "stage"
    certificate = c.prepare(full, expected, stage)
    compact_archive = tmp_path / "compact.tar.gz"
    c.seal(stage, descriptor, compact_archive)
    cipher = tmp_path / "compact.enc"
    transform(
        "encrypt",
        compact_archive,
        cipher,
        KEY,
        "editor-picks-20261024/compact-result/" + identity(expected),
    )
    metadata = [
        {
            "id": part["asset_id"],
            "name": part["name"],
            "size": part["bytes"],
            "digest": "sha256:" + part["sha256"],
            "state": "uploaded",
            "browser_download_url": part["browser_download_url"],
        }
        for part in descriptor["parts"]
    ]
    return expected, files, certificate, compact_archive, cipher, metadata


def collect_bundle(tmp_path):
    values = setup_bundle(tmp_path)
    expected, _, _, archive_path, cipher, metadata = values
    root = tmp_path / "collected"
    record = c.collect(archive_path, root, expected, metadata, cipher, sha(cipher.read_bytes()))
    return root, record, values


def test_roundtrip_preserves_all_critical_bytes_and_explicitly_omits_only_raw(tmp_path):
    root, record, (expected, files, cert, _, cipher, _) = collect_bundle(tmp_path)
    omitted = next(iter(cert["omitted"]))
    assert list(cert["omitted"]) == [omitted]
    assert cert["omitted"][omitted] == {"sha256": sha(files[omitted]), "bytes": len(files[omitted])}
    assert not (root / omitted).exists()
    for name in cert["kept"]:
        assert (root / name).read_bytes() == files[name]
    assert (root / record["cipher_file"]).read_bytes() == cipher.read_bytes()
    with pytest.raises(ValueError):
        c.check_file(root, omitted, sha(files[omitted]))
    with c.context(root, KEY, {"plan_sha256": expected["plan_sha256"], "head": expected["head"]}):
        assert c.check_file(root, omitted, sha(files[omitted])) is None
        for name in cert["kept"]:
            assert c.check_file(root, name, sha(files[name])) is None
        with pytest.raises(ValueError):
            c.check_file(root, omitted, "d" * 64)
        with pytest.raises(ValueError):
            c.check_file(
                root, omitted.replace("result.json.gz", "missing.json"), sha(files[omitted])
            )
    with pytest.raises(ValueError):
        c.check_file(root, omitted, sha(files[omitted]))


@pytest.mark.parametrize(
    "change",
    [
        "receipt",
        "source_field",
        "native_plan",
        "missing",
        "provenance",
        "traversal",
        "duplicate",
        "symlink",
    ],
)
def test_prepare_rejects_original_tampering_and_does_not_leave_stage(tmp_path, change):
    expected, files, _, _, _, _ = setup_bundle(tmp_path)
    receipt = next(name for name in files if name.endswith("receipt.json"))
    if change in {"receipt", "source_field"}:
        files[receipt] = b'{"source_sha256":"altered"}'
    elif change == "native_plan":
        files["native-checks/one.json"] = b'{"id":"one","plan_sha256":"wrong"}'
    elif change == "missing":
        del files[receipt]
    elif change == "provenance":
        expected = {**expected, "attempt": 2}
    elif change == "traversal":
        files["../escaped"] = b"no"
    target = tmp_path / "tampered.tar.gz"
    archive(target, files)
    if change in {"duplicate", "symlink"}:
        with tarfile.open(target, "w:gz") as output:
            member = tarfile.TarInfo(receipt)
            if change == "symlink":
                member.type = tarfile.SYMTYPE
                member.linkname = "/outside"
                output.addfile(member)
            else:
                member.size = 1
                output.addfile(member, io.BytesIO(b"a"))
                output.addfile(member, io.BytesIO(b"a"))
    stage = tmp_path / "rejected-stage"
    with pytest.raises((ValueError, FileNotFoundError)):
        c.prepare(target, expected, stage)
    assert not stage.exists()
    assert not (tmp_path / "escaped").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("digest", "sha256:" + "0" * 64),
        ("size", 1),
        ("id", 13),
        ("state", "new"),
        ("browser_download_url", "https://github.com/attacker/repo/full.enc"),
    ],
)
def test_collect_requires_actual_uploaded_full_assets(tmp_path, field, value):
    expected, _, _, archive_path, cipher, metadata = setup_bundle(tmp_path)
    metadata[0][field] = value
    with pytest.raises(ValueError):
        c.collect(
            archive_path, tmp_path / "root", expected, metadata, cipher, sha(cipher.read_bytes())
        )
    assert not (tmp_path / "root").exists()


@pytest.mark.parametrize(
    "change", ["kept_bytes", "missing_kept", "omit_receipt", "omitted_sha", "provenance"]
)
def test_compact_certificate_cannot_hide_or_modify_critical_evidence(tmp_path, change):
    expected, _, _, archive_path, cipher, metadata = setup_bundle(tmp_path)
    stage = tmp_path / "unpacked"
    actual = c._stream(archive_path, stage)
    cert = read(stage / c._CERT)
    receipt = next(name for name in cert["kept"] if name.endswith("receipt.json"))
    if change == "kept_bytes":
        (stage / receipt).write_bytes(b"changed")
    elif change == "missing_kept":
        (stage / receipt).unlink()
    elif change == "omit_receipt":
        cert["omitted"][receipt] = cert["kept"].pop(receipt)
        (stage / receipt).unlink()
    elif change == "omitted_sha":
        next(iter(cert["omitted"].values()))["sha256"] = "d" * 64
    else:
        cert["provenance"]["head"] = "wrong"
    write(stage / c._CERT, cert)
    altered = tmp_path / "altered.tar.gz"
    archive(
        altered,
        {
            str(path.relative_to(stage)): path.read_bytes()
            for path in stage.rglob("*")
            if path.is_file()
        },
    )
    with pytest.raises(ValueError):
        c.collect(altered, tmp_path / "root", expected, metadata, cipher, sha(cipher.read_bytes()))
    assert actual


@pytest.mark.parametrize("change", ["key", "aad", "cipher", "kept", "base", "record"])
def test_context_reauthenticates_cipher_and_critical_files(tmp_path, change):
    root, record, (expected, files, cert, archive_path, _, _) = collect_bundle(tmp_path)
    cipher_path = root / record["cipher_file"]
    key = KEY
    base = {"plan_sha256": expected["plan_sha256"]}
    if change == "key":
        key = b"x" * 32
    elif change == "aad":
        cipher_path.unlink()
        transform("encrypt", archive_path, cipher_path, KEY, "wrong-aad")
        record["cipher"] = c._hash(cipher_path)
        write(root / f"compact-collections/{identity(expected)}/collection.json", record)
    elif change == "cipher":
        cipher_path.write_bytes(cipher_path.read_bytes()[:-1] + b"x")
    elif change == "kept":
        (root / next(name for name in cert["kept"] if name.endswith("receipt.json"))).write_bytes(
            b"changed"
        )
    elif change == "base":
        base["plan_sha256"] = "wrong"
    else:
        record["provenance"]["head"] = "wrong"
        write(root / f"compact-collections/{identity(expected)}/collection.json", record)
    with pytest.raises(Exception), c.context(root, key, base):
        pass
    omitted = next(iter(cert["omitted"]))
    with pytest.raises(ValueError):
        c.check_file(root, omitted, sha(files[omitted]))


def test_context_restores_nested_context_and_exception_without_cross_root_leak(tmp_path):
    root, _, (expected, files, cert, _, _, _) = collect_bundle(tmp_path)
    name = next(iter(cert["omitted"]))
    with c.context(root, KEY, expected):
        with pytest.raises(RuntimeError), c.context(root, KEY, expected):
            raise RuntimeError("trusted failure")
        c.check_file(root, name, sha(files[name]))
        with pytest.raises(ValueError):
            c.check_file(tmp_path / "other-root", name, sha(files[name]))
    assert c._OMITTED.get() is None


def test_collect_is_idempotent_but_existing_evidence_conflicts_are_rejected(tmp_path):
    root, record, (expected, _, _, archive_path, cipher, metadata) = collect_bundle(tmp_path)
    assert (
        c.collect(archive_path, root, expected, metadata, cipher, sha(cipher.read_bytes()))
        == record
    )
    receipt = next((root / "results").glob("*/receipt.json"))
    receipt.write_bytes(b"changed")
    with pytest.raises(ValueError):
        c.collect(archive_path, root, expected, metadata, cipher, sha(cipher.read_bytes()))


@pytest.mark.parametrize(
    "change", ["unknown", "owner", "tag", "part_sha", "full_sha", "size", "duplicate", "order"]
)
def test_full_cipher_descriptor_is_strict(tmp_path, change):
    _, _, _, _, _, _ = setup_bundle(tmp_path)
    cert = read(tmp_path / "stage" / c._CERT)
    descriptor = copy.deepcopy(cert["full_cipher"])
    part = descriptor["parts"][0]
    if change == "unknown":
        descriptor["ignored"] = True
    elif change in {"owner", "tag"}:
        part["browser_download_url"] = (
            part["browser_download_url"].replace("woosung-dev", "other")
            if change == "owner"
            else part["browser_download_url"].replace("editor-picks-research-20261024", "other-tag")
        )
    elif change == "part_sha":
        part["sha256"] = "wrong"
    elif change == "full_sha":
        descriptor["sha256"] = "d" * 64
    elif change == "size":
        descriptor["bytes"] += 1
    else:
        descriptor["parts"].append(copy.deepcopy(part))
        descriptor["bytes"] *= 2
        if change == "order":
            for index, item in enumerate(descriptor["parts"]):
                item["name"] = f"full.enc.part{1 - index:04d}"
                item["browser_download_url"] = (
                    item["browser_download_url"].rsplit("/", 1)[0] + "/" + item["name"]
                )
    with pytest.raises(ValueError):
        c._descriptor(descriptor)


def test_physical_raw_tamper_is_not_hidden_by_authenticated_omission(tmp_path):
    root, _, (expected, files, cert, _, _, _) = collect_bundle(tmp_path)
    omitted = next(iter(cert["omitted"]))
    with c.context(root, KEY, expected):
        path = root / omitted
        path.write_bytes(b"tampered local raw")
        with pytest.raises(ValueError):
            c.check_file(root, omitted, sha(files[omitted]))


def test_context_map_is_immutable_and_empty_root_cannot_authorize_missing_raw(tmp_path):
    root, _, (expected, files, cert, _, _, _) = collect_bundle(tmp_path)
    omitted = next(iter(cert["omitted"]))
    with c.context(root, KEY, expected), pytest.raises(TypeError):
        c._OMITTED.get()[1][omitted] = "d" * 64
    with c.context(tmp_path / "empty", KEY, expected), pytest.raises(ValueError):
        c.check_file(tmp_path / "empty", omitted, sha(files[omitted]))
    assert c._OMITTED.get() is None


def test_collect_rejects_wrong_authenticated_cipher_sha(tmp_path):
    expected, _, _, archive_path, cipher, metadata = setup_bundle(tmp_path)
    with pytest.raises(ValueError):
        c.collect(archive_path, tmp_path / "root", expected, metadata, cipher, "d" * 64)


def test_multipart_manifest_preserves_order_and_metadata_listing_order_is_irrelevant(tmp_path):
    expected, _, _, _, _, _ = setup_bundle(tmp_path)
    stage = tmp_path / "stage"
    certificate = read(stage / c._CERT)
    original = (tmp_path / "full.enc").read_bytes()
    cut = len(original) // 2
    certificate["full_cipher"]["parts"] = [
        {
            "name": f"full.enc.part{index:04d}",
            "sha256": sha(block),
            "bytes": len(block),
            "asset_id": 20 + index,
            "browser_download_url": f"https://github.com/woosung-dev/quantbridge/releases/download/editor-picks-research-20261024/full.enc.part{index:04d}",
        }
        for index, block in enumerate((original[:cut], original[cut:]))
    ]
    write(stage / c._CERT, certificate)
    compact_archive = tmp_path / "multipart.tar.gz"
    archive(
        compact_archive,
        {
            str(path.relative_to(stage)): path.read_bytes()
            for path in stage.rglob("*")
            if path.is_file()
        },
    )
    cipher = tmp_path / "multipart.enc"
    transform(
        "encrypt",
        compact_archive,
        cipher,
        KEY,
        "editor-picks-20261024/compact-result/" + identity(expected),
    )
    metadata = [
        {
            "id": part["asset_id"],
            "name": part["name"],
            "size": part["bytes"],
            "digest": "sha256:" + part["sha256"],
            "state": "uploaded",
            "browser_download_url": part["browser_download_url"],
        }
        for part in certificate["full_cipher"]["parts"]
    ]
    root = tmp_path / "multipart-root"
    first = c.collect(compact_archive, root, expected, metadata, cipher, sha(cipher.read_bytes()))
    assert (
        c.collect(
            compact_archive,
            root,
            expected,
            list(reversed(metadata)),
            cipher,
            sha(cipher.read_bytes()),
        )
        == first
    )
    with c.context(root, KEY, expected):
        for name, value in certificate["omitted"].items():
            c.check_file(root, name, value["sha256"])
