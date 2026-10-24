"""연구 번들의 청크별 인증 암호화. 키·평가 내용은 출력하지 않는다."""

from __future__ import annotations

import argparse
import base64
import os
import struct
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"QBENC7\x00"
CHUNK = 16 * 1024 * 1024


def exact(stream, length):
    value = stream.read(length)
    if len(value) != length:
        raise ValueError("truncated_authenticated_bundle")
    return value


def transform(mode, source, destination, key, context):
    if mode not in {"encrypt", "decrypt"}:
        raise ValueError("invalid_transform_mode")
    if len(key) != 32 or not context or len(context.encode()) > 256:
        raise ValueError("invalid_key_or_context")
    cipher = AESGCM(key)
    created = False
    try:
        with Path(source).open("rb") as incoming:
            descriptor = os.open(
                destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            created = True
            with os.fdopen(descriptor, "wb") as outgoing:
                if mode == "encrypt":
                    prefix = os.urandom(8)
                    outgoing.write(MAGIC + prefix)
                else:
                    if exact(incoming, len(MAGIC)) != MAGIC:
                        raise ValueError("unknown_bundle_format")
                    prefix = exact(incoming, 8)
                index = 0
                while True:
                    counter = struct.pack(">I", index)
                    aad = MAGIC + context.encode() + b"\x00" + counter
                    if mode == "encrypt":
                        block = incoming.read(CHUNK)
                        value = cipher.encrypt(prefix + counter, block, aad)
                        outgoing.write(struct.pack(">I", len(value)))
                        outgoing.write(value)
                        if not block:
                            break
                    else:
                        length = struct.unpack(">I", exact(incoming, 4))[0]
                        if not 16 <= length <= CHUNK + 16:
                            raise ValueError("invalid_encrypted_chunk_length")
                        value = cipher.decrypt(
                            prefix + counter, exact(incoming, length), aad
                        )
                        if not value:
                            if incoming.read(1):
                                raise ValueError("trailing_encrypted_data")
                            break
                        outgoing.write(value)
                    index += 1
                outgoing.flush()
                os.fsync(outgoing.fileno())
    except BaseException:
        if created:
            Path(destination).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encrypt", "decrypt"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-env", required=True)
    parser.add_argument("--context", required=True)
    args = parser.parse_args()
    key = base64.b64decode(os.environ[args.key_env], altchars=b"-_", validate=True)
    transform(args.mode, args.input, args.output, key, args.context)


if __name__ == "__main__":
    main()
