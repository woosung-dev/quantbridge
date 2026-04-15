"""POST /api/v1/strategies/parse E2E."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_parse_preview_returns_ok_for_valid_source(client, mock_clerk_auth):
    source = """//@version=5
strategy("ema")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": source})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["pine_version"] == "v5"


@pytest.mark.asyncio
async def test_parse_preview_returns_unsupported(client, mock_clerk_auth):
    source = """//@version=5
strategy("no")
x = request.security(syminfo.tickerid, "1D", close)
"""
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": source})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("unsupported", "error")
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_parse_preview_rejects_empty_source(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": ""})
    assert res.status_code == 422  # Pydantic min_length


@pytest.mark.asyncio
async def test_parse_preview_requires_auth(client):
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": "x"})
    assert res.status_code == 401
