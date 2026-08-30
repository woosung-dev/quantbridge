# 계정 범위 USDT balance endpoint의 HTTP·캐시 계약을 검증한다.
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.common.exceptions import AppException
from src.main import app_exc_handler
from src.trading.dependencies import get_balance_service
from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, ExchangeName
from src.trading.providers import BalanceSnapshot, Credentials
from src.trading.router import router
from src.trading.services.balance_service import AccountBalanceService


def _account(
    account_id,
    user_id,
    exchange: ExchangeName = ExchangeName.bybit,
    mode: ExchangeMode = ExchangeMode.demo,
):
    return SimpleNamespace(id=account_id, user_id=user_id, exchange=exchange, mode=mode)


def _service(account, redis_value=None, provider_result=None):
    repo = SimpleNamespace(get_by_id=AsyncMock(return_value=account))
    account_service = SimpleNamespace(
        get_credentials_for_order=AsyncMock(
            return_value=Credentials(api_key="key", api_secret="secret")
        )
    )
    provider = SimpleNamespace(
        fetch_usdt_balance_snapshot=AsyncMock(
            return_value=provider_result or BalanceSnapshot(Decimal("10"), Decimal("8"))
        )
    )
    redis = SimpleNamespace(get=AsyncMock(return_value=redis_value), set=AsyncMock())
    return (
        AccountBalanceService(
            account_repo=repo,
            account_service=account_service,
            bybit_futures_provider=provider,
            redis=redis,
        ),
        account_service,
        provider,
        redis,
    )


def _app(service, user_id):
    app = FastAPI()
    app.add_exception_handler(AppException, app_exc_handler)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_balance_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    return app


@pytest.mark.asyncio
async def test_balance_api_returns_usdt_wallet_snapshot():
    account_id, user_id = uuid4(), uuid4()
    service, _, _, redis = _service(_account(account_id, user_id))
    app = _app(service, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{account_id}/balance")

    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == str(account_id)
    assert body["asset"] == "USDT"
    assert body["supported"] is True
    assert body["reason"] is None
    assert body["total"] == "10"
    assert body["free"] == "8"
    assert body["fetched_at"] is not None
    cache_key, cache_value = redis.set.await_args.args[:2]
    assert cache_key == f"qb_balance_snapshot:{account_id}"
    assert json.loads(cache_value)["total"] == "10"
    assert redis.set.await_args.kwargs["ex"] == 15


@pytest.mark.asyncio
async def test_balance_api_returns_404_for_missing_account():
    account_id, user_id = uuid4(), uuid4()
    service, _, _, _ = _service(None)
    app = _app(service, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{account_id}/balance")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_balance_api_returns_404_for_non_owner():
    account_id, user_id = uuid4(), uuid4()
    service, _, _, _ = _service(_account(account_id, uuid4()))
    app = _app(service, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{account_id}/balance")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_balance_api_returns_unsupported_for_non_bybit_account():
    account_id, user_id = uuid4(), uuid4()
    service, account_service, provider, _ = _service(
        _account(account_id, user_id, ExchangeName.okx)
    )
    app = _app(service, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{account_id}/balance")

    assert response.status_code == 200
    assert response.json() == {
        "account_id": str(account_id),
        "asset": "USDT",
        "supported": False,
        "reason": "bybit_demo_only",
        "total": None,
        "free": None,
        "fetched_at": None,
    }
    account_service.get_credentials_for_order.assert_not_awaited()
    provider.fetch_usdt_balance_snapshot.assert_not_awaited()


@pytest.mark.asyncio
async def test_balance_api_maps_provider_error_to_503():
    account_id, user_id = uuid4(), uuid4()
    service, _, provider, _ = _service(_account(account_id, user_id))
    provider.fetch_usdt_balance_snapshot.side_effect = ProviderError("unavailable")
    app = _app(service, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/exchange-accounts/{account_id}/balance")

    assert response.status_code == 503
    assert response.json()["detail"] == "exchange balance lookup unavailable"


async def test_balance_service_uses_cache_without_calling_provider():
    account_id, user_id = uuid4(), uuid4()
    fetched_at = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    cache_value = json.dumps(
        {"total": "100.5", "free": "90.25", "fetched_at": fetched_at.isoformat()}
    ).encode()
    service, account_service, provider, redis = _service(
        _account(account_id, user_id), redis_value=cache_value
    )

    response = await service.get_balance(user_id, account_id)

    assert response.total == Decimal("100.5")
    assert response.free == Decimal("90.25")
    assert response.fetched_at == fetched_at
    account_service.get_credentials_for_order.assert_not_awaited()
    provider.fetch_usdt_balance_snapshot.assert_not_awaited()
    redis.set.assert_not_awaited()


async def test_balance_service_force_refresh_bypasses_cache():
    """BL-479 — 세션 기준선처럼 영구히 남는 값은 15초 stale 을 물려받으면 안 된다.

    ★위 캐시 테스트와 **쌍으로** 판별력이다. 캐시 히트 상황을 그대로 두고 플래그만 켜서
    거래소를 실제로 치는지 본다. 한쪽만 있으면 "항상 캐시를 건너뛰는" 구현을 정상으로
    착각한다.
    """
    account_id, user_id = uuid4(), uuid4()
    fetched_at = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    cache_value = json.dumps(
        {"total": "100.5", "free": "90.25", "fetched_at": fetched_at.isoformat()}
    ).encode()
    service, account_service, provider, redis = _service(
        _account(account_id, user_id), redis_value=cache_value
    )

    response = await service.get_balance(user_id, account_id, force_refresh=True)

    # 캐시(100.5)가 아니라 provider 가 준 값이 나와야 한다.
    assert response.total != Decimal("100.5")
    account_service.get_credentials_for_order.assert_awaited_once()
    provider.fetch_usdt_balance_snapshot.assert_awaited_once()
    # 갱신값은 캐시에 다시 써서 뒤따르는 조회가 이득을 본다.
    redis.set.assert_awaited_once()
