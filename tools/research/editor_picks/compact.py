"""원본 암호문을 보존하고 인증된 원시 결과 해시만 제한적으로 참조한다."""

from __future__ import annotations

import hashlib
import re
import shutil
import tarfile
import tempfile
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from urllib.parse import urlsplit

from .common import checked_file, identity, read, write
from .crypto import transform

_CERT = "compact-certificate.json"
_OMIT = re.compile(r"results/[0-9a-f]{64}/result\.json\.gz")
_HEX = re.compile(r"[0-9a-f]{64}")
_OMITTED: ContextVar[tuple[Path, Mapping[str, str]] | None] = ContextVar(
    "compact_omitted", default=None
)


def _path(name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("compact 경로가 잘못됐습니다")
    value = PurePosixPath(name)
    if (
        value.is_absolute()
        or any(part in {".", ".."} for part in value.parts)
        or str(value) != name
    ):
        raise ValueError("compact 상대 경로만 허용합니다")
    return name


def _digest(value):
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError("compact SHA256 형식이 잘못됐습니다")
    return value


def _hash(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _prefix(expected):
    from .remote import remote_namespace

    return str(remote_namespace(expected) / str(expected["shard"]))


def _allowed(name, prefix):
    if not (
        name.startswith("results/")
        or name.startswith("native-checks/")
        or name.startswith(prefix + "/")
    ):
        raise ValueError("compact 원래 결과 경로 밖의 파일입니다")


def _stream(archive, destination=None, omit=False):
    """링크·중복 없이 모든 member를 실제로 읽어 SHA와 크기를 계산한다."""
    files = {}
    with tarfile.open(archive, "r|gz") as incoming:
        for member in incoming:
            name = _path(member.name)
            if not member.isfile() or name in files:
                raise ValueError("compact 파일 외 member 또는 중복 경로입니다")
            output = None
            try:
                if destination is not None and not (omit and _OMIT.fullmatch(name)):
                    target = destination / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    output = target.open("xb")
                digest = hashlib.sha256()
                size = 0
                stream = incoming.extractfile(member)
                if stream is None:
                    raise ValueError("compact member를 읽을 수 없습니다")
                with stream:
                    while block := stream.read(1024 * 1024):
                        digest.update(block)
                        size += len(block)
                        if output is not None:
                            output.write(block)
                if size != member.size:
                    raise ValueError("compact member 크기가 다릅니다")
                files[name] = {"sha256": digest.hexdigest(), "bytes": size}
            finally:
                if output is not None:
                    output.close()
    return files


def _envelope(folder, expected, files):
    name = _prefix(expected) + "/envelope.json"
    if name not in files:
        raise ValueError("compact 원래 envelope가 없습니다")
    envelope = read(folder / name)
    if set(envelope) != set(expected) | {"files"} or identity(
        {k: envelope.get(k) for k in expected}
    ) != identity(expected):
        raise ValueError("compact provenance가 다릅니다")
    declared = envelope.get("files")
    if not isinstance(declared, dict) or set(files) != set(declared) | {name}:
        raise ValueError("compact 원래 파일 목록이 다릅니다")
    for relative, digest in declared.items():
        _path(relative)
        _allowed(relative, _prefix(expected))
        if files[relative]["sha256"] != _digest(digest):
            raise ValueError("compact 원래 파일 SHA가 다릅니다")
        if relative.startswith("native-checks/"):
            proof = read(folder / relative)
            if (
                proof.get("plan_sha256") != expected["plan_sha256"]
                or relative != f"native-checks/{proof.get('id')}.json"
            ):
                raise ValueError("compact native proof의 plan 또는 ID가 다릅니다")
    return envelope


def prepare(full_archive: Path, expected_provenance: dict, stage: Path) -> dict:
    """전체 원본을 스트림 검증하고 정확한 result.json.gz만 stage에서 제외한다."""
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=False)
    try:
        files = _stream(full_archive, stage, omit=True)
        envelope = _envelope(stage, expected_provenance, files)
        certificate = {
            "schema_version": 1,
            "provenance": expected_provenance,
            "envelope": envelope,
            "envelope_file": _prefix(expected_provenance) + "/envelope.json",
            "full_archive": _hash(full_archive),
            "kept": {name: value for name, value in files.items() if not _OMIT.fullmatch(name)},
            "omitted": {name: value for name, value in files.items() if _OMIT.fullmatch(name)},
            "scope": "authenticated_omitted_hashes_not_local_raw_files",
        }
        write(stage / _CERT, certificate)
        return certificate
    except BaseException:
        shutil.rmtree(stage)
        raise


def _descriptor(value, metadata=None):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "sha256", "bytes", "parts"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
    ):
        raise ValueError("full cipher descriptor 형식이 다릅니다")
    _digest(value["sha256"])
    if (
        type(value["bytes"]) is not int
        or value["bytes"] <= 0
        or not isinstance(value["parts"], list)
        or not value["parts"]
    ):
        raise ValueError("full cipher 크기·parts가 잘못됐습니다")
    names = set()
    for part in value["parts"]:
        if not isinstance(part, dict) or set(part) != {
            "name",
            "sha256",
            "bytes",
            "asset_id",
            "browser_download_url",
        }:
            raise ValueError("full cipher part 형식이 다릅니다")
        name = _path(part["name"])
        url = urlsplit(part["browser_download_url"])
        path = url.path.split("/")
        if (
            "/" in name
            or name in names
            or type(part["bytes"]) is not int
            or not 0 < part["bytes"] <= 1024**3
            or type(part["asset_id"]) is not int
            or part["asset_id"] <= 0
        ):
            raise ValueError("full cipher part 이름·크기·ID가 잘못됐습니다")
        if not (
            url.scheme == "https"
            and url.netloc == "github.com"
            and not url.query
            and not url.fragment
            and len(path) == 7
            and path[1:5] == ["woosung-dev", "quantbridge", "releases", "download"]
            and path[5] == "editor-picks-research-20261024"
            and path[6] == name
        ):
            raise ValueError("full cipher asset 소유자·release URL이 다릅니다")
        _digest(part["sha256"])
        names.add(name)
    if len(value["parts"]) == 1 and value["parts"][0]["sha256"] != value["sha256"]:
        raise ValueError("단일 full cipher part의 SHA가 전체 SHA와 다릅니다")
    if len(value["parts"]) > 1:
        base = value["parts"][0]["name"].removesuffix(".part0000")
        if any(
            part["name"] != f"{base}.part{index:04d}" for index, part in enumerate(value["parts"])
        ):
            raise ValueError("full cipher part 순서가 다릅니다")
    if sum(part["bytes"] for part in value["parts"]) != value["bytes"]:
        raise ValueError("full cipher part 총 크기가 다릅니다")
    if metadata is not None:
        if not isinstance(metadata, list) or len(metadata) != len(value["parts"]):
            raise ValueError("GitHub full asset 목록이 다릅니다")
        actual = {item.get("name"): item for item in metadata if isinstance(item, dict)}
        if len(actual) != len(metadata) or set(actual) != names:
            raise ValueError("GitHub full asset 중복·누락입니다")
        for part in value["parts"]:
            item = actual[part["name"]]
            if type(item.get("id")) is not int or type(item.get("size")) is not int:
                raise ValueError("GitHub full asset ID·크기 타입이 다릅니다")
            if any(
                item.get(k) != v
                for k, v in {
                    "id": part["asset_id"],
                    "name": part["name"],
                    "size": part["bytes"],
                    "digest": "sha256:" + part["sha256"],
                    "state": "uploaded",
                    "browser_download_url": part["browser_download_url"],
                }.items()
            ):
                raise ValueError("GitHub full asset 업로드·digest가 다릅니다")
    return value


