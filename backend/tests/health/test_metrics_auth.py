# Sprint 60 S5 — BL-246 /metrics endpoint 인증 검증 (2026-08-11 skip 해제 + deny 전환)
"""BL-246 / Multi-Agent QA QA(Sentinel) 발견 — Public `/metrics` Prometheus
endpoint 가 `prometheus_bearer_token` 미설정 시 unauth allow (Beta 외부 노출 시
즉시 audit fail).

계약 (2026-08-11 ledger-truth 이후):
1. token **미설정** → 401. 종전의 「dev/local 은 allow」는 폐기했다 — production 만
   `core/config.py` validator 로 막혀 있었고 나머지 환경은 전부 무인증 노출이었다.
2. token 설정 + bearer 없음 → 401 / 잘못된 bearer → 403 / 올바른 bearer → 200.

★2026-05-14 ~ 2026-08-11 동안 아래 3건은 `@pytest.mark.skip("fixture env issue (CI 환경
routing 미등록) … Sprint 61 follow-up")` 로 죽어 있었다. Sprint 61 은 2026-05-17 에 끝났고
대응 BL 은 0건이다.

★**그 사유의 절반은 거짓이었다.** 「routing 미등록」은 사실이지만 원인이 CI 환경이 아니다 —
`tests/health/conftest.py` 가 `client` 픽스처를 **이름 가리기**로 덮어 `health_router` 만
mount 한 minimal app 을 주는데, 거기엔 `/metrics` 가 없어 404 가 났다(2026-08-11 실측).
환경 문제가 아니라 **같은 디렉터리 안 픽스처 충돌**이고, 아래 `client` 재정의 한 개로 끝난다.
3개월을 기다릴 이유가 없었다. 다시 skip 하지 마라.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """`/metrics` 가 실제로 달린 full app client.

    ★`tests/health/conftest.py` 의 `client` 를 **다시** 덮는다. 그쪽은 DB 를 피하려고
    `health_router` 만 mount 하는데 `/metrics` 는 `create_app()` 본문이 등록하므로
    그 app 에서는 404 다. 여기서도 DB 는 안 쓴다 — `/metrics` 는 세션을 타지 않고
    ASGITransport 는 lifespan 을 돌리지 않는다.
    """
    from src.main import create_app

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_metrics_401_when_token_unset(
    client: AsyncClient,
) -> None:
    """★deny 전환 회귀 핀 — 토큰 **미설정** 상태에서 `/metrics` 는 401.

    이 한 건이 `_verify_prometheus_bearer` 의 fail-open 복귀를 잡는 유일한 테스트다.
    아래 3건은 전부 토큰을 **설정한** 케이스라 `if not expected: return` 을 되돌려도
    초록으로 통과한다 — 실측으로 확인했다. 이 테스트를 지우면 그 변이가 무증거가 된다.
    """
    from src import main as main_module

    with patch.object(main_module.settings, "prometheus_bearer_token", None):
        resp = await client.get("/metrics")

    assert resp.status_code == 401, (
        f"토큰 미설정 시 /metrics 는 401 이어야 한다 (fail-closed), "
        f"got {resp.status_code}: {resp.text[:200]}"
    )


@pytest.mark.asyncio
async def test_metrics_401_when_token_empty_string(
    client: AsyncClient,
) -> None:
    """★빈 문자열도 「없음」이다 — [BL-704] 의 공용 술어를 **엔드포인트 경로로** 고정한다.

    `_metrics_auth_token()` 을 직접 부르는 단위 테스트는 그 함수만 재고 **가드가 그것을
    쓰는지**는 못 잰다([LESSON-092] §2). 부팅 로그 쪽 대응 케이스는
    `test_metrics_auth_boot_log.py::test_boot_treats_empty_token_as_disabled` 이고,
    둘이 같은 진리값을 요구하므로 술어가 갈라지면 **한쪽이 반드시 red** 다.
    """
    from src import main as main_module

    with patch.object(main_module.settings, "prometheus_bearer_token", SecretStr("")):
        resp = await client.get("/metrics")

    assert resp.status_code == 401, (
        f"빈 토큰은 미설정과 같아야 한다 (fail-closed), got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_metrics_unauth_401_when_token_set(
    client: AsyncClient,
) -> None:
    """BL-246 — token 설정된 환경에서 bearer 없으면 401."""
    from src import main as main_module

    with patch.object(
        main_module.settings, "prometheus_bearer_token", SecretStr("test-secret-token")
    ):
        resp = await client.get("/metrics")

    assert resp.status_code == 401, (
        f"BL-246 — /metrics without bearer should 401 (token configured), "
        f"got {resp.status_code}: {resp.text[:200]}"
    )
    body = resp.json()
    assert "detail" in body
    assert "bearer" in body["detail"].lower()


@pytest.mark.asyncio
async def test_metrics_invalid_bearer_403_when_token_set(
    client: AsyncClient,
) -> None:
    """BL-246 — token 설정된 환경에서 잘못된 bearer 면 403."""
    from src import main as main_module

    with patch.object(
        main_module.settings, "prometheus_bearer_token", SecretStr("test-secret-token")
    ):
        resp = await client.get(
            "/metrics",
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert resp.status_code == 403, (
        f"BL-246 — /metrics with wrong bearer should 403, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_metrics_valid_bearer_returns_text(
    client: AsyncClient,
) -> None:
    """BL-246 — 정확한 bearer 시 200 + Prometheus text format."""
    from src import main as main_module

    token = "test-secret-token-xyz"
    with patch.object(main_module.settings, "prometheus_bearer_token", SecretStr(token)):
        resp = await client.get(
            "/metrics",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, (
        f"BL-246 — /metrics with valid bearer should 200, got {resp.status_code}"
    )
    # Prometheus text format = "text/plain; version=0.0.4; charset=utf-8" 등
    assert "text/plain" in resp.headers.get("content-type", "").lower()


def test_settings_production_requires_prometheus_token() -> None:
    """BL-246 — production 환경에서 prometheus_bearer_token 강제 권고 (Beta gate).

    이 test 는 현재 Settings 의 prometheus_bearer_token 이 production 에서
    None 가능한지 확인 — None 이면 P1-13 외부 노출 risk 명시.
    2026-08-11 이후: 모든 환경이 deny 이고, production 은 그 위에 **부팅 차단**까지 건다.
    """
    from src.core.config import Settings

    # Settings 의 prometheus_bearer_token 이 SecretStr | None 타입 — production 에서
    # 명시 의무 (.env.example 갱신 + production deploy 시 환경변수 설정 의무).
    # 본 test 는 type 검증만 (실제 production 검증은 deploy CI 책임).
    field_info = Settings.model_fields.get("prometheus_bearer_token")
    assert field_info is not None
    # SecretStr | None 형태 (Optional)
    # production deploy 시 환경변수 PROMETHEUS_BEARER_TOKEN 의무 (manual).
