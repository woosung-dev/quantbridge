"""Sprint 6 Trading config field validation."""
from __future__ import annotations

from decimal import Decimal

import pytest


def test_settings_has_trading_fields(monkeypatch):
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("TRADING_ENCRYPTION_KEYS", test_key)
    monkeypatch.setenv("EXCHANGE_PROVIDER", "fixture")
    monkeypatch.setenv("KILL_SWITCH_CUMULATIVE_LOSS_PERCENT", "10.0")
    monkeypatch.setenv("KILL_SWITCH_DAILY_LOSS_USD", "500.0")
    monkeypatch.setenv("KILL_SWITCH_CAPITAL_BASE_USD", "10000")

    from src.core.config import Settings
    s = Settings()
    assert test_key in s.trading_encryption_keys.get_secret_value()
    assert s.exchange_provider == "fixture"
    assert s.kill_switch_cumulative_loss_percent == Decimal("10.0")
    assert s.kill_switch_daily_loss_usd == Decimal("500.0")
    assert s.kill_switch_capital_base_usd == Decimal("10000")


def test_settings_multiple_encryption_keys(monkeypatch):
    """autoplan Eng E4 — MultiFernet 기반 다중 키."""
    from cryptography.fernet import Fernet
    k1 = Fernet.generate_key().decode()
    k2 = Fernet.generate_key().decode()
    monkeypatch.setenv("TRADING_ENCRYPTION_KEYS", f"{k1},{k2}")
    monkeypatch.setenv("EXCHANGE_PROVIDER", "fixture")

    from src.core.config import Settings
    s = Settings()
    keys = s.trading_encryption_keys.get_secret_value()
    assert k1 in keys and k2 in keys


def test_settings_invalid_encryption_key_raises(monkeypatch):
    monkeypatch.setenv("TRADING_ENCRYPTION_KEYS", "not-a-valid-fernet-key")
    monkeypatch.setenv("EXCHANGE_PROVIDER", "fixture")

    from src.core.config import Settings
    with pytest.raises(ValueError, match="Invalid Fernet key"):
        Settings()