def _validate(folder, expected, actual):
    certificate = read(folder / _CERT)
    if (
        set(certificate)
        != {
            "schema_version",
            "provenance",
            "envelope",
            "envelope_file",
            "full_archive",
            "kept",
            "omitted",
            "scope",
            "full_cipher",
        }
        or type(certificate["schema_version"]) is not int
        or certificate["schema_version"] != 1
        or identity(certificate["provenance"]) != identity(expected)
    ):
        raise ValueError("compact certificate 형식·provenance가 다릅니다")
    if certificate["scope"] != "authenticated_omitted_hashes_not_local_raw_files":
        raise ValueError("compact 보증 범위가 다릅니다")
    if (
        not isinstance(certificate["full_archive"], dict)
        or set(certificate["full_archive"]) != {"sha256", "bytes"}
        or type(certificate["full_archive"]["bytes"]) is not int
        or certificate["full_archive"]["bytes"] <= 0
    ):
        raise ValueError("compact 원본 archive descriptor가 다릅니다")
    _digest(certificate["full_archive"]["sha256"])
    _descriptor(certificate["full_cipher"])
    if set(actual) != set(certificate["kept"]) | {_CERT}:
        raise ValueError("compact 보존 파일 목록이 다릅니다")
    combined = dict(certificate["kept"])
    for name, value in certificate["omitted"].items():
        if not _OMIT.fullmatch(_path(name)) or name in combined:
            raise ValueError("compact 생략 대상이 raw 결과와 다릅니다")
        combined[name] = value
    for name, value in combined.items():
        _path(name)
        if (
            not isinstance(value, dict)
            or set(value) != {"sha256", "bytes"}
            or type(value["bytes"]) is not int
            or value["bytes"] < 0
        ):
            raise ValueError("compact 파일 descriptor가 다릅니다")
        _digest(value["sha256"])
        if name in certificate["kept"] and actual[name] != value:
            raise ValueError("compact 보존 파일 SHA·크기가 다릅니다")
    envelope = _envelope(folder, expected, combined)
    if (
        envelope != certificate["envelope"]
        or certificate["envelope_file"] != _prefix(expected) + "/envelope.json"
    ):
        raise ValueError("compact 원래 envelope가 certificate와 다릅니다")
    return certificate


