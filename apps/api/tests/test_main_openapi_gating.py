# Sprint 61 T-4 (BL-312) — production env 시 OpenAPI 익명 노출 차단 회귀 test
"""docs_url / redoc_url / openapi_url production gating.

Curious + QA Sentinel 페르소나 발견 (Multi-Agent QA 2026-05-17, integrated-report.html §3):
production 환경에서 /openapi.json (97870 bytes 전체 스키마) + /docs + /redoc 익명 200 응답 =
공격자 reconnaissance phase 즉시 완료. settings.is_production 가 True 일 때만 None 으로
비활성 → 404. dev / staging 은 노출 유지 (DX 보존).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _build_app_with_env(monkeypatch: pytest.MonkeyPatch, env: str, *, debug: bool = True):
    """app_env(+debug) 를 강제 monkeypatch 후 create_app() 재실행.

    settings 는 module-level singleton 이라 monkeypatch 후 create_app() 의
    `_hide_docs = settings.is_production or not settings.debug` 분기가 즉시 반영된다.

    ★`debug` 기본값을 True 로 명시한다 — 종전 판본은 ambient `.env.local` 의 DEBUG 에
    의존했다. 그 암묵 의존이 바로 아래 회귀 테스트가 막는 결함을 가리고 있었다.
    """
    from src.core.config import settings
    from src.main import create_app

    monkeypatch.setattr(settings, "app_env", env)
    monkeypatch.setattr(settings, "debug", debug)
    return create_app()


@pytest.mark.parametrize(
    "path",
    ["/openapi.json", "/docs", "/redoc"],
)
def test_openapi_endpoints_exposed_in_development(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """development env → OpenAPI / Swagger UI / Redoc 모두 200 (DX 보존)."""
    app = _build_app_with_env(monkeypatch, "development")
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 200, (
        f"development env 에서 {path} 가 200 이어야 한다 (실제 {response.status_code})"
    )


@pytest.mark.parametrize(
    "path",
    ["/openapi.json", "/docs", "/redoc"],
)
def test_openapi_endpoints_exposed_in_staging(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """staging env → OpenAPI / Swagger UI / Redoc 모두 200 (내부 QA 보존)."""
    app = _build_app_with_env(monkeypatch, "staging")
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 200, (
        f"staging env 에서 {path} 가 200 이어야 한다 (실제 {response.status_code})"
    )


@pytest.mark.parametrize(
    "path",
    ["/openapi.json", "/docs", "/redoc"],
)
def test_openapi_endpoints_blocked_in_production(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """production env → OpenAPI / Swagger UI / Redoc 모두 404 (attack surface 차단)."""
    app = _build_app_with_env(monkeypatch, "production")
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 404, (
        f"production env 에서 {path} 가 404 이어야 한다 (BL-312 회귀, 실제 {response.status_code})"
    )


# ---------------------------------------------------------------------------
# 2026-08-15 surface-truth — 실사고 모양 회귀
#
# 위 세 묶음은 **`app_env` 축만** 잰다. 그런데 실제로 노출된 호스트는 `APP_ENV` 를
# **아예 안 넣은** 배포였다(`frontend-deploy.md:13,132`). 그 호스트는 `app_env` 기본값
# `"development"` 를 그대로 쓰므로 위 테스트 기준으로는 「의도된 노출」이고, 그래서
# 9건 전부 초록인 채로 `https://qb-api.woosung.dev/docs` 가 **인터넷에 200** 이었다
# (2026-08-15 실측: /openapi.json 200 · /docs 200 · /health → {"env":"development"}).
# 그 API 는 Cloudflare Access 뒤도 아니다 — `frontend-deploy.md:48`.
#
# ⇒ 검사 축을 하나 더 세운다: **「배포됐는데 DEBUG 를 안 켰다」면 숨긴다.**
#    이것이 `_hide_docs` 를 `is_production` 에서 `is_production or not debug` 로
#    옮긴 이유이고, 아래 테스트가 그 되돌림을 red 로 만든다.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
@pytest.mark.parametrize("env", ["development", "staging"])
def test_openapi_hidden_when_debug_off_outside_production(
    monkeypatch: pytest.MonkeyPatch, env: str, path: str
) -> None:
    """★실사고 모양 — `APP_ENV` 미설정(=development) + DEBUG 미설정(=False) → 404.

    종전 판정식 `_hide_docs = settings.is_production` 으로 되돌리면 이 테스트가 red 다.
    """
    app = _build_app_with_env(monkeypatch, env, debug=False)
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 404, (
        f"{env} env + DEBUG=false 에서 {path} 는 404 여야 한다 "
        f"(2026-08-15 실배포 노출 회귀, 실제 {response.status_code})"
    )


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
def test_openapi_still_exposed_for_local_debug(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """음성 대조 — 로컬 개발(DEBUG=true)에서는 그대로 200 이어야 한다.

    이게 없으면 위 테스트는 「전부 404 로 만들기」로도 통과한다(판별력 0).
    """
    app = _build_app_with_env(monkeypatch, "development", debug=True)
    client = TestClient(app)
    response = client.get(path)
    assert response.status_code == 200, (
        f"로컬 DEBUG=true 에서 {path} 는 200 이어야 한다 (실제 {response.status_code})"
    )


def test_debug_default_is_false() -> None:
    """★뿌리 — 기본값이 안전한 쪽이어야 한다.

    `Settings.debug` 기본값이 True 로 돌아가면, `APP_ENV` 를 안 넣은 호스트가 다시
    traceback(`main.py` unhandled 핸들러를 Starlette debug 분기가 앞질러 간다) ·
    `/docs` · HSTS 미부착을 **한꺼번에** 얻는다.
    ★ambient `.env.local` 의 DEBUG 가 섞이지 않도록 **클래스 필드 기본값**을 직접 잰다.
    """
    from src.core.config import Settings

    assert Settings.model_fields["debug"].default is False, (
        "Settings.debug 기본값은 False 여야 한다 — 안전한 쪽이 기본이다 (2026-08-15 surface-truth)"
    )
