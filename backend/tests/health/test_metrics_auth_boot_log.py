# BL-704 — `/metrics` 인증 활성 여부를 부팅 시점에 말하는가 (2026-08-11 metrics-boot-log)
"""`/metrics` fail-closed 를 지켜 주는 것이 실배포 호스트에는 없었다.

`core/config.py` 의 production validator 는 `app_env` **문자열**이 `production` 일 때만
돌고(staging 은 명시 면제), 이 레포의 실배포 호스트는 `APP_ENV` 를 아예 설정하지 않아
기본값 `development` 로 돈다(`frontend-deploy.md:13`). 즉 **보호를 가장 못 받는 환경이
경고도 못 받았다.** 재프로비저닝에서 `PROMETHEUS_BEARER_TOKEN` 한 줄이 빠지면 `/metrics`
는 조용히 401 이 되고 부팅은 성공한다 — fail-closed 라 결과는 노출이 아니라 **관측 상실**이다.

★**이 파일은 lifespan 을 실제로 태운다.** 로그 문장을 만드는 헬퍼를 직접 부르면
「그 함수」만 재고 **그것이 부팅 경로에 배선됐는지**는 못 잰다([LESSON-092] §2). 관용구는
`tests/test_main_lifespan_deprecated_warning.py` 와 같다 — `ohlcv_provider=fixture` 로
CCXTProvider 를 피하고 Redis healthcheck 를 no-op 으로 바꾼다.
"""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from pydantic import SecretStr

MARKER = "metrics_auth="


@pytest.fixture
def bootable(monkeypatch: pytest.MonkeyPatch) -> None:
    """lifespan 이 외부 자원 없이 끝까지 돌게 한다 (DB·Redis·거래소 접촉 0)."""
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "ohlcv_provider", "fixture")

    async def _noop_healthcheck(_app: FastAPI) -> None:
        return None

    monkeypatch.setattr("src.common.redis_client.healthcheck_redis_lock", _noop_healthcheck)

    class _StubManager:
        async def listen(self) -> None:
            return None

        async def close(self) -> None:
            return None

    monkeypatch.setattr("src.realtime.manager.ConnectionManager", _StubManager)


async def _boot(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """lifespan 을 왕복시키고 `metrics_auth=` 를 말한 레코드를 돌려준다.

    ★수집은 **yield 안**에서 한다 — 「부팅 로그」의 계약은 *startup 시점*이지 「언젠가」가
    아니다. 컨텍스트를 빠져나온 뒤에 세면 그 줄을 shutdown 으로 미루는 변경이 **초록으로
    통과**한다(실측으로 확인한 구멍이다). 운영자는 부팅 직후 로그를 보지 종료 로그를 안 본다.
    """
    from src.main import lifespan

    caplog.set_level(logging.INFO, logger="src.main")
    async with lifespan(FastAPI()):
        return [r for r in caplog.records if MARKER in r.getMessage()]


@pytest.mark.asyncio
async def test_boot_warns_when_token_unset(
    bootable: None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """토큰 미설정 → 부팅 로그에 WARNING 1건. 부팅은 성공한다."""
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "prometheus_bearer_token", None)

    records = await _boot(caplog)

    assert len(records) == 1, f"부팅 로그가 {len(records)}건이다 (계약 1건)"
    assert records[0].levelno == logging.WARNING, (
        "관측 상실은 INFO 로 흘리면 아무도 안 본다 — WARNING 이어야 한다"
    )
    assert "DISABLED" in records[0].getMessage()


@pytest.mark.asyncio
async def test_boot_reports_enabled_when_token_set(
    bootable: None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """토큰 설정 → INFO 「enabled」 1건 · WARNING 0건 (음성 대조)."""
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "prometheus_bearer_token", SecretStr("boot-token"))

    records = await _boot(caplog)

    assert len(records) == 1, f"부팅 로그가 {len(records)}건이다 (계약 1건)"
    assert records[0].levelno == logging.INFO
    assert "enabled" in records[0].getMessage()
    assert "boot-token" not in records[0].getMessage(), "토큰 값을 로그에 찍으면 안 된다"


@pytest.mark.asyncio
async def test_boot_treats_empty_token_as_disabled(
    bootable: None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """빈 문자열도 「없음」이다 — 엔드포인트의 `if not expected` 와 같은 진리값.

    술어가 갈라지면 로그는 「활성」인데 스크레이프는 401 인 상태가 생긴다.
    """
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "prometheus_bearer_token", SecretStr(""))

    records = await _boot(caplog)

    assert len(records) == 1
    assert "DISABLED" in records[0].getMessage()


@pytest.mark.asyncio
@pytest.mark.parametrize("app_env", ["development", "staging", "production"])
async def test_boot_warns_regardless_of_app_env(
    app_env: str,
    bootable: None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★이 항목의 본체 — 경고는 `app_env` **문자열에 걸리지 않는다.**

    실배포 호스트는 `APP_ENV` 미설정(= `development`)이라, 이 줄을 `is_production` 같은
    조건으로 감싸는 순간 **그 호스트에서만 조용해진다.** 그것이 [BL-704] 가 지적한 결함
    자체다. 변이로 확인 — 로그를 `if settings.is_production:` 로 감싸면 이 케이스가 red 다.
    """
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "app_env", app_env)
    monkeypatch.setattr(main_settings, "prometheus_bearer_token", None)

    records = await _boot(caplog)

    assert len(records) == 1, f"app_env={app_env} 에서 부팅 로그가 {len(records)}건이다"
    assert records[0].levelno == logging.WARNING
    assert app_env in records[0].getMessage(), "어느 환경으로 떴는지도 함께 말해야 한다"


@pytest.mark.asyncio
async def test_lifespan_still_completes_when_disabled(
    bootable: None,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**부팅을 막지 않는다** — 토큰이 없어도 lifespan 은 yield 를 넘긴다.

    막는 처방(raise)은 dev·local·CI 를 전부 깨고, 그 결과 아무도 토큰을 안 켜는 대신
    이 가드를 지운다. 관측 상실은 경고할 값이지 부팅을 죽일 값이 아니다.
    """
    from src.main import lifespan
    from src.main import settings as main_settings

    monkeypatch.setattr(main_settings, "prometheus_bearer_token", None)

    entered = False
    async with lifespan(FastAPI()):
        entered = True

    assert entered, "토큰 미설정이 부팅을 막았다 — 계약 위반"
