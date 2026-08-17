"""Sprint 30 ε B2 — production guard validator.

production app_env 진입 시:
- debug=True → False 강제
- log_level=DEBUG → INFO 승격
- secret_key/waitlist_token_secret placeholder → ValueError
- FRONTEND_URL/WAITLIST_INVITE_BASE_URL/BETTER_AUTH_URL 이 localhost 기본값이면 ValueError (ADR-034)

dev/staging 은 backward-compat 유지 (강제 X).
"""

from __future__ import annotations

from decimal import Decimal  # noqa: F401 — 다른 setenv 와 정합

import pytest
from cryptography.fernet import Fernet


def _baseline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings 인스턴스화 baseline.

    필수 ``TRADING_ENCRYPTION_KEYS`` 채움 + 로컬 ``.env.local`` 에 미리 설정된
    ``SECRET_KEY`` / ``WAITLIST_TOKEN_SECRET`` 가
    placeholder-감지 테스트의 의도된 default ('change-me' / '') 를 가리지
    않도록 explicit "unset" semantics 를 setenv 로 강제 (envvar > .env file
    pydantic-settings 우선순위 활용).

    개별 테스트가 placeholder 가 아닌 값을 검증해야 하면 setenv 로 override.
    """
    monkeypatch.setenv("TRADING_ENCRYPTION_KEYS", Fernet.generate_key().decode())
    # ``.env.local`` 의 값을 envvar 로 덮어쓰기 — placeholder semantics 강제.
    monkeypatch.setenv("SECRET_KEY", "change-me")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "")
    # ADR-034 — production 은 이 셋이 localhost 기본값이면 거부한다. placeholder 축을 재는
    # 테스트가 URL 축에서 걸리지 않도록 baseline 에서 실주소를 준다.
    monkeypatch.setenv("FRONTEND_URL", "https://qb.example.dev")
    monkeypatch.setenv("BETTER_AUTH_URL", "https://qb.example.dev")
    monkeypatch.setenv("WAITLIST_INVITE_BASE_URL", "https://qb.example.dev/invite")
    # [BL-784] 로컬 `.env.local` 이 e2e 면제 이메일을 채워 두면 production 축 테스트가 전부
    # **그 에러**로 raise 해서 원래 재려던 축이 사라진다. 여기서 "미설정" 을 강제한다.
    monkeypatch.setenv("E2E_RATE_LIMIT_EXEMPT_EMAIL", "")


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
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    # SECRET_KEY 미설정 → default 'change-me'

    from src.core.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_production_rejects_known_dev_secret_key_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production + secret_key='dev-secret-change-in-prod' (.env.example default) → ValueError.

    .env.example 의 SECRET_KEY default 를 그대로 prod 로 복사하는 footgun 차단.
    'change-me' 만 막으면 공개된 dev default 가 prod validator 를 통과한다.
    """
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "dev-secret-change-in-prod")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    monkeypatch.setenv("PROMETHEUS_BEARER_TOKEN", "test-prod-bearer-token")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_production_rejects_empty_waitlist_token_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production + waitlist_token_secret='' → ValueError.

    ★이것이 왜 중요한가 — 비어 있으면 `waitlist/dependencies.py:get_token_service` 가
    **레포에 공개된 상수**를 HMAC 키로 조용히 주입한다. 즉 초대 토큰이 위조 가능해진다.
    이 validator 가 그 상태로 production 이 뜨는 것을 막는 유일한 가드다([BL-753]).
    """
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "real-prod-secret-32bytes-min-xx")
    monkeypatch.setenv("PROMETHEUS_BEARER_TOKEN", "test-prod-bearer-token")
    # WAITLIST_TOKEN_SECRET 은 baseline 이 '' 로 강제한다.

    from src.core.config import Settings

    with pytest.raises(ValueError, match="WAITLIST_TOKEN_SECRET"):
        Settings()


def test_production_requires_prometheus_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """production + PROMETHEUS_BEARER_TOKEN 부재 → ValueError.

    ★★**이 축을 겨누는 테스트가 2026-08-17 까지 0건이었다.** 다른 테스트들은 이 값을
    **세팅해서 에러를 피할 뿐**이라 validator 가 살아 있는지 아무도 재지 않았다
    ([BL-246] 이 만든 가드의 무증거 구간).
    """
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "real-prod-secret-32bytes-min-xx")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    monkeypatch.delenv("PROMETHEUS_BEARER_TOKEN", raising=False)

    from src.core.config import Settings

    with pytest.raises(ValueError, match="PROMETHEUS_BEARER_TOKEN"):
        Settings()


@pytest.mark.parametrize(
    ("var", "value"),
    [
        ("FRONTEND_URL", "http://localhost:3000"),
        ("BETTER_AUTH_URL", "http://localhost:3000"),
        ("WAITLIST_INVITE_BASE_URL", "http://localhost:3000/invite"),
    ],
)
def test_production_rejects_localhost_defaults(
    monkeypatch: pytest.MonkeyPatch, var: str, value: str
) -> None:
    """production + URL 3종이 localhost 기본값이면 → ValueError (ADR-034 신설).

    ★종전 validator 는 이 셋을 **안 봤다**. 값이 비어 있지 않아서 「채워졌다」로 보였고,
    그 상태로 뜬 API 는 CORS 에서 실 FE origin 을 조용히 거부한다 — 화면에서는 그것이
    「데이터 없음」으로 보인다([BL-707] 과 같은 병의 다른 판).
    """
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "real-prod-secret-32bytes-min-xx")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    monkeypatch.setenv("PROMETHEUS_BEARER_TOKEN", "test-prod-bearer-token")
    monkeypatch.setenv(var, value)

    from src.core.config import Settings

    with pytest.raises(ValueError, match=var):
        Settings()


def test_jwks_url_derives_from_better_auth_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWKS URL 은 명시값 우선, 없으면 better_auth_url 에서 파생 (trailing slash 무관)."""
    _baseline_env(monkeypatch)
    monkeypatch.setenv("BETTER_AUTH_URL", "https://qb.example.dev/")
    monkeypatch.delenv("BETTER_AUTH_JWKS_URL", raising=False)

    from src.core.config import Settings

    assert Settings().jwks_url == "https://qb.example.dev/api/auth/jwks"

    monkeypatch.setenv("BETTER_AUTH_JWKS_URL", "http://quantbridge-frontend:3000/api/auth/jwks")
    assert Settings().jwks_url == "http://quantbridge-frontend:3000/api/auth/jwks"


