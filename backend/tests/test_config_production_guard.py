"""Sprint 30 ε B2 — production guard validator.

production app_env 진입 시:
- debug=True → False 강제
- log_level=DEBUG → INFO 승격
- secret_key/clerk_secret_key/waitlist_token_secret placeholder → ValueError

dev/staging 은 backward-compat 유지 (강제 X).
"""

from __future__ import annotations

from decimal import Decimal  # noqa: F401 — 다른 setenv 와 정합

import pytest
from cryptography.fernet import Fernet


def _baseline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings 인스턴스화 baseline.

    필수 ``TRADING_ENCRYPTION_KEYS`` 채움 + 로컬 ``.env.local`` 에 미리 설정된
    ``SECRET_KEY`` / ``CLERK_SECRET_KEY`` / ``WAITLIST_TOKEN_SECRET`` 가
    placeholder-감지 테스트의 의도된 default ('change-me' / '') 를 가리지
    않도록 explicit "unset" semantics 를 setenv 로 강제 (envvar > .env file
    pydantic-settings 우선순위 활용).

    개별 테스트가 placeholder 가 아닌 값을 검증해야 하면 setenv 로 override.
    """
    monkeypatch.setenv("TRADING_ENCRYPTION_KEYS", Fernet.generate_key().decode())
    # ``.env.local`` 의 값을 envvar 로 덮어쓰기 — placeholder semantics 강제.
    monkeypatch.setenv("SECRET_KEY", "change-me")
    monkeypatch.setenv("CLERK_SECRET_KEY", "")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "")


def test_dev_env_allows_debug_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """development 환경은 debug=True / change-me secret 모두 허용."""
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEBUG", "true")

    from src.core.config import Settings

    s = Settings()
    assert s.app_env == "development"
    assert s.debug is True
    assert s.is_production is False
    assert s.is_staging is False


def test_production_forces_debug_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """production 환경은 debug=True 입력해도 강제 False."""
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")
    # placeholder 차단 회피용 envs
    monkeypatch.setenv("SECRET_KEY", "real-prod-secret-32bytes-min-xx")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_live_test")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    # Sprint 60 S5 BL-246 — production env validator 의무
    monkeypatch.setenv("PROMETHEUS_BEARER_TOKEN", "test-prod-bearer-token")

    from src.core.config import Settings

    s = Settings()
    assert s.is_production is True
    assert s.debug is False  # 강제 OFF


def test_production_rejects_placeholder_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production 환경 + secret_key='change-me' (default) → ValueError."""
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_live_test")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    # SECRET_KEY 미설정 → default 'change-me'

    from src.core.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_production_rejects_empty_clerk_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production + clerk_secret_key='' (default) → ValueError."""
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "real-prod-secret-32bytes-min-xx")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    # CLERK_SECRET_KEY 미설정 → default ''

    from src.core.config import Settings

    with pytest.raises(ValueError, match="CLERK_SECRET_KEY"):
        Settings()


def test_environment_enum_values_match_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment enum value 가 Literal 정의와 정합해야 backward-compat 유지."""
    from src.core.config import Environment

    assert Environment.DEVELOPMENT.value == "development"
    assert Environment.STAGING.value == "staging"
    assert Environment.PRODUCTION.value == "production"
