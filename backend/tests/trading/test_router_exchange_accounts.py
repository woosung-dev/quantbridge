"""ExchangeAccount REST endpoints E2E (T18).

Uses mock_clerk_auth fixture from conftest.py for auth bypass.
URLs: /api/v1/exchange-accounts (router has no prefix; main.py adds /api/v1).
"""
from __future__ import annotations

import pytest


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
async def test_list_exchange_accounts_returns_registered(client, mock_clerk_auth):
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

    res = await client.get("/api/v1/exchange-accounts")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["exchange"] == "bybit"
    assert "******" in item["api_key_masked"]


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
