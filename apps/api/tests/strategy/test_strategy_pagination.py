"""Strategy list pagination — limit/offset 표준 + page deprecated fallback."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_with_limit_offset_default(
    client: AsyncClient, mock_clerk_auth
) -> None:
    """offset 미지정 시 0 — 첫 페이지."""
    res = await client.get("/api/v1/strategies?limit=10&offset=0")
    assert res.status_code == 200
    body = res.json()
    assert body["limit"] == 10
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_list_with_offset_advances_page(
    client: AsyncClient, mock_clerk_auth
) -> None:
    """offset이 limit의 배수면 page는 자동 환산."""
    res = await client.get("/api/v1/strategies?limit=10&offset=20")
    assert res.status_code == 200
    body = res.json()
    # offset=20, limit=10 → page=3 (역산)
    assert body["page"] == 3
    assert body["limit"] == 10


@pytest.mark.asyncio
async def test_list_with_legacy_page_param(
    client: AsyncClient, mock_clerk_auth
) -> None:
    """기존 page 파라미터 — deprecated이지만 fallback 동작."""
    res = await client.get("/api/v1/strategies?limit=10&page=3")
    assert res.status_code == 200
    body = res.json()
    # page=3, limit=10 → offset=20 → 응답 page=3
    assert body["page"] == 3
    assert body["limit"] == 10


@pytest.mark.asyncio
async def test_list_page_overrides_offset_when_both_supplied(
    client: AsyncClient, mock_clerk_auth
) -> None:
    """둘 다 들어오면 page가 우선 (legacy 호환)."""
    # page=2, limit=10 → offset=10 (offset=999 무시)
    res = await client.get("/api/v1/strategies?limit=10&page=2&offset=999")
    assert res.status_code == 200
    body = res.json()
    assert body["page"] == 2