def seal(stage: Path, full_cipher_descriptor: dict, compact_archive: Path) -> dict:
    """원본 암호문 업로드 descriptor와 이미 검증한 작은 파일들을 결박한다."""
    stage = Path(stage)
    certificate = read(stage / _CERT)
    if "full_cipher" in certificate:
        raise ValueError("compact stage는 이미 seal됐습니다")
    certificate["full_cipher"] = _descriptor(full_cipher_descriptor)
    write(stage / _CERT, certificate)
    paths = {str(path.relative_to(stage)): path for path in stage.rglob("*") if path.is_file()}
    if any(path.is_symlink() for path in stage.rglob("*")):
        raise ValueError("compact stage 링크는 허용하지 않습니다")
    _validate(stage, certificate["provenance"], {name: _hash(path) for name, path in paths.items()})
    with (
        Path(compact_archive).open("xb") as destination,
        tarfile.open(fileobj=destination, mode="w:gz", compresslevel=1) as output,
    ):
        for name, path in sorted(paths.items()):
            output.add(path, arcname=name, recursive=False)
    return certificate


def _merge(root, paths):
    for name, incoming in paths.items():
        target = root / _path(name)
        if (
            target.is_symlink()
            or not target.resolve().is_relative_to(root.resolve())
            or (target.exists() and _hash(target) != _hash(incoming))
        ):
            raise ValueError("기존 compact 수거 파일 충돌입니다")
    for name, incoming in paths.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open("xb") as destination, incoming.open("rb") as source:
                shutil.copyfileobj(source, destination)
            target.chmod(0o600)


