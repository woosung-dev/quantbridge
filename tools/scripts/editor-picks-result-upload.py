"""QBENC7 암호문만 분할 업로드하고 실제 GitHub asset의 SHA를 결박한다."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

REPO = "woosung-dev/quantbridge"
TAG = "editor-picks-research-20261024"
PART_BYTES = 1024**3
BLOCK_BYTES = 1024**2
# tools/research/editor_picks/crypto.py의 암호문 식별자. 키·평문은 읽지 않는다.
MAGIC = b"QBENC7\x00"


def gh(*arguments):
    environment = {
        key: value for key, value in os.environ.items() if key not in {"GH_DEBUG", "DEBUG"}
    }
    environment["GH_HOST"] = "github.com"
    try:
        return subprocess.run(  # noqa: S603 — 고정 owner release에 검증한 암호문·asset 이름만 전달한다.
            ["gh", *arguments],  # noqa: S607 — runner에 설치된 GitHub CLI를 사용한다.
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
    except subprocess.CalledProcessError:
        raise ValueError("github_request_failed") from None


def assets(release_id):
    pages = json.loads(
        gh(
            "api",
            "--paginate",
            "--slurp",
            f"repos/{REPO}/releases/{release_id}/assets?per_page=100",
        )
    )
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError("invalid_asset_listing")
    return [asset for page in pages for asset in page]


def remote_part(entries, name, size, digest):
    matches = [entry for entry in entries if entry.get("name") == name]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("duplicate_remote_asset_name")
    asset = matches[0]
    url = f"https://github.com/{REPO}/releases/download/{TAG}/{name}"
    if (
        asset.get("state") != "uploaded"
        or type(asset.get("size")) is not int
        or asset["size"] != size
        or asset.get("digest") != f"sha256:{digest}"
        or type(asset.get("id")) is not int
        or asset["id"] <= 0
        or asset.get("browser_download_url") != url
    ):
        raise ValueError("remote_asset_conflict")
    return {
        "name": name,
        "sha256": digest,
        "bytes": size,
        "asset_id": asset["id"],
        "browser_download_url": url,
    }


def describe(stream, part_bytes):
    if stream.read(len(MAGIC)) != MAGIC:
        raise ValueError("encrypted_QBENC7_input_required")
    stream.seek(0)
    whole = hashlib.sha256()
    parts = []
    while True:
        digest, size = hashlib.sha256(), 0
        while size < part_bytes:
            block = stream.read(min(BLOCK_BYTES, part_bytes - size))
            if not block:
                break
            whole.update(block)
            digest.update(block)
            size += len(block)
        if not size:
            break
        parts.append({"sha256": digest.hexdigest(), "bytes": size})
    size = sum(part["bytes"] for part in parts)
    if size < len(MAGIC) + 8 + 4 + 16:
        raise ValueError("truncated_encrypted_input")
    return {
        "schema_version": 1,
        "sha256": whole.hexdigest(),
        "bytes": size,
        "parts": parts,
    }


def write_descriptor(path, value):
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.is_symlink() or json.loads(path.read_bytes()) != value:
            raise ValueError("existing_descriptor_conflict") from None
        return
    with os.fdopen(descriptor, "wb") as output:
        owned = os.fstat(output.fileno())
        try:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        except BaseException:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                path.unlink()
            raise


def upload(cipher, output, repo, tag, asset_name, *, part_bytes=PART_BYTES):
    cipher, output = Path(cipher), Path(output)
    if repo != REPO or tag != TAG:
        raise ValueError("owner_release_only")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,170}\.enc", asset_name):
        raise ValueError("unsafe_cipher_asset_name")
    if type(part_bytes) is not int or not 1 <= part_bytes <= PART_BYTES:
        raise ValueError("invalid_part_size")
    if cipher.is_symlink() or output.is_symlink() or cipher.resolve() == output.resolve():
        raise ValueError("unsafe_local_path")
    if not output.parent.is_dir():
        raise ValueError("descriptor_parent_missing")
    # fd를 고정하고 분할 전후 각 part SHA를 비교한다. 업로드는 검증한 사본만 읽는다.
    descriptor = os.open(cipher, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("regular_cipher_file_required")
        result = describe(source, part_bytes)
        for index, part in enumerate(result["parts"]):
            part["name"] = (
                asset_name if len(result["parts"]) == 1 else f"{asset_name}.part{index:04d}"
            )
        if output.exists():
            previous = json.loads(output.read_bytes())
            if (
                any(
                    previous.get(key) != result[key]
                    for key in ("schema_version", "sha256", "bytes")
                )
                or [
                    {key: part.get(key) for key in ("name", "sha256", "bytes")}
                    for part in previous.get("parts", [])
                ]
                != result["parts"]
            ):
                raise ValueError("existing_descriptor_conflict")
        release = json.loads(gh("api", f"repos/{REPO}/releases/tags/{TAG}"))
        if (
            release.get("tag_name") != TAG
            or type(release.get("id")) is not int
            or release["id"] <= 0
        ):
            raise ValueError("invalid_owner_release")
        release_id = release["id"]
        known = assets(release_id)
        missing = sum(
            remote_part(known, part["name"], part["bytes"], part["sha256"]) is None
            for part in result["parts"]
        )
        if len(known) + missing > 1000:
            raise ValueError("release_asset_limit_exceeded")
        source.seek(0)
        verified = []
        with tempfile.TemporaryDirectory(prefix="qb-encrypted-result-upload-") as directory:
            for part in result["parts"]:
                path = Path(directory) / part["name"]
                digest = hashlib.sha256()
                remaining = part["bytes"]
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as local:
                    while remaining:
                        block = source.read(min(BLOCK_BYTES, remaining))
                        if not block:
                            raise ValueError("cipher_changed_during_split")
                        local.write(block)
                        digest.update(block)
                        remaining -= len(block)
                if digest.hexdigest() != part["sha256"]:
                    raise ValueError("cipher_changed_during_split")
                asset = remote_part(known, part["name"], part["bytes"], part["sha256"])
                if asset is None:
                    gh("release", "upload", TAG, str(path), "--repo", REPO)
                    known = assets(release_id)
                    asset = remote_part(known, part["name"], part["bytes"], part["sha256"])
                    if asset is None:
                        raise ValueError("uploaded_asset_missing")
                verified.append(asset)
                path.unlink()  # 이번 호출에서 O_EXCL로 만든 part만 정리한다.
            if source.read(1):
                raise ValueError("cipher_changed_during_split")
        result["parts"] = verified
        write_descriptor(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--asset-name", required=True)
    args = parser.parse_args()
    try:
        upload(args.input, args.output, args.repo, args.tag, args.asset_name)
    except Exception as error:
        # HTTP 응답·경로·인증값·암호문을 터미널이나 CI 로그에 노출하지 않는다.
        raise SystemExit(f"encrypted_result_upload_failed:{type(error).__name__}") from None


if __name__ == "__main__":
    main()
