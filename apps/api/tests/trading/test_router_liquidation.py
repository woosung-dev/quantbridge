"""청산가 미리보기 엔드포인트 E2E — demo-only calc+display, 인증 필요.

URL: /api/v1/liquidation/preview (router prefix 없음; main.py 가 /api/v1 추가).
"""

from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_preview_long_liquidation(client, mock_authed_user):
    """Long: 50000 × (1 − 0.1 + 0.005) = 45250, distance 9.5%."""
    resp = await client.post(
        "/api/v1/liquidation/preview",
        json={
            "symbol": "BTC/USDT",
            "side": "buy",
            "entry_price": "50000",
            "leverage": 10,
            "maintenance_margin_rate": "0.005",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert Decimal(body["liquidation_price"]) == Decimal("45250")
    assert Decimal(body["distance_pct"]) == Decimal("9.5")
    assert Decimal(body["maintenance_margin_rate"]) == Decimal("0.005")
    assert body["side"] == "buy"


@pytest.mark.asyncio
async def test_preview_short_liquidation(client, mock_authed_user):
    """Short: 50000 × (1 + 0.1 − 0.005) = 54750."""
    resp = await client.post(
        "/api/v1/liquidation/preview",
        json={
            "symbol": "BTC/USDT",
            "side": "sell",
            "entry_price": "50000",
            "leverage": 10,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert Decimal(body["liquidation_price"]) == Decimal("54750")
    # default MMR 적용 (0.005)
    assert Decimal(body["maintenance_margin_rate"]) == Decimal("0.005")


@pytest.mark.asyncio
async def test_preview_rejects_zero_leverage(client, mock_authed_user):
    resp = await client.post(
        "/api/v1/liquidation/preview",
        json={
            "symbol": "BTC/USDT",
            "side": "buy",
            "entry_price": "50000",
            "leverage": 0,
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_preview_rejects_negative_entry(client, mock_authed_user):
    resp = await client.post(
        "/api/v1/liquidation/preview",
        json={
            "symbol": "BTC/USDT",
            "side": "buy",
            "entry_price": "-1",
            "leverage": 10,
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_preview_requires_auth(client):
    """인증 없으면 401/403 (IDOR 표면 없음, 인증만 게이트)."""
    resp = await client.post(
        "/api/v1/liquidation/preview",
        json={
            "symbol": "BTC/USDT",
            "side": "buy",
            "entry_price": "50000",
            "leverage": 10,
        },
    )
    assert resp.status_code in (401, 403), resp.text
