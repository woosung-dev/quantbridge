"""ExchangeAccount REST endpoints E2E (T18).

Uses mock_clerk_auth fixture from conftest.py for auth bypass.
URLs: /api/v1/exchange-accounts (router has no prefix; main.py adds /api/v1).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.trading.providers import BybitFuturesProvider


@pytest.fixture(autouse=True)
def mock_exchange_identity(monkeypatch):
    identity = AsyncMock(return_value=("558689281", False))
    monkeypatch.setattr(BybitFuturesProvider, "fetch_api_identity", identity)
    return identity


@pytest.mark.asyncio
async def test_register_exchange_account_returns_201(client, mock_clerk_auth):
    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": "ABCD1234EFGH5678",
            "api_secret": "secret_value_here_1234",
            "label": "My Bybit Demo",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["exchange"] == "bybit"
    assert body["mode"] == "demo"
    assert body["label"] == "My Bybit Demo"
    # api_key_masked should hide middle portion
    assert body["api_key_masked"].startswith("ABCD")
    assert body["api_key_masked"].endswith("5678")
    assert "******" in body["api_key_masked"]
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_list_exchange_accounts_returns_registered(
    client, mock_clerk_auth, mock_exchange_identity
):
    # Register an account first
    await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": "ABCD1234EFGH5678",
            "api_secret": "secret_value_here_1234",
        },
    )
    mock_exchange_identity.reset_mock()

    res = await client.get("/api/v1/exchange-accounts")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["exchange"] == "bybit"
    assert "******" in item["api_key_masked"]
    assert item["exchange_uid"] == "558689281"
    assert item["read_only"] is False
    mock_exchange_identity.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_exchange_account_returns_204(client, mock_clerk_auth):
    # Register
    create_res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": "ABCD1234EFGH5678",
            "api_secret": "secret_value_here_1234",
        },
    )
    account_id = create_res.json()["id"]

    # Delete
    del_res = await client.delete(f"/api/v1/exchange-accounts/{account_id}")
    assert del_res.status_code == 204

    # Verify gone
    list_res = await client.get("/api/v1/exchange-accounts")
    assert list_res.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_account_returns_404(client, mock_clerk_auth):
    import uuid

    fake_id = uuid.uuid4()
    res = await client.delete(f"/api/v1/exchange-accounts/{fake_id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_mask_api_key_short_key(client, mock_clerk_auth):
    """Keys shorter than 8 chars should be fully masked."""
    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": "short",
            "api_secret": "secret_value_here_1234",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["api_key_masked"] == "*****"


# ── [BL-762] 라우터가 **공개 표면을 통해서만** 서비스를 부르는지 고정한다 ──────────
#
# ★codex P3 (2026-08-16): 서비스 단위 commit-spy 만으로는 이 회차의 목표가 안 지켜진다.
#   라우터를 다시 `svc._repo.get_by_id/delete/commit` 로 되돌려도 그 spy 와 위의 204/404
#   테스트는 **전부 통과**한다 — 즉 「라우터가 private 을 뚫는다」의 회귀를 아무도 못 막는다.
#   여기서는 DI 를 갈아끼워 **어느 메서드가 불렸는지**를 직접 본다.


@pytest.fixture
def spy_account_service(app):
    """`ExchangeAccountService` 를 spy 로 갈아끼운다. 공개 메서드만 노출한다."""
    from src.trading.dependencies import get_exchange_account_service

    spy = AsyncMock()
    spy.masked_api_key = lambda _account: "AB******78"  # 동기 메서드다
    app.dependency_overrides[get_exchange_account_service] = lambda: spy
    yield spy
    app.dependency_overrides.pop(get_exchange_account_service, None)


@pytest.mark.asyncio
async def test_delete_route_calls_public_service_method(
    client, mock_clerk_auth, spy_account_service
):
    """DELETE 는 `delete_for_user(account_id, user_id)` 를 부른다 — repo 를 직접 만지지 않는다."""
    import uuid

    account_id = uuid.uuid4()
    res = await client.delete(f"/api/v1/exchange-accounts/{account_id}")

    assert res.status_code == 204
    spy_account_service.delete_for_user.assert_awaited_once_with(account_id, mock_clerk_auth.id)
    # ★라우터가 트랜잭션·조회를 직접 몰아서는 안 된다. 이 셋이 이 회차가 지운 것이다.
    spy_account_service._repo.commit.assert_not_awaited()
    spy_account_service._repo.delete.assert_not_awaited()
    spy_account_service._repo.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_route_calls_public_service_method(client, mock_clerk_auth, spy_account_service):
    """GET 목록은 `list_for_user(user_id)` 를 부른다."""
    spy_account_service.list_for_user.return_value = []

    res = await client.get("/api/v1/exchange-accounts")

    assert res.status_code == 200
    spy_account_service.list_for_user.assert_awaited_once_with(mock_clerk_auth.id)
    spy_account_service._repo.list_by_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_route_does_not_commit_twice(client, mock_clerk_auth, spy_account_service):
    """POST 는 `register()` 만 부른다 — 커밋은 서비스 안에서 한 번이다.

    종전 라우터는 `register()` 뒤에 `svc._repo.commit()` 을 한 번 더 쳤다(중복 커밋).
    """
    import uuid
    from datetime import UTC, datetime

    from src.trading.models import ExchangeMode, ExchangeName

    saved = SimpleNamespace(
        id=uuid.uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        label="spy",
        api_key_encrypted=b"x",
        exchange_uid="558689281",
        read_only=False,
        created_at=datetime.now(UTC),
    )
    spy_account_service.register.return_value = saved

    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": "ABCD1234EFGH5678",
            "api_secret": "secret_value_here_1234",
        },
    )

    assert res.status_code == 201, res.text
    spy_account_service.register.assert_awaited_once()
    spy_account_service._repo.commit.assert_not_awaited()
