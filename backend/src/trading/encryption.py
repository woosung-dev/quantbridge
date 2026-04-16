"""EncryptionService — AES-256 MultiFernet wrapper (autoplan CEO F3 + Eng E4).

Sprint 6: 단일 키로 시작하되 MultiFernet 리스트 추상화로 구조화 — Sprint 7+
key rotation 시 "새 키 prepend"만으로 무중단 전환 가능.

MultiFernet 동작:
- encrypt: 리스트의 첫 키 (newest) 사용
- decrypt: 리스트 순회하며 첫 성공 결과 반환

복호화는 Service 레이어의 명시적 메서드에서만 호출 — Repository는 암호문만 다룬다.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from pydantic import SecretStr

from src.trading.exceptions import EncryptionError


class EncryptionService:
    """MultiFernet 래퍼. DI로 주입되어 ExchangeAccountService가 사용."""

    def __init__(self, master_keys: SecretStr) -> None:
        """master_keys: comma-separated Fernet keys, newest first."""
        raw = master_keys.get_secret_value()
        key_strs = [k.strip() for k in raw.split(",") if k.strip()]
        if not key_strs:
            raise EncryptionError("TRADING_ENCRYPTION_KEYS must contain at least 1 Fernet key")
        try:
            fernets = [Fernet(k.encode("utf-8")) for k in key_strs]
        except ValueError as e:
            raise EncryptionError(f"Invalid Fernet key: {e}") from e
        self._multi = MultiFernet(fernets)

    def encrypt(self, plaintext: str) -> bytes:
        return self._multi.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._multi.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as e:
            raise EncryptionError("AES-256 복호화 실패 — ciphertext 손상 또는 모든 키 불일치") from e
