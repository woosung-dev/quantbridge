# Worker/HTTP DI 조립이 dispatcher 재귀와 provider 경로를 바꾸지 않도록 고정한다.
"""Worker와 HTTP 경로의 DI 조립 계약 회귀 테스트."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.backtest.dependencies import (
    build_backtest_service_for_worker,
    get_backtest_service,
)
from src.backtest.dispatcher import CeleryTaskDispatcher, NoopTaskDispatcher
from src.core.config import settings
from src.market_data.dependencies import get_ccxt_provider, get_ohlcv_provider
from src.market_data.providers.fixture import FixtureProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.optimizer.dependencies import (
    build_optimizer_service_for_worker,
    get_optimizer_service,
)
from src.optimizer.dispatcher import (
    CeleryOptimizationTaskDispatcher,
    NoopOptimizationTaskDispatcher,
)
from src.stress_test.dependencies import (
    build_stress_test_service_for_worker,
    get_stress_test_service,
)
from src.stress_test.dispatcher import (
    CeleryStressTaskDispatcher,
    NoopStressTaskDispatcher,
)

WORKER_BUILDERS = (
    pytest.param(
        build_optimizer_service_for_worker,
        NoopOptimizationTaskDispatcher,
        id="optimizer",
    ),
    pytest.param(
        build_stress_test_service_for_worker,
        NoopStressTaskDispatcher,
        id="stress_test",
    ),
    pytest.param(
        build_backtest_service_for_worker,
        NoopTaskDispatcher,
        id="backtest",
    ),
)

HTTP_BUILDERS = (
    pytest.param(
        get_optimizer_service,
        CeleryOptimizationTaskDispatcher,
        id="optimizer",
    ),
    pytest.param(
        get_stress_test_service,
        CeleryStressTaskDispatcher,
        id="stress_test",
    ),
    pytest.param(
        get_backtest_service,
        CeleryTaskDispatcher,
        id="backtest",
    ),
)

REPOSITORY_ATTRIBUTES = (
    pytest.param(
        build_optimizer_service_for_worker,
        ("repo", "backtest_repo", "strategy_repo"),
        id="optimizer",
    ),
    pytest.param(
        build_stress_test_service_for_worker,
        ("repo", "backtest_repo", "strategy_repo"),
        id="stress_test",
    ),
    pytest.param(
        build_backtest_service_for_worker,
        ("repo", "strategy_repo", "ohlcv_repo", "funding_repo"),
        id="backtest",
    ),
)


def _request_with_ccxt(ccxt_provider: object | None) -> SimpleNamespace:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ccxt_provider=ccxt_provider)))


def _patch_worker_ccxt(monkeypatch: pytest.MonkeyPatch, provider: object) -> None:
    celery_module = import_module("src.tasks.celery_app")
    monkeypatch.setattr(
        celery_module,
        "get_ccxt_provider_for_worker",
        lambda: provider,
    )


@pytest.mark.parametrize(("builder", "dispatcher_type"), WORKER_BUILDERS)
def test_worker_services_use_noop_dispatchers(builder, dispatcher_type) -> None:
    """Worker 실행은 자기 자신을 Celery에 다시 dispatch하지 않는다."""
    session = object()

    service = builder(session)

    assert isinstance(service.dispatcher, dispatcher_type)


@pytest.mark.asyncio
@pytest.mark.parametrize(("builder", "dispatcher_type"), HTTP_BUILDERS)
async def test_http_services_use_celery_dispatchers(builder, dispatcher_type) -> None:
    """HTTP submit 경로는 Celery dispatcher를 주입한다."""
    session = object()
    ohlcv_provider = object()

    service = await builder(ohlcv_provider, session)

    assert isinstance(service.dispatcher, dispatcher_type)


@pytest.mark.parametrize(("builder", "_dispatcher_type"), WORKER_BUILDERS)
def test_worker_services_use_fixture_provider_with_configured_root(
    monkeypatch: pytest.MonkeyPatch,
    builder,
    _dispatcher_type,
) -> None:
    """fixture 설정은 세 worker 모두 같은 configured root를 쓴다."""
    monkeypatch.setattr(settings, "ohlcv_provider", "fixture")

    service = builder(object())

    assert isinstance(service.provider, FixtureProvider)
    assert service.provider.root == Path(settings.ohlcv_fixture_root)


@pytest.mark.parametrize(("builder", "_dispatcher_type"), WORKER_BUILDERS)
def test_worker_services_use_timescale_provider_with_configured_exchange(
    monkeypatch: pytest.MonkeyPatch,
    builder,
    _dispatcher_type,
) -> None:
    """timescale 설정은 세 worker 모두 worker CCXT와 기본 거래소를 조립한다."""
    ccxt_provider = object()
    monkeypatch.setattr(settings, "ohlcv_provider", "timescale")
    _patch_worker_ccxt(monkeypatch, ccxt_provider)

    service = builder(object())

    assert isinstance(service.provider, TimescaleProvider)
    assert service.provider.ccxt is ccxt_provider
    assert service.provider.exchange_name == settings.default_exchange


@pytest.mark.parametrize(("builder", "repository_attributes"), REPOSITORY_ATTRIBUTES)
def test_worker_services_share_one_session_across_repositories(
    builder,
    repository_attributes: tuple[str, ...],
) -> None:
    """한 worker service의 모든 repository는 같은 transaction session을 공유한다."""
    session = object()

    service = builder(session)

    assert all(
        getattr(service, attribute).session is session for attribute in repository_attributes
    )


def test_worker_builder_reads_provider_setting_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """관측값: import 뒤 설정을 바꿔도 다음 worker 조립에 즉시 반영된다."""
    session = object()
    monkeypatch.setattr(settings, "ohlcv_provider", "fixture")
    fixture_service = build_optimizer_service_for_worker(session)

    ccxt_provider = object()
    monkeypatch.setattr(settings, "ohlcv_provider", "timescale")
    _patch_worker_ccxt(monkeypatch, ccxt_provider)
    timescale_service = build_optimizer_service_for_worker(session)

    assert isinstance(fixture_service.provider, FixtureProvider)
    assert isinstance(timescale_service.provider, TimescaleProvider)
    assert timescale_service.provider.ccxt is ccxt_provider


@pytest.mark.asyncio
async def test_get_ccxt_provider_returns_request_app_state_identity() -> None:
    """HTTP DI는 lifespan가 보관한 CCXT singleton을 변형 없이 넘긴다."""
    ccxt_provider = object()
    request = _request_with_ccxt(ccxt_provider)

    result = await get_ccxt_provider(request)

    assert result is ccxt_provider


@pytest.mark.asyncio
async def test_get_ohlcv_provider_uses_fixture_with_configured_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP DI도 fixture 설정에서는 request CCXT 없이 fixture를 조립한다."""
    monkeypatch.setattr(settings, "ohlcv_provider", "fixture")

    provider = await get_ohlcv_provider(_request_with_ccxt(None), object())

    assert isinstance(provider, FixtureProvider)
    assert provider.root == Path(settings.ohlcv_fixture_root)


@pytest.mark.asyncio
async def test_get_ohlcv_provider_rejects_timescale_without_ccxt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """timescale HTTP 경로는 lifespan CCXT singleton이 없으면 즉시 실패한다."""
    monkeypatch.setattr(settings, "ohlcv_provider", "timescale")

    with pytest.raises(RuntimeError, match="ccxt_provider가 None"):
        await get_ohlcv_provider(_request_with_ccxt(None), object())


@pytest.mark.asyncio
async def test_get_ohlcv_provider_uses_timescale_with_request_ccxt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """timescale HTTP 경로는 request CCXT와 session repository를 조립한다."""
    session = object()
    ccxt_provider = object()
    monkeypatch.setattr(settings, "ohlcv_provider", "timescale")

    provider = await get_ohlcv_provider(_request_with_ccxt(ccxt_provider), session)

    assert isinstance(provider, TimescaleProvider)
    assert provider.repo.session is session
    assert provider.ccxt is ccxt_provider
    assert provider.exchange_name == settings.default_exchange