def test_environment_enum_values_match_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment enum value 가 Literal 정의와 정합해야 backward-compat 유지."""
    from src.core.config import Environment

    assert Environment.DEVELOPMENT.value == "development"
    assert Environment.STAGING.value == "staging"
    assert Environment.PRODUCTION.value == "production"


def test_production_rejects_e2e_rate_limit_exemption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[BL-784] production + E2E_RATE_LIMIT_EXEMPT_EMAIL 값 존재 → ValueError.

    ★런타임 판정(`is_rate_limit_exempt_identity`)이 이미 production 을 막는데 왜 또 막나 —
    그 판정은 `APP_ENV` 가 **실제로 붙어 있을 때만** 작동하기 때문이다. 2026-08-15 에 배포
    호스트가 `APP_ENV` 를 안 넣어 `{"env":"development"}` 로 돌던 실사고가 있었다. 라벨이
    production 인 구성에서는 **값의 존재 자체**를 부팅 실패로 만들어 층을 하나 더 둔다.
    """
    _baseline_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "real-prod-secret-32bytes-min-xx")
    monkeypatch.setenv("WAITLIST_TOKEN_SECRET", "x" * 32)
    monkeypatch.setenv("PROMETHEUS_BEARER_TOKEN", "test-prod-bearer-token")
    monkeypatch.setenv("E2E_RATE_LIMIT_EXEMPT_EMAIL", "e2e@dogfood.local")

    from src.core.config import Settings

    with pytest.raises(ValueError, match="E2E_RATE_LIMIT_EXEMPT_EMAIL"):
        Settings()

    # ★양성 대조 — 값이 없으면 같은 구성이 정상 부팅한다. 이 줄이 없으면 위 raise 가
    #   「이 구성은 어차피 못 뜬다」와 구분되지 않는다.
    monkeypatch.setenv("E2E_RATE_LIMIT_EXEMPT_EMAIL", "")
    assert Settings().is_production is True
