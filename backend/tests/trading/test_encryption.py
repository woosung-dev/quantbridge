"""EncryptionService — MultiFernet round-trip + 키 로테이션 케이스."""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr


@pytest.fixture
def single_key() -> SecretStr:
    return SecretStr(Fernet.generate_key().decode())


@pytest.fixture
def two_keys() -> SecretStr:
    """newest first convention."""
    k1 = Fernet.generate_key().decode()
    k2 = Fernet.generate_key().decode()
    return SecretStr(f"{k1},{k2}")


def test_encrypt_then_decrypt_returns_original(single_key):
    from src.trading.encryption import EncryptionService

    svc = EncryptionService(single_key)
    ciphertext = svc.encrypt("my-api-secret-xyz")
    assert isinstance(ciphertext, bytes)
    assert ciphertext != b"my-api-secret-xyz"
    assert svc.decrypt(ciphertext) == "my-api-secret-xyz"


def test_decrypt_with_wrong_key_raises_encryption_error(single_key):
    from src.trading.encryption import EncryptionService
    from src.trading.exceptions import EncryptionError

    svc_a = EncryptionService(single_key)
    ciphertext = svc_a.encrypt("secret")

    other_key = SecretStr(Fernet.generate_key().decode())
    svc_b = EncryptionService(other_key)
    with pytest.raises(EncryptionError):
        svc_b.decrypt(ciphertext)


def test_decrypt_with_invalid_ciphertext_raises(single_key):
    from src.trading.encryption import EncryptionService
    from src.trading.exceptions import EncryptionError

    svc = EncryptionService(single_key)
    with pytest.raises(EncryptionError):
        svc.decrypt(b"not-a-valid-fernet-ciphertext")


def test_unicode_secret_round_trip(single_key):
    from src.trading.encryption import EncryptionService

    svc = EncryptionService(single_key)
    original = "한국어-secret-🔑"
    assert svc.decrypt(svc.encrypt(original)) == original


def test_multifernet_encrypts_with_first_key_decrypts_any(two_keys):
    """autoplan Eng E4 — 다중 키 list에서 encryption은 첫 키(newest), decryption은 순차 시도."""
    from src.trading.encryption import EncryptionService

    svc = EncryptionService(two_keys)
    ciphertext = svc.encrypt("rotation-test")
    # cryptography.MultiFernet은 첫 키로 암호화 → fallback 복호화 지원
    assert svc.decrypt(ciphertext) == "rotation-test"


def test_key_rotation_old_ciphertext_decrypts_after_prepending_new_key():
    """CEO F3 + Eng E4 핵심 — 새 키 prepend만으로 구 ciphertext 유지."""
    from src.trading.encryption import EncryptionService
    from src.trading.exceptions import EncryptionError

    # Phase 1: 단일 키로 시작
    old_key = Fernet.generate_key().decode()
    svc_before = EncryptionService(SecretStr(old_key))
    old_ciphertext = svc_before.encrypt("long-lived-secret")

    # Phase 2: 새 키 prepend (rotation 시점)
    new_key = Fernet.generate_key().decode()
    svc_after = EncryptionService(SecretStr(f"{new_key},{old_key}"))

    # 구 ciphertext 여전히 복호화 가능
    assert svc_after.decrypt(old_ciphertext) == "long-lived-secret"

    # 새 암호화는 new_key 사용
    new_ciphertext = svc_after.encrypt("new-secret")
    assert svc_after.decrypt(new_ciphertext) == "new-secret"

    # old_key 제거 후엔 old_ciphertext 복호화 불가 (grace 종료 시나리오)
    svc_final = EncryptionService(SecretStr(new_key))
    with pytest.raises(EncryptionError):
        svc_final.decrypt(old_ciphertext)


def test_empty_keys_string_raises():
    from src.trading.encryption import EncryptionService
    from src.trading.exceptions import EncryptionError

    with pytest.raises(EncryptionError):
        EncryptionService(SecretStr(""))