def collect(
    compact_archive: Path,
    root: Path,
    expected: dict,
    full_asset_metadata: list,
    authenticated_cipher: Path,
    cipher_sha: str,
) -> dict:
    """caller가 AES 인증한 작은 archive를 불변 수거한다. 인증은 context에서 재확인한다."""
    root = Path(root)
    cipher_info = _hash(authenticated_cipher)
    if cipher_info["sha256"] != _digest(cipher_sha):
        raise ValueError("compact 암호문 SHA가 다릅니다")
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        actual = _stream(compact_archive, folder)
        certificate = _validate(folder, expected, actual)
        _descriptor(certificate["full_cipher"], full_asset_metadata)
        ident = identity(expected)
        cipher_name = f"compact-ciphers/{ident}.enc"
        cert_name = f"compact-collections/{ident}/certificate.json"
        record_name = f"compact-collections/{ident}/collection.json"
        record = {
            "provenance": expected,
            "cipher_file": cipher_name,
            "cipher": cipher_info,
            "archive": _hash(compact_archive),
            "certificate_sha256": actual[_CERT]["sha256"],
            "full_assets": [
                {
                    key: item[key]
                    for key in ("id", "name", "size", "digest", "state", "browser_download_url")
                }
                for item in sorted(full_asset_metadata, key=lambda value: value["name"])
            ],
        }
        write(folder / "collection.json", record)
        paths = {name: folder / name for name in certificate["kept"]}
        paths.update(
            {
                cipher_name: Path(authenticated_cipher),
                cert_name: folder / _CERT,
                record_name: folder / "collection.json",
            }
        )
        _merge(root, paths)
        return record


@contextmanager
def context(root: Path, key: bytes, expected_base: dict):
    """현재 동기 검증 범위에서만 AES 재인증된 raw 누락 SHA를 사용할 수 있다."""
    root = Path(root).resolve()
    omitted = {}
    for record_path in sorted((root / "compact-collections").glob("*/collection.json")):
        record = read(record_path)
        expected = record["provenance"]
        if identity({k: expected.get(k) for k in expected_base}) != identity(expected_base):
            raise ValueError("compact 인증 문맥의 base provenance가 다릅니다")
        ident = identity(expected)
        if (
            record_path.parent.name != ident
            or record["cipher_file"] != f"compact-ciphers/{ident}.enc"
        ):
            raise ValueError("compact 수거 record namespace가 다릅니다")
        cipher = checked_file(root, record["cipher_file"], record["cipher"]["sha256"])
        if _hash(cipher) != record["cipher"]:
            raise ValueError("보존 compact 암호문이 바뀌었습니다")
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive = folder / "authenticated.tar.gz"
            transform(
                "decrypt", cipher, archive, key, "editor-picks-20261024/compact-result/" + ident
            )
            if _hash(archive) != record["archive"]:
                raise ValueError("compact 인증 archive가 수거 record와 다릅니다")
            incoming = folder / "incoming"
            incoming.mkdir()
            actual = _stream(archive, incoming)
            certificate = _validate(incoming, expected, actual)
            _descriptor(certificate["full_cipher"], record["full_assets"])
            if actual[_CERT]["sha256"] != record["certificate_sha256"]:
                raise ValueError("compact certificate가 수거 record와 다릅니다")
            checked_file(
                root, f"compact-collections/{ident}/certificate.json", record["certificate_sha256"]
            )
            for name, value in certificate["kept"].items():
                checked_file(root, name, value["sha256"])
                if _hash(root / name) != value:
                    raise ValueError("compact 보존 원시 파일이 바뀌었습니다")
            for name, value in certificate["omitted"].items():
                if name in omitted and omitted[name] != value["sha256"]:
                    raise ValueError("compact 생략 원시 SHA가 충돌합니다")
                omitted[name] = value["sha256"]
    token = _OMITTED.set((root, MappingProxyType(omitted)))
    try:
        yield
    finally:
        _OMITTED.reset(token)


def check_file(root: Path, relative: str, digest: str) -> None:
    """실파일 또는 인증된 정확한 누락 raw SHA를 확인하며 가짜 Path는 반환하지 않는다."""
    relative = _path(relative)
    target = Path(root) / relative
    if target.exists() or target.is_symlink():
        checked_file(Path(root), relative, digest)
        return
    active = _OMITTED.get()
    if (
        not _OMIT.fullmatch(relative)
        or active is None
        or Path(root).resolve() != active[0]
        or active[1].get(relative) != _digest(digest)
    ):
        raise ValueError("물리 파일이 없고 인증된 compact raw 참조도 없습니다")
