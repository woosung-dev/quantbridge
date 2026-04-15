"""Strategy CRUD E2E — POST/GET."""
from __future__ import annotations

import pytest

_OK = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""

_BAD = """//@version=5
strategy("bad")
x = request.security(syminfo.tickerid, "1D", close)
"""


@pytest.mark.asyncio
async def test_create_strategy_ok_returns_201_with_parse_status(client, mock_clerk_auth):
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "my ema", "pine_source": _OK, "timeframe": "1h", "symbol": "BTCUSDT", "tags": ["ema"]},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "my ema"
    assert body["parse_status"] == "ok"
    assert body["pine_version"] == "v5"
    assert body["tags"] == ["ema"]


@pytest.mark.asyncio
async def test_create_strategy_stores_unsupported(client, mock_clerk_auth):
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "bad", "pine_source": _BAD},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["parse_status"] in ("unsupported", "error")
    assert body["parse_errors"] is not None


@pytest.mark.asyncio
async def test_list_strategies_paginates(client, mock_clerk_auth):
    # 3건 생성
    for i in range(3):
        await client.post(
            "/api/v1/strategies",
            json={"name": f"s{i}", "pine_source": _OK},
        )
    res = await client.get("/api/v1/strategies?page=1&limit=2")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_filter_parse_status(client, mock_clerk_auth):
    await client.post("/api/v1/strategies", json={"name": "ok", "pine_source": _OK})
    await client.post("/api/v1/strategies", json={"name": "bad", "pine_source": _BAD})

    res = await client.get("/api/v1/strategies?parse_status=unsupported")
    assert res.status_code == 200
    body = res.json()
    for item in body["items"]:
        assert item["parse_status"] == "unsupported"


@pytest.mark.asyncio
async def test_list_pine_source_not_in_items(client, mock_clerk_auth):
    await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    res = await client.get("/api/v1/strategies")
    assert res.status_code == 200
    body = res.json()
    for item in body["items"]:
        assert "pine_source" not in item
