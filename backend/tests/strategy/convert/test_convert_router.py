"""Convert 라우터 — 인증 및 에러 처리 테스트."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_convert_requires_auth(client: AsyncClient) -> None:
    """인증 없이 요청 시 401 반환."""
    resp = await client.post(
        "/api/v1/strategies/convert-indicator",
        json={"code": "//@version=5\nindicator(\"T\")\nbull=close>open\nplotshape(bull)"},
    )
    assert resp.status_code == 401
